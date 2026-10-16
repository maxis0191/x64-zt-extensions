// AUTHORED SOURCE ONLY. Not compiled/run by the Python Source checks.
// All objects/events are owned fakes. No real FILE, native arena, route or OS API.
#include "native_pair_session.hpp"
#include <algorithm>
#include <iostream>
#include <string>
#include <type_traits>
#include <vector>

namespace ps = player_pair_session;
static void check(bool value) { if (!value) throw std::runtime_error("pair session fixture check failed"); }
template<class F> static void refuses(F call)
{
    bool threw = false;
    try { call(); } catch (const std::logic_error&) { threw = true; }
    check(threw);
}
static ps::ReadRequest request()
{
    ps::FileIdentity identity;
    identity.volume = 7; identity.id[0] = 42; identity.bytes = 66; identity.ordinary = true;
    return {ps::Role::Weapon, identity};
}

static void first_read_order()
{
    auto input = request(); ps::FirstReadOrder order(input);
    input.expected.id[0] = 99; // Mutable diagnostic input cannot change model copy.
    order.guards_retained(); order.opened(ps::Role::Weapon, 1);
    order.identity_checked(1, request().expected); order.before_size(1);
    order.before_first_byte(1); order.closed(1); order.guards_released();
    refuses([&] { order.before_first_byte(1); });
}
static void before_check_refuses()
{
    ps::FirstReadOrder order(request()); order.guards_retained(); order.opened(ps::Role::Weapon, 1);
    refuses([&] { order.before_size(1); });
    refuses([&] { order.identity_checked(1, request().expected); }); // No retry after failure.
    order.closed(1); order.guards_released();
}
static void foreign_identity_refuses()
{
    auto foreign = request().expected; foreign.id[0] = 43;
    ps::FirstReadOrder order(request()); order.guards_retained(); order.opened(ps::Role::Weapon, 1);
    refuses([&] { order.identity_checked(1, foreign); });
    order.closed(1); order.guards_released();
    foreign = request().expected; foreign.ordinary = false;
    check(!ps::same_file(request().expected, foreign));
}
static void role_stream_and_early_release_refuse()
{
    ps::FirstReadOrder role(request()); role.guards_retained();
    refuses([&] { role.opened(ps::Role::Attachment, 1); });
    ps::FirstReadOrder null(request()); null.guards_retained();
    refuses([&] { null.opened(ps::Role::Weapon, 0); });
    ps::FirstReadOrder swap(request()); swap.guards_retained(); swap.opened(ps::Role::Weapon, 1);
    refuses([&] { swap.identity_checked(2, request().expected); });
    ps::FirstReadOrder release(request()); release.guards_retained(); release.opened(ps::Role::Weapon, 1);
    refuses([&] { release.guards_released(); });
    refuses([&] { release.before_first_byte(1); });
}
static void checker_effects_and_reopen_refuse()
{
    ps::FirstReadOrder order(request()); order.guards_retained(); order.opened(ps::Role::Weapon, 1);
    refuses([&] { order.checker_consumed_repositioned_or_closed(); });
    refuses([&] { order.before_first_byte(1); });
    order.closed(1); order.guards_released();
    refuses([&] { order.opened(ps::Role::Weapon, 1); });
}
static void inactive_never_grants_admission()
{
    first_read_order(); // A complete fake event sequence still cannot enable hooks.
    refuses([] { ps::reject_native_activation(); });
    refuses([] { ps::relative_path(static_cast<ps::Role>(99)); });
}

