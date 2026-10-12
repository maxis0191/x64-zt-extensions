"""Pure adversarial FLAC17 contracts; no binaries, admission or native processes."""
import copy
import json
import ntpath
from pathlib import Path
import unittest
from unittest.mock import patch

import build_contract as contract
import flac_build_profile as flac
from prepare_flac_build_plan import source_bytes
from test_sdk_tools import fixture as sdk_fixture


def fixture():
    plan = sdk_fixture()
    repo, candidate = r"C:\fixture\repo", r"C:\fixture\repo\runtime\zt-sound-flac-test"
    plan.update(schema=flac.SCHEMA, source_pin="fab935826c898806855376662a8a03317b3ad8f1",
                gsc_provider_revision="eabe74ab65d8ce2a943b54d24b15a60749a0cf2a",
                shared_repo=repo, candidate=candidate, output=candidate, physical_bytes=4*1024**3,
                commit_bytes=6*1024**3, stop_bytes=512*1024**2, planning_ceiling_bytes=768*1024**2,
                sealed=True, sab_ff_authorized=False, ready=False,
                providers=[dict(role=k, sha256=v) for k, v in contract.PROVIDERS.items()],
                common_objects={n: ntpath.join(r"C:\fixture\old", n) for n in contract.COMMON_MEMBERS})
    for name in ("python", "inventory", "seal", "seal_result", "worker"):
        plan[name] = ntpath.join(repo, name + ".fixture")
    for name in ("seal_sha256", "seal_result_sha256", "python_sha256"):
        plan[name] = "a" * 64
    for name in ("CL", "_CL_", "LINK", "_LINK_", "LIBPATH", "PYTHONPATH", "PYTHONHOME"):
        plan["environment"][name] = ""
    plan["environment"].update(VSLANG="1033", NUMBER_OF_PROCESSORS="1", TEMP=candidate+r"\tmp", TMP=candidate+r"\tmp")
    overlay = repo+r"\runtime\content-surfaces\original-sound-flac-dump-source-test"
    sources = [dict(path=ntpath.join(overlay, n), bytes=b, sha256=h) for n, (b, h) in flac.SOURCE_PINS.items()]
    review = dict(path=repo+r"\original-review.json", bytes=100, sha256=flac.REVIEW_SHA)
    plan["flac"] = dict(overlay=overlay, sources=sources, review=review,
                        original_sound_bank=r"C:\native\src\zonetool\zonetool\iw7\assets\sound_bank.cpp")
    plan["source_pins"] += copy.deepcopy(sources) + [copy.deepcopy(review)]
    plan["commands"], plan["response_pins"] = [], []
    for name in contract.build_order(plan):
        command = dict(phase=name, working_directory=candidate)
        if name.endswith("-run"):
            tag = "original" if "original" in name else ("flac-header" if "flac" in name else "patched")
            command.update(kind="probe_run", executable=ntpath.join(candidate, "probe", tag+".exe"),
                           arguments=[] if tag == "flac-header" else ["--expect-observed-corrupt" if tag == "original" else "--expect-original"])
        else:
            kind = "candidate_compile" if name.endswith("-compile") or name.startswith("compile-") else "candidate_link"
            exe = "cl.exe" if kind.endswith("compile") else ("lib.exe" if name == "archive-common" else "link.exe")
            path = ntpath.join(repo, "rsp", name+".rsp")
            pin = dict(path=path, bytes=100, sha256="b"*64)
            command.update(kind=kind, executable=ntpath.join(ntpath.dirname(plan["compiler"]), exe), arguments=["@"+path],
                           response_path=path, response_sha256=pin["sha256"], executable_sha256="c"*64)
            plan["response_pins"].append(pin)
            plan["source_pins"].append(copy.deepcopy(pin))
        plan["commands"].append(command)
    return plan


