#pragma once

// Opt-in provenance of one copied binding field. Never read a GfxImage body.
#include "selected_material_observation.hpp"
#include <atomic>
#include <mutex>

namespace zonetool::t7::selected_image_provenance
{
    namespace base = selected_material_observation;
    inline constexpr char model_name[] = "p7_fre_platform_cap_02";
    inline constexpr unsigned binding_index = 4;
    inline constexpr std::uint32_t binding_hash = 0xA0AB1041u;
    inline constexpr std::size_t image_span = 264;
    inline constexpr unsigned search_limit = 1024;
    static_assert(sizeof(GfxImage) == image_span && offsetof(XModel, name) == 0);

    inline std::string hex(std::uintptr_t value)
    {
        constexpr char digits[] = "0123456789abcdef";
        std::string result(16, '0');
        for (unsigned i = 0; i < 16; ++i) { result[15-i] = digits[value & 15u]; value >>= 4; }
        return result;
    }

    struct region
    {
        std::uintptr_t base{}, allocation{};
        std::size_t extent{};
        DWORD state{}, protect{}, type{};
    };
    struct memory_state
    {
        std::array<region, 2> rows{};
        unsigned count{};
        bool complete{}, readable{}, query_failed{}, overflow{}, limit{};
    };

    inline memory_state query_memory_state(const void* pointer) noexcept
    {
        memory_state result;
        auto cursor = reinterpret_cast<std::uintptr_t>(pointer);
        if (!cursor || image_span > UINTPTR_MAX-cursor) { result.overflow = true; return result; }
        const auto end = cursor + image_span;
        result.readable = true;
        while (cursor < end)
        {
            if (result.count == result.rows.size()) { result.limit = true; return result; }
            MEMORY_BASIC_INFORMATION info{};
            if (VirtualQuery(reinterpret_cast<const void*>(cursor), &info, sizeof(info)) != sizeof(info))
            { result.query_failed = true; return result; }
            const auto begin = reinterpret_cast<std::uintptr_t>(info.BaseAddress);
            if (begin > cursor || !info.RegionSize || info.RegionSize > UINTPTR_MAX-begin ||
                begin + info.RegionSize <= cursor)
            { result.overflow = true; return result; }
            result.rows[result.count++] = {begin, reinterpret_cast<std::uintptr_t>(info.AllocationBase),
                info.RegionSize, info.State, info.Protect, info.Type};
            const auto protection = info.Protect & 0xff;
            result.readable = result.readable && info.State == MEM_COMMIT &&
                !(info.Protect & PAGE_GUARD) &&
                (protection == PAGE_READONLY || protection == PAGE_READWRITE ||
                 protection == PAGE_WRITECOPY || protection == PAGE_EXECUTE_READ ||
                 protection == PAGE_EXECUTE_READWRITE || protection == PAGE_EXECUTE_WRITECOPY);
            cursor = (std::min)(end, begin + info.RegionSize);
        }
        result.complete = true;
        return result; // VirtualQuery metadata only: no ReadProcessMemory or memcpy.
    }

