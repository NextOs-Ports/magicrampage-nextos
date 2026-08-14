#!/usr/bin/env bash
# Exercise the exact archived launcher with no usable external stat command.
set -euo pipefail

export LC_ALL=C
export TZ=UTC
umask 077

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
REPOSITORY_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)
ARCHIVE=${1:-"$REPOSITORY_ROOT/dist/v1.1.0/magicrampage.zip"}
APK=${MAGICRAMPAGE_APK:-}

fail() {
  printf 'magicrampage final ZIP gate: FAIL: %s\n' "$*" >&2
  exit 1
}

[[ -f $ARCHIVE && ! -L $ARCHIVE ]] || fail "unsafe or missing archive: $ARCHIVE"
[[ -n $APK && -f $APK && ! -L $APK ]] ||
  fail 'set MAGICRAMPAGE_APK to the accepted owner APK'
[[ $(sha256sum -- "$APK" | awk '{print $1}') == \
   91adf146037def58867c23e705a26284d56adce7b56787b6e7eea417473021e6 ]] ||
  fail 'owner APK SHA-256 differs from the release recipe'

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
[[ -x $PORTS_ROOT/Magic\ Rampage.sh ]] || fail 'launcher mode was lost'
[[ -x $PORTS_ROOT/magicrampage/nxsplash-nextos ]] ||
  fail 'nxsplash mode was lost'

mkdir -p -- "$PORTS_ROOT/magicrampage/gamedata"
cp -- "$APK" "$PORTS_ROOT/magicrampage/gamedata/owner.apk"

# Keep the launcher bytes exact while replacing only target-architecture
# payloads in this disposable host fixture.
cat > "$PORTS_ROOT/magicrampage/nxsplash-nextos" <<'SPLASH'
#!/bin/bash
printf 'splash=%s\n' "$1" > "$NXZIP_MARKERS/splash"
exit 0
SPLASH
cat > "$PORTS_ROOT/magicrampage/bin/aarch64/magicrampage-nextos" <<'GAME'
#!/bin/bash
printf 'game_dir=%s\n' "$1" > "$NXZIP_MARKERS/child"
exit 42
GAME
chmod 0755 \
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
[[ -s $MARKERS/child && -s $MARKERS/splash ]] ||
  fail 'splash or child did not execute'
[[ $(wc -l < "$MARKERS/pm-finish") == 1 ]] ||
  fail 'pm_finish did not run exactly once'
grep -Fq 'nxsplash 0.1.1: mandatory handoff complete' \
  "$PORTS_ROOT/magicrampage/log.txt" || fail 'runtime log lacks splash handoff'
grep -Fq '== end (status 42) ==' "$PORTS_ROOT/magicrampage/log.txt" ||
  fail 'runtime log lacks truthful child status'

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
if "nxbootstrap 0.6.10 | pre-runtime failure" not in text or "status=1 " not in text:
    raise SystemExit("pre-runtime proof lacks version or truthful status")
PY
[[ $(wc -l < "$MARKERS/early-pm-finish") == 1 ]] ||
  fail 'pre-runtime pm_finish did not run exactly once'
[[ ! -e $MARKERS/stat-called ]] || fail 'pre-runtime path called external stat'

printf '%s\n' \
  'magicrampage final ZIP gate: PASS exact-launcher=1 no-stat=1 nxextract=1 splash-order=1 early-log-0600=1 finish-once=2'
