#!/usr/bin/env python3
"""Prove that public installation instructions match the NXExtract recipe."""

import json
import pathlib
import re
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
recipe_text = recipe_path.read_text(encoding="utf-8")

expected_package = "com.asanteegames.magicrampage"
expected_abi = "arm64-v8a"
expected_versions = ("7.8.2", "7.8.7")
expected_recipe_version = "7.8.2-7.8.7-aarch64-3"
reference_782_size = 162114946
reference_782_sha256 = (
    "91adf146037def58867c23e705a26284d56adce7b56787b6e7eea417473021e6"
)
reference_787_size = 170894843
reference_787_sha256 = (
    "23f72590c725b2c4457136614e95f641be320b61e7f2db2453a934f77b905ae4"
)
reference_787_base_size = 147950103
reference_787_base_sha256 = (
    "f2602fdda59f1326dc7d6045893373e14397fe80b5d3800892e7067b9c3cdaa9"
)
minimum_size = 134217728
maximum_size = 268435456
engine_sha256 = "8a616b3246250ea976f0935f964d1be31df186836249dfdd061558a3428fea3f"
runner_sha256 = "c931427c7226d22d7e30eee8549b50f0621dca1c9d0336634aca08631f454d7a"
runtime_env_sha256 = "332919a9960d4317563b647f9932d1a4367da147a425fe2f78eafd706f01563f"
ui_sha256 = "7ca901d8515ab9a084be81e05888e1fd03cec80fb03896df6331c1c95698ef56"
critical_payloads = {
    "android-libcxx": (
        "lib/{abi}/libc++_shared.so",
        "libc++_shared.so",
        1253544,
        "ad74bf43eb1fd576518168f664ad16a74e00eeda9595875c33dd87f6dd197869",
    ),
    "android-crypto": (
        "lib/{abi}/libcrypto.so",
        "libcrypto.so",
        5613536,
        "97cad5581cdfe401251067ac41b507478ae434d7597fe8d08c78bc215a556587",
    ),
    "android-fmod": (
        "lib/{abi}/libfmod.so",
        "libfmod.so",
        1472528,
        "fbb2ee0f88bcbd79ad1449d74215f421efa2456b3397da49229986bcfc2f27ad",
    ),
    "android-game": (
        "lib/{abi}/libmachine.so",
        "libmachine.so",
        4916048,
        "a7d56f224bbc7277551a1e16b52b36383a780d356ad099f9197658509d17b4dc",
    ),
}

for container_sha256 in (
    reference_782_sha256,
    reference_787_sha256,
    reference_787_base_sha256,
):
    if container_sha256 in recipe_text:
        fail("reference whole-container SHA-256 became a recipe lock")
if re.search(r"(?i)\b(?:5play|apkvision|mod|hack)\b", installation):
    fail("INSTALLATION.md exposes a prohibited distribution label")
for removed_label in ("Reference filename:", "Nome de referência:"):
    if removed_label in installation:
        fail("INSTALLATION.md exposes an unnecessary source filename")
for forbidden in ("SDL or active terminal", "SDL ou terminal ativo"):
    if forbidden in installation:
        fail("INSTALLATION.md still permits the quarantined terminal renderer")
for required_text in (
    "approved SDL/framebuffer identity",
    "identidade SDL/framebuffer aprovada",
):
    if required_text not in installation:
        fail("INSTALLATION.md does not preserve the approved graphical UI contract")

if recipe.get("input", {}).get("packages") != [expected_package]:
    fail("package ID differs from the accepted owner data")
if recipe.get("input", {}).get("max_bundle_apks") != 64:
    fail("bundle member ceiling must safely cover the 32-member 7.8.7 APKM")
if recipe.get("abi_order") != [expected_abi]:
    fail("ABI differs from the accepted owner data")
if recipe.get("version") != expected_recipe_version:
    fail("recipe version does not identify the 7.8.2/7.8.7 contract")

owner_entries = [
    item for item in recipe.get("extract", []) if item.get("id") == "owner-apk"
]
if len(owner_entries) != 1:
    fail("recipe must contain exactly one owner-apk extraction")
owner_validation = owner_entries[0].get("validate", {})
if owner_entries[0].get("source") != {"kind": "container"}:
    fail("owner-apk must copy the selected package container")
if owner_validation != {
    "type": "file",
    "min_size": minimum_size,
    "max_size": maximum_size,
    "magic_hex": "504b0304",
}:
    fail("owner APK must use bounded ZIP validation without one whole-file identity")

final_owner = [
    item for item in recipe.get("validate", []) if item.get("path") == "game.apk"
]
if len(final_owner) != 1 or final_owner[0] != {
    "path": "game.apk",
    "type": "file",
    "min_size": minimum_size,
    "max_size": maximum_size,
    "magic_hex": "504b0304",
}:
    fail("final owner APK gate differs from the flexible container contract")

