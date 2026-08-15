#!/usr/bin/env bash
# Exercise the exact archived launcher with no usable external stat command.
set -euo pipefail

export LC_ALL=C
export TZ=UTC
umask 077

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
REPOSITORY_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)
ARCHIVE=${1:-"$REPOSITORY_ROOT/dist/v1.1.2/magicrampage.zip"}
APK=${MAGICRAMPAGE_APK:-}
EXPECTED_APK_SHA256=${MAGICRAMPAGE_EXPECT_APK_SHA256:-23f72590c725b2c4457136614e95f641be320b61e7f2db2453a934f77b905ae4}

fail() {
  printf 'magicrampage final ZIP gate: FAIL: %s\n' "$*" >&2
  exit 1
}

[[ -f $ARCHIVE && ! -L $ARCHIVE ]] || fail "unsafe or missing archive: $ARCHIVE"
[[ -n $APK && -f $APK && ! -L $APK ]] ||
  fail 'set MAGICRAMPAGE_APK to the accepted owner APK'
[[ $EXPECTED_APK_SHA256 =~ ^[0-9a-f]{64}$ ]] ||
  fail 'MAGICRAMPAGE_EXPECT_APK_SHA256 is invalid'
[[ $(sha256sum -- "$APK" | awk '{print $1}') == "$EXPECTED_APK_SHA256" ]] ||
  fail 'owner APK SHA-256 differs from the selected fixture identity'

TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/magicrampage-final-zip.XXXXXX")
cleanup() {
  case $TEST_ROOT in
    "${TMPDIR:-/tmp}"/magicrampage-final-zip.*)
      [[ -d $TEST_ROOT ]] && rm -rf -- "$TEST_ROOT"
      ;;
    *) printf 'refusing unsafe cleanup target: %s\n' "$TEST_ROOT" >&2 ;;
  esac
}
trap cleanup EXIT INT TERM

PORTS_ROOT="$TEST_ROOT/roms/ports"
XDG_ROOT="$TEST_ROOT/xdg"
PM_ROOT="$XDG_ROOT/PortMaster"
RUNTIME_ROOT="$TEST_ROOT/runtime"
MARKERS="$TEST_ROOT/markers"
NO_STAT="$TEST_ROOT/no-stat"
mkdir -p -- "$PORTS_ROOT" "$PM_ROOT" "$RUNTIME_ROOT" "$MARKERS" "$NO_STAT"
chmod 0700 "$RUNTIME_ROOT"
unzip -q "$ARCHIVE" -d "$PORTS_ROOT"

[[ -f $PORTS_ROOT/magicrampage/INSTALLATION.md ]] ||
  fail 'INSTALLATION.md is absent from the final ZIP'
python3 -B - "$PORTS_ROOT" <<'PY'
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
for path in root.rglob("*"):
    if not path.is_file():
        continue
    if path.suffix.lower() not in {".md", ".txt", ".json", ".xml"} and \
            path.name not in {"LICENSE", "NOTICE"}:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    match = re.search(r"(?i)\b(?:5play|apkvision|mod|hack)\b", text)
    if match:
        raise SystemExit(
            "prohibited distribution label in %s: %s" %
            (path.relative_to(root), match.group(0))
        )
    if "Reference filename:" in text or "Nome de referência:" in text:
        raise SystemExit("owner source filename leaked in " + str(path.relative_to(root)))
PY
[[ -x $PORTS_ROOT/Magic\ Rampage.sh ]] || fail 'launcher mode was lost'
[[ -x $PORTS_ROOT/magicrampage/nxsplash-nextos ]] ||
  fail 'nxsplash mode was lost'
[[ -x $PORTS_ROOT/magicrampage/nxextract/nxextract-ui ]] ||
  fail 'NXExtract UI mode was lost'
[[ $(sha256sum -- "$PORTS_ROOT/magicrampage/nxextract/nxextract-ui" | awk '{print $1}') == \
   7ca901d8515ab9a084be81e05888e1fd03cec80fb03896df6331c1c95698ef56 ]] ||
  fail 'NXExtract UI identity drifted in the final ZIP'

mkdir -p -- "$PORTS_ROOT/magicrampage/gamedata"
REPACKED_APK="$TEST_ROOT/renamed-and-repacked-owner.apk"
cp -- "$APK" "$REPACKED_APK"
python3 -B - "$REPACKED_APK" <<'PY'
import pathlib
import sys
import zipfile

