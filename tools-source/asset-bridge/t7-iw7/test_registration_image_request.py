"""Authored registration copies/F2 metadata only; no native, game or provider IO."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import image_metadata_consumer as provenance
import registration_image_request as registration
import selected_image_request as selected
from test_selected_image_request import body_report


def registration_report():
    report = body_report()
    for legacy, current in zip(selected.TRUES, registration.TRUES):
        report[current] = report.pop(legacy)
    report.update(schema=registration.SCHEMA, source_profile=registration.PROFILE,
                  capture_phase=registration.PHASE, recheck_phase=registration.PHASE,
                  capture_ordinal=1, registration_header_bytes_copied=528,
                  same_object_proven=False)
    lookup = report["provenance"]["lookup"]
    lookup["range_readable_at_query"] = False
    lookup["regions"][0].update(state_raw=0x2000, protect_raw=0)
    return report


def select(report, **kwargs):
    args = dict(part_index=1, native_exit_code=0, qualified_object_mip_count=1)
    args.update(kwargs)
    return registration.select_registration_image(report, **args)


class RegistrationRequestTests(unittest.TestCase):
    def test_owned_registration_survives_nonreadable_lookup_without_io_or_proof_promotion(self):
        report = registration_report()
        before = copy.deepcopy(report)
        with patch.object(Path, "open", side_effect=AssertionError("IO")):
            request = select(report)
        self.assertIs(type(request), selected.SelectedImageRequest)
        self.assertEqual((request.image_name, request.key_hex, request.expected_bytes,
                          request.image.dxgi_format, request.image.level_count),
                         ("authored_image", "deadbeef00000002", 32, 72, 1))
        self.assertEqual(request.raw_packed_size & 15, 3)
        self.assertEqual(report, before)
        result = provenance.consume(report["provenance"])
        self.assertFalse(result["epochs"][1]["range_readable_at_query"])
        self.assertTrue(result["reference_only"])
        for key in ("image_header_admitted", "same_object_proven", "lifetime_proven", "ready"):
            self.assertFalse(result[key])

    def test_lookup_readability_is_not_required_or_fabricated(self):
        report = registration_report()
        report["provenance"] = body_report()["provenance"]
        self.assertEqual(select(report).expected_bytes, 32)

    def test_old_envelope_and_f2_cannot_be_relabelled_as_registration(self):
        for report in (body_report(), body_report()["provenance"], None):
            with self.subTest(report=type(report)), self.assertRaises(ValueError):
                select(report)
        with self.assertRaises(ValueError):
            selected.select_image(registration_report(), part_index=1,
                                  native_exit_code=0, qualified_object_mip_count=1)

    def test_missing_wrong_phase_source_and_copy_counts_refuse(self):
        for key, value in (("schema", selected.SCHEMA), ("source_profile", "t7-image-metadata-v1"),
                           ("capture_phase", "after_zone_model_lookup"),
                           ("recheck_phase", "after_zone_model_lookup"),
                           ("capture_ordinal", 0), ("capture_ordinal", True),
                           ("header_copies", 1), ("image_header_bytes", 528),
                           ("registration_header_bytes_copied", 264),
                           ("registration_header_bytes_copied", True)):
            report = registration_report()
            report[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                select(report)
        report = registration_report()
        del report["capture_phase"]
        with self.assertRaises(ValueError):
            select(report)

    def test_unreadable_registration_and_incomplete_association_refuse(self):
        report = registration_report()
        epoch = report["provenance"]["registration"]
        epoch["range_readable_at_query"] = False
        epoch["regions"][0].update(state_raw=0x2000, protect_raw=0)
        self.assertEqual(provenance.consume(report["provenance"])["observation_status"], "complete")
        with self.assertRaises(ValueError):
            select(report)
        for key in ("binding_rechecked", "query_complete"):
            report = registration_report()
            report["provenance"]["registration"][key] = False
            with self.subTest(key=key), self.assertRaises(ValueError):
                select(report)

    def test_changed_numerical_chain_refuses_without_claiming_object_identity(self):
        for key in ("selected_model_header_hex", "material_hex", "texture_table_hex", "image_field_hex"):
            report = registration_report()
            f2 = report["provenance"]
            f2["lookup"][key] = "0000000000005020"
            if key == "selected_model_header_hex":
                f2["header_changed"] = True
            elif key == "image_field_hex":
                f2["same_numeric_image_field"] = False
            self.assertEqual(provenance.consume(f2)["observation_status"], "complete")
            with self.subTest(key=key), self.assertRaises(ValueError):
                select(report)

    def test_refusal_missing_name_and_runtime_proof_claims_refuse(self):
        for key, value in (("registration_header_observed", False),
                           ("association_rechecked_at_registration", False),
                           ("header_rechecked_at_registration", False),
                           ("name_rechecked_at_registration", False),
                           ("model_default", True), ("refused", True),
                           ("same_object_proven", True), ("allocation_retained", True),
                           ("atomic_snapshot_proven", True), ("runtime_abi_proven", True),
                           ("lifetime_proven", True), ("ready", True),
                           ("pixels_copied", True), ("payload_bytes_read", 1),
                           ("reason", ""), ("failure_stage", "")):
            report = registration_report()
            report[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                select(report)
        report = registration_report()
        report["image"].update(image_name=None, image_name_observed=False)
        with self.assertRaises(ValueError):
            select(report)

    def test_original_exit_and_mip_fact_are_required_without_defaults(self):
        for code in (1, -1, True):
            with self.subTest(code=code), self.assertRaises(ValueError):
                select(registration_report(), native_exit_code=code)
        for count in (None, False, 2):
            with self.subTest(count=count), self.assertRaises(ValueError):
                select(registration_report(), qualified_object_mip_count=count)
        with self.assertRaises(TypeError):
            registration.select_registration_image(registration_report(), part_index=1,
                                                   native_exit_code=0)


if __name__ == "__main__":
    unittest.main()
