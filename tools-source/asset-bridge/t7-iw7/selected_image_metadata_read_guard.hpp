#pragma once

// Mode-local protection for the exact owned copy consumed by G2 image_metadata.
// No game read, pointer dereference, engine call or changes to the frozen G2 API.
#include "resident_image_copy.hpp"
#include <type_traits>

namespace zonetool::t7::selected_image_metadata_read_guard
{
    inline thread_local bool active = false;

    class scope
    {
        bool prior_;
    public:
        scope() noexcept : prior_(active) { active = true; }
        ~scope() { active = prior_; }
        scope(const scope&) = delete;
        scope& operator=(const scope&) = delete;
    };

    inline void validate_if_active(const GfxImage& owned)
    {
        if (!active) return;
        static_assert(sizeof(GfxImage) == 264 && offsetof(GfxImage, delayLoadPixels) == 188 &&
            sizeof(decltype(GfxImage{}.delayLoadPixels)) == 1);
        std::uint8_t raw{};
        std::memcpy(&raw, reinterpret_cast<const unsigned char*>(&owned) + 188, sizeof(raw));
        resident_image::require(raw <= 1, "Invalid selected owned delayLoadPixels representation");
    }
}
