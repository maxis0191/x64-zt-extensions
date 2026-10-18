// Authored production-code causals. NOT compiled/run by Source checks.
// A distinct reviewed CPP recipe/admission/GO is required.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>
#define assert_sizeof(T, N) static_assert(sizeof(T) == N)
#define assert_offsetof(T, M, N) static_assert(offsetof(T, M) == N)
#ifndef IW7_NATIVE_STRUCTS_HEADER
#error Exact pinned native structs header required under a distinct CPP admission
#endif
#include IW7_NATIVE_STRUCTS_HEADER
#include "native_neutral_pair_contract.hpp"

namespace
{
    using namespace zonetool::iw7;
    namespace nd = neutral_dependencies;
    namespace contract = neutral_pair_contract;
    void check(bool value) { if (!value) throw std::runtime_error("inventory fixture check failed"); }
    struct Memory
    {
        struct Span { const void* data; size_t size; };
        std::vector<Span> spans;
        void allow(const char* name) { spans.push_back({name, std::strlen(name) + 1}); }
        static bool copy(void* out, const void* input, size_t bytes, void* context)
        {
            const auto address = reinterpret_cast<std::uintptr_t>(input);
            for (const auto& span : static_cast<Memory*>(context)->spans)
            {
                const auto start = reinterpret_cast<std::uintptr_t>(span.data);
                if (address >= start && address - start <= span.size && bytes <= span.size - (address - start))
                { std::memcpy(out, input, bytes); return true; }
            }
            return false;
        }
    };
    struct Pair
    {
        WeaponCompleteDef weapon{}; WeaponDef fields{}; WeaponAttachment attachment{};
        Memory memory;
        Pair()
        {
            weapon.name = nd::weapon_name; weapon.weapDef = &fields; attachment.name = nd::attachment_name;
            memory.allow(weapon.name); memory.allow(attachment.name);
        }
    };
    constexpr int recognized[]{ASSET_TYPE_ANIM_PACKAGE, ASSET_TYPE_ATTACHMENT, ASSET_TYPE_FX,
        ASSET_TYPE_GESTURE, ASSET_TYPE_LASER, ASSET_TYPE_MATERIAL, ASSET_TYPE_RETICLE, ASSET_TYPE_RUMBLE,
        ASSET_TYPE_SFX_PACKAGE, ASSET_TYPE_TRACER, ASSET_TYPE_VFX, ASSET_TYPE_VFX_PACKAGE, ASSET_TYPE_XMODEL};

