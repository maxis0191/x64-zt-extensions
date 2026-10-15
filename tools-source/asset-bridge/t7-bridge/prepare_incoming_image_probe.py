"""Finite CPP87 incoming-header source plan data adapter; no process, alias or binary reads."""
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

CANDIDATE = (22059008, "4fcb0205e30979457784d1b883a153ecf5c20751543b68dfb184671d59e3ee4d")
BUILD = (403533, "2becaab02373a248dbcf5797501680beeb4d80f1c5603cbe969540a35776c0f9")
RECEIPT = (49161, "481dfa424367320699ee368b7272fa17d64b29babef775efe63f4e1fcd81f9b4")
HANDOFF = (15076, "da75f2c758282ed0e31bcd1f3c0f99ad0ad772c7773ee731bd0e69df374230c3")
CONTROLLERS = (
    "tools-source/asset-bridge/t7-bridge/Run-T7Catalogue.ps1",
    "tools-source/asset-bridge/t7-bridge/T7Catalogue.Profile.ps1",
    "tools-source/asset-bridge/t7-bridge/T7Prepatch.Profile.ps1",
    "tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1",
    "ops/Resource-Scheduler.Core.ps1", "ops/Resource-Memory.ps1",
    "ops/Resource-RecorderOwnedProcess.Core.ps1", "ops/native/ResourceMemory.cs",
    "ops/hud-lab/HudFileIdentity.cs",
    "tools-source/asset-bridge/t7-bridge/T7ImageProvenance.Profile.ps1",
    "tools-source/asset-bridge/t7-bridge/T7IncomingImage.Profile.ps1",
)
FIXTURE = (71, "414c5d2a646e4a9d3671ae904a9d6d1f8109b559790ef2045fbbc7f8ffbbfdf2")

REVIEWED_SOURCE = "41e595f09dabdd6dff14439f09bd701bddd4a235"
COMPILED_SOURCE = "bde117b8dd40945033d00231b28738b345f09fdb"
TEXT_PINS = {
    "Contract": (4613, "a2cdaf54b7387616bd56d9a78538e7a273ec35e9eb2f6f6ac1e130ecd3851323"),
    "SourceManifest": (372028, "d38eef9eb4be10c865cbed0bbc15ea12617321bc673cc8674ae514a997e31c59"),
    "HostWitness": (10340, "9a895ee72e2d75909d006ee4bd8f0893cc172e992c9d016de7858dff71d2620b"),
    "ClosureWitness": (6327, "5c33ec17caddb888a07d4f7697bba12bf97f9e54612549a3922fcbae144b7a66"),
    "FixtureStdout": FIXTURE,
    "FreshWitness": (401, "98b8636504f3484b48cea365590a340c3bcad98c7a9369341997f0cca23786bf"),
}


