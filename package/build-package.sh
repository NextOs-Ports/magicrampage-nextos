#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export TZ=UTC
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1786665600}
umask 022

ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
OUT=${1:-"$ROOT/dist"}
ARCHIVE="$OUT/magicrampage.zip"
HASH_FILE="$ARCHIVE.sha256"

fail() {
  printf 'magicrampage package error: %s\n' "$*" >&2
  exit 1
}

[[ ! -e $ARCHIVE && ! -e $HASH_FILE ]] || fail "release output already exists: $OUT"
[[ -x $ROOT/build/magicrampage-nextos ]] || fail "build/magicrampage-nextos is missing"

WORK=$(mktemp -d "${TMPDIR:-/tmp}/magicrampage-package.XXXXXX")
cleanup() {
  case $WORK in
    "${TMPDIR:-/tmp}"/magicrampage-package.*) rm -rf -- "$WORK" ;;
    *) printf 'refusing unsafe cleanup path: %s\n' "$WORK" >&2 ;;
  esac
}
trap cleanup EXIT INT TERM
STAGE="$WORK/stage"
VERIFY="$WORK/verify"
mkdir -p -- "$STAGE" "$VERIFY" "$OUT"

put() {
  local mode=$1 source=$2 target=$3
  [[ -f $ROOT/$source && ! -L $ROOT/$source ]] || fail "unsafe or missing source: $source"
  install -D -m "$mode" -- "$ROOT/$source" "$STAGE/$target"
}

# Explicit release allowlist. Proprietary APKs and extracted Android libraries
# never enter the package.
put 0755 "Magic Rampage.sh" "Magic Rampage.sh"
put 0755 "build/magicrampage-nextos" "magicrampage/bin/aarch64/magicrampage-nextos"
put 0644 "magicrampage/nxport.json" "magicrampage/nxport.json"
put 0644 "magicrampage/nxproject.json" "magicrampage/nxproject.json"
put 0644 "magicrampage/port-env.sh" "magicrampage/port-env.sh"
put 0644 "magicrampage/extractor.json" "magicrampage/extractor.json"
put 0644 "magicrampage/nxextract/nxextract.py" "magicrampage/nxextract/nxextract.py"
put 0644 "magicrampage/nxextract/run-extractor.sh" "magicrampage/nxextract/run-extractor.sh"
put 0644 "magicrampage/nxextract/nxextract-runtime-env.sh" "magicrampage/nxextract/nxextract-runtime-env.sh"
put 0644 "magicrampage/port.json" "magicrampage/port.json"
put 0644 "magicrampage/README.md" "magicrampage/README.md"
put 0644 "magicrampage/INSTALLATION.md" "magicrampage/INSTALLATION.md"
put 0644 "magicrampage/LICENSE" "magicrampage/LICENSE"
put 0644 "magicrampage/NOTICE.md" "magicrampage/NOTICE.md"
put 0644 "magicrampage/version.txt" "magicrampage/version.txt"
put 0644 "magicrampage/FRAMEWORK-PIN.json" "magicrampage/FRAMEWORK-PIN.json"
put 0644 "magicrampage/adapter/adapter-contract.json" "magicrampage/adapter/adapter-contract.json"
put 0644 "magicrampage/gamedata/README.txt" "magicrampage/gamedata/README.txt"

[[ -f $STAGE/magicrampage/INSTALLATION.md ]] || fail "INSTALLATION.md path is wrong"
[[ $(sha256sum "$ROOT/magicrampage/INSTALLATION.md" | awk '{print $1}') == \
   $(sha256sum "$STAGE/magicrampage/INSTALLATION.md" | awk '{print $1}') ]] ||
  fail "INSTALLATION.md differs from the documented recipe"

