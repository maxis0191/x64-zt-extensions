"""Mocked phase/Plan controls only; all generated files remain below 1 MiB."""
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest
from unittest.mock import patch

import prepare_sab_ff as prepare
import sound_ff_phase as phase
from read_sab import sha
from test_sab import fixture

REPO = Path(__file__).resolve().parents[4]


def spec(root, name="build"):
    return dict(schema="iw7.material-v2-phase/1", phase=name, exe=str(Path(root) / "zonetool.exe"),
                sha256=phase.TOOL_SHA, arguments=["-headless", "-unbuffered-io", "-strict-content-sources", "-" + name + "zone", "sdk_original_sound_v1"],
                cwd=str(Path(root)), logs=str(Path(root) / "logs"), timeout=240)


class PhaseTests(unittest.TestCase):
    def test_literal_phase_guards(self):
        with tempfile.TemporaryDirectory() as root:
            for key, value in (("timeout", True), ("timeout", 240.0), ("timeout", 241),
                               ("sha256", "0" * 64), ("phase", "compile"), ("exe", "relative.exe")):
                item = spec(root); item[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError): phase.validate(item)
            item = spec(root); item["arguments"].append("-anything")
            with self.assertRaises(ValueError): phase.validate(item)
            item = spec(root); item["extra"] = 0
            with self.assertRaises(ValueError): phase.validate(item)

    def run_fake(self, root, error=None, calls=2, exit_code=0, false_code=False):
        item = spec(root)
        def drain(source, destination, failed, limit):
            self.assertEqual(limit, 2 * 1024 * 1024)
            if error is not None: raise error
            destination.write(source.read())
        def run(spec, guarded):
            logs = Path(spec["logs"]); logs.mkdir()
            failed = threading.Event()
            for _ in range(calls): guarded(io.BytesIO(b"original fixture"), io.BytesIO(), failed)
            receipt = dict(schema="iw7.material-v2-phase-result/1", phase="build", exit_code=False if false_code else exit_code,
                           failure=None, executable_sha256=phase.TOOL_SHA, log_limit_each=2 * 1024 * 1024)
            (logs / "phase.json").write_text(json.dumps(receipt))
            return exit_code
        code = phase.run(item, SimpleNamespace(run=run), drain)
        return code, json.loads((Path(item["logs"]) / "sound-phase.json").read_text())

    def test_existing_runner_mock_success(self):
        with tempfile.TemporaryDirectory() as root:
            code, report = self.run_fake(root)
            self.assertEqual(code, 0)
            self.assertTrue(report["explicit_normal_pipe_returns"])
            self.assertFalse(report["ready"])

    def test_all_baseexceptions_fail_existing_runner_receipt(self):
        for error in (ValueError("read"), SystemExit(4), KeyboardInterrupt()):
            with self.subTest(kind=type(error).__name__), tempfile.TemporaryDirectory() as root:
                code, report = self.run_fake(root, error)
                self.assertEqual(code, 1)
                self.assertFalse(report["verified"])
                self.assertFalse(report["explicit_normal_pipe_returns"])
                self.assertEqual(report["drain_exception_types"], [type(error).__name__] * 2)

    def test_normal_returns_native_code_and_types_required(self):
        for settings in ({"calls": 0}, {"calls": 1}, {"calls": 3}, {"exit_code": 3}, {"false_code": True}):
            with self.subTest(settings=settings), tempfile.TemporaryDirectory() as root:
                code, report = self.run_fake(root, **settings)
                self.assertEqual(code, 1)
                self.assertFalse(report["verified"])

    def test_caught_provider_error_cannot_complete(self):
        failed, completed, errors = threading.Event(), threading.Event(), []
        phase.guarded_drain(lambda a, b, event, limit: event.set(), None, None, failed, completed, errors)
        self.assertTrue(failed.is_set())
        self.assertFalse(completed.is_set())


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, _, _, _ = fixture(self.root)
        self.run = self.root / "native-not-created"
        self.executable = self.root / "existing-tool.exe"; self.executable.write_bytes(b"fixture")
        receipt = dict(schema="iw7.zonetool-community-candidate/1", executable=dict(path=str(self.executable), bytes=21696512, sha256=phase.TOOL_SHA))
        self.receipt = self.root / "receipt.json"; self.receipt.write_text(json.dumps(receipt))
        self.prior = self.root / "prior.json"
        self.previous = dict(Schema="iw7.material-v2-execution-plan/1", FFPhysicalBytes=8 * 1024**3,
                             FFCommitBytes=11 * 1024**3, Source=dict(builder=dict(receipt_sha256=sha(self.receipt.read_bytes()))),
                             StockRoot=str(self.root / "stock-not-staged"))
        self.prior.write_text(json.dumps(self.previous))

    def prepare(self):
        real_read, real_stat, real_sha = prepare.Inputs.read, Path.stat, prepare.sha
        python = Path(prepare.sys.executable)
        def read(inputs, path, *args):
            if Path(path) == python:
                inputs.observed[python] = (0, phase.PYTHON_SHA)
                return b"python-placeholder"
            return real_read(inputs, path, *args)
        def stat(path, *args, **kwargs):
            value = real_stat(path, *args, **kwargs)
            return SimpleNamespace(st_size=21696512, st_mode=value.st_mode, st_file_attributes=0) if path == self.executable else value
        with patch.object(prepare.Inputs, "read", read), patch.object(Path, "stat", stat), \
                patch.object(prepare, "sha", side_effect=lambda raw: phase.PYTHON_SHA if raw == b"python-placeholder" else real_sha(raw)), \
                patch.object(prepare.Inputs, "recheck"):
            return prepare.prepare(self.source, self.run, REPO, self.prior, sha(self.prior.read_bytes()), self.receipt)

    def test_plan_reuses_runner_has_four_exact_phases_and_stages_nothing(self):
        value = self.prepare()
        self.assertEqual([p["phase"] for p in value["phase_specs"]], ["build", "verify", "dump", "read"])
        self.assertEqual((value["physical_bytes"], value["commit_bytes"]), (8 * 1024**3, 11 * 1024**3))
        self.assertFalse(value["stock_staged"])
        self.assertFalse(value["native_authorized"])
        self.assertFalse(self.run.exists())
        self.assertEqual(len(value["owned_future_outputs"]), 3)
        self.assertNotIn("original/source.wav", value["source_stage_relatives"])

    def test_existing_run_root_refused(self):
        self.run.mkdir()
        with self.assertRaisesRegex(ValueError, "fresh absent"): self.prepare()

    def test_lowered_native_or_noninteger_budget_refused(self):
        for amount in (512 * 1024**2, 8.0 * 1024**3, True):
            self.previous["FFPhysicalBytes"] = amount; self.prior.write_text(json.dumps(self.previous))
            with self.subTest(amount=amount), self.assertRaisesRegex(ValueError, "native budget"): self.prepare()

    def test_plan_digest_mismatch_refused(self):
        with self.assertRaisesRegex(ValueError, "historical stock plan"):
            prepare.prepare(self.source, self.run, REPO, self.prior, "0" * 64, self.receipt)

    def test_unverified_codec_checkpoint_refused(self):
        actual = prepare.strict_json
        def changed(raw, *args):
            result = actual(raw, *args)
            if isinstance(result, dict) and result.get("schema") == "iw7.original-sound-codec-checkpoint/1":
                result["external_decoder_verified"] = False
            return result
        with patch.object(prepare, "strict_json", side_effect=changed), self.assertRaisesRegex(ValueError, "codec checkpoint"):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
