"""Finite CPP39 registration-owned header source plan data adapter; no process, alias or binary reads."""
import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path, PureWindowsPath
from prepare_material_parts_probe import EXPORT_FIELDS, REFERENCE_PIN, key, require, read_text_pin
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"t7-iw7"))
from prepare_image_provenance_probe import read_snapshot, apply_preservation

CANDIDATE = (22024704, "eeeca36f26ff2c76b98a608fe17a6b47259401b1cd800f73fe886bd099ac6dbc")
BUILD = (396872, "dd85b86f508439ee45ff9a23543f8b7e16e852b8dab39bf2215ebb1c53f6f4e4")
RECEIPT = (46047, "24380749ad1407e71587c57cfe35aea770cfa75510247749a8c165f7cdb8c0b1")
HANDOFF = (9556, "066aa9e359a6b2232e9920b82404f3652c09d9b3f97a75f1588ed38becf62ebc")
CONTROLLERS = (
    "tools-source/asset-bridge/t7-bridge/Run-T7Catalogue.ps1",
    "tools-source/asset-bridge/t7-bridge/T7Catalogue.Profile.ps1",
    "tools-source/asset-bridge/t7-bridge/T7Prepatch.Profile.ps1",
    "tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1",
    "ops/Resource-Scheduler.Core.ps1", "ops/Resource-Memory.ps1",
    "ops/Resource-RecorderOwnedProcess.Core.ps1", "ops/native/ResourceMemory.cs",
    "ops/hud-lab/HudFileIdentity.cs",
    "tools-source/asset-bridge/t7-bridge/T7ImageProvenance.Profile.ps1",
    "tools-source/asset-bridge/t7-bridge/T7RegistrationImage.Profile.ps1",
)
FIXTURE = (38, "3aa779ecccb3f318c1a61b34b0fc1b267077231c7ecaa9646c34ea999e483f3f")


def read_source_text(path, expected=None):
    if expected != FIXTURE:
        return read_text_pin(path, expected)
    # The sole log input is the exact 38-byte closed CPP fixture stdout.
    path = Path(path)
    require(path.is_absolute() and path == path.resolve() and path.name == "stdout.log",
            "Exact fixture text path required")
    for parent in (path, *path.parents):
        require(not parent.is_symlink() and not parent.is_junction(), "Reparse fixture text refused")
    require(path.stat().st_size == FIXTURE[0], "Exact fixture text length required before open")
    with path.open("rb") as stream:
        raw = stream.read(FIXTURE[0]+1)
    require((len(raw), hashlib.sha256(raw).hexdigest()) == FIXTURE, "Exact closed fixture text required")
    raw.decode("utf-8")
    return dict(Path=str(path), Bytes=len(raw), SHA256=FIXTURE[1]), raw


