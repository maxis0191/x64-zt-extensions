#pragma once

// One opt-in registration epoch. Finalization consumes only owned data.
#include "selected_material_observation.hpp"
#include "selected_image_header_metadata.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <optional>
#include <string>

namespace zonetool::t7::registration_image_header_capture
{
    namespace base = selected_material_observation;
    namespace scalar = selected_image_header_metadata;
    inline constexpr char schema[] = "iw7.t7-registration-image-header-metadata/1";
    inline constexpr char profile[] = "t7-registration-image-header-metadata-v1";
    inline constexpr char phase[] = "after_original_model_add";
    inline constexpr std::size_t span = 264;
    static_assert(sizeof(GfxImage) == span && alignof(GfxImage) == 8);
    static_assert(offsetof(GfxImage, name) == 248 && sizeof(GfxImage::name) == 8);
    static_assert(offsetof(GfxImage, delayLoadPixels) == 188 && sizeof(bool) == 1);

    // No C++ objects/unwinding in this leaf. A query is not an allocation lock.
    // The only callers copy a whole 264-byte header or one bounded name byte.
#if defined(_MSC_VER) && defined(_WIN32)
    __declspec(noinline) inline bool copy_header_leaf(void* target, const void* source) noexcept
    {
        if (!target || !source) return false;
        __try { std::memcpy(target, source, span); return true; }
        __except ((GetExceptionCode() == EXCEPTION_ACCESS_VIOLATION ||
                   GetExceptionCode() == EXCEPTION_IN_PAGE_ERROR) ?
                   EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH) { return false; }
    }
    __declspec(noinline) inline bool copy_name_byte_leaf(unsigned char* target, const unsigned char* source) noexcept
    {
        if (!target || !source) return false;
        __try { *target = *source; return true; }
        __except ((GetExceptionCode() == EXCEPTION_ACCESS_VIOLATION ||
                   GetExceptionCode() == EXCEPTION_IN_PAGE_ERROR) ?
                   EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH) { return false; }
    }
#else
    inline bool copy_header_leaf(void*, const void*) noexcept { return false; }
    inline bool copy_name_byte_leaf(unsigned char*, const unsigned char*) noexcept { return false; }
#endif
    inline bool copy_leaf(void* target, const void* source, std::size_t bytes) noexcept
    {
        if (bytes == span) return copy_header_leaf(target, source);
        if (bytes == 1) return copy_name_byte_leaf(static_cast<unsigned char*>(target), static_cast<const unsigned char*>(source));
        return false;
    }

    struct association
    {
        std::uint64_t ordinal{};
        std::uintptr_t returned{}, material{}, table{}, image{};
        bool bound{}, query_readable{};
    };

    inline nlohmann::ordered_json envelope(bool nondefault)
    {
        return {{"schema", schema}, {"source_profile", profile},
            {"native_source_commit", "fab935826c898806855376662a8a03317b3ad8f1"},
            {"zone", "mp_freerun_04"}, {"model", "p7_fre_platform_cap_02"},
            {"model_default", nondefault ? nlohmann::ordered_json(false) : nlohmann::ordered_json(nullptr)},
            {"lod", 0}, {"slot", 0}, {"binding_index", 4}, {"binding_hash_u32", 0xA0AB1041u},
            {"image_header_bytes", span}, {"header_copies", 0}, {"registration_header_observed", false},
            {"association_rechecked_at_registration", false}, {"header_rechecked_at_registration", false},
            {"name_rechecked_at_registration", false}, {"refused", true}, {"failure_stage", nullptr},
            {"reason", nullptr}, {"image", nullptr}, {"provenance", nullptr}, {"allocation_retained", false},
            {"atomic_snapshot_proven", false}, {"pixels_copied", false}, {"payload_bytes_read", 0},
            {"runtime_abi_proven", false}, {"lifetime_proven", false}, {"ready", false},
            {"capture_phase", phase}, {"capture_ordinal", 0}, {"recheck_phase", phase},
            {"registration_header_bytes_copied", 0}, {"same_object_proven", false}};
    }

    class cache
    {
        alignas(GfxImage) std::array<std::uint8_t, span> owned_{};
        std::string name_;
        nlohmann::ordered_json image_ = nullptr;
        association captured_{};
        unsigned copies_{};
        bool attempted_{}, observed_{}, copy_fault_{};
        std::array<char, 256> error_{};

