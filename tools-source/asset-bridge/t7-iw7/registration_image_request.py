"""Pure selection from registration-owned metadata; no historical pointer/IO read.

The two 264-byte copies and owned name were rechecked at the registration
callback. The separate F2 lookup may be nonreadable. Numerical chain continuity
is only an association filter and never proves object identity or lifetime.
"""
import image_metadata_consumer as provenance
import selected_image_request as selected

SCHEMA = "iw7.t7-registration-image-header-metadata/1"
PROFILE = "t7-registration-image-header-metadata-v1"
PHASE = "after_original_model_add"
TRUES = ("registration_header_observed", "association_rechecked_at_registration",
         "header_rechecked_at_registration", "name_rechecked_at_registration")
OUTER = (selected.OUTER - set(selected.TRUES)) | set(TRUES) | {
    "capture_phase", "capture_ordinal", "recheck_phase",
    "registration_header_bytes_copied", "same_object_proven",
}


def select_registration_image(report, *, part_index, native_exit_code, qualified_object_mip_count):
    """Validate registration scope, then reuse the existing whole-object selector.

    qualified_object_mip_count is a separately qualified fact with no default.
    This function does not authorize extraction or dereference any game pointer.
    """
    need, uint = selected.need, selected.uint
    need(type(native_exit_code) is int and native_exit_code == 0,
         "successful original native exit required")
    need(type(report) is dict and set(report) == OUTER,
         "exact closed registration report required; F2 or lookup v1 is insufficient")
    need(report["schema"] == SCHEMA and report["source_profile"] == PROFILE and
         report["native_source_commit"] == selected.PIN and report["zone"] == "mp_freerun_04" and
         report["model"] == provenance.MODEL, "exact registration source/selector required")
    need(report["capture_phase"] == PHASE and report["recheck_phase"] == PHASE,
         "copy and rechecks must occur at registration, never lookup")
    for name in (*selected.FALSES, "same_object_proven"):
        need(report[name] is False, "refused/default/proof promotion cannot select an object")
    for name in TRUES:
        need(report[name] is True, "registration body/association/header/name must be rechecked")
    for name, value in (("lod", 0), ("slot", 0), ("binding_index", 4),
                        ("binding_hash_u32", provenance.HASH), ("image_header_bytes", 264),
                        ("header_copies", 2), ("registration_header_bytes_copied", 528),
                        ("payload_bytes_read", 0)):
        need(uint(report[name]) == value, "exact registration selector/copy scope required")
    need(report["failure_stage"] is None and report["reason"] is None,
         "native refusal diagnostic cannot select an object")
    observed = provenance.consume(report["provenance"])
    need(observed["observation_status"] == "complete", "same-pass F2 association incomplete")
    f2 = report["provenance"]
    registration = f2["registration"]
    need(f2["matched_registrations"] == 1 and registration["binding_rechecked"] is True and
         registration["query_complete"] is True and registration["range_readable_at_query"] is True,
         "unique rechecked readable registration required")
    need(uint(report["capture_ordinal"], 2**64-1) == registration["ordinal"],
         "capture ordinal must match the same-pass F2 registration")
    comparisons = observed["comparisons"]
    need(all(comparisons[name] is False for name in
             ("header_changed", "material_changed", "texture_table_changed")) and
         comparisons["same_numeric_image_field"] is True,
         "numerical association changed; this filter proves no lifetime or identity")
    return selected.select_copied_image(report["image"], part_index=part_index,
                                        qualified_object_mip_count=qualified_object_mip_count)
