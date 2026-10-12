"""Pure diagnostic simulations: no fixture import, WinDLL, process or native call."""
import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import cdb_transport as transport


class FakeInt:
    def __init__(self, value=0):
        self.value = value


class JobProbeTests(unittest.TestCase):
    def probe(self, source, result, member, last_error, width=8):
        # Extract this one definition only; never import or call fixture.main.
        tree = ast.parse(Path(__file__).with_name(source).read_text(encoding="utf-8"))
        definition = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "query_job_membership")
        ffi = Mock()
        ffi.c_void_p = object()
        ffi.c_int = FakeInt
        ffi.POINTER.side_effect = lambda value: ("pointer", value)
        ffi.sizeof.side_effect = lambda value: width if value is ffi.c_void_p else 4
        ffi.byref.side_effect = lambda value: value
        ffi.get_last_error.return_value = last_error
        calls = []
        ffi.set_last_error.side_effect = lambda value: calls.append(("reset", value))
        kernel = Mock()
        kernel.GetCurrentProcess.return_value = 0xFFFFFFFFFFFFFFFF

        def native(handle, job, output):
            calls.append(("query", handle, job))
            output.value = member
            return result

        kernel.IsProcessInJob.side_effect = native
        namespace = {"ctypes": ffi}
        exec(compile(ast.Module(body=[definition], type_ignores=[]), source, "exec"), namespace)
        value = namespace["query_job_membership"](kernel)
        self.assertEqual(kernel.GetCurrentProcess.argtypes, [])
        self.assertIs(kernel.GetCurrentProcess.restype, ffi.c_void_p)
        self.assertEqual(kernel.IsProcessInJob.argtypes, [ffi.c_void_p, ffi.c_void_p, ("pointer", FakeInt)])
        self.assertIs(kernel.IsProcessInJob.restype, FakeInt)
        self.assertEqual(calls, [("reset", 0), ("query", 0xFFFFFFFFFFFFFFFF, None)])
        return value

    def test_api_failure_keeps_invalid_member_separate(self):
        for source in ("debug_fixture.py", "cdb_transport.py"):
            with self.subTest(source=source):
                result = self.probe(source, 0, 1, 6)
                self.assertEqual(result["ApiReturn"], 0)
                self.assertFalse(result["ApiSucceeded"])
                self.assertEqual(result["LastError"], 6)
                self.assertTrue(result["LastErrorMeaningful"])
                self.assertEqual(result["MemberValue"], 1)
                self.assertFalse(result["MemberValid"])
                self.assertIsNone(result["InAnyJob"])

    def test_successful_nonmembership_is_not_api_failure(self):
        for source in ("debug_fixture.py", "cdb_transport.py"):
            result = self.probe(source, 1, 0, 0)
            self.assertTrue(result["ApiSucceeded"])
            self.assertTrue(result["MemberValid"])
            self.assertFalse(result["InAnyJob"])
            self.assertFalse(result["LastErrorMeaningful"])

    def test_nonzero_bool_and_last_error_do_not_claim_specific_job(self):
        for source in ("debug_fixture.py", "cdb_transport.py"):
            result = self.probe(source, 2, 1, 123)
            self.assertEqual(result["ApiReturn"], 2)
            self.assertTrue(result["InAnyJob"])
            self.assertFalse(result["LastErrorMeaningful"])
            self.assertFalse(result["SpecificOriginalJobProven"])

    def test_wrong_pointer_width_refused_before_query(self):
        for source in ("debug_fixture.py", "cdb_transport.py"):
            with self.assertRaisesRegex(RuntimeError, "x64"):
                self.probe(source, 1, 1, 0, width=4)

    def test_probe_definitions_stay_identical(self):
        definitions = []
        for source in ("debug_fixture.py", "cdb_transport.py"):
            tree = ast.parse(Path(__file__).with_name(source).read_text(encoding="utf-8"))
            node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "query_job_membership")
            definitions.append(ast.dump(node, include_attributes=False))
        self.assertEqual(*definitions)

    def test_fixture_guard_preserved_for_api_failure_and_nonmember(self):
        tree = ast.parse(Path(__file__).with_name("debug_fixture.py").read_text(encoding="utf-8"))
        node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "require_job_membership")
        namespace = {}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "fixture-guard", "exec"), namespace)
        guard = namespace["require_job_membership"]
        for api, member in ((False, None), (False, True), (True, False)):
            with self.assertRaisesRegex(RuntimeError, "Outer owning job required"):
                guard({"ApiSucceeded": api, "InAnyJob": member, "ApiReturn": int(api), "LastError": 6,
                       "MemberValue": int(bool(member)), "MemberValid": api})
        guard({"ApiSucceeded": True, "InAnyJob": True})


