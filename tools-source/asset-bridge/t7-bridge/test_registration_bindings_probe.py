"""Finite CPP80 plan authoring only; no factory, DEFAULT or binary metadata access."""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_material_parts_probe as parts
import prepare_registration_bindings_probe as probe


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


if __name__ == "__main__":
    unittest.main()
