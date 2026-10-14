#pragma once

// Pure scalar publication from a caller-owned copy. No pointer/IO/engine read.
// 51 owns the checked copy, source-layout attestation and association rechecks.
#include "zonetool/t7/structs.hpp"
#include <json.hpp>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>

namespace zonetool::t7::selected_image_header_metadata
{
    inline constexpr std::string_view source_profile =
        "fab935826c898806855376662a8a03317b3ad8f1:T7.GfxImage/264";
    inline constexpr std::size_t header_bytes = 264;
    inline constexpr std::size_t name_limit = 255;
    inline constexpr std::size_t output_limit = 8192;
    static_assert(sizeof(GfxImage) == header_bytes && offsetof(GfxImage, name) == 248);
    static_assert(sizeof(GfxImageStreamLevelCountAndSize) == sizeof(std::uint32_t));
    static_assert(std::is_same_v<decltype(GfxImage{}.format), DXGI_FORMAT>);
    static_assert(std::endian::native == std::endian::little);

    struct admission
    {
        std::string_view layout_source_profile{};
        std::size_t copied_header_bytes{};
        bool source_layout_attested{};
        bool header_rechecked{};
        bool association_rechecked{};
        bool owned_name_rechecked{};
    };

    inline void require(bool ok, const char* reason)
    {
        if (!ok) throw std::runtime_error(reason);
    }

    inline std::string key_hex(std::uint64_t value)
    {
        constexpr char digits[] = "0123456789abcdef";
        std::string text(16, '0');
        for (unsigned i = 0; i < 16; ++i)
        {
            text[15 - i] = digits[value & 15u];
            value >>= 4;
        }
        return text;
    }

    inline nlohmann::ordered_json build(const GfxImage& copied, const admission& gate,
        const std::optional<std::string>& owned_name = std::nullopt)
    {
        require(gate.layout_source_profile == source_profile && gate.source_layout_attested,
            "Attested exact image source layout required");
        require(gate.copied_header_bytes == header_bytes && gate.header_rechecked &&
            gate.association_rechecked, "Complete rechecked selected header copy required");
        require(copied.streamedPartCount <= 4, "Physical image part count exceeds four");
        require(gate.owned_name_rechecked == owned_name.has_value(),
            "Owned image name requires its separate checked/rechecked read");
        if (owned_name)
        {
            require(!owned_name->empty() && owned_name->size() <= name_limit,
                "Bounded owned image name required");
            require(owned_name->find('\0') == std::string::npos, "Owned image name contains NUL");
            // Existing JSON serialization validates UTF-8; no new text validator.
            const auto checked_name = nlohmann::ordered_json(*owned_name).dump();
            (void)checked_name;
        }
        auto parts = nlohmann::ordered_json::array();
        for (unsigned i = 0; i < 4; ++i)
        {
            const auto& part = copied.streamedParts[i];
            std::uint32_t packed{};
            // This reads four bytes inside the owned POD, never a game pointer.
            std::memcpy(&packed, &part.levelCountAndSize, sizeof(packed));
            parts.push_back({{"index", i}, {"active", i < copied.streamedPartCount},
                {"width", part.width}, {"height", part.height},
                {"packed_size_raw", packed}, {"key_hex", key_hex(part.xpakEntry.key)}});
        }
        nlohmann::ordered_json result = {
            {"schema", "iw7.t7-selected-image-header-metadata/1"},
            {"source_profile", std::string(source_profile)}, {"header_bytes", header_bytes},
            {"image_name", owned_name ? nlohmann::ordered_json(*owned_name) : nlohmann::ordered_json(nullptr)},
            {"image_name_observed", owned_name.has_value()},
            {"width", copied.width}, {"height", copied.height}, {"depth", copied.depth},
            {"width1", copied.width1}, {"height1", copied.height1},
            {"level_count", copied.levelCount}, {"level_count1", copied.levelCount1},
            {"map_type", static_cast<unsigned>(copied.mapType)},
            {"format_namespace", "DXGI_FORMAT"},
            {"format_namespace_attestation", "source-layout-member"},
            {"dxgi_format", static_cast<std::uint32_t>(copied.format)},
            {"total_size", copied.totalSize}, {"flags", copied.flags},
            {"streaming", copied.streaming}, {"streamed_part_count", copied.streamedPartCount},
            {"use_fallback", copied.useFallback}, {"fallback_level", copied.fallbackLevel},
            {"fallback_size", copied.fallbackSize},
            {"fallback_pointer_present", copied.fallbackPixels != nullptr},
            {"delay_load_pixels", copied.delayLoadPixels},
            {"source_semantic", static_cast<int>(copied.semantic)}, {"parts", std::move(parts)},
            {"pixel_payload_bytes_read", 0}, {"allocation_retained", false},
            {"atomic_snapshot_proven", false}, {"runtime_abi_proven", false},
            {"lifetime_proven", false}, {"ready", false}};
        require(result.dump().size() <= output_limit, "Bounded copied-header metadata required");
        return result;
    }
}
