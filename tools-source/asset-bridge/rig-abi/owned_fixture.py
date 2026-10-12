"""New suspended fixture only; every operation uses its original creation handles.

Import and fake-kernel tests do not load WinDLL or create a process. There is no
PID-input/open/adoption API. The controller still proves ORIGINAL job membership.
"""
import ctypes
from pathlib import Path
import subprocess


class StartupInfo(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_uint32), ("reserved", ctypes.c_wchar_p),
                ("desktop", ctypes.c_wchar_p), ("title", ctypes.c_wchar_p),
                ("x", ctypes.c_uint32), ("y", ctypes.c_uint32),
                ("xsize", ctypes.c_uint32), ("ysize", ctypes.c_uint32),
                ("xchars", ctypes.c_uint32), ("ychars", ctypes.c_uint32),
                ("fill", ctypes.c_uint32), ("flags", ctypes.c_uint32),
                ("show", ctypes.c_uint16), ("reserved_bytes", ctypes.c_uint16),
                ("reserved_data", ctypes.c_void_p), ("stdin", ctypes.c_void_p),
                ("stdout", ctypes.c_void_p), ("stderr", ctypes.c_void_p)]


class ProcessInfo(ctypes.Structure):
    _fields_ = [("process", ctypes.c_void_p), ("thread", ctypes.c_void_p),
                ("pid", ctypes.c_uint32), ("tid", ctypes.c_uint32)]


class FileTime(ctypes.Structure):
    _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]


class OwnedFixture:
    FLAGS = 0x08000000 | 0x00004000 | 0x4  # NO_WINDOW, BELOW_NORMAL, SUSPENDED

    def __init__(self, kernel, ffi=ctypes):
        self.kernel, self.ffi = kernel, ffi
        self.info = ProcessInfo()
        self.created_filetime = None
        self.prepared = False
        self.prepare_attempted = False
        self.resumed = False
        self.resume_attempted = False
        self.stop_attempted = False
        self.closed = False
        if ffi.sizeof(ffi.c_void_p) != 8 or ctypes.sizeof(StartupInfo) != 104 or ctypes.sizeof(ProcessInfo) != 24:
            raise ValueError("Windows x64 creation ABI required")
        signatures = {
            "CreateProcessW": ([ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_void_p,
                                ctypes.c_int, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_wchar_p,
                                ctypes.POINTER(StartupInfo), ctypes.POINTER(ProcessInfo)], ctypes.c_int),
            "GetProcessId": ([ctypes.c_void_p], ctypes.c_uint32),
            "GetThreadId": ([ctypes.c_void_p], ctypes.c_uint32),
            "GetProcessTimes": ([ctypes.c_void_p] + [ctypes.POINTER(FileTime)] * 4, ctypes.c_int),
            "WaitForSingleObject": ([ctypes.c_void_p, ctypes.c_uint32], ctypes.c_uint32),
            "GetExitCodeProcess": ([ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)], ctypes.c_int),
            "ResumeThread": ([ctypes.c_void_p], ctypes.c_uint32),
            "TerminateProcess": ([ctypes.c_void_p, ctypes.c_uint32], ctypes.c_int),
            "CloseHandle": ([ctypes.c_void_p], ctypes.c_int),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(kernel, name)
            function.argtypes, function.restype = arguments, result

    def checked(self, name, *args):
        self.ffi.set_last_error(0)
        result = getattr(self.kernel, name)(*args)
        error = self.ffi.get_last_error()
        if not result:
            raise OSError(f"{name}: ApiReturn={result} LastError={error}")
        return result

    def prepare(self, spec, root):
        if self.prepare_attempted or self.info.process or self.closed or spec.get("mode") != "fixture":
            raise ValueError("one new fixture creation only")
        self.prepare_attempted = True
        command = [spec["python"], "-I", "-B", str(Path(__file__).with_name("debug_fixture.py")),
                   "--manifest", str(root / "fixture.json"), "--nonce", spec["nonce"]]
        startup = StartupInfo()
        startup.cb = ctypes.sizeof(startup)
        text = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
        # No breakaway, alternate parent/token, inherited handles or debugger flag.
        self.checked("CreateProcessW", spec["python"], text, None, None, 0, self.FLAGS,
                     None, str(root), ctypes.byref(startup), ctypes.byref(self.info))
        self.prepared = True  # retain returned handles even if identity validation fails
        if not self.info.process or not self.info.thread or not self.info.pid or not self.info.tid:
            raise ValueError("complete original creation handles required")
        self.created_filetime = self._creation_time()
        return self.identity()

    def _creation_time(self):
        created, exited, kernel, user = (FileTime() for _ in range(4))
        self.checked("GetProcessTimes", self.info.process, *(ctypes.byref(x) for x in (created, exited, kernel, user)))
        value = (created.high << 32) | created.low
        if value <= 0:
            raise ValueError("positive original creation FILETIME required")
        return value

    def exited(self):
        if not self.prepared or self.closed or not self.info.process:
            raise ValueError("live retained creation handle required")
        value = self.kernel.WaitForSingleObject(self.info.process, 0)
        if value not in (0, 0x102):
            raise OSError(f"original process wait returned {value}")
        return value == 0

    def identity(self):
        if self.exited():
            raise ValueError("new owned fixture already exited")
        if self.checked("GetProcessId", self.info.process) != self.info.pid or self.checked("GetThreadId", self.info.thread) != self.info.tid:
            raise ValueError("original creation identity differs")
        if self._creation_time() != self.created_filetime:
            raise ValueError("original creation time differs")
        return {"pid": self.info.pid, "tid": self.info.tid, "created_filetime": self.created_filetime,
                "OriginalHandles": True, "CreatedSuspended": True, "PrimaryResumed": self.resumed,
                "CreationFlags": self.FLAGS, "InheritedHandles": False}

    def resume_once(self):
        self.identity()
        if self.resume_attempted:
            raise ValueError("original primary thread resume already attempted")
        self.resume_attempted = True
        self.ffi.set_last_error(0)
        previous = self.kernel.ResumeThread(self.info.thread)
        error = self.ffi.get_last_error()
        if previous != 1:
            raise OSError(f"ResumeThread: PreviousSuspendCount={previous} LastError={error} LastErrorMeaningful={previous == 0xffffffff}")
        self.resumed = True
        return previous

    def request_stop(self):
        if self.prepared and not self.closed and not self.exited() and not self.stop_attempted:
            self.stop_attempted = True
            self.checked("TerminateProcess", self.info.process, 122)

    def close_after_exit(self):
        if not self.prepared:
            return {"Created": False, "Closed": True, "StopAttempted": False}
        if self.closed or not self.exited():
            raise ValueError("original created process must have exited before closing handles")
        code = ctypes.c_uint32()
        self.checked("GetExitCodeProcess", self.info.process, ctypes.byref(code))
        receipt = {"Created": True, "Closed": True, "StopAttempted": self.stop_attempted,
                   "PID": self.info.pid, "CreatedFileTime": self.created_filetime, "ExitCode": code.value,
                   "OriginalHandles": True}
        self.checked("CloseHandle", self.info.thread)
        self.info.thread = None
        self.checked("CloseHandle", self.info.process)
        self.info.process = None
        self.closed = True
        return receipt
