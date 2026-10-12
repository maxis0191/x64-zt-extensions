#pragma once

// Pilot v1 for the pinned ZoneTool tree. Include after std_include.hpp.
// The caller pins the engine build and keeps its database stable through dump.
// This header does not load a zone, read XPAKs, rename assets or write files.
#include "game/shared.hpp"
#include "zonetool/t7/structs.hpp"
#include "utils/memory.hpp"
#include "t7_asset_name.hpp"
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>

namespace zonetool::t7::resident_iw7
{
    inline constexpr const char* profile = "t7-iw7-resident-static-v1";
    inline constexpr std::size_t max_buffer_bytes = 16u * 1024u * 1024u;
    inline constexpr std::size_t max_name_bytes = 255;

    namespace detail
    {
        inline void require(const bool condition, const char* reason)
        {
            if (!condition) throw std::runtime_error(std::string(profile) + ": " + reason);
        }

        inline void readable(const void* pointer, const std::size_t bytes)
        {
            const auto start = reinterpret_cast<std::uintptr_t>(pointer);
            require(start != 0 && bytes != 0 && bytes <= max_buffer_bytes,
                "missing or oversized readable range");
            require(bytes <= std::numeric_limits<std::uintptr_t>::max() - start,
                "readable range overflow");
            const auto end = start + bytes;
            auto cursor = start;
            unsigned regions = 0;
            while (cursor < end)
            {
                MEMORY_BASIC_INFORMATION page{};
                require(++regions <= 4096 && VirtualQuery(reinterpret_cast<const void*>(cursor),
                    &page, sizeof(page)) == sizeof(page), "unmapped readable range");
                const auto protection = page.Protect & 0xff;
                require(page.State == MEM_COMMIT && !(page.Protect & PAGE_GUARD) &&
                    (protection == PAGE_READONLY || protection == PAGE_READWRITE ||
                     protection == PAGE_WRITECOPY || protection == PAGE_EXECUTE_READ ||
                     protection == PAGE_EXECUTE_READWRITE || protection == PAGE_EXECUTE_WRITECOPY),
                    "range is not committed readable memory");
                const auto base = reinterpret_cast<std::uintptr_t>(page.BaseAddress);
                require(page.RegionSize <= std::numeric_limits<std::uintptr_t>::max() - base,
                    "memory region overflow");
                const auto next = base + page.RegionSize;
                require(base <= cursor && next > cursor, "invalid memory region");
                cursor = next < end ? next : end;
            }
        }

        template <typename T> inline const T& object(const T* value)
        {
            readable(value, sizeof(T));
            require(reinterpret_cast<std::uintptr_t>(value) % alignof(T) == 0,
                "unaligned typed pointer");
            return *value;
        }

        inline std::string name(const char* value)
        {
            require(value != nullptr, "missing asset or script name");
            std::string result;
            for (std::size_t i = 0; i <= max_name_bytes; ++i)
            {
                const auto start = reinterpret_cast<std::uintptr_t>(value);
                require(i <= std::numeric_limits<std::uintptr_t>::max() - start, "name overflow");
                const auto current = reinterpret_cast<const char*>(start + i);
                readable(current, 1);
                if (*current == '\0')
                {
                    require(!result.empty(), "empty asset or script name");
                    return result;
                }
                const auto c = static_cast<unsigned char>(*current);
                require(c >= 0x20 && c < 0x7f, "non-ASCII or control character in name");
                result.push_back(*current);
            }
            throw std::runtime_error(std::string(profile) + ": name exceeds pilot limit");
        }

        inline std::size_t stream_start(const std::uint32_t offset, const std::uint32_t base,
            const std::size_t stride, const std::size_t count, const std::size_t total)
        {
            require(stride > 0 && base <= (std::numeric_limits<std::uint64_t>::max() - offset) / stride &&
                count <= std::numeric_limits<std::uint64_t>::max() / stride, "stream arithmetic overflow");
            // Source offsets/counts are at most uint32; promote before arithmetic.
            const auto start = static_cast<std::uint64_t>(offset) +
                static_cast<std::uint64_t>(base) * stride;
            const auto bytes = static_cast<std::uint64_t>(count) * stride;
            require(start <= total && bytes <= total - start, "stream exceeds resident buffer");
            return static_cast<std::size_t>(start);
        }

