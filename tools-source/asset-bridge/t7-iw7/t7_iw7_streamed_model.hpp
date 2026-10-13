#pragma once

// Explicit selected-XPAK profile. Include after the pinned resident selector
// and selected_xpak reader. The caller retains its DB and sealed package views.
// This materializes a separate CPU view; it never edits an engine flag/pointer
// or opens the legacy ZoneTool XPAK cache.
#include <array>
#include <type_traits>
#include <vector>

namespace zonetool::t7::streamed_iw7
{
    inline constexpr const char* profile = "t7-iw7-selected-streamed-static-v1";

    struct selection
    {
        selection() = default;
        selection(const selection&) = delete;
        selection& operator=(const selection&) = delete;
        selection(selection&&) = default;
        selection& operator=(selection&&) = default;
        XModel* model{};
        selected_xpak::payload payload;
        std::uint32_t source_shared_flags{};
        std::uint32_t cpu_view_shared_flags{};
        std::uint64_t source_key{};
        std::array<std::uint64_t, 3> opaque_descriptor_words{};
        std::vector<std::uint16_t> source_surface_flags;
    };
    static_assert(!std::is_copy_constructible_v<selection> && !std::is_copy_assignable_v<selection>);
    static_assert(std::is_move_constructible_v<selection> && std::is_move_assignable_v<selection>);

    namespace detail
    {
        template <class T> struct capture
        {
            static_assert(std::is_trivially_copyable_v<T>);
            T value{};
            std::array<std::uint8_t, sizeof(T)> bytes{};
            explicit capture(const T* pointer)
            {
                const auto& original = resident_iw7::detail::object(pointer);
                std::memcpy(bytes.data(), &original, sizeof(T));
                std::memcpy(&value, bytes.data(), sizeof(T));
            }
            void recheck(const T* pointer) const
            {
                const auto& current = resident_iw7::detail::object(pointer);
                resident_iw7::detail::require(std::memcmp(bytes.data(), &current, sizeof(T)) == 0,
                    "selected source header changed while materializing XPAK payload");
            }
        };
    }

