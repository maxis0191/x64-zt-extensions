"""Finite CPP80 plan authoring only; no factory, DEFAULT or binary metadata access."""
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_material_parts_probe as parts
import prepare_registration_bindings_probe as probe
import image_metadata_consumer as bounded


class BindingsPlanTests(unittest.TestCase):
    def fixture(self):
        reference, controllers, _, _, _, metadata, run = parts.PartsPlanTests().fixture()
        metadata.update(Path=r"C:\authored\cpp80\link\zonetool-t7.exe", Bytes=probe.CANDIDATE[0])
        proofs = {name: dict(Path="C:\\authored\\"+name+".json", Bytes=size, SHA256=sha) for name, (size, sha) in probe.PINS.items()}
        build = dict(Schema="iw7.t7-minimal-build-plan/1", SourceCommit=probe.NATIVE, RunRoot=r"C:\authored\cpp80",
                     BuildProfile={name: parts.pin("C:\\authored\\build\\"+name+".json") for name in probe.BUILD_FIELDS})
        build["BuildProfile"]["BindingsLegacyFixture"] = copy.deepcopy(build["BuildProfile"]["RegistrationFixture"])
        build["BuildProfile"]["BindingsResponse"] = copy.deepcopy(build["BuildProfile"]["RegistrationResponse"])
        receipt = dict(Schema="iw7.t7-minimal-build/1", Status="Passed", PlanSHA256=probe.PINS["Plan"][1], RegistrationBindingsFixturePassed=True,
                       Stages=[dict(Artifacts=[]) for _ in range(5)])
        receipt["Stages"][2]["Artifacts"] = [parts.pin(r"C:\authored\cpp80\main\dependencies.json")]
        receipt["Stages"][-1]["Artifacts"] = [dict(Path=metadata["Path"], Bytes=probe.CANDIDATE[0], SHA256=probe.CANDIDATE[1])]
        contract = dict(Path=r"C:\authored\registration-material-bindings-source-contract.json", Bytes=probe.CONTRACT[0], SHA256=probe.CONTRACT[1])
        reader = dict(Path=r"C:\authored\registration_bindings_consumer.py", Bytes=probe.READER[0], SHA256=probe.READER[1])
        return reference, controllers, build, receipt, proofs, contract, reader, metadata, run

    def test_pure_reduction_preserves_collection_and_separates_proofs(self):
        args = self.fixture(); before = copy.deepcopy(args)
        with patch.object(Path, "open", side_effect=AssertionError("opened")), patch.object(Path, "stat", side_effect=AssertionError("stat")):
            plan = probe.derive(*args)
        self.assertEqual(args, before)
        self.assertEqual((len(plan["Bindings"]), sum(p["IsText"] for p in plan["Bindings"]), len(plan["InputMetadata"])), (112, 84, 27))
        self.assertEqual(plan["Bootstraps"], args[0]["Bootstraps"])
        self.assertEqual(plan["SharedQualification"], args[0]["SharedQualification"])
        self.assertEqual(plan["Arguments"], ["-t7-iw7-registration-material-bindings-v1", "mp_freerun_04", "p7_fre_platform_cap_02", "0"])
        self.assertEqual((plan["CandidateBytes"], plan["CandidateSHA256"]), probe.CANDIDATE)
        marker = plan["SelectedRegistrationMaterialBindingsV1"]
        self.assertEqual(marker["CompiledExtensionSource"], probe.SOURCE)
        self.assertEqual(marker["CPPQualification"], args[4]["Handoff"])
        self.assertTrue(marker["CPPQualified"])
        self.assertFalse(marker["NativeObserved"]); self.assertFalse(marker["Ready"])
        self.assertIsNone(marker["DeepMetadataOutcome"]); self.assertIsNone(marker["QualifiedObjectMipCount"])
        self.assertFalse(set(probe.EXPORT_FIELDS) & set(plan))
        self.assertFalse(any("provider.xpak" in p["Path"] for p in plan["Bindings"]))

    def test_wrong_cohort_candidate_schema_and_inventory_refuse(self):
        for case in ("old39", "old87", "source", "receipt", "invented-flag", "candidate", "link-path", "duplicate", "inventory", "controllers", "fixture-alias", "response-alias"):
            args = list(self.fixture())
            if case == "old39": args[4]["Plan"]["SHA256"] = "0"*64
            elif case == "old87": args[3]["Stages"][-1]["Artifacts"][0]["SHA256"] = "4fcb0205e30979457784d1b883a153ecf5c20751543b68dfb184671d59e3ee4d"
            elif case == "source": args[2]["SourceCommit"] = probe.SOURCE
            elif case == "receipt": args[3]["RegistrationBindingsFixturePassed"] = 1
            elif case == "invented-flag": args[3]["RegistrationBindingsCPPQualified"] = True
            elif case == "candidate": args[7]["Bytes"] = 22059008
            elif case == "link-path": args[2]["RunRoot"] = r"C:\authored\different"
            elif case == "duplicate": args[1][0]["Path"] = args[5]["Path"]
            elif case == "inventory": args[0]["Bootstraps"].pop()
            elif case == "controllers": args[1].pop()
            elif case == "fixture-alias": args[2]["BuildProfile"]["BindingsLegacyFixture"]["Path"] = "C:\\authored\\different.cpp"
            else: args[2]["BuildProfile"]["BindingsResponse"]["Path"] = "C:\\authored\\different.rsp"
            with self.subTest(case=case), patch.object(Path, "open", side_effect=AssertionError("opened")), self.assertRaises(ValueError):
                probe.derive(*args)

    def test_all_cohort_pins_require_exact_typed_metadata(self):
        for name in probe.PINS:
            for field, value in (("Bytes", True), ("Bytes", "1"), ("SHA256", [probe.PINS[name][1]]), ("Path", ["source.json"])):
                args = list(self.fixture()); args[4][name][field] = value
                with self.subTest(name=name, field=field), self.assertRaises(ValueError):
                    probe.derive(*args)

    def test_fixture_wrong_size_refuses_before_open(self):
        path = Path.cwd()/"authored-never-created"/"stdout.log"
        with patch.object(Path, "is_symlink", return_value=False), patch.object(Path, "is_junction", return_value=False), \
             patch.object(Path, "stat", return_value=SimpleNamespace(st_size=71)), patch.object(Path, "open", side_effect=AssertionError("opened")):
            with self.assertRaises(ValueError): probe.read_source_text(path, probe.PINS["FixtureStdout"])

    def test_opaque_text_input_refuses_before_stat_or_open(self):
        for suffix in (".exe", ".pdb", ".dll", ".ff", ".xpak"):
            with self.subTest(suffix=suffix), patch.object(Path, "stat", side_effect=AssertionError("stat")), patch.object(Path, "open", side_effect=AssertionError("opened")):
                with self.assertRaises(ValueError): probe.read_source_text(Path.cwd()/("never-created"+suffix), (1, "a"*64))

    def test_receiver_constants_match_source_and_consumer(self):
        source = (Path(__file__).parent/"T7Catalogue.Profile.ps1").read_text(encoding="utf-8")
        for size, sha in (probe.CANDIDATE, *probe.PINS.values(), probe.CONTRACT, probe.READER):
            self.assertIn(str(size), source); self.assertIn(sha, source)
        self.assertIn(probe.SOURCE, source); self.assertIn(probe.NATIVE, source)
        self.assertIn("iw7.t7-registration-bindings-consumer/1", source)

    def run_authored_main(self, root, *, manifest_size=386862, duplicate_manifest=False, manifest_schema="iw7.source-workspace/1"):
        """Real main/strict JSON/derive/output with fake input pin readers only.

        The immutable-cohort reader layer is mocked; this is invented Source
        authoring, never an operational factory or a claim of cryptographic proof.
        """
        reference, controllers, build, receipt, proofs, contract, reader, metadata, _ = self.fixture()
        source = root/"source"; source.mkdir()
        run = source/"runtime/t7-registration-bindings-authored"
        output = source/"runtime/registration-bindings-plan-authored"
        (source/"runtime").mkdir()
        workspace = dict(schema=manifest_schema, product="x64-zt-extensions", revisions={"x64-zt-extensions": "a"*40},
            files=[dict(path=name, bytes=1, sha256="a"*64) for name in probe.CONTROLLERS])
        handoff = dict(Schema="iw7.t7-registration-bindings-cpp-actual-handoff/1", Status="Passed", SourceCommit=probe.SOURCE,
            NativeSourceCommit=probe.NATIVE, CPP80ObservedClosed=True, CandidateExecuted=False,
            CandidateOrSymbolsReadAfterRelease=False, Candidate=copy.deepcopy(receipt["Stages"][-1]["Artifacts"][0]))
        handoff.update({name: value for name, value in proofs.items() if name != "Handoff"})

        def padded(value, size):
            raw = json.dumps(value).encode()
            self.assertLessEqual(len(raw), size)
            return raw+b" "*(size-len(raw))

        manifest_raw = padded(workspace, manifest_size)
        if duplicate_manifest:
            # Exercise the shared strict duplicate-key check on a large Source input.
            manifest_raw = b'{"schema":0,"schema":1}'+b" "*(manifest_size-23)
        source_payloads = {
            str(source/"source-workspace.json"): manifest_raw,
            str(root/"reference.json"): padded(reference, probe.REFERENCE_PIN[0]),
            str(root/"handoff.json"): padded(handoff, probe.PINS["Handoff"][0]),
            proofs["Plan"]["Path"]: padded(build, probe.PINS["Plan"][0]),
            proofs["Receipt"]["Path"]: padded(receipt, probe.PINS["Receipt"][0]),
        }
        calls = []

        def source_reader(path, expected=None):
            path = str(path); calls.append(path)
            raw = source_payloads.get(path, b"authored Source")
            size, sha = expected or (1, "a"*64)
            if path == str(source/"source-workspace.json"):
                size = len(raw)
            return dict(Path=path, Bytes=size, SHA256=sha), raw

        preservation = dict(Schema="iw7.t7-preservation-metadata/1", MainBaseline="Stopped",
            PreservedMain=dict(PID=1234, CreatedUtc="2026-10-15T00:00:00Z", Image=r"C:\authored\main.exe"), PreservedProcesses=[])
        def snapshot(path):
            return parts.pin(str(path)), copy.deepcopy(metadata if Path(path).name == "candidate.json" else preservation)

        real_stat = Path.stat
        def guard_stat(path, *args, **kwargs):
            if path.suffix.lower() in (".exe", ".dll", ".pdb", ".ff", ".xpak"):
                raise AssertionError("Source test queried opaque metadata")
            return real_stat(path, *args, **kwargs)

        argv = ["--source", str(source), "--reference", str(root/"reference.json"), "--handoff", str(root/"handoff.json"),
            "--candidate-metadata", str(root/"candidate.json"), "--preservation-metadata", str(root/"preservation.json"),
            "--run-root", str(run), "--output", str(output)]
        stdout = io.StringIO()
        with patch.object(probe, "read_text_pin", side_effect=source_reader), patch.object(probe, "read_source_text", side_effect=source_reader), \
             patch.object(probe, "read_snapshot", side_effect=snapshot), patch.object(Path, "stat", guard_stat), patch("sys.stdout", stdout):
            probe.main(argv)
        return json.loads(stdout.getvalue()), json.loads((output/"plan.local.json").read_text(encoding="utf-8")), calls, source_payloads

    def test_actual_main_accepts_large_source_metadata_without_opaque_queries(self):
        with tempfile.TemporaryDirectory() as temp:
            result, plan, calls, payloads = self.run_authored_main(Path(temp).resolve())
        # Manifest386862, reference70998, handoff37937, plan406073 and receipt50715
        # all exceed the DTO's 32-KiB default. Exercise every real Source decode site.
        self.assertEqual(len(payloads), 5)
        for path, raw in payloads.items():
            self.assertGreater(len(raw), 32768)
            self.assertIn(path, calls)
            with self.assertRaises(ValueError): bounded.strict_json(raw)
        self.assertEqual((result["Bindings"], result["InputMetadata"]), (112, 27))
        self.assertFalse(result["NativeExecuted"]); self.assertFalse(result["LeaseAcquired"])
        self.assertEqual(plan["CandidateSHA256"], probe.CANDIDATE[1])

    def test_actual_main_refuses_source_over_one_mib_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            with self.assertRaisesRegex(ValueError, "bounded Source JSON"):
                self.run_authored_main(root, manifest_size=1024*1024+1)
            self.assertFalse((root/"source/runtime/registration-bindings-plan-authored").exists())

    def test_actual_main_reproduces_old_report_cap_role_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            with patch.object(probe, "read_source_metadata_json", side_effect=bounded.strict_json), self.assertRaisesRegex(ValueError, "bounded JSON report"):
                self.run_authored_main(root)
            self.assertFalse((root/"source/runtime/registration-bindings-plan-authored").exists())

    def test_actual_main_keeps_strict_duplicate_key_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            with self.assertRaisesRegex(ValueError, "duplicate"):
                self.run_authored_main(root, duplicate_manifest=True)
            self.assertFalse((root/"source/runtime/registration-bindings-plan-authored").exists())

    def test_source_decoder_keeps_types_utf8_and_finite_numbers_strict(self):
        for raw in (None, "{}", bytearray(b"{}"), b"", b"[]", b"false", b"null", b'{"v":NaN}', b'{"v":Infinity}', b'{"v":"\xff"}', b'{"nested":{"x":1,"x":2}}'):
            with self.subTest(raw=repr(raw)), self.assertRaises(ValueError): probe.read_source_metadata_json(raw)
        self.assertEqual(probe.read_source_metadata_json(b'{}'+b' '*(1024*1024-2)), {})
        for limit in (32768, 65536):
            self.assertEqual(bounded.strict_json(b'{}'+b' '*(limit-2), limit=limit), {})
            with self.assertRaises(ValueError): bounded.strict_json(b'{}'+b' '*(limit-1), limit=limit)
        with self.assertRaisesRegex(ValueError, "explicit 32 or 64"):
            bounded.strict_json(b'{}', limit=1024*1024)

    def test_actual_main_refuses_source_manifest_schema_type_forgery(self):
        for schema in (None, False, ["iw7.source-workspace/1"], "iw7.t7-registration-material-bindings/1"):
            with self.subTest(schema=schema), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                with self.assertRaisesRegex(ValueError, "Composed receiver Source"):
                    self.run_authored_main(root, manifest_schema=schema)
                self.assertFalse((root/"source/runtime/registration-bindings-plan-authored").exists())


if __name__ == "__main__":
    unittest.main()
