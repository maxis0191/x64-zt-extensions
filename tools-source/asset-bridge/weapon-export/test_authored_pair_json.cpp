// This real-preflight composition is AUTHORED, NOT COMPILED/LINKED/EXECUTED.
// J7 qualifies its older exact Source only. A new admitted native GO is required.
// No fake parser, DB/SL/filesystem stub, builder, captured input or game entry.
#include "weapon_pair_json_core.hpp"
#include "native_pair_session.hpp"
#include "native_pair_owned_input.hpp"
#include "native_pair_bodies.hpp"
#include "native_neutral_dependencies.hpp"
#include <algorithm>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string_view>

namespace authored_pair_fixture
{
    using namespace zonetool::iw7;
    namespace pq = zonetool::iw7::pair_json;
    namespace nd = zonetool::iw7::neutral_dependencies;
    namespace input = player_pair_input;
    using Arena = zonetool::zone_memory;
    using Report = zonetool::checked_memory_report;
    using Release = zonetool::checked_memory_release;
    using Failure = zonetool::checked_memory_failure;
    using Pin = input::Pin;
    using Inputs = input::Inputs;
    using Pins = input::Pins;
    struct ExpectedReference { int type; std::string_view name; bool owned; };
    struct ExpectedEdge { size_t reference; nd::Owner owner; std::string_view path; };
    struct AuthoredCase
    {
        const char* label;
        Inputs original;
        Pins trusted_source_pins;
        size_t capacity, weapondef_offset, attachment_offset;
        std::array<ExpectedReference, 4> references;
        std::array<ExpectedEdge, 4> edges;
        size_t occurrences;
    };
}
#include "authored_pair_json_cases.hpp"