struct Tracker
{
    std::vector<std::string> events;
    bool bad = false, guards = false, raw = false, arena = false, weapon_map = false, attachment_map = false;
    Tracker() { events.reserve(128); }
    void need(bool condition) noexcept { if (!condition) bad = true; }
};
struct Env
{
    struct Snapshot { std::string fastfile, cwd; std::vector<std::string> paths; bool sealed; };
    Tracker& track;
    Snapshot state{"before", "owned-cwd", {"first", "second"}, false};
    bool enter_throw = false, restore_throw = false, restore_false = false, aliases = false;
    Snapshot capture() const { return state; }
    void enter()
    {
        if (state.sealed || aliases) throw std::logic_error("unproven alias/reentry");
        state.sealed = true; track.events.push_back("route-enter");
        if (enter_throw) { state.fastfile = "changed"; throw std::logic_error("owned unwindable enter failure"); }
    }
    bool restore(const Snapshot& saved)
    {
        track.events.push_back("route-restore");
        if (restore_throw) throw std::logic_error("owned restore failure");
        if (restore_false) return false;
        state = saved; return true;
    }
    void mutate() { if (state.sealed) throw std::logic_error("sealed mutator"); state.paths.push_back("extra"); }
};
static void route_restore_on_unwind()
{
    Tracker t; Env env{t}; ps::CleanupReport report;
    try { ps::ScopedRoute<Env> scope(env, report); refuses([&] { env.mutate(); }); throw std::logic_error("owned throw"); }
    catch (const std::logic_error&) {}
    check(!report.cleanup_failed() && !env.state.sealed && env.state.paths == std::vector<std::string>({"first", "second"}));
    check(env.state.fastfile == "before" && env.state.cwd == "owned-cwd");
}
static void route_constructor_throw_is_only_unwindable()
{
    Tracker t; Env env{t}; ps::CleanupReport report; env.enter_throw = true;
    refuses([&] { ps::ScopedRoute<Env> scope(env, report); });
    check(!report.cleanup_failed() && !env.state.sealed && env.state.fastfile == "before");
    // This fake C++ throw is NOT VirtualAlloc failure/std::exit(0) qualification.
}
static void route_failure_is_reported()
{
    for (bool throwing : {false, true})
    {
        Tracker t; Env env{t}; ps::CleanupReport report;
        env.restore_throw = throwing; env.restore_false = !throwing;
        { ps::ScopedRoute<Env> scope(env, report); }
        check(report.cleanup_failed()); // No success/admission inferred.
    }
    Tracker t; Env env{t}; ps::CleanupReport report; env.aliases = true;
    refuses([&] { ps::ScopedRoute<Env> scope(env, report); });
}

