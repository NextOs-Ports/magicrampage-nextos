#!/usr/bin/env bash
# Validate and atomically bundle the public-quality BYO-data release.
set -euo pipefail

export LC_ALL=C
export TZ=UTC
export PYTHONDONTWRITEBYTECODE=1
umask 077

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
REPOSITORY_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)
FRAMEWORK_ROOT=${NEXTOS_FRAMEWORK_ROOT:-}
[[ -n $FRAMEWORK_ROOT && -d $FRAMEWORK_ROOT ]] || {
  printf '%s\n' \
    'set NEXTOS_FRAMEWORK_ROOT to the pinned NextOS framework source tree' >&2
  exit 1
}
FRAMEWORK_ROOT=$(CDPATH= cd -- "$FRAMEWORK_ROOT" && pwd -P)

NXRELEASE="$FRAMEWORK_ROOT/nxrelease/nxrelease.py"
NXRELEASE_VERSION=0.2.12
NXRELEASE_SHA256=276cc09d16b74c1ae22202ed8f663ce1f07e81c734932a32152e3f1fe1825621
NXGENERATOR_ROOT="$FRAMEWORK_ROOT/nxgenerator"
NXBOOTSTRAP_ROOT="$FRAMEWORK_ROOT/nxbootstrap"
NXSPLASH_ROOT="$FRAMEWORK_ROOT/nxsplash"
NXEXTRACT_ROOT="$FRAMEWORK_ROOT/../suportando_outros_devices/extrator-universal"
MANIFEST="$REPOSITORY_ROOT/nxrelease.json"
DESTINATION=${1:-"$REPOSITORY_ROOT/dist/v1.1.2"}
ARCHIVE_NAME=magicrampage.zip

fail() {
  printf 'magicrampage package error: %s\n' "$*" >&2
  exit 1
}

require_pinned_file() {
  local input_path=$1 expected_sha256=$2 label=$3
  [[ -f $input_path && ! -L $input_path ]] ||
    fail "$label is missing or unsafe"
  [[ $(sha256sum -- "$input_path" | awk '{print $1}') == "$expected_sha256" ]] ||
    fail "$label SHA-256 drifted"
}

[[ -f $NXRELEASE && -f $MANIFEST ]] || fail 'release tool or manifest missing'
require_pinned_file "$NXRELEASE" "$NXRELEASE_SHA256" 'NXRelease'
[[ $(python3 -B "$NXRELEASE" --version) == "nxrelease $NXRELEASE_VERSION" ]] ||
  fail 'NXRelease version drifted'
[[ $(<"$NXGENERATOR_ROOT/VERSION") == 0.2.8 ]] ||
  fail 'NXGenerator version drifted'
require_pinned_file \
  "$NXGENERATOR_ROOT/nxgenerator.py" \
  25b4de66ee059bf21caf162a1b0e565865f7cc38efc88b11d016d6d4b5807f27 \
  'NXGenerator'
[[ $(<"$NXBOOTSTRAP_ROOT/VERSION") == 0.6.14 ]] ||
  fail 'NXBootstrap version drifted'
require_pinned_file \
  "$NXBOOTSTRAP_ROOT/tools/generate-port.py" \
  7328364845f1044baa0275344f959d5c98c71080e749343e8b7963163e84268c \
  'NXBootstrap generator'
require_pinned_file \
  "$NXBOOTSTRAP_ROOT/templates/launcher.sh.in" \
  a3be9b12d048d3111487e9fa0295f3a7e13671258ea92c8db9b0c17ce01035f2 \
  'NXBootstrap launcher template'
[[ $(<"$NXSPLASH_ROOT/VERSION") == 0.1.2 ]] || fail 'NXSplash version drifted'
require_pinned_file \
  "$NXSPLASH_ROOT/release/manifest-v1.json" \
  14c9a0ec823eceb6b53620e443821375c0d6c2dbe4004470bcee514bb8e3d118 \
  'NXSplash release manifest'
require_pinned_file \
  "$NXSPLASH_ROOT/release/aarch64/nxsplash-nextos" \
  d85d896a906a778c9af250e5617d45d085a98b18552cb0254addbbc626036c97 \
  'NXSplash AArch64 artifact'
require_pinned_file \
  "$REPOSITORY_ROOT/magicrampage/nxsplash-nextos" \
  d85d896a906a778c9af250e5617d45d085a98b18552cb0254addbbc626036c97 \
  'vendored NXSplash AArch64 artifact'
