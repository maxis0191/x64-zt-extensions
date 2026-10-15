"""Authored JSON metadata only. No producer, native fixture or provider is run."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import incoming_image_consumer as c
import selected_image_request as core
from test_selected_image_request import body_report


def sample(raw_name, zero=False):
    image = body_report()["image"]
    image["image_name"] = raw_name
    if zero:
        for key, value in image.items():
            if type(value) is int and key != "header_bytes":
                image[key] = 0
        image.update(fallback_pointer_present=False, delay_load_pixels=False)
        for part in image["parts"]:
            part.update(active=False, width=0, height=0, packed_size_raw=0,
                        key_hex="0000000000000000")
    return dict(header_observed=True, header_copies=2, completed_header_bytes=528,
                header_rechecked=True, name_rechecked=True, callback_header_name_rechecked=True,
                copy_fault=False, image=image, refused=False, reason=None)


def report():
    value = dict.fromkeys(c.FALSES, False)
    value.update(schema=c.SCHEMA, source_profile=c.PROFILE, native_source_commit=core.PIN,
                 target_name=c.TARGET, zone="mp_freerun_04", arm_phase="before_db_add_hook_create",
                 capture_phase="before_image_bypass", name_comparison_rule=c.RULE, arm_generation=1,
                 exact_argv_validated_before_arm=True, bootstrap_complete=True, map_complete=True,
                 window_complete=True, cap_refused=False, image_callbacks=2, non_target_callbacks=0,
                 callback_limit=65536, target_case_limit_per_phase=16, read_bytes=2000, read_limit=2097152,
                 reference_events=1, ordinary_name_events=1, reference_name_observed=True,
                 ordinary_name_observed=True, ordinary_absence_scope=None, refused=False, reason=None,
                 payload_bytes_read=0, qualified_object_mip_count=None)
    rows = []
    for index, (phase, category) in enumerate(c.ORDER):
        present = index in (0, 3)
        raw = (("," if category == "reference" else "") + c.TARGET) if present else None
        shot = sample(raw, zero=index == 0) if present else None
        rows.append(dict(phase=phase, name_category=category, callback_ordinal=(1 if index == 0 else 2) if present else None,
                         raw_name=raw, effective_name=c.TARGET if present else None,
                         leading_comma_reference=(category == "reference") if present else None,
                         snapshot=shot, matching_events_in_phase=int(present),
                         state="first_complete_sample" if present else "not_observed",
                         single_event_observed_in_phase=present, unique_in_phase=present,
                         repeated_headers_compared=False, conflict_absence_proven=False,
                         nonzero_descriptor_scalar_fields=sum(shot["image"][key] != 0 for key in c.NONZERO) if present else None,
                         descriptor_admissible=False))
    value["cases"] = rows
    return value


def refused(value):
    value.update(refused=True, window_complete=False, reason="Authored observation refusal")
    for row in value["cases"]:
        row["unique_in_phase"] = False
    return value


class IncomingConsumerTests(unittest.TestCase):
    def test_owned_zero_reference_and_nonzero_ordinary_remain_metadata_without_io(self):
        value = report()
        before = copy.deepcopy(value)
        with patch.object(Path, "open", side_effect=AssertionError("IO")):
            result = c.classify(value, 0)
        self.assertEqual(result["outcome"], "IncomingMetadataObserved")
        self.assertIs(result["metadata_only"], True)
        self.assertEqual(result["cases"][0]["snapshot"]["image"]["width"], 0)
        self.assertEqual(result["cases"][3]["snapshot"]["image"]["width"], 8)
        self.assertEqual(result["cases"][0]["raw_name"], ",$camo_base_normal")
        self.assertIsNone(result["cases"][1]["snapshot"])
        for key in ("descriptor_admissible", "source_asset_name_association_proven", "model_binding_correlated",
                    "renderer_binding_proven", "same_object_proven", "runtime_abi_proven", "pixels_copied", "ready"):
            self.assertIs(result[key], False)
        self.assertIsNone(result["qualified_object_mip_count"])
        self.assertEqual(value, before)

    def test_source_contract_shapes_match_without_interpreting_mips(self):
        contract = json.loads(Path(c.__file__).with_name("incoming-image-source-contract.json").read_text())
        self.assertEqual(c.OUTER, set(contract["outer_keys"]))
        self.assertEqual(c.CASE, set(contract["case_keys"]))
        self.assertEqual(c.SNAPSHOT, set(contract["snapshot_keys"]))
        self.assertEqual((len(c.OUTER), len(c.CASE), len(c.SNAPSHOT)), (42, 15, 10))

    def test_old_envelope_missing_keys_wrong_source_and_claims_refuse(self):
        with self.assertRaises(ValueError): c.consume(body_report())
        for key, value in (("schema", "iw7.t7-selected-image-metadata/2"), ("source_profile", "old"),
                           ("arm_generation", True), ("capture_phase", "after_original_model_add"),
                           ("exact_argv_validated_before_arm", False), ("payload_bytes_read", 1),
                           ("qualified_object_mip_count", 1), ("descriptor_admissible", True),
                           ("source_asset_name_association_proven", True), ("renderer_binding_proven", True),
                           ("same_object_proven", True), ("runtime_abi_proven", True), ("ready", True)):
            item = report(); item[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): c.consume(item)
        item = report(); del item["cases"]
        with self.assertRaises(ValueError): c.consume(item)

    def test_names_slot_order_snapshot_name_and_recheck_must_match(self):
        for key, value in (("raw_name", ",,$camo_base_normal"), ("raw_name", ",$Camo_base_normal"),
                           ("effective_name", "camo_base_normal"), ("phase", "map_load"),
                           ("leading_comma_reference", False), ("callback_ordinal", True)):
            item = report(); item["cases"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): c.consume(item)
        item = report(); item["cases"][0]["snapshot"]["image"]["image_name"] = c.TARGET
        with self.assertRaises(ValueError): c.consume(item)
        item = report(); item["cases"][3]["snapshot"]["name_rechecked"] = False
        with self.assertRaises(ValueError): c.consume(item)

    def test_repeated_first_sample_does_not_imply_comparison_or_uniqueness(self):
        item = report(); item["image_callbacks"] = 3; item["ordinary_name_events"] = 2
        row = item["cases"][3]
        row.update(matching_events_in_phase=2, state="repeated_target_ambiguous",
                   single_event_observed_in_phase=False, unique_in_phase=False)
        self.assertEqual(c.consume(item)["cases"][3]["state"], "repeated_target_ambiguous")
        for key in ("unique_in_phase", "repeated_headers_compared", "conflict_absence_proven"):
            altered = copy.deepcopy(item); altered["cases"][3][key] = True
            with self.subTest(key=key), self.assertRaises(ValueError): c.consume(altered)

    def test_copy_fault_and_failed_sample_remain_distinct_from_absence(self):
        item = refused(report()); row = item["cases"][3]
        row.update(state="target_matched_sample_refused", nonzero_descriptor_scalar_fields=None)
        row["snapshot"].update(header_observed=False, header_copies=1, completed_header_bytes=None,
                               header_rechecked=False, name_rechecked=False, callback_header_name_rechecked=False,
                               copy_fault=True, image=None, refused=True, reason="Authored partial fault")
        result = c.classify(item, 1)
        self.assertEqual(result["outcome"], "IncomingMetadataRefused")
        self.assertEqual(result["cases"][3]["state"], "target_matched_sample_refused")
        altered = copy.deepcopy(item); altered["cases"][3]["snapshot"]["completed_header_bytes"] = 264
        with self.assertRaises(ValueError): c.consume(altered)
        with self.assertRaises(ValueError): c.classify(item, 0)

    def test_caps_keep_trigger_counts_and_incomplete_windows_do_not_claim_uniqueness(self):
        item = refused(report()); item.update(cap_refused=True, image_callbacks=65537,
                                              non_target_callbacks=65534, read_bytes=600000)
        self.assertEqual(c.consume(item)["observation_status"], "refused")
        altered = copy.deepcopy(item); altered["cap_refused"] = False
        with self.assertRaises(ValueError): c.consume(altered)
        item = refused(report()); item.update(cap_refused=True, image_callbacks=18, ordinary_name_events=17)
        item["cases"][3].update(matching_events_in_phase=17, state="repeated_target_ambiguous",
                                single_event_observed_in_phase=False)
        self.assertFalse(c.consume(item)["window_complete"])
        item["window_complete"] = True
        with self.assertRaises(ValueError): c.consume(item)
        item = refused(report()); item.update(bootstrap_complete=False, map_complete=False)
        with self.assertRaises(ValueError): c.consume(item)

    def test_absence_is_only_bounded_and_null_samples_never_become_zero_headers(self):
        item = report(); item.update(image_callbacks=1, ordinary_name_events=0, ordinary_name_observed=False,
                                     ordinary_absence_scope="not_observed_in_this_bounded_callback_window")
        item["cases"][3] = copy.deepcopy(item["cases"][1]); item["cases"][3]["phase"] = "map_load"
        self.assertIsNone(c.consume(item)["cases"][3]["snapshot"])
        altered = copy.deepcopy(item); altered["cases"][3]["snapshot"] = {}
        with self.assertRaises(ValueError): c.consume(altered)
        item = refused(item); item.update(map_complete=False, ordinary_absence_scope="partial_or_refused_callback_window")
        self.assertFalse(c.classify(item, 1)["window_complete"])

    def test_raw_dto_metadata_is_shared_and_does_not_enable_object_selection(self):
        image = sample(",$camo_base_normal", zero=True)["image"]
        core.validate_copied_image_metadata(image)
        with self.assertRaises(ValueError): core.select_copied_image(image, part_index=0, qualified_object_mip_count=None)
        item = report(); item["cases"][0]["snapshot"]["image"]["parts"][0]["active"] = True
        with self.assertRaises(ValueError): c.consume(item)
        item = report(); item["cases"][3]["nonzero_descriptor_scalar_fields"] = True
        with self.assertRaises(ValueError): c.consume(item)

    def test_original_exit_no_report_and_json_null_are_not_promoted(self):
        self.assertEqual(c.classify(report(), 1)["outcome"], "ValidIncomingMetadataFromFailedProcess")
        self.assertEqual(c.classify(None, 0)["outcome"], "NoReport")
        with self.assertRaises(ValueError): c.classify(report(), True)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "authored.json"; path.write_text("null")
            with patch.object(sys, "argv", ["consumer", str(path), "--native-exit-code", "0"]):
                with self.assertRaises(ValueError): c.main()

    def test_read_budget_must_cover_known_copies_and_filtering_without_guessing_fault_bytes(self):
        for budget in (0, 1056, 1182):
            item = report(); item["read_bytes"] = budget
            with self.subTest(budget=budget), self.assertRaises(ValueError): c.consume(item)
        item = report(); item["read_bytes"] = 1183
        self.assertEqual(c.classify(item, 0)["outcome"], "IncomingMetadataObserved")

    def test_repeated_counts_must_fit_phase_positions_beyond_the_first_samples(self):
        item = report(); item.update(image_callbacks=3, reference_events=2)
        item["cases"][0].update(matching_events_in_phase=2, state="repeated_target_ambiguous",
                                single_event_observed_in_phase=False, unique_in_phase=False)
        with self.assertRaises(ValueError): c.classify(item, 0)
        item["cases"][3]["callback_ordinal"] = 3
        self.assertEqual(c.classify(item, 0)["outcome"], "IncomingMetadataObserved")
        item = report(); item.update(image_callbacks=3, ordinary_name_events=2)
        item["cases"][3].update(callback_ordinal=3, matching_events_in_phase=2,
                                state="repeated_target_ambiguous", single_event_observed_in_phase=False, unique_in_phase=False)
        with self.assertRaises(ValueError): c.classify(item, 0)


if __name__ == "__main__":
    unittest.main()
