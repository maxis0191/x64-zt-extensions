#pragma once

// Metadata only, at the pinned T7 ABI. The caller selects one exact model/LOD/slot
// and supplies the existing throwing readability guard. No pixel/stream reads,
// DB calls, allocation retention, filesystem access or engine writes are added.
#include "resident_image_copy.hpp"
#include <json.hpp>
#include <algorithm>
#include <array>
#include <string>
#include <utility>

namespace zonetool::t7::selected_material_observation
{
    inline constexpr std::size_t read_limit = 64u * 1024u;
    inline constexpr std::size_t output_limit = 32u * 1024u;
    inline constexpr std::size_t name_limit = 256;

    template <typename Readable> class reader
    {
        Readable& readable_;
        std::size_t remaining_ = read_limit;

    public:
        explicit reader(Readable& readable) : readable_(readable) {}

        void range(const void* source, std::size_t bytes)
        {
            const auto address = reinterpret_cast<std::uintptr_t>(source);
            resident_image::require(source && bytes && bytes <= remaining_ &&
                bytes <= std::numeric_limits<std::uintptr_t>::max() - address,
                "Selected-material metadata range/budget refused");
            remaining_ -= bytes;
            readable_(source, bytes); // Must throw for an unreadable range.
        }

        template <typename T> T one(const T* source)
        {
            range(source, sizeof(T));
            T value;
            std::memcpy(&value, source, sizeof(T));
            return value;
        }

        template <typename T> std::vector<T> array(const T* source, std::size_t count,
            std::size_t maximum)
        {
            resident_image::require(count <= maximum, "Selected-material table count refused");
            if (!count) return {};
            resident_image::require(count <= std::numeric_limits<std::size_t>::max() / sizeof(T),
                "Selected-material table overflow");
            range(source, count * sizeof(T));
            std::vector<T> values(count);
            std::memcpy(values.data(), source, count * sizeof(T));
            return values;
        }

        std::string name(const char* source)
        {
            const auto address = reinterpret_cast<std::uintptr_t>(source);
            resident_image::require(source && address <=
                std::numeric_limits<std::uintptr_t>::max() - name_limit,
                "Selected-material name range refused");
            std::string value;
            for (std::size_t i = 0; i <= name_limit; ++i)
            {
                const char c = one(reinterpret_cast<const char*>(address + i));
                if (!c)
                {
                    resident_image::require(!value.empty(), "Empty selected-material name");
                    return value;
                }
                resident_image::require(i < name_limit, "Selected-material name exceeds bound");
                value += c;
            }
            throw std::runtime_error("Unterminated selected-material name");
        }

        template <typename T> void unchanged(const T* source, const T& before)
        {
            const auto after = one(source);
            resident_image::require(std::memcmp(&before, &after, sizeof(T)) == 0,
                "Selected-material metadata changed during observation");
        }
    };

    inline nlohmann::ordered_json image_metadata(const GfxImage& source)
    {
        const auto v = resident_image::view(source);
        bool admitted = false;
        std::string refusal;
        try { resident_image::validate(v); admitted = source.pixels != nullptr; }
        catch (const std::exception& error) { refusal = error.what(); }
        if (!admitted && refusal.empty()) refusal = "Missing resident pixel pointer";
        return {{"format_namespace", "DXGI_FORMAT"}, {"dxgi_format", v.dxgi_format},
            {"width", v.width}, {"height", v.height}, {"depth", v.depth},
            {"width1", v.width1}, {"height1", v.height1},
            {"level_count", v.level_count}, {"level_count1", v.level_count1},
            {"total_size", v.total_size}, {"map_type", v.map_type}, {"flags", v.flags},
            {"streaming", v.streaming}, {"streamed_part_count", v.streamed_part_count},
            {"use_fallback", v.use_fallback}, {"fallback_level", v.fallback_level},
            {"fallback_size", v.fallback_size}, {"fallback_pointer_present", v.fallback_pointer_present},
            {"delay_load_pixels", v.delay_load_pixels}, {"source_semantic", v.source_semantic},
            {"pixel_pointer_present", source.pixels != nullptr},
            {"resident_metadata_admitted", admitted}, {"resident_metadata_refusal", refusal},
            {"pixel_range_verified", false}, {"pixels_copied", false}};
    }

