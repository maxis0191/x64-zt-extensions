#pragma once

// Reuse the existing G3 checked reader/capture; F2's observer and schema stay intact.
#include "selected_material_parts_observation.hpp"
#include "selected_image_header_metadata.hpp"
#include "selected_image_metadata_read_guard.hpp"
#ifndef IW7_SELECTED_IMAGE_METADATA_GUARD_INSTALLED
#error This adapter requires the sealed metadata overlay guard before G2 typed image fields
#endif

namespace zonetool::t7::selected_image_metadata
{
    namespace base = selected_material_observation;
    namespace capture_api = selected_material_parts_observation;
    namespace scalar_api = selected_image_header_metadata;

    inline nlohmann::ordered_json envelope(bool nondefault_lookup_confirmed)
    {
        return {{"schema", "iw7.t7-selected-image-metadata/1"},
            {"source_profile", "t7-image-metadata-v1"},
            {"native_source_commit", "fab935826c898806855376662a8a03317b3ad8f1"},
            {"zone", "mp_freerun_04"}, {"model", "p7_fre_platform_cap_02"},
            {"model_default", nondefault_lookup_confirmed ? nlohmann::ordered_json(false) : nlohmann::ordered_json(nullptr)},
            {"lod", 0}, {"slot", 0}, {"binding_index", 4}, {"binding_hash_u32", 0xA0AB1041u},
            {"image_header_bytes", 264}, {"header_copies", 0}, {"body_observed", false},
            {"association_rechecked", false}, {"header_rechecked", false}, {"name_rechecked", false},
            {"refused", true}, {"failure_stage", nullptr}, {"reason", nullptr},
            {"image", nullptr}, {"provenance", nullptr}, {"allocation_retained", false},
            {"atomic_snapshot_proven", false}, {"pixels_copied", false}, {"payload_bytes_read", 0},
            {"runtime_abi_proven", false}, {"lifetime_proven", false}, {"ready", false}};
    }

    template <typename Readable> nlohmann::ordered_json observe(const XModel* source,
        const nlohmann::ordered_json& provenance, Readable readable, bool nondefault_lookup_confirmed)
    {
        auto result = envelope(nondefault_lookup_confirmed);
        capture_api::header_capture<Readable> capture(readable);
        try
        {
            result["provenance"] = provenance;
            resident_image::require(nondefault_lookup_confirmed && source &&
                provenance.at("schema") == "iw7.t7-selected-image-provenance/1" &&
                provenance.at("capture_complete") == true && provenance.at("refused") == false &&
                provenance.at("model") == "p7_fre_platform_cap_02" && provenance.at("lod") == 0 &&
                provenance.at("slot") == 0 && provenance.at("binding_index") == 4 &&
                provenance.at("binding_name_hash") == 0xA0AB1041u,
                "Complete scoped F2 provenance and fresh nondefault lookup required");
            const base::image_binding_selection selection{4, 0xA0AB1041u};
            const selected_image_metadata_read_guard::scope raw_boolean_guard;
            const auto observed = nlohmann::ordered_json::parse(base::observe_binding(source,
                "p7_fre_platform_cap_02", 0, 0,
                [&](const void* pointer, std::size_t bytes) { capture.range(pointer, bytes); }, selection));
            resident_image::require(!observed.value("refused", false) && observed.at("headers_rechecked") == true &&
                observed.at("model") == "p7_fre_platform_cap_02" && observed.at("lod") == 0 &&
                observed.at("slot") == 0 && selection.index < observed.at("textures").size(),
                "Existing selected-header association guard refused");
            const auto& row = observed.at("textures").at(selection.index);
            resident_image::require(row.at("index") == selection.index && row.at("nameHash") == selection.expected_name_hash &&
                row.at("image_header_read") == true && row.at("image_read_state") == "observed" &&
                row.contains("image_name") && row.at("image_name").is_string(),
                "Exact selected header and owned rechecked name required");
            resident_image::require(!capture.ambiguous && capture.count == 2 &&
                capture.addresses[0] == capture.addresses[1] &&
                std::memcmp(&capture.headers[0], &capture.headers[1], sizeof(GfxImage)) == 0 &&
                base::image_metadata(capture.headers[0]) == row.at("image"),
                "Owned selected headers changed or were ambiguous");
            const scalar_api::admission gate{scalar_api::source_profile, 264, true, true, true, true};
            result["image"] = scalar_api::build(capture.headers[0], gate,
                std::optional<std::string>{row.at("image_name").get<std::string>()});
            result["header_copies"] = capture.count;
            result["body_observed"] = true;
            result["association_rechecked"] = true;
            result["header_rechecked"] = true;
            result["name_rechecked"] = true;
            result["refused"] = false;
            resident_image::require(result.dump().size() <= base::output_limit, "Metadata envelope exceeds 32 KiB");
            return result;
        }
        catch (const std::exception& error)
        {
            // Retain observed copy count but publish no accepted metadata after any refusal.
            result["header_copies"] = capture.count;
            result["body_observed"] = false;
            result["association_rechecked"] = false;
            result["header_rechecked"] = false;
            result["name_rechecked"] = false;
            result["image"] = nullptr;
            result["refused"] = true;
            result["failure_stage"] = "selected_header_metadata";
            result["reason"] = std::string(error.what()).substr(0, 256);
            try { if (result.dump().size() <= base::output_limit) return result; }
            catch (const std::exception&) {}
            auto fallback = envelope(nondefault_lookup_confirmed);
            fallback["header_copies"] = capture.count;
            fallback["failure_stage"] = "serialization";
            fallback["reason"] = "Bounded metadata diagnostic serialization refused";
            return fallback;
        }
    }
}
