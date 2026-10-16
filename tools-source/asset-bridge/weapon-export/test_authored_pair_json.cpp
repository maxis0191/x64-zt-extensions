// AUTHORED, NOT COMPILED/LINKED/EXECUTED. A separate admitted native GO is required.
// No fake parser, DB/SL/filesystem stub, builder, captured input or game entry.
#include "weapon_pair_json_core.hpp"
#include "native_pair_session.hpp"
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
    using Arena = zonetool::zone_memory;
    using Report = zonetool::checked_memory_report;
    using Release = zonetool::checked_memory_release;
    using Failure = zonetool::checked_memory_failure;
    struct Pin { size_t bytes; std::string_view sha256; };
    using Inputs = std::array<std::string_view, 4>;
    using Pins = std::array<Pin, 4>;
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
    struct PinError : std::runtime_error { PinError() : std::runtime_error("Private copy Source pin differs") {} };
    // Fixture-local SHA256, no extra SDK/crypto/engine dependency. Actual C++
    // known-vector checks below must pass before trusting this implementation.
    std::string sha256(std::string_view input)
    {
        static constexpr std::uint32_t k[] = {
            0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
            0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
            0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
            0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
            0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
            0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
            0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
            0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
        need(input.size() <= 2097152);
        std::vector<std::uint8_t> bytes(input.begin(), input.end());
        const auto bits = static_cast<std::uint64_t>(bytes.size()) * 8;
        bytes.push_back(0x80);
        while (bytes.size() % 64 != 56) bytes.push_back(0);
        for (unsigned i = 0; i < 8; ++i) bytes.push_back(static_cast<std::uint8_t>(bits >> (56 - 8*i)));
        std::array<std::uint32_t,8> h{0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
        const auto rotr=[](std::uint32_t n,unsigned count){return (n>>count)|(n<<(32-count));};
        for(size_t at=0;at<bytes.size();at+=64)
        {
            std::uint32_t w[64]{};
            for(unsigned i=0;i<16;++i) for(unsigned j=0;j<4;++j) w[i]=(w[i]<<8)|bytes[at+4*i+j];
            for(unsigned i=16;i<64;++i) w[i]=w[i-16]+(rotr(w[i-15],7)^rotr(w[i-15],18)^(w[i-15]>>3))+w[i-7]+(rotr(w[i-2],17)^rotr(w[i-2],19)^(w[i-2]>>10));
            auto a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],v=h[7];
            for(unsigned i=0;i<64;++i)
            {
                const auto t1=v+(rotr(e,6)^rotr(e,11)^rotr(e,25))+((e&f)^((~e)&g))+k[i]+w[i];
                const auto t2=(rotr(a,2)^rotr(a,13)^rotr(a,22))+((a&b)^(a&c)^(b&c));
                v=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
            }
            h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=v;
        }
        static constexpr char digits[]="0123456789abcdef";
        std::string result;result.reserve(64);
        for(auto value:h) for(unsigned i=0;i<8;++i) result.push_back(digits[(value>>(28-4*i))&15]);
        return result;
    }
    // Entry intervals only; reaching a phase never means its parser succeeded.
    enum class ParsePhase : unsigned { pair_construction, weapon_parse, attachment_parse, post_parse };
    struct Stats
    {
        unsigned copies{}, hashes{}, decodes{}, arenas{}, weapon_parses{}, attachment_parses{}, publications{};
        ParsePhase phase = ParsePhase::pair_construction;
    };
    // Ordinary private byte storage, not a transferable validation capability.
    struct Buffers
    {
        std::array<std::string,4> bytes;
        pq::ordered_json weapon, attachment;
        Buffers(const Inputs& incoming, const Pins& trusted, Stats& stats)
        {
            const size_t caps[]{65536,2097152,2097152,66};
            for(size_t i=0;i<4;++i)
            {
                if(incoming[i].empty()||incoming[i].size()>caps[i]||trusted[i].bytes>caps[i]) throw PinError();
                bytes[i].assign(incoming[i]);++stats.copies;
            }
            // All four PRIVATE copies are checked before any JSON decode/arena.
            for(size_t i=0;i<4;++i)
            {
                if(trusted[i].sha256.size()!=64||!std::all_of(trusted[i].sha256.begin(),trusted[i].sha256.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');})) throw PinError();
                ++stats.hashes;
                if(bytes[i].size()!=trusted[i].bytes||sha256(bytes[i])!=trusted[i].sha256) throw PinError();
            }
            const auto report=pq::ordered_json::parse(bytes[0]);++stats.decodes;
            for(const char* flag:{"bo3_assets_authenticated","external_name_driven_gameplay_verified","native_parser_verified","ff_built","roundtrip_verified","runtime_abi_verified","lifetime_verified","weapon_granted","projectile_damage_verified","physics_qualified","retail_pap_transaction_verified","gameplay_accepted","ready"}) need(report.at(flag).is_boolean()&&!report.at(flag).get<bool>());
            weapon=pq::ordered_json::parse(bytes[1]);++stats.decodes;
            attachment=pq::ordered_json::parse(bytes[2]);++stats.decodes;
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
        Factory factory(source,incoming,report,stats,capacity?capacity:source.capacity);
        Result result;
        {
            stats.phase=ParsePhase::pair_construction;
            Pair pair(factory);
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
