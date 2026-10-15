// Authored owned synthetic data. NOT compiled/executed by the Source test suite.
#define main original_material_fixture_main
#include "selected_material_observation_fixture.cpp"
#undef main
#include "selected_image_material_bindings_observer.hpp"

namespace bindings = t7::registration_material_bindings;
namespace provenance = t7::selected_image_provenance;
namespace capture = t7::registration_image_header_capture;
namespace
{
    void setup(fixture& f)
    {
        f.seven_bindings(); f.model_name = provenance::model_name;
        f.model.name = f.model_name.c_str(); f.image.name = f.image_name.c_str();
        for (unsigned i=0; i<7; ++i)
        {
            f.extra_textures[i].image = &f.image;
            f.extra_textures[i].nameHash = 100u+i; // Intentionally NOT the historical binding4 hash.
            f.extra_textures[i].usage = static_cast<decltype(f.extra_textures[i].usage)>(i == 6 ? 65535 : i);
        }
    }
    provenance::memory_state memory(const void* pointer)
    {
        provenance::memory_state result{};
        const auto address = reinterpret_cast<std::uintptr_t>(pointer);
        result.complete = result.readable = true; result.count = 1;
        result.rows[0] = {address,address,264,MEM_COMMIT,PAGE_READWRITE,0};
        return result;
    }
    t7::XAssetHeader header(fixture& f)
    { t7::XAssetHeader value{}; value.data = &f.model; return value; }
    template <typename Copy> nlohmann::ordered_json collect(fixture& f, Copy copy)
    {
        bindings::collector result;
        result.record(1,&f.model,[&](const void* p,std::size_t n){f.readable(p,n);},&memory,copy);
        return result.finish(1,1,false,false,true);
    }
}
int main()
{
    try
    {
        fixture all; setup(all);
        auto guard = [&](const void* p,std::size_t n){all.readable(p,n);};
        provenance::observer probe(guard,&memory);
        probe.begin_material_bindings();
        unsigned calls = 0;
        const auto returned = probe.original_add_and_observe(t7::ASSET_TYPE_XMODEL,header(all),
            [&](t7::XAssetType,t7::XAssetHeader){++calls; return header(all);});
        check(calls == 1 && returned.data == &all.model);
        const auto reads = all.image_reads;
        all.deny_image = all.deny_image_name = true;
        all.image.width = 999;
        const auto result = probe.finish_material_bindings(true);
        check(result.at("refused") == false && result.at("bindings").size() == 7);
        check(result.at("schema") == bindings::schema && result.at("source_profile") == bindings::profile);
        check(result.at("header_copies") == 14 && result.at("completed_header_bytes") == 3696);
        check(all.image_reads == reads && result.at("model_default").is_null());
        check(result.at("bindings")[0].at("snapshot").at("image").at("width") == 2);
        check(result.at("bindings")[4].at("binding_hash_u32") == 104);
        check(result.at("bindings")[6].at("usage_u16") == 65535);

        fixture first_denied; setup(first_denied);
        first_denied.extra_textures[0].image = reinterpret_cast<t7::GfxImage*>(std::uintptr_t{0x1000});
        const auto independent = collect(first_denied,&capture::copy_leaf);
        check(independent.at("refused") == false);
        check(independent.at("bindings")[0].at("snapshot").at("refused") == true);
        check(independent.at("bindings")[6].at("snapshot").at("header_observed") == true);
        check(independent.at("completed_header_bytes") == 3168);

        fixture fault; setup(fault);
        unsigned attempts = 0;
        const auto partial = collect(fault,[&](void* to,const void* from,std::size_t n)
        {
            if (n == 264 && ++attempts == 3)
            { std::memcpy(to,from,17); return false; }
            return capture::copy_leaf(to,from,n);
        });
        check(partial.at("refused") == false && partial.at("bindings").size() == 7);
        check(partial.at("completed_header_bytes").is_null() && partial.at("header_copies") == 12);
        check(partial.at("bindings")[1].at("snapshot").at("copy_fault") == true);
        check(partial.at("bindings")[6].at("snapshot").at("header_observed") == true);

        fixture raw; setup(raw); attempts = 0;
        const auto invalid = collect(raw,[&](void* to,const void* from,std::size_t n)
        {
            const bool ok = capture::copy_leaf(to,from,n);
            if (n == 264 && ++attempts == 2) static_cast<unsigned char*>(to)[188] = 2;
            return ok;
        });
        check(invalid.at("bindings")[0].at("snapshot").at("refused") == true);
        check(invalid.at("bindings")[0].at("snapshot").at("image").is_null());
        check(invalid.at("bindings")[6].at("snapshot").at("header_observed") == true);

        fixture changed; setup(changed); changed.change_image_name = true;
        const auto name_changed = collect(changed,&capture::copy_leaf);
        check(name_changed.at("bindings")[0].at("snapshot").at("refused") == true);
        check(name_changed.at("bindings")[6].at("snapshot").at("header_observed") == true);

        fixture chain; setup(chain); attempts = 0;
        const auto chain_changed = collect(chain,[&](void* to,const void* from,std::size_t n)
        {
            const bool ok = capture::copy_leaf(to,from,n);
            if (n == 264 && ++attempts == 1) ++chain.extra_textures[0].nameHash;
            return ok;
        });
        check(chain_changed.at("refused") == true && chain_changed.at("completed_header_bytes").is_null());
        check(chain_changed.at("bindings").size() == 7);
        check(chain_changed.at("bindings")[0].at("binding_rechecked") == false);

        fixture wrong_count; setup(wrong_count); wrong_count.material.textureCount = 8;
        const auto count_refused = collect(wrong_count,&capture::copy_leaf);
        check(count_refused.at("refused") == true && count_refused.at("bindings").empty());

        fixture controls; controls.image_name = std::string(255,'\x01'); setup(controls);
        const auto bounded = collect(controls,&capture::copy_leaf);
        check(bounded.at("refused") == false && bounded.dump().size() < 32768);
        check(bounded.at("bindings")[6].at("snapshot").at("refused") == true);

        fixture duplicate; setup(duplicate);
        auto dup_guard = [&](const void* p,std::size_t n){duplicate.readable(p,n);};
        provenance::observer dup(dup_guard,&memory); dup.begin_material_bindings();
        dup.after_model_add(t7::ASSET_TYPE_XMODEL,header(duplicate),header(duplicate));
        dup.after_model_add(t7::ASSET_TYPE_XMODEL,header(duplicate),header(duplicate));
        check(dup.finish_material_bindings(true).at("refused") == true);
        bool single_use = false;
        try { dup.begin_material_bindings(); } catch (const std::exception&) { single_use = true; }
        check(single_use);
        for (const auto key : {"descriptor_admissible","source_asset_name_association_proven",
            "model_binding_correlated","renderer_binding_proven","same_object_proven","allocation_retained",
            "atomic_snapshot_proven","runtime_abi_proven","lifetime_proven","pixels_copied","ready"})
            check(result.at(key) == false);
        check(result.at("qualified_object_mip_count").is_null() && result.at("payload_bytes_read") == 0);
        if (checks != 41) throw std::runtime_error("Exact 41 registration bindings fixture checks required");
        std::printf("IW7_T7_REGISTRATION_BINDINGS_CHECKS=%u\n",checks);
        return 0;
    }
    catch (const std::exception& error) { std::fprintf(stderr,"%s\n",error.what()); return 1; }
}
