"""Authored closed metadata fixtures only; no producer, C++, native or provider IO."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import registration_bindings_consumer as c
from test_incoming_image_consumer import sample


def report():
    value = dict.fromkeys(c.FALSES, False)
    value.update(schema=c.SCHEMA, source_profile=c.PROFILE, native_source_commit=c.copied.PIN,
                 zone="mp_freerun_04", model=c.bounded.MODEL, lod=0, slot=0, model_default=None,
                 capture_phase=c.PHASE, recheck_phase=c.PHASE, capture_ordinal=1,
                 model_callbacks=3, matched_registrations=1, duplicate_registration=False,
                 registration_search_refused=False, zone_load_complete=True, bindings_enumerated=True,
                 registration_chain=dict(model_header_hex="0000000000010000", material_hex="0000000000020000",
                                         texture_table_hex="0000000000030000"),
                 bindings=[], binding_count=7, image_header_bytes=264, header_copies=14,
                 completed_header_bytes=3696, header_byte_limit=3696, image_name_max_utf8_bytes=255,
                 metadata_read_limit=65536, refused=False, reason=None, qualified_object_mip_count=None,
                 payload_bytes_read=0)
    for index in range(7):
        name = ",$camo_base_normal" if index == 0 else "original_image_" + str(index)
        value["bindings"].append(dict(index=index, binding_hash_u32=100 + index,
            usage_u16=65535 if index == 6 else index, image_pointer_present=True,
            raw_name=name, leading_comma_reference=name.startswith(","),
            registration_chain=dict(value["registration_chain"], image_field_hex=f"{0x40000 + index * 264:016x}"),
            binding_rechecked=True, snapshot=sample(name, zero=index == 0)))
    return value


def refuse_row(value, index, *, copies=0, copy_fault=False, null_pointer=False):
    row = value["bindings"][index]
    row.update(raw_name=None, leading_comma_reference=None, binding_rechecked=False)
    if null_pointer:
        row["image_pointer_present"] = False
        row["registration_chain"]["image_field_hex"] = "0" * 16
    row["snapshot"] = dict(header_observed=False, header_copies=copies,
        completed_header_bytes=None if copy_fault else copies * 264,
        header_rechecked=False, name_rechecked=False, callback_header_name_rechecked=False,
        copy_fault=copy_fault, image=None, refused=True, reason="Authored row refusal")
    value["header_copies"] = sum(item["snapshot"]["header_copies"] for item in value["bindings"])
    value["completed_header_bytes"] = None if any(item["snapshot"]["copy_fault"] for item in value["bindings"]) else value["header_copies"] * 264


class RegistrationBindingsTests(unittest.TestCase):
    def test_zero_reference_nonzero_ordinary_and_uint16_usage_are_metadata_only(self):
        value = report(); before = copy.deepcopy(value)
        with patch.object(Path, "open", side_effect=AssertionError("IO")):
            result = c.classify(value, 0)
        self.assertEqual(value, before)
        self.assertEqual((result["outcome"], result["observation_status"], result["observed_snapshots"]),
                         ("RegistrationBindingsObserved", "complete", 7))
        self.assertEqual(result["observation"]["bindings"][6]["usage_u16"], 65535)
        self.assertEqual(result["binding_summaries"][0]["nonzero_descriptor_scalar_fields"], 0)
        self.assertEqual(result["binding_summaries"][0]["name_category"], "reference")
        self.assertEqual(result["binding_summaries"][1]["name_category"], "ordinary")
        self.assertEqual(result["observation"], value)
        for flag in (*c.FALSES, "same_pointer_proven"):
            self.assertIs(result[flag], False)
        self.assertIsNone(result["qualified_object_mip_count"])
        self.assertEqual(result["payload_bytes_read"], 0)
        value["bindings"][0]["snapshot"]["image"]["width"] = 7
        self.assertEqual(result["observation"], before)

    def test_per_row_refusal_does_not_refuse_complete_enumeration_or_later_rows(self):
        value = report(); refuse_row(value, 3, copies=1)
        result = c.classify(value, 0)
        self.assertEqual(result["outcome"], "RegistrationBindingsObserved")
        self.assertEqual((result["observed_snapshots"], result["refused_snapshots"]), (6, 1))
        self.assertIsNone(result["binding_summaries"][3]["name_category"])
        self.assertTrue(result["binding_summaries"][6]["snapshot_observed"])
        for index in range(7):
            refuse_row(value, index, null_pointer=True)
        result = c.classify(value, 0)
        self.assertEqual((result["observation_status"], result["observed_snapshots"], result["refused_snapshots"]),
                         ("complete", 0, 7))
        self.assertEqual(result["observation"]["completed_header_bytes"], 0)

    def test_copy_fault_unknown_bytes_and_structural_prefixes_are_preserved(self):
        value = report(); refuse_row(value, 1, copies=1, copy_fault=True)
        self.assertIsNone(c.classify(value, 0)["observation"]["completed_header_bytes"])
        value["completed_header_bytes"] = value["header_copies"] * 264
        with self.assertRaises(ValueError): c.consume(value)
        for count in (0, 3, 7):
            value = report(); value["bindings"] = value["bindings"][:count]
            value.update(bindings_enumerated=False, refused=True, reason="Structural chain refusal",
                         header_copies=count * 2, completed_header_bytes=None)
            result = c.classify(value, 2)
            self.assertEqual((result["outcome"], result["unpublished_bindings"]), ("RegistrationBindingsRefused", 7-count))
            self.assertIsNone(result["observation"]["completed_header_bytes"])
            with self.assertRaises(ValueError): c.classify(value, 0)

    def test_no_capture_search_trigger_duplicate_and_failed_native_are_distinct(self):
        value = report()
        self.assertEqual(c.classify(value, 3)["outcome"], "ValidRegistrationBindingsFromFailedProcess")
        for counter in ("duplicate", "search"):
            value = report(); value.update(refused=True, reason="Window refusal")
            if counter == "duplicate": value.update(matched_registrations=2, duplicate_registration=True)
            else: value.update(model_callbacks=1025, registration_search_refused=True)
            self.assertEqual(c.classify(value, 2)["outcome"], "RegistrationBindingsRefused")
        value = report(); value.update(capture_ordinal=0, model_callbacks=0, matched_registrations=0,
            bindings=[], bindings_enumerated=False, header_copies=0, completed_header_bytes=0,
            refused=True, reason="No selected registration", registration_chain=dict.fromkeys(c.CHAIN, "0" * 16))
        self.assertEqual(c.classify(value, 2)["unpublished_bindings"], 7)
        self.assertEqual(c.classify(None, 2)["outcome"], "NoReport")

    def test_copy_and_fault_require_the_original_pointer_gate_but_diagnostics_do_not(self):
        value = report()
        value["bindings"][0]["registration_chain"]["image_field_hex"] = "0000000000000001"
        with self.assertRaises(ValueError): c.classify(value, 0)
        value = report(); refuse_row(value, 0, copy_fault=True, null_pointer=True)
        with self.assertRaises(ValueError): c.classify(value, 0)
        value = report(); refuse_row(value, 0, copy_fault=True)
        value["bindings"][0]["registration_chain"]["image_field_hex"] = "0000000000000001"
        with self.assertRaises(ValueError): c.classify(value, 0)
        value = report(); refuse_row(value, 0)
        value["bindings"][0]["registration_chain"]["image_field_hex"] = "0000000000000001"
        result = c.classify(value, 0)
        self.assertEqual(result["outcome"], "RegistrationBindingsObserved")
        self.assertEqual((result["observed_snapshots"], result["refused_snapshots"]), (6, 1))

    def test_changed_keys_chain_types_counts_copies_and_proof_promotions_refuse(self):
        mutations = [lambda v: v.update(schema=c.copied.SCHEMA),
                     lambda v: v.update(model_default=False), lambda v: v.update(qualified_object_mip_count=1),
                     lambda v: v.update(model_callbacks=1026), lambda v: v.update(capture_ordinal=True),
                     lambda v: v.update(bindings=v["bindings"][:-1]), lambda v: v.update(header_copies=13),
                     lambda v: v.update(completed_header_bytes=0), lambda v: v.update(refused=True, reason="bad"),
                     lambda v: v["bindings"][2].update(index=1), lambda v: v["bindings"][0].update(usage_u16=65536),
                     lambda v: v["bindings"][0].update(usage_u16=True),
                     lambda v: v["bindings"][0].update(binding_hash_u32=-1),
                     lambda v: v["bindings"][0].update(leading_comma_reference=False),
                     lambda v: v["bindings"][0].update(image_pointer_present=False),
                     lambda v: v["bindings"][0].update(binding_rechecked=False),
                     lambda v: v["bindings"][0]["registration_chain"].update(material_hex="0" * 16),
                     lambda v: v["bindings"][0]["registration_chain"].update(image_field_hex="0X1"),
                     lambda v: v["bindings"][0]["snapshot"].update(completed_header_bytes=0)]
        for mutate in mutations:
            value = report(); mutate(value)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError): c.consume(value)
        for key in c.FALSES:
            for promotion in (True, 0, "false"):
                value = report(); value[key] = promotion
                with self.subTest(key=key, value=promotion), self.assertRaises(ValueError): c.consume(value)
        value = report(); value["bindings"][0]["usage_u8"] = value["bindings"][0].pop("usage_u16")
        with self.assertRaises(ValueError): c.consume(value)
        value = report(); value.update(bindings=[], bindings_enumerated=False, refused=True,
            reason="Structural refusal", header_copies=0, completed_header_bytes=None)
        value["registration_chain"]["texture_table_hex"] = "0" * 16
        with self.assertRaises(ValueError): c.consume(value)
        for exit_code in (True, "0", 2**32, -(2**31)-1):
            with self.assertRaises(ValueError): c.classify(report(), exit_code)

    def test_alias_names_hashes_and_255_utf8_bytes_are_not_selection_allowlists(self):
        value = report()
        for row in value["bindings"]:
            name = '"\\' + "é" * 126 + "a"  # Exactly 255 UTF-8 bytes, no C0.
            row.update(raw_name=name, leading_comma_reference=False, binding_hash_u32=0, usage_u16=65535)
            row["snapshot"]["image"]["image_name"] = name
            row["registration_chain"]["image_field_hex"] = value["bindings"][0]["registration_chain"]["image_field_hex"]
        self.assertEqual(c.classify(value, 0)["observed_snapshots"], 7)
        row = value["bindings"][0]
        row["raw_name"] = row["snapshot"]["image"]["image_name"] = "bad\nname"
        with self.assertRaises(ValueError): c.consume(value)

    def test_default_32k_strict_reader_duplicate_json_and_null_cli_refuse(self):
        value = report(); raw = json.dumps(value, separators=(",", ":")).encode()
        self.assertLess(len(raw), 32768)
        self.assertEqual(c.consume(c.bounded.strict_json(raw))["observed_snapshots"], 7)
        for invalid in (b'{"schema":1,"schema":2}', b'{"n":NaN}', b" " * 32769):
            with self.assertRaises(ValueError): c.bounded.strict_json(invalid)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"closed.json"; path.write_bytes(raw)
            command = [sys.executable, "-B", "-S", str(Path(c.__file__)), str(path), "--native-exit-code", "0"]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["outcome"], "RegistrationBindingsObserved")
            path.write_text("null")
            completed = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(completed.returncode, 0)


if __name__ == "__main__":
    unittest.main()
