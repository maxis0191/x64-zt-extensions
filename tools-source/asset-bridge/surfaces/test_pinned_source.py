"""Optional integration check against existing pinned sources; never compiles."""
import argparse
import json
from pathlib import Path
import subprocess
import struct
import sys
import tempfile

from inspect_content import Inputs, require, verify_contract
from prepare_reader_patch import BASE, FLAG, prepare, verify_prepared
import test_surfaces


def run(source, native_source=None):
    contract = verify_contract(source)
    checks = [str(len(contract["zonetool"]["files"])) + " pinned ZoneTool interfaces match"]
    if native_source:
        ui = contract["native_ui"]
        native = Inputs(native_source)
        native.read(ui["path"])
        require(native.files[ui["path"]]["sha256"] == ui["sha256"], "native UI source contract differs")
        checks.append("native HKS loader source hash matches; no execution claim")
    with tempfile.TemporaryDirectory(prefix="iw7-surfaces-patch-test-") as directory:
        output = Path(directory) / "prepared"
        manifest = prepare(source, output)
        require(verify_prepared(source, output) == manifest, "patch recomputation differs")
        require((output / "strict-content-sources.patch").read_bytes() ==
                Path(__file__).with_name("strict-content-sources.patch").read_bytes(), "tracked diff drift")
        checks.append("prepared patch recomputes exactly and equals tracked diff")
        material = (output / (BASE + "material.cpp")).read_text()
        require("std::string name(asset->constantTable[i].name, sizeof(asset->constantTable[i].name));" in material and
                "std::string name = asset->constantTable[i].name;" not in material and
                "name.resize(12);" in material and 'cent##entry["name"] = name.data();' in material,
                "constant dump must bound its read while retaining JSON name text semantics")
        record_tail = b"reflectionRa" + struct.pack("<4f", 1.1, 1.1, 1.1, 1.1)
        require(len(record_tail) == 28 and b"\x00" not in record_tail and record_tail[:12] == b"reflectionRa",
                "full-width name witness must have no later float NUL to hide overread")
        checks.append("real dump macro bounded to12; name12/four-float1.1 witness contains no accidental terminator")
        before = (source / (BASE + "gfximage.cpp")).read_text()
        after = (output / (BASE + "gfximage.cpp")).read_text()
        gate = 'if ((' + FLAG + ' || filesystem::get_fastfile().starts_with("paris_enemy_")) &&'
        require(gate in after, "strict mode must reject cached placeholder before init returns")
        start = "asset->imageFormat == DXGI_FORMAT_R8G8B8A8_UNORM && asset->category == IMG_CATEGORY_AUTO_GENERATED"
        end = 'throw std::runtime_error("IW7 enemy image source is the generated missing-image placeholder: " + name);'
        witness = before[before.index(start):before.index(end) + len(end)]
        require(witness in after and after.index(gate) < after.index(witness), "exact placeholder predicate must stay unchanged")
        checks.append("strict cached red placeholder gate added; full existing byte/shape/category predicate retained")
        flag_source = (source / "src/common/utils/flags.cpp").read_text()
        require("wide_flag[0] == L'-'" in flag_source and "wide_flag.erase(wide_flag.begin());" in flag_source and
                "string::to_lower(name) == string::to_lower(flag)" in flag_source,
                "command-line flag activation source changed")
        checks.append("existing has_flag parser recognizes single-dash named opt-in by source contract")
        subprocess.run(["git", "-C", str(source), "apply", "--check", str(output / "strict-content-sources.patch")],
                       check=True, capture_output=True, text=True)
        checks.append("git apply --check passes against actual source; no patch applied")
        fixture = test_surfaces.SurfacesTests()
        fixture.setUp()
        try:
            fixture.material()
            fixture.put("references.csv", b"techset,recipient_tech\n")
            command = [sys.executable, "-B", str(Path(__file__).with_name("inspect_content.py")),
                       "--root", str(fixture.root), "--zt-source", str(source),
                       "--zone", "community_beacon", "--material", "probe", "--references", "references.csv"]
            original = subprocess.run(command, capture_output=True, text=True, check=False)
            require(original.returncode == 1 and "early_db_material_lookup" in original.stdout,
                    "actual CLI must reject old reader early DB lookup")
            planned = subprocess.run(command + ["--reader-patch", str(output)], capture_output=True, text=True, check=False)
            report = json.loads(planned.stdout)
            require(planned.returncode == 2 and report["ready"] is False and report["errors"] == 0 and
                    any(x["code"] == "strict_reader_build_required" for x in report["findings"]),
                    "verified patch still needs build, external resolution and runtime")
            checks.append("CLI old-reader rejection and prepared-reader incomplete status proven on synthetic material")
        finally:
            fixture.doCleanups()
        try:
            prepare(source, output)
        except ValueError:
            checks.append("existing patch output refused")
        else:
            raise AssertionError("existing output overwritten")
        patched = output / "src/zonetool/zonetool/iw7/assets/material.cpp"
        patched.write_bytes(patched.read_bytes() + b"\n// changed\n")
        try:
            verify_prepared(source, output)
        except ValueError:
            checks.append("tampered prepared source refused without trusting manifest")
        else:
            raise AssertionError("tampered source accepted")
    verify_contract(source)
    checks.append("shared source interfaces unchanged after all checks")
    return {"checks": checks, "passed": len(checks), "native_compiled": False, "runtime_verified": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zt-source", type=Path, required=True)
    parser.add_argument("--native-source", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.zt_source, args.native_source), indent=2))
