"""Finite actual CPP80 D Catalogue data adapter; Source/JSON only, no process or alias.

Candidate metadata must come from a separately admitted snapshot. This adapter
never stats/opens the candidate, symbols, SDK or retail inputs and never runs
Catalogue DEFAULT. The ordinary runner independently validates all sealed proof.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path, PureWindowsPath
from prepare_material_parts_probe import EXPORT_FIELDS, REFERENCE_PIN, key, require, read_text_pin
from prepare_image_provenance_probe import CONTROLLERS, read_snapshot, apply_preservation

SOURCE = "0f669b58f7a962cb5f5c01af252ce05d8bdbbc3b"
NATIVE = "fab935826c898806855376662a8a03317b3ad8f1"
CANDIDATE = (22054400, "f14a0af9c8e7a0a58e7f1331fa996806139356c6063e47fc6325f2ad423c8f40")
PINS = {
    "Plan": (406073, "11544206c4a723722696e35ef869bc8ad9c713a8ada212811deae8bb7b5dc092"),
    "Receipt": (50715, "320bcfc68b205eee81b00e0b5e0fa50e391523db15737ff6670ad2d0e5944b8d"),
    "Handoff": (37937, "d1c06527a7e149111efc593b6c09d9ce5cbcbc92ef3b0218e2ac836039dad7a1"),
    "SourceManifest": (385050, "fe60a6ed7eb0a912e399251c358ff48798bc705a8c079b9d1884f6f49505a272"),
    "PreExit": (58054, "599382303342137f09729487463c9f8db0c1e63cb68c9a0ceb933a7b22da129e"),
    "PostExit": (35547, "40b59ede7f671d9d7e6d534ec923eba5d9f58b13475975c0d13f520e7880740d"),
    "PreReleaseReceipt": (50674, "78fe9943e7163e43a7b22064f4df98a3ad48070a40bda0e0d28107d96be44e68"),
    "FixtureStdout": (78, "a7956d2cf5c0a8daca4f9969315067999151c992d4742ab52f7fa7efceea1a2a"),
}
BUILD_FIELDS = (
    "Wiring", "PreparedMain", "PreparedCLI", "BaseBuildPlan", "BaseBuildReceipt", "LinkResponse",
    "RegistrationWiring", "RegistrationContract", "RegistrationCapture", "RegistrationEntry",
    "RegistrationFixture", "RegistrationObserver", "RegistrationResponse", "BindingsBuildWiring",
    "BindingsIncomingWiring", "BindingsBuildValidator", "BindingsBuildContract", "BindingsWiring",
    "BindingsContract", "BindingsModule", "BindingsEntry", "BindingsFixture", "BindingsLegacyFixture",
    "BindingsCapture", "BindingsObserver", "BindingsBaselineFixture", "BindingsCombinedFixture", "BindingsResponse",
)
CONTRACT = (5391, "d60f0e33d9dddb69656744f6481ba32ced1a7a040d75ff913908192297e3c9a6")
READER = (9687, "8e1d464c6467492b65e102b784aa9f265723560b9b486499e3a49cb4073f5c81")


def read_source_metadata_json(raw):
    # Immutable Source manifests/plans/proofs use the existing text-input bound.
    # Runtime reports/snapshots keep their independent 32/64-KiB decoder.
    require(type(raw) is bytes and 0 < len(raw) <= 1024*1024, "bounded Source JSON required")
    def pairs(items):
        result = {}
        for name, value in items:
            require(name not in result, "duplicate Source JSON field")
            result[name] = value
        return result
    def constant(_):
        raise ValueError("nonfinite Source JSON number")
    value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs, parse_constant=constant)
    require(type(value) is dict, "Source JSON object required")
    return value


def exact_pin(pin, expected):
    require(type(pin) is dict and set(pin) == {"Path", "Bytes", "SHA256"} and
            type(pin["Path"]) is str and type(pin["Bytes"]) is int and type(pin["SHA256"]) is str and
            (pin["Bytes"], pin["SHA256"]) == expected, "Exact typed actual CPP80 text pin required")


def read_source_text(path, expected):
    # Reject opaque/device/ADS selectors before Path.resolve can query metadata.
    lexical = str(path).replace("\\", "/")
    require(not lexical.casefold().startswith(("//?/", "//./", "/??/", "//??/")) and
            ":" not in lexical[2:] and not PureWindowsPath(lexical).is_reserved(), "Ordinary Source text path required")
    require(Path(path).suffix.lower() in ((".log",) if expected == PINS["FixtureStdout"] else
            (".json", ".ps1", ".py", ".cs", ".hpp", ".inc", ".cpp", ".rsp")), "Declared Source text extension required")
    if expected != PINS["FixtureStdout"]:
        return read_text_pin(path, expected)
    # The sole log input is this immutable 78-byte CPP fixture, never stderr or runtime output.
    path = Path(path)
    require(path.is_absolute() and path == path.resolve() and path.name == "stdout.log", "Exact fixture path required")
    for parent in (path, *path.parents):
        require(not parent.is_symlink() and not parent.is_junction(), "Reparse fixture refused")
    require(path.stat().st_size == expected[0], "Exact fixture size required before open")
    with path.open("rb") as stream:
        raw = stream.read(expected[0]+1)
    require((len(raw), hashlib.sha256(raw).hexdigest()) == expected, "Exact fixture bytes required")
    require(raw == b"IW7_T7_REGISTRATION_HEADER_CHECKS=39\r\nIW7_T7_REGISTRATION_BINDINGS_CHECKS=41\r\n", "Actual 39+41 fixture required")
    return dict(Path=str(path), Bytes=len(raw), SHA256=expected[1]), raw


def derive(reference, controllers, build, receipt, proofs, contract, reader, candidate_metadata, run):
    require(reference["Operation"] == "ResidentExportV1" and reference["CandidateProfile"] == "t7-catalog-message-publication" and
            reference["SelectedStreamedRenderOnlyV2"]["Schema"] == "iw7.t7-selected-streamed-render-only-plan/2" and
            len(reference["Bootstraps"]) == 23 and len(reference["InputMetadata"]) == 29,
            "Exact qualified E5 reference family required")
    require(len(controllers) == 10, "Existing ten Catalogue controller pins required")
    for name, expected in PINS.items():
        exact_pin(proofs[name], expected)
    exact_pin(contract, CONTRACT); exact_pin(reader, READER)
    require(type(candidate_metadata) is dict and type(candidate_metadata["Bytes"]) is int and
            candidate_metadata["Bytes"] == CANDIDATE[0], "Admitted actual CPP80 candidate metadata required")
    require(build["Schema"] == "iw7.t7-minimal-build-plan/1" and build["SourceCommit"] == NATIVE and
            receipt["Schema"] == "iw7.t7-minimal-build/1" and receipt["Status"] == "Passed" and
            receipt["PlanSHA256"] == PINS["Plan"][1] and receipt["RegistrationBindingsFixturePassed"] is True and
            "RegistrationBindingsCPPQualified" not in receipt, "Actual CPP80 receipt required; no invented top flag")
    linked = [p for p in receipt["Stages"][-1]["Artifacts"] if p["Path"] == candidate_metadata["Path"]]
    require(len(linked) == 1 and (linked[0]["Bytes"], linked[0]["SHA256"]) == CANDIDATE and
            key(candidate_metadata["Path"]) == key(str(PureWindowsPath(build["RunRoot"])/"link/zonetool-t7.exe")),
            "Candidate must be original CPP80 under-lease link artifact")
    marker = dict(Schema="iw7.t7-registration-bindings-cpp80/1", SourceRevision="92118595079b86d66c340c22b299de90c49a2b6a",
        ReaderRevision="6d16303437f706df4037c636b3ee9f8a5da00aaf", Contract=contract, Reader=reader,
        NativeSchema="iw7.t7-registration-material-bindings/1", BindingCount=7, ReportLimitBytes=32768,
        SourceOnlyPending=False, BuildRecipeWired=True, CompiledExtensionSource=SOURCE, CPPQualification=proofs["Handoff"],
        CPPQualified=True, NativeObserved=False, DeepMetadataOutcome=None, QualifiedObjectMipCount=None, Ready=False)
    result = copy.deepcopy(reference)
    for name in EXPORT_FIELDS:
        result.pop(name, None)
    result.update(Schema="iw7.t7-registration-bindings-plan/1", Operation="RegistrationMaterialBindingsV1",
        CandidateProfile="t7-registration-material-bindings-v1",
        Arguments=["-t7-iw7-registration-material-bindings-v1", "mp_freerun_04", "p7_fre_platform_cap_02", "0"],
        OutputKey="t7_iw7_registration_material_bindings_v1", ReportLimitBytes=32768, TraceStderrLimitBytes=16384,
        RunRoot=str(run), WorkingDirectory=str(run/"work"), StageRoot=str(run/"evidence"), Image=str(run/"work/t7-zonetool-candidate.exe"),
        CandidateSource=candidate_metadata["Path"], CandidateBytes=CANDIDATE[0], CandidateSHA256=CANDIDATE[1],
        BuildPlan=proofs["Plan"]["Path"], ExpectedBuildPlanSHA256=PINS["Plan"][1],
        BuildReceipt=proofs["Receipt"]["Path"], ExpectedBuildReceiptSHA256=PINS["Receipt"][1], Runner=controllers[0]["Path"],
        SelectedRegistrationMaterialBindingsV1=marker)
    allowed = {key(reference[name]) for name in ("EngineSource", "SteamSource")}
    allowed.add(key(reference["Zone"]["Path"])); allowed.update(key(p["Path"]) for p in reference["Bootstraps"])
    result["InputMetadata"] = [copy.deepcopy(candidate_metadata)] + [copy.deepcopy(p) for p in reference["InputMetadata"] if key(p["Path"]) in allowed]
    require(len(result["InputMetadata"]) == 27, "Only candidate/engine/Steam/zone/23 bootstrap metadata allowed")
    retained = {key(p["QualificationScript"]["Path"]) for p in reference["Bootstraps"]}
    retained.update(key(p["QualificationReceipt"]["Path"]) for p in reference["Bootstraps"])
    retained.update(key(reference["SharedQualification"][name]["Path"]) for name in ("Script", "Plan", "Receipt"))
    bindings = [copy.deepcopy(p) for p in reference["Bindings"] if not p["IsText"] or key(p["Path"]) in retained]
    old = [p for p in bindings if key(p["Path"]) == key(reference["CandidateSource"])]
    require(len(old) == 1, "One historical candidate binding required")
    old[0].update(Path=candidate_metadata["Path"], Bytes=CANDIDATE[0], SHA256=CANDIDATE[1])
    require(build["BuildProfile"]["RegistrationFixture"] == build["BuildProfile"]["BindingsLegacyFixture"] and
            build["BuildProfile"]["RegistrationResponse"] == build["BuildProfile"]["BindingsResponse"], "Original CPP80 shared fixture/response aliases required")
    text = [*proofs.values(), *controllers, contract, reader, *(build["BuildProfile"][name] for name in BUILD_FIELDS)]
    dependencies = [p for p in receipt["Stages"][2]["Artifacts"] if PureWindowsPath(p["Path"]).name == "dependencies.json"]
    require(len(dependencies) == 1, "One original main dependencies text required")
    text.extend(dependencies)
    unique = {}
    for pin in text:
        identity = key(pin["Path"])
        require(identity not in unique or unique[identity] == pin, "Conflicting shared Source pin refused")
        unique[identity] = pin
    bindings.extend(dict(p, IsText=True) for p in unique.values())
    require(len({key(p["Path"]) for p in bindings}) == len(bindings) == 112, "Exact unique CPP80 binding set required")
    result["Bindings"] = bindings
    result["OutputLimitBytes"] = 16977344+21737352+235600+64*1024**2+CANDIDATE[0]+sum(p["Bytes"] for p in reference["Bootstraps"])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "reference", "handoff", "candidate-metadata", "preservation-metadata", "run-root", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(argv)
    source = args.source.resolve(strict=True)
    source_pin, raw = read_text_pin(source/"source-workspace.json"); workspace = read_source_metadata_json(raw)
    require(workspace["schema"] == "iw7.source-workspace/1" and workspace["product"] == "x64-zt-extensions" and
            workspace["revisions"]["x64-zt-extensions"] and workspace["files"], "Composed receiver Source required")
    reference_pin, raw = read_source_text(args.reference, REFERENCE_PIN); reference = read_source_metadata_json(raw)
    handoff_pin, raw = read_source_text(args.handoff, PINS["Handoff"]); handoff = read_source_metadata_json(raw)
    require(handoff["Schema"] == "iw7.t7-registration-bindings-cpp-actual-handoff/1" and handoff["Status"] == "Passed" and
            handoff["SourceCommit"] == SOURCE and handoff["NativeSourceCommit"] == NATIVE and handoff["CPP80ObservedClosed"] is True and
            handoff["CandidateExecuted"] is False and handoff["CandidateOrSymbolsReadAfterRelease"] is False,
            "Actual closed CPP80 D handoff required")
    proofs = dict(Handoff=handoff_pin); values = {}
    for name, expected in PINS.items():
        if name == "Handoff":
            continue
        exact_pin(handoff[name], expected)
        pin, raw = read_source_text(handoff[name]["Path"], expected)
        proofs[name] = pin
        if name in ("Plan", "Receipt"):
            values[name] = read_source_metadata_json(raw)
    metadata_pin, metadata = read_snapshot(args.candidate_metadata)
    require(metadata["Path"] == handoff["Candidate"]["Path"], "Admitted candidate path differs")
    controllers = [read_text_pin(source/name)[0] for name in CONTROLLERS]
    rows = {row["path"]: row for row in workspace["files"]}
    for name, pin in zip(CONTROLLERS, controllers):
        row = rows.get(name, {})
        require((row.get("bytes"), row.get("sha256")) == (pin["Bytes"], pin["SHA256"]), "Receiver Source manifest differs")
    contract = read_text_pin(source/"tools-source/asset-bridge/t7-iw7/registration-material-bindings-source-contract.json", CONTRACT)[0]
    reader = read_text_pin(source/"tools-source/asset-bridge/t7-iw7/registration_bindings_consumer.py", READER)[0]
    preservation_pin, preservation = read_snapshot(args.preservation_metadata)
    run = args.run_root; output = args.output
    require(run.is_absolute() and run == run.resolve() and run.parent == source/"runtime" and
            re.fullmatch(r"t7-registration-bindings-[a-z][a-z0-9-]*", run.name) and not run.exists(), "Fresh receiver runtime required")
    require(output.is_absolute() and output == output.resolve() and output.parent == source/"runtime" and
            re.fullmatch(r"registration-bindings-plan-[a-z][a-z0-9-]*", output.name) and not output.exists(), "Fresh control output required")
    for parent in (*run.parents, *output.parents):
        require(not parent.is_symlink() and not parent.is_junction(), "Reparse output parent refused")
    plan = derive(reference, controllers, values["Plan"], values["Receipt"], proofs, contract, reader, metadata, run)
    apply_preservation(plan, preservation)
    for pin in plan["Bindings"]:
        if pin["IsText"]:
            read_source_text(pin["Path"], (pin["Bytes"], pin["SHA256"]))
    raw = (json.dumps(plan, indent=2)+"\n").encode(); require(len(raw) <= 128*1024, "Existing plan limit exceeded")
    plan_path = output/"plan.local.json"; plan_hash = hashlib.sha256(raw).hexdigest()
    entry = source/"tools-source/asset-bridge/t7-bridge/Invoke-T7CatalogueHost.ps1"
    host_pins = [read_text_pin(path)[0] for path in (entry, source/"tools-source/asset-bridge/t7-bridge/T7CatalogueHost.Core.ps1",
                                                 source/"tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1")]
    shells = [p for p in plan["Bindings"] if not p["IsText"] and PureWindowsPath(p["Path"]).name == "pwsh.exe"]
    require(len(shells) == 1, "One exact retained host binding required")
    host = dict(Schema="iw7.t7-registration-bindings-host/1", PlanPath=str(plan_path), PlanSHA256=plan_hash, RunRoot=str(run),
                HostImage=shells[0]["Path"], SourcePins=host_pins, PreservedProcesses=preservation["PreservedProcesses"])
    host_raw = (json.dumps(host, indent=2)+"\n").encode(); host_hash = hashlib.sha256(host_raw).hexdigest()
    require(len(host_raw) <= 32*1024, "Existing host contract limit exceeded")
    output.mkdir(parents=True, exist_ok=False); run.mkdir(parents=True, exist_ok=False)
    for name in ("work", "evidence", "temp"):
        (run/name).mkdir()
    with plan_path.open("xb") as stream:
        stream.write(raw)
    host_path = output/"host-contract.local.json"
    with host_path.open("xb") as stream:
        stream.write(host_raw)
    host_args = ["-NoLogo", "-NoProfile", "-NoExit", "-File", str(entry), "-PlanPath", str(plan_path), "-PlanSHA256", plan_hash,
                 "-RunRoot", str(run), "-HostContractPath", str(host_path), "-HostContractSHA256", host_hash]
    print(json.dumps(dict(Plan=str(plan_path), PlanBytes=len(raw), PlanSHA256=plan_hash, HostContract=str(host_path), HostContractSHA256=host_hash,
        ReferencePlan=reference_pin, ReceiverSourceManifest=source_pin, CandidateStatMetadata=metadata_pin, PreservationMetadata=preservation_pin,
        DefaultCommand=dict(Executable=host["HostImage"], Arguments=host_args), NativeCommand=dict(Executable=host["HostImage"], Arguments=host_args+["-Run"]),
        Bindings=112, InputMetadata=27, NativeExecuted=False, OpaqueContentRead=False, LeaseAcquired=False, Ready=False), indent=2))


if __name__ == "__main__":
    main()
