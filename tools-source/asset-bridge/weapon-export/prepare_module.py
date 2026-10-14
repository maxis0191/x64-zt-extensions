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
    addition = "\n".join("\t" + line if line else "" for line in module.splitlines()) + "\n\n"
    result = text.replace(ANCHOR, addition + ANCHOR, 1)
    # Standard includes stay global, before the existing native namespace.
    result = result.replace("namespace zonetool::iw7\n{",
        "#include <array>\n#include <cmath>\n#include <fstream>\n#include <sstream>\n"
        "namespace zonetool::iw7\n{", 1)
    require(len(result.encode("utf-8")) <= CAP, "Staged source cap exceeded")
    return result, module


def stage(source_root, output):
    output = Path(output)
    require(output.is_absolute() and not output.exists() and
            not any(p.is_symlink() or p.is_junction() for p in (output, *output.parents)),
            "Fresh ordinary absolute output required")
    original = read_source(Path(source_root) / NATIVE_PATH)
    patched, module = wire_module(original)
    target = output / NATIVE_PATH
    report = {"schema": "iw7.player-template-export-support/1", "native_source_pin": SOURCE_PIN,
        "base_lf_sha256": BASE_LF_SHA256,
        "module_sha256": hashlib.sha256(module.encode("utf-8")).hexdigest(),
        "staged_lf_sha256": hashlib.sha256(patched.encode("utf-8")).hexdigest(),
        "support_function": FUNCTION, "allowlisted_weapon": "iw7_shredder_zm",
        "allowlisted_pap": "shredderpap1", "cli_wired": False, "compiled": False,
        "native_export_executed": False, "full_templates_observed": False, "ready": False}
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
    args = parser.parse_args()
    print(json.dumps(stage(args.native_source_root, args.output)))
