// Prepared only. Compile/link/run solely through the existing reviewed stage owner.
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <cstdint>
#include <cstddef>
#include <array>
#include <cstdio>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string_view>

// Identical ABI assertions to the pinned std_include.hpp, without its application deps.
#define assert_sizeof(T, N) static_assert(sizeof(T) == N)
#define assert_offsetof(T, M, N) static_assert(offsetof(T, M) == N)
#include "resident_image_copy.hpp" // Includes the real zonetool/t7/structs.hpp.

namespace t7 = zonetool::t7;
namespace image = zonetool::t7::resident_image;
static_assert(sizeof(void*) == 8);
static_assert(sizeof(t7::GfxImage) == 264 && offsetof(t7::GfxImage, name) == 248);

namespace
{
    unsigned copied_cases = 0, format_cases = 0, refused_cases = 0;
    std::size_t largest_pixel_copy = 0;

    void check(bool value)
    {
        if (!value) throw std::runtime_error("fixture assertion failed");
    }

    struct fixture
    {
        t7::GfxImage source{};
        std::array<std::uint8_t, 128> pixels{};
        std::size_t readable_bytes = pixels.size();
        unsigned header_reads = 0, pixel_reads = 0;
        bool deny_header = false, deny_pixels = false;
        enum class change { none, metadata, pointer } on_second_header = change::none;

        fixture(std::uint16_t width = 2, std::uint16_t height = 2, std::uint8_t mips = 1,
            DXGI_FORMAT format = DXGI_FORMAT_R8G8B8A8_UNORM, std::uint32_t size = 16)
        {
            source.width = source.width1 = width;
            source.height = source.height1 = height;
            source.depth = 1;
            source.levelCount = source.levelCount1 = mips;
            source.mapType = t7::MAPTYPE_2D;
            source.format = format;
            source.semantic = t7::IMG_SEMANTIC_DIFFUSE_MAP;
            source.totalSize = size;
            source.pixels = pixels.data();
            for (std::size_t i = 0; i < pixels.size(); ++i)
                pixels[i] = static_cast<std::uint8_t>((i * 7u + 3u) & 255u);
        }
        fixture(const fixture&) = delete;
        fixture& operator=(const fixture&) = delete;

        void readable(const void* pointer, std::size_t bytes)
        {
            if (pointer == &source && bytes == sizeof(source))
            {
                if (deny_header) throw std::runtime_error("synthetic header unreadable");
                ++header_reads;
                if (header_reads == 2 && on_second_header == change::metadata) source.flags = 1;
                if (header_reads == 2 && on_second_header == change::pointer) source.pixels = pixels.data() + 1;
                return;
            }
            // Compare with the actual array, NEVER the possibly corrupted source.pixels.
            if (deny_pixels || pointer != pixels.data() || !bytes || bytes > readable_bytes)
                throw std::runtime_error("synthetic pixels unreadable");
            ++pixel_reads;
            if (bytes > largest_pixel_copy) largest_pixel_copy = bytes;
        }

        image::copied_image copy()
        {
            return image::copy(&source, [this](const void* p, std::size_t n) { readable(p, n); });
        }
    };

    void copies(std::uint16_t width, std::uint16_t height, std::uint8_t levels,
        DXGI_FORMAT format, std::uint32_t expected_bytes, bool format_case = false)
    {
        fixture value(width, height, levels, format, expected_bytes);
        const auto before = image::view(value.source);
        auto result = value.copy();
        check(value.header_reads == 2 && value.pixel_reads == 1 && image::view(value.source) == before);
        check(result.image == before && result.pixels.size() == expected_bytes);
        check(std::memcmp(result.pixels.data(), value.pixels.data(), expected_bytes) == 0);
        const auto original = result.pixels[0];
        value.pixels[0] = static_cast<std::uint8_t>(value.pixels[0] ^ 255u);
        check(result.pixels[0] == original); // Output owns a copy, not an engine alias.
        if (format_case) ++format_cases; else ++copied_cases;
    }

    template <typename Action> void refusal(const char* reason, Action action)
    {
        bool refused = false;
        try { action(); }
        catch (const std::runtime_error& error)
        {
            check(std::string_view(error.what()) == reason);
            refused = true;
        }
        check(refused);
        ++refused_cases;
    }

    template <typename Change> void changed(const char* reason, Change change)
    {
        fixture value;
        change(value);
        refusal(reason, [&] { (void)value.copy(); });
    }