namespace authored_pair_fixture
{
    void need(bool value) { if (!value) throw std::runtime_error("Authored real-core witness refused"); }
    using PinError = input::PinError;
    using input::detail::sha256;
    // The finite fixture alone selects parse cases; generic byte ownership
    // cannot turn caller-supplied pins into PR216/native eligibility.
    void require_approved_source(const AuthoredCase& source)
    {
        for (const auto& approved : approved_cases) if (&source == &approved) return;
        throw PinError();
    }
    // Entry intervals only; reaching a phase never means its parser succeeded.
    enum class ParsePhase : unsigned { pair_construction, weapon_parse, attachment_parse, post_parse };
    struct Stats : input::Counters
    {
        // Constructor hashes and explicit core DOM reads only; the real
        // preflight performs additional hashing/JSON work outside these counters.
        unsigned decodes{}, arenas{}, weapon_parses{}, attachment_parses{}, publications{};
        ParsePhase phase = ParsePhase::pair_construction;
    };
    // Keep the raw owner and decoded JSON together for the whole OwnedPair.
    struct Buffers
    {
        input::OwnedInput raw;
        pq::ordered_json weapon, attachment;
        Buffers(const Inputs& incoming, const Pins& trusted, Stats& stats)
            : raw(incoming, trusted, stats)
        {
            iw7::neutral::player_pair_bodies::validate_owned_pair_bodies(raw);
            const auto report=pq::ordered_json::parse(raw.bytes(input::Role::report));++stats.decodes;
            for(const char* flag:{"bo3_assets_authenticated","external_name_driven_gameplay_verified","native_parser_verified","ff_built","roundtrip_verified","runtime_abi_verified","lifetime_verified","weapon_granted","projectile_damage_verified","physics_qualified","retail_pap_transaction_verified","gameplay_accepted","ready"}) need(report.at(flag).is_boolean()&&!report.at(flag).get<bool>());
            weapon=pq::ordered_json::parse(raw.bytes(input::Role::weapon));++stats.decodes;
            attachment=pq::ordered_json::parse(raw.bytes(input::Role::attachment));++stats.decodes;
        }
    };
    struct ParserMaps { pq::ScriptStrings strings; };
    using NoFileRoute=std::false_type; // No FILE acquisition, capture or fake seal.
    enum class Mode { normal, preseed_maps, second_parse_error, bypass_core };
    struct Factory
    {
        const AuthoredCase& source;
        Report& report;
        Stats& stats;
        std::unique_ptr<Buffers> pending;
        Buffers* raw_ref{};
        Arena* memory{};
        ParserMaps *weapon_map{}, *attachment_map{};
        size_t capacity;
        Factory(const AuthoredCase& s,const Inputs& incoming,Report& r,Stats& t,size_t cap)
            :source(s),report(r),stats(t),pending(std::make_unique<Buffers>(incoming,s.trusted_source_pins,t)),capacity(cap)
        {raw_ref=pending.get();}
        std::unique_ptr<Pins> guards(){return std::make_unique<Pins>(source.trusted_source_pins);}
        std::unique_ptr<Buffers> raw(){return std::move(pending);}
        std::unique_ptr<NoFileRoute> route(){return std::make_unique<NoFileRoute>();}
        std::unique_ptr<Arena> arena()
        {
            ++stats.arenas;
            auto value=std::make_unique<Arena>(zonetool::checked_memory_tag{},capacity,report);
            need(reinterpret_cast<std::uintptr_t>(report.original_pool())%alignof(WeaponDef)==0);
            memory=value.get();return value;
        }
        std::unique_ptr<ParserMaps> weapon(){auto v=std::make_unique<ParserMaps>();weapon_map=v.get();return v;}
        std::unique_ptr<ParserMaps> attachment(){auto v=std::make_unique<ParserMaps>();attachment_map=v.get();return v;}
        static bool copy(void* out,const void* in,size_t count,void* context)
        {
            const auto& f=*static_cast<Factory*>(context);
            const auto base=reinterpret_cast<std::uintptr_t>(f.report.original_pool()), at=reinterpret_cast<std::uintptr_t>(in);
            if(!f.report.bound()||f.report.release()!=Release::not_attempted||at<base||at-base>f.capacity||count>f.capacity-(at-base)) return false;
            std::memcpy(out,in,count);return true;
        }
    };
    using Pair=player_pair_session::OwnedPair<Pins,Buffers,NoFileRoute,Arena,ParserMaps,ParserMaps,WeaponCompleteDef,WeaponAttachment,nd::Inventory>;
    struct Result { std::vector<nd::Reference> references;std::vector<nd::Edge> edges;size_t occurrences{}; };
    bool oracle(const AuthoredCase& expected,const Result& actual)
    {
        if(actual.references.size()!=expected.references.size()||actual.edges.size()!=expected.edges.size()||actual.occurrences!=expected.occurrences) return false;
        for(size_t i=0;i<actual.references.size();++i){const auto& a=actual.references[i];const auto& e=expected.references[i];if(a.type!=e.type||a.name!=e.name||a.owned!=e.owned)return false;}
        for(size_t i=0;i<actual.edges.size();++i){const auto& a=actual.edges[i];const auto& e=expected.edges[i];if(a.reference!=e.reference||a.owner!=e.owner||a.path!=e.path)return false;}
        return true;
    }
    Result execute(const AuthoredCase& source,const Inputs& incoming,Report& report,Stats& stats,Mode mode=Mode::normal,size_t capacity=0)
    {
        require_approved_source(source); // Before copies, decoding or arena.
        Factory factory(source,incoming,report,stats,capacity?capacity:source.capacity);
        const auto* const original_raw=&factory.raw_ref->raw;
        Result result;
        {
            stats.phase=ParsePhase::pair_construction;
            Pair pair(factory);
            need(!factory.pending && &factory.raw_ref->raw == original_raw);
            try
            {
                need(factory.weapon_map!=factory.attachment_map);
                const auto base=reinterpret_cast<std::uintptr_t>(report.original_pool());
                if(mode==Mode::preseed_maps)
                {
                    factory.weapon_map->strings.emplace_back(reinterpret_cast<scr_string_t*>(base+source.weapondef_offset+offsetof(WeaponDef,knifeAttachTagOverride)),"first_weapon");
                    factory.attachment_map->strings.emplace_back(reinterpret_cast<scr_string_t*>(base+source.attachment_offset+offsetof(WeaponAttachment,internalName)),"first_attachment");
                }
                WeaponCompleteDef* weapon=nullptr;
                if(mode!=Mode::bypass_core){stats.phase=ParsePhase::weapon_parse;++stats.weapon_parses;weapon=pq::parse_weapon_json(factory.raw_ref->weapon,factory.memory,factory.weapon_map->strings);}
                if(mode==Mode::second_parse_error) factory.raw_ref->attachment["papAttachment"]="authored_negative_type_fault"; // Explicit non-null type fault after trusted-byte checks.
                stats.phase=ParsePhase::attachment_parse;
                ++stats.attachment_parses;
                auto* attachment=pq::parse_attachment_json(factory.raw_ref->attachment,factory.memory,factory.attachment_map->strings);
                stats.phase=ParsePhase::post_parse;
                pair.retain_returned_roots(weapon,attachment);
                need(reinterpret_cast<std::uintptr_t>(weapon)%alignof(WeaponCompleteDef)==0&&reinterpret_cast<std::uintptr_t>(attachment)%alignof(WeaponAttachment)==0);
                need(reinterpret_cast<std::uintptr_t>(weapon->weapDef)==base+source.weapondef_offset&&reinterpret_cast<std::uintptr_t>(attachment)==base+source.attachment_offset);
                need(weapon->weapDef->weapType==WEAPTYPE_BULLET&&attachment->weaponType==WEAPTYPE_NONE&&attachment->papAttachment);
                need(!factory.weapon_map->strings.empty()&&!factory.attachment_map->strings.empty());
                for(const auto& entry:factory.weapon_map->strings)need(*entry.first==scr_string_t(0));
                for(const auto& entry:factory.attachment_map->strings)need(*entry.first==scr_string_t(0));
                if(mode==Mode::preseed_maps){need(std::string_view(factory.weapon_map->strings.front().second)=="first_weapon");need(std::string_view(factory.attachment_map->strings.front().second)=="first_attachment");}
                auto inventory=std::make_unique<nd::Inventory>(Factory::copy,&factory);
                need(nd::inventory_pair(const_cast<WeaponCompleteDef*>(pair.roots().weapon),const_cast<WeaponAttachment*>(pair.roots().attachment),*inventory));
                need(inventory->good()&&inventory->frozen()&&!inventory->policy_blocked());
                result={inventory->references(),inventory->edges(),inventory->occurrences()};
                need(oracle(source,result));
                pair.retain_copied_inventory(std::move(inventory));++stats.publications;
            }
            catch(...)
            {
                // Preserve the original exception; explicit free plus later
                // arena destruction must still record one attempt, no retry.
                const auto primary=std::current_exception();factory.memory->free();std::rethrow_exception(primary);
            }
        }
        return result; // Only copied std::string inventory survives its arena.
    }
    void released_once(const Report& report)
    {need(report.release_attempts()==1&&report.release()==Release::succeeded&&report.release_result_available()&&report.release_result()&&!report.cleanup_exception());}
    void hash_vectors()
    {
        need(sha256("")=="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
        need(sha256("abc")=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
        need(sha256(std::string(1000000,'a'))=="cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
    }
    void real_pair_variants()
    {
        Result golden;
        for(size_t i=0;i<3;++i)
        {
            Report report;Stats stats;
            Result actual;
            try { actual=execute(approved_cases[i],approved_cases[i].original,report,stats); }
            catch(const zonetool::checked_memory_error& error)
            {
                const auto& failure=report.allocation_failure();
                if(failure.available)
                {
                    char requested[21]="NA";
                    if(failure.requested_bytes_valid) std::snprintf(requested,sizeof(requested),"%zu",failure.requested_bytes);
                    std::fprintf(stderr,
                        "FAIL authored_pair label=%.16s phase=%u snapshot=1 ordinal=%zu unit=%zu count=%zu bytes=%.20s "
                        "type_align=%zu align_api=none used=%zu cap=%zu padding=NA source_pad=0 reason_enum=%d primary_enum=%d "
                        "releases=%u copies=%u hashes=%u decodes=%u arenas=%u w_calls=%u a_calls=%u pubs=%u\n",
                        approved_cases[i].label, static_cast<unsigned>(stats.phase), failure.ordinal,
                        failure.element_bytes, failure.count, requested, failure.requested_type_alignment,
                        failure.used_before, failure.capacity, static_cast<int>(error.reason()), static_cast<int>(report.primary()),
                        report.release_attempts(), stats.copies, stats.hashes, stats.decodes, stats.arenas,
                        stats.weapon_parses, stats.attachment_parses, stats.publications);
                }
                else
                {
                    std::fprintf(stderr,
                        "FAIL authored_pair label=%.16s phase=%u snapshot=0 ordinal=NA unit=NA count=NA bytes=NA "
                        "type_align=NA align_api=none used=NA report_cap=%zu padding=NA source_pad=0 reason_enum=%d primary_enum=%d "
                        "releases=%u copies=%u hashes=%u decodes=%u arenas=%u w_calls=%u a_calls=%u pubs=%u\n",
                        approved_cases[i].label, static_cast<unsigned>(stats.phase), report.capacity(),
                        static_cast<int>(error.reason()), static_cast<int>(report.primary()), report.release_attempts(),
                        stats.copies, stats.hashes, stats.decodes, stats.arenas, stats.weapon_parses, stats.attachment_parses, stats.publications);
                }
                std::fprintf(stderr,
                    "FAIL compiled_sizes wc=%zu/%zu wd=%zu/%zu wa=%zu/%zu ptr_wa=%zu ptr_ret=%zu ptr_str=%zu "
                    "char=%zu fx_align=%zu ret_align=%zu vec2=%zu\n",
                    sizeof(WeaponCompleteDef),alignof(WeaponCompleteDef),sizeof(WeaponDef),alignof(WeaponDef),
                    sizeof(WeaponAttachment),alignof(WeaponAttachment),sizeof(WeaponAttachment*),sizeof(ReticleDef*),
                    sizeof(const char*),sizeof(char),alignof(FxEffectDef),alignof(ReticleDef),sizeof(vec2_t));
                throw; // Preserve this same unexpected refusal after diagnostics.
            }
            need(stats.hashes==4&&stats.decodes==3&&stats.arenas==1&&stats.weapon_parses==1&&stats.attachment_parses==1&&stats.publications==1);
            released_once(report);need(oracle(approved_cases[i],actual));
            if(i==0)golden=actual;else need(!oracle(approved_cases[i],golden)); // A prefab golden result cannot satisfy mutants.
        }
    }
    void same_length_old_pin_refuses()
    {
        Report report;Stats stats;bool refused=false;
        try{execute(approved_cases[0],approved_cases[1].original,report,stats);}catch(const PinError&){refused=true;}
        need(refused&&stats.decodes==0&&stats.arenas==0&&stats.publications==0&&!report.bound());
    }
    void malformed_inputs_refuse_before_decode()
    {
        for(unsigned kind=0;kind<3;++kind)
        {
            const auto& original=approved_cases[0];std::string bad(original.original[1]);
            if(kind==0)bad[0]=static_cast<char>(0xff);
            if(kind==1)bad.insert(1,"\"szInternalName\":\"duplicate\",");
            if(kind==2){const auto at=bad.find("\"weapDef\"");need(at!=std::string::npos);bad.replace(at,9,"\"missing\"");}
            Inputs input=original.original;input[1]=bad;Report report;Stats stats;bool refused=false;
            try{execute(original,input,report,stats);}catch(const PinError&){refused=true;}
            need(refused&&stats.decodes==0&&stats.arenas==0&&stats.publications==0&&!report.bound());
        }
        // Fresh caller pins qualify only these direct ordinary Buffers negatives,
        // never a fourth AuthoredCase address or a native parse through execute().
        for(const bool report_mismatch:{true,false})
        {
            const auto& source=approved_cases[0];
            std::array<std::string,4> changed,hashes;
            for(size_t i=0;i<4;++i)changed[i]=source.original[i];
            changed[1]="not-json-before-core-dom";
            auto metadata=pq::ordered_json::parse(changed[0]);
            for(auto& row:metadata["files"]) if(row["path"]=="weapons/sdk_shredder_clone_zm.json")
            {
                row["bytes"]=changed[1].size();
                row["sha256"]=report_mismatch?std::string(64,'0'):sha256(changed[1]);
            }
            changed[0]=metadata.dump();Inputs incoming;Pins trusted;
            for(size_t i=0;i<4;++i)
            {
                hashes[i]=sha256(changed[i]);incoming[i]=changed[i];
                trusted[i]={changed[i].size(),hashes[i]};
            }
            Report report;Stats stats;bool refused=false;
            try{Buffers buffers(incoming,trusted,stats);static_cast<void>(buffers);}
            catch(const player_pair_report::ReportError& error)
            {
                need(report_mismatch&&std::string_view(error.what())=="Report row does not bind SAME owned role");
                refused=true;
            }
            catch(const iw7::neutral::player_pair_bodies::detail::BodyError& error)
            {
                need(!report_mismatch&&std::string_view(error.what()).find("weapon:")==0);
                refused=true;
            }
            need(refused&&stats.copies==4&&stats.hashes==4&&stats.decodes==0&&stats.arenas==0&&
                stats.weapon_parses==0&&stats.attachment_parses==0&&stats.publications==0&&!report.bound());
            // Zero decodes means no explicit core DOM read, not no validator work.
        }
    }
    void map_lifetime_and_first_pointer_wins()
    {Report report;Stats stats;const auto& c=approved_cases[0];const auto r=execute(c,c.original,report,stats,Mode::preseed_maps);released_once(report);need(oracle(c,r));}
    void capacity_failure_unwinds()
    {
        Report report;Stats stats;bool refused=false;
        try{execute(approved_cases[0],approved_cases[0].original,report,stats,Mode::normal,1);}catch(const zonetool::checked_memory_error& e){refused=e.reason()==Failure::capacity;}
        need(refused&&stats.publications==0&&stats.attachment_parses==0&&report.primary()==Failure::capacity);released_once(report);
    }
    void real_second_parse_error_keeps_primary()
    {
        Report report;Stats stats;bool refused=false;
        try{execute(approved_cases[0],approved_cases[0].original,report,stats,Mode::second_parse_error);}catch(const pq::ordered_json::type_error&){refused=true;}
        need(refused&&stats.weapon_parses==1&&stats.attachment_parses==1&&stats.publications==0&&report.primary()==Failure::none);released_once(report);
    }
    void bypass_real_core_refuses()
    {
        // Author a fourth consistent raw/pin set solely to prove refusal.
        // Leading JSON whitespace preserves the body; its report pins are updated.
        auto fourth=approved_cases[0];
        std::string weapon=" " + std::string(fourth.original[1]);
        const auto weapon_hash=sha256(weapon);
        auto report_json=pq::ordered_json::parse(fourth.original[0]);
        for(auto& row:report_json["files"]) if(row["path"]=="weapons/sdk_shredder_clone_zm.json")
        {row["bytes"]=weapon.size();row["sha256"]=weapon_hash;}
        const auto report_raw=report_json.dump();const auto report_hash=sha256(report_raw);
        fourth.original[0]=report_raw;fourth.original[1]=weapon;
        fourth.trusted_source_pins[0]={report_raw.size(),report_hash};
        fourth.trusted_source_pins[1]={weapon.size(),weapon_hash};
        Report fourth_report;Stats fourth_stats;bool fourth_refused=false;
        try{execute(fourth,fourth.original,fourth_report,fourth_stats);}catch(const PinError&){fourth_refused=true;}
        need(fourth_refused&&fourth_stats.copies==0&&fourth_stats.hashes==0&&fourth_stats.decodes==0&&
            fourth_stats.arenas==0&&fourth_stats.publications==0&&!fourth_report.bound());
        Report report;Stats stats;bool refused=false;
        try{execute(approved_cases[0],approved_cases[0].original,report,stats,Mode::bypass_core);}catch(const std::logic_error&){refused=true;}
        need(refused&&stats.weapon_parses==0&&stats.publications==0);released_once(report);
    }
}
int main()
{
    using namespace authored_pair_fixture;
    struct Case{const char* name;void(*run)();};
    const Case tests[]={{"sha256_known_vectors",hash_vectors},{"real_pair_and_approved_mutants",real_pair_variants},
        {"same_length_mutant_old_source_pin_refuses",same_length_old_pin_refuses},{"malformed_raw_old_pins_refuse_before_decode",malformed_inputs_refuse_before_decode},
        {"real_maps_outlive_roots_first_pointer_wins",map_lifetime_and_first_pointer_wins},{"checked_capacity_failure_unwinds_once",capacity_failure_unwinds},
        {"real_second_parser_failure_keeps_primary",real_second_parse_error_keeps_primary},{"bypassed_core_cannot_publish_inventory",bypass_real_core_refuses}};
    try{for(const auto& c:tests){c.run();std::cout<<"PASS "<<c.name<<'\n';}std::cout<<"IW7_AUTHORED_PAIR_REAL_CORE_FIXTURE=8\n";return 0;}
    catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