    void all_recognized_descriptive()
    {
        Pair pair; const char name[] = "fixture_shared"; pair.memory.allow(name);
        nd::Inventory inventory(Memory::copy, &pair.memory);
        check(inventory.begin(nd::Owner::weapon, pair.weapon.name));
        unsigned index = 0;
        for (const int type : recognized) check(inventory.asset(type, name, {"dependency[]", index++}));
        check(inventory.begin(nd::Owner::attachment, pair.attachment.name) && inventory.freeze());
        check(inventory.references().size() == 13 && inventory.edges().size() == 13 && inventory.occurrences() == 13);
        check(inventory.frozen() && inventory.policy_blocked() && inventory.blocked_external_count() == 9);
        check(contract::assess(inventory).state == contract::InventoryState::complete_policy_blocked);
    }
    void real_walkers_continue_after_blocker()
    {
        Pair pair;
        std::remove_pointer_t<decltype(pair.fields.gunXModel)> model{}; model.name = "fixture_model";
        FxEffectDef effect{}; effect.name = "fixture_fx";
        effect.elemDefCountLooping = 1; effect.elemDefs = reinterpret_cast<FxElemDef*>(1);
        pair.memory.allow(model.name); pair.memory.allow(effect.name);
        pair.fields.gunXModel = &model; pair.attachment.worldModelCamo = &model;
        pair.fields.projExplosionEffect.type = FX_COMBINED_FX; pair.fields.projExplosionEffect.u.fx = &effect;
        nd::Collector strict(Memory::copy, &pair.memory);
        check(!nd::collect_pair(&pair.weapon, &pair.attachment, strict));
        nd::Inventory inventory(Memory::copy, &pair.memory);
        check(nd::inventory_pair(&pair.weapon, &pair.attachment, inventory));
        check(inventory.references().size() == 2 && inventory.edges().size() == 3 && inventory.occurrences() == 3);
        check(inventory.edges()[0].path == "weapDef.gunXModel");
        check(inventory.edges()[1].path == "weapDef.projExplosionEffect");
        check(inventory.edges()[2].path == "worldModelCamo" && inventory.edges()[2].owner == nd::Owner::attachment);
        check(inventory.blocked_external_count() == 1);
    }
    void dedup_preserves_owners_and_indices()
    {
        Pair pair; const char name[] = "fixture_model"; pair.memory.allow(name);
        nd::Inventory inventory(Memory::copy, &pair.memory);
        check(inventory.begin(nd::Owner::weapon, pair.weapon.name));
        for (unsigned index : {2u, 2u, 5u}) check(inventory.asset(ASSET_TYPE_XMODEL, name, {"models[]", index}));
        check(inventory.begin(nd::Owner::attachment, pair.attachment.name));
        check(inventory.asset(ASSET_TYPE_XMODEL, name, {"models[]", 7}) && inventory.freeze());
        check(inventory.occurrences() == 4 && inventory.references().size() == 1 && inventory.edges().size() == 3);
        check(inventory.edges()[0].path == "models[2]" && inventory.edges()[1].path == "models[5]");
        check(inventory.edges()[2].path == "models[7]" && inventory.edges()[2].owner == nd::Owner::attachment);
    }
    void strict_reference_policy()
    {
        Pair pair; const char name[] = "fixture_external"; pair.memory.allow(name);
        for (const int type : recognized)
        {
            const bool allowed = type == ASSET_TYPE_FX || type == ASSET_TYPE_VFX || type == ASSET_TYPE_RETICLE || type == ASSET_TYPE_RUMBLE;
            check(nd::reference_supported(type) == allowed);
            nd::Collector strict(Memory::copy, &pair.memory);
            check(strict.begin(nd::Owner::weapon, pair.weapon.name));
            check(strict.asset(type, name, {"field", 0}) == allowed);
            if (allowed)
            {
                check(strict.begin(nd::Owner::attachment, pair.attachment.name) && strict.freeze());
                const nd::Row row{type, name}; check(strict.verify_rows(&row, 1));
            }
            else check(!strict.good() && !strict.frozen());
        }
    }
    void rumble_assessment_only()
    {
        Pair pair; RumbleInfo rumble{}; rumble.name = "fixture_rumble"; pair.memory.allow(rumble.name);
        pair.fields.fireRumble = &rumble;
        nd::Inventory allowed(Memory::copy, &pair.memory);
        check(nd::inventory_pair(&pair.weapon, &pair.attachment, allowed));
        check(allowed.frozen() && allowed.external_count() == 1 && allowed.blocked_external_count() == 0 && !allowed.policy_blocked());
        check(contract::assess(allowed).state == contract::InventoryState::complete_no_policy_blockers);
        Material material{}; material.name = "fixture_material"; pair.memory.allow(material.name); pair.weapon.killIcon = &material;
        nd::Inventory blocked(Memory::copy, &pair.memory);
        check(nd::inventory_pair(&pair.weapon, &pair.attachment, blocked));
        check(blocked.external_count() == 2 && blocked.blocked_external_count() == 1 && blocked.policy_blocked());
        check(contract::assess(blocked).state == contract::InventoryState::complete_policy_blocked);
        // These assessments describe policy only; Inventory still has no rows or builder authority.
    }
    void incomplete_and_refused_are_blocked()
    {
        Pair pair; nd::Inventory inventory(Memory::copy, &pair.memory);
        check(contract::assess(inventory).state == contract::InventoryState::incomplete && inventory.policy_blocked());
        check(inventory.begin(nd::Owner::weapon, pair.weapon.name) && !inventory.freeze());
        check(contract::assess(inventory).state == contract::InventoryState::refused && inventory.policy_blocked());
        nd::Inventory complete(Memory::copy, &pair.memory);
        check(nd::inventory_pair(&pair.weapon, &pair.attachment, complete));
        check(contract::assess(complete).state == contract::InventoryState::complete_no_policy_blockers);
        check(!complete.asset(ASSET_TYPE_FX, pair.weapon.name, {"late", 0}));
        check(contract::assess(complete).state == contract::InventoryState::refused && complete.policy_blocked());
    }
    void unknown_image_and_fx_refuse()
    {
        Pair pair; const char name[] = "fixture_external"; pair.memory.allow(name);
        for (const int type : {-1, static_cast<int>(ASSET_TYPE_IMAGE)})
        {
            nd::Inventory inventory(Memory::copy, &pair.memory);
            check(inventory.begin(nd::Owner::weapon, pair.weapon.name));
            check(!inventory.asset(type, name, {"field", 0}) && !inventory.frozen() && inventory.policy_blocked());
        }
        FxEffectDef fx{}; fx.name = name;
        pair.fields.projExplosionEffect.type = static_cast<FxCombinedType>(2); pair.fields.projExplosionEffect.u.fx = &fx;
        nd::Inventory invalid(Memory::copy, &pair.memory);
        check(!nd::inventory_pair(&pair.weapon, &pair.attachment, invalid) && !invalid.frozen());
    }
    void inherited_bounds_refuse()
    {
        Pair pair; const char name[] = "fixture_model"; pair.memory.allow(name);
        nd::Inventory inventory(Memory::copy, &pair.memory);
        check(inventory.begin(nd::Owner::weapon, pair.weapon.name));
        for (size_t i = 0; i < nd::Inventory::max_occurrences; ++i)
            check(inventory.asset(ASSET_TYPE_XMODEL, name, {"field", 0}));
        check(!inventory.asset(ASSET_TYPE_XMODEL, name, {"field", 0}) && !inventory.frozen());
        nd::Inventory count(Memory::copy, &pair.memory);
        check(!count.count(65, true) && count.policy_blocked());
        nd::Inventory origin(Memory::copy, &pair.memory);
        check(origin.begin(nd::Owner::weapon, pair.weapon.name));
        check(!origin.asset(ASSET_TYPE_XMODEL, name, {"models[]", 8192}));
        nd::Inventory unreadable(Memory::copy, &pair.memory);
        check(unreadable.begin(nd::Owner::weapon, pair.weapon.name));
        check(!unreadable.asset(ASSET_TYPE_XMODEL, reinterpret_cast<const char*>(1), {"field", 0}));
    }
    template<class T, class = void> struct HasRows : std::false_type {};
    template<class T> struct HasRows<T, std::void_t<decltype(std::declval<const T&>().verify_rows(nullptr, 0))>> : std::true_type {};
    void no_rows_or_strict_conversion()
    {
        static_assert(HasRows<nd::Collector>::value);
        static_assert(!HasRows<nd::Inventory>::value);
        static_assert(!std::is_convertible_v<nd::Inventory*, nd::Collector*>);
        static_assert(!std::is_constructible_v<nd::Collector, bool, nd::Copy, void*>);
        static_assert(nd::Inventory::max_occurrences == nd::Collector::max_occurrences);
        static_assert(nd::Inventory::max_external == nd::Collector::max_external);
    }
    void canonical_collisions_both_orders()
    {
        using Mode = contract::Mode;
        contract::Claim claims[]{{ASSET_TYPE_ATTACHMENT, nd::attachment_name, Mode::owned_full},
            {ASSET_TYPE_ATTACHMENT, ",sdk_shredder_clone_pap_zm", Mode::reference_shell}};
        auto result = contract::check_identities(claims, 2);
        check(result.failure == contract::Failure::mixed_modes && result.first == 0 && result.second == 1);
        std::swap(claims[0], claims[1]);
        check(contract::check_identities(claims, 2).failure == contract::Failure::mixed_modes);
        claims[0] = claims[1]; check(contract::check_identities(claims, 2).failure == contract::Failure::duplicate_owned);
        // Separate helper check, not a claim that Collector enforces arbitrary mixed modes.
        contract::Claim rumble[]{{ASSET_TYPE_RUMBLE, "fixture_rumble", Mode::owned_full},
            {ASSET_TYPE_RUMBLE, ",fixture_rumble", Mode::reference_shell}};
        check(contract::check_identities(rumble, 2).failure == contract::Failure::mixed_modes);
        std::swap(rumble[0], rumble[1]);
        check(contract::check_identities(rumble, 2).failure == contract::Failure::mixed_modes);
    }
    void canonical_aliases_preserve_types()
    {
        using Mode = contract::Mode;
        contract::Claim claims[]{{ASSET_TYPE_FX, "fixture", Mode::reference_shell},
            {ASSET_TYPE_FX, ",fixture", Mode::reference_shell}, {ASSET_TYPE_VFX, "fixture", Mode::owned_full}};
        check(contract::check_identities(claims, 3).valid());
        claims[2] = {ASSET_TYPE_FX, "Fixture", Mode::owned_full};
        check(contract::check_identities(claims, 3).valid()); // Native keys remain case-sensitive.
        claims[2] = {ASSET_TYPE_FX, "fixture", Mode::owned_full};
        check(contract::check_identities(claims, 3).failure == contract::Failure::mixed_modes);
    }
    void malformed_claims_refuse()
    {
        using Mode = contract::Mode;
        const char embedded[]{'a', 0, 'b'};
        const std::string long_name(512, 'a');
        const std::string_view bad[]{"", ",", ",,fixture", "default", "$default", "bad\nname", "\xc0\xaf",
            std::string_view(embedded, sizeof(embedded)), long_name};
        for (const auto name : bad)
        {
            const contract::Claim claim{ASSET_TYPE_FX, name, Mode::reference_shell};
            check(contract::check_identities(&claim, 1).failure == contract::Failure::name);
        }
        contract::Claim claim{ASSET_TYPE_FX, ",fixture", Mode::owned_full};
        check(contract::check_identities(&claim, 1).failure == contract::Failure::name);
        claim = {ASSET_TYPE_IMAGE, "fixture", Mode::reference_shell};
        check(contract::check_identities(&claim, 1).failure == contract::Failure::type);
        claim = {ASSET_TYPE_FX, "fixture", static_cast<Mode>(99)};
        check(contract::check_identities(&claim, 1).failure == contract::Failure::mode);
        std::string_view invalid; check(!contract::canonical_name(claim, invalid));
        check(contract::check_identities(nullptr, 1).failure == contract::Failure::bounds);
        check(contract::check_identities(&claim, nd::Collector::max_external + 3).failure == contract::Failure::bounds);
    }
    void owned_edges_remain_owned()
    {
        Pair pair; WeaponAttachment* pointers[]{&pair.attachment};
        pair.weapon.attachments6 = pointers; pair.weapon.numAttachments6 = 1;
        nd::Inventory inventory(Memory::copy, &pair.memory);
        check(nd::inventory_pair(&pair.weapon, &pair.attachment, inventory));
        check(inventory.references().size() == 1 && inventory.references()[0].owned && inventory.external_count() == 0);
        check(inventory.edges()[0].path == "attachments6[0]" && !inventory.policy_blocked());
        nd::Inventory mismatch(Memory::copy, &pair.memory);
        check(mismatch.begin(nd::Owner::weapon, pair.weapon.name));
        check(!mismatch.asset(ASSET_TYPE_XMODEL, pair.attachment.name, {"model", 0}));
    }
}
int main()
{
    const struct Case { const char* name; void (*run)(); } cases[]{
        {"all_recognized_descriptive", all_recognized_descriptive},
        {"real_walkers_continue_after_blocker", real_walkers_continue_after_blocker},
        {"dedup_preserves_owners_and_indices", dedup_preserves_owners_and_indices},
        {"strict_reference_policy", strict_reference_policy},
        {"rumble_assessment_only", rumble_assessment_only},
        {"incomplete_and_refused_are_blocked", incomplete_and_refused_are_blocked},
        {"unknown_image_and_fx_refuse", unknown_image_and_fx_refuse},
        {"inherited_bounds_refuse", inherited_bounds_refuse},
        {"no_rows_or_strict_conversion", no_rows_or_strict_conversion},
        {"canonical_collisions_both_orders", canonical_collisions_both_orders},
        {"canonical_aliases_preserve_types", canonical_aliases_preserve_types},
        {"malformed_claims_refuse", malformed_claims_refuse},
        {"owned_edges_remain_owned", owned_edges_remain_owned},
    };
    for (const auto& item : cases)
    {
        try { item.run(); std::printf("PASS %s\n", item.name); }
        catch (const std::exception& error) { std::printf("FAIL %s: %s\n", item.name, error.what()); return 1; }
    }
    std::puts("13/13 INVENTORY PASS");
    return 0;
}
