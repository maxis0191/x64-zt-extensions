#pragma once
// Same MODEL callback, one material and seven owned binding samples. No asset lookup.
#include "selected_image_material_bindings_capture.hpp"

namespace zonetool::t7::registration_material_bindings
{
    namespace base = selected_material_observation;
    namespace scalar = selected_image_header_metadata;
    namespace capture = registration_image_header_capture;
    inline constexpr char schema[] = "iw7.t7-registration-material-bindings/1";
    inline constexpr char profile[] = "t7-registration-material-bindings-v1";
    inline constexpr unsigned binding_count = 7;
    inline constexpr unsigned header_limit = binding_count * 2 * capture::span;
    static_assert(sizeof(MaterialTextureDef::usage) == 2 && sizeof(MaterialTextureDef::nameHash) == 4);

    class collector
    {
        bool attempted_{}, enumerated_{}, bytes_known_ = true;
        std::uint64_t ordinal_{};
        unsigned copies_{};
        std::uintptr_t model_{}, material_{}, table_{};
        nlohmann::ordered_json rows_ = nlohmann::ordered_json::array();
        std::array<char, 256> error_{};

        void fail(const char* why) noexcept
        {
            enumerated_ = false; bytes_known_ = false;
            if (!why) why = "Registration material bindings refused";
            unsigned i = 0;
            for (; i < error_.size()-1 && why[i]; ++i) error_[i] = why[i];
            error_[i] = 0;
        }

    public:
        template <typename Readable, typename Query, typename Copy>
        void record(std::uint64_t ordinal, const XModel* pointer,
            Readable readable, Query query, Copy copy) noexcept
        {
            try
            {
                scalar::require(!attempted_, "Material bindings capture is single-use");
                attempted_ = true; ordinal_ = ordinal;
                model_ = reinterpret_cast<std::uintptr_t>(pointer);
                scalar::require(ordinal && pointer, "Original MODEL registration required");
                base::reader<Readable> read(readable); // One shared 64-KiB metadata budget.
                const auto model = read.one(pointer);
                scalar::require(read.name(model.name) == "p7_fre_platform_cap_02" &&
                    model.numLods && model.numLods <= 8, "Exact registration model/LOD required");
                const auto lods = read.array(model.meshMaterials, model.numLods, 8);
                const auto table = lods[0];
                scalar::require(table.numMaterials && table.numMaterials <= 32,
                    "Bounded registration material table required");
                const auto materials = read.array(table.materials, table.numMaterials, 32);
                const auto material = read.one(materials[0]);
                scalar::require(material.textureCount == binding_count,
                    "Exactly seven registration bindings required");
                const auto textures = read.array(material.textureTable, binding_count, binding_count);
                material_ = reinterpret_cast<std::uintptr_t>(materials[0]);
                table_ = reinterpret_cast<std::uintptr_t>(material.textureTable);
                const auto recheck_chain = [&]
                {
                    read.unchanged(materials[0], material);
                    read.unchanged(table.materials, materials[0]);
                    read.unchanged(model.meshMaterials, table);
                    read.unchanged(pointer, model);
                    scalar::require(read.name(model.name) == "p7_fre_platform_cap_02",
                        "Registration model name changed");
                };
                for (unsigned i = 0; i < binding_count; ++i)
                {
                    const auto binding = textures[i];
                    capture::cache sample;
                    sample.reset();
                    // A refused row never terminates the following rows.
                    sample.record_binding(binding.image,
                        [&] { read.unchanged(material.textureTable+i, binding); recheck_chain(); },
                        [&](const void* p, std::size_t n) { read.range(p,n); }, query, copy);
                    auto snapshot = sample.incoming_snapshot(); // Existing closed ten-key shape.
                    const bool observed = snapshot.at("header_observed") == true;
                    const auto name = observed ? snapshot.at("image").at("image_name") :
                        nlohmann::ordered_json(nullptr);
                    const auto chain = nlohmann::ordered_json{
                        {"model_header_hex", scalar::key_hex(model_)},
                        {"material_hex", scalar::key_hex(material_)},
                        {"texture_table_hex", scalar::key_hex(table_)},
                        {"image_field_hex", scalar::key_hex(reinterpret_cast<std::uintptr_t>(binding.image))}};
                    rows_.push_back({{"index", i}, {"binding_hash_u32", binding.nameHash},
                        {"usage_u16", binding.usage}, {"image_pointer_present", binding.image != nullptr},
                        {"raw_name", name}, {"leading_comma_reference", observed ?
                            nlohmann::ordered_json(name.template get<std::string>()[0] == ',') : nlohmann::ordered_json(nullptr)},
                        {"registration_chain", chain}, {"binding_rechecked", observed},
                        {"snapshot", std::move(snapshot)}});
                    const auto& saved = rows_.back().at("snapshot");
                    copies_ += saved.at("header_copies").template get<unsigned>();
                    bytes_known_ = bytes_known_ && !saved.at("completed_header_bytes").is_null();
                }
                // Detect changes in any table row, including an independently refused image.
                for (unsigned i = 0; i < binding_count; ++i)
                    read.unchanged(material.textureTable+i, textures[i]);
                recheck_chain();
                enumerated_ = true;
            }
            catch (const std::exception& error) { fail(error.what()); }
            catch (...) { fail("Unknown registration material bindings refusal"); }
        }

