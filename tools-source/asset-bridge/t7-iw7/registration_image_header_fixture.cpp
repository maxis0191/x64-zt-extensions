// Authored synthetic owned pages only. Requires separate admitted CPP GO.
#define main original_material_fixture_main
#include "selected_material_observation_fixture.cpp"
#undef main
#include "selected_image_registration_observer.hpp"

namespace capture = t7::registration_image_header_capture;
namespace provenance = t7::selected_image_provenance;
namespace
{
    void setup(fixture& f)
    {
        f.seven_bindings(); f.model_name = provenance::model_name;
        f.model.name = f.model_name.c_str(); f.material.name = f.material_name.c_str();
        f.image.name = f.image_name.c_str(); f.technique.name = f.technique_name.c_str();
    }
    t7::XAssetHeader model_header(fixture& f)
    { t7::XAssetHeader result{}; result.data = &f.model; return result; }
    provenance::memory_state memory(const void* pointer, bool readable)
    {
        provenance::memory_state value{};
        const auto address = reinterpret_cast<std::uintptr_t>(pointer);
        value.complete = true; value.readable = readable; value.count = 1;
        value.rows[0] = {address, address, capture::span,
            static_cast<DWORD>(readable ? MEM_COMMIT : MEM_RESERVE),
            static_cast<DWORD>(readable ? PAGE_READWRITE : 0), 0};
        return value;
    }
    capture::association association(fixture& f, std::uint64_t ordinal = 1)
    {
        return {ordinal, reinterpret_cast<std::uintptr_t>(&f.model),
            reinterpret_cast<std::uintptr_t>(&f.material),
            reinterpret_cast<std::uintptr_t>(f.material.textureTable),
            reinterpret_cast<std::uintptr_t>(f.extra_textures[4].image), true, true};
    }
    nlohmann::ordered_json diagnostic(fixture& f)
    {
        bool readable = true;
        auto guard = [&](const void* p, std::size_t n) { f.readable(p,n); };
        auto query = [&](const void* p) { return memory(p,readable); };
        provenance::observer probe(guard,query); probe.begin();
        probe.after_model_add(t7::ASSET_TYPE_XMODEL,model_header(f),model_header(f));
        readable = false;
        return probe.finish(&f.model);
    }
    template <typename Copy> nlohmann::ordered_json capture_direct(fixture& f, Copy copy)
    {
        capture::cache cache;
        auto guard = [&](const void* p, std::size_t n) { f.readable(p,n); };
        auto query = [&](const void* p) { return memory(p,true); };
        cache.reset(); cache.record(association(f),&f.model,guard,query,copy);
        return cache.finish(diagnostic(f),association(f),association(f,2),true);
    }
}