    // The 18,624-byte profile comes from the real D refusal. A fresh E2
    // observation supplies the expected key; no engine descriptor tail is
    // interpreted as a package index, extent, compression size or validity bit.
    // Both this owning selection and the caller's allocator must outlive dump;
    // the DB remains required for borrowed bone/material names and metadata.
    inline selection select(const XModel* source, const char* exact_name,
        const unsigned lod, const std::uint64_t expected_key,
        const std::span<const selected_xpak::package> packages,
        const selected_xpak::lz4_decoder decompress, utils::memory::allocator& allocator)
    {
        try
        {
            using namespace resident_iw7::detail;
            const detail::capture<XModel> model(source);
            require(resident_iw7::asset_name(model.value.name) == resident_iw7::asset_name(exact_name),
                "source model differs from exact streamed selection");
            require(model.value.numLods > 0 && model.value.numLods <= 8 && lod < model.value.numLods,
                "invalid streamed LOD selection");
            require(model.value.numBones == 1 && model.value.numRootBones == 1 &&
                model.value.numCosmeticBones == 0, "selected streamed profile requires one root bone");
            require(model.value.numSubmodels == 0 && !model.value.submodels &&
                model.value.numCollSurfs == 0 && !model.value.collSurfs &&
                model.value.numCollmaps == 0 && !model.value.collmaps && !model.value.collLod &&
                !model.value.physPreset && !model.value.physConstraints,
                "submodels, collision and physics are outside selected streamed profile");
            const auto* mesh_pointer = model.value.meshes[lod];
            const detail::capture<XModelMesh> mesh(mesh_pointer);
            const detail::capture<XSurfaceShared> shared(mesh.value.shared);
            require(shared.value.flags == 9 && shared.value.dataSize == selected_xpak::expected_mesh_bytes &&
                mesh.value.xpakEntry.key == expected_key,
                "raw selected flags, byte count or observed XPAK key differs");
            require(mesh.value.numSurfs > 0 && shared.value.skinVertCount == 0,
                "nonempty rigid streamed mesh required");
            (void)resident_iw7::asset_name(mesh.value.name);
            readable(mesh.value.surfs, std::size_t(mesh.value.numSurfs) * sizeof(XSurface));
            std::vector<detail::capture<XSurface>> surfaces;
            std::vector<detail::capture<XRigidVertList>> rigid_lists;
            surfaces.reserve(mesh.value.numSurfs); rigid_lists.reserve(mesh.value.numSurfs);
            std::uint64_t vertices = 0, triangles = 0;
            for (unsigned i = 0; i < mesh.value.numSurfs; ++i)
            {
                surfaces.emplace_back(mesh.value.surfs + i);
                const auto& surface = surfaces.back().value;
                require(!(surface.flags & XSURFACE_FLAG_SKINNED) && surface.shared == mesh.value.shared &&
                    surface.vertCount >= 3 && surface.triCount > 0 && surface.vertListCount == 1,
                    "selected streamed surface must be rigid and share the selected payload");
                rigid_lists.emplace_back(surface.vertList);
                const auto& rigid = rigid_lists.back().value;
                require(rigid.boneOffset == 0 && rigid.vertCount == surface.vertCount &&
                    rigid.triOffset == 0 && rigid.triCount == surface.triCount && !rigid.collisionTree,
                    "selected streamed rigid coverage differs");
                require(std::uint64_t(surface.baseVertOffset) + surface.vertCount <= shared.value.vertCount &&
                    std::uint64_t(surface.baseIndexOffset) + std::uint64_t(surface.triCount) * 3 <= shared.value.indexCount,
                    "selected streamed surface exceeds shared counts");
                (void)stream_start(shared.value.posOffset, surface.baseVertOffset, 12,
                    surface.vertCount, shared.value.dataSize);
                (void)stream_start(shared.value.vertsOffset, surface.baseVertOffset, 16,
                    surface.vertCount, shared.value.dataSize);
                (void)stream_start(shared.value.indicesOffset, surface.baseIndexOffset, 2,
                    std::size_t(surface.triCount) * 3, shared.value.dataSize);
                (void)stream_start(shared.value.skinWeightsOffset, surface.baseVertOffset, 12, 0,
                    shared.value.dataSize);
                vertices += surface.vertCount; triangles += surface.triCount;
            }
            (void)resident_iw7::geometry_work_bytes_upper_bound(mesh.value.numSurfs, vertices, triangles);

            selection result;
            result.source_shared_flags = shared.value.flags;
            result.source_key = mesh.value.xpakEntry.key;
            static_assert(sizeof(mesh.value.xpakEntry) == sizeof(result.source_key) +
                sizeof(result.opaque_descriptor_words));
            std::memcpy(result.opaque_descriptor_words.data(),
                reinterpret_cast<const std::uint8_t*>(&mesh.value.xpakEntry) + sizeof(result.source_key),
                sizeof(result.opaque_descriptor_words));
            result.payload = selected_xpak::read_selected_key(packages, expected_key,
                shared.value.dataSize, decompress);
            require(result.payload.bytes.size() == shared.value.dataSize,
                "selected XPAK payload does not match raw shared byte count");

            const auto recheck = [&]
            {
                model.recheck(source); mesh.recheck(mesh_pointer); shared.recheck(mesh.value.shared);
                for (unsigned i = 0; i < mesh.value.numSurfs; ++i)
                {
                    surfaces[i].recheck(mesh.value.surfs + i);
                    rigid_lists[i].recheck(surfaces[i].value.vertList);
                }
            };
            recheck();
            auto* cpu_model = allocator.allocate<XModel>();
            auto* cpu_mesh = allocator.allocate<XModelMesh>();
            auto* cpu_shared = allocator.allocate<XSurfaceShared>();
            auto* cpu_surfaces = allocator.allocate_array<XSurface>(mesh.value.numSurfs);
            auto* cpu_rigid = allocator.allocate_array<XRigidVertList>(mesh.value.numSurfs);
            require(cpu_model && cpu_mesh && cpu_shared && cpu_surfaces && cpu_rigid,
                "selected streamed CPU view allocation failed");
            *cpu_model = model.value; *cpu_mesh = mesh.value; *cpu_shared = shared.value;
            // Only this owned CPU view changes storage routing. The raw flags
            // remain 9 in the provenance, and resident v1/v2 still refuse them.
            cpu_shared->flags &= ~1u;
            cpu_shared->data = result.payload.bytes.data();
            cpu_shared->vbPos = cpu_shared->vbVerts = cpu_shared->vbSkinWeights = cpu_shared->ibIndices = nullptr;
            result.cpu_view_shared_flags = cpu_shared->flags;
            for (unsigned i = 0; i < mesh.value.numSurfs; ++i)
            {
                cpu_surfaces[i] = surfaces[i].value;
                result.source_surface_flags.push_back(static_cast<std::uint16_t>(cpu_surfaces[i].flags));
                cpu_surfaces[i].flags = static_cast<XSurfaceFlags>(
                    static_cast<std::uint16_t>(cpu_surfaces[i].flags) & ~std::uint16_t(XSURFACE_FLAG_STREAMED));
                cpu_surfaces[i].shared = cpu_shared;
                cpu_rigid[i] = rigid_lists[i].value;
                cpu_surfaces[i].vertList = cpu_rigid + i;
            }
            cpu_mesh->shared = cpu_shared; cpu_mesh->surfs = cpu_surfaces;
            cpu_model->meshes[lod] = cpu_mesh;
            // Reuse the same root, material, offset, finite-UV/position,
            // triangle and logical-work validation on the materialized CPU
            // representation. This is not a resident-source receipt or API.
            result.model = resident_iw7::select_impl(cpu_model, exact_name, lod, allocator, true);
            recheck();
            return result; // Owning payload stays alive through conversion/dump.
        }
        catch (const std::runtime_error& error)
        {
            const std::string old_prefix = std::string(resident_iw7::profile) + ": ";
            const std::string reason = error.what();
            throw std::runtime_error(std::string(profile) + ": " +
                (reason.starts_with(old_prefix) ? reason.substr(old_prefix.size()) : reason));
        }
    }
}
