#pragma once

// Source-only capture adapter for the pinned T7 layout; not wired into the exporter.
// Caller owns a stable DB scope and supplies the existing checked-readable callback.
// No Win32 APIs, file writes, XPAK reads, shader/texture handles or engine mutations.
#include "zonetool/t7/structs.hpp"
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <vector>

namespace zonetool::t7::resident_image
{
    inline constexpr std::size_t max_pixel_bytes = 16u * 1024u * 1024u;
    inline constexpr std::uint32_t max_dimension = 4096;

    // Serialize these exact scalar keys under image in resident_image.py's schema.
    // No pointer values are exported. DXGI namespace is explicit, never GfxPixelFormat.
    struct metadata
    {
        std::uint32_t width, height, depth, width1, height1;
        std::uint32_t level_count, level_count1, dxgi_format, total_size, map_type, flags;
        std::uint32_t streaming, streamed_part_count, use_fallback, fallback_level, fallback_size;
        bool fallback_pointer_present, delay_load_pixels;
        std::uint32_t source_semantic;
        bool operator==(const metadata&) const = default;
    };

    struct copied_image
    {
        metadata image;
        std::vector<std::uint8_t> pixels;
    };

    inline void require(bool value, const char* reason)
    {
        if (!value) throw std::runtime_error(reason);
    }

    inline metadata view(const GfxImage& source)
    {
        return {source.width, source.height, source.depth, source.width1, source.height1,
            source.levelCount, source.levelCount1, static_cast<std::uint32_t>(source.format),
            source.totalSize, static_cast<std::uint32_t>(source.mapType), source.flags,
            source.streaming, source.streamedPartCount, source.useFallback, source.fallbackLevel,
            source.fallbackSize, source.fallbackPixels != nullptr, source.delayLoadPixels,
            static_cast<std::uint32_t>(source.semantic)};
    }

    // Validate the chain before copying its bytes. Keep in sync with the explicit
    // Python encoder profile; native compilation/execution remains a separate gate.
    inline void validate(const metadata& image)
    {
        require(image.width && image.width <= max_dimension && image.height && image.height <= max_dimension,
            "resident image dimensions outside pilot bounds");
        require(image.map_type == 1 && image.depth == 1, "T7 2D image required");
        require(image.width1 == image.width && image.height1 == image.height &&
            image.level_count1 == image.level_count, "ambiguous resident image dimensions/mips");
        auto largest = image.width > image.height ? image.width : image.height;
        unsigned max_levels = 0;
        for (; largest; largest >>= 1) ++max_levels;
        require(image.level_count && image.level_count <= max_levels, "invalid resident mip count");
        require(image.flags == 0, "unmapped T7 image flags refused");
        require(image.streaming == 0 && image.streamed_part_count == 0, "streamed image refused");
        require(image.use_fallback == 0 && image.fallback_level == 0 && image.fallback_size == 0 &&
            !image.fallback_pointer_present && !image.delay_load_pixels, "fallback/delayed image refused");
        require(image.source_semantic < 0x15, "invalid T7 image semantic");
        require(image.total_size && image.total_size <= max_pixel_bytes, "resident image budget exceeded");
        unsigned unit = 0;
        bool blocks = false;
        switch (image.dxgi_format)
        {
        case 28: case 29: case 87: case 91: unit = 4; break; // RGBA/BGRA8, linear or sRGB
        case 49: unit = 2; break; // RG8 UNORM
        case 61: unit = 1; break; // R8 UNORM
        case 71: case 72: case 80: case 81: unit = 8; blocks = true; break; // BC1/BC4
        case 74: case 75: case 77: case 78: case 83: case 84: case 98: case 99:
            unit = 16; blocks = true; break; // BC2/BC3/BC5/BC7
        default: throw std::runtime_error("unsupported typed DXGI format");
        }
        std::size_t total = 0;
        for (unsigned level = 0; level < image.level_count; ++level)
        {
            const auto w = (image.width >> level) ? image.width >> level : 1u;
            const auto h = (image.height >> level) ? image.height >> level : 1u;
            const std::size_t columns = blocks ? (w + 3u) / 4u : w;
            const std::size_t rows = blocks ? (h + 3u) / 4u : h;
            const auto bytes = columns * unit * rows;
            require(bytes <= max_pixel_bytes - total, "resident mip chain exceeds budget");
            total += bytes;
        }
        require(total == image.total_size, "resident totalSize differs from tight mip chain");
    }

    template <typename Readable>
    copied_image copy(const GfxImage* source, Readable&& readable)
    {
        static_assert(sizeof(GfxImage) == 0x108 && offsetof(GfxImage, name) == 248,
            "pinned T7 image layout required");
        require(source != nullptr, "missing resident image");
        const auto copy_header = [&]()
        {
            const auto address = reinterpret_cast<std::uintptr_t>(source);
            require(sizeof(GfxImage) <= std::numeric_limits<std::uintptr_t>::max() - address,
                "image header address overflow");
            readable(source, sizeof(GfxImage)); // Callback must throw unless the ENTIRE range is readable.
            GfxImage result{};
            std::memcpy(&result, source, sizeof(result));
            return result;
        };
        const auto before = copy_header();
        copied_image result{view(before), {}};
        validate(result.image);
        const auto address = reinterpret_cast<std::uintptr_t>(before.pixels);
        require(address && result.image.total_size <= std::numeric_limits<std::uintptr_t>::max() - address,
            "missing/overflowing resident pixels");
        readable(before.pixels, result.image.total_size);
        result.pixels.resize(result.image.total_size);
        std::memcpy(result.pixels.data(), before.pixels, result.pixels.size());
        const auto after = copy_header();
        require(view(after) == result.image && after.pixels == before.pixels,
            "resident image metadata/pointer changed while copying");
        return result;
    }
}
