"""Read-only plan for the original rig -> native writer -> FF -> independent read.

No subprocess, dynamic provider import, compiler, lease, stock scan or writes.
Commands are review data for a future coordinator-owned executor, not launched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).absolute().parent))
from prepare_skin_writer import geometry_header, source_report, OWN_FILES
from read_rig_chain import MODELS, PROFILES, load_inputs
from verify_clip_rig import read_bounded

ZONE = "sdk_original_rig_probe"
MATERIAL = "mopw/character_park_clown_zombie_shoes"
CLIP = "paris_original_probe_bend"
PROVIDERS = {
    "ops/Base-Client.Core.ps1": "e504a87334fae8f294458c72d7980c3e9b00d3c6549b969d1dfb41f26ca70605",
    "ops/model-lab/ModelFF.Core.ps1": "5ccf97178816706e47e263f4fec2c2e5a74277827e58841e666e58cb30dcd278",
    "ops/hud-lab/HudFileIdentity.cs": "61255ad8bbb6b4e2437291d3083811a56c1217ab68484bb1f22a4d5148616dbd",
    "ops/Resource-Scheduler.Core.ps1": "0d0ebef0f434c4e1ecc2614a4061f7e0685988adefcae596ff5a7891b1f3e25b",
    "ops/Resource-Memory.ps1": "6a708d2e7fa9803628bfbf5c670068d63d22a2d2cfc157994afa82d56ac9c241",
    "ops/native/ResourceMemory.cs": "b159804d12ca504cd592f4cdee191a9b68353e9e0117f9045a28a522b25692e9",
    "ops/Resource-RecorderOwnedProcess.Core.ps1": "23d6f589a6f973f6d9c56a2ff3dcb66c4df6a0aa9fe0a7125048dd9061f93c54",
    "sdk/modding/BeaconFF.Core.ps1": "b80047875a39731ea54838459fb71e0dca580c5e42284bd2749dc4b39c3a08a8",
    "sdk/modding/beacon_tool_phase.py": "a2ab493cf551a43eea3797e5e8437e41aa8f0246d770838956d8984b68c4701d",
}
CANDIDATE_SHA = "e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04"
JOB_SHA = "f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def load_json(path, expected=None):
    payload = read_bounded(path, 1024 * 1024)
    if expected is not None:
        require(re.fullmatch("[a-fA-F0-9]{64}", expected) is not None and sha(payload) == expected.lower(), "plan/receipt hash differs")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate plan/receipt key")
            result[key] = value
        return result
    return json.loads(payload, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def pinned(path, expected, cap=2 * 1024 * 1024):
    require(isinstance(expected, str) and re.fullmatch("[a-fA-F0-9]{64}", expected) is not None, "explicit SHA256 required")
    require(sha(read_bounded(Path(path), cap)) == expected.lower(), "pinned file differs: " + str(path))


def fresh_root(path, runtime):
    require(path.is_absolute() and runtime.is_absolute() and path != runtime and path.is_relative_to(runtime), "fresh child of this worktree runtime required")
    require(".." not in path.parts and not path.exists(), "fresh canonical run directory required")
    for parent in (path, *path.parents):
        require(not parent.is_symlink() and not parent.is_junction(), "reparse run ancestry refused")


def expected_inventory():
    return (["material,," + MATERIAL] +
            ["xmodelsurfs," + MODELS[h] + "_lod0" for h in PROFILES] +
            ["xmodel," + MODELS[h] for h in PROFILES] +
            ["xanim," + CLIP, "rawfile," + ZONE])


def inventory(log):
    require(len(log.encode("utf-8")) <= 2 * 1024 * 1024, "bounded inventory log required")
    require('Loading zone "' + ZONE + '"' in log and
            not re.search(r"could not be found|Could not find referenced|\[ ERROR \]|\[ FATAL \]", log, re.I), "rig inventory absent or unresolved")
    rows = []
    for line in log.splitlines():
        if "Loading asset " not in line:
            continue
        match = re.fullmatch(r'Loading asset "([^"\r\n]+)" of type ([a-z0-9]+)\.', line)
        require(match is not None, "malformed rig inventory row")
        rows.append(match[2] + "," + match[1])
    require(len(rows) == 7 and len(set(rows)) == 7 and set(rows) == set(expected_inventory()), "exact seven-asset offline rig inventory required")
    return rows


def check_base(base):
    require(base.get("Schema") == "iw7.animation-ff-plan/2" and base.get("Zone") == "sdk_animation_probe", "reviewed animation FF base plan required")
    require(base.get("Ready") is False and base.get("FFBuilt") is False, "base must remain a plan")
    require(set(base.get("Bindings", {})) == set(PROVIDERS), "exact nine existing providers required")
    for name, expected in PROVIDERS.items():
        require(base["Bindings"][name]["SHA256"].lower() == expected, "provider pin changed; coordinator review required: " + name)
    require(base["Candidate"]["SHA256"].lower() == CANDIDATE_SHA and base["JobSourceSHA256"].lower() == JOB_SHA, "existing full candidate and job implementation required")
    require(base["PhysicalBytes"] == 8 * 1024**3 and base["CommitBytes"] == 11 * 1024**3, "do not lower admitted FF estimates")
    require(len(base["StockInputs"]) == 72 and base["StagingCopyBytes"] == 77 and base["StockContentAndIdentityRecheckPending"] is True, "existing 72-entry stock binding with pending live proof required")
    relatives = [row["Relative"].lower() for row in base["StockInputs"]]
    require(len(set(relatives)) == 72, "duplicate stock destinations")
    copies = [row for row in base["StockInputs"] if row["Mode"] == "Copy"]
    require(len(copies) == 1 and copies[0]["Relative"] == "main/fileSysCheck.cfg" and copies[0]["Bytes"] == 77 and
            sum(row["Mode"] == "HardLink" for row in base["StockInputs"]) == 71, "71 hardlinks and one 77-byte copy required")


def compose(base, run, inputs, prepared, source, compiler, sdk, rig):
    check_base(base)
    native, work, retained = run / "native", run / "work", run / "roundtrip"
    writer = run / "build/two-bone-writer.exe"
    python, clip = base["PythonExe"], base["NativeInput"]
    reader = str(rig / "read_rig_chain.py")
    model_read = [python, "-I", "-B", reader, "--inputs", str(inputs), "--native-root", str(native), "--native-xab", clip]
    vc = Path(compiler["Compiler"]).parents[3]
    includes = [vc / "include"] + [sdk / "Include" / compiler["WindowsSdk"] / sub for sub in ("ucrt", "shared", "um", "winrt")]
    libraries = [vc / "lib/x64"] + [sdk / "Lib" / compiler["WindowsSdk"] / sub / "x64" for sub in ("ucrt", "um")]
    phases = [{"id": "compile", "group": "native", "depends_on": [], "command": [compiler["Compiler"],
               "/nologo", "/std:c++20", "/EHsc", "/MD", "/W4", "/WX", "/bigobj", "/X", "/D_CRT_SECURE_NO_WARNINGS",
               "/I" + str(source / "src/zonetool"), "/I" + str(prepared),
               str(prepared / "writer_skin_two_bone.cpp"), "/Fo" + str(run / "build/writer.obj"),
               "/Fe" + str(writer), "/Fd" + str(run / "build/writer.pdb"), *["/I" + str(p) for p in includes],
               "/link", "/INCREMENTAL:NO", *["/LIBPATH:" + str(p) for p in libraries], "kernel32.lib", "user32.lib"],
               "requires": ["reviewed native runner with frozen compiler/SDK environment", "original-handle job ownership", "complete reservation", "source guards"]}]
    for i, h in enumerate(PROFILES):
        phases.append({"id": "emit-" + h, "group": "native", "depends_on": ["compile" if i == 0 else "emit-first"],
                       "command": [str(writer), str(native / h), h], "requires": ["pin newly produced writer before execution", "fresh output", "same reviewed native owner"]})
    phases.append({"id": "read-native", "group": "native", "depends_on": ["emit-second"], "command": model_read,
                   "requires": ["actual native outputs and exact successful emission receipts", "complete independent model and CPU read"]})
    for phase, verb, previous in (("build", "-buildzone", "read-native"), ("verify", "-verifyzone", "build"), ("dump", "-dumpzone", "verify")):
        phases.append({"id": phase, "group": "ff", "depends_on": [previous],
                       "command": [str(work / "zonetool.exe"), "-headless", "-unbuffered-io", "-strict-content-sources", verb, ZONE],
                       "requires": ["fresh separate FF reservation", "live stock guards and content/identity proof", "existing bounded phase adapter and outer job"]})
    phases.append({"id": "read-ff", "group": "ff", "depends_on": ["dump"], "command": model_read +
                   ["--redump-root", str(retained), "--redump-xab", str(retained / "xanim" / (CLIP + ".xab"))],
                   "requires": ["bounded retention of all five actual redumps", "exact seven-row inventory", "real FF build/verify/dump exit and ownership receipts"]})
    for phase in phases:
        phase["working_directory"] = str(work if phase["group"] == "ff" else run / "build")
    phases[4]["requires"].append("native group closed and its lease released before FF admission")
    staged = [{"relative": "zonetool.exe", "source": base["Candidate"].get("Path"),
               "mode": "HardLink", "sha256": CANDIDATE_SHA}]
    for h, name in MODELS.items():
        for folder, filename in (("xmodel", name + ".xmb"), ("xsurface", name + "_lod0.xsb")):
            staged.append({"relative": folder + "/" + filename, "source": str(native / h / folder / filename), "mode": "HardLink", "requires_future_hash_and_identity": True})
    csv = "material,," + MATERIAL + "\n" + "".join("xmodel," + name + "\n" for name in MODELS.values()) + "xanim," + CLIP + "\n"
    staged += [{"relative": "xanim/" + CLIP + ".xab", "source": clip, "mode": "HardLink"},
               {"relative": "zone_source/" + ZONE + ".csv", "source": str(run / "profile/zone_source" / (ZONE + ".csv")),
                "mode": "CreateNew", "sha256": sha(csv.encode("ascii"))}]
    redumps = [{"source": str(work / "dump" / ZONE / folder / filename), "retained": str(retained / folder / filename), "max_bytes": 65536}
               for name in MODELS.values() for folder, filename in (("xmodel", name + ".xmb"), ("xsurface", name + "_lod0.xsb"))]
    redumps.append({"source": str(work / "dump" / ZONE / "xanim" / (CLIP + ".xab")),
                    "retained": str(retained / "xanim" / (CLIP + ".xab")), "max_bytes": 65536})
    return {"schema": "iw7.original-rig-chain-plan/1", "mode": "plan-only", "zone": ZONE,
            "run_root": str(run), "phases": phases, "staged_profile_inputs": staged,
            "zone_csv": csv, "total_ff_staged_entries": 79, "retain_redumps_before_restore": redumps,
            "expected_inventory": expected_inventory(), "live_stock_recheck_pending": True,
            "stock_binding": {"inputs": base["StockInputs"], "copy_bytes": 77, "source_metadata_mutation_allowed": False},
            "provider_bindings": base["Bindings"], "job_source": {"path": base["JobSource"], "sha256": JOB_SHA},
            "candidate": base["Candidate"], "compiler_receipt": compiler,
            "compiler_environment_recipe": {"remove": ["CL", "_CL_", "PYTHONPATH", "PYTHONHOME"], "vc_root": str(vc),
                "windows_sdk_root": str(sdk), "windows_sdk_version": compiler["WindowsSdk"], "transitive_freeze_pending": True,
                "include_paths": [str(p) for p in includes], "library_paths": [str(p) for p in libraries],
                "freeze_roots": [str(Path(compiler["Compiler"]).parent), str(source / "src/zonetool"), str(prepared), *[str(p) for p in includes], *[str(p) for p in libraries]]},
            "limits": {"native_proposed_physical_bytes": 4 * 1024**3, "native_proposed_commit_bytes": 6 * 1024**3,
                "ff_physical_bytes": base["PhysicalBytes"], "ff_commit_bytes": base["CommitBytes"],
                "native_artifact_stop_bytes": 32 * 1024**2, "ff_output_stop_bytes": 64 * 1024**2,
                "ff_artifact_max_bytes": 1024**2, "each_redump_max_bytes": 65536, "stream_max_bytes": 2 * 1024**2,
                "native_compile_seconds": 120, "native_emit_seconds": 30,
                "ff_phase_seconds": 240, "reader_seconds": 30, "ff_group_seconds": 900},
            "executor_integration_pending": False, "executor_native_validation_pending": True, "native_and_ff_groups_sequential": True,
            "acceptance_requires": ["all exact owned jobs closed before restoration", "all source hashes and IDs preserved", "stock restored before lease release", "final hidden-file byte accounting converged", "bind data readback hashes to actual phase receipts"],
            "material_binding_verified": False, "engine_animation_conventions_verified": False,
            "runtime_render_verified": False, "compiled": False, "ff_built": False, "ready": False}


def inspect(args):
    rig = Path(__file__).absolute().parent
    fresh_root(args.run_root, rig.parents[3] / "runtime")
    base = load_json(args.ff_base_plan, args.ff_base_sha256)
    check_base(base)
    for row in base["Bindings"].values():
        pinned(row["Path"], row["SHA256"])
    for path, digest in base["SourceHashes"].items():
        pinned(path, digest)
    pinned(base["JobSource"], JOB_SHA)
    pinned(base["Candidate"]["Path"], CANDIDATE_SHA, 32 * 1024**2)
    pinned(base["PythonExe"], base["PythonSHA256"], 32 * 1024**2)
    files, manifest = load_inputs(args.inputs)
    receipt = load_json(args.prepared / "skin-writer-source.json")
    require(receipt["source_pin"] == manifest["source_pin"] == "fab935826c898806855376662a8a03317b3ad8f1", "pinned real IW7 source required")
    require(receipt["input_manifest_sha256"] == sha(read_bounded(args.inputs / "fixture-input.json", 16384)), "prepared input manifest differs")
    require(set(p.name for p in args.prepared.iterdir()) == set(OWN_FILES) | {"skin_geometry.hpp", "skin-writer-source.json"}, "exact prepared writer source inventory")
    expected_sources = {name: read_bounded(rig / name, 65536) for name in OWN_FILES}
    expected_sources["skin_geometry.hpp"] = geometry_header(files, manifest)
    for name, payload in expected_sources.items():
        require(read_bounded(args.prepared / name, 65536) == payload and receipt["prepared_hashes"][name] == sha(payload), "prepared source/header differs")
    expected_interfaces = load_json(rig / "validation-2026-10-12.json")["interface_hashes"]
    require(receipt["interface_hashes"] == expected_interfaces, "all eleven reviewed interface bindings required")
    originals = dict(files)
    originals["fixture-input.json"] = read_bounded(args.inputs / "fixture-input.json", 16384)
    expected_receipt = source_report(originals, manifest, expected_interfaces, expected_sources)
    require(json.dumps(receipt, sort_keys=True) == json.dumps(expected_receipt, sort_keys=True), "exact typed source preparation receipt required")
    for name, digest in expected_interfaces.items():
        relative = "src/zonetool/game/shared.cpp" if name == "../game/shared.cpp" else "src/zonetool/zonetool/" + name
        pinned(args.source / relative, digest)
    compiler_receipt = load_json(args.compiler_receipt, args.compiler_receipt_sha256)
    require(compiler_receipt["Status"] == "NativeSerializerAndReadbackPassed", "existing successful compiler observation required")
    compiler = {k: compiler_receipt[k] for k in ("Compiler", "CompilerSHA256", "VCTools", "WindowsSdk")}
    pinned(compiler["Compiler"], compiler["CompilerSHA256"], 32 * 1024**2)
    require(args.sdk_root.is_absolute() and (args.sdk_root / "Include" / compiler["WindowsSdk"] / "um/Windows.h").is_file(), "existing Windows SDK only")
    result = compose(base, args.run_root, args.inputs, args.prepared, args.source, compiler, args.sdk_root, rig)
    result["plan_source_sha256"] = sha(read_bounded(Path(__file__).absolute(), 65536))
    result["chain_reader_sha256"] = sha(read_bounded(rig / "read_rig_chain.py", 65536))
    dependencies = [rig / name for name in ("plan_rig_chain.py", "read_rig_chain.py", "read_skin_native.py", "read_skin_fixture.py",
                    "skin_oracle.py", "verify_clip_rig.py", "prepare_skin_writer.py", "validation-2026-10-12.json")]
    dependencies.append(rig.parent / "read_probe.py")
    result["local_source_hashes_for_future_guards"] = {str(p): sha(read_bounded(p, 65536)) for p in dependencies}
    result["base_plan_sha256"] = args.ff_base_sha256.lower()
    result["prepared_receipt_sha256"] = sha(read_bounded(args.prepared / "skin-writer-source.json", 16384))
    result["physical_provider_and_input_hashes_rechecked"] = True
    result["stock_files_read_or_copied"] = False
    # The executor does not trust commands from JSON. It asks this source-only
    # planner to reproduce the entire plan byte-semantically before every Run.
    path_keys = ("ff_base_plan", "inputs", "prepared", "source", "compiler_receipt", "sdk_root", "run_root")
    result["revalidation"] = {key: str(getattr(args, key)) for key in path_keys}
    result["revalidation"].update(ff_base_sha256=args.ff_base_sha256.lower(), compiler_receipt_sha256=args.compiler_receipt_sha256.lower())
    result["python"] = {"path": base["PythonExe"], "sha256": base["PythonSHA256"]}
    frozen = dict(base["SourceHashes"])
    frozen[str(args.ff_base_plan)] = args.ff_base_sha256.lower()
    frozen[str(args.compiler_receipt)] = args.compiler_receipt_sha256.lower()
    candidate_root = Path(base["Candidate"]["Path"]).parent.parent
    artifact_path = candidate_root / "build-artifact.local.json"
    artifact = load_json(artifact_path, base["Candidate"]["ArtifactSHA256"])
    frozen[str(artifact_path)] = base["Candidate"]["ArtifactSHA256"]
    for filename, digest in (("preparation.local.json", artifact["preparation_sha256"]),
                             ("result.local.json", artifact["result_sha256"])):
        pinned(candidate_root / filename, digest)
        frozen[str(candidate_root / filename)] = digest
    command_evidence = Path(artifact["commands_tlog"]["path"])
    require(command_evidence.is_absolute() and command_evidence.is_relative_to(candidate_root), "candidate-owned compiler evidence required")
    pinned(command_evidence, artifact["commands_tlog"]["sha256"], 16 * 1024**2)
    frozen[str(command_evidence)] = artifact["commands_tlog"]["sha256"]
    for name in (*files, "fixture-input.json"):
        frozen[str(args.inputs / name)] = sha(read_bounded(args.inputs / name, 16384))
    for name, payload in expected_sources.items():
        frozen[str(args.prepared / name)] = sha(payload)
    frozen[str(args.prepared / "skin-writer-source.json")] = result["prepared_receipt_sha256"]
    for name, digest in expected_interfaces.items():
        relative = "src/zonetool/game/shared.cpp" if name == "../game/shared.cpp" else "src/zonetool/zonetool/" + name
        frozen[str(args.source / relative)] = digest
    for path in rig.iterdir():
        if path.is_file() and path.suffix in (".ps1", ".py", ".cs", ".hpp", ".cpp"):
            frozen[str(path)] = sha(read_bounded(path, 131072))
    result["execution_input_hashes"] = frozen
    observation = load_json(Path(base["StockBindingReceipt"]), base["StockBindingReceiptSHA256"])
    result["stock_receipts"] = {"binding": base["StockBindingReceipt"], "binding_sha256": base["StockBindingReceiptSHA256"],
        "baseline": observation["BaselineReceipt"], "baseline_sha256": observation["BaselineReceiptSHA256"],
        "reviewed": observation["ReviewedStockManifest"], "reviewed_sha256": observation["ReviewedStockManifestSHA256"], "root": observation["StockRoot"]}
    require(not args.run_root.exists(), "planning must not create run root")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ff-base-plan", "inputs", "prepared", "source", "compiler-receipt", "sdk-root", "run-root"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--ff-base-sha256")
    parser.add_argument("--compiler-receipt-sha256")
    parser.add_argument("--check-plan", type=Path)
    parser.add_argument("--check-plan-sha256")
    args = parser.parse_args()
    try:
        if args.check_plan:
            require(args.check_plan_sha256 is not None, "checked plan hash required")
            supplied = load_json(args.check_plan, args.check_plan_sha256)
            values = supplied["revalidation"]
            expected_keys = {"ff_base_plan", "inputs", "prepared", "source", "compiler_receipt", "sdk_root", "run_root", "ff_base_sha256", "compiler_receipt_sha256"}
            require(set(values) == expected_keys and all(isinstance(v, str) and v for v in values.values()), "exact plan revalidation inputs required")
            bound = SimpleNamespace(**{k: v if k.endswith("sha256") else Path(v) for k, v in values.items()})
            result = inspect(bound)
            require(json.dumps(supplied, sort_keys=True) == json.dumps(result, sort_keys=True), "plan differs from current exact recipe; regeneration/review required")
        else:
            require(all(getattr(args, k) is not None for k in ("ff_base_plan", "inputs", "prepared", "source", "compiler_receipt", "sdk_root", "run_root", "ff_base_sha256", "compiler_receipt_sha256")), "all plan arguments required")
            result = inspect(args)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({"status": "invalid-rig-chain-plan", "error": str(error)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
