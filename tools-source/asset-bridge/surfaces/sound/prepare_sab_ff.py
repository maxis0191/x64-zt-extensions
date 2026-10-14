"""Prepare a read-only review plan, never stage stock, reserve or launch a tool."""
import argparse
import json
from pathlib import Path
import sys

from read_sab import Inputs, SOURCES, ZONE, contract, original, plain, require, sha, strict_json
from sound_ff_phase import TOOL_SHA, PYTHON_SHA, SOURCE_IDENTITY, validate, verify_helpers

BUILD_RECEIPT_SHA = "a8253c8efa5b315c7870f27c6732eb6893528c0bd4c8ad3ddcbe7dde407faf62"
BUILD_STATE_SHA = "5a99ed368636d08d1d4407e3125cab73f5da879344880588c6aa54efcb556ed8"
BUILD_PLAN_SHA = "91280092489387e909516693d4234c60ea0416657166cf6bd8674bd974729c3a"


def candidate_metadata(receipt, state):
    require(receipt.get("schema") == "iw7.sound-checksum-build-receipt/1" and
            receipt.get("status") == "NativeBuildAndCppProbesPassed" and
            state.get("Schema") == "iw7.sound-checksum-supervisor/1", "actual sound Build F receipts required")
    for name in ("Success", "InputsVerifiedBefore", "InputsVerifiedAfter", "FinalArtifactsVerified", "TreeClosed", "LeaseReleased"):
        require(state.get(name) is True, "completed closed Build F required")
    require(state.get("Failure") is None and state.get("RetainedLeaseToken") is None and
            type(state.get("RootExitCode")) is int and state["RootExitCode"] == 0 and
            type(state.get("JobActiveAtClose")) is int and state["JobActiveAtClose"] == 0,
            "released successful Build F required")
    require(state.get("PlanSHA256") == receipt.get("plan_sha256") == BUILD_PLAN_SHA and
            state.get("RunID") == receipt.get("run_id") and state.get("RunID"), "same completed Build F generation required")
    require(receipt.get("native_cpp_probes_verified") is True and receipt.get("sab_ff_tested") is False and
            receipt.get("ready") is False and state.get("Ready") is False and state.get("SABFFVerified") is False,
            "build provenance cannot grant sound playback")
    artifact = receipt["artifacts"]["candidate_exe"]
    require(artifact == state["Artifacts"]["candidate_exe"] and artifact.get("relative") == "bin/zonetool-sound-md5.exe" and
            type(artifact.get("bytes")) is int and artifact["bytes"] == 21696512 and artifact.get("sha256") == TOOL_SHA,
            "verified checksum candidate artifact differs")
    return artifact


def read_candidate(candidate_receipt):
    receipt_path = plain(candidate_receipt)
    require(receipt_path.name == "build-receipt.json", "actual Build F receipt path required")
    root, inputs = receipt_path.parent, Inputs()
    state_path = root / "supervisor-state.json"
    receipt_raw = inputs.read(receipt_path, 512*1024)
    state_raw = inputs.read(state_path, 16384)
    require(sha(receipt_raw) == BUILD_RECEIPT_SHA and sha(state_raw) == BUILD_STATE_SHA, "exact completed Build F hashes required")
    artifact = candidate_metadata(strict_json(receipt_raw, 512*1024), strict_json(state_raw))
    exe = root / artifact["relative"]
    require(plain(exe).is_file() and exe.stat().st_size == artifact["bytes"], "existing checksum candidate unavailable")
    # Separate bounded metadata collector: the independent SAB reader keeps its
    # 256 KiB per-file limit; this actual build receipt is 413367 bytes.
    require(inputs.read(receipt_path, 512*1024) == receipt_raw and inputs.read(state_path, 16384) == state_raw,
            "Build F metadata changed during preparation")
    return root, {"path": str(exe), "bytes": artifact["bytes"], "sha256": artifact["sha256"]}, inputs.observed


