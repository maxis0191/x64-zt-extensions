// Authored callback/memory metadata: no engine or real image body reads.
#define main legacy_material_fixture_main
#include "selected_material_observation_fixture.cpp"
#undef main
#include "selected_image_provenance.hpp"

namespace provenance = t7::selected_image_provenance;
namespace
{
    void prepare(fixture& f)
    {
        f.seven_bindings();
        f.model_name = provenance::model_name;
        f.model.name = f.model_name.c_str();
        f.material.name = f.material_name.c_str();
        f.image.name = f.image_name.c_str();
        f.technique.name = f.technique_name.c_str();
        f.deny_image = true;
    }
    t7::XAssetHeader header(fixture& f)
    {
        t7::XAssetHeader result{};
        result.data = &f.model;
        return result;
    }
    provenance::memory_state memory(const void* pointer, bool readable = false)
    {
        provenance::memory_state result{};
        result.complete = true;
        result.readable = readable;
        result.count = 1;
        const auto address = reinterpret_cast<std::uintptr_t>(pointer);
        result.rows[0] = {address, address, provenance::image_span,
            static_cast<DWORD>(readable ? MEM_COMMIT : MEM_FREE),
            static_cast<DWORD>(readable ? PAGE_READWRITE : PAGE_NOACCESS), 0};
        return result;
    }
}