        void fail(const char* message) noexcept
        {
            observed_ = false;
            if (!message) message = "Registration header capture refused";
            unsigned i = 0;
            for (; i < error_.size()-1 && message[i]; ++i) error_[i] = message[i];
            error_[i] = 0;
            owned_.fill(0);
            name_.clear();
            image_.clear();
        }
        template <typename Query> static void fresh_query(Query& query, const void* pointer)
        {
            const auto state = query(pointer);
            scalar::require(state.complete && state.readable && state.count && state.count <= 2 &&
                !state.query_failed && !state.overflow && !state.limit,
                "Fresh registration header range is not readable");
            auto cursor = reinterpret_cast<std::uintptr_t>(pointer);
            scalar::require(cursor && span <= UINTPTR_MAX-cursor, "Registration header range overflow");
            const auto end = cursor + span;
            for (unsigned i = 0; i < state.count; ++i)
            {
                const auto& row = state.rows[i];
                const auto protection = row.protect & 0xff;
                scalar::require(cursor < end && row.base <= cursor && row.extent &&
                    row.extent <= UINTPTR_MAX-row.base && row.base+row.extent > cursor &&
                    row.state == MEM_COMMIT && !(row.protect & PAGE_GUARD) &&
                    (protection == PAGE_READONLY || protection == PAGE_READWRITE ||
                     protection == PAGE_WRITECOPY || protection == PAGE_EXECUTE_READ ||
                     protection == PAGE_EXECUTE_READWRITE || protection == PAGE_EXECUTE_WRITECOPY),
                    "Registration header query coverage/protection refused");
                cursor = (std::min)(end, row.base+row.extent);
            }
            scalar::require(cursor == end, "Registration header query coverage incomplete");
        }
        template <typename Readable, typename Copy> std::string owned_name(
            base::reader<Readable>& read, const std::array<std::uint8_t, span>& raw, Copy& copy)
        {
            const char* pointer{};
            std::memcpy(&pointer, raw.data()+offsetof(GfxImage, name), sizeof(pointer));
            const auto address = reinterpret_cast<std::uintptr_t>(pointer);
            scalar::require(address && scalar::name_limit <= UINTPTR_MAX-address,
                "Bounded registration image name pointer required");
            std::string result;
            for (std::size_t i = 0; i <= scalar::name_limit; ++i)
            {
                const auto source = reinterpret_cast<const char*>(address+i);
                read.range(source, 1);
                char value{};
                if (!copy(&value, source, 1)) { copy_fault_ = true; throw std::runtime_error("Registration name copy fault"); }
                if (!value)
                {
                    scalar::require(!result.empty(), "Empty registration image name");
                    (void)nlohmann::ordered_json(result).dump(); // Validate UTF-8 while owned.
                    return result;
                }
                scalar::require(i < scalar::name_limit, "Registration image name exceeds 255 bytes");
                result += value;
            }
            throw std::runtime_error("Unterminated registration image name");
        }

    public:
        void reset()
        {
            owned_.fill(0); name_.clear(); image_ = nullptr; captured_ = {};
            copies_ = 0; attempted_ = observed_ = copy_fault_ = false; error_.fill(0);
        }
        template <typename Readable, typename Query, typename Copy>
        void record(const association& epoch, const XModel* pointer, Readable readable, Query query, Copy copy) noexcept
        {
            try
            {
                scalar::require(!attempted_, "Only one registration capture is permitted");
                attempted_ = true; captured_ = epoch;
                scalar::require(epoch.bound && epoch.query_readable && epoch.ordinal && epoch.image % alignof(GfxImage) == 0 &&
                    epoch.returned == reinterpret_cast<std::uintptr_t>(pointer),
                    "Exact readable same-context registration required");
                base::reader<Readable> read(readable);
                const auto model = read.one(pointer);
                scalar::require(read.name(model.name) == "p7_fre_platform_cap_02" && model.numLods && model.numLods <= 8,
                    "Exact registration model/LOD required");
                const auto lods = read.array(model.meshMaterials, model.numLods, 8);
                const auto table = lods[0];
                scalar::require(table.numMaterials && table.numMaterials <= 32, "Bounded registration materials required");
                const auto materials = read.array(table.materials, table.numMaterials, 32);
                const auto material = read.one(materials[0]);
                const auto textures = read.array(material.textureTable, material.textureCount, 16);
                scalar::require(textures.size() > 4 && textures[4].nameHash == 0xA0AB1041u,
                    "Exact registration binding4/hash required");
                const auto binding = textures[4];
                scalar::require(epoch.material == reinterpret_cast<std::uintptr_t>(materials[0]) &&
                    epoch.table == reinterpret_cast<std::uintptr_t>(material.textureTable) &&
                    epoch.image == reinterpret_cast<std::uintptr_t>(binding.image), "Registration capture association changed");
                alignas(GfxImage) std::array<std::uint8_t, span> first{}, second{};
                const auto copy_header = [&](auto& target)
                {
                    fresh_query(query, binding.image);
                    read.range(binding.image, span);
                    if (!copy(target.data(), binding.image, span))
                    { copy_fault_ = true; throw std::runtime_error("Registration header copy fault"); }
                    ++copies_;
                    scalar::require(target[offsetof(GfxImage, delayLoadPixels)] <= 1,
                        "Invalid registration delayLoadPixels raw byte");
                };
                copy_header(first);
                const auto first_name = owned_name(read, first, copy);
                copy_header(second);
                const auto second_name = owned_name(read, second, copy);
                scalar::require(first == second && first_name == second_name,
                    "Registration header/name changed during capture");
                read.unchanged(material.textureTable+4, binding);
                read.unchanged(materials[0], material);
                read.unchanged(table.materials, materials[0]);
                read.unchanged(model.meshMaterials, table);
                read.unchanged(pointer, model);
                scalar::require(read.name(model.name) == "p7_fre_platform_cap_02", "Registration model name changed");
                fresh_query(query, binding.image);
                // Only now materialize a typed aligned POD, after validating BOTH raw bool bytes.
                GfxImage copied{};
                std::memcpy(&copied, first.data(), span);
                const scalar::admission gate{scalar::source_profile, span, true, true, true, true};
                auto dto = scalar::build(copied, gate, std::optional<std::string>{first_name});
                owned_ = first; name_ = first_name; image_ = std::move(dto); observed_ = true;
            }
            catch (const std::exception& error) { fail(error.what()); }
            catch (...) { fail("Unknown registration header capture refusal"); }
        }

