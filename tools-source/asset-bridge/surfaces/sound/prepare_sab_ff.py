"""Prepare a read-only review plan, never stage stock, reserve or launch a tool."""
import argparse
import json
from pathlib import Path
import sys

from read_sab import Inputs, SOURCES, ZONE, contract, original, plain, require, sha, strict_json
from sound_ff_phase import TOOL_SHA, PYTHON_SHA, SOURCE_IDENTITY, validate, verify_helpers


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
    for field, amount in (("FFPhysicalBytes", 8 * 1024**3), ("FFCommitBytes", 11 * 1024**3)):
        require(type(previous.get(field)) is int and previous[field] == amount, "native budget differs")
    receipt_raw = inputs.read(candidate_receipt, 16384)
    candidate = strict_json(receipt_raw)
    builder = previous["Source"]["builder"]
    require(sha(receipt_raw) == builder["receipt_sha256"] and candidate["schema"] == "iw7.zonetool-community-candidate/1",
            "reviewed existing candidate receipt differs")
    exe = candidate["executable"]
    require(exe["sha256"] == TOOL_SHA and type(exe["bytes"]) is int and exe["bytes"] == 21696512, "known existing tool required")
    require(plain(exe["path"]).is_file() and Path(exe["path"]).stat().st_size == exe["bytes"], "existing tool unavailable")
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
            "existing_candidate": exe, "candidate_binary_hash_recheck_pending": True,
            "historical_stock_plan": str(Path(prior_stock_plan).absolute()), "historical_stock_plan_sha256": prior_stock_plan_sha.lower(),
            "stock_root": previous["StockRoot"], "fresh_stock_identity_and_content_pending": True,
            "stock_staged": False, "physical_bytes": 8 * 1024**3, "commit_bytes": 11 * 1024**3,
            "source_output_budget_bytes": 10 * 1024**2 - 1, "future_new_output_stop_bytes": 64 * 1024**2,
            "source_stage_relatives": sorted(SOURCES - {"original/source.wav"}),
            "owned_future_outputs": ["zone/" + ZONE + ending for ending in (".ff", ".sabl", ".sabs")],
            "phase_specs": phases, "phase_adapter": str(own / "sound_ff_phase.py"),
            "shared_phase_runner": "tools-source/asset-bridge/surfaces/material_v2_phase.py",
            "helper_source_identity": SOURCE_IDENTITY, "runtime_input_identity": "exact-bytes-size-sha256",
            "outer_functions": ["Start-MaterialV2OwnedPhase", "Wait-MaterialV2OwnedPhase", "Stop-MaterialV2OwnedPhase", "Complete-ModelFFRestore"],
            "pending_execution_work": ["Review original-sound reader/adapter and pins",
                "Bind the existing outer original-job/stock transaction to these four specs",
                "Include FF, SABL and SABS in backup/restore and output bounds",
                "Fresh complete 8/11 admission, stock identities and candidate binary hash under guards",
                "Unique central native GO; no retries"],
            "input_pins": [{"path": str(path), "bytes": size, "sha256": digest} for path, (size, digest) in inputs.observed.items()],
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
