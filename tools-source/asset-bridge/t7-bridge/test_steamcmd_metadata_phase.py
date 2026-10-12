"""Light refusal/boundary checks only; never starts SteamCMD or a native job."""
import io
import tempfile
import threading
import unittest
from pathlib import Path
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
