"""Protocol/pipe simulations only: never starts Popen, CDB or the fixture."""
import hashlib
import io
from pathlib import Path
import queue
import threading
import unittest
from unittest.mock import Mock

import capture
import cdb_transport as transport
from test_rig_abi import witness


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.spec = {"mode": "fixture", "nonce": "a" * 32, "lease_token": "synthetic-lease",
                     "python": "C:/synthetic/python.exe", "python_sha256": "b" * 64,
                     "fixture_sha256": hashlib.sha256(Path(__file__).with_name("debug_fixture.py").read_bytes()).hexdigest(),
                     "cdb": "C:/synthetic/cdb.exe"}
        self.manifest = {"schema": "iw7.rig-watch-fixture/1", "nonce": "a" * 32,
                         "pid": 0x1234, "xsurface": "0x20000", "xmodelsurfs": "0x30000",
                         "creation_utc": "2026-10-12T00:00:00.0000000Z", "created_filetime": 1}
        self.io = Mock()
        self.files = {}
        self.protocol = transport.FixtureProtocol(self.spec, Path("synthetic"), self.io,
            read_json=lambda _: self.manifest,
            write_json=lambda path, data: self.files.__setitem__(path.name, data),
            write_bytes=lambda path, data: self.files.__setitem__(path.name, data))
        self.raw = b"CDB synthetic banner\n0:000> "

    def reach_armed(self):
        self.protocol.step(self.raw)
        self.raw += b"bl\n0:000> "
        self.protocol.step(self.raw)
        self.raw += b"g\nBreakpoint exception\n0:000> "
        self.protocol.step(self.raw)
        self.raw += b"probe\nRIG58_PROBE " + b"a" * 32 + b" pid=1234 rip=140001000 code=9090909090909090\n0:000> "
        self.protocol.step(self.raw)
        arm = witness().split(b"RIG58 " + b"a" * 32 + b" WRITE")[0]
        self.raw += b"arm commands\n" + arm + b"0:000> "
        return self.protocol.step(self.raw)

    def test_full_fixture_protocol_seals_known_write(self):
        event = self.reach_armed()
        self.assertEqual(event["Status"], "ArmedStopped")
        self.assertTrue(event["BreakpointChecked"])
        self.assertEqual(self.io.send.call_count, 4)
        self.protocol.step(self.raw)  # No continuation request: must remain parked.
        self.assertEqual(self.io.send.call_count, 4)
        self.protocol.step(self.raw, {"Nonce": self.spec["nonce"], "Command": "continue-once"})
        self.assertEqual(self.io.send.call_args.args, ("g\n",))
        write = b"RIG58 " + b"a" * 32 + b" WRITE"
        self.raw += b"g\n" + write + witness().split(write)[1] + b"0:000> "
        event = self.protocol.step(self.raw)
        self.assertEqual(event["Status"], "CaptureStopped")
        self.assertEqual(self.files["sealed.log"], self.raw)
        self.assertTrue(self.files["witness.json"]["fixture_only"])
        self.assertFalse(self.files["witness.json"]["semantic_acceptance"])

    def test_breakpoint_ack_required(self):
        self.reach_armed()
        self.protocol.phase = "arm"
        raw = self.raw.replace(b"BP_PRESENT", b"BP_ABSENT")
        with self.assertRaises(ValueError):
            self.protocol.step(raw)

    def test_foreign_continuation_cannot_resume(self):
        self.reach_armed()
        with self.assertRaises(ValueError):
            self.protocol.step(self.raw, {"Nonce": "0" * 32, "Command": "continue-once"})
        self.assertFalse(self.protocol.continued)

    def test_fixture_pid_mismatch(self):
        self.manifest["pid"] = 99
        with self.assertRaises(ValueError):
            self.reach_armed()

    def test_existing_breakpoint_refused_before_startup(self):
        self.protocol.step(self.raw)
        self.raw += b"bl\n 3 e 00000000`00020058 w 8\n0:000> "
        with self.assertRaises(ValueError):
            self.protocol.step(self.raw)
        self.assertEqual(self.io.send.call_count, 1)

    def test_error_and_guard_output_refused(self):
        for line in (b"Syntax error", b"Bad register", b"RIG58_REFUSED_PID"):
            with self.subTest(line=line), self.assertRaises(ValueError):
                self.protocol.step(line + b"\n0:000> ")

    def test_prompt_must_be_new_and_at_tail(self):
        self.assertFalse(transport.has_prompt(b"0:000> command\nmore output"))
        self.assertFalse(transport.has_prompt(self.raw, len(self.raw)))
        self.assertTrue(transport.has_prompt(self.raw))

    def test_retail_launcher_is_absent(self):
        spec = dict(self.spec, mode="retail")
        with self.assertRaises(ValueError):
            transport.fixture_command(spec, Path("synthetic"))
        command = transport.fixture_command(self.spec, Path("synthetic"))
        self.assertNotIn("-p", command)
        self.assertNotIn("-pn", command)
        self.assertNotIn("-g", command)
        self.assertIn("-cf", command)
        self.assertIn("-noshell", command)
        self.assertIn("-netsyms:no", command)

    def test_fixture_cannot_impersonate_real_rig_schema(self):
        event = self.reach_armed()
        self.assertTrue(event["FixtureOnly"])
        context = self.files["context.json"]
        self.assertIsNone(context["ff_sha256"])
        context["schema"] = capture.SCHEMA
        with self.assertRaises(ValueError):
            capture.validate(context)


class PipeTests(unittest.TestCase):
    def setUp(self):
        # Do not call the constructor: no thread or process starts in these tests.
        self.pipe = transport.PipeIO.__new__(transport.PipeIO)
        self.pipe.process = Mock()
        self.pipe.process.poll.return_value = None
        self.pipe.events = queue.Queue(maxsize=64)
        self.pipe.commands = queue.Queue(maxsize=4)
        self.pipe.failure = threading.Event()
        self.pipe.error = None
        self.pipe.raw = {"stdout": bytearray(), "stderr": bytearray()}
        self.pipe.eof = set()

    def test_nonblocking_pump_and_send(self):
        self.pipe.events.put_nowait(("stdout", b"hello"))
        self.assertEqual(self.pipe.pump(), b"hello")
        self.pipe.send("g\n")
        self.assertEqual(self.pipe.commands.get_nowait(), b"g\n")

    def test_eof_not_success(self):
        self.pipe.events.put_nowait(("stdout", b""))
        with self.assertRaises(ValueError):
            self.pipe.pump()

    def test_combined_cap(self):
        self.pipe.raw["stdout"] = bytearray(b"x" * (capture.MAX_LOG - 1))
        self.pipe.events.put_nowait(("stderr", b"xx"))
        with self.assertRaises(ValueError):
            self.pipe.pump()
        self.assertLessEqual(sum(map(len, self.pipe.raw.values())), capture.MAX_LOG)

    def test_stdin_backpressure_fails_without_blocking(self):
        for _ in range(5):
            self.pipe.send("g\n")
        self.assertTrue(self.pipe.failure.is_set())

    def test_drain_exception_surfaces(self):
        stream = Mock()
        stream.read1.side_effect = OSError("synthetic pipe error")
        self.pipe.drain("stdout", stream)
        with self.assertRaises(ValueError):
            self.pipe.pump()

    def test_debugger_exit_surfaces(self):
        self.pipe.process.poll.return_value = 0
        with self.assertRaises(ValueError):
            self.pipe.pump()


if __name__ == "__main__":
    unittest.main()