struct Life
{
    Tracker& t; std::string name;
    Life(Tracker& track, std::string n) : t(track), name(std::move(n))
    {
        t.events.push_back(name + "+");
        if (name == "guards") t.guards = true;
        if (name == "raw") t.raw = true;
        if (name == "arena") t.arena = true;
        if (name == "weapon-map") t.weapon_map = true;
        if (name == "attachment-map") t.attachment_map = true;
    }
    ~Life() noexcept
    {
        if (name == "inventory") t.need(t.weapon_map && t.attachment_map && t.arena);
        if (name == "weapon-map" || name == "attachment-map") t.need(t.arena && t.raw && t.guards);
        if (name == "arena") { t.need(!t.weapon_map && !t.attachment_map); t.arena = false; }
        if (name == "weapon-map") t.weapon_map = false;
        if (name == "attachment-map") t.attachment_map = false;
        if (name == "raw") { t.need(!t.arena && t.guards); t.raw = false; }
        if (name == "guards") { t.need(!t.raw && !t.arena); t.guards = false; }
        t.events.push_back(name + "-");
    }
};
struct RouteLife
{
    Tracker& t; ps::ScopedRoute<Env> scope;
    RouteLife(Tracker& track, Env& env, ps::CleanupReport& report) : t(track), scope(env, report) {}
    ~RouteLife() noexcept { t.need(!t.arena); }
};
struct Factory
{
    Tracker& t; Env& env; ps::CleanupReport& report;
    std::string refuse; unsigned arena_calls = 0;
    std::unique_ptr<Life> make(const char* name)
    {
        if (refuse == name) throw std::logic_error("owned unwindable construction refusal");
        return std::make_unique<Life>(t, name);
    }
    auto guards() { return make("guards"); }
    auto raw() { return make("raw"); }
    auto route() { return std::make_unique<RouteLife>(t, env, report); }
    auto arena() { ++arena_calls; return make("arena"); }
    auto weapon() { return make("weapon-map"); }
    auto attachment() { return make("attachment-map"); }
};
using Owner = ps::OwnedPair<Life, Life, RouteLife, Life, Life, Life, int, int, Life>;
static_assert(!std::is_copy_constructible_v<Owner> && !std::is_move_constructible_v<Owner>);
static_assert(!std::is_copy_assignable_v<Owner> && !std::is_move_assignable_v<Owner>);
static void owner_preserves_both_maps_and_order()
{
    Tracker t; Env env{t}; ps::CleanupReport report; Factory factory{t, env, report}; int w = 1, a = 2;
    {
        Owner owner(factory); refuses([&] { owner.roots(); });
        owner.retain_returned_roots(&w, &a); check(owner.roots().weapon == &w && owner.roots().attachment == &a);
        check(t.weapon_map && t.attachment_map && t.arena && t.guards);
        owner.retain_copied_inventory(std::make_unique<Life>(t, "inventory"));
    }
    std::vector<std::string> ending{"inventory-", "attachment-map-", "weapon-map-", "arena-", "route-restore", "raw-", "guards-"};
    check(t.events.size() >= ending.size() && std::equal(ending.begin(), ending.end(), t.events.end() - ending.size()));
    check(!t.bad && !report.cleanup_failed() && !env.state.sealed);
}
static void partial_owner_unwinds_without_arena_before_raw()
{
    for (const auto& at : {"raw", "arena", "attachment-map"})
    {
        Tracker t; Env env{t}; ps::CleanupReport report; Factory factory{t, env, report}; factory.refuse = at;
        refuses([&] { Owner owner(factory); });
        check(!t.bad && !t.guards && !t.raw && !t.arena && !t.weapon_map && !t.attachment_map && !env.state.sealed);
        if (factory.refuse == "raw") check(factory.arena_calls == 0);
    }
}
static void root_binding_is_one_shot_not_adoption()
{
    Tracker t; Env env{t}; ps::CleanupReport report; Factory factory{t, env, report}; int w = 1, a = 2;
    Owner owner(factory);
    refuses([&] { owner.retain_returned_roots(nullptr, &a); });
    owner.retain_returned_roots(&w, &a);
    refuses([&] { owner.retain_returned_roots(&w, &a); });
    // No engine pointer()/init/prepare, builder or source-schema success token.
}

int main()
{
    const std::pair<const char*, void(*)()> cases[] = {
        {"first_read_order", first_read_order}, {"before_check_refuses", before_check_refuses},
        {"foreign_identity_refuses", foreign_identity_refuses}, {"role_stream_and_early_release_refuse", role_stream_and_early_release_refuse},
        {"checker_effects_and_reopen_refuse", checker_effects_and_reopen_refuse}, {"inactive_never_grants_admission", inactive_never_grants_admission},
        {"route_restore_on_unwind", route_restore_on_unwind}, {"route_constructor_throw_is_only_unwindable", route_constructor_throw_is_only_unwindable},
        {"route_failure_is_reported", route_failure_is_reported}, {"owner_preserves_both_maps_and_order", owner_preserves_both_maps_and_order},
        {"partial_owner_unwinds_without_arena_before_raw", partial_owner_unwinds_without_arena_before_raw}, {"root_binding_is_one_shot_not_adoption", root_binding_is_one_shot_not_adoption},
    };
    unsigned passed = 0;
    try { for (const auto& test : cases) { test.second(); ++passed; std::cout << "PASS " << test.first << '\n'; } }
    catch (const std::exception& e) { std::cerr << "FAIL after " << passed << ": " << e.what() << '\n'; return 1; }
    std::cout << "IW7_PAIR_SESSION_SOURCE_FIXTURE=" << passed << '\n';
    return passed == 12 ? 0 : 2;
}
