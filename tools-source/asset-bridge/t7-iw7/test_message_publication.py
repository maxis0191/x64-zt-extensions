"""Source wiring and explicit scheduling model; never executes native code."""
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import unittest

import prepare_message_publication as p
from test_catalog_callers import render_format


class PublicationModel:
    """Small behavioral oracle with atomic state transitions and a fake clock.

    It tests schedules without pretending to execute MSVC/Win32. Operations
    correspond to the reviewed source; source tests bind critical transitions.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.phase, self.publication, self.closure = "idle", "pending", "not_closed"
        self.claims, self.writes = 0, 0

    def claim(self):
        with self.lock:
            if self.phase != "idle":
                return False
            self.phase = "capturing"
            self.claims += 1
            return True

    def finish(self, requested=50, written=50, ok=True, format_ok=True):
        with self.lock:
            if not format_ok:
                self.publication = "format_failed"
            else:
                self.writes += 1
                self.publication = "written" if ok and written == requested else "failed"
            if self.publication == "written" and self.phase == "capturing":
                self.phase = "published"

    def close(self, tick=lambda n: n, progress=lambda n: None):
        with self.lock:
            previous, self.phase = self.phase, "closing"
            if self.closure == "not_closed":
                self.closure = "close_pending"
        result, polls, sleeps = "incomplete", 0, 0
        if previous == "idle":
            result = "no_capture"
        else:
            start = tick(0)
            for poll in range(100):
                polls += 1
                with self.lock:
                    terminal, publication = self.closure, self.publication
                if terminal != "close_pending":
                    result = terminal
                    break
                if publication != "pending":
                    result = "published" if publication == "written" else "publish_failed"
                    break
                if tick(poll) - start >= 100:
                    break
                sleeps += 1
                progress(poll)
        with self.lock:
            if self.closure == "close_pending":
                self.closure = result
            return self.closure, polls, sleeps


class SchedulingTests(unittest.TestCase):
    def test_eight_simultaneous_observers_admit_exactly_one(self):
        model = PublicationModel()
        barrier = threading.Barrier(9)
        def observer():
            barrier.wait(timeout=2)
            if model.claim():
                model.finish()
        threads = [threading.Thread(target=observer) for _ in range(8)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=2)
        for thread in threads:
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
        self.assertEqual((model.claims, model.writes, model.phase), (1, 1, "published"))
        self.assertEqual(model.close(), ("published", 1, 0))

    def test_close_before_capture_admits_nothing(self):
        model = PublicationModel()
        self.assertEqual(model.close(), ("no_capture", 0, 0))
        self.assertFalse(model.claim())
        self.assertEqual(model.close(), ("no_capture", 1, 0))
        self.assertEqual(model.writes, 0)

    def test_blocked_writer_cannot_extend_close_and_late_success_cannot_reopen(self):
        model = PublicationModel()
        entered, release = threading.Event(), threading.Event()
        def writer():
            if model.claim():
                entered.set()
                if release.wait(timeout=2):
                    model.finish()
        thread = threading.Thread(target=writer)
        thread.start()
        self.assertTrue(entered.wait(timeout=1))
        try:
            self.assertEqual(model.close(tick=lambda n: 2 * n), ("incomplete", 51, 50))
            self.assertFalse(model.claim())
            self.assertEqual(model.writes, 0)
        finally:
            release.set()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual((model.phase, model.publication), ("closing", "written"))
        self.assertEqual(model.close(), ("incomplete", 1, 0))

    def test_frozen_clock_is_still_bounded_by_poll_count(self):
        model = PublicationModel()
        self.assertTrue(model.claim())
        self.assertEqual(model.close(tick=lambda n: 0), ("incomplete", 100, 100))

    def test_completion_during_close_and_all_publish_failures(self):
        for ok, written, formatted, expected in ((True, 50, True, "published"),
                (False, 0, True, "publish_failed"), (False, 50, True, "publish_failed"),
                (True, 49, True, "publish_failed"), (True, 0, False, "publish_failed")):
            with self.subTest(ok=ok, written=written, formatted=formatted):
                model = PublicationModel()
                model.claim()
                def progress(n):
                    if n == 2:
                        model.finish(written=written, ok=ok, format_ok=formatted)
                self.assertEqual(model.close(progress=progress), (expected, 4, 3))
                self.assertFalse(model.claim())
                self.assertEqual(model.phase, "closing")

    def test_all_complete_capture_vs_close_interleavings_preserve_terminal_gate(self):
        # Enumerate the only atomic orderings with claim before completion.
        for order in itertools.permutations(("claim", "complete", "close")):
            if order.index("complete") < order.index("claim"):
                continue
            model = PublicationModel()
            claimed = False
            for event in order:
                if event == "claim":
                    claimed = model.claim()
                elif event == "complete" and claimed:
                    model.finish()
                elif event == "close":
                    model.close(tick=lambda n: 100 * n)
            self.assertEqual(model.phase, "closing")
            self.assertLessEqual(model.claims, 1)
            self.assertFalse(model.claim())


class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = p.NATIVE.read_text()

    def test_preformatted_bounded_record_and_one_verified_os_write(self):
        s = self.native
        self.assertIn("char record[1024]{};", s)
        self.assertIn("std::snprintf(record, sizeof(record)", s)
        self.assertEqual(s.count("WriteFile("), 1)
        self.assertIn("length <= 0 || length >= 1024", s)
        self.assertIn("catalog_message_written_bytes == catalog_message_requested_bytes", s)
        self.assertIn("!ok ? message_write_failed", s)
        self.assertNotIn("std::fprintf", s)
        self.assertNotIn("std::fflush", s)
        self.assertNotIn("strlen", s)

    def test_claim_and_publication_use_compare_exchange_and_never_reopen(self):
        s = self.native
        self.assertIn("InterlockedCompareExchange(&catalog_message_state, message_capturing, message_idle)", s)
        self.assertIn("InterlockedCompareExchange(&catalog_message_state, message_published, message_capturing)", s)
        self.assertIn("InterlockedExchange(&catalog_message_publication_result, result)", s)
        complete = s.split("void catalog_message_complete", 1)[1].split("void catalog_message_publish", 1)[0]
        self.assertLess(complete.index("catalog_message_publication_result"), complete.index("catalog_message_state"))
        self.assertNotIn("catalog_message_seen", s)

    def test_close_has_no_io_or_join_and_retains_time_and_iteration_caps(self):
        close = self.native.split("LONG catalog_message_close()", 1)[1].split("void catalog_message_observe", 1)[0]
        for forbidden in ("printf", "WriteFile", "fflush", "WaitFor", "Join", "CriticalSection", "mutex", "__try"):
            self.assertNotIn(forbidden, close)
        self.assertIn("catalog_message_close_budget_ms = 100", self.native)
        self.assertIn("catalog_message_close_max_polls = 100", self.native)
        self.assertIn("poll < catalog_message_close_max_polls", close)
        self.assertLess(close.index("message_closing)"), close.index("for (unsigned poll"))
        self.assertLess(close.index("GetTickCount64() - start >="), close.index("Sleep(1)"))
        self.assertLess(close.index("GetLastError()"), close.index("InterlockedExchange"))
        self.assertIn("SetLastError(saved_error);", close)
        self.assertIn("result = message_close_incomplete", close)

    def test_exit_wrapper_preserves_code_last_error_and_non_catalogue_flush(self):
        self.assertEqual(p.WRAPPER.count("std::quick_exit(code)"), 1)
        self.assertIn("else std::fflush(nullptr);", p.WRAPPER)
        self.assertIn("if (catalog_trace_enabled)", p.WRAPPER)
        self.assertLess(p.WRAPPER.index("GetLastError()"), p.WRAPPER.index("catalog_message_close()"))
        self.assertLess(p.WRAPPER.index("SetLastError(saved_error)"), p.WRAPPER.index("std::quick_exit(code)"))

    def test_full_format_fits_unchanged_8192_byte_stderr_contract(self):
        fmt = re.search(r'std::snprintf\(record, sizeof\(record\), "([^"]+)"', self.native).group(1)
        size = len(render_format(fmt, [4294967295, "S" * 32, 384, 384, 384, 1, 4294967295, "FF" * 384]))
        self.assertEqual(size, 948)
        self.assertLess(size, 1024)
        self.assertLessEqual(6911 + 135 + size, 8192)

    def test_historical_build_reuse_refuses_changed_cli(self):
        import prepare_build
        from test_build_commands import ReuseTests
        prior, receipt, payloads, run = ReuseTests().fixture()
        payloads["prepared/main.cpp"] = b"new message publication source"
        payloads["prepared/zonetool.cpp"] = b"new two-exit CLI source"
        with self.assertRaisesRegex(ValueError, "differs from compiled prior stage"):
            prepare_build.reuse_compilation(prior, json.dumps(receipt).encode(), payloads, run,
                                           recompile_main=True, catalog_trace=True)


@unittest.skipUnless(os.environ.get("IW7_T7_SOURCE"), "Retained source-only path not supplied")
class WiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.environ["IW7_T7_SOURCE"])
        cls.outputs, cls.report = p.render(cls.source)

    def test_only_two_cli_exits_replaced_and_no_engine_exit_hook_changed(self):
        _, old = p.prepare_cli.render(self.source)
        before = p.legacy.wire_message_main(old[p.prepare_cli.PATHS[0]])
        main, cli = (self.outputs[n].decode() for n in ("main.cpp", "zonetool.cpp"))
        old_hook = before.split("void WINAPI exit_hook(", 1)[1].split("\n\t}", 1)[0]
        new_hook = main.split("void WINAPI exit_hook(", 1)[1].split("\n\t}", 1)[0]
        self.assertEqual(old_hook, new_hook)
        for code in ("EXIT_SUCCESS", "EXIT_FAILURE"):
            self.assertEqual(cli.count("t7_catalog_message_cli_exit(" + code + ");"), 1)
        restored = cli.replace("\n" + p.DECLARATION, "")
        for code in ("EXIT_SUCCESS", "EXIT_FAILURE"):
            restored = restored.replace("t7_catalog_message_cli_exit(" + code + ");",
                       "std::fflush(nullptr);\n\t\t\t\tstd::quick_exit(" + code + ");")
        self.assertEqual(restored, old[p.prepare_cli.PATHS[1]])
        forward = p.legacy.MESSAGE_SUPPORT.split("uintptr_t catalog_message_forward(", 1)[1].split("struct catalog_message_install", 1)[0]
        self.assertIn(forward, main)

    def test_report_requires_both_fresh_objects_and_no_build_claim(self):
        self.assertEqual(self.report["RequiredFreshStages"], ["main", "zonetool11", "link"])
        for key in ("HistoricalMainOnlyProfileCompatible", "BuildPlanCreated", "NativeExecuted", "CandidateCreated", "RuntimeVerified", "Ready"):
            self.assertIs(self.report[key], False)
        self.assertLessEqual(sum(map(len, self.outputs.values())), 1024 * 1024)
        for name, pin in self.report["Outputs"].items():
            self.assertEqual(hashlib.sha256(self.outputs[name]).hexdigest(), pin["SHA256"])

    def test_second_overlay_and_source_anchor_drift_are_refused(self):
        with self.assertRaises(ValueError):
            p.overlay(self.outputs["main.cpp"].decode(), self.outputs["zonetool.cpp"].decode())
        _, old = p.prepare_cli.render(self.source)
        main = p.legacy.wire_message_main(old[p.prepare_cli.PATHS[0]])
        with self.assertRaises(ValueError):
            p.overlay(main, old[p.prepare_cli.PATHS[1]].replace("std::quick_exit(EXIT_FAILURE)", "changed_exit(EXIT_FAILURE)"))

    def test_preparation_is_source_only_bounded_and_refuses_existing_root(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "prepared"
            report = p.prepare(self.source, out)
            self.assertEqual({n.name for n in out.iterdir()}, set(self.outputs))
            self.assertEqual(report, self.report)
            with self.assertRaises(ValueError):
                p.prepare(self.source, out)


if __name__ == "__main__":
    unittest.main()