    struct snapshot
    {
        std::uintptr_t incoming{}, returned{}, material{}, table{}, image{};
        std::uint64_t ordinal{}, tick{};
        DWORD thread{};
        unsigned texture_count{};
        bool field_observed{}, bound{};
        memory_state memory;
        std::array<char, 256> error{};
    };
    inline void failure(snapshot& value, const char* reason) noexcept
    {
        value.bound = false;
        if (!reason) reason = "Unknown provenance refusal";
        unsigned i = 0;
        for (; i < value.error.size()-1 && reason[i]; ++i) value.error[i] = reason[i];
        value.error[i] = 0;
        value.error.back() = 0;
    }
    inline nlohmann::ordered_json describe(const snapshot& value, const char* phase)
    {
        auto rows = nlohmann::ordered_json::array();
        for (unsigned i = 0; i < (std::min)(value.memory.count, 2u); ++i)
        {
            const auto& row = value.memory.rows[i];
            rows.push_back({{"base_hex", hex(row.base)}, {"allocation_base_hex", hex(row.allocation)},
                {"region_extent", row.extent}, {"state_raw", row.state},
                {"protect_raw", row.protect}, {"type_raw", row.type}});
        }
        return {{"phase", phase}, {"ordinal", value.ordinal}, {"thread_id", value.thread},
            {"tick_milliseconds", value.tick},
            {"incoming_model_header_hex", value.ordinal && std::strcmp(phase,"after_original_model_add")==0 ?
                nlohmann::ordered_json(hex(value.incoming)) : nlohmann::ordered_json(nullptr)},
            {"selected_model_header_hex", value.ordinal ? nlohmann::ordered_json(hex(value.returned)) :
                nlohmann::ordered_json(nullptr)},
            {"material_hex", value.field_observed ? nlohmann::ordered_json(hex(value.material)) :
                nlohmann::ordered_json(nullptr)},
            {"texture_table_hex", value.field_observed ? nlohmann::ordered_json(hex(value.table)) :
                nlohmann::ordered_json(nullptr)},
            {"image_field_hex", value.field_observed ? nlohmann::ordered_json(hex(value.image)) :
                nlohmann::ordered_json(nullptr)},
            {"lod", 0}, {"slot", 0}, {"binding_index", binding_index},
            {"expected_binding_name_hash", binding_hash}, {"binding_observed", value.field_observed},
            {"texture_count", value.field_observed ? nlohmann::ordered_json(value.texture_count) :
                nlohmann::ordered_json(nullptr)},
            {"binding_rechecked", value.bound}, {"failure", value.error.data()},
            {"queried_span_bytes", image_span}, {"query_complete", value.memory.complete},
            {"range_readable_at_query", value.memory.readable && value.memory.complete},
            {"query_failed", value.memory.query_failed}, {"range_overflow", value.memory.overflow},
            {"region_limit_refused", value.memory.limit}, {"regions", rows},
            {"image_body_bytes_read", 0}, {"atomic_snapshot_proven", false}};
    }