if find "$STAGE" -type f \( -iname '*.apk' -o -iname '*.apkm' -o -iname '*.apks' \
  -o -iname '*.xapk' -o -iname '*.obb' -o -iname '*.dex' -o -iname 'libmachine.so' \
  -o -iname 'libfmod.so' -o -iname 'libcrypto.so' -o -iname 'libc++_shared.so' \) \
  -print -quit | grep -q .; then
  fail "proprietary owner data leaked into release"
fi

while IFS= read -r shell_path; do
  bash -n "$shell_path" || fail "shell syntax failed: $shell_path"
done < <(find "$STAGE" -type f -name '*.sh' -print | sort)

python3 - "$STAGE" <<'PY'
import pathlib, re, sys
root = pathlib.Path(sys.argv[1])
external_stat = re.compile(r"(?<![A-Za-z0-9_./-])stat(?=\s|$)")
for path in root.rglob("*.sh"):
    for number, line in enumerate(path.read_text(errors="strict").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        if external_stat.search(line):
            raise SystemExit(f"external stat command in {path.relative_to(root)}:{number}")
PY

python3 -B "$STAGE/magicrampage/nxextract/nxextract.py" recipe-check \
  --recipe "$STAGE/magicrampage/extractor.json" >/dev/null
[[ $(python3 -B "$STAGE/magicrampage/nxextract/nxextract.py" --version) == \
   'NXExtract 1.2.6' ]] || fail "NXExtract version drift"

ELF="$STAGE/magicrampage/bin/aarch64/magicrampage-nextos"
file "$ELF" | grep -q 'ARM aarch64' || fail "release executable is not AArch64"
[[ $(readelf -l "$ELF" | sed -n 's@.*Requesting program interpreter: \(.*\)]@\1@p') == \
   '/lib/ld-linux-aarch64.so.1' ]] || fail "unexpected ELF interpreter"
MAX_GLIBC=$(readelf --version-info "$ELF" |
  sed -n 's/.*Name: GLIBC_\([0-9][0-9.]*\).*/\1/p' | sort -Vu | tail -n 1)
[[ -n $MAX_GLIBC ]] || fail "cannot determine GLIBC requirement"
[[ $(printf '%s\n%s\n' 2.30 "$MAX_GLIBC" | sort -V | tail -n 1) == 2.30 ]] ||
  fail "ELF exceeds GLIBC_2.30: GLIBC_$MAX_GLIBC"
[[ $(find "$STAGE" -type f -exec file --brief {} \; | grep -c '^ELF ') == 1 ]] ||
  fail "unclassified or missing ELF in package"

(
  cd "$STAGE"
  find . -type f ! -path './magicrampage/RELEASE-MANIFEST.sha256' -print0 |
    sort -z | xargs -0 sha256sum > magicrampage/RELEASE-MANIFEST.sha256
)
find "$STAGE" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +

TMP_ARCHIVE="$WORK/magicrampage.zip"
(
  cd "$STAGE"
  find . -type f -printf '%P\n' | sort | zip -X -q -9 "$TMP_ARCHIVE" -@
)
unzip -q "$TMP_ARCHIVE" -d "$VERIFY"
[[ -f $VERIFY/magicrampage/INSTALLATION.md ]] || fail "final ZIP lost INSTALLATION.md"
[[ $(sha256sum "$VERIFY/magicrampage/INSTALLATION.md" | awk '{print $1}') == \
   $(sha256sum "$ROOT/magicrampage/INSTALLATION.md" | awk '{print $1}') ]] ||
  fail "final ZIP INSTALLATION.md hash mismatch"
(
  cd "$VERIFY"
  sha256sum -c magicrampage/RELEASE-MANIFEST.sha256 >/dev/null
)

install -m 0644 "$TMP_ARCHIVE" "$ARCHIVE"
(
  cd "$OUT"
  sha256sum magicrampage.zip > magicrampage.zip.sha256
)
printf 'release=%s\nmax_glibc=%s\n' "$ARCHIVE" "$MAX_GLIBC"
sha256sum "$ARCHIVE"