    void run()
    {
        // Tight pitches/chain totals are independent constants, not calls to the validator.
        copies(2, 2, 1, DXGI_FORMAT_R8G8B8A8_UNORM, 16);
        copies(3, 5, 3, DXGI_FORMAT_R8G8B8A8_UNORM, 72); // 60+8+4
        copies(7, 5, 3, DXGI_FORMAT_BC1_UNORM, 48); // 32+8+8
        copies(7, 5, 3, DXGI_FORMAT_BC3_UNORM, 96); // 64+16+16
        copies(1, 1, 1, DXGI_FORMAT_BC1_UNORM, 8); // Complete sub-block tail.
        copies(3, 2, 2, DXGI_FORMAT_R8_UNORM, 7); // 6+1, no row alignment padding.
        struct format_case { DXGI_FORMAT format; std::uint32_t bytes; };
        const format_case formats[] = {
            {DXGI_FORMAT_R8G8B8A8_UNORM,4},{DXGI_FORMAT_R8G8B8A8_UNORM_SRGB,4},
            {DXGI_FORMAT_R8G8_UNORM,2},{DXGI_FORMAT_R8_UNORM,1},
            {DXGI_FORMAT_BC1_UNORM,8},{DXGI_FORMAT_BC1_UNORM_SRGB,8},
            {DXGI_FORMAT_BC2_UNORM,16},{DXGI_FORMAT_BC2_UNORM_SRGB,16},
            {DXGI_FORMAT_BC3_UNORM,16},{DXGI_FORMAT_BC3_UNORM_SRGB,16},
            {DXGI_FORMAT_BC4_UNORM,8},{DXGI_FORMAT_BC4_SNORM,8},
            {DXGI_FORMAT_BC5_UNORM,16},{DXGI_FORMAT_BC5_SNORM,16},
            {DXGI_FORMAT_B8G8R8A8_UNORM,4},{DXGI_FORMAT_B8G8R8A8_UNORM_SRGB,4},
            {DXGI_FORMAT_BC7_UNORM,16},{DXGI_FORMAT_BC7_UNORM_SRGB,16}};
        for (const auto& test : formats) copies(1, 1, 1, test.format, test.bytes, true);

        changed("streamed image refused", [](fixture& f) { f.source.streaming = 1; });
        changed("streamed image refused", [](fixture& f) { f.source.streamedPartCount = 1; });
        changed("fallback/delayed image refused", [](fixture& f) { f.source.useFallback = 1; });
        changed("fallback/delayed image refused", [](fixture& f) { f.source.fallbackLevel = 1; });
        changed("fallback/delayed image refused", [](fixture& f) { f.source.fallbackSize = 1; });
        changed("fallback/delayed image refused", [](fixture& f) { f.source.fallbackPixels = f.pixels.data(); });
        changed("fallback/delayed image refused", [](fixture& f) { f.source.delayLoadPixels = true; });
        changed("unmapped T7 image flags refused", [](fixture& f) { f.source.flags = 1; });
        changed("ambiguous resident image dimensions/mips", [](fixture& f) { f.source.width1 = 1; });
        changed("ambiguous resident image dimensions/mips", [](fixture& f) { f.source.height1 = 1; });
        changed("ambiguous resident image dimensions/mips", [](fixture& f) { f.source.levelCount1 = 2; });
        changed("invalid resident mip count", [](fixture& f) { f.source.levelCount = f.source.levelCount1 = 3; });
        changed("resident image dimensions outside pilot bounds", [](fixture& f) { f.source.width = f.source.width1 = 0; });
        changed("T7 2D image required", [](fixture& f) { f.source.mapType = t7::MAPTYPE_CUBE; });
        changed("T7 2D image required", [](fixture& f) { f.source.depth = 2; });
        changed("unsupported typed DXGI format", [](fixture& f) { f.source.format = DXGI_FORMAT_R8G8B8A8_TYPELESS; });
        changed("unsupported typed DXGI format", [](fixture& f) { f.source.format = DXGI_FORMAT_BC6H_UF16; });
        changed("resident totalSize differs from tight mip chain", [](fixture& f) { f.source.totalSize = 15; });
        changed("resident totalSize differs from tight mip chain", [](fixture& f) { f.source.totalSize = 17; });
        changed("resident image budget exceeded", [](fixture& f) { f.source.totalSize = 16777217; });
        changed("synthetic header unreadable", [](fixture& f) { f.deny_header = true; });
        changed("synthetic pixels unreadable", [](fixture& f) { f.deny_pixels = true; });
        changed("synthetic pixels unreadable", [](fixture& f) { f.readable_bytes = 15; });
        changed("synthetic pixels unreadable", [](fixture& f) { f.source.pixels = reinterpret_cast<decltype(f.source.pixels)>(std::uintptr_t{1}); });
        changed("missing/overflowing resident pixels", [](fixture& f) { f.source.pixels = nullptr; });
        changed("missing/overflowing resident pixels", [](fixture& f) {
            f.source.pixels = reinterpret_cast<decltype(f.source.pixels)>((std::numeric_limits<std::uintptr_t>::max)() - 7);
        });
        changed("resident image metadata/pointer changed while copying", [](fixture& f) { f.on_second_header = fixture::change::metadata; });
        changed("resident image metadata/pointer changed while copying", [](fixture& f) { f.on_second_header = fixture::change::pointer; });
        const auto never_read = [](const void*, std::size_t) { throw std::runtime_error("callback must not run"); };
        refusal("missing resident image", [&] { (void)image::copy(nullptr, never_read); });
        refusal("image header address overflow", [&] {
            const auto pointer = reinterpret_cast<const t7::GfxImage*>((std::numeric_limits<std::uintptr_t>::max)() - 7);
            (void)image::copy(pointer, never_read);
        });
        check(copied_cases == 6 && format_cases == 18 && refused_cases == 30 && largest_pixel_copy == 96);
    }
}

int main(int argc, char**)
{
    if (argc != 1) { std::fputs("resident image fixture requires no arguments\n", stderr); return 2; }
    try
    {
        run();
        std::printf("{\"schema\":\"iw7.t7-resident-image-fixture/1\",\"status\":\"synthetic-pass\","
            "\"copied_cases\":%u,\"format_cases\":%u,\"refused_cases\":%u,\"largest_pixel_copy\":%zu,"
            "\"layout_bytes\":%zu,\"name_offset\":%zu,\"engine_observed\":false,"
            "\"atomic_snapshot\":false,\"seh_verified\":false,\"readable_callback\":\"synthetic-allowlist\"}\n",
            copied_cases, format_cases, refused_cases, largest_pixel_copy, sizeof(t7::GfxImage), offsetof(t7::GfxImage, name));
        return 0;
    }
    catch (const std::exception& error)
    {
        // All messages originate from fixed fixture/adapter literals, not game data.
        std::fprintf(stderr, "resident image fixture failed: %.160s\n", error.what());
        return 2;
    }
}
