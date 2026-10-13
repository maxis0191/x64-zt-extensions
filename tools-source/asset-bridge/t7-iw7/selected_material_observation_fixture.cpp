// Tiny synthetic fixture for the existing native build owner's combined group.
// No engine, game data, disk payload or real pointer discovery is involved.
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <cstdint>
#include <cstddef>
#include <cstdio>
#define assert_sizeof(T, N) static_assert(sizeof(T) == N)
#define assert_offsetof(T, M, N) static_assert(offsetof(T, M) == N)
#include "selected_material_observation.hpp"

namespace t7 = zonetool::t7;
namespace observation = t7::selected_material_observation;

namespace
{
    unsigned checks = 0;
    void check(bool value)
    {
        ++checks;
        if (!value) throw std::runtime_error("Selected material fixture assertion failed");
    }

    struct fixture
    {
        t7::XModel model{};
        t7::XModelMeshMaterials table{};
        t7::Material material{};
        t7::Material* slots[2] = {&material, &material};
        t7::MaterialTextureDef texture{};
        t7::GfxImage image{};
        t7::MaterialTechniqueSet technique{};
        std::string model_name = "original_fixture_model";
        std::string material_name = "original_fixture_material";
        std::string image_name = "original_fixture_image";
        std::string technique_name = "original_fixture_technique";
        std::string replacement_technique = "replacement_fixture_technique";
        unsigned material_reads = 0;
        unsigned model_reads = 0, image_reads = 0, technique_reads = 0;
        bool change_header = false;
        bool change_model_name = false, change_image_name = false, change_technique_name = false;
        bool change_technique_pointer = false;
        bool deny_image = false;
        std::size_t total_read = 0;

        fixture()
        {
            model.numLods = 1;
            model.meshMaterials = &table;
            table.numMaterials = 2;
            table.materials = slots;
            material.textureCount = 1;
            material.textureTable = &texture;
            material.techniqueSet = &technique;
            texture.image = &image;
            texture.nameHash = 42;
            texture.uvScale[0] = 2.0f;
            texture.uvScale[1] = 0.5f;
            image.width = image.width1 = image.height = image.height1 = 2;
            image.depth = 1;
            image.levelCount = image.levelCount1 = 1;
            image.format = DXGI_FORMAT_R8G8B8A8_UNORM;
            image.mapType = t7::MAPTYPE_2D;
            image.semantic = t7::IMG_SEMANTIC_DIFFUSE_MAP;
            image.totalSize = 16;
            image.pixels = reinterpret_cast<std::uint8_t*>(std::uintptr_t{1}); // NEVER readable.
        }

        void readable(const void* pointer, std::size_t bytes)
        {
            if (deny_image && pointer == &image) throw std::runtime_error("Synthetic image unreadable");
            if (pointer == &material && bytes == sizeof(material) && ++material_reads == 4 && change_header)
                material.cameraRegion = static_cast<t7::GfxCameraRegion>(1);
            if (pointer == &model && bytes == sizeof(model) && ++model_reads == 2 && change_model_name)
                model_name[0] = 'x';
            if (pointer == &image && bytes == sizeof(image) && ++image_reads == 2 && change_image_name)
                image_name[0] = 'x';
            if (pointer == &technique.name && bytes == sizeof(technique.name) && ++technique_reads == 2)
            {
                if (change_technique_name) technique_name[0] = 'x';
                if (change_technique_pointer) technique.name = replacement_technique.c_str();
            }
            const auto address = reinterpret_cast<std::uintptr_t>(pointer);
            const std::pair<const void*, std::size_t> ranges[] = {
                {&model, sizeof(model)}, {&table, sizeof(table)}, {slots, sizeof(slots)},
                {&material, sizeof(material)}, {&texture, sizeof(texture)}, {&image, sizeof(image)},
                {&technique.name, sizeof(technique.name)},
                {model_name.c_str(), model_name.size()+1},
                {material_name.c_str(), material_name.size()+1}, {image_name.c_str(), image_name.size()+1},
                {technique_name.c_str(), technique_name.size()+1},
                {replacement_technique.c_str(), replacement_technique.size()+1}
            };
            for (const auto& range : ranges)
            {
                const auto start = reinterpret_cast<std::uintptr_t>(range.first);
                if (address >= start && address-start < range.second && bytes <= range.second-(address-start))
                {
                    total_read += bytes;
                    return;
                }
            }
            throw std::runtime_error("Synthetic range/pixels refused");
        }

        nlohmann::ordered_json observe(unsigned lod = 0, unsigned slot = 0)
        {
            model.name = model_name.c_str();
            material.name = material_name.c_str();
            image.name = image_name.c_str();
            technique.name = technique_name.c_str();
            const auto text = observation::observe(&model, model_name, lod, slot,
                [this](const void* p, std::size_t n) { readable(p, n); });
            check(text.size() <= observation::output_limit);
            return nlohmann::ordered_json::parse(text);
        }
    };
}

int main()
{
    try
    {
        fixture good;
        const auto result = good.observe();
        check(result.at("material_names") == nlohmann::ordered_json::array({good.material_name, good.material_name}));
        check(result.at("aliased_slots") == nlohmann::ordered_json::array({0, 1}));
        check(result.at("textures")[0].at("image_name") == good.image_name);
        check(result.at("textures")[0].at("image").at("resident_metadata_admitted") == true);
        check(result.at("textures")[0].at("uvScaleBits") == nlohmann::ordered_json::array({0x40000000u, 0x3f000000u}));
        check(result.at("headers_rechecked") == true && result.at("pixels_copied") == false && result.at("ready") == false);
        check(good.total_read <= observation::read_limit); // The pixel sentinel was never requested.

        fixture streamed;
        streamed.image.streaming = 1;
        const auto streamed_result = streamed.observe();
        check(streamed_result.at("textures")[0].at("image").at("resident_metadata_admitted") == false);
        check(streamed_result.at("pixels_copied") == false);

        fixture changing;
        changing.change_header = true;
        const auto changed = changing.observe();
        check(changed.at("refused") == true && changed.at("headers_rechecked") == false);
        check(changed.at("material_names").size() == 2);

        for (unsigned name_case = 0; name_case < 4; ++name_case)
        {
            fixture changing_name;
            changing_name.change_model_name = name_case == 0;
            changing_name.change_image_name = name_case == 1;
            changing_name.change_technique_name = name_case == 2;
            changing_name.change_technique_pointer = name_case == 3;
            const auto refused_name = changing_name.observe();
            check(refused_name.at("refused") == true && refused_name.at("headers_rechecked") == false);
        }

        fixture unreadable;
        unreadable.deny_image = true;
        const auto denied = unreadable.observe();
        check(denied.at("refused") == true && denied.at("material_names").size() == 2);

        fixture excessive;
        excessive.material.textureCount = 17;
        check(excessive.observe().at("refused") == true);
        fixture invalid_lod;
        check(invalid_lod.observe(1).at("refused") == true);
        fixture invalid_slot;
        check(invalid_slot.observe(0, 2).at("refused") == true);
        fixture long_name;
        long_name.model_name.assign(257, 'a');
        check(long_name.observe().at("refused") == true);
        std::printf("PASS selected material metadata fixture: %u checks; no pixels or engine calls.\n", checks);
        return 0;
    }
    catch (const std::exception& error)
    {
        std::fprintf(stderr, "%s\n", error.what());
        return 1;
    }
}