class FlacBuildContracts(unittest.TestCase):
    def test_exact17_order14responses_and_four_sources(self):
        plan = fixture()
        self.assertIs(contract.validate_plan(plan, sealed=True), plan)
        self.assertEqual(len(plan["commands"]), 17)
        self.assertEqual(len(contract.reviewed_responses(plan, {})), 14)
        self.assertEqual(len(flac.validate_extension(plan, {})), 4)

    def test_closed_profile_mutations_fail(self):
        mutations = {
            "schema-downgrade": lambda p: p.update(schema=contract.SCHEMA),
            "missing-phase": lambda p: p["commands"].pop(),
            "duplicate-phase": lambda p: p["commands"].__setitem__(7, copy.deepcopy(p["commands"][6])),
            "reordered-phase": lambda p: p["commands"].reverse(),
            "probe-extra-arg": lambda p: p["commands"][8]["arguments"].append("--accept"),
            "probe-old-image": lambda p: p["commands"][8].update(executable=p["commands"][5]["executable"]),
            "unsealed-source": lambda p: p["source_pins"].pop(2),
            "duplicate-source": lambda p: p["flac"]["sources"].__setitem__(1, p["flac"]["sources"][0]),
            "changed-source": lambda p: p["flac"]["sources"][0].update(sha256="0"*64),
            "typed-source": lambda p: p["flac"]["sources"][0].update(bytes="113219"),
            "extra-source": lambda p: p["flac"]["sources"].append(copy.deepcopy(p["flac"]["sources"][0])),
            "unknown-extension": lambda p: p["flac"].update(unreviewed=True),
            "shared-overlay": lambda p: p["flac"].update(overlay=r"C:\shared"),
            "missing-response": lambda p: p["response_pins"].pop(),
            "duplicate-response": lambda p: p["response_pins"].__setitem__(1, p["response_pins"][0]),
            "response-wrong-hash": lambda p: p["commands"][0].update(response_sha256="0"*64),
            "ready": lambda p: p.update(ready=True),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                plan = fixture()
                mutate(plan)
                with self.assertRaises(ValueError):
                    contract.validate_plan(plan, sealed=True)

    def test_new_source_cannot_be_backdated_into_old_seal(self):
        plan = fixture()
        with self.assertRaisesRegex(ValueError, "not Seal C"):
            flac.validate_extension(plan, {contract.key(plan["flac"]["sources"][0]["path"]): {}})

    def test_probe_actual_json_is_typed_complete_and_nonpromoting(self):
        good = dict(schema="iw7.flac-dump-header-probe/1", cases=103, input_unchanged=True,
                    extent_checks=True, native_dump_tested=False, full_conformance=False, ready=False)
        self.assertEqual(flac.probe_result(json.dumps(good).encode()), good)
        for key, value in (("cases", "103"), ("cases", 102), ("cases", True), ("input_unchanged", 1),
                           ("extent_checks", False), ("native_dump_tested", True), ("full_conformance", True), ("ready", True)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                flac.probe_result(json.dumps({**good, key: value}).encode())
        with self.assertRaises(ValueError):
            flac.probe_result(json.dumps({**good, "unexpected": True}).encode())

    def test_plan_source_reader_refuses_binary_before_open(self):
        with patch.object(Path, "open", side_effect=AssertionError("must not open payload")):
            for suffix in (".exe", ".dll", ".obj", ".lib", ".pdb", ".wav", ".flac", ".sabl", ".ff"):
                with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, "source/metadata"):
                    source_bytes(Path("C:/fixture/payload"+suffix))

    def test_response_verification_rejects_content_even_with_rebound_hash(self):
        plan = fixture()
        expected_commands = copy.deepcopy(plan["commands"])
        responses = {c["phase"]: b"reviewed-source-and-flags" for c in plan["commands"] if c["kind"] != "probe_run"}
        actual = {c["response_path"]: responses[c["phase"]] for c in plan["commands"] if c["kind"] != "probe_run"}
        for c in plan["commands"]:
            if c["kind"] != "probe_run":
                c["response_sha256"] = contract.sha(actual[c["response_path"]])
        with patch.object(flac, "expected_commands", return_value=(expected_commands, responses)):
            self.assertTrue(flac.verify_responses(plan, lambda p, _: actual[p], {}))
            command = plan["commands"][6]
            actual[command["response_path"]] += b"\n/FIunreviewed.hpp"
            command["response_sha256"] = contract.sha(actual[command["response_path"]])
            with self.assertRaisesRegex(ValueError, "outside reviewed"):
                flac.verify_responses(plan, lambda p, _: actual[p], {})


if __name__ == "__main__":
    unittest.main()