        inline void bounds(const float* mins, const float* maxs)
        {
            for (unsigned axis = 0; axis < 3; ++axis)
            {
                require(std::isfinite(mins[axis]) && std::isfinite(maxs[axis]) &&
                    mins[axis] <= maxs[axis], "invalid bounds");
                const auto half = (maxs[axis] - mins[axis]) / 2.0f;
                require(std::isfinite(half) && std::isfinite(half + mins[axis]),
                    "converted bounds overflow");
            }
        }
    }

    inline std::string asset_name(const char* value)
    {
        return checked_asset_name(detail::name(value));
    }

    inline XModel* select(const XModel* source, const char* exact_name,
        const unsigned int lod, utils::memory::allocator& allocator)
    {
        using namespace detail;
        const auto& model = object(source);
        require(asset_name(model.name) == asset_name(exact_name), "model name differs from exact selection");
        require(model.numLods > 0 && model.numLods <= 8 && lod < model.numLods, "invalid LOD selection");
        require(model.numBones == 1 && model.numRootBones == 1 && model.numCosmeticBones == 0,
            "pilot requires one root bone and no cosmetic bones");
        require(model.numSubmodels == 0 && !model.submodels, "submodels are outside pilot");
        require(model.numCollSurfs == 0 && !model.collSurfs && model.numCollmaps == 0 &&
            !model.collmaps && !model.collLod && !model.physPreset && !model.physConstraints,
            "collision and physics are outside pilot");
        require(std::isfinite(model.areaScale) && model.areaScale > 0 &&
            std::isfinite(model.radius) && model.radius >= 0, "invalid model scale/radius");
        bounds(model.mins, model.maxs);
        const auto area = model.averageTriArea[lod];
        require(std::isfinite(area) && area > 0 && std::isfinite(1000000.0f / area),
            "invalid LOD area for production distance heuristic");

        const auto bone_id = object(model.boneNames);
        require(bone_id != 0 && SL_ConvertToString.get() != nullptr, "missing T7 bone resolver or ID");
        (void)name(SL_ConvertToString(bone_id)); // Engine-resolved; never synthesize a fallback.
        (void)object(model.partClassification);
        const auto& matrix = object(model.baseMat);
        for (const auto v : matrix.quat) require(std::isfinite(v), "nonfinite root rotation");
        for (const auto v : matrix.trans) require(std::isfinite(v), "nonfinite root translation");
        require(std::isfinite(matrix.transWeight), "nonfinite root translation weight");
        const auto& bone = object(model.boneInfo);
        bounds(bone.bounds[0], bone.bounds[1]);
        require(std::isfinite(bone.radiusSquared) && bone.radiusSquared >= 0, "invalid bone radius");

        const auto& mesh = object(model.meshes[lod]);
        (void)asset_name(mesh.name);
        require(mesh.numSurfs == 1, "pilot requires one selected surface");
        const auto& surf = object(mesh.surfs);
        require((surf.flags & (XSURFACE_FLAG_SKINNED | XSURFACE_FLAG_STREAMED)) == 0,
            "skinned or streamed surface is outside resident pilot");
        require(surf.vertCount >= 3 && surf.triCount > 0 && surf.vertListCount == 1,
            "pilot requires nonempty geometry and one rigid list");
        const auto& rigid = object(surf.vertList);
        require(rigid.boneOffset == 0 && rigid.vertCount == surf.vertCount && rigid.triOffset == 0 &&
            rigid.triCount == surf.triCount && !rigid.collisionTree, "invalid root rigid coverage");
        const auto& shared = object(mesh.shared);
        require(surf.shared == mesh.shared && !(shared.flags & 1) && shared.data &&
            shared.dataSize > 0 && shared.dataSize <= max_buffer_bytes,
            "selected mesh must use one bounded resident shared buffer");
        readable(shared.data, shared.dataSize);
        require(shared.skinVertCount == 0, "resident buffer contains skin vertices");
        require(static_cast<std::uint64_t>(surf.baseVertOffset) + surf.vertCount <= shared.vertCount &&
            static_cast<std::uint64_t>(surf.baseIndexOffset) + surf.triCount * 3u <= shared.indexCount,
            "surface exceeds shared element counts");
        const auto positions = stream_start(shared.posOffset, surf.baseVertOffset, 12,
            surf.vertCount, shared.dataSize);
        const auto attributes = stream_start(shared.vertsOffset, surf.baseVertOffset, 16,
            surf.vertCount, shared.dataSize);
        const auto indices = stream_start(shared.indicesOffset, surf.baseIndexOffset, 2,
            surf.triCount * 3u, shared.dataSize);
        // The production converter constructs this unused pointer for rigid meshes.
        // Require its start to be within/one-past the buffer; no skin payload needed.
        (void)stream_start(shared.skinWeightsOffset, surf.baseVertOffset, 12, 0, shared.dataSize);
        require((reinterpret_cast<std::uintptr_t>(shared.data) + positions) % alignof(float) == 0 &&
            (reinterpret_cast<std::uintptr_t>(shared.data) + attributes) % alignof(GfxStreamVertex) == 0 &&
            (reinterpret_cast<std::uintptr_t>(shared.data) + indices) % alignof(GfxStreamFace) == 0,
            "unaligned production stream");

        static_assert(sizeof(GfxStreamVertex) == 16 && sizeof(GfxStreamFace) == 6);
        const auto* xyz = reinterpret_cast<const vec3_t*>(shared.data + positions);
        for (unsigned i = 0; i < surf.vertCount; ++i)
        {
            for (const auto value : xyz[i]) require(std::isfinite(value), "nonfinite vertex position");
            GfxStreamVertex vertex{};
            std::memcpy(&vertex, shared.data + attributes + i * sizeof(vertex), sizeof(vertex));
            require((vertex.UVUPosition & 0x7c00) != 0x7c00 &&
                (vertex.UVVPosition & 0x7c00) != 0x7c00, "nonfinite half-float UV");
        }
        for (unsigned i = 0; i < surf.triCount; ++i)
        {
            GfxStreamFace face{};
            std::memcpy(&face, shared.data + indices + i * sizeof(face), sizeof(face));
            require(face.Index1 < surf.vertCount && face.Index2 < surf.vertCount &&
                face.Index3 < surf.vertCount, "triangle index outside vertex range");
            double u[3]{}, v[3]{};
            for (unsigned axis = 0; axis < 3; ++axis)
            {
                u[axis] = static_cast<double>(xyz[face.Index2][axis]) - xyz[face.Index1][axis];
                v[axis] = static_cast<double>(xyz[face.Index3][axis]) - xyz[face.Index1][axis];
            }
            const double cross[3]{u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]};
            const auto area_squared = cross[0]*cross[0] + cross[1]*cross[1] + cross[2]*cross[2];
            require(std::isfinite(area_squared) && area_squared > 0, "degenerate triangle");
        }