def prepare(source, run_root, shared_repo, prior_stock_plan, prior_stock_plan_sha, candidate_receipt):
    source, run_root, repo = map(plain, (source, run_root, shared_repo))
    require(not run_root.exists(), "fresh absent run root required")
    for root in (source,):
        require(run_root != root and root not in run_root.parents and run_root not in root.parents, "run and original source overlap")
    inputs = Inputs()
    own = Path(__file__).resolve().parent
    contract_path = own / "sab_contract.json"
    contract_raw = inputs.read(contract_path, 16384)
    spec = contract(contract_raw)
    original(inputs, source, spec)
    codec_raw = inputs.read(own / "codec-checkpoint-2026-10-12.json", 16384)
    codec = strict_json(codec_raw)
    require(codec.get("schema") == "iw7.original-sound-codec-checkpoint/1" and codec.get("external_decoder_verified") is True
            and codec.get("input_flac_sha256") == spec["sources"]["sound_assets/community/original_chime_v1.flac"]["sha256"]
            and codec.get("pcm", {}).get("sha256") == spec["pcm_sha256"] and codec.get("job_closed") is True
            and codec.get("retained_lease") is False, "completed original codec checkpoint required")
    verify_helpers(inputs, repo)
    raw = inputs.read(prior_stock_plan, 131072)
    require(sha(raw) == prior_stock_plan_sha.lower(), "historical stock plan changed")
    previous = strict_json(raw, 131072)
    require(previous.get("Schema") == "iw7.material-v2-execution-plan/1", "known existing stock plan required")
    # Preserve the reviewed scenario estimates, without a numeric RAM/commit
    # floor. Positive int64 values are required by the shared lease API.
    for field in ("FFPhysicalBytes", "FFCommitBytes"):
        require(type(previous.get(field)) is int and 0 < previous[field] <= 2**63 - 1,
                "positive typed native estimate required")
    candidate_root, exe, candidate_pins = read_candidate(candidate_receipt)
    # Source-only: do not stage/hash retail files or claim fresh stock identity.
    for name in ("read_sab.py", "read_flac.py", "sound_ff_phase.py", "prepare_sab_ff.py"):
        inputs.read(own / name)
    work, logs = run_root / "work", run_root / "logs"
    python = str(Path(sys.executable).absolute())
    require(sha(inputs.read(python)) == PYTHON_SHA, "reviewed Python changed")
    phases = []
    for name in ("build", "verify", "dump", "read"):
        arguments = (["-headless", "-unbuffered-io", "-strict-content-sources", "-" + name + "zone", ZONE]
                     if name != "read" else ["-B", str(own / "read_sab.py"), "--source", str(source),
                        "--banks", str(work / "zone"), "--contract", str(contract_path),
                        "--dump", str(work / "dump" / ZONE), "--inventory", str(logs / "verify" / "stdout.log")])
        phase = dict(schema="iw7.material-v2-phase/1", phase=name, exe=str(work / "zonetool.exe") if name != "read" else python,
                     sha256=TOOL_SHA if name != "read" else PYTHON_SHA, arguments=arguments,
                     cwd=str(work), logs=str(logs / name), timeout=240 if name != "read" else 30)
        phases.append(validate(phase))
    inputs.recheck()
    return {"schema": "iw7.original-sound-ff-review-plan/1", "status": "SourcePlanOnly", "source": str(source),
            "run_root": str(run_root), "shared_repo": str(repo), "source_contract_sha256": sha(contract_raw),
            "prior_codec_checkpoint_sha256": sha(codec_raw), "codec_repeated": False,
            "existing_candidate": exe, "candidate_root": str(candidate_root),
            "candidate_receipt_sha256": BUILD_RECEIPT_SHA, "candidate_state_sha256": BUILD_STATE_SHA,
            "candidate_binary_hash_recheck_pending": True,
            "historical_stock_plan": str(Path(prior_stock_plan).absolute()), "historical_stock_plan_sha256": prior_stock_plan_sha.lower(),
            "stock_root": previous["StockRoot"], "fresh_stock_identity_and_content_pending": True,
            "stock_staged": False, "physical_bytes": previous["FFPhysicalBytes"], "commit_bytes": previous["FFCommitBytes"],
            "source_output_budget_bytes": 10 * 1024**2 - 1, "future_new_output_stop_bytes": 64 * 1024**2,
            "source_stage_relatives": sorted(SOURCES - {"original/source.wav"}),
            "owned_future_outputs": ["zone/" + ZONE + ending for ending in (".ff", ".sabl", ".sabs")],
            "phase_specs": phases, "phase_adapter": str(own / "sound_ff_phase.py"),
            "shared_phase_runner": "tools-source/asset-bridge/surfaces/material_v2_phase.py",
            "helper_source_identity": SOURCE_IDENTITY, "runtime_input_identity": "exact-bytes-size-sha256",
            "outer_functions": ["Start-MaterialV2OwnedPhase", "Wait-MaterialV2OwnedPhase", "Stop-MaterialV2OwnedPhase", "Restore-IW7BaseTransaction"],
            "pending_execution_work": ["Independent review of original-sound reader, complete transaction and pins",
                "Prepare a fresh checkout-bound execution plan for the four specs and FF/SABL/SABS restoration",
                "Fresh complete scenario admission, stock identities and candidate binary hash under guards",
                "Unique central native GO; no retries"],
            "input_pins": [{"path": str(path), "bytes": size, "sha256": digest}
                           for path, (size, digest) in {**inputs.observed, **candidate_pins}.items()],
            "native_authorized": False, "native_executions": 0, "ready": False, "playback_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "run-root", "shared-repo", "prior-stock-plan", "candidate-receipt"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--prior-stock-plan-sha", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = prepare(args.source, args.run_root, args.shared_repo, args.prior_stock_plan, args.prior_stock_plan_sha, args.candidate_receipt)
    text = json.dumps(result, indent=2) + "\n"
    require(len(text.encode()) < 131072, "review plan size exceeded")
    if args.output:
        with plain(args.output).open("x", encoding="utf-8") as stream:
            stream.write(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
