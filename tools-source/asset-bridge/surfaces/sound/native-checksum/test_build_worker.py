"""Mock the native phase boundary; no compiler, executable or reservation runs."""
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_worker as worker
from build_contract import sha


class NativeBoundary(unittest.TestCase):
    def test_runner_requires_two_successful_normal_drain_returns(self):
        for mode in ("success", "nonzero", "missing-eof", "base-exception", "wrong-receipt", "changed-image"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "logs").mkdir()
                exe = root / "cl.exe"
                exe.write_bytes(b"fixture-only-not-an-executable")
                expected = sha(exe.read_bytes())
                def drain(source, destination, failed, limit):
                    if mode == "base-exception":
                        raise KeyboardInterrupt("synthetic drain exception")
                    destination.write(source.read())
                # Use the production sound adapter without importing its provider
                # graph; this function is text-identical and loaded via AST below.
                import ast
                source_path = Path(__file__).resolve().parents[1] / "sound_ff_phase.py"
                tree = ast.parse(source_path.read_text(encoding="utf-8-sig"))
                function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "guarded_drain")
                namespace = {}
                exec(compile(ast.Module(body=[function], type_ignores=[]), str(source_path), "exec"), namespace)
                adapter = types.SimpleNamespace(guarded_drain=namespace["guarded_drain"])
                def run(spec, guarded):
                    log = Path(spec["logs"])
                    log.mkdir()
                    for i, name in enumerate(("stdout", "stderr")):
                        with (log / (name + ".log")).open("wb") as output:
                            if not (mode == "missing-eof" and i == 1):
                                import threading
                                guarded(io.BytesIO(b"fixture output"), output, threading.Event())
                    data = {"schema": "iw7.material-v2-phase-result/1", "phase": "compile", "pid": 123,
                            "exit_code": 1 if mode == "nonzero" else 0, "failure": None,
                            "executable_sha256": "0"*64 if mode == "wrong-receipt" else expected,
                            "log_limit_each": 2*1024*1024}
                    (log / "phase.json").write_text(json.dumps(data), encoding="utf-8")
                    if mode == "changed-image":
                        exe.write_bytes(b"changed")
                    return 1 if mode == "nonzero" else 0
                command = {"phase": "fixture-compile", "kind": "candidate_compile", "executable": str(exe), "arguments": ["@fixture.rsp"]}
                args = ({"candidate": str(root)}, command, expected, adapter, types.SimpleNamespace(run=run), drain)
                if mode == "success":
                    receipt = worker.native_phase(*args)
                    self.assertTrue(receipt["normal_eof"])
                    self.assertEqual(receipt["exit_code"], 0)
                else:
                    with self.assertRaises(ValueError):
                        worker.native_phase(*args)

    def test_seal_manifest_without_successful_final_lifecycle_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seal = {"Schema": "iw7.sound-checksum-sealed-inputs/1", "FileCount": 1,
                    "Inputs": [{"Path": r"C:\fixture\one.obj", "SHA256": "a"*64}]}
            seal_path, state_path = root / "seal.json", root / "state.json"
            seal_path.write_text(json.dumps(seal), encoding="utf-8")
            digest = sha(seal_path.read_bytes())
            for status, released, token, twice in (("Sealed", True, None, True), ("Failed", True, None, True),
                                                  ("Sealed", False, "token", True), ("Sealed", True, None, False)):
                state = {"Status": status, "LeaseReleased": released, "RetainedLeaseToken": token,
                         "InputHashesVerifiedTwice": twice, "ManifestSHA256": digest}
                state_path.write_text(json.dumps(state), encoding="utf-8")
                plan = {"seal": str(seal_path), "seal_sha256": digest,
                        "seal_result": str(state_path), "seal_result_sha256": sha(state_path.read_bytes())}
                if status == "Sealed" and released and twice:
                    self.assertEqual(len(worker.verify_seal(plan)), 1)
                else:
                    with self.assertRaisesRegex(ValueError, "complete separately admitted"):
                        worker.verify_seal(plan)


if __name__ == "__main__":
    unittest.main()