        require(model.meshMaterials != nullptr, "missing mesh materials");
        readable(model.meshMaterials, model.numLods * sizeof(XModelMeshMaterials));
        const auto& materials = object(model.meshMaterials + lod);
        require(materials.numMaterials == 1, "pilot requires one material reference");
        const auto* material = object(materials.materials);
        (void)name(object(material).name);
        const auto mip = object(materials.himipInvSqRadii);
        require(std::isfinite(mip) && mip >= 0 && std::sqrt(mip) <= 65504.0f,
            "material radius cannot be represented as finite half float");

        // Owned view: stable after return, no writes through any engine pointer.
        auto* selected_materials = allocator.allocate<XModelMeshMaterials>();
        auto* selected = allocator.allocate<XModel>();
        require(selected_materials && selected, "view allocation failed");
        *selected_materials = materials;
        *selected = model;
        selected->numLods = 1;
        for (auto& item : selected->meshes) item = nullptr;
        for (auto& item : selected->averageTriArea) item = 0.0f;
        selected->meshes[0] = model.meshes[lod];
        selected->averageTriArea[0] = area;
        selected->meshMaterials = selected_materials;
        // This profile has no non-root bones. Canonicalize only the owned view's
        // unused zero-count arrays so the writer cannot serialize stale pointers.
        selected->parentList = nullptr;
        selected->tagAngles = nullptr;
        selected->tagPositions = nullptr;
        selected->highestRenderLod = XMODEL_LOD_0;
        selected->highestShadowLod = XMODEL_LOD_0;
        return selected;
    }
}
