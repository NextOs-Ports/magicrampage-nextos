#!/usr/bin/env python3
"""Fail if the validated Magic Rampage runtime changes during framework migration."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parent.parent
RC2 = "v1.0.0-rc2"
V111 = "v1.1.1"
EXPECTED_BINARY_SHA256 = (
    "83b6b51f7e1112f23e52b8e89e9f36768a0456eee55b8e81e7c1e8738f9c3f99"
)
IMMUTABLE_PATHS = ("Dockerfile.glibc230",)
# v1.1.4 vendors the nxinput 0.4.0 exit-chord header (compiled into the loader).
# Pin its bytes so the runtime code shipped stays exactly the audited 0.4.0.
NXINPUT_CHORD_HEADER = "vendor/nxinput/include/nxinput_evdev_chord.h"
EXPECTED_NXINPUT_CHORD_SHA256 = (
    "813e3e7a43c4a065bad77171e8d290ac451e3098ae0cdf9dc352b72702754625"
)
RECIPE_PATHS = ("project/extractor.json", "magicrampage/extractor.json")
EXPECTED_RECIPE_VERSION = "7.8.2-7.8.7-aarch64-3"
EXPECTED_BUNDLE_APK_LIMIT = 64


def fail(message: str) -> None:
    raise SystemExit("magicrampage runtime preservation gate: FAIL: " + message)


def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), *arguments],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        fail(detail.strip())


def require_no_diff(left: str, right: str | None, paths: tuple[str, ...]) -> None:
    arguments = ["diff", "--quiet", left]
    if right is not None:
        arguments.append(right)
    arguments.extend(("--", *paths))
    result = git(*arguments, check=False)
    if result.returncode == 1:
        target = "worktree/index" if right is None else right
        fail(f"validated bytes differ between {left} and {target}")
    if result.returncode != 0:
        fail(result.stderr.strip() or "git diff could not compare validated bytes")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        fail("historical source shape drifted: " + label)
    return text.replace(old, new, 1)


for reference in (RC2, V111):
    git("rev-parse", "--verify", reference + "^{commit}")

# The historical rc2 and public v1.1.1 baselines must themselves agree. This
# makes the migration gate prove continuity instead of trusting a copied hash.
require_no_diff(RC2, V111, IMMUTABLE_PATHS)
require_no_diff(V111, None, IMMUTABLE_PATHS)

# build-glibc230.sh: the ONLY approved change from v1.1.1 is adding the include
# dirs the vendored nxinput 0.4.0 header needs (its own dir + the SDK's SDL2/ dir,
# because the header does #include <SDL.h>). No compiler/link flags otherwise.
expected_build = git("show", V111 + ":build-glibc230.sh").stdout
expected_build = replace_once(
    expected_build,
    "  -I /src/src -idirafter /sdk/usr/include \\\n",
    "  -I /src/src -I /src/vendor/nxinput/include \\\n"
    "  -idirafter /sdk/usr/include -idirafter /sdk/usr/include/SDL2 \\\n",
    "nxinput include dirs",
)
actual_build = (ROOT / "build-glibc230.sh").read_text(encoding="utf-8")
if actual_build != expected_build:
    fail("build-glibc230.sh changed outside the approved nxinput include-dir delta")

# Version 1.1.3 changes only the engine-owned input adapter: the native I-key
# slot receives keyboard I or L1. All other source files remain byte-identical
# to the physically playable v1.1.1 baseline.
source_paths = tuple(
    path
    for path in git("ls-tree", "-r", "--name-only", V111, "--", "src").stdout.splitlines()
    if path not in ("src/main.c", "src/audio_backend.c")
)
require_no_diff(RC2, V111, source_paths)
require_no_diff(V111, None, source_paths)

# src/audio_backend.c: the ONLY approved change from v1.1.1 is calling the real
# Mix_PlayChannelTimed instead of the Mix_PlayChannel macro. Some SDL_mixer SDKs
# export Mix_PlayChannel as a real symbol, so the loader carried an undefined
# Mix_PlayChannel and crashed on the first sound (spruce/Mali-G52, status 127).
expected_audio = git("show", V111 + ":src/audio_backend.c").stdout
expected_audio = replace_once(
    expected_audio,
    "    ch = Mix_PlayChannel(-1, sfx->chunk, loops);\n",
    "    /* Mix_PlayChannel e' macro -> Mix_PlayChannelTimed na maioria das SDL_mixer,\n"
    "     * mas alguns SDKs a exportam como simbolo real: o loader ganhava UND\n"
    "     * Mix_PlayChannel e crashava com \"undefined symbol\" no 1o som (spruce/Mali-G52).\n"
    "     * Chamar a funcao real (universal em toda SDL_mixer) elimina a dependencia. */\n"
    "    ch = Mix_PlayChannelTimed(-1, sfx->chunk, loops, -1);\n",
    "Mix_PlayChannelTimed universal symbol",
)
actual_audio = (ROOT / "src/audio_backend.c").read_text(encoding="utf-8")
if actual_audio != expected_audio:
    fail("src/audio_backend.c changed outside the approved Mix_PlayChannelTimed delta")

expected_main = git("show", V111 + ":src/main.c").stdout
expected_main = replace_once(
    expected_main,
    "  GS_KEY_D = 46,\n  GS_KEY_S = 61,",
    "  GS_KEY_D = 46,\n  GS_KEY_I = 51,\n  GS_KEY_S = 61,",
    "GS2D I-key enum",
)
expected_main = replace_once(
    expected_main,
    "  int accept = keys[SDL_SCANCODE_RETURN] ||",
    "  int inventory = keys[SDL_SCANCODE_I] ||\n"
    "                  controller_button_down(SDL_CONTROLLER_BUTTON_LEFTSHOULDER);\n"
    "  int accept = keys[SDL_SCANCODE_RETURN] ||",
    "L1 inventory sampling",
)
expected_main = replace_once(
    expected_main,
    "  if (accept && !(g_input_evidence & 8u)) {",
    "  if (inventory && !(g_input_evidence & 32u)) {\n"
    "    fprintf(stderr, \"[input] evidence inventory=OK\\n\");\n"
    "    g_input_evidence |= 32u;\n"
    "  }\n"
    "  if (accept && !(g_input_evidence & 8u)) {",
    "inventory diagnostic",
)
expected_main = replace_once(
    expected_main,
    "  update_android_key(self, GS_KEY_SPACE, attack);\n"
    "  update_android_key(self, GS_KEY_ENTER, accept);",
    "  update_android_key(self, GS_KEY_SPACE, attack);\n"
    "  update_android_key(self, GS_KEY_I, inventory);\n"
    "  update_android_key(self, GS_KEY_ENTER, accept);",
    "inventory publication",
)
# v1.1.4 also replaces the event-latch exit combo (BACK+START tracked by event,
# which stuck when a release was lost and closed the game on START alone) with the
# canonical nxinput 0.4.0 state-poll. Three disjoint edits, none touching the
# I-key sampling region above.
expected_main = replace_once(
    expected_main,
    '#include "audio_backend.h"\n'
    '#include "jni_min.h"\n'
    '#include "so_util.h"\n'
    '#include "util.h"\n',
    '#include "audio_backend.h"\n'
    '#include "jni_min.h"\n'
    '#include "so_util.h"\n'
    '#include "util.h"\n'
    "\n"
    "/* Exit-chord canonico (nxinput 0.4.0): SELECT+START por ESTADO vivo do SDL,\n"
    " * com hold de 3 polls e log de controle. Substitui o latch por-evento que\n"
    " * grudava BACK e fechava o jogo com START sozinho no Knulli/RG34XX-SP. */\n"
    "#define NXINPUT_EVDEV_CHORD_IMPLEMENTATION\n"
    '#include "nxinput_evdev_chord.h"\n',
    "nxinput chord include",
)
expected_main = replace_once(
    expected_main,
    "  int running = 1;\n"
    "  int back_down = 0;\n"
    "  int start_down = 0;\n"
    "  unsigned frame = 0;\n"
    "  while (running) {\n"
    "    SDL_Event e;\n"
    "    while (SDL_PollEvent(&e)) {\n"
    "      if (e.type == SDL_QUIT)\n"
    "        running = 0;\n"
    "      else if (e.type == SDL_KEYDOWN && e.key.keysym.sym == SDLK_ESCAPE)\n"
    "        running = 0;\n"
    "      else if (e.type == SDL_CONTROLLERBUTTONDOWN ||\n"
    "               e.type == SDL_CONTROLLERBUTTONUP) {\n"
    "        int down = e.type == SDL_CONTROLLERBUTTONDOWN;\n"
    "        if (e.cbutton.button == SDL_CONTROLLER_BUTTON_BACK)\n"
    "          back_down = down;\n"
    "        if (e.cbutton.button == SDL_CONTROLLER_BUTTON_START)\n"
    "          start_down = down;\n"
    "        if (back_down && start_down)\n"
    "          running = 0;\n"
    "      } else if (e.type == SDL_WINDOWEVENT &&\n",
    "  int running = 1;\n"
    "  unsigned frame = 0;\n"
    "  while (running) {\n"
    "    SDL_Event e;\n"
    "    while (SDL_PollEvent(&e)) {\n"
    "      if (e.type == SDL_QUIT)\n"
    "        running = 0;\n"
    "      else if (e.type == SDL_KEYDOWN && e.key.keysym.sym == SDLK_ESCAPE)\n"
    "        running = 0;\n"
    "      else if (e.type == SDL_WINDOWEVENT &&\n",
    "event-latch removal",
)
expected_main = replace_once(
    expected_main,
    "        GS_resize(jni_env(), jni_class(), width, height);\n"
    "      }\n"
    "    }\n"
    "\n"
    "    void *ret = GS_mainLoop(jni_env(), jni_class(), NULL);\n",
    "        GS_resize(jni_env(), jni_class(), width, height);\n"
    "      }\n"
    "    }\n"
    "\n"
    "    /* SELECT+START por ESTADO vivo (nxinput 0.4.0): imune a release perdido. */\n"
    "    if (nx_exit_chord_update(&g_controller, g_controller ? 1 : 0))\n"
    "      running = 0;\n"
    "\n"
    "    void *ret = GS_mainLoop(jni_env(), jni_class(), NULL);\n",
    "state-poll chord insertion",
)
actual_main = (ROOT / "src/main.c").read_text(encoding="utf-8")
if actual_main != expected_main:
    fail("src/main.c changed outside the approved inventory + nxinput-chord deltas")

baseline_adapter = git("show", V111 + ":magicrampage/adapter/adapter-contract.json").stdout
expected_adapter = replace_once(
    baseline_adapter,
    '    "mapping": "SDL GameController to gs2d KeyStateManager at engine-owned update point",',
    '    "mapping": "SDL GameController to gs2d KeyStateManager at engine-owned update point; L1 publishes the native I-key inventory action",',
    "adapter inventory contract",
)
actual_adapter = (ROOT / "magicrampage/adapter/adapter-contract.json").read_text(
    encoding="utf-8"
)
if actual_adapter != expected_adapter:
    fail("adapter contract changed outside the approved inventory description")

# port-env.sh: the ONLY approved change from v1.1.1 is prepending the bundled
# library directory to LD_LIBRARY_PATH so libzip.so.5 (+ libbz2/liblzma) ships
# with the port. On plain ArkOS those are absent from the host and the loader
# used to die with "libzip.so.5: cannot open shared object" (status 127). No SDL
# video/audio driver is forced. Everything else stays byte-identical.
baseline_env = git("show", V111 + ":magicrampage/port-env.sh").stdout
expected_env = replace_once(
    baseline_env,
    'BIN="$GAMEDIR/bin/aarch64/magicrampage-nextos"\nexport BIN\n',
    'BIN="$GAMEDIR/bin/aarch64/magicrampage-nextos"\n'
    'export BIN\n'
    '# Bundled libs so the port is self-contained on CFWs that do not ship them.\n'
    '# libzip.so.5 (+ libbz2.so.1.0, liblzma.so.5) is present on muOS/Knulli but NOT\n'
    '# on plain ArkOS, where the loader used to die with\n'
    '# "libzip.so.5: cannot open shared object" (status 127). Prepending the bundled\n'
    '# dir keeps every other lib coming from the firmware/PortMaster as before.\n'
    'if [ -d "$GAMEDIR/lib/aarch64" ]; then\n'
    '  export LD_LIBRARY_PATH="$GAMEDIR/lib/aarch64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n'
    'fi\n',
    "bundled-lib LD_LIBRARY_PATH",
)
expected_env = replace_once(
    expected_env,
    "inherited video/audio; PortMaster controller mapping",
    "inherited video/audio; bundled libzip; PortMaster controller mapping",
    "adapter banner note",
)
actual_env = (ROOT / "magicrampage/port-env.sh").read_text(encoding="utf-8")
if actual_env != expected_env:
    fail("port-env.sh changed outside the approved bundled-lib LD_LIBRARY_PATH delta")

# port.json: the ONLY approved change from v1.1.1 is adding the empty
# "runtime": [] attribute the current framework (nxrelease) requires in the
# PortMaster port manifest. Nothing else changes.
baseline_portjson = git("show", V111 + ":magicrampage/port.json").stdout
expected_portjson = replace_once(
    baseline_portjson,
    '    "title": "Magic Rampage"\n',
    '    "title": "Magic Rampage",\n    "runtime": []\n',
    "port.json runtime attribute",
)
actual_portjson = (ROOT / "magicrampage/port.json").read_text(encoding="utf-8")
if actual_portjson != expected_portjson:
    fail("port.json changed outside the approved runtime attribute delta")

# Version 1.1.2 deliberately adds the strongly validated 7.8.7 bundle shape.
# Prove that the only recipe changes from the playable 7.8.2 baseline are its
# visible contract label and the bounded inner-APK count (32 observed, 64 cap).
current_recipes = []
for relative in RECIPE_PATHS:
    baseline = json.loads(git("show", V111 + ":" + relative).stdout)
    current = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if current.get("version") != EXPECTED_RECIPE_VERSION:
        fail("unexpected current recipe version: " + relative)
    if current.get("input", {}).get("max_bundle_apks") != EXPECTED_BUNDLE_APK_LIMIT:
        fail("unexpected current bundle APK limit: " + relative)
    if baseline.get("version") != "7.8.2-aarch64-2":
        fail("historical recipe version drifted: " + relative)
    if baseline.get("input", {}).get("max_bundle_apks") != 16:
        fail("historical bundle APK limit drifted: " + relative)
    normalized = json.loads(json.dumps(current))
    normalized["version"] = baseline["version"]
    normalized["input"]["max_bundle_apks"] = baseline["input"]["max_bundle_apks"]
    if normalized != baseline:
        fail("recipe changed outside the approved 7.8.7 bundle delta: " + relative)
    current_recipes.append(current)
if current_recipes[0] != current_recipes[1]:
    fail("source and vendored recipes differ")

# The vendored nxinput 0.4.0 chord header is compiled into the loader; pin it.
chord_header = ROOT / NXINPUT_CHORD_HEADER
if chord_header.is_symlink() or not chord_header.is_file():
    fail(f"missing or unsafe vendored header: {NXINPUT_CHORD_HEADER}")
if hashlib.sha256(chord_header.read_bytes()).hexdigest() != EXPECTED_NXINPUT_CHORD_SHA256:
    fail("vendored nxinput chord header SHA-256 drifted: " + NXINPUT_CHORD_HEADER)

tracked_binary = ROOT / "magicrampage/bin/aarch64/magicrampage-nextos"
build_binary = ROOT / "build/magicrampage-nextos"
for path in (tracked_binary, build_binary):
    if path.is_symlink() or not path.is_file():
        fail(f"missing or unsafe validated binary: {path.relative_to(ROOT)}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != EXPECTED_BINARY_SHA256:
        fail(f"validated binary SHA-256 drifted: {path.relative_to(ROOT)}")

print(
    "magicrampage runtime preservation gate: PASS "
    "rc2=v1.0.0-rc2 baseline=v1.1.1 "
    "src_delta=inventory(main.c)+Mix_PlayChannelTimed(audio_backend.c)+nxinput-chord(main.c) "
    "build_delta=nxinput-include-dirs recipe_delta=version+max_bundle_apks-only"
)
