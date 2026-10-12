"""Fake Win32 functions only: no WinDLL, Popen, fixture, process or thread launch."""
import ctypes
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from owned_fixture import OwnedFixture, ProcessInfo, StartupInfo


class OwnedTests(unittest.TestCase):
    def setUp(self):
        self.stopped = False
        self.ffi = SimpleNamespace(sizeof=ctypes.sizeof, c_void_p=ctypes.c_void_p,
                                   set_last_error=Mock(), get_last_error=Mock(return_value=0))
        def create(app, command, pa, ta, inherit, flags, env, cwd, startup, result):
            result._obj.process, result._obj.thread = 0x100000008, 0x200000009
            result._obj.pid, result._obj.tid = 4660, 99
            return 1
        def times(handle, created, *rest):
            created._obj.low, created._obj.high = 123, 456
            return 1
        def terminate(handle, code):
            self.stopped = True
            return 1
        def exit_code(handle, value):
            value._obj.value = 122
            return 1
        self.kernel = SimpleNamespace(CreateProcessW=Mock(side_effect=create), GetProcessId=Mock(return_value=4660),
            GetThreadId=Mock(return_value=99), GetProcessTimes=Mock(side_effect=times),
            WaitForSingleObject=Mock(side_effect=lambda *_: 0 if self.stopped else 0x102),
            ResumeThread=Mock(return_value=1), TerminateProcess=Mock(side_effect=terminate),
            CloseHandle=Mock(return_value=1), GetExitCodeProcess=Mock(side_effect=exit_code))
        self.owner = OwnedFixture(self.kernel, self.ffi)
        self.spec = {"mode": "fixture", "python": "C:/owned path/python.exe", "nonce": "a" * 32}

    def prepare(self):
        return self.owner.prepare(self.spec, Path("C:/synthetic"))

    def test_creation_abi_flags_and_only_fixed_fixture_command(self):
        identity = self.prepare()
        self.assertEqual(ctypes.sizeof(StartupInfo), 104)
        self.assertEqual(ctypes.sizeof(ProcessInfo), 24)
        args = self.kernel.CreateProcessW.call_args.args
        self.assertEqual(args[0], self.spec["python"])
        self.assertEqual(args[4:7], (0, 0x08004004, None))
        self.assertIn('"C:/owned path/python.exe" -I -B ', args[1].value)
        self.assertIn("debug_fixture.py", args[1].value)
        self.assertEqual(identity["created_filetime"], (456 << 32) | 123)
        self.assertTrue(identity["OriginalHandles"])
        self.assertFalse(identity["PrimaryResumed"])
        self.assertEqual(self.kernel.CreateProcessW.restype, ctypes.c_int)
        self.assertEqual(self.kernel.ResumeThread.restype, ctypes.c_uint32)

    def test_resume_once_uses_exact_original_thread_handle(self):
        self.prepare()
        self.assertEqual(self.owner.resume_once(), 1)
        self.kernel.ResumeThread.assert_called_once_with(0x200000009)
        with self.assertRaises(ValueError):
            self.owner.resume_once()
        self.assertTrue(self.owner.resumed)

    def test_bad_suspend_counts_refuse_without_retry(self):
        for count in (0, 2, 0xffffffff):
            with self.subTest(count=count):
                self.setUp(); self.prepare()
                self.kernel.ResumeThread.return_value = count
                with self.assertRaises(OSError):
                    self.owner.resume_once()
                with self.assertRaises(ValueError):
                    self.owner.resume_once()
                self.assertFalse(self.owner.resumed)
                self.assertEqual(self.kernel.ResumeThread.call_count, 1)

    def test_changed_identity_cannot_resume(self):
        self.prepare()
        self.kernel.GetProcessId.return_value = 12
        with self.assertRaises(ValueError):
            self.owner.resume_once()
        self.kernel.ResumeThread.assert_not_called()

    def test_exited_identity_cannot_attach_or_resume(self):
        self.prepare(); self.stopped = True
        with self.assertRaises(ValueError):
            self.owner.identity()
        with self.assertRaises(ValueError):
            self.owner.resume_once()
        self.kernel.ResumeThread.assert_not_called()

    def test_failure_recovery_terminates_original_handle_not_pid(self):
        self.prepare()
        with self.assertRaises(ValueError):
            self.owner.close_after_exit()
        self.kernel.CloseHandle.assert_not_called()
        self.owner.request_stop(); self.owner.request_stop()
        self.kernel.TerminateProcess.assert_called_once_with(0x100000008, 122)
        receipt = self.owner.close_after_exit()
        self.assertEqual(receipt["ExitCode"], 122)
        self.assertTrue(receipt["Closed"])
        self.assertEqual([c.args[0] for c in self.kernel.CloseHandle.call_args_list], [0x200000009, 0x100000008])

    def test_creation_error_keeps_api_failure_distinct(self):
        self.kernel.CreateProcessW.side_effect = None
        self.kernel.CreateProcessW.return_value = 0
        self.ffi.get_last_error.return_value = 5
        with self.assertRaisesRegex(OSError, "ApiReturn=0 LastError=5"):
            self.prepare()
        self.assertFalse(self.owner.prepared)
        self.assertEqual(self.owner.close_after_exit(), {"Created": False, "Closed": True, "StopAttempted": False})
        self.kernel.TerminateProcess.assert_not_called()

    def test_identity_error_after_creation_retains_handles_for_stop(self):
        self.kernel.GetProcessTimes.side_effect = None
        self.kernel.GetProcessTimes.return_value = 0
        with self.assertRaises(OSError):
            self.prepare()
        self.assertTrue(self.owner.prepared)
        self.owner.request_stop()
        self.kernel.TerminateProcess.assert_called_once_with(0x100000008, 122)

    def test_no_second_creation_or_retail_creation(self):
        self.prepare()
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(self.kernel.CreateProcessW.call_count, 1)
        self.setUp(); self.spec["mode"] = "retail"
        with self.assertRaises(ValueError):
            self.prepare()
        self.kernel.CreateProcessW.assert_not_called()

    def test_termination_failure_never_claims_closed(self):
        self.prepare()
        self.kernel.TerminateProcess.side_effect = None
        self.kernel.TerminateProcess.return_value = 0
        with self.assertRaises(OSError):
            self.owner.request_stop()
        with self.assertRaises(ValueError):
            self.owner.close_after_exit()
        self.assertFalse(self.owner.closed)
        self.kernel.CloseHandle.assert_not_called()


if __name__ == "__main__":
    unittest.main()
