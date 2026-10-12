"""Mocked codec failure/EOF tests only. No FFmpeg, native owner or reservation."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import codec_worker as worker
from pcm_source import original_wave

DRAIN_PATH = Path(__file__).resolve().parents[4] / "sdk/modding/beacon_tool_phase.py"
spec = importlib.util.spec_from_file_location("existing_drain", DRAIN_PATH)
drain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drain)


class FakeProcess:
    pid = 777

    def __init__(self, exit_code=0, stderr=b"synthetic log", running=False):
        self.returncode = exit_code
        self.stdout = io.BytesIO(b"")
        self.stderr = io.BytesIO(stderr)
        self.running = running

    def poll(self):
        return None if self.running else self.returncode


class CodecTests(unittest.TestCase):
    def fixture(self, root, profile="OriginalSource"):
        root = Path(root)
        original = root / "original.wav"
        original.write_bytes(original_wave())
        run = root / "run"
        run.mkdir()
        plan = {"InputProfile": profile, "RunRoot": str(run), "Codec": str(root / "ffmpeg.exe"),
                "InputFLAC": str(root / "source.flac"), "OriginalWAV": str(original)}
        plan["CodecArguments"] = worker.expected_arguments(plan["InputFLAC"], run / "decoded.wav")
        hashes = {plan["Codec"]: worker.CODEC_SHA, plan["InputFLAC"]: worker.input_profile(plan)[1],
                  plan["OriginalWAV"]: worker.WAV_SHA}
        return plan, hashes, run

    def run_mock(self, root, process=None, corrupt=False, profile="OriginalSource"):
        plan, hashes, run = self.fixture(root, profile)

        def fake_launch(*args, **kwargs):
            raw = bytearray(original_wave())
            if corrupt:
                raw[100] ^= 1
            (run / "decoded.wav").write_bytes(raw)
            return process or FakeProcess()

        with patch.object(worker, "file_hash", side_effect=lambda path: hashes[str(path)]), \
                patch.object(worker.subprocess, "Popen", side_effect=fake_launch) as launch:
            result = worker.decode(plan, drain.copy_bounded)
        return result, launch, run

    def test_shared_drain_pin(self):
        self.assertEqual(hashlib.sha256(DRAIN_PATH.read_bytes()).hexdigest(), worker.DRAIN_SHA)

    def test_mock_success_requires_exact_pcm_and_no_shell(self):
        with tempfile.TemporaryDirectory() as root:
            result, launch, run = self.run_mock(root)
            self.assertTrue(result["pcm_verified"])
            self.assertTrue(result["pipes_eof"])
            self.assertTrue(all(item["normal_return"] and item["exception_type"] is None
                                for item in result["drains"].values()))
            self.assertEqual(result["native_exit_code"], 0)
            self.assertFalse(result["ready"])
            self.assertNotIn("shell", launch.call_args.kwargs)
            self.assertEqual(launch.call_args.kwargs["stdin"], worker.subprocess.DEVNULL)
            self.assertEqual(result, json.loads((run / "worker-receipt.json").read_text()))

    def test_nonzero_native_refused(self):
        with tempfile.TemporaryDirectory() as root:
            result, _, _ = self.run_mock(root, FakeProcess(exit_code=3))
            self.assertEqual(result["failure"], "codec exit nonzero")
            self.assertFalse(result["pcm_verified"])

    def test_native_dump_profile_has_separate_status_without_conformance_claim(self):
        for profile, expected in (("NativeDumpF", worker.DUMP_F_SHA), ("NativeDumpOnlyC", worker.DUMP_ONLY_C_SHA)):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as root:
                result, launch, _ = self.run_mock(root, profile=profile)
                self.assertEqual(result["status"], "DumpDecodedByFFmpeg")
                self.assertEqual(result["input_flac_sha256"], expected)
                self.assertEqual(result["input_profile"], profile)
                self.assertTrue(result["pcm_verified"])
                self.assertFalse(result["standalone_flac_conformance_verified"])
                self.assertFalse(result["playback_verified"])
                args = launch.call_args.args[0]
                self.assertNotIn("-ar", args)
                self.assertNotIn("-ac", args)

    def test_closed_profiles_reject_unknown_or_missing_before_any_payload_read(self):
        for value in (None, "nativedumpf", "Other", True, {}, 1):
            with self.subTest(profile=value), tempfile.TemporaryDirectory() as root:
                plan, _, _ = self.fixture(root)
                plan["InputProfile"] = value
                with patch.object(worker, "file_hash") as hashed, patch.object(worker.subprocess, "Popen") as launch:
                    with self.assertRaisesRegex(ValueError, "closed codec profile"):
                        worker.decode(plan, drain.copy_bounded)
                    hashed.assert_not_called()
                    launch.assert_not_called()

    def test_profiles_cannot_exchange_input_hashes(self):
        for name, wrong_sha in (("OriginalSource", worker.DUMP_F_SHA), ("NativeDumpF", worker.FLAC_SHA),
                                ("NativeDumpOnlyC", worker.FLAC_SHA), ("NativeDumpOnlyC", worker.DUMP_F_SHA),
                                ("NativeDumpF", worker.DUMP_ONLY_C_SHA)):
            with self.subTest(profile=name), tempfile.TemporaryDirectory() as root:
                plan, hashes, _ = self.fixture(root, name)
                hashes[plan["InputFLAC"]] = wrong_sha
                with patch.object(worker, "file_hash", side_effect=lambda path: hashes[str(path)]), \
                        patch.object(worker.subprocess, "Popen") as launch:
                    with self.assertRaisesRegex(ValueError, "pinned"):
                        worker.decode(plan, drain.copy_bounded)
                    launch.assert_not_called()

    def test_resampling_arguments_refused(self):
        for option in ("-ar", "-ac"):
            with self.subTest(option=option), tempfile.TemporaryDirectory() as root:
                plan, _, _ = self.fixture(root, "NativeDumpF")
                plan["CodecArguments"][0:0] = [option, "48000"]
                with patch.object(worker, "file_hash") as hashed, patch.object(worker.subprocess, "Popen") as launch:
                    with self.assertRaisesRegex(ValueError, "arguments"):
                        worker.decode(plan, drain.copy_bounded)
                    hashed.assert_not_called()
                    launch.assert_not_called()

    def test_log_flood_is_truncated_and_refused(self):
        with tempfile.TemporaryDirectory() as root:
            result, _, run = self.run_mock(root, FakeProcess(stderr=b"X" * 70000))
            self.assertIn("log failure", result["failure"])
            self.assertEqual((run / "stderr.log").stat().st_size, 32768)
            self.assertFalse(result["pcm_verified"])

    def test_read_baseexceptions_fail_capture_without_formatting(self):
        class Unformattable(ValueError):
            def __str__(self):
                raise AssertionError("exception text must not be formatted")

        for error in (ValueError("read failed"), SystemExit(7), KeyboardInterrupt(),
                      Unformattable(), type("X" * 200, (BaseException,), {})()):
            with self.subTest(error_type=type(error).__name__), tempfile.TemporaryDirectory() as root:
                process = FakeProcess()
                process.stderr.read = lambda _count, error=error: (_ for _ in ()).throw(error)
                with patch.object(worker.threading, "excepthook") as escaped:
                    result, _, _ = self.run_mock(root, process)
                escaped.assert_not_called()
                self.assertIn("log failure", result["failure"])
                self.assertFalse(result["pipes_eof"])
                self.assertFalse(result["pcm_verified"])
                self.assertFalse(result["drains"]["stderr"]["normal_return"])
                self.assertEqual(result["drains"]["stderr"]["exception_type"], type(error).__name__[:128])

    def output_failure(self, method):
        original_open = Path.open

        class BrokenOutput:
            def __init__(self, raw):
                self.raw = raw

            def write(self, data):
                if method == "write":
                    raise ValueError("output write failed")
                return self.raw.write(data)

            def flush(self):
                if method == "flush":
                    raise ValueError("output flush failed")
                return self.raw.flush()

            def close(self):
                self.raw.close()

        def open_output(path, *args, **kwargs):
            raw = original_open(path, *args, **kwargs)
            return BrokenOutput(raw) if path.name == "stderr.log" and args == ("xb",) else raw

        with tempfile.TemporaryDirectory() as root, patch.object(Path, "open", open_output), \
                patch.object(worker.threading, "excepthook") as escaped:
            result, _, run = self.run_mock(root)
            escaped.assert_not_called()
            self.assertIn("log failure", result["failure"])
            self.assertFalse(result["pipes_eof"])
            self.assertFalse(result["pcm_verified"])
            self.assertEqual(result["drains"]["stderr"], {"normal_return": False, "exception_type": "ValueError"})
            self.assertLessEqual((run / "stderr.log").stat().st_size, 32768)

    def test_output_write_exception_refused(self):
        self.output_failure("write")

    def test_output_flush_exception_refused(self):
        self.output_failure("flush")

    def test_provider_caught_oserror_cannot_qualify_normal_eof(self):
        with tempfile.TemporaryDirectory() as root:
            process = FakeProcess()
            process.stderr.read = lambda _: (_ for _ in ()).throw(OSError("pipe failed"))
            result, _, _ = self.run_mock(root, process)
            self.assertFalse(result["pipes_eof"])
            self.assertFalse(result["pcm_verified"])
            self.assertEqual(result["drains"]["stderr"], {"normal_return": False, "exception_type": None})

    def test_dead_thread_without_normal_return_refused(self):
        class NeverRan:
            def __init__(self, **kwargs):
                pass
            def start(self):
                pass
            def join(self, timeout):
                pass
            def is_alive(self):
                return False
        with tempfile.TemporaryDirectory() as root, patch.object(worker.threading, "Thread", NeverRan):
            result, _, _ = self.run_mock(root)
            self.assertIn("EOF", result["failure"])
            self.assertFalse(result["pipes_eof"])
            self.assertFalse(result["pcm_verified"])
            self.assertFalse(any(item["normal_return"] for item in result["drains"].values()))

    def test_changed_pcm_refused(self):
        with tempfile.TemporaryDirectory() as root:
            result, _, _ = self.run_mock(root, corrupt=True)
            self.assertEqual(result["failure"], "PCM hash mismatch")

    def test_deadline_failure_does_not_kill_by_pid(self):
        with tempfile.TemporaryDirectory() as root, patch.object(worker.time, "monotonic", side_effect=[0, 11]):
            result, _, _ = self.run_mock(root, FakeProcess(running=True))
            self.assertIn("deadline", result["failure"])
            self.assertIsNone(result["native_exit_code"])
            self.assertFalse(result["pipes_eof"])

    def test_open_pipe_refused(self):
        held_streams = []
        class OpenPipe:
            def __init__(self, **kwargs):
                held_streams.append(kwargs["args"][2])
            def start(self):
                pass
            def join(self, timeout):
                pass
            def is_alive(self):
                return True
        with tempfile.TemporaryDirectory() as root, patch.object(worker.threading, "Thread", OpenPipe):
            try:
                result, _, _ = self.run_mock(root)
            finally:
                for stream in held_streams:
                    stream.close()
            self.assertIn("EOF", result["failure"])
            self.assertFalse(result["pcm_verified"])

    def test_existing_output_refused_before_launch(self):
        with tempfile.TemporaryDirectory() as root:
            plan, _, run = self.fixture(root)
            (run / "decoded.wav").write_bytes(b"existing")
            with patch.object(worker.subprocess, "Popen") as launch, self.assertRaisesRegex(ValueError, "fresh WAV"):
                worker.decode(plan, drain.copy_bounded)
            launch.assert_not_called()
            self.assertEqual((run / "decoded.wav").read_bytes(), b"existing")

    def test_argument_drift_refused_before_launch(self):
        with tempfile.TemporaryDirectory() as root:
            plan, _, _ = self.fixture(root)
            plan["CodecArguments"].insert(0, "-y")
            with patch.object(worker.subprocess, "Popen") as launch, self.assertRaisesRegex(ValueError, "arguments"):
                worker.decode(plan, drain.copy_bounded)
            launch.assert_not_called()

    def test_codec_pin_drift_refused_before_launch(self):
        with tempfile.TemporaryDirectory() as root:
            plan, _, _ = self.fixture(root)
            with patch.object(worker, "file_hash", return_value="0" * 64), \
                    patch.object(worker.subprocess, "Popen") as launch, self.assertRaisesRegex(ValueError, "pinned"):
                worker.decode(plan, drain.copy_bounded)
            launch.assert_not_called()

    def test_wrong_wave_metadata_and_trailing_refused(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "input.wav"
            for offset in (22, 24, 34):
                data = bytearray(original_wave())
                data[offset] ^= 1
                path.write_bytes(data)
                with self.subTest(offset=offset), self.assertRaises((ValueError, worker.wave.Error)):
                    worker.read_wave(path)
            path.write_bytes(original_wave() + b"extra")
            with self.assertRaisesRegex(ValueError, "closure"):
                worker.read_wave(path)


if __name__ == "__main__":
    unittest.main()
