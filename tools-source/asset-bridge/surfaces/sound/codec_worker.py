"""One pinned FFmpeg decode inside the caller's existing BuildJob; no admission API."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import wave

PCM_SHA = "72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9"
WAV_SHA = "299727b757b46804ca52144133b7e72405f13ddcdaf8aea30a497afc62ca9cb4"
FLAC_SHA = "9f807b3f4dfee213dfd44e3f60b9109075327b233f321bdf38f594c3a0c47bbb"
CODEC_SHA = "ad8f211bc894755e0061c55ab280ae00e8d3d4f15a8cc4372b24cfa247b5942e"
DRAIN_SHA = "a2ab493cf551a43eea3797e5e8437e41aa8f0246d770838956d8984b68c4701d"


def check(ok, message):
    if not ok:
        raise ValueError(message)


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def expected_arguments(flac, output):
    return ["-nostdin", "-n", "-loglevel", "info", "-xerror", "-err_detect", "explode",
            "-threads", "1", "-f", "flac", "-protocol_whitelist", "file", "-i", str(flac),
            "-map", "0:a:0", "-vn", "-sn", "-dn", "-map_metadata", "-1", "-c:a", "pcm_s16le",
            "-threads", "1", "-fflags", "+bitexact", "-flags:a", "+bitexact", "-f", "wav",
            "-fs", "131072", str(output)]


def read_wave(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(131073)
    check(44 <= len(raw) <= 131072, "WAV outside 128 KiB success bound")
    check(raw[:4] == b"RIFF" and raw[8:12] == b"WAVE" and
          int.from_bytes(raw[4:8], "little") + 8 == len(raw), "RIFF/WAVE closure mismatch")
    with wave.open(io.BytesIO(raw), "rb") as decoder:
        check((decoder.getnchannels(), decoder.getsampwidth(), decoder.getframerate(),
               decoder.getnframes(), decoder.getcomptype()) == (1, 2, 48000, 48000, "NONE"),
              "mono16/48000Hz/48000frames/uncompressed required")
        pcm = decoder.readframes(48001)
        check(len(pcm) == 96000 and decoder.readframes(1) == b"", "PCM size/EOF mismatch")
    check(hashlib.sha256(pcm).hexdigest() == PCM_SHA, "PCM hash mismatch")
    return raw, pcm


def decode(plan, copy_bounded):
    root = Path(plan["RunRoot"])
    output = root / "decoded.wav"
    check(not output.exists(), "fresh WAV required")
    check(plan["CodecArguments"] == expected_arguments(plan["InputFLAC"], output), "codec arguments changed")
    for path, sha in ((plan["Codec"], CODEC_SHA), (plan["InputFLAC"], FLAC_SHA), (plan["OriginalWAV"], WAV_SHA)):
        check(file_hash(path) == sha, "pinned codec/audio changed")
    exceeded = threading.Event()
    streams, workers = [], []
    result = {"schema": "iw7.original-sound-codec-worker/1", "codec_sha256": CODEC_SHA,
              "native_exit_code": None, "pipes_eof": False, "failure": None,
              "pcm_verified": False, "playback_verified": False, "ready": False}
    # Outer shared job owns this root and descendants. Never detach or kill by PID.
    process = subprocess.Popen([plan["Codec"], *plan["CodecArguments"]], cwd=root,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=0x08000000 if os.name == "nt" else 0)
    result["native_pid"] = process.pid
    try:
        deadline = time.monotonic() + 10
        for name, source in (("stdout", process.stdout), ("stderr", process.stderr)):
            destination = (root / (name + ".log")).open("xb")
            streams.append(destination)
            thread = threading.Thread(target=copy_bounded, args=(source, destination, exceeded, 32768), daemon=True)
            thread.start()
            workers.append(thread)
        while process.poll() is None:
            check(not exceeded.is_set(), "codec log bound or pipe error")
            check(time.monotonic() < deadline, "codec deadline expired")
            time.sleep(.05)
        for thread in workers:
            thread.join(max(0, deadline - time.monotonic()))
        result["native_exit_code"] = process.returncode
        check(time.monotonic() < deadline and not exceeded.is_set() and not any(t.is_alive() for t in workers),
              "codec EOF/deadline/log failure")
        result["pipes_eof"] = True
        check(process.returncode == 0, "codec exit nonzero")
        raw, pcm = read_wave(output)
        _, original = read_wave(plan["OriginalWAV"])
        check(pcm == original, "decoded samples differ from original WAV")
        result.update(pcm_verified=True, pcm_bytes=96000, pcm_sha256=PCM_SHA, samples=48000,
                      channels=1, bits_per_sample=16, sample_rate=48000,
                      wav_bytes=len(raw), wav_sha256=hashlib.sha256(raw).hexdigest())
    except Exception as error:
        result["failure"] = str(error)
    finally:
        for destination, thread in zip(streams, workers):
            if not thread.is_alive():
                destination.close()
    with (root / "worker-receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    # An unsuccessful child may still hold pipes/processes: only the parent may
    # close the original job. Abrupt root exit must not claim descendant closure.
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args()
    with args.plan.open("rb") as stream:
        raw = stream.read(65537)
    check(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == args.plan_sha256.lower(), "plan changed")
    plan = json.loads(raw)
    check(plan["Schema"] == "iw7.original-sound-codec-execution/1", "plan schema differs")
    drain_path = Path(plan["SharedRepo"]) / "sdk/modding/beacon_tool_phase.py"
    check(file_hash(drain_path) == DRAIN_SHA, "shared log drain changed")
    spec = importlib.util.spec_from_file_location("existing_bounded_drain", drain_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = decode(plan, module.copy_bounded)
    if result["failure"]:
        os._exit(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