int main()
{
    try
    {
        // Actual derived observer and actual fixed leaf: no current header/name
        // read is allowed after the synthetic backing becomes unavailable.
        fixture f; setup(f);
        bool readable = true;
        auto guard = [&](const void* p, std::size_t n) { f.readable(p,n); };
        auto query = [&](const void* p) { return memory(p,readable); };
        provenance::observer probe(guard,query);
        unsigned original_calls = 0;
        const auto original = [&](t7::XAssetType, t7::XAssetHeader) { ++original_calls; return model_header(f); };
        probe.begin_registration_metadata();
        const auto returned = probe.original_add_and_observe(t7::ASSET_TYPE_XMODEL,model_header(f),original);
        check(returned.data == &f.model && original_calls == 1);
        const auto reads_before_finish = f.image_reads;
        f.deny_image = f.deny_image_name = true; readable = false;
        f.image.width = 777; f.image_name[0] = 'x';
        const auto result = probe.finish_registration_metadata(&f.model,true);
        check(result.at("refused") == false && result.at("registration_header_observed") == true);
        check(result.at("schema") == capture::schema && result.at("source_profile") == capture::profile);
        check(result.size() == 33);
        check(result.at("capture_phase") == capture::phase && result.at("recheck_phase") == capture::phase);
        check(result.at("capture_ordinal") == result.at("provenance").at("registration").at("ordinal"));
        check(result.at("header_copies") == 2 && result.at("registration_header_bytes_copied") == 528);
        check(result.at("image").at("width") == 2 && result.at("image").at("image_name") == "original_fixture_image");
        check(f.image_reads == reads_before_finish);
        check(result.at("provenance").at("lookup").at("range_readable_at_query") == false);
        check(result.at("provenance").at("image_body_bytes_read") == 0);
        for (const auto key : {"same_object_proven", "lifetime_proven", "allocation_retained",
                              "atomic_snapshot_proven", "runtime_abi_proven", "pixels_copied", "ready"})
            check(result.at(key) == false);

        fixture raw; setup(raw);
        reinterpret_cast<unsigned char*>(&raw.image)[188] = 2;
        const auto invalid = capture_direct(raw,&capture::copy_leaf);
        check(invalid.at("refused") == true && invalid.at("image").is_null());
        check(invalid.at("header_copies") == 1);
        reinterpret_cast<unsigned char*>(&raw.image)[188] = 0;

        fixture changed; setup(changed); unsigned header_reads = 0;
        const auto changed_copy = [&](void* to,const void* from,std::size_t n)
        { if (n == capture::span && ++header_reads == 2) ++changed.image.width; return capture::copy_leaf(to,from,n); };
        check(capture_direct(changed,changed_copy).at("refused") == true);
        fixture name_changed; setup(name_changed); header_reads = 0;
        const auto name_copy = [&](void* to,const void* from,std::size_t n)
        { if (n == capture::span && ++header_reads == 2) name_changed.image_name[0] = 'x'; return capture::copy_leaf(to,from,n); };
        check(capture_direct(name_changed,name_copy).at("refused") == true);
        fixture fault; setup(fault);
        const auto fault_copy = [](void*,const void*,std::size_t) { return false; };
        const auto refused_copy = capture_direct(fault,fault_copy);
        check(refused_copy.at("refused") == true && refused_copy.at("image").is_null());
        check(refused_copy.at("registration_header_bytes_copied").is_null());

        fixture duplicate; setup(duplicate);
        auto dup_guard = [&](const void* p,std::size_t n) { duplicate.readable(p,n); };
        auto dup_query = [&](const void* p) { return memory(p,true); };
        provenance::observer duplicate_probe(dup_guard,dup_query);
        duplicate_probe.begin_registration_metadata();
        duplicate_probe.after_model_add(t7::ASSET_TYPE_XMODEL,model_header(duplicate),model_header(duplicate));
        duplicate_probe.after_model_add(t7::ASSET_TYPE_XMODEL,model_header(duplicate),model_header(duplicate));
        check(duplicate_probe.finish_registration_metadata(&duplicate.model,true).at("refused") == true);
        bool reused = false;
        try { duplicate_probe.begin_registration_metadata(); } catch (const std::exception&) { reused = true; }
        check(reused);

        fixture reset_fixture; setup(reset_fixture);
        auto reset_guard = [&](const void* p,std::size_t n) { reset_fixture.readable(p,n); };
        auto reset_query = [&](const void* p) { return memory(p,true); };
        capture::cache reset_cache;
        reset_cache.record(association(reset_fixture),&reset_fixture.model,reset_guard,reset_query,&capture::copy_leaf);
        const auto reset_provenance = diagnostic(reset_fixture);
        check(reset_cache.finish(reset_provenance,association(reset_fixture),association(reset_fixture,2),true).at("refused") == false);
        auto wrong_epoch = association(reset_fixture); ++wrong_epoch.ordinal;
        check(reset_cache.finish(reset_provenance,wrong_epoch,association(reset_fixture,2),true).at("refused") == true);
        auto changed_lookup = association(reset_fixture,2); ++changed_lookup.image;
        check(reset_cache.finish(reset_provenance,association(reset_fixture),changed_lookup,true).at("refused") == true);
        check(reset_cache.finish(reset_provenance,association(reset_fixture),association(reset_fixture,2),false).at("refused") == true);
        reset_cache.reset();
        const auto cleared = reset_cache.finish(reset_provenance,association(reset_fixture),association(reset_fixture,2),true);
        check(cleared.at("refused") == true && cleared.at("image").is_null() && cleared.at("header_copies") == 0);
        provenance::observer original_error_probe(reset_guard,reset_query);
        original_error_probe.begin_registration_metadata();
        unsigned failed_original_calls = 0; bool original_error = false;
        try
        {
            original_error_probe.original_add_and_observe(t7::ASSET_TYPE_XMODEL,model_header(reset_fixture),
                [&](t7::XAssetType,t7::XAssetHeader) -> t7::XAssetHeader
                { ++failed_original_calls; throw std::runtime_error("Original add failure"); });
        }
        catch (const std::exception&) { original_error = true; }
        check(original_error && failed_original_calls == 1);

        // Real leaf fault containment on OWNED synthetic pages. The existing
        // guard sees readable memory, then protection is withdrawn before copy.
        fixture protected_page; setup(protected_page);
        void* page = VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
        if (!page) throw std::runtime_error("Synthetic header page allocation failed");
        std::memcpy(page,&protected_page.image,capture::span);
        protected_page.extra_textures[4].image = static_cast<t7::GfxImage*>(page);
        bool withdrawn = false;
        auto page_guard = [&](const void* p,std::size_t n)
        {
            if (p == page && n == capture::span)
            {
                const auto before = provenance::query_memory_state(page);
                if (!before.complete || !before.readable) throw std::runtime_error("Synthetic guard failed before withdrawal");
                DWORD old{};
                if (!VirtualProtect(page,4096,PAGE_NOACCESS,&old)) throw std::runtime_error("Synthetic withdrawal failed");
                withdrawn = true;
                return;
            }
            protected_page.readable(p,n);
        };
        provenance::observer protected_probe(page_guard,&provenance::query_memory_state);
        protected_probe.begin_registration_metadata();
        protected_probe.after_model_add(t7::ASSET_TYPE_XMODEL,model_header(protected_page),model_header(protected_page));
        const auto denied = protected_probe.finish_registration_metadata(&protected_page.model,true);
        const bool released = VirtualFree(page,0,MEM_RELEASE) != 0;
        check(withdrawn && released);
        check(denied.at("refused") == true && denied.at("image").is_null());
        check(denied.at("header_copies") == 0 && denied.at("registration_header_bytes_copied").is_null());
        check(denied.at("registration_header_observed") == false);
        unsigned char byte{};
        void* name_page = VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
        if (!name_page) throw std::runtime_error("Synthetic name page allocation failed");
        *static_cast<unsigned char*>(name_page) = 'n';
        check(capture::copy_name_byte_leaf(&byte,static_cast<const unsigned char*>(name_page)) && byte == 'n');
        DWORD prior{};
        if (!VirtualProtect(name_page,4096,PAGE_NOACCESS,&prior)) throw std::runtime_error("Synthetic name withdrawal failed");
        const bool name_fault_refused = !capture::copy_name_byte_leaf(&byte,static_cast<const unsigned char*>(name_page));
        const bool name_released = VirtualFree(name_page,0,MEM_RELEASE) != 0;
        check(name_fault_refused && name_released);
        check(!capture::copy_leaf(&byte,&byte,2));
        if (checks != 39) throw std::runtime_error("Exact 39 registration fixture checks required");
        std::printf("IW7_T7_REGISTRATION_HEADER_CHECKS=%u\n",checks);
        return 0;
    }
    catch (const std::exception& error) { std::fprintf(stderr,"%s\n",error.what()); return 1; }
}