    template <typename Readable, typename Query> class observer
    {
#ifdef IW7_PROVENANCE_FIXTURE
    protected: // Test-only legacy control; absent from the operational build.
#endif
        Readable readable_;
        Query query_;
        base::reader<Readable> search_;
        std::mutex mutex_;
        bool begun_{}, finished_{}, duplicate_{};
        std::atomic<bool> active_{false};
        std::atomic<bool> search_refused_{false};
        unsigned callbacks_{}, matches_{};
        std::uint64_t ordinal_{};
        snapshot registration_, lookup_;

        snapshot capture(const XModel* model_pointer, std::uintptr_t incoming)
        {
            snapshot value;
            value.incoming = incoming;
            value.returned = reinterpret_cast<std::uintptr_t>(model_pointer);
            value.ordinal = ++ordinal_;
            value.tick = GetTickCount64();
            value.thread = GetCurrentThreadId();
            try
            {
                base::reader<Readable> read(readable_); // One existing 64-KiB budget per epoch.
                const auto model = read.one(model_pointer);
                resident_image::require(read.name(model.name) == model_name &&
                    model.numLods && model.numLods <= 8, "Exact provenance model/LOD required");
                const auto lods = read.array(model.meshMaterials, model.numLods, 8);
                const auto table = lods[0];
                resident_image::require(table.numMaterials && table.numMaterials <= 32,
                    "Bounded provenance material table required");
                const auto materials = read.array(table.materials, table.numMaterials, 32);
                const auto material = read.one(materials[0]);
                const auto textures = read.array(material.textureTable, material.textureCount, 16);
                resident_image::require(textures.size() > binding_index &&
                    textures[binding_index].nameHash == binding_hash,
                    "Exact provenance binding required");
                const auto binding = textures[binding_index];
                value.material = reinterpret_cast<std::uintptr_t>(materials[0]);
                value.table = reinterpret_cast<std::uintptr_t>(material.textureTable);
                value.image = reinterpret_cast<std::uintptr_t>(binding.image);
                value.texture_count = material.textureCount;
                value.field_observed = true;
                // Query the field's address range; NEVER copy or dereference that target.
                value.memory = query_(binding.image);
                if (value.memory.count > value.memory.rows.size())
                {
                    value.memory.limit = true;
                    value.memory.complete = false;
                    throw std::runtime_error("Bounded provenance region metadata required");
                }
                if (value.memory.complete)
                {
                    auto cursor = value.image;
                    resident_image::require(cursor && image_span <= UINTPTR_MAX-cursor &&
                        value.memory.count && !value.memory.query_failed &&
                        !value.memory.overflow && !value.memory.limit,
                        "Consistent complete provenance query required");
                    const auto end = cursor + image_span;
                    for (unsigned i = 0; i < value.memory.count; ++i)
                    {
                        const auto& row = value.memory.rows[i];
                        resident_image::require(cursor < end && row.base <= cursor && row.extent &&
                            row.extent <= UINTPTR_MAX-row.base && row.base + row.extent > cursor,
                            "Provenance query range association refused");
                        cursor = (std::min)(end, row.base + row.extent);
                    }
                    resident_image::require(cursor == end, "Incomplete provenance query coverage");
                }
                read.unchanged(material.textureTable + binding_index, binding);
                read.unchanged(materials[0], material);
                read.unchanged(table.materials, materials[0]);
                read.unchanged(model.meshMaterials, table);
                read.unchanged(model_pointer, model);
                resident_image::require(read.name(model.name) == model_name,
                    "Provenance model name changed");
                value.bound = true;
            }
            catch (const std::exception& error) { failure(value, error.what()); }
            catch (...) { failure(value, "Unknown selected-binding refusal"); }
            return value;
        }

    public:
        observer(Readable readable, Query query) : readable_(readable), query_(query), search_(readable_) {}
        void begin()
        {
            const std::lock_guard lock(mutex_);
            resident_image::require(!begun_, "Provenance context is single-use");
            begun_ = true;
            active_.store(true);
        }
        void after_model_add(XAssetType type, XAssetHeader incoming, XAssetHeader returned) noexcept
        {
            // Called AFTER the unmodified original MODEL add. No exception may reach the engine.
            if (!active_.load() || type != ASSET_TYPE_XMODEL) return;
            try
            {
                const std::lock_guard lock(mutex_);
                try
                {
                    if (!active_.load() || search_refused_.load()) return;
                    if (++callbacks_ > search_limit) { search_refused_ = true; return; }
                    const auto pointer = reinterpret_cast<const XModel*>(returned.data);
                    const auto name_pointer = search_.one(reinterpret_cast<const char* const*>(pointer));
                    if (search_.name(name_pointer) != model_name) return;
                    if (++matches_ != 1) { duplicate_ = true; return; }
                    registration_ = capture(pointer, reinterpret_cast<std::uintptr_t>(incoming.data));
                }
                catch (...)
                {
#ifdef IW7_PROVENANCE_FIXTURE
                    IW7_PROVENANCE_BEFORE_REFUSAL(mutex_);
#endif
                    search_refused_ = true; // Publish before the same lock is released.
                }
            }
            catch (...) { search_refused_ = true; } // Only lock acquisition failed; no metadata was read.
        }
        template <typename OriginalAdd> XAssetHeader original_add_and_observe(
            XAssetType type, XAssetHeader incoming, OriginalAdd&& original)
        {
            const auto returned = original(type, incoming); // Exactly once; original errors propagate.
            after_model_add(type, incoming, returned); // Its own failures never alter the return.
            return returned; // Already a HEADER. Do not add an entry offset.
        }
        nlohmann::ordered_json finish(const XModel* lookup_pointer)
        {
            const std::lock_guard lock(mutex_);
            resident_image::require(begun_ && !finished_, "Original provenance context required");
            active_.store(false);
            finished_ = true;
            lookup_ = capture(lookup_pointer, 0);
            const bool complete = matches_ == 1 && !duplicate_ && !search_refused_.load() &&
                registration_.bound && lookup_.bound &&
                registration_.memory.complete && lookup_.memory.complete;
            const bool associated = registration_.bound && lookup_.bound;
            return {{"schema", "iw7.t7-selected-image-provenance/1"},
                {"model", model_name}, {"lod", 0}, {"slot", 0},
                {"binding_index", binding_index}, {"binding_name_hash", binding_hash},
                {"capture_complete", complete}, {"refused", !complete},
                {"model_callbacks", callbacks_}, {"matched_registrations", matches_},
                {"duplicate_registration", duplicate_}, {"registration_search_refused", search_refused_.load()},
                {"registration", describe(registration_, "after_original_model_add")},
                {"lookup", describe(lookup_, "after_zone_model_lookup")},
                {"association_complete", associated},
                {"header_changed", associated ? nlohmann::ordered_json(
                    registration_.returned != lookup_.returned) : nlohmann::ordered_json(nullptr)},
                {"same_numeric_image_field", associated ? nlohmann::ordered_json(
                    registration_.image == lookup_.image) : nlohmann::ordered_json(nullptr)},
                {"same_object_proven", false}, {"lifetime_proven", false},
                {"allocation_retained", false}, {"pixels_copied", false},
                {"image_header_read", false}, {"image_body_admitted", false},
                {"image_body_bytes_read", 0}, {"payload_bytes_read", 0},
                {"g3_image_header_admission_changed", false},
                {"registration_path_changed", false}, {"ready", false}};
        }
    };
}