class FailureTests(unittest.TestCase):
    def setUp(self):
        self.spec = {"mode": "fixture", "nonce": "a" * 32}

    def test_failed_event_remains_bound_without_workers(self):
        event = transport.failed_event(self.spec, RuntimeError("initial refusal"), 123)
        self.assertEqual(event["RootPID"], 123)
        self.assertEqual(event["Nonce"], self.spec["nonce"])
        self.assertIs(event["FixtureOnly"], True)
        self.assertIs(event["Healthy"], False)
        self.assertEqual(event["InitialFailure"]["Message"], "RuntimeError: initial refusal")

    def test_hostile_exception_description_not_called(self):
        class Hostile(Exception):
            def __str__(self):
                raise AssertionError("must not stringify exception")
        self.assertEqual(transport.error_description(Hostile("retained args")), "Hostile: retained args")

    def test_guard_api_failure_and_nonmember_remain_distinct(self):
        for api, member, expected in ((False, None, "IsProcessInJobAPIFailure"), (True, False, "IsProcessInJobNonmember")):
            evidence = [{"role": "fixture", "query": {"ApiSucceeded": api, "InAnyJob": member, "ApiReturn": int(api), "LastError": 6 if not api else 0}}]
            event = transport.failed_event(self.spec, FileNotFoundError("manifest absent"), 123, job_evidence=evidence)
            self.assertEqual(event["InitialFailure"]["Type"], expected)
            self.assertEqual(event["ImmediateFailure"]["Type"], "FileNotFoundError")
            self.assertEqual(event["JobEvidence"], evidence)

    def test_first_failure_retained_across_bootstrap_wrapper(self):
        with tempfile.TemporaryDirectory(prefix="iw7-job-diag-") as directory:
            root = Path(directory)
            evidence = {"schema": "iw7.rig-watch-self-job/1", "nonce": self.spec["nonce"], "pid": 456, "role": "fixture",
                        "query": {"ApiSucceeded": False, "ApiReturn": 0, "LastError": 6, "InAnyJob": None}}
            (root / "fixture-job.json").write_text(json.dumps(evidence), encoding="ascii")
            first = transport.retain_failure(root, self.spec, FileNotFoundError("initial manifest failure"), 123, debugger_pid=789, phase="fixture")
            raw = (root / "transport.json").read_bytes()
            again = transport.retain_failure(root, self.spec, RuntimeError("later wrapper"), 123)
            self.assertEqual(again, first)
            self.assertEqual((root / "transport.json").read_bytes(), raw)
            self.assertEqual(again["DebuggerPID"], 789)
            self.assertEqual(again["Phase"], "fixture")
            self.assertEqual(again["InitialFailure"]["Type"], "IsProcessInJobAPIFailure")

    def test_foreign_job_nonce_never_becomes_primary_cause(self):
        with tempfile.TemporaryDirectory(prefix="iw7-job-diag-") as directory:
            root = Path(directory)
            (root / "fixture-job.json").write_text(json.dumps({"schema": "iw7.rig-watch-self-job/1", "nonce": "b" * 32, "role": "fixture"}))
            with self.assertRaisesRegex(ValueError, "foreign job evidence"):
                transport.retain_failure(root, self.spec, ValueError("failure"), 123)
            self.assertFalse((root / "transport.json").exists())


if __name__ == "__main__":
    unittest.main()