apk = pathlib.Path(sys.argv[1])
with zipfile.ZipFile(apk, "a", allowZip64=True) as archive:
    archive.comment = b"NXExtract flexible-container fixture\n"
PY
[[ $(sha256sum -- "$REPACKED_APK" | awk '{print $1}') != "$EXPECTED_APK_SHA256" ]] ||
  fail 'repacked APK did not change whole-container SHA-256'
python3 -B - "$REPACKED_APK" <<'PY'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1], "r") as archive:
    bad = archive.testzip()
if bad is not None:
    raise SystemExit("repacked APK contains a damaged member: " + bad)
PY
cp -- "$REPACKED_APK" "$PORTS_ROOT/magicrampage/gamedata/community-variant.apk"

# Keep the launcher bytes exact while replacing only target-architecture
# payloads in this disposable host fixture.
cat > "$PORTS_ROOT/magicrampage/nxextract/nxextract-ui" <<'UI'
#!/bin/bash
printf 'ui\n' >> "$NXZIP_MARKERS/events"
(umask 077; printf 'visible=sdl\n' > "$3")
printf 'title=%s version=%s\n' "$4" "$5" > "$NXZIP_MARKERS/ui"
while [ ! -e "$2" ]; do sleep 0.05; done
exit 0
UI
cat > "$PORTS_ROOT/magicrampage/nxsplash-nextos" <<'SPLASH'
#!/bin/bash
printf 'splash\n' >> "$NXZIP_MARKERS/events"
printf 'splash=%s\n' "$1" >> "$NXZIP_MARKERS/splash"
exit 0
SPLASH
cat > "$PORTS_ROOT/magicrampage/bin/aarch64/magicrampage-nextos" <<'GAME'
#!/bin/bash
printf 'game\n' >> "$NXZIP_MARKERS/events"
printf 'game_dir=%s\n' "$1" >> "$NXZIP_MARKERS/child"
exit 42
GAME
chmod 0755 \
  "$PORTS_ROOT/magicrampage/nxextract/nxextract-ui" \
  "$PORTS_ROOT/magicrampage/nxsplash-nextos" \
  "$PORTS_ROOT/magicrampage/bin/aarch64/magicrampage-nextos"

cat > "$NO_STAT/stat" <<NO_STAT_SENTINEL
#!/bin/bash
: > "$MARKERS/stat-called"
exit 127
NO_STAT_SENTINEL
chmod 0755 "$NO_STAT/stat"

cat > "$PM_ROOT/control.txt" <<CONTROL
directory="${TEST_ROOT#/}/roms"
controlfolder="$PM_ROOT"
CFW_NAME=hostfixture
ESUDO=""
CUR_TTY=/dev/null
sdl_controllerconfig="fixture-guid,Magic Rampage Test,a:b0"
get_controls() { ANALOGSTICKS=2; }
pm_platform_helper() { printf 'helper\n' >> "$MARKERS/platform-helper"; }
pm_finish() { printf 'finish\n' >> "$MARKERS/pm-finish"; }
CONTROL

status=0
env -i PATH="$NO_STAT:$PATH" HOME="$TEST_ROOT" TMPDIR="${TMPDIR:-/tmp}" \
  XDG_DATA_HOME="$XDG_ROOT" XDG_RUNTIME_DIR="$RUNTIME_ROOT" \
  NXZIP_MARKERS="$MARKERS" \
  bash "$PORTS_ROOT/Magic Rampage.sh" </dev/null || status=$?
[[ $status == 42 ]] || fail "launcher returned $status instead of child status 42"
[[ ! -e $MARKERS/stat-called ]] || fail 'an executable shell path called external stat'
[[ -s $MARKERS/ui && -s $MARKERS/child && -s $MARKERS/splash ]] ||
  fail 'NXExtract UI, splash or child did not execute'
[[ $(paste -sd, "$MARKERS/events") == ui,splash,game ]] ||
  fail 'first-launch order differs from UI -> splash -> game'
[[ $(wc -l < "$MARKERS/pm-finish") == 1 ]] ||
  fail 'pm_finish did not run exactly once'
grep -Fq 'setup UI started with' \
  "$PORTS_ROOT/magicrampage/nxextract.log" ||
  fail 'NXExtract log lacks proof that the packaged UI started'
