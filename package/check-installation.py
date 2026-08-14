#!/usr/bin/env python3
"""Prove that public installation instructions match the NXExtract recipe."""

import json
import pathlib
import sys


def fail(message: str) -> None:
    raise SystemExit("magicrampage installation gate: " + message)


if len(sys.argv) != 5:
    fail("expected recipe, nxport, INSTALLATION.md and nxrelease manifest")

recipe_path, nxport_path, installation_path, release_path = map(
    pathlib.Path, sys.argv[1:]
)
for path in (recipe_path, nxport_path, installation_path, release_path):
    if path.is_symlink() or not path.is_file():
        fail("missing or unsafe input: " + str(path))

recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
nxport = json.loads(nxport_path.read_text(encoding="utf-8"))
release = json.loads(release_path.read_text(encoding="utf-8"))
installation = installation_path.read_text(encoding="utf-8")

expected_package = "com.asanteegames.magicrampage"
expected_abi = "arm64-v8a"
expected_version = "7.8.2"
expected_size = 162114946
expected_sha256 = (
    "91adf146037def58867c23e705a26284d56adce7b56787b6e7eea417473021e6"
)

if recipe.get("input", {}).get("packages") != [expected_package]:
    fail("package ID differs from the accepted owner data")
if recipe.get("abi_order") != [expected_abi]:
    fail("ABI differs from the accepted owner data")

owner_entries = [
    item for item in recipe.get("extract", []) if item.get("id") == "owner-apk"
]
if len(owner_entries) != 1:
    fail("recipe must contain exactly one owner-apk extraction")
owner_validation = owner_entries[0].get("validate", {})
if owner_validation.get("size") != expected_size:
    fail("APK size differs from the accepted owner data")
if owner_validation.get("sha256") != expected_sha256:
    fail("APK SHA-256 differs from the accepted owner data")

for token, label in (
    (expected_version, "game version"),
    (expected_package, "package ID"),
    (expected_abi, "ABI"),
    (str(expected_size), "APK size"),
    (expected_sha256, "APK SHA-256"),
):
    if installation.count(token) < 2:
        fail(label + " is not present in both languages")

required = nxport.get("required_files", [])
if required[:2] != ["bin/aarch64/magicrampage-nextos", "nxsplash-nextos"]:
    fail("launcher payload order does not pin nxsplash immediately after the executable")
for path in ("game.apk", "libc++_shared.so", "libcrypto.so", "libfmod.so", "libmachine.so"):
    if path not in required:
        fail("required owner payload is missing: " + path)

release_targets = [item.get("target") for item in release.get("files", [])]
if release_targets.count("magicrampage/INSTALLATION.md") != 1:
    fail("release must contain exactly one magicrampage/INSTALLATION.md")
if any(str(target).lower().endswith((".apk", ".obb", ".dex")) for target in release_targets):
    fail("release allowlist contains proprietary Android data")

print("magicrampage installation gate: PASS")
