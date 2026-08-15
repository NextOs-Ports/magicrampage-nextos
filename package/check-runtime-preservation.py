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
    "0b10c6c96de082cec9923d0fa32c4541c13495908b3465096a6f91481b3040e8"
)
IMMUTABLE_PATHS = (
    "Dockerfile.glibc230",
    "build-glibc230.sh",
    "magicrampage/port-env.sh",
    "magicrampage/port.json",
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

# Version 1.1.3 changes only the engine-owned input adapter: the native I-key
# slot receives keyboard I or L1. All other source files remain byte-identical
# to the physically playable v1.1.1 baseline.
source_paths = tuple(
    path
    for path in git("ls-tree", "-r", "--name-only", V111, "--", "src").stdout.splitlines()
    if path != "src/main.c"
)
require_no_diff(RC2, V111, source_paths)
require_no_diff(V111, None, source_paths)

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
actual_main = (ROOT / "src/main.c").read_text(encoding="utf-8")
if actual_main != expected_main:
    fail("src/main.c changed outside the approved L1-to-I inventory delta")

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
    "rc2=v1.0.0-rc2 baseline=v1.1.1 inventory_delta=L1-to-I-only "
    "recipe_delta=version+max_bundle_apks-only"
)