grep -Fq 'mandatory setup UI graphical renderer confirmed: sdl' \
  "$PORTS_ROOT/magicrampage/nxextract.log" ||
  fail 'NXExtract log lacks visible-renderer attestation'
grep -Fq 'nxsplash 0.1.2: mandatory handoff complete' \
  "$PORTS_ROOT/magicrampage/log.txt" || fail 'runtime log lacks splash handoff'
grep -Fq '== end (status 42) ==' "$PORTS_ROOT/magicrampage/log.txt" ||
  fail 'runtime log lacks truthful child status'

# The second launch takes the fast marker path: extraction UI is no longer
# needed, but the mandatory five-second framework splash must still run.
: > "$MARKERS/events"
status=0
env -i PATH="$NO_STAT:$PATH" HOME="$TEST_ROOT" TMPDIR="${TMPDIR:-/tmp}" \
  XDG_DATA_HOME="$XDG_ROOT" XDG_RUNTIME_DIR="$RUNTIME_ROOT" \
  NXZIP_MARKERS="$MARKERS" \
  bash "$PORTS_ROOT/Magic Rampage.sh" </dev/null || status=$?
[[ $status == 42 ]] || fail "second launcher run returned $status"
[[ $(paste -sd, "$MARKERS/events") == splash,game ]] ||
  fail 'second-launch order differs from splash -> game'
[[ $(wc -l < "$MARKERS/splash") == 2 ]] ||
  fail 'mandatory splash did not execute on both launches'
[[ $(wc -l < "$MARKERS/pm-finish") == 2 ]] ||
  fail 'pm_finish did not run exactly once on each normal launch'
grep -Fq 'fast validation marker accepted; no source scan needed' \
  "$PORTS_ROOT/magicrampage/nxextract.log" ||
  fail 'second launch did not use the installed-data marker'
grep -Fq 'nxsplash 0.1.2: mandatory handoff complete' \
  "$PORTS_ROOT/magicrampage/log.txt" ||
  fail 'second runtime log lacks mandatory splash handoff'

# Fail before the normal log opens and prove the per-PID 0600 evidence file.
EARLY_ROOT="$TEST_ROOT/early"
EARLY_XDG="$TEST_ROOT/early-xdg"
mkdir -p -- "$EARLY_ROOT" "$EARLY_XDG/PortMaster"
cp -- "$PORTS_ROOT/Magic Rampage.sh" "$EARLY_ROOT/Magic Rampage.sh"
cat > "$EARLY_XDG/PortMaster/control.txt" <<EARLY_CONTROL
directory="${TEST_ROOT#/}/missing"
CFW_NAME=earlyfixture
ESUDO=""
CUR_TTY=/dev/null
pm_finish() { printf 'finish\n' >> "$MARKERS/early-pm-finish"; }
EARLY_CONTROL
status=0
env -i PATH="$NO_STAT:$PATH" HOME="$TEST_ROOT" TMPDIR="${TMPDIR:-/tmp}" \
  XDG_DATA_HOME="$EARLY_XDG" \
  bash "$EARLY_ROOT/Magic Rampage.sh" </dev/null >/dev/null 2>&1 || status=$?
[[ $status == 1 ]] || fail "pre-runtime failure returned $status"
python3 -B - "$EARLY_ROOT" <<'PY'
import pathlib
import stat
import sys

root = pathlib.Path(sys.argv[1])
logs = list(root.glob("magicrampage-launcher-error.*.log"))
if len(logs) != 1:
    raise SystemExit("pre-runtime proof count differs from one")
if stat.S_IMODE(logs[0].stat().st_mode) != 0o600:
    raise SystemExit("pre-runtime proof mode differs from 0600")
text = logs[0].read_text(encoding="utf-8")
if "nxbootstrap 0.6.14 | pre-runtime failure" not in text or "status=1 " not in text:
    raise SystemExit("pre-runtime proof lacks version or truthful status")
PY
[[ $(wc -l < "$MARKERS/early-pm-finish") == 1 ]] ||
  fail 'pre-runtime pm_finish did not run exactly once'
[[ ! -e $MARKERS/stat-called ]] || fail 'pre-runtime path called external stat'

printf '%s\n' \
  'magicrampage final ZIP gate: PASS exact-launcher=1 no-stat=1 nxextract-graphical-ui=1 repacked-apk=1 splash-every-launch=2 early-log-0600=1 finish-once=3'