        nlohmann::ordered_json finish(unsigned callbacks, unsigned matches, bool duplicate,
            bool search_refused, bool zone_complete) const
        {
            const bool complete = attempted_ && enumerated_ && zone_complete && matches == 1 &&
                !duplicate && !search_refused && rows_.size() == binding_count;
            nlohmann::ordered_json result = {{"schema", schema}, {"source_profile", profile},
                {"native_source_commit", "fab935826c898806855376662a8a03317b3ad8f1"},
                {"zone", "mp_freerun_04"}, {"model", "p7_fre_platform_cap_02"}, {"lod", 0}, {"slot", 0},
                {"model_default", nullptr}, {"capture_phase", "after_original_model_add"},
                {"recheck_phase", "after_original_model_add"}, {"capture_ordinal", ordinal_},
                {"model_callbacks", callbacks}, {"matched_registrations", matches},
                {"duplicate_registration", duplicate}, {"registration_search_refused", search_refused},
                {"zone_load_complete", zone_complete}, {"bindings_enumerated", enumerated_},
                {"registration_chain", {{"model_header_hex", scalar::key_hex(model_)},
                    {"material_hex", scalar::key_hex(material_)}, {"texture_table_hex", scalar::key_hex(table_)}}},
                {"bindings", rows_}, {"binding_count", binding_count}, {"image_header_bytes", capture::span},
                {"header_copies", copies_}, {"completed_header_bytes", bytes_known_ ?
                    nlohmann::ordered_json(copies_*capture::span) : nlohmann::ordered_json(nullptr)},
                {"header_byte_limit", header_limit}, {"image_name_max_utf8_bytes", scalar::name_limit},
                {"metadata_read_limit", base::read_limit}, {"refused", !complete},
                {"reason", complete ? nlohmann::ordered_json(nullptr) : nlohmann::ordered_json(
                    error_[0] ? error_.data() : "Unique complete MODEL registration window required")},
                {"descriptor_admissible", false}, {"qualified_object_mip_count", nullptr},
                {"source_asset_name_association_proven", false}, {"model_binding_correlated", false},
                {"renderer_binding_proven", false}, {"same_object_proven", false},
                {"allocation_retained", false}, {"atomic_snapshot_proven", false},
                {"runtime_abi_proven", false}, {"lifetime_proven", false},
                {"pixels_copied", false}, {"payload_bytes_read", 0}, {"ready", false}};
            scalar::require(result.dump().size() <= base::output_limit,
                "Registration material bindings report exceeds 32 KiB");
            return result; // Owned JSON only; no historic pointer dereference.
        }
    };
}
