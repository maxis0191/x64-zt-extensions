// The generated baseline differs only in its derived observer include and main name.
// Its existing 39 checks run first; no historical result is relabelled.
#include <iostream>
#include "incoming_registration_baseline_fixture.cpp"

namespace incoming = t7::incoming_image_event_observation;
namespace
{
    unsigned incoming_checks=0;
    void ic(bool ok) { ++incoming_checks; if (!ok) throw std::runtime_error("Incoming fixture check failed"); }
    std::vector<std::string> arguments()
    { return {"fixture.exe",incoming::option,"mp_freerun_04","p7_fre_platform_cap_02","0"}; }
    t7::XAssetHeader image_header(fixture& f) { t7::XAssetHeader h{};h.data=&f.image;return h; }
    void named(fixture& f,const std::string& name)
    { setup(f);f.image_name=name;f.image.name=f.image_name.c_str(); }
    template<typename Copy> nlohmann::ordered_json one(fixture& f,Copy copy)
    {
        incoming::collector c;c.arm(arguments(),true);
        c.observe(t7::ASSET_TYPE_IMAGE,image_header(f),[&](const void* p,std::size_t n){f.readable(p,n);},
            [&](const void* p){return memory(p,true);},copy);
        c.begin_map();return c.finish(true);
    }
}
int main()
{
    try
    {
        if (original_registration_fixture_main()!=0) return 1;
        // Actual early native predicate/configure: malformed/mixed args cannot arm or read.
        for (unsigned bad_case=0;bad_case<7;++bad_case)
        {
            fixture f;named(f,incoming::target);unsigned reads=0;
            auto guard=[&](const void*,std::size_t){++reads;};
            auto query=[&](const void* p){return memory(p,true);};
            provenance::observer probe(guard,query);auto args=arguments();
            switch(bad_case){case 0:args.pop_back();break;case 1:args.push_back("-t7-iw7-image-registration-metadata-v1");break;
                case 2:args[1]="-t7-iw7-image-registration-metadata-v1";break;case 3:args[2]="cp_zmb";break;
                case 4:args[3]="other";break;case 5:args[4]="00";break;case 6:args[0]="";break;}
            bool refused=false;try{probe.configure_incoming(args,true);}catch(...){refused=true;}
            ic(refused);probe.before_image_bypass(t7::ASSET_TYPE_IMAGE,image_header(f));ic(reads==0 && !probe.incoming_selected());
        }
        {
            incoming::collector c;ic(!c.arm({},false));
            bool refused=false;try{c.begin_map();}catch(...){refused=true;}ic(refused);
        }
        {
            fixture f;named(f,std::string(",")+incoming::target);f.image={};f.image.name=f.image_name.c_str();
            auto guard=[&](const void* p,std::size_t n){f.readable(p,n);};auto query=[&](const void* p){return memory(p,true);};
            provenance::observer probe(guard,query);probe.configure_incoming(arguments(),true);
            probe.before_image_bypass(t7::ASSET_TYPE_IMAGE,image_header(f));probe.begin_incoming_map();
            f.image_name=incoming::target;f.image.name=f.image_name.c_str();f.image.width=64;f.image.height=32;f.image.depth=1;
            f.image.levelCount=7;f.image.format=DXGI_FORMAT_BC1_UNORM;f.image.streamedPartCount=1;f.image.streamedParts[0].xpakEntry.key=0x123;
            probe.before_image_bypass(t7::ASSET_TYPE_IMAGE,image_header(f));
            const auto before=f.image_reads;f.deny_image=f.deny_image_name=true;f.image.width=777;f.image_name[0]='X';
            const auto r=probe.finish_incoming(true);
            ic(r.at("schema")==incoming::schema && r.at("source_profile")==incoming::profile && r.at("cases").size()==4);
            ic(r.at("refused")==false && r.at("window_complete")==true && r.at("bootstrap_complete")==true && r.at("map_complete")==true);
            ic(r.at("reference_events")==1 && r.at("ordinary_name_events")==1 && r.at("image_callbacks")==2);
            const auto& ref=r.at("cases").at(0);const auto& ordinary=r.at("cases").at(3);
            ic(ref.at("raw_name")==std::string(",")+incoming::target && ref.at("effective_name")==incoming::target && ref.at("leading_comma_reference")==true);
            ic(ref.at("snapshot").at("image").at("width")==0 && ref.at("nonzero_descriptor_scalar_fields")==0);
            ic(ordinary.at("raw_name")==incoming::target && ordinary.at("snapshot").at("image").at("image_name")==incoming::target && ordinary.at("snapshot").at("image").at("width")==64);
            ic(ordinary.at("snapshot").at("header_copies")==2 && ordinary.at("snapshot").at("completed_header_bytes")==528 && ordinary.at("unique_in_phase")==true);
            ic(r.at("cases").at(1).at("state")=="not_observed" && r.at("cases").at(1).at("snapshot").is_null() && r.at("cases").at(1).at("raw_name").is_null());
            ic(f.image_reads==before && ordinary.at("descriptor_admissible")==false && r.at("qualified_object_mip_count").is_null());
            for (const auto key : {"descriptor_admissible","source_asset_name_association_proven","model_binding_correlated","renderer_binding_proven",
                "same_pointer_proven","same_object_proven","allocation_retained","atomic_snapshot_proven","runtime_abi_proven","lifetime_proven","pixels_copied","ready"}) ic(r.at(key)==false);
        }
        {
            fixture f;unsigned full_copies=0;incoming::collector c;c.arm(arguments(),true);
            auto guard=[&](const void* p,std::size_t n){f.readable(p,n);};auto query=[&](const void* p){return memory(p,true);};
            auto copy=[&](void* t,const void* s,std::size_t n){if(n==264)++full_copies;return capture::copy_leaf(t,s,n);};
            for (const auto name : {"","$Camo_base_normal","$camo_base_normal_extra",",,$camo_base_normal","camo_base_normal","other"})
            {named(f,name);c.observe(t7::ASSET_TYPE_IMAGE,image_header(f),guard,query,copy);}
            c.observe(t7::ASSET_TYPE_XMODEL,image_header(f),guard,query,copy);c.begin_map();const auto r=c.finish(true);
            ic(full_copies==0 && r.at("image_callbacks")==6 && r.at("non_target_callbacks")==6);
            ic(r.at("ordinary_name_observed")==false && r.at("ordinary_absence_scope")=="not_observed_in_this_bounded_callback_window");
        }
        {
            fixture f;named(f,incoming::target);incoming::collector c;c.arm(arguments(),true);unsigned copies=0;
            auto guard=[&](const void* p,std::size_t n){f.readable(p,n);};auto query=[&](const void* p){return memory(p,true);};
            auto copy=[&](void* t,const void* s,std::size_t n){if(n==264)++copies;return capture::copy_leaf(t,s,n);};
            c.observe(t7::ASSET_TYPE_IMAGE,image_header(f),guard,query,copy);f.image.width=99;
            c.observe(t7::ASSET_TYPE_IMAGE,image_header(f),guard,query,copy);c.begin_map();const auto r=c.finish(true);const auto& row=r.at("cases").at(1);
            ic(copies==2 && row.at("snapshot").at("image").at("width")==2 && row.at("matching_events_in_phase")==2);
            ic(row.at("state")=="repeated_target_ambiguous" && row.at("unique_in_phase")==false && row.at("repeated_headers_compared")==false && row.at("conflict_absence_proven")==false);
        }
        {
            fixture f;named(f,incoming::target);reinterpret_cast<unsigned char*>(&f.image)[188]=2;
            const auto r=one(f,&capture::copy_leaf);const auto& row=r.at("cases").at(1);
            ic(r.at("refused")==true && row.at("state")=="target_matched_sample_refused" && row.at("snapshot").at("image").is_null());
            ic(row.at("snapshot").at("header_copies")==1 && row.at("snapshot").at("completed_header_bytes")==264);
        }
        {
            fixture f;named(f,incoming::target);bool header_seen=false;
            const auto r=one(f,[&](void* t,const void* s,std::size_t n){if(n==264){header_seen=true;return false;}return capture::copy_leaf(t,s,n);});
            const auto& snapshot=r.at("cases").at(1).at("snapshot");
            ic(header_seen && snapshot.at("copy_fault")==true && snapshot.at("completed_header_bytes").is_null() && snapshot.at("image").is_null());
        }
        {
            fixture f;named(f,incoming::target);unsigned copies=0;
            const auto r=one(f,[&](void* t,const void* s,std::size_t n){if(n==264 && ++copies==2)++f.image.width;return capture::copy_leaf(t,s,n);});
            ic(r.at("cases").at(1).at("snapshot").at("header_copies")==2 && r.at("cases").at(1).at("snapshot").at("image").is_null());
        }
        {
            fixture f;named(f,incoming::target);incoming::collector c;c.arm(arguments(),true);
            for(unsigned i=0;i<=incoming::case_count_limit;++i)c.observe(t7::ASSET_TYPE_IMAGE,image_header(f),[&](const void* p,std::size_t n){f.readable(p,n);},[&](const void* p){return memory(p,true);},&capture::copy_leaf);
            c.begin_map();const auto r=c.finish(true);
            ic(r.at("refused")==true && r.at("cap_refused")==true && r.at("window_complete")==false && r.at("ordinary_name_events")==17);
        }
        {
            fixture f;named(f,"x");incoming::collector c;c.arm(arguments(),true);
            for(unsigned i=0;i<=incoming::callback_limit;++i)c.observe(t7::ASSET_TYPE_IMAGE,image_header(f),[&](const void* p,std::size_t n){f.readable(p,n);},[&](const void* p){return memory(p,true);},&capture::copy_leaf);
            c.begin_map();const auto r=c.finish(true);
            ic(r.at("cap_refused")==true && r.at("image_callbacks")==incoming::callback_limit+1 && r.at("ordinary_absence_scope")=="partial_or_refused_callback_window");
        }
        {
            incoming::collector c;c.arm(arguments(),true);const auto r=c.finish(false);
            ic(r.at("refused")==true && r.at("reason")=="map_load_not_complete" && r.at("map_complete")==false);
        }
        if(incoming_checks!=48)throw std::runtime_error("Unexpected authored incoming check count");
        std::cout<<"IW7_T7_INCOMING_IMAGE_CHECKS=48\n";return 0;
    }
    catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