        nlohmann::ordered_json finish(const nlohmann::ordered_json& provenance,
            const association& registration, const association& lookup, bool nondefault) const
        {
            auto result = envelope(nondefault);
            result["capture_ordinal"] = captured_.ordinal;
            result["header_copies"] = copies_;
            result["registration_header_bytes_copied"] = copy_fault_ ? nlohmann::ordered_json(nullptr) : nlohmann::ordered_json(copies_*span);
            try
            {
                result["provenance"] = provenance;
                scalar::require(nondefault && attempted_ && observed_ && copies_ == 2 && !copy_fault_,
                    error_[0] ? error_.data() : "Complete owned registration header required");
                scalar::require(provenance.at("schema") == "iw7.t7-selected-image-provenance/1" &&
                    provenance.at("model") == "p7_fre_platform_cap_02" && provenance.at("lod") == 0 &&
                    provenance.at("slot") == 0 && provenance.at("binding_index") == 4 &&
                    provenance.at("binding_name_hash") == 0xA0AB1041u &&
                    provenance.at("capture_complete") == true && provenance.at("refused") == false &&
                    provenance.at("matched_registrations") == 1 && provenance.at("duplicate_registration") == false &&
                    provenance.at("registration_search_refused") == false, "Unique complete F2 registration required");
                scalar::require(registration.bound && registration.query_readable && lookup.bound &&
                    captured_.ordinal == registration.ordinal && captured_.returned == registration.returned &&
                    captured_.material == registration.material && captured_.table == registration.table &&
                    captured_.image == registration.image && registration.returned == lookup.returned &&
                    registration.material == lookup.material && registration.table == lookup.table &&
                    registration.image == lookup.image, "Registration cache/context or numeric lookup association changed");
                const auto& row = provenance.at("registration");
                scalar::require(row.at("phase") == phase && row.at("ordinal") == captured_.ordinal &&
                    row.at("binding_rechecked") == true && row.at("query_complete") == true &&
                    row.at("range_readable_at_query") == true &&
                    row.at("selected_model_header_hex") == scalar::key_hex(captured_.returned) &&
                    row.at("material_hex") == scalar::key_hex(captured_.material) &&
                    row.at("texture_table_hex") == scalar::key_hex(captured_.table) &&
                    row.at("image_field_hex") == scalar::key_hex(captured_.image), "F2 registration/cache correlation refused");
                result["image"] = image_; // Owned JSON/name; NEVER copied.name or historic engine memory.
                result["registration_header_observed"] = true;
                result["association_rechecked_at_registration"] = true;
                result["header_rechecked_at_registration"] = true;
                result["name_rechecked_at_registration"] = true;
                result["refused"] = false;
                scalar::require(result.dump().size() <= base::output_limit, "Registration metadata exceeds 32 KiB");
                return result;
            }
            catch (const std::exception& error)
            {
                auto refused = envelope(nondefault);
                refused["capture_ordinal"] = captured_.ordinal;
                refused["header_copies"] = copies_;
                refused["registration_header_bytes_copied"] = result["registration_header_bytes_copied"];
                refused["failure_stage"] = "registration_header_metadata";
                refused["reason"] = std::string(error.what()).substr(0, 255);
                try { refused["provenance"] = provenance; if (refused.dump().size() <= base::output_limit) return refused; }
                catch (const std::exception&) {}
                refused["provenance"] = nullptr;
                refused["failure_stage"] = "serialization";
                refused["reason"] = "Bounded registration metadata serialization refused";
                return refused;
            }
        }
    };
}