[[ $(<"$NXEXTRACT_ROOT/VERSION") == 1.2.9 ]] || fail 'NXExtract version drifted'
require_pinned_file \
  "$NXEXTRACT_ROOT/nxextract.py" \
  7c9d44df71cbe06ff24266c3fa73f08d14ad72973c532d8ef0808af7756a4901 \
  'NXExtract engine'
require_pinned_file \
  "$NXEXTRACT_ROOT/run-extractor.sh" \
  c931427c7226d22d7e30eee8549b50f0621dca1c9d0336634aca08631f454d7a \
  'NXExtract runner'
require_pinned_file \
  "$NXEXTRACT_ROOT/nxextract-runtime-env.sh" \
  332919a9960d4317563b647f9932d1a4367da147a425fe2f78eafd706f01563f \
  'NXExtract runtime helper'
require_pinned_file \
  "$NXEXTRACT_ROOT/ui/release/aarch64/nxextract-ui" \
  7ca901d8515ab9a084be81e05888e1fd03cec80fb03896df6331c1c95698ef56 \
  'NXExtract UI AArch64 artifact'
require_pinned_file \
  "$REPOSITORY_ROOT/magicrampage/nxextract/nxextract.py" \
  7c9d44df71cbe06ff24266c3fa73f08d14ad72973c532d8ef0808af7756a4901 \
  'vendored NXExtract engine'
require_pinned_file \
  "$REPOSITORY_ROOT/magicrampage/nxextract/run-extractor.sh" \
  c931427c7226d22d7e30eee8549b50f0621dca1c9d0336634aca08631f454d7a \
  'vendored NXExtract runner'
require_pinned_file \
  "$REPOSITORY_ROOT/magicrampage/nxextract/nxextract-runtime-env.sh" \
  332919a9960d4317563b647f9932d1a4367da147a425fe2f78eafd706f01563f \
  'vendored NXExtract runtime helper'
require_pinned_file \
  "$REPOSITORY_ROOT/magicrampage/nxextract/nxextract-ui" \
  7ca901d8515ab9a084be81e05888e1fd03cec80fb03896df6331c1c95698ef56 \
  'vendored NXExtract UI AArch64 artifact'

python3 -B "$SCRIPT_DIR/check-runtime-preservation.py"
python3 -B "$SCRIPT_DIR/check-generation.py"
python3 -B "$SCRIPT_DIR/check-installation.py" \
  "$REPOSITORY_ROOT/magicrampage/extractor.json" \
  "$REPOSITORY_ROOT/magicrampage/nxport.json" \
  "$REPOSITORY_ROOT/magicrampage/INSTALLATION.md" \
  "$MANIFEST"

[[ ! -e $DESTINATION && ! -L $DESTINATION ]] ||
  fail "destination already exists: $DESTINATION"
mkdir -p -- "$(dirname -- "$DESTINATION")"

WORK_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/magicrampage-package.XXXXXX")
cleanup() {
  case $WORK_ROOT in
    "${TMPDIR:-/tmp}"/magicrampage-package.*)
      [[ -d $WORK_ROOT ]] && rm -rf -- "$WORK_ROOT"
      ;;
    *) printf 'refusing unsafe cleanup target: %s\n' "$WORK_ROOT" >&2 ;;
  esac
}
trap cleanup EXIT INT TERM

python3 -B "$NXRELEASE" validate --manifest "$MANIFEST"
python3 -B "$NXRELEASE" bundle \
  --manifest "$MANIFEST" \
  --stage "$WORK_ROOT/stage" \
  --destination "$DESTINATION" \
  --archive-name "$ARCHIVE_NAME" \
  --max-glibc 2.17
python3 -B "$NXRELEASE" verify \
  --archive "$DESTINATION/$ARCHIVE_NAME" \
  --sha256-file "$DESTINATION/$ARCHIVE_NAME.sha256" \
  --max-glibc 2.17

"$SCRIPT_DIR/test-final-zip.sh" "$DESTINATION/$ARCHIVE_NAME"

printf 'MAGIC RAMPAGE BYO RELEASE: %s\n' "$DESTINATION/$ARCHIVE_NAME"
printf '%s\n' 'profile=universal-portmaster proprietary_payload=0 compatible_apk_recipe=content-pinned'
sha256sum -- "$DESTINATION/$ARCHIVE_NAME"
