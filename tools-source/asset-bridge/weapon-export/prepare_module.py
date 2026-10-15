"""Stage inactive bounded IW7 player/PAP export support; no CLI, build or run."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_PIN = "fab935826c898806855376662a8a03317b3ad8f1"
BASE_LF_SHA256 = "5abd5c9b0c4a71e665c052cd51db0003c089fdb40f88380baaa4b59a2f8c6a78"
NATIVE_PATH = "src/zonetool/zonetool/iw7/zonetool.cpp"
ANCHOR = "\tvoid load_enemy_source_zones(const std::string& donor_zone)\n\t{"
FUNCTION = "dump_iw7_player_weapon_templates"
CAP = 2 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_source(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "Regular source text required")
    with path.open("rb") as stream:
        raw = stream.read(CAP + 1)
    require(len(raw) <= CAP, "Source cap exceeded before decode/hash")
    return raw.decode("utf-8-sig").replace("\r\n", "\n")


def wire_module(text, expected_sha256=BASE_LF_SHA256):
    require(hashlib.sha256(text.encode("utf-8")).hexdigest() == expected_sha256,
            "Pinned IW7 source changed")
    require(text.count("namespace zonetool::iw7\n{") == 1 and text.count(ANCHOR) == 1 and
            FUNCTION not in text, "Exactly one fresh pinned IW7 insertion site required")
    module = read_source(HERE / "native_player_templates.inc")
    name_header = read_source(HERE / "native_bounded_name.hpp").removeprefix("#pragma once\n")
    primary_header = read_source(HERE / "native_primary_guard.hpp").removeprefix("#pragma once\n")
    addition = "\n".join("\t" + line if line else "" for line in module.splitlines()) + "\n\n"
    result = text.replace(ANCHOR, addition + ANCHOR, 1)
    # Standard includes stay global, before the existing native namespace.
    result = result.replace("namespace zonetool::iw7\n{",
        "#include <array>\n#include <cmath>\n#include <fstream>\n#include <sstream>\n" + name_header + "\n" + primary_header + "\n"
        "namespace zonetool::iw7\n{", 1)
    require(len(result.encode("utf-8")) <= CAP, "Staged source cap exceeded")
    return result, module


def wire_cli(text):
    """Apply support first on pristine source, then the finite pre-loop callsite."""
    result, module = wire_module(text)
    anchor = '\t\tauto args = get_command_line_arguments();\n'
    require(result.count(anchor) == 1, 'One exact IW7 argument entry required')
    header = read_source(HERE/'native_player_cli.hpp').removeprefix('#pragma once\n')
    entry = read_source(HERE/'native_player_cli.inc')
    result = result.replace('namespace zonetool::iw7\n{', header+'\nnamespace zonetool::iw7\n{', 1)
    addition = '\n'.join('\t\t'+line if line else '' for line in entry.splitlines())+'\n'
    result = result.replace(anchor, anchor+addition, 1)
    require(len(result.encode()) <= CAP, 'Wired IW7 source cap exceeded')
    return result, module


def stage(source_root, output, *, player_cli=False):
    require(type(player_cli) is bool, 'Explicit source CLI boolean required')
    output = Path(output)
    require(output.is_absolute() and not output.exists() and
            not any(p.is_symlink() or p.is_junction() for p in (output, *output.parents)),
            "Fresh ordinary absolute output required")
    original = read_source(Path(source_root) / NATIVE_PATH)
    patched, module = wire_cli(original) if player_cli else wire_module(original)
    target = output / NATIVE_PATH
    report = {"schema": "iw7.player-template-export-support/1", "native_source_pin": SOURCE_PIN,
        "base_lf_sha256": BASE_LF_SHA256,
        "module_sha256": hashlib.sha256(module.encode("utf-8")).hexdigest(),
        "bounded_name_sha256": hashlib.sha256(read_source(HERE / "native_bounded_name.hpp").encode("utf-8")).hexdigest(),
        "primary_guard_sha256": hashlib.sha256(read_source(HERE / "native_primary_guard.hpp").encode("utf-8")).hexdigest(),
        "staged_lf_sha256": hashlib.sha256(patched.encode("utf-8")).hexdigest(),
        "support_function": FUNCTION, "allowlisted_weapon": "iw7_shredder_zm",
        "allowlisted_pap": "shredderpap1", "cli_wired": player_cli, "compiled": False,
        "native_export_executed": False, "full_templates_observed": False, "ready": False}
    if player_cli:
        names = ('prepare_module.py','native_player_templates.inc','native_bounded_name.hpp',
                 'native_player_cli.hpp','native_player_cli.inc','test_bounded_name.cpp','test_player_cli.cpp',
                 'native_primary_guard.hpp','test_primary_guard.cpp')
        report['build_extension'] = dict(translation_unit=NATIVE_PATH, replace_retained_translation_unit=True,
            source_only=True, requires_fresh_native_compile=True, argv_count_including_executable=6,
            option='-iw7-player-weapon-templates', other_overlays_preserved=False,
            ordering='pristine pinned IW7 -> reviewed support127 -> exact CLI -> separately reviewed compatible overlays',
            inputs={name: hashlib.sha256(read_source(HERE/name).encode()).hexdigest() for name in names},
            name_fixture_checks_authored=8, argv_fixture_checks_authored=10, primary_fixture_checks_authored=36, cpp_executed=False, ready=False)
    target.parent.mkdir(parents=True, exist_ok=False)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(patched)
    with (output / "module-source.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--player-template-cli", action='store_true')
    args = parser.parse_args()
    print(json.dumps(stage(args.native_source_root, args.output, player_cli=args.player_template_cli)))