int main()
{
    try
    {
        fixture f;
        prepare(f);
        unsigned image_attempts = 0, queries = 0;
        auto guard = [&](const void* p, std::size_t n)
        {
            if (p == &f.image) { ++image_attempts; throw std::runtime_error("Image body denied"); }
            f.readable(p,n);
        };
        auto query = [&](const void* p) { ++queries; check(p == &f.image); return memory(p); };
        // Causal old/new difference: old binding read refuses the body; the new
        // operation observes only its field and authored query metadata.
        const auto old = nlohmann::ordered_json::parse(observation::observe_binding(
            &f.model, provenance::model_name, 0, 0, guard, {4u, provenance::binding_hash}));
        check(old.at("refused") == true && old.at("failure_stage") == "image_header");
        check(image_attempts == 1 && queries == 0);
        provenance::observer probe(guard,query);
        auto incoming = header(f);
        incoming.data = reinterpret_cast<void*>(std::uintptr_t{0xdeadbeef});
        unsigned original_calls = 0;
        auto original = [&](t7::XAssetType type,t7::XAssetHeader in)
        { ++original_calls;check(type==t7::ASSET_TYPE_XMODEL && in.data==incoming.data);return header(f); };
        const auto inactive_return = probe.original_add_and_observe(t7::ASSET_TYPE_XMODEL,incoming,original);
        check(inactive_return.data==&f.model && original_calls==1);
        check(queries == 0); // Inactive route never inspects any source.
        probe.begin();
        probe.after_model_add(t7::ASSET_TYPE_IMAGE,incoming,incoming);
        check(queries == 0); // IMAGE add route remains untouched.
        const auto active_return = probe.original_add_and_observe(t7::ASSET_TYPE_XMODEL,incoming,original);
        check(active_return.data==&f.model && original_calls==2);
        const auto good = probe.finish(&f.model);
        check(good.at("capture_complete") == true && good.at("refused") == false);
        check(good.at("registration").at("incoming_model_header_hex") == "00000000deadbeef");
        check(good.at("registration").at("selected_model_header_hex") ==
            provenance::hex(reinterpret_cast<std::uintptr_t>(&f.model)));
        check(good.at("header_changed") == false && good.at("same_numeric_image_field") == true);
        check(good.at("lookup").at("incoming_model_header_hex").is_null());
        check(good.at("registration").at("range_readable_at_query") == false);
        check(good.at("registration").at("regions")[0].at("state_raw") == MEM_FREE);
        check(queries == 2 && image_attempts == 1);
        check(good.at("image_body_bytes_read") == 0 && good.at("payload_bytes_read") == 0);
        check(good.at("same_object_proven") == false && good.at("lifetime_proven") == false &&
            good.at("allocation_retained") == false && good.at("ready") == false);
        check(good.at("registration").at("ordinal") < good.at("lookup").at("ordinal"));
        check(good.at("registration_path_changed") == false);
        bool reused = false;
        try { probe.begin(); } catch (const std::exception&) { reused = true; }
        check(reused);

        fixture second;
        prepare(second);
        auto both = [&](const void* p,std::size_t n)
        {
            try { f.readable(p,n); }
            catch (const std::exception&) { second.readable(p,n); }
        };
        provenance::observer changed(both,[](const void* p) { return memory(p,true); });
        changed.begin();
        changed.after_model_add(t7::ASSET_TYPE_XMODEL,incoming,header(f));
        const auto different = changed.finish(&second.model);
        check(different.at("capture_complete") == true && different.at("header_changed") == true);
        check(different.at("same_numeric_image_field") == false &&
            different.at("same_object_proven") == false);

        provenance::observer missing(guard,query);
        missing.begin();
        const auto absent = missing.finish(&f.model);
        check(absent.at("refused") == true && absent.at("matched_registrations") == 0);
        check(absent.at("association_complete") == false && absent.at("header_changed").is_null() &&
            absent.at("same_numeric_image_field").is_null());
        check(absent.at("registration").at("image_field_hex").is_null() &&
            absent.at("registration").at("selected_model_header_hex").is_null());

        provenance::observer duplicate(guard,query);
        duplicate.begin();
        duplicate.after_model_add(t7::ASSET_TYPE_XMODEL,incoming,header(f));
        duplicate.after_model_add(t7::ASSET_TYPE_XMODEL,incoming,header(f));
        const auto twice = duplicate.finish(&f.model);
        check(twice.at("duplicate_registration") == true && twice.at("refused") == true);

        provenance::observer unknown(guard,query);
        unknown.begin();
        t7::XAssetHeader invalid{};
        const auto returned_invalid = unknown.original_add_and_observe(t7::ASSET_TYPE_XMODEL,incoming,
            [&](t7::XAssetType,t7::XAssetHeader) { ++original_calls;return invalid; });
        check(returned_invalid.data==nullptr && original_calls==3);
        const auto refused = unknown.finish(&f.model);
        check(refused.at("registration_search_refused") == true &&
            refused.at("capture_complete") == false);
        bool original_error = false;
        try { unknown.original_add_and_observe(t7::ASSET_TYPE_XMODEL,incoming,
            [](t7::XAssetType,t7::XAssetHeader)->t7::XAssetHeader {throw std::runtime_error("Original");}); }
        catch (const std::runtime_error& error) { original_error=std::string(error.what())=="Original"; }
        check(original_error);

        f.extra_textures[4].nameHash ^= 1;
        provenance::observer bad_hash(guard,query);
        bad_hash.begin();
        bad_hash.after_model_add(t7::ASSET_TYPE_XMODEL,incoming,header(f));
        check(bad_hash.finish(&f.model).at("refused") == true);
        f.extra_textures[4].nameHash ^= 1;

        provenance::observer truncated(guard,[](const void* p)
        { auto v=memory(p);v.rows[0].extent=1;return v; });
        truncated.begin();
        truncated.after_model_add(t7::ASSET_TYPE_XMODEL,incoming,header(f));
        check(truncated.finish(&f.model).at("refused") == true);
        provenance::observer extra(guard,[](const void* p)
        { auto v=memory(p);v.count=3;return v; });
        extra.begin();
        extra.after_model_add(t7::ASSET_TYPE_XMODEL,incoming,header(f));
        check(extra.finish(&f.model).at("refused") == true);

        std::printf("PASS selected image provenance fixture: %u checks; no engine/image bodies.\n",checks);
        return 0;
    }
    catch (const std::exception& error) { std::fprintf(stderr,"%s\n",error.what());return 1; }
}
