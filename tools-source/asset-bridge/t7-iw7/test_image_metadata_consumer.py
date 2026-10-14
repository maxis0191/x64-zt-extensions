"""Authored JSON cases only: no native producer, engine or memory query runs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import image_metadata_consumer as c


def epoch(phase, ordinal, readable=True):
    row = {"base_hex": "0000000000005000", "allocation_base_hex": "0000000000005000",
           "region_extent": 4096, "state_raw": 0x1000 if readable else 0x10000,
           "protect_raw": 4 if readable else 1, "type_raw": 0x20000 if readable else 0}
    value = dict.fromkeys(c.EBOOLS, False)
    value.update(dict.fromkeys(c.POINTERS, None))
    value.update(phase=phase, ordinal=ordinal, thread_id=17, tick_milliseconds=100+ordinal,
                 lod=0, slot=0, binding_index=4, expected_binding_name_hash=c.HASH,
                 binding_observed=True, texture_count=7, binding_rechecked=True, failure="",
                 queried_span_bytes=264, query_complete=True, range_readable_at_query=readable,
                 regions=[row], image_body_bytes_read=0,
                 selected_model_header_hex="0000000000002000", material_hex="0000000000003000",
                 texture_table_hex="0000000000004000", image_field_hex="0000000000005010")
    if phase == "after_original_model_add":
        value["incoming_model_header_hex"] = "0000000000001000"
    return value


def report(readable=True):
    value = dict.fromkeys(c.BOOLS, False)
    value.update(dict.fromkeys(c.ZEROES, 0))
    value.update(schema="iw7.t7-selected-image-provenance/1", model=c.MODEL, lod=0, slot=0,
                 binding_index=4, binding_name_hash=c.HASH, model_callbacks=6, matched_registrations=1,
                 capture_complete=True, association_complete=True, header_changed=False,
                 same_numeric_image_field=True,
                 registration=epoch("after_original_model_add", 1, readable),
                 lookup=epoch("after_zone_model_lookup", 2, readable))
    return value


def refused(value, associated=False):
    value.update(capture_complete=False, refused=True, association_complete=associated)
    if not associated:
        value.update(header_changed=None, same_numeric_image_field=None)
    return value


def missing_registration():
    value = refused(report())
    value["matched_registrations"] = 0
    item = value["registration"]
    item.update(ordinal=0, thread_id=0, tick_milliseconds=0, binding_observed=False,
                binding_rechecked=False, query_complete=False, range_readable_at_query=False,
                texture_count=None, regions=[])
    item.update(dict.fromkeys(c.POINTERS, None))
    value["lookup"]["ordinal"] = 1
    return value


class ConsumerTests(unittest.TestCase):
    def test_complete_readable_still_has_no_body_admission_or_identity_proof(self):
        result = c.classify(report(), 0)
        self.assertEqual(result["outcome"], "ProvenanceMetadataObserved")
        self.assertEqual(result["refusal_reasons"], [])
        for name in ("image_header_admitted", "extraction_authorized", "pointer_transform_authorized",
                     "same_object_proven", "lifetime_proven", "authentic_bo3_texture_proven", "ready"):
            self.assertIs(result[name], False)

    def test_complete_mem_free_is_valid_and_readability_is_preserved(self):
        result = c.classify(report(False), 0)
        self.assertEqual(result["observation_status"], "complete")
        self.assertFalse(result["epochs"][0]["range_readable_at_query"])
        self.assertFalse(result["image_header_admitted"])

    def test_guard_and_noaccess_are_unreadable_not_incomplete_queries(self):
        for state, protect in ((0x1000, 0x104), (0x1000, 1), (0x2000, 4)):
            value = report(False)
            for item in (value["registration"], value["lookup"]):
                item["regions"][0].update(state_raw=state, protect_raw=protect)
            self.assertEqual(c.consume(value)["observation_status"], "complete")

    def test_two_regions_cover_exact_span_without_body_access(self):
        value = report()
        for item in (value["registration"], value["lookup"]):
            item["image_field_hex"] = "0000000000005ff0"
            item["regions"].append(dict(item["regions"][0], base_hex="0000000000006000"))
        self.assertEqual(c.consume(value)["observation_status"], "complete")

    def test_header_and_material_changes_are_independent_numeric_comparisons(self):
        value = report()
        value["lookup"].update(selected_model_header_hex="0000000000002100",
                               material_hex="0000000000003100", texture_table_hex="0000000000004100")
        value["header_changed"] = True
        result = c.consume(value)
        self.assertEqual(result["comparisons"], {"header_changed": True, "same_numeric_image_field": True,
                         "incoming_equals_returned": False, "material_changed": True, "texture_table_changed": True})
        self.assertFalse(result["same_object_proven"])

    def test_incoming_header_zero_is_scalar_and_not_dereferenced(self):
        value = report()
        value["registration"]["incoming_model_header_hex"] = "0000000000000000"
        self.assertFalse(c.consume(value)["comparisons"]["incoming_equals_returned"])

    def test_no_selected_registration_keeps_null_fields_and_comparisons(self):
        result = c.classify(missing_registration(), 1)
        self.assertIn("no_selected_registration", result["refusal_reasons"])
        self.assertIsNone(result["comparisons"]["incoming_equals_returned"])

    def test_unobserved_binding_cannot_invent_a_memory_query(self):
        for flag in ("query_complete", "range_readable_at_query", "query_failed", "range_overflow", "region_limit_refused"):
            value = missing_registration()
            value["registration"][flag] = True
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, "query metadata requires an observed binding"):
                c.consume(value)
        value = missing_registration()
        value["registration"].update(query_complete=True, range_readable_at_query=True)
        with self.assertRaisesRegex(ValueError, "query metadata requires an observed binding"):
            c.consume(value)
        value = missing_registration()
        value["registration"]["regions"] = report()["registration"]["regions"]
        with self.assertRaisesRegex(ValueError, "query metadata requires an observed binding"):
            c.consume(value)

    def test_late_recheck_failure_preserves_observed_fields_without_association(self):
        value = refused(report())
        value["registration"].update(binding_rechecked=False, failure="Material changed after query")
        result = c.classify(value, 1)
        self.assertIn("registration_association_not_rechecked", result["refusal_reasons"])
        self.assertIsNone(result["comparisons"]["material_changed"])
        self.assertTrue(result["epochs"][0]["query_complete"])
        self.assertTrue(result["epochs"][0]["range_readable_at_query"])

    def test_null_image_overflow_is_a_valid_refused_query(self):
        value = refused(report(), associated=True)
        for item in (value["registration"], value["lookup"]):
            item.update(image_field_hex="0000000000000000", query_complete=False,
                        range_readable_at_query=False, range_overflow=True, regions=[])
        result = c.classify(value, 1)
        self.assertEqual(result["outcome"], "ProvenanceMetadataRefused")
        self.assertTrue(result["epochs"][0]["range_overflow"])

    def test_query_failure_and_region_limit_are_preserved(self):
        for flag in ("query_failed", "region_limit_refused"):
            value = refused(report(), associated=True)
            value["lookup"].update(query_complete=False, range_readable_at_query=False)
            value["lookup"][flag] = True
            self.assertTrue(c.classify(value, 1)["epochs"][1][flag])

    def test_duplicate_and_search_refusal_do_not_discard_first_association(self):
        for flag in ("duplicate_registration", "registration_search_refused"):
            value = refused(report(), associated=True)
            value[flag] = True
            if flag == "duplicate_registration":
                value["matched_registrations"] = 2
            else:
                value["model_callbacks"] = 2048
            self.assertIn(flag, c.classify(value, 1)["refusal_reasons"])

    def test_nonzero_exit_is_not_promoted_when_metadata_is_complete(self):
        self.assertEqual(c.classify(report(), -1)["outcome"], "ValidMetadataFromFailedProcess")
        self.assertEqual(c.classify(None, 1)["outcome"], "NoReport")
        self.assertEqual(c.classify(None, 0)["outcome"], "NoReport")

    def test_refused_capture_and_zero_exit_contradict(self):
        value = refused(report(), associated=True)
        value.update(duplicate_registration=True, matched_registrations=2)
        with self.assertRaises(ValueError):
            c.classify(value, 0)

    def test_exact_schema_selector_fields_and_types_refuse(self):
        changes = [("schema", "iw7.t7-selected-material-observation/3"), ("model", "other"),
                   ("lod", 1), ("slot", True), ("binding_index", 3), ("binding_name_hash", "a0ab1041"),
                   ("model_callbacks", True), ("capture_complete", 1)]
        for name, replacement in changes:
            value = report(); value[name] = replacement
            with self.subTest(name=name), self.assertRaises(ValueError):
                c.consume(value)
        for key in ("new_field", "image_name", "xpak_key_hex"):
            value = report(); value[key] = "invented"
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.consume(value)

    def test_zero_bytes_and_proof_flags_cannot_be_promoted(self):
        for key in c.FALSES + c.ZEROES:
            value = report(); value[key] = 1 if key in c.ZEROES else True
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.consume(value)
        for key, replacement in (("atomic_snapshot_proven", True), ("image_body_bytes_read", 1)):
            value = report(); value["lookup"][key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.consume(value)

    def test_pointer_nullability_canonical_hex_and_ordinal_order_refuse(self):
        for key, replacement in (("incoming_model_header_hex", "0000000000001000"),
                                 ("image_field_hex", None), ("material_hex", "0x3000"),
                                 ("selected_model_header_hex", "000000000000ABCD"), ("ordinal", 3)):
            value = report(); value["lookup"][key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.consume(value)

    def test_association_and_capture_comparisons_cannot_be_invented(self):
        for name, replacement in (("association_complete", False), ("capture_complete", False),
                                  ("header_changed", True), ("same_numeric_image_field", False),
                                  ("duplicate_registration", True)):
            value = report(); value[name] = replacement
            with self.subTest(name=name), self.assertRaises(ValueError):
                c.consume(value)
        value = refused(report()); value["registration"]["binding_rechecked"] = False
        value["header_changed"] = False
        with self.assertRaises(ValueError):
            c.consume(value)

    def test_complete_rechecked_coverage_or_readability_contradictions_refuse(self):
        for change in ("gap", "short", "overflow", "third", "readability", "queryflag"):
            value = report(); item = value["lookup"]
            if change == "gap": item["regions"][0]["base_hex"] = "0000000000005020"
            if change == "short": item["regions"][0]["region_extent"] = 32
            if change == "overflow": item["regions"][0]["region_extent"] = c.MAX64
            if change == "third": item["regions"] *= 3
            if change == "readability": item["range_readable_at_query"] = False
            if change == "queryflag": item["query_failed"] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                c.consume(value)

    def test_invalid_query_retained_by_refused_binding_is_not_promoted(self):
        value = refused(report())
        value["registration"].update(binding_rechecked=False, failure="Invalid scripted query coverage")
        value["registration"]["regions"][0]["region_extent"] = 1
        self.assertEqual(c.consume(value)["observation_status"], "refused")

    def test_raw_json_bounds_duplicate_keys_nonfinite_and_utf8_refuse(self):
        for raw in (b"", b" "*(c.LIMIT+1), b'{"schema":1,"schema":2}', b'{"x":NaN}',
                    b'{"x":Infinity}', b'"\xff"'):
            with self.subTest(raw=raw[:40]), self.assertRaises((ValueError, UnicodeError)):
                c.strict_json(raw)
        self.assertEqual(c.strict_json(json.dumps(report()).encode())["model"], c.MODEL)

    def test_cli_reads_only_existing_json_and_does_not_fabricate_missing_report(self):
        script = str(Path(c.__file__).resolve())
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/"existing.json"
            target.write_text(json.dumps(report(False)), encoding="utf-8")
            before = target.read_bytes()
            run = subprocess.run([sys.executable, "-B", script, str(target), "--native-exit-code", "0"],
                                 capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)["outcome"], "ProvenanceMetadataObserved")
            self.assertEqual(target.read_bytes(), before)
            missing = subprocess.run([sys.executable, "-B", script, str(Path(temp)/"missing.json")],
                                     capture_output=True, text=True, timeout=10)
            self.assertNotEqual(missing.returncode, 0)
            self.assertEqual(missing.stdout, "")
            self.assertEqual(set(Path(temp).iterdir()), {target})
            target.write_text("null", encoding="utf-8")
            invalid = subprocess.run([sys.executable, "-B", script, str(target), "--native-exit-code", "1"],
                                     capture_output=True, text=True, timeout=10)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertEqual(invalid.stdout, "")
            self.assertEqual(target.read_text(encoding="utf-8"), "null")


if __name__ == "__main__":
    unittest.main()