    template <typename Readable> std::string observe(const XModel* source,
        const std::string& expected_model, unsigned lod, unsigned slot, Readable readable)
    {
        // Return one compact diagnostic. The caller logs it separately and still
        // performs its original geometry selection/refusal afterward.
        nlohmann::ordered_json result = {{"schema", "iw7.t7-selected-material-observation/1"},
            {"headers_rechecked", false}, {"allocation_retained", false},
            {"atomic_snapshot_proven", false}, {"pixels_copied", false}, {"ready", false}};
        try
        {
            reader<Readable> read(readable);
            const auto model = read.one(source);
            const auto model_name = read.name(model.name);
            resident_image::require(model_name == expected_model && model.numLods &&
                model.numLods <= 8 && lod < model.numLods, "Exact selected model/LOD required");
            const auto lod_materials = read.array(model.meshMaterials, model.numLods, 8);
            const auto& table = lod_materials[lod];
            resident_image::require(table.numMaterials && slot < table.numMaterials,
                "Explicit selected material slot required");
            const auto materials = read.array(table.materials, table.numMaterials, 32);
            auto names = nlohmann::ordered_json::array();
            auto aliases = nlohmann::ordered_json::array();
            std::vector<Material> material_headers;
            for (std::size_t i = 0; i < materials.size(); ++i)
            {
                const auto material = read.one(materials[i]);
                material_headers.push_back(material);
                names.push_back(read.name(material.name));
                if (materials[i] == materials[slot]) aliases.push_back(i);
            }
            result["model"] = model_name;
            result["lod"] = lod;
            result["slot"] = slot;
            result["material_names"] = names;
            result["aliased_slots"] = aliases;
            const auto selected = read.one(materials[slot]);
            const auto textures = read.array(selected.textureTable, selected.textureCount, 16);
            const auto samplers = read.array(selected.samplerTable, selected.samplerCount, 16);
            const auto constants = read.array(selected.constantTable, selected.constantCount, 32);
            auto texture_rows = nlohmann::ordered_json::array();
            std::vector<std::pair<const GfxImage*, GfxImage>> image_headers;
            std::vector<std::string> image_names;
            for (std::size_t i = 0; i < textures.size(); ++i)
            {
                const auto& texture = textures[i];
                std::array<std::uint32_t, 2> uv_bits;
                static_assert(sizeof(uv_bits) == sizeof(texture.uvScale));
                std::memcpy(uv_bits.data(), texture.uvScale, sizeof(uv_bits));
                nlohmann::ordered_json row = {{"index", i}, {"nameHash", texture.nameHash},
                    {"usage", texture.usage}, {"uvScaleBits", uv_bits},
                    {"texSizeShift", {texture.texSizeShift[0], texture.texSizeShift[1]}},
                    {"uvOffset", {texture.uvOffset[0], texture.uvOffset[1], texture.uvOffset[2]}},
                    {"isMatureContent", texture.isMatureContent}};
                if (texture.image)
                {
                    const auto image = read.one(texture.image);
                    const auto image_name = read.name(image.name);
                    row["image_name"] = image_name;
                    row["image"] = image_metadata(image);
                    image_headers.emplace_back(texture.image, image);
                    image_names.push_back(image_name);
                }
                else row["image"] = nullptr;
                texture_rows.push_back(std::move(row));
                read.unchanged(selected.textureTable + i, texture);
            }
            auto sampler_rows = nlohmann::ordered_json::array();
            for (std::size_t i = 0; i < samplers.size(); ++i)
            {
                sampler_rows.push_back({{"nameHash", samplers[i].nameHash},
                    {"samplerState", samplers[i].samplerState}});
                read.unchanged(selected.samplerTable + i, samplers[i]);
            }
            auto constant_rows = nlohmann::ordered_json::array();
            for (std::size_t i = 0; i < constants.size(); ++i)
            {
                std::array<std::uint32_t, 4> literal_bits;
                static_assert(sizeof(literal_bits) == sizeof(constants[i].literal));
                std::memcpy(literal_bits.data(), constants[i].literal, sizeof(literal_bits));
                const auto end = std::find(constants[i].name, constants[i].name + 12, '\0');
                constant_rows.push_back({{"nameHash", constants[i].nameHash},
                    {"name", std::string(constants[i].name, end)}, {"literalBits", literal_bits}});
                read.unchanged(selected.constantTable + i, constants[i]);
            }
            nlohmann::ordered_json technique_name = nullptr;
            const char* technique_name_pointer = nullptr;
            if (selected.techniqueSet)
            {
                technique_name_pointer = read.one(&selected.techniqueSet->name);
                technique_name = read.name(technique_name_pointer);
            }
            for (std::size_t i = 0; i < image_headers.size(); ++i)
            {
                read.unchanged(image_headers[i].first, image_headers[i].second);
                resident_image::require(read.name(image_headers[i].second.name) == image_names[i],
                    "Selected image name changed during observation");
            }
            if (selected.techniqueSet)
            {
                read.unchanged(&selected.techniqueSet->name, technique_name_pointer);
                resident_image::require(read.name(technique_name_pointer) == technique_name.get<std::string>(),
                    "Selected technique name changed during observation");
            }
            read.unchanged(materials[slot], selected);
            for (std::size_t i = 0; i < materials.size(); ++i)
            {
                read.unchanged(materials[i], material_headers[i]);
                resident_image::require(read.name(material_headers[i].name) == names[i].get<std::string>(),
                    "Selected-material name changed during observation");
                read.unchanged(table.materials + i, materials[i]);
            }
            read.unchanged(model.meshMaterials + lod, table);
            read.unchanged(source, model);
            resident_image::require(read.name(model.name) == model_name,
                "Selected model name changed during observation");
            result["technique_set"] = technique_name;
            result["textures"] = texture_rows;
            result["samplers"] = sampler_rows;
            result["constants"] = constant_rows;
            result["headers_rechecked"] = true;
            const auto output = result.dump();
            resident_image::require(output.size() <= output_limit, "Material observation output exceeds bound");
            return output;
        }
        catch (const std::exception& error)
        {
            result["refused"] = true;
            result["headers_rechecked"] = false;
            result["reason"] = std::string(error.what()).substr(0, 256);
            try
            {
                const auto output = result.dump();
                if (output.size() <= output_limit) return output;
            }
            catch (const std::exception&) {} // Invalid names must not escape as invalid JSON.
            return nlohmann::ordered_json({{"schema", "iw7.t7-selected-material-observation/1"},
                {"refused", true}, {"reason", "Observation could not be serialized within bounds"},
                {"pixels_copied", false}, {"ready", false}}).dump();
        }
    }
}
