// NativeComponents additions are AUTHORED, NOT COMPILED/LINKED/EXECUTED.
// J16/J18 qualify their older exact Sources only. A new native GO is required.
// No fake parser, DB/SL/filesystem stub, builder, captured input or game entry.
#include "weapon_pair_json_core.hpp"
#include "native_pair_session.hpp"
#include "native_pair_owned_input.hpp"
#include "native_pair_bodies.hpp"
#include "native_pair_native_components.hpp"
#include "native_neutral_dependencies.hpp"
#include <algorithm>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include <cstdlib>
#include <cstdio>
#include <new>

// Fixture-local ordinary-new observation only; never a production injection API.
namespace native_component_fault
{
    struct Allocation { void* pointer; size_t bytes; bool arena_bound; };
    enum class RefusalCause : unsigned { none, requested, observer_limit, malloc_null };
    struct RefusalEvent { size_t ordinal; RefusalCause cause; size_t bytes; bool arena_bound; };
    inline Allocation allocations[65536]{};
    inline void* deletions[65536]{};
    inline size_t calls{}, deletes{}, fail_at{}, failed_bytes{}, refusal_count{};
    inline RefusalEvent first_refusal{};
    inline bool active{}, failed_bound{};
    inline const zonetool::checked_memory_report* report{};
    inline const std::bad_alloc* primary{};
    void begin(const zonetool::checked_memory_report& value, size_t failure = 0) noexcept
    { calls=deletes=failed_bytes=refusal_count=0;first_refusal={};failed_bound=false;fail_at=failure;report=&value;primary=nullptr;active=true; }
    struct Watch final
    {
        explicit Watch(const zonetool::checked_memory_report& value,size_t failure=0) noexcept{begin(value,failure);}
        ~Watch() noexcept{active=false;primary=nullptr;report=nullptr;}
    };
    [[noreturn]] void refuse_active(size_t ordinal,RefusalCause cause,size_t bytes)
    {
        const bool first=++refusal_count==1;
        if(first)
        {
            // Only begin() resets this event; later refusals cannot replace it.
            first_refusal={ordinal,cause,bytes,report->bound()};
            failed_bytes=first_refusal.bytes;failed_bound=first_refusal.arena_bound;
        }
        try{throw std::bad_alloc();}
        catch(const std::bad_alloc& error){if(first)primary=&error;throw;}
    }
    void* allocate(size_t bytes)
    {
        const auto ordinal=active?++calls:0;
        if(active&&(ordinal>65536||ordinal==fail_at))
        {
            refuse_active(ordinal,ordinal>65536?RefusalCause::observer_limit:RefusalCause::requested,bytes);
        }
        void* pointer=std::malloc(bytes?bytes:1);
        if(!pointer)
        {
            if(active)refuse_active(ordinal,RefusalCause::malloc_null,bytes);
            throw std::bad_alloc();
        }
        if(active)allocations[ordinal-1]={pointer,bytes,report->bound()};
        return pointer;
    }
    void deallocate(void* pointer) noexcept
    {
        if(active&&pointer&&deletes<65536)deletions[deletes++]=pointer;
        std::free(pointer);
    }
}
void* operator new(size_t bytes){return native_component_fault::allocate(bytes);}
void* operator new[](size_t bytes){return ::operator new(bytes);}
void operator delete(void* pointer) noexcept{native_component_fault::deallocate(pointer);}
void operator delete[](void* pointer) noexcept{::operator delete(pointer);}
void operator delete(void* pointer,size_t) noexcept{::operator delete(pointer);}
void operator delete[](void* pointer,size_t) noexcept{::operator delete(pointer);}

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
    namespace owned = player_pair_owned_session;
    using Native = owned::NativeComponents;
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
    // Group-eight failure evidence only. Context borrows a live report while
    // assertions run; the failure POD copies scalars before any unwind.
    struct NativeDiagnosticContext
    {
        const char *block, *assertion;
        const Report* report;
        size_t phase, observed_bytes, expected_bytes;
        unsigned destroyed;
        bool refused, order_equal;
    };
    struct NativeDiagnosticFailure
    {
        const char *block, *assertion, *helper;
        size_t phase, calls, deletes, fail_at, failed_bytes, refusal_count, refusal_ordinal, release_attempts, observed_bytes, expected_bytes,
            pair_at, weapon_at, wrapper_at;
        unsigned destroyed, release, refusal_cause;
        bool available, failed_bound, refused, report_present, bound, release_available,
            release_result, cleanup_exception, order_equal;
    };
    NativeDiagnosticContext native_diagnostic_context{};
    NativeDiagnosticFailure native_diagnostic_failure{};
    size_t native_diagnostic_phase_ordinals[3]{};
    bool native_diagnostic_active{};
    struct NativeDiagnosticScope final
    {
        NativeDiagnosticScope() noexcept
        {native_diagnostic_context={};native_diagnostic_failure={};for(auto& ordinal:native_diagnostic_phase_ordinals)ordinal=0;native_diagnostic_active=true;}
        ~NativeDiagnosticScope() noexcept{native_diagnostic_active=false;native_diagnostic_context={};}
    };
    void native_diagnostic_step(const char* block,const char* assertion,size_t phase,const Report* report=nullptr,
        unsigned destroyed=0,bool refused=false,bool order_equal=false,size_t observed_bytes=0,size_t expected_bytes=0) noexcept
    {native_diagnostic_context={block,assertion,report,phase,observed_bytes,expected_bytes,destroyed,refused,order_equal};}
    void capture_native_diagnostic(const char* assertion=nullptr,const char* helper=nullptr) noexcept
    {
        if(!native_diagnostic_active)return;
        const auto& context=native_diagnostic_context;
        auto& failure=native_diagnostic_failure;
        failure={};failure.available=true;failure.block=context.block;
        failure.assertion=assertion?assertion:context.assertion;failure.helper=helper;
        failure.phase=context.phase;failure.destroyed=context.destroyed;failure.refused=context.refused;
        failure.order_equal=context.order_equal;failure.observed_bytes=context.observed_bytes;failure.expected_bytes=context.expected_bytes;
        failure.calls=native_component_fault::calls;failure.deletes=native_component_fault::deletes;failure.fail_at=native_component_fault::fail_at;
        failure.failed_bytes=native_component_fault::failed_bytes;failure.failed_bound=native_component_fault::failed_bound;
        failure.refusal_count=native_component_fault::refusal_count;failure.refusal_ordinal=native_component_fault::first_refusal.ordinal;
        failure.refusal_cause=static_cast<unsigned>(native_component_fault::first_refusal.cause);
        failure.pair_at=native_diagnostic_phase_ordinals[0];failure.weapon_at=native_diagnostic_phase_ordinals[1];
        failure.wrapper_at=native_diagnostic_phase_ordinals[2];
        if(context.report)
        {
            failure.report_present=true;failure.bound=context.report->bound();
            failure.release_attempts=context.report->release_attempts();failure.release=static_cast<unsigned>(context.report->release());
            failure.release_available=context.report->release_result_available();
            failure.release_result=failure.release_available&&context.report->release_result();
            failure.cleanup_exception=bool(context.report->cleanup_exception());
        }
    }
    void emit_native_diagnostic() noexcept
    {
        const auto& failure=native_diagnostic_failure;if(!failure.available)return;
        // Captured assertion-time values, not a claim about later cleanup.
        char line[896];
        const int count=std::snprintf(line,sizeof(line),
            "G8_FAILURE block=%.32s assertion=%.48s helper=%.20s phase=%zu calls=%zu deletes=%zu fail_at=%zu failed_bytes=%zu failed_bound=%u refusal_count=%zu refusal_ordinal=%zu refusal_cause=%u refused=%u destroyed=%u report=%u bound=%u releases=%zu release=%u release_available=%u release_result=%u cleanup_exception=%u order_equal=%u observed_bytes=%zu expected_bytes=%zu pair_at=%zu weapon_at=%zu wrapper_at=%zu\n",
            failure.block?failure.block:"NA",failure.assertion?failure.assertion:"NA",failure.helper?failure.helper:"NA",
            failure.phase,failure.calls,failure.deletes,failure.fail_at,failure.failed_bytes,unsigned(failure.failed_bound),
            failure.refusal_count,failure.refusal_ordinal,failure.refusal_cause,unsigned(failure.refused),
            failure.destroyed,unsigned(failure.report_present),unsigned(failure.bound),failure.release_attempts,failure.release,
            unsigned(failure.release_available),unsigned(failure.release_result),unsigned(failure.cleanup_exception),unsigned(failure.order_equal),
            failure.observed_bytes,failure.expected_bytes,failure.pair_at,failure.weapon_at,failure.wrapper_at);
        if(count>0)std::fwrite(line,1,std::min(static_cast<size_t>(count),sizeof(line)-1),stderr);
    }
    void need(bool value,const char* assertion=nullptr)
    {if(!value){capture_native_diagnostic(assertion);throw std::runtime_error("Authored real-core witness refused");}}
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
            for(const char* flag:{"bo3_assets_authenticated","external_name_driven_gameplay_verified","native_parser_verified","ff_built","roundtrip_verified","runtime_abi_verified","lifetime_verified","weapon_granted","projectile_damage_verified","physics_qualified","retail_pap_transaction_verified","gameplay_accepted","ready"}) need(report.at(flag).is_boolean()&&!report.at(flag).get<bool>(),flag);
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
            need(reinterpret_cast<std::uintptr_t>(report.original_pool())%alignof(WeaponDef)==0,"execute.pool_alignment");
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
            bool absent=false;try{pair.roots();}catch(const std::logic_error&){absent=true;}need(absent,"execute.roots_absent");
            if(native_diagnostic_active)native_diagnostic_context.assertion="execute.same_raw";
            need(!factory.pending && &factory.raw_ref->raw == original_raw);
            try
            {
                need(factory.weapon_map!=factory.attachment_map,"execute.distinct_maps");
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
                bool duplicate=false;try{pair.retain_returned_roots(weapon,attachment);}catch(const std::logic_error&){duplicate=true;}need(duplicate);
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
    struct NativeGuards final
    {
        unsigned& destroyed;
        explicit NativeGuards(unsigned& value) noexcept:destroyed(value){}
        ~NativeGuards() noexcept{++destroyed;}
    };
    using NativeOwner=owned::TypedOwnedPair<NativeGuards,Native>;
    template<class T,class=void> struct exposes_completion:std::false_type{};
    template<class T> struct exposes_completion<T,std::void_t<decltype(
        std::declval<T&>().register_component_returns(std::declval<const typename T::Roots&>()))>>:std::true_type{};
    template<class T,class=void> struct exposes_rvalue_roots:std::false_type{};
    template<class T> struct exposes_rvalue_roots<T,std::void_t<decltype(std::declval<const T&&>().roots())>>:std::true_type{};
    static_assert(!std::is_constructible_v<Native,size_t,Report&>);
    static_assert(!std::is_constructible_v<Native::WeaponMap,const input::OwnedInput&,Arena&>);
    static_assert(!std::is_constructible_v<Native::AttachmentMap,const input::OwnedInput&,Arena&>);
    static_assert(!std::is_constructible_v<owned::detail::Transfer<NativeGuards,Native>,
        std::unique_ptr<owned::OwnedIngress<NativeGuards>>&&,Native&>);
    static_assert(!exposes_completion<NativeOwner>::value&&!exposes_rvalue_roots<NativeOwner>::value);
    static_assert(std::is_same_v<decltype(std::declval<const NativeOwner&>().roots()),const NativeOwner::Roots&>);
    static_assert(!noexcept(std::declval<const NativeOwner&>().roots()));
    struct NativeReader
    {
        const Report& report;
        static bool copy(void* out,const void* in,size_t count,void* context)
        {
            const auto& observation=static_cast<NativeReader*>(context)->report;
            const auto base=reinterpret_cast<std::uintptr_t>(observation.original_pool()),at=reinterpret_cast<std::uintptr_t>(in);
            if(!observation.bound()||observation.release()!=Release::not_attempted||at<base||
                at-base>observation.capacity()||count>observation.capacity()-(at-base))return false;
            std::memcpy(out,in,count);return true;
        }
    };
    std::unique_ptr<owned::OwnedIngress<NativeGuards>> native_ingress(const AuthoredCase& source,
        const Inputs& incoming,const Pins& pins,input::Counters& counters,unsigned& destroyed,NativeGuards** observer=nullptr)
    {
        require_approved_source(source); // SAME three original addresses, before any owner/copy.
        auto guards=std::make_unique<NativeGuards>(destroyed);
        if(observer)*observer=guards.get(); // Borrowed address for deletion observation only.
        return owned::copy_with_guards(std::move(guards),incoming,pins,counters);
    }
    size_t last_delete(const void* pointer,const char* label="last_delete")
    {
        for(size_t i=native_component_fault::deletes;i>0;--i)
            if(native_component_fault::deletions[i-1]==pointer)return i;
        capture_native_diagnostic(nullptr,label);
        throw std::runtime_error("Expected original owner deletion missing");
    }
    size_t allocation_of(const void* pointer,const char* label="allocation_of")
    {
        for(size_t i=native_component_fault::calls;i>0;--i)
            if(native_component_fault::allocations[i-1].pointer==pointer)return i;
        capture_native_diagnostic(nullptr,label);
        throw std::runtime_error("Expected original allocation missing");
    }
    void native_components_variants()
    {
        for(const auto& source:approved_cases)
        {
            Report report;input::Counters counters;unsigned destroyed=0;
            auto ingress=native_ingress(source,source.original,source.trusted_source_pins,counters,destroyed);
            const auto* raw=&ingress->input();
            auto owner=owned::make_in_memory_owned_pair(std::move(ingress),source.capacity,report);
            // The configuration-only builder is already dead here. Roots borrow
            // their owner; only the copied Inventory below can outlive that owner.
            need(!ingress && &owner->input()==raw&&counters.copies==4&&counters.hashes==4&&destroyed==0);
            const auto& roots=owner->roots();need(&roots==&owner->roots()&&roots.weapon&&roots.attachment);
            const auto base=reinterpret_cast<std::uintptr_t>(report.original_pool());
            need(reinterpret_cast<std::uintptr_t>(roots.weapon->weapDef)==base+source.weapondef_offset&&
                reinterpret_cast<std::uintptr_t>(roots.attachment)==base+source.attachment_offset);
            NativeReader reader{report};nd::Inventory inventory(NativeReader::copy,&reader);
            need(nd::inventory_pair(const_cast<WeaponCompleteDef*>(roots.weapon),
                const_cast<WeaponAttachment*>(roots.attachment),inventory));
            Result result{inventory.references(),inventory.edges(),inventory.occurrences()};
            need(inventory.good()&&inventory.frozen()&&oracle(source,result));
            owner.reset();need(destroyed==1);released_once(report);need(oracle(source,result));
        }
    }
    void native_preflight_refusals()
    {
        for(const bool report_mismatch:{true,false})
        {
            const auto& source=approved_cases[0];
            std::array<std::string,4> bytes,hashes;for(size_t i=0;i<4;++i)bytes[i]=source.original[i];
            bytes[1]="not-json-before-native-role-dom";
            auto metadata=pq::ordered_json::parse(bytes[0]);
            for(auto& row:metadata["files"])if(row["path"]=="weapons/sdk_shredder_clone_zm.json")
            {row["bytes"]=bytes[1].size();row["sha256"]=report_mismatch?std::string(64,'0'):sha256(bytes[1]);}
            bytes[0]=metadata.dump();Inputs incoming;Pins pins;
            for(size_t i=0;i<4;++i){hashes[i]=sha256(bytes[i]);incoming[i]=bytes[i];pins[i]={bytes[i].size(),hashes[i]};}
            Report report;input::Counters counters;unsigned destroyed=0;bool refused=false;
            auto ingress=native_ingress(source,incoming,pins,counters,destroyed);
            try{auto value=owned::make_in_memory_owned_pair(std::move(ingress),source.capacity,report);static_cast<void>(value);}
            catch(const player_pair_report::ReportError& error)
            {need(report_mismatch&&std::string_view(error.what())=="Report row does not bind SAME owned role");refused=true;}
            catch(const iw7::neutral::player_pair_bodies::detail::BodyError& error)
            {need(!report_mismatch&&std::string_view(error.what()).find("weapon:")==0);refused=true;}
            need(refused&&!ingress&&destroyed==1&&counters.copies==4&&counters.hashes==4&&!report.bound());
            // This observes no role arena. The real preflight has its own JSON
            // temporaries; it is not a zero-allocation or zero-decode operation.
        }
    }
    void native_second_role_capacity_failure()
    {
        const auto& source=approved_cases[0];Report report;input::Counters counters;unsigned destroyed=0;bool refused=false;
        auto ingress=native_ingress(source,source.original,source.trusted_source_pins,counters,destroyed);
        try{auto value=owned::make_in_memory_owned_pair(std::move(ingress),source.attachment_offset,report);static_cast<void>(value);}
        catch(const zonetool::checked_memory_error& error)
        {
            const auto& failure=report.allocation_failure();
            need(error.reason()==Failure::capacity&&failure.available&&failure.used_before==source.attachment_offset&&
                failure.element_bytes==sizeof(WeaponAttachment)&&failure.count==1&&report.primary()==Failure::capacity);
            refused=true; // The actual second core's root allocation, not a deep JSON error.
        }
        need(refused&&!ingress&&destroyed==1);released_once(report);
    }
    void native_storage_failures_and_order()
    {
        const auto& source=approved_cases[0];std::array<size_t,3> phases{};
        {
            Report report;input::Counters counters;unsigned destroyed=0;
            NativeGuards* guards=nullptr;
            auto ingress=native_ingress(source,source.original,source.trusted_source_pins,counters,destroyed,&guards);
            const auto* raw=&ingress->input();
            native_component_fault::Watch watch(report);
            native_diagnostic_step("storage.calibration","maker",3,&report,destroyed);
            auto owner=owned::make_in_memory_owned_pair(std::move(ingress),source.capacity,report);
            const auto* wrapper=owner.get();
            native_diagnostic_step("storage.calibration","wrapper.allocation",3,&report,destroyed);
            phases[2]=allocation_of(wrapper,"allocation.wrapper");native_diagnostic_phase_ordinals[2]=phases[2];
            // First ordinary allocation after checked arena binding is the
            // first role's storage (before its DOM). Check its actual size too.
            for(size_t i=0;i<native_component_fault::calls;++i)
                if(native_component_fault::allocations[i].arena_bound){phases[1]=i+1;native_diagnostic_phase_ordinals[1]=phases[1];break;}
            native_diagnostic_step("storage.calibration","weapon.storage_size",3,&report,destroyed,false,false,
                phases[1]?native_component_fault::allocations[phases[1]-1].bytes:0,sizeof(Native::WeaponMap));
            need(phases[1]&&native_component_fault::allocations[phases[1]-1].bytes==sizeof(Native::WeaponMap));
            const void* weapon_component=native_component_fault::allocations[phases[1]-1].pointer;
            const void* arena=report.owner();
            owner.reset();
            native_diagnostic_step("storage.calibration","deletion_count",3,&report,destroyed);
            need(native_component_fault::deletes>=2);
            const void* pair=native_component_fault::deletions[native_component_fault::deletes-2];
            native_diagnostic_step("storage.calibration","pair.allocation",3,&report,destroyed);
            phases[0]=allocation_of(pair,"allocation.pair");native_diagnostic_phase_ordinals[0]=phases[0];
            native_diagnostic_step("storage.calibration","pair.storage_size",3,&report,destroyed,false,false,
                native_component_fault::allocations[phases[0]-1].bytes,sizeof(owned::detail::Pair<NativeGuards,Native>));
            need(native_component_fault::allocations[phases[0]-1].bytes==sizeof(owned::detail::Pair<NativeGuards,Native>));
            native_diagnostic_step("storage.calibration","deletion_order",3,&report,destroyed);
            const bool order_equal=last_delete(weapon_component,"last_delete.weapon")<last_delete(arena,"last_delete.arena")&&
                last_delete(arena,"last_delete.arena")<last_delete(raw,"last_delete.raw")&&
                last_delete(raw,"last_delete.raw")<last_delete(guards,"last_delete.guards")&&
                last_delete(guards,"last_delete.guards")<last_delete(pair,"last_delete.pair")&&
                last_delete(pair,"last_delete.pair")<last_delete(wrapper,"last_delete.wrapper");
            native_diagnostic_step("storage.calibration","deletion_order",3,&report,destroyed,false,order_equal);
            need(order_equal);
            native_component_fault::active=false;
            native_diagnostic_step("storage.calibration","phase_order_and_owner",3,&report,destroyed);
            need(destroyed==1&&phases[0]<phases[1]&&phases[1]<phases[2]);
            native_diagnostic_step("storage.calibration","release_once",3,&report,destroyed);released_once(report);
        }
        for(size_t phase=0;phase<phases.size();++phase)
        {
            Report report;input::Counters counters;unsigned destroyed=0;bool refused=false;
            auto ingress=native_ingress(source,source.original,source.trusted_source_pins,counters,destroyed);
            const auto* raw=&ingress->input();
            native_component_fault::Watch watch(report,phases[phase]);
            native_diagnostic_step("storage.fault","maker",phase,&report,destroyed);
            try{auto value=owned::make_in_memory_owned_pair(std::move(ingress),source.capacity,report);static_cast<void>(value);}
            catch(const std::bad_alloc& error)
            {
                native_diagnostic_step("storage.fault","first_requested_refusal",phase,&report,destroyed,refused);
                need(native_component_fault::refusal_count==1&&
                    native_component_fault::first_refusal.cause==native_component_fault::RefusalCause::requested&&
                    native_component_fault::first_refusal.ordinal==native_component_fault::fail_at&&
                    native_component_fault::first_refusal.ordinal==phases[phase]);
                native_diagnostic_step("storage.fault","same_live_primary",phase,&report,destroyed,refused);
                need(&error==native_component_fault::primary); // SAME live exception, not current_exception() copies.
                native_component_fault::primary=nullptr;refused=true;
            }
            native_component_fault::active=false;
            native_diagnostic_step("storage.fault","ownership_after_refusal",phase,&report,destroyed,refused);
            need(refused&&!ingress&&destroyed==1&&
                native_component_fault::primary==nullptr&&last_delete(raw,"last_delete.raw")>0&&report.primary()==Failure::none);
            const std::array<size_t,3> expected_sizes{sizeof(owned::detail::Pair<NativeGuards,Native>),
                sizeof(Native::WeaponMap),sizeof(NativeOwner)};
            native_diagnostic_step("storage.fault","failed_storage_size_and_bound",phase,&report,destroyed,refused,false,
                native_component_fault::failed_bytes,expected_sizes[phase]);
            need(native_component_fault::failed_bytes==expected_sizes[phase]&&native_component_fault::failed_bound==(phase!=0));
            native_diagnostic_step("storage.fault",phase==0?"no_arena_release":"release_once",phase,&report,destroyed,refused);
            if(phase==0)need(!report.bound()&&report.release_attempts()==0);
            else released_once(report);
        }
        // These are storage-before-move/DOM frontiers. None is claimed as a
        // parser-internal allocation failure or a fatal allocator/OS guarantee.
    }
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
    void real_pair_and_native_variants(){real_pair_variants();native_components_variants();}
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
        native_preflight_refusals();
    }
    void map_lifetime_and_first_pointer_wins()
    {Report report;Stats stats;const auto& c=approved_cases[0];const auto r=execute(c,c.original,report,stats,Mode::preseed_maps);released_once(report);need(oracle(c,r));}
    void capacity_failure_unwinds()
    {
        Report report;Stats stats;bool refused=false;
        try{execute(approved_cases[0],approved_cases[0].original,report,stats,Mode::normal,1);}catch(const zonetool::checked_memory_error& e){refused=e.reason()==Failure::capacity;}
        need(refused&&stats.publications==0&&stats.attachment_parses==0&&report.primary()==Failure::capacity);released_once(report);
        native_second_role_capacity_failure();
    }
    void real_second_parse_error_keeps_primary()
    {
        Report report;Stats stats;bool refused=false;
        try{execute(approved_cases[0],approved_cases[0].original,report,stats,Mode::second_parse_error);}catch(const pq::ordered_json::type_error&){refused=true;}
        need(refused&&stats.weapon_parses==1&&stats.attachment_parses==1&&stats.publications==0&&report.primary()==Failure::none);released_once(report);
    }
    void bypass_real_core_refuses()
    {
        NativeDiagnosticScope diagnostic_scope;
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
        native_diagnostic_step("fourth_address.legacy","execute",0,&fourth_report);
        try{execute(fourth,fourth.original,fourth_report,fourth_stats);}catch(const PinError&){fourth_refused=true;}
        native_diagnostic_step("fourth_address.legacy","refused_before_copy",0,&fourth_report,0,fourth_refused);
        need(fourth_refused&&fourth_stats.copies==0&&fourth_stats.hashes==0&&fourth_stats.decodes==0&&
            fourth_stats.arenas==0&&fourth_stats.publications==0&&!fourth_report.bound());
        input::Counters fourth_counters;unsigned fourth_destroyed=0;bool native_fourth_refused=false;
        native_diagnostic_step("fourth_address.native","ingress",0,nullptr,fourth_destroyed);
        try{auto ingress=native_ingress(fourth,fourth.original,fourth.trusted_source_pins,fourth_counters,fourth_destroyed);static_cast<void>(ingress);}
        catch(const PinError&){native_fourth_refused=true;}
        native_diagnostic_step("fourth_address.native","refused_before_copy",0,nullptr,fourth_destroyed,native_fourth_refused);
        need(native_fourth_refused&&fourth_counters.copies==0&&fourth_counters.hashes==0&&fourth_destroyed==0);
        Report report;Stats stats;bool refused=false;
        native_diagnostic_step("bypass_core","execute",0,&report);
        try{execute(approved_cases[0],approved_cases[0].original,report,stats,Mode::bypass_core);}catch(const std::logic_error&){refused=true;}
        native_diagnostic_step("bypass_core","no_publication",0,&report,0,refused);
        need(refused&&stats.weapon_parses==0&&stats.publications==0);
        native_diagnostic_step("bypass_core","release_once",0,&report,0,refused);released_once(report);
        native_storage_failures_and_order();
    }
}
int main()
{
    using namespace authored_pair_fixture;
    struct Case{const char* name;void(*run)();};
    const Case tests[]={{"sha256_known_vectors",hash_vectors},{"real_pair_and_approved_mutants",real_pair_and_native_variants},
        {"same_length_mutant_old_source_pin_refuses",same_length_old_pin_refuses},{"malformed_raw_old_pins_refuse_before_decode",malformed_inputs_refuse_before_decode},
        {"real_maps_outlive_roots_first_pointer_wins",map_lifetime_and_first_pointer_wins},{"checked_capacity_failure_unwinds_once",capacity_failure_unwinds},
        {"real_second_parser_failure_keeps_primary",real_second_parse_error_keeps_primary},{"bypassed_core_cannot_publish_inventory",bypass_real_core_refuses}};
    try{for(const auto& c:tests){c.run();std::cout<<"PASS "<<c.name<<'\n';}std::cout<<"IW7_AUTHORED_PAIR_REAL_CORE_FIXTURE=8\n";return 0;}
    catch(const std::exception& e){std::cerr<<e.what()<<'\n';emit_native_diagnostic();return 2;}
}
