#pragma once

// Opt-in metadata adapter for the exact G2 observer. Default G2 bytes stay frozen.
// No engine lookup, pixel/stream IO, pointer workaround or allocation retention.
#include "selected_material_observation.hpp"

namespace zonetool::t7::selected_material_parts_observation
{
    namespace base = selected_material_observation;

    inline std::string hex64(std::uint64_t value)
    {
        constexpr char digits[] = "0123456789abcdef";
        std::string text(16, '0');
        for (unsigned i = 0; i < 16; ++i) { text[15 - i] = digits[value & 15u]; value >>= 4; }
        return text;
    }

    template <typename Readable> class header_capture
    {
        Readable& readable_;
        std::size_t remaining_ = base::read_limit;

    public:
        std::array<GfxImage, 2> headers{};
        std::array<const void*, 2> addresses{};
        unsigned count = 0;
        bool ambiguous = false;

        explicit header_capture(Readable& readable) : readable_(readable) {}

        void range(const void* source, std::size_t bytes)
        {
            const auto address = reinterpret_cast<std::uintptr_t>(source);
            resident_image::require(source && bytes && bytes <= remaining_ &&
                bytes <= std::numeric_limits<std::uintptr_t>::max() - address,
                "Parts metadata range/budget refused");
            const bool image_sized = bytes == sizeof(GfxImage);
            if (image_sized && count >= headers.size())
            {
                ambiguous = true;
                throw std::runtime_error("Extra or ambiguous image-sized metadata range");
            }
            const auto extra = image_sized ? sizeof(GfxImage) : 0;
            resident_image::require(extra <= remaining_ - bytes, "Parts header copy budget refused");
            remaining_ -= bytes + extra; // Charge both G2's read and our owned copy.
            readable_(source, bytes); // Existing guard must approve the entire range first.
            if (image_sized)
            {
                std::memcpy(&headers[count], source, sizeof(GfxImage));
                addresses[count] = source;
                ++count;
            }
        }
    };

    inline nlohmann::ordered_json fields(const GfxImage& source)
    {
        static_assert(sizeof(GfxImage) == 0x108 && offsetof(GfxImage, streamedParts) == 0 &&
            sizeof(GfxStreamedPartInfo) == 40 && offsetof(GfxStreamedPartInfo, xpakEntry) == 8 &&
            sizeof(GfxImageStreamLevelCountAndSize) == 4 && sizeof(XPakEntryInfo) == 32 &&
            offsetof(XPakEntryInfo, key) == 0 && offsetof(GfxImage, format) == 0xF0);
        std::uint32_t format_word;
        std::memcpy(&format_word, &source.format, sizeof(format_word));
        nlohmann::ordered_json result = {{"format_raw_u32", format_word},
            {"format_raw_byte0", static_cast<std::uint32_t>(
                *reinterpret_cast<const std::uint8_t*>(&source.format))},
            {"format_field_width_runtime_verified", false},
            {"stream_part_count_in_bounds", source.streamedPartCount <= 4},
            {"streamed_parts", nlohmann::ordered_json::array()}};
        // Always four physical records, never the untrusted declared count.
        for (unsigned i = 0; i < 4; ++i)
        {
            const auto& part = source.streamedParts[i];
            std::uint32_t packed;
            std::memcpy(&packed, &part.levelCountAndSize, sizeof(packed));
            std::array<std::uint64_t, 3> opaque;
            std::memcpy(opaque.data(), reinterpret_cast<const std::uint8_t*>(&part.xpakEntry) + 8,
                sizeof(opaque));
            result["streamed_parts"].push_back({{"index", i},
                {"declared_active", i < source.streamedPartCount},
                {"level_count_and_size_u32", packed},
                {"level_count_raw", static_cast<std::uint32_t>(part.levelCountAndSize.levelCount)},
                {"pixel_size_raw", static_cast<std::uint32_t>(part.levelCountAndSize.pixelSize)},
                {"width", part.width}, {"height", part.height},
                {"xpak_key_hex", hex64(part.xpakEntry.key)},
                {"opaque_descriptor_words_hex", {hex64(opaque[0]), hex64(opaque[1]), hex64(opaque[2])}},
                {"descriptor_field_semantics_verified", false}, {"payload_bytes_read", 0}});
        }
        return result;
    }

    inline std::string bounded_output(const nlohmann::ordered_json& result)
    {
        const auto text = result.dump();
        resident_image::require(text.size() <= base::output_limit, "Parts observation output exceeds bound");
        return text;
    }

    template <typename Readable> std::string observe_binding_parts(const XModel* source,
        const std::string& expected_model, unsigned lod, unsigned slot, Readable readable,
        base::image_binding_selection selection)
    {
        nlohmann::ordered_json result = {{"schema", "iw7.t7-selected-material-observation/3"},
            {"headers_rechecked", false}, {"stream_parts_headers_rechecked", false},
            {"allocation_retained", false}, {"atomic_snapshot_proven", false},
            {"pixels_copied", false}, {"ready", false}};
        try
        {
            header_capture<Readable> capture(readable);
            const auto text = base::observe_binding(source, expected_model, lod, slot,
                [&](const void* pointer, std::size_t bytes) { capture.range(pointer, bytes); }, selection);
            result = nlohmann::ordered_json::parse(text);
            result["schema"] = "iw7.t7-selected-material-observation/3";
            result["image_selection"] = {{"mode", "exact_binding_stream_parts"},
                {"index", selection.index}, {"expected_nameHash", selection.expected_name_hash}};
            result["stream_parts_headers_rechecked"] = false;
            result["stream_parts_header_copies"] = capture.count;
            if (result.value("refused", false)) return bounded_output(result); // Preserve G2 refusal.
            resident_image::require(result.at("headers_rechecked") == true &&
                result.at("model") == expected_model && result.at("lod") == lod && result.at("slot") == slot &&
                selection.index < result.at("textures").size(), "Exact rechecked parts selection required");
            auto& row = result["textures"][selection.index];
            resident_image::require(row.at("index") == selection.index && row.at("nameHash") == selection.expected_name_hash &&
                row.at("image_header_read") == true && row.at("image_read_state") == "observed" &&
                row.contains("image_name"), "Exact selected image header/name required");
            resident_image::require(!capture.ambiguous && capture.count == 2 &&
                capture.addresses[0] == capture.addresses[1] &&
                std::memcmp(&capture.headers[0], &capture.headers[1], sizeof(GfxImage)) == 0,
                "Owned selected parts headers changed or were ambiguous");
            resident_image::require(base::image_metadata(capture.headers[0]) == row.at("image"),
                "Owned parts header differs from G2 selected metadata");
            const auto extra = fields(capture.headers[0]);
            for (const auto& field : extra.items()) row["image"][field.key()] = field.value();
            result["stream_parts_headers_rechecked"] = true;
            return bounded_output(result);
        }
        catch (const std::exception& error)
        {
            result["refused"] = true;
            result["headers_rechecked"] = false;
            result["stream_parts_headers_rechecked"] = false;
            result["failure_stage"] = "image_stream_parts_capture";
            result["failure_index"] = selection.index;
            result["reason"] = std::string(error.what()).substr(0, 256);
            try { return bounded_output(result); }
            catch (const std::exception&)
            {
                return nlohmann::ordered_json({{"schema", "iw7.t7-selected-material-observation/3"},
                    {"refused", true}, {"failure_stage", "serialization"},
                    {"headers_rechecked", false}, {"stream_parts_headers_rechecked", false},
                    {"allocation_retained", false}, {"atomic_snapshot_proven", false},
                    {"pixels_copied", false}, {"ready", false}}).dump();
            }
        }
    }
}