def derive(reference, controllers, build, receipt, marker, candidate_metadata, run):
    require(reference["Operation"] == "ResidentExportV1" and
            reference["CandidateProfile"] == "t7-catalog-message-publication" and
            reference["SelectedStreamedRenderOnlyV2"]["Schema"] == "iw7.t7-selected-streamed-render-only-plan/2",
            "Exact retained E5 metadata family required")
    require(len(reference["Bootstraps"]) == 23 and len(reference["InputMetadata"]) == 29,
            "Qualified E5 collection required")
    require((build["pin"]["Bytes"], build["pin"]["SHA256"]) == BUILD and
            (receipt["pin"]["Bytes"], receipt["pin"]["SHA256"]) == RECEIPT,
            "Exact closed CPP39 recipe and receipt required")
    require(candidate_metadata["Bytes"] == CANDIDATE[0] and
            receipt["data"]["Stages"][-1]["Name"] == "link", "Measured D candidate metadata required")
    linked = [p for p in receipt["data"]["Stages"][-1]["Artifacts"]
              if p["Path"] == candidate_metadata["Path"]]
    require(len(linked) == 1 and (linked[0]["Bytes"], linked[0]["SHA256"]) == CANDIDATE,
            "Candidate must be the original admitted D link artifact")
    result = copy.deepcopy(reference)
    for name in EXPORT_FIELDS:
        result.pop(name, None)
    result.update(Schema="iw7.t7-registration-image-plan/1", Operation="RegistrationImageMetadataV1",
        CandidateProfile="t7-registration-image-header-metadata-v1",
        Arguments=["-t7-iw7-image-registration-metadata-v1", "mp_freerun_04", "p7_fre_platform_cap_02", "0"],
        OutputKey="t7_iw7_registration_image_metadata_v1", ReportLimitBytes=65536, TraceStderrLimitBytes=16384,
        RunRoot=str(run), WorkingDirectory=str(run/"work"), StageRoot=str(run/"evidence"),
        Image=str(run/"work/t7-zonetool-candidate.exe"), CandidateSource=candidate_metadata["Path"],
        CandidateBytes=CANDIDATE[0], CandidateSHA256=CANDIDATE[1],
        BuildPlan=build["pin"]["Path"], ExpectedBuildPlanSHA256=BUILD[1],
        BuildReceipt=receipt["pin"]["Path"], ExpectedBuildReceiptSHA256=RECEIPT[1],
        Runner=controllers[0]["Path"],
        SelectedRegistrationImageHeaderV1=dict(Schema="iw7.t7-registration-image-cpp39/1", **marker))
    allowed = {key(reference[name]) for name in ("EngineSource", "SteamSource")}
    allowed.add(key(reference["Zone"]["Path"]))
    allowed.update(key(p["Path"]) for p in reference["Bootstraps"])
    result["InputMetadata"] = [copy.deepcopy(p) for p in reference["InputMetadata"] if key(p["Path"]) in allowed]
    result["InputMetadata"].insert(0, candidate_metadata)
    require(len(result["InputMetadata"]) == 27, "Only declared candidate/engine/Steam/zone/bootstrap metadata allowed")
    retained = {key(p["QualificationScript"]["Path"]) for p in reference["Bootstraps"]}
    retained.update(key(p["QualificationReceipt"]["Path"]) for p in reference["Bootstraps"])
    retained.update(key(reference["SharedQualification"][name]["Path"]) for name in ("Script", "Plan", "Receipt"))
    bindings = [copy.deepcopy(p) for p in reference["Bindings"] if not p["IsText"] or key(p["Path"]) in retained]
    old = [p for p in bindings if key(p["Path"]) == key(reference["CandidateSource"])]
    require(len(old) == 1, "One historical candidate binding required")
    old[0].update(Path=candidate_metadata["Path"], Bytes=CANDIDATE[0], SHA256=CANDIDATE[1])
    text = [build["pin"], receipt["pin"], *controllers, *marker.values()]
    text.extend(build["data"]["BuildProfile"][name] for name in
                ("Wiring", "PreparedMain", "PreparedCLI", "BaseBuildPlan", "BaseBuildReceipt", "LinkResponse", "RegistrationWiring", "RegistrationContract", "RegistrationCapture",
                 "RegistrationEntry", "RegistrationFixture", "RegistrationObserver", "RegistrationResponse"))
    dependencies = [p for p in receipt["data"]["Stages"][2]["Artifacts"]
                    if PureWindowsPath(p["Path"]).name == "dependencies.json"]
    require(len(dependencies) == 1, "One original main dependency text required")
    text.extend(dependencies)
    bindings.extend(dict(p, IsText=True) for p in text)
    require(len({key(p["Path"]) for p in bindings}) == len(bindings) == 96, "Exact unique registration binding set required")
    result["Bindings"] = bindings
    result["OutputLimitBytes"] = 16977344+21737352+235600+64*1024**2+CANDIDATE[0]+sum(p["Bytes"] for p in reference["Bootstraps"])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "reference", "handoff", "candidate-metadata", "preservation-metadata", "run-root", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(argv)
    source = args.source.resolve(strict=True)
    source_pin, source_raw = read_text_pin(source/"source-workspace.json")
    workspace = json.loads(source_raw)
    require(workspace.get("schema") == "iw7.source-workspace/1" and workspace.get("product") == "x64-zt-extensions" and
            workspace["revisions"]["x64-zt-extensions"] and len(workspace["files"]) > 0,
            "Composed receiver source required")
    reference_pin, raw = read_text_pin(args.reference, REFERENCE_PIN)
    reference = json.loads(raw)
    _, raw = read_text_pin(args.handoff, HANDOFF)
    handoff = json.loads(raw)
    require(handoff["ExtensionSourceCommit"] == "b38a5d9cacc39f1e150a7ad0de21000c6e2f52d4" and
            handoff["RegistrationCPPQualified"] is True and handoff["CandidateExecuted"] is False,
            "Closed unexecuted CPP39 handoff required")
    build_pin, raw = read_text_pin(handoff["Plan"]["Path"], BUILD)
    build = json.loads(raw)
    receipt_pin, raw = read_text_pin(handoff["Receipt"]["Path"], RECEIPT)
    receipt = json.loads(raw)
    metadata_pin, metadata = read_snapshot(args.candidate_metadata)  # Never stat/hash the candidate here.
    require(metadata["Path"] == handoff["LinkArtifactsRecordedUnderAdmission"][0]["Path"] and
            type(metadata["Bytes"]) is int and metadata["Bytes"] == CANDIDATE[0],
            "Admitted candidate stat metadata required")
    controllers = [read_text_pin(source/name)[0] for name in CONTROLLERS]
    source_rows = {row["path"]: row for row in workspace["files"]}
    for name, pin in zip(CONTROLLERS, controllers):
        row = source_rows.get(name, {})
        require((row.get("bytes"), row.get("sha256")) == (pin["Bytes"], pin["SHA256"]),
                "Receiver controller differs from its composed source manifest")
    preservation_pin, preservation = read_snapshot(args.preservation_metadata)
    marker = {"PreExit": handoff["Preexit"], "Closure": handoff["Closure"]}
    marker = dict(SourceManifest=handoff["PackageSourceManifest"], HostWitness=marker["PreExit"],
                  ClosureWitness=marker["Closure"], FixtureStdout=handoff["RegistrationFixture"]["Stdout"])
    run = args.run_root; output = args.output
    require(run.is_absolute() and run == run.resolve() and run.parent == source/"runtime" and
            re.fullmatch(r"t7-registration-image-[a-z][a-z0-9-]*", run.name) and not run.exists(),
            "Fresh receiver private runtime required")
    require(output.is_absolute() and output == output.resolve() and output.parent == source/"runtime" and
            re.fullmatch(r"registration-image-plan-[a-z][a-z0-9-]*", output.name) and not output.exists(),
            "Fresh receiver private control output required")
    for parent in (*run.parents, *output.parents):
        require(not parent.is_symlink() and not parent.is_junction(), "Reparse output parent refused")
    plan = derive(reference, controllers, dict(pin=build_pin, data=build),
                  dict(pin=receipt_pin, data=receipt), marker, metadata, run)
    apply_preservation(plan, preservation)
    for pin in plan["Bindings"]:
        if pin["IsText"]:
            read_source_text(pin["Path"], (pin["Bytes"], pin["SHA256"]))
    raw = (json.dumps(plan, indent=2)+"\n").encode()
    require(len(raw) <= 128*1024, "Existing plan limit exceeded")
    plan_path = output/"plan.local.json"; plan_hash = hashlib.sha256(raw).hexdigest()
    entry = source/"tools-source/asset-bridge/t7-bridge/Invoke-T7CatalogueHost.ps1"
    host_pins = [read_text_pin(path)[0] for path in (entry,
        source/"tools-source/asset-bridge/t7-bridge/T7CatalogueHost.Core.ps1",
        source/"tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1")]
    shells = [p for p in plan["Bindings"] if not p["IsText"] and PureWindowsPath(p["Path"]).name == "pwsh.exe"]
    require(len(shells) == 1, "One exact retained host binding required")
    host = dict(Schema="iw7.t7-registration-image-host/1", PlanPath=str(plan_path), PlanSHA256=plan_hash,
                RunRoot=str(run), HostImage=shells[0]["Path"], SourcePins=host_pins,
                PreservedProcesses=preservation["PreservedProcesses"])
    host_raw = (json.dumps(host, indent=2)+"\n").encode()
    host_path = output/"host-contract.local.json"; host_hash = hashlib.sha256(host_raw).hexdigest()
    output.mkdir(parents=True, exist_ok=False); run.mkdir(parents=True, exist_ok=False)
    for name in ("work", "evidence", "temp"):
        (run/name).mkdir()
    with plan_path.open("xb") as stream:
        stream.write(raw)
    with host_path.open("xb") as stream:
        stream.write(host_raw)
    host_args = ["-NoLogo", "-NoProfile", "-NoExit", "-File", str(entry), "-PlanPath", str(plan_path),
                 "-PlanSHA256", plan_hash, "-RunRoot", str(run), "-HostContractPath", str(host_path),
                 "-HostContractSHA256", host_hash]
    print(json.dumps(dict(Plan=str(plan_path), PlanBytes=len(raw), PlanSHA256=plan_hash,
        HostContract=str(host_path), HostContractSHA256=host_hash, ReferencePlan=reference_pin,
        ReceiverSourceManifest=source_pin, CandidateStatMetadata=metadata_pin, PreservationMetadata=preservation_pin,
        DefaultCommand=dict(Executable=host["HostImage"], Arguments=host_args),
        NativeCommand=dict(Executable=host["HostImage"], Arguments=host_args+["-Run"]),
        Bindings=96, InputMetadata=27, NativeExecuted=False, OpaqueContentRead=False,
        LeaseAcquired=False, Ready=False), indent=2))


if __name__ == "__main__":
    main()