by_id = {item.get("id"): item for item in recipe.get("extract", [])}
final_by_path = {item.get("path"): item for item in recipe.get("validate", [])}
for rule_id, (pattern, destination, size, sha256) in critical_payloads.items():
    rule = by_id.get(rule_id)
    if not isinstance(rule, dict):
        fail("critical extraction is missing: " + rule_id)
    if rule.get("source") != {"kind": "entry", "patterns": [pattern]}:
        fail("critical entry pattern drifted: " + rule_id)
    if rule.get("destination") != destination:
        fail("critical destination drifted: " + rule_id)
    expected_validation = {
        "type": "file",
        "elf_machine": "{abi}",
        "size": size,
        "sha256": sha256,
    }
    if rule.get("validate") != expected_validation:
        fail("critical extraction identity drifted: " + rule_id)
    final_validation = dict(expected_validation)
    final_validation["path"] = destination
    final_validation["elf_machine"] = expected_abi
    if final_by_path.get(destination) != final_validation:
        fail("critical final identity drifted: " + destination)

for token, label in (
    (expected_versions[0], "7.8.2 game version"),
    (expected_versions[1], "7.8.7 game version"),
    ("1214", "7.8.7 version code"),
    (expected_package, "package ID"),
    (expected_abi, "ABI"),
    (str(reference_782_size), "7.8.2 reference APK size"),
    (reference_782_sha256, "7.8.2 reference APK SHA-256"),
    (str(reference_787_size), "7.8.7 reference APKM size"),
    (reference_787_sha256, "7.8.7 reference APKM SHA-256"),
    (str(reference_787_base_size), "7.8.7 base APK size"),
    (reference_787_base_sha256, "7.8.7 base APK SHA-256"),
    (str(minimum_size), "minimum compatible APK size"),
    (str(maximum_size), "maximum compatible APK size"),
    *[(value[3], rule_id + " SHA-256") for rule_id, value in critical_payloads.items()],
):
    if installation.count(token) < 2:
        fail(label + " is not present in both languages")

required = nxport.get("required_files", [])
if nxport.get("nxextract") != {"mode": "yes", "version": "1.2.12"}:
    fail("nxport does not opt into the exact NXExtract 1.2.12 set")
if required[:2] != ["bin/aarch64/magicrampage-nextos", "nxsplash-nextos"]:
    fail("launcher payload order does not pin nxsplash immediately after the executable")
for path in ("game.apk", "libc++_shared.so", "libcrypto.so", "libfmod.so", "libmachine.so"):
    if path not in required:
        fail("required owner payload is missing: " + path)

release_files = release.get("files", [])
release_targets = [item.get("target") for item in release_files]
if release_targets.count("magicrampage/INSTALLATION.md") != 1:
    fail("release must contain exactly one magicrampage/INSTALLATION.md")
canonical_nxextract_files = {
    "magicrampage/nxextract/nxextract.py":
        ("nxextract", "0644", engine_sha256),
    "magicrampage/nxextract/run-extractor.sh":
        ("nxextract-runner", "0644", runner_sha256),
    "magicrampage/nxextract/nxextract-runtime-env.sh":
        ("nxextract-runtime-env", "0644", runtime_env_sha256),
    "magicrampage/nxextract/nxextract-ui":
        ("nxextract-ui-linux", "0755", ui_sha256),
}
for target, (kind, mode, sha256) in canonical_nxextract_files.items():
    entries = [item for item in release_files if item.get("target") == target]
    if len(entries) != 1:
        fail("release must contain exactly one canonical NXExtract file: " + target)
    if (
        entries[0].get("kind") != kind
        or entries[0].get("mode") != mode
        or entries[0].get("sha256") != sha256
    ):
        fail("NXExtract release identity drifted: " + target)
release_nxextract = release.get("nxextract", {})
if (
    release_nxextract.get("version") != "1.2.12"
    or release_nxextract.get("minimum_version") != "1.2.9"
    or release_nxextract.get("sha256") != engine_sha256
    or release_nxextract.get("runner_sha256") != runner_sha256
    or release_nxextract.get("runtime_env_sha256") != runtime_env_sha256
    or release_nxextract.get("ui_path") != "magicrampage/nxextract/nxextract-ui"
    or release_nxextract.get("ui_sha256") != ui_sha256
):
    fail("NXExtract manifest contract drifted")
if any(str(target).lower().endswith((".apk", ".obb", ".dex")) for target in release_targets):
    fail("release allowlist contains proprietary Android data")

print("magicrampage installation gate: PASS")