def read_source_text(path, expected=None):
    if expected != FIXTURE:
        return read_text_pin(path, expected)
    # The sole log input is the exact 71-byte closed CPP fixture stdout.
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
            "Exact closed CPP87 recipe and receipt required")
    require(candidate_metadata["Bytes"] == CANDIDATE[0] and
            receipt["data"]["Stages"][-1]["Name"] == "link", "Measured CPP87 candidate metadata required")
    linked = [p for p in receipt["data"]["Stages"][-1]["Artifacts"]
              if p["Path"] == candidate_metadata["Path"]]
    require(len(linked) == 1 and (linked[0]["Bytes"], linked[0]["SHA256"]) == CANDIDATE,
            "Candidate must be the original admitted CPP87 link artifact")
    require(marker["ReviewedPrerequisiteSource"] == REVIEWED_SOURCE and marker["CompiledExtensionSource"] == COMPILED_SOURCE,
            "Separate reviewed prerequisite and actual compiled source required")
    for name, expected in TEXT_PINS.items():
        value = marker[name]
        require(set(value) == {"Path", "Bytes", "SHA256"} and type(value["Bytes"]) is int and
                type(value["SHA256"]) is str and (value["Bytes"], value["SHA256"]) == expected,
                "Exact typed closed incoming text pin required")
    require(marker["Contract"] == build["data"]["BuildProfile"]["IncomingContract"],
            "Contract marker must alias the original IncomingContract pin")
    result = copy.deepcopy(reference)
    for name in EXPORT_FIELDS:
        result.pop(name, None)
    result.update(Schema="iw7.t7-incoming-image-plan/1", Operation="IncomingImageObservationV1",
        CandidateProfile="t7-incoming-image-header-observation-v1",
        Arguments=["-t7-iw7-incoming-image-header-v1", "mp_freerun_04", "p7_fre_platform_cap_02", "0"],
        OutputKey="t7_iw7_incoming_image_observation_v1", ReportLimitBytes=32768, TraceStderrLimitBytes=16384,
        RunRoot=str(run), WorkingDirectory=str(run/"work"), StageRoot=str(run/"evidence"),
        Image=str(run/"work/t7-zonetool-candidate.exe"), CandidateSource=candidate_metadata["Path"],
        CandidateBytes=CANDIDATE[0], CandidateSHA256=CANDIDATE[1],
        BuildPlan=build["pin"]["Path"], ExpectedBuildPlanSHA256=BUILD[1],
        BuildReceipt=receipt["pin"]["Path"], ExpectedBuildReceiptSHA256=RECEIPT[1],
        Runner=controllers[0]["Path"],
        SelectedIncomingImageObservationV1=dict(Schema="iw7.t7-incoming-image-cpp87/1", **marker))
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
    text = [build["pin"], receipt["pin"], *controllers, *(marker[name] for name in ("SourceManifest", "HostWitness", "ClosureWitness", "FixtureStdout", "FreshWitness"))]
    text.extend(build["data"]["BuildProfile"][name] for name in
                ("Wiring", "PreparedMain", "PreparedCLI", "BaseBuildPlan", "BaseBuildReceipt", "LinkResponse", "RegistrationWiring", "RegistrationContract", "RegistrationCapture",
                 "RegistrationEntry", "RegistrationFixture", "RegistrationObserver", "RegistrationResponse",
                 "IncomingWiring", "IncomingContract", "IncomingMembers", "IncomingModule", "IncomingEntry", "IncomingFixture",
                 "IncomingCapture", "IncomingObserver", "IncomingBaselineFixture"))
    dependencies = [p for p in receipt["data"]["Stages"][2]["Artifacts"]
                    if PureWindowsPath(p["Path"]).name == "dependencies.json"]
    require(len(dependencies) == 1, "One original main dependency text required")
    text.extend(dependencies)
    bindings.extend(dict(p, IsText=True) for p in text)
    require(len({key(p["Path"]) for p in bindings}) == len(bindings) == 106, "Exact unique incoming binding set required")
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
    require(handoff["Schema"] == "iw7.t7-incoming-image-cpp-qualification-handoff/1" and
            handoff["SourceCommit"] == "bde117b8dd40945033d00231b28738b345f09fdb" and
            handoff["NativeSourceCommit"] == "fab935826c898806855376662a8a03317b3ad8f1" and handoff["IncomingCPPQualified"] is True and
            handoff["RegistrationCPPQualified"] is True and handoff["CandidateExecuted"] is False,
            "Closed unexecuted CPP87 handoff required")
    build_pin, raw = read_text_pin(handoff["Plan"]["Path"], BUILD)
    build = json.loads(raw)
    receipt_pin, raw = read_text_pin(handoff["Receipt"]["Path"], RECEIPT)
    receipt = json.loads(raw)
    metadata_pin, metadata = read_snapshot(args.candidate_metadata)  # Never stat/hash the candidate here.
    require(metadata["Path"] == handoff["CandidateRecordedUnderLease"]["Path"] and
            type(metadata["Bytes"]) is int and metadata["Bytes"] == CANDIDATE[0],
            "Admitted candidate stat metadata required")
    controllers = [read_text_pin(source/name)[0] for name in CONTROLLERS]
    source_rows = {row["path"]: row for row in workspace["files"]}
    for name, pin in zip(CONTROLLERS, controllers):
        row = source_rows.get(name, {})
        require((row.get("bytes"), row.get("sha256")) == (pin["Bytes"], pin["SHA256"]),
                "Receiver controller differs from its composed source manifest")
    preservation_pin, preservation = read_snapshot(args.preservation_metadata)
    closure_pin, closure_raw = read_text_pin(handoff["Closure"]["Path"], TEXT_PINS["ClosureWitness"])
    closure = json.loads(closure_raw)
    marker = dict(ReviewedPrerequisiteSource=REVIEWED_SOURCE, CompiledExtensionSource=COMPILED_SOURCE,
        Contract=handoff["IncomingContract"], SourceManifest=handoff["SourceManifest"], HostWitness=handoff["Preexit"],
        ClosureWitness=closure_pin, FixtureStdout=handoff["FixtureStdout"], FreshWitness=closure["FreshObservation"])
    run = args.run_root; output = args.output
    require(run.is_absolute() and run == run.resolve() and run.parent == source/"runtime" and
            re.fullmatch(r"t7-incoming-image-[a-z][a-z0-9-]*", run.name) and not run.exists(),
            "Fresh receiver private runtime required")
    require(output.is_absolute() and output == output.resolve() and output.parent == source/"runtime" and
            re.fullmatch(r"incoming-image-plan-[a-z][a-z0-9-]*", output.name) and not output.exists(),
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
    host = dict(Schema="iw7.t7-incoming-image-host/1", PlanPath=str(plan_path), PlanSHA256=plan_hash,
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
        Bindings=106, InputMetadata=27, NativeExecuted=False, OpaqueContentRead=False,
        LeaseAcquired=False, Ready=False), indent=2))


if __name__ == "__main__":
    main()
