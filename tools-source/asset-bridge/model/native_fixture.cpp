// Prepared native test; compile only after parent GO/resource admission.
// Uses actual pinned H1/IW7 structs, allocator declarations/templates and exact
// patched production ValidateH1BlendVerts/PackIW7BlendVerts/convert bodies.
// Allocation is a bounded test adapter; optional codec calls fail deliberately.
#define NOMINMAX
#include <Windows.h>
#include <cstdint>
#include <cstddef>
#include <cstdlib>
#include <cassert>
#include <cstring>
#include <string>
#include <vector>
#include <mutex>
#include <stdexcept>
#include <type_traits>
#include <iostream>
#define assert_sizeof(T, N) static_assert(sizeof(T) == N)
#define assert_offsetof(T, M, N) static_assert(offsetof(T, M) == N)
#include "zonetool/h1/structs.hpp"
#include "zonetool/iw7/structs.hpp"
#include "utils/memory.hpp"

static unsigned int checks = 0;
static unsigned int allocations = 0;
static void check(bool ok, const char* message)
{
    if (!ok) throw std::runtime_error(message);
    ++checks;
}

// Only the allocator operations called by the extracted production functions
// are implemented. This fixture neither links nor tests the ZoneTool allocator.
void* utils::memory::allocator::allocate(size_t bytes)
{
    check(bytes <= 65536, "fixture allocation budget");
    if (!bytes) return nullptr;
    void* value = std::calloc(1, bytes);
    if (!value) throw std::bad_alloc();
    try { pool_.push_back(value); }
    catch (...) { std::free(value); throw; }
    ++allocations;
    return value;
}
utils::memory::allocator::~allocator()
{
    for (void* value : pool_) std::free(value);
}

namespace zonetool::half_float
{
    float half_to_float(unsigned short)
    {
        throw std::runtime_error("lightmap codec outside this native fixture");
    }
}
namespace zonetool::self_visibility
{
    unsigned int XSurfacePackSelfVisibility(const float*)
    {
        throw std::runtime_error("selfVisibility codec outside this native fixture");
    }
}

// Generated from the pinned source and checked patch, not a hand-written model.
#include "native_production.inc"

using zonetool::h1::converter::iw7::PackIW7BlendVerts;
using zonetool::h1::converter::iw7::convert;

template <typename F> void reject_before_allocation(F action, const char* expected)
{
    const auto before = allocations;
    bool refused = false;
    try { action(); }
    catch (const std::runtime_error& error)
    {
        refused = std::string(error.what()).find(expected) != std::string::npos;
    }
    check(refused, "expected native refusal missing or wrong");
    check(allocations == before, "invalid blend allocated output");
}

int main()
{
    try
    {
        static_assert(sizeof(zonetool::h1::XSurface) == 264);
        static_assert(sizeof(zonetool::iw7::XSurface) == 256);
        static_assert(sizeof(zonetool::h1::XBlendInfo) == 2);
        static_assert(sizeof(zonetool::iw7::XBlendInfo) == 2);
        static_assert(std::is_same_v<decltype(zonetool::h1::XSurface::blendVertCounts), short[8]>);
        const unsigned short input[] = {192, 0,64,65535, 0,64,4660,128,43981, 0,64,1,128,2,192,3};
        const unsigned short expected[] = {3,0, 0,1,65535,0, 0,1,4660,2,43981,0, 0,1,1,2,2,3,3,0};
        unsigned short words[16];
        std::memcpy(words, input, sizeof(words));
        zonetool::h1::XSurface source{};
        source.vertCount = 4;
        source.blendVerts = words;
        for (int i = 0; i < 4; ++i) source.blendVertCounts[i] = 1;
        utils::memory::allocator memory;
        zonetool::iw7::XSurface target{};
        PackIW7BlendVerts(&source, &target, memory);
        check(target.blendVertSize == sizeof(expected), "real pack byte count");
        check(std::memcmp(target.blendVerts, expected, sizeof(expected)) == 0, "real pack golden words");
        check(std::memcmp(words, input, sizeof(words)) == 0, "source words changed");

        reject_before_allocation([&] { PackIW7BlendVerts(nullptr, &target, memory); }, "null surface");
        for (int group = 4; group < 8; ++group)
        {
            auto invalid = source;
            invalid.blendVertCounts[group] = 1;
            reject_before_allocation([&] { PackIW7BlendVerts(&invalid, &target, memory); }, "5..8");
        }
        auto invalid = source;
        invalid.blendVertCounts[0] = -1;
        reject_before_allocation([&] { PackIW7BlendVerts(&invalid, &target, memory); }, "negative");
        invalid = source;
        invalid.vertCount = 3;
        reject_before_allocation([&] { PackIW7BlendVerts(&invalid, &target, memory); }, "exceed");
        invalid = source;
        invalid.blendVerts = nullptr;
        reject_before_allocation([&] { PackIW7BlendVerts(&invalid, &target, memory); }, "null data");
        const int bone_words[] = {0, 1,2, 4,5,7, 9,10,12,14};
        for (int index : bone_words)
        {
            ++words[index];
            reject_before_allocation([&] { PackIW7BlendVerts(&source, &target, memory); }, "multiple of 64");
            --words[index];
        }

        // Rigid/empty blend is valid in native conversion, unlike raw profile.
        zonetool::h1::XSurface empty{};
        empty.vertCount = 1;
        target = {};
        const auto before = allocations;
        PackIW7BlendVerts(&empty, &target, memory);
        check(target.blendVerts == nullptr && target.blendVertSize == 0, "native empty blend");
        check(allocations == before, "empty blend allocated");

        // Execute the real convert() subdivision branch with the real SDK
        // structs. A motion vertex avoids invoking unrelated ordinary codecs.
        // This only tests the copied count/flag, never subdivision rendering.
        for (unsigned char levels : {0, 1})
        {
            zonetool::h1::GfxPackedMotionVertex vertex{};
            zonetool::h1::XSurfaceSubdivInfo subdivision{};
            zonetool::h1::XSurface surface{};
            surface.flags = zonetool::h1::SURF_FLAG_REACTIVE_MOTION;
            surface.vertCount = 1;
            surface.verts0.packedMotionVerts0 = &vertex;
            surface.subdivLevelCount = levels;
            surface.subdiv = levels ? &subdivision : nullptr;
            zonetool::h1::XModelSurfs model{};
            model.name = "original_h1_bridge_flag_fixture";
            model.numsurfs = 1;
            model.surfs = &surface;
            const auto* converted = convert(&model, memory);
            check(converted->surfs[0].subdivLevelCount == levels, "real copied subdivision count");
            check(bool(converted->surfs[0].flags & zonetool::iw7::SURF_FLAG_SUBDIV) == bool(levels),
                  "real converter subdivision flag");
            check(converted->surfs[0].blendVertSize == 0, "rigid conversion synthesized blend");
        }
        std::cout << "{\"checks\":" << checks << ",\"production_lf_sha256\":\""
                  << BRIDGE_PRODUCTION_SHA256 << "\",\"full_zonetool_build\":false,"
                  << "\"codec_or_render_verified\":false}\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
