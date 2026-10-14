// Authored owned headers only. Requires separate admitted CPP before claiming PASS.
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <Windows.h>
#include <cstddef>
#include <cstdint>
#ifndef assert_sizeof
#define assert_sizeof(T, N) static_assert(sizeof(T) == N)
#endif
#ifndef assert_offsetof
#define assert_offsetof(T, M, N) static_assert(offsetof(T, M) == N)
#endif
#include "selected_image_header_metadata.hpp"
#include <cstdio>
#include <utility>

namespace image = zonetool::t7::selected_image_header_metadata;
namespace
{
    unsigned checks{};
    void check(bool ok)
    {
        ++checks;
        if (!ok) throw std::runtime_error("Copied image metadata fixture failed");
    }
    template <typename F> void refused(F&& fn)
    {
        bool seen = false;
        try { fn(); } catch (const std::exception&) { seen = true; }
        check(seen);
    }
    image::admission admitted()
    {
        return {image::source_profile, image::header_bytes, true, true, true, false};
    }
    zonetool::t7::GfxImage authored()
    {
        zonetool::t7::GfxImage value{};
        value.width = 1024; value.height = 512; value.depth = 1;
        value.width1 = 128; value.height1 = 64;
        value.levelCount = 11; value.levelCount1 = 8;
        value.mapType = zonetool::t7::MAPTYPE_2D;
        value.format = DXGI_FORMAT_BC7_UNORM_SRGB;
        value.totalSize = 0xabcdeu; value.flags = 0x87654321u;
        value.streaming = 1; value.streamedPartCount = 2;
        value.useFallback = 1; value.fallbackLevel = 3; value.fallbackSize = 2048;
        value.delayLoadPixels = true;
        value.name = reinterpret_cast<const char*>(std::uintptr_t{1});
        value.pixels = reinterpret_cast<zonetool::t7::byte*>(std::uintptr_t{1});
        value.fallbackPixels = reinterpret_cast<zonetool::t7::byte*>(std::uintptr_t{1});
        for (unsigned i = 0; i < 4; ++i)
        {
            value.streamedParts[i].width = static_cast<std::uint16_t>(16u << i);
            value.streamedParts[i].height = static_cast<std::uint16_t>(8u << i);
            const std::uint32_t packed = (0x01000000u + i) * 16u + i + 1u;
            std::memcpy(&value.streamedParts[i].levelCountAndSize, &packed, sizeof(packed));
            value.streamedParts[i].xpakEntry.key = UINT64_C(0xfedcba9876543210) + i;
        }
        return value;
    }
}
int main()
{
    try
    {
        const auto source = authored();
        auto gate = admitted();
        const auto result = image::build(source, gate);
        check(result.at("schema") == "iw7.t7-selected-image-header-metadata/1");
        check(result.at("image_name").is_null() && result.at("image_name_observed") == false);
        check(result.at("header_bytes") == 264 && result.at("format_namespace") == "DXGI_FORMAT");
        check(result.at("format_namespace_attestation") == "source-layout-member");
        check(result.at("dxgi_format") == 99); // sRGB stays sRGB; no Greyhound remap.
        check(result.at("width") == 1024 && result.at("height") == 512 && result.at("depth") == 1);
        check(result.at("width1") == 128 && result.at("height1") == 64);
        check(result.at("level_count") == 11 && result.at("level_count1") == 8);
        check(result.at("flags") == 0x87654321u && result.at("streaming") == 1);
        check(result.at("total_size") == 0xabcdeu && result.at("use_fallback") == 1);
        check(result.at("fallback_level") == 3 && result.at("fallback_size") == 2048);
        check(result.at("fallback_pointer_present") == true && result.at("delay_load_pixels") == true);
        check(result.at("parts").size() == 4);
        for (unsigned i = 0; i < 4; ++i)
        {
            const auto& part = result.at("parts").at(i);
            check(part.at("index") == i && part.at("active") == (i < 2));
            check(part.at("width") == (16u << i) && part.at("height") == (8u << i));
            check(part.at("packed_size_raw") == ((0x01000000u + i) * 16u + i + 1u));
            check(part.at("key_hex") == image::key_hex(UINT64_C(0xfedcba9876543210) + i));
        }
        check(result.at("parts").at(0).at("key_hex") == "fedcba9876543210");
        for (const char* field : {"allocation_retained", "atomic_snapshot_proven", "runtime_abi_proven", "lifetime_proven", "ready"})
            check(result.at(field) == false);
        check(result.at("pixel_payload_bytes_read") == 0);
        gate.owned_name_rechecked = true;
        check(image::build(source, gate, std::string(",authored/image")).at("image_name") == ",authored/image");
        check(image::build(source, gate, std::string("\xc3\xa9/image")).at("image_name") == "\xc3\xa9/image");
        refused([&] { image::build(source, admitted(), std::string("unattested-name")); });
        refused([&] { image::build(source, gate); });
        refused([&] { image::build(source, gate, std::string()); });
        refused([&] { image::build(source, gate, std::string(256, 'a')); });
        refused([&] { image::build(source, gate, std::string("bad\0name", 8)); });
        refused([&] { image::build(source, gate, std::string("\xff", 1)); });
        for (unsigned variant = 0; variant < 5; ++variant)
        {
            auto changed = admitted();
            if (variant == 0) changed.source_layout_attested = false;
            if (variant == 1) changed.header_rechecked = false;
            if (variant == 2) changed.association_rechecked = false;
            if (variant == 3) changed.copied_header_bytes = 263;
            if (variant == 4) changed.layout_source_profile = "unattested-layout";
            refused([&] { image::build(source, changed); });
        }
        auto malformed = authored(); malformed.streamedPartCount = 5;
        refused([&] { image::build(malformed, admitted()); });
        std::printf("PASS copied image metadata fixture: %u checks; authored only.\n", checks);
        return 0;
    }
    catch (const std::exception& error)
    {
        std::fprintf(stderr, "%s\n", error.what());
        return 1;
    }
}
