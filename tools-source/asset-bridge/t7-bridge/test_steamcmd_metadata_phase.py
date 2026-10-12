"""Light refusal/boundary checks only; never starts SteamCMD or a native job."""
import io
import hashlib
import json
import tempfile
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import steamcmd_metadata_phase as phase


class MetadataPhaseTests(unittest.TestCase):
    def test_exact_metadata_command_has_no_payload_or_personal_login(self):
        self.assertEqual(phase.ARGUMENTS, (
            "+@ShutdownOnFailedCommand", "1", "+@NoPromptForPassword", "1",
            "+login", "anonymous", "+app_info_update", "1",
            "+app_info_print", "545990", "+quit"))

    def test_nested_files_count_towards_same_total(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "cache").mkdir()
            (root / "steamcmd.exe").write_bytes(b"123")
            (root / "cache" / "data").write_bytes(b"45678")
            self.assertEqual(phase.tree_bytes(root), 8)

    def test_disk_limit_reserves_receipt_space(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").write_bytes(b"123456789")
            with patch.object(phase, "DISK_LIMIT", 10), patch.object(phase, "METADATA_RESERVE", 2):
                with self.assertRaisesRegex(ValueError, "512 MiB"):
                    phase.tree_bytes(root)

    def test_reparse_file_rejected_without_following_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").write_bytes(b"small")
            # Attribute mask injection avoids creating a real link or requiring
            # admin/developer-mode privileges; no contents outside root are read.
            original = phase.stat.FILE_ATTRIBUTE_REPARSE_POINT
            with patch.object(phase.stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x20):
                with self.assertRaisesRegex(ValueError, "Reparse"):
                    phase.tree_bytes(root)
            self.assertEqual(phase.stat.FILE_ATTRIBUTE_REPARSE_POINT, original)

    def test_existing_reviewed_output_helper_is_bounded(self):
        helper = phase.output_copy_function()
        event = threading.Event()
        destination = io.BytesIO()
        helper(io.BytesIO(b"too much output"), destination, event, 4)
        self.assertTrue(event.is_set())
        self.assertEqual(destination.getvalue(), b"too ")

    def test_output_worker_marks_every_failure_before_thread_exit(self):
        for error in (OSError, ValueError, SystemExit):
            with self.subTest(error=error.__name__):
                event = threading.Event()

                def broken_copy(*_):
                    raise error("injected output failure")

                worker = threading.Thread(target=phase.guarded_copy,
                                          args=(broken_copy, None, None, event))
                worker.start()
                worker.join(2)
                self.assertFalse(worker.is_alive())
                self.assertTrue(event.is_set())

    def run_simulated_phase(self, exit_time=0, drain_seconds=0, output_error=None):
        """Exercise the actual main path, replacing only time/child/pipe threads."""
        clock = [0]
        destinations = []

        class PhaseFailed(BaseException):
            pass

        class SimulatedWorker:
            def __init__(self, target, args, daemon):
                self.target, self.args = target, args
                destinations.append(args[2])

            def start(self):
                self.target(*self.args)

            def join(self, _timeout):
                clock[0] += drain_seconds

            def is_alive(self):
                return False

        def child_poll():
            clock[0] = max(clock[0], exit_time)
            return 0

        child = SimpleNamespace(pid=123, returncode=0, poll=child_poll,
                                stdout=io.BytesIO(b"metadata"), stderr=io.BytesIO())
        helper = phase.output_copy_function()
        if output_error:
            def helper(*_):
                raise output_error("injected copy failure")

        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            root = Path(temporary).resolve()
            bootstrap = b"x" * 1687464  # Test data only; Popen is always mocked.
            (root / "steamcmd.exe").write_bytes(bootstrap)
            (root / "steamcmd.zip").write_bytes(b"test zip")
            for target, value in (
                    ("sys.argv", ["phase", "--tool-root", str(root)]),
                    ("steamcmd_metadata_phase.BOOTSTRAP_SHA256", hashlib.sha256(bootstrap).hexdigest()),
                    ("steamcmd_metadata_phase.time.monotonic", lambda: clock[0]),
                    ("steamcmd_metadata_phase.threading.Thread", SimulatedWorker),
                    ("steamcmd_metadata_phase.output_copy_function", lambda: helper)):
                stack.enter_context(patch(target, value))
            launch = stack.enter_context(patch.object(phase.subprocess, "Popen", return_value=child))
            abort = stack.enter_context(patch.object(phase.os, "_exit", side_effect=PhaseFailed))
            failed = False
            try:
                self.assertEqual(phase.main(), 0)
            except PhaseFailed:
                failed = True
                abort.assert_called_once_with(2)
            finally:
                # Production abort closes these through OS process teardown.
                # Simulated abort must close them explicitly before temp cleanup.
                for destination in destinations:
                    destination.close()
            launch.assert_called_once()
            result = json.loads((root / "metadata-attempt-a" / "phase.json").read_text("utf-8"))
            return failed, result

    def test_exit_zero_after_deadline_is_failure(self):
        failed, result = self.run_simulated_phase(exit_time=phase.DEADLINE_SECONDS)
        self.assertTrue(failed)
        self.assertEqual(result["steamcmd_exit_code"], 0)
        self.assertEqual(result["failure"], "phase deadline")

    def test_output_drain_crossing_deadline_is_failure(self):
        failed, result = self.run_simulated_phase(exit_time=179, drain_seconds=0.6)
        self.assertTrue(failed)
        self.assertEqual(result["failure"], "phase deadline")

    def test_thread_failure_cannot_produce_phase_success(self):
        failed, result = self.run_simulated_phase(output_error=SystemExit)
        self.assertTrue(failed)
        self.assertEqual(result["failure"], "output error or inherited pipe remains open")

    def test_timely_exit_and_complete_output_can_succeed(self):
        failed, result = self.run_simulated_phase(exit_time=1, drain_seconds=0.1)
        self.assertFalse(failed)
        self.assertIsNone(result["failure"])

    def test_extra_files_fail_before_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "owner-state").write_bytes(b"preserve")
            with patch("sys.argv", ["phase", "--tool-root", str(root)]), \
                    patch.object(phase.subprocess, "Popen") as launch:
                with self.assertRaisesRegex(ValueError, "only the prepared ZIP"):
                    phase.main()
                launch.assert_not_called()
            self.assertEqual((root / "owner-state").read_bytes(), b"preserve")

    def test_bad_bootstrap_fails_before_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "steamcmd.exe").write_bytes(b"wrong")
            (root / "steamcmd.zip").write_bytes(b"wrong")
            with patch("sys.argv", ["phase", "--tool-root", str(root)]), \
                    patch.object(phase.subprocess, "Popen") as launch:
                with self.assertRaisesRegex(ValueError, "bootstrap identity"):
                    phase.main()
                launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
