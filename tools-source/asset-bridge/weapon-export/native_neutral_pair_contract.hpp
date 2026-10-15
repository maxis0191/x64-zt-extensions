#pragma once
// Pure identity and descriptive-inventory checks only. No input manifest,
// parser schema, filesystem, runtime authority or builder plan is implemented.
#include "native_neutral_dependencies.hpp"

namespace zonetool::iw7::neutral_pair_contract
{
    namespace dependencies = neutral_dependencies;
    enum class Mode { owned_full, reference_shell };
    struct Claim { int type; std::string_view name; Mode mode; };
    enum class Failure { none, bounds, mode, type, name, mixed_modes, duplicate_owned };
    struct IdentityCheck
    {
        Failure failure = Failure::none;
        size_t first = 0, second = 0;
        bool valid() const { return failure == Failure::none; }
    };
    namespace detail
    {
        // Only use after validating each claim, or as part of that validation.
        inline std::string_view canonical_view(const Claim& claim)
        {
            auto name = claim.name;
            if (claim.mode == Mode::reference_shell && !name.empty() && name.front() == ',') name.remove_prefix(1);
            return name;
        }
    }

    // A reference spelling may be bare or carry exactly one native comma.
    // An owned identity must be bare. No case-folding or Unicode normalization.
    inline bool canonical_name(const Claim& claim, std::string_view& name)
    {
        if (claim.mode != Mode::owned_full && claim.mode != Mode::reference_shell) return false;
        name = detail::canonical_view(claim);
        return dependencies::Collector::valid_name(name);
    }

    inline IdentityCheck check_identities(const Claim* claims, size_t count)
    {
        if (count > dependencies::Collector::max_external + 2 || (count && !claims))
            return {Failure::bounds, 0, 0};
        // Validate the whole finite input before comparing identities. This is
        // a descriptive collision check, never an external-family policy grant.
        for (size_t i = 0; i < count; ++i)
        {
            if (claims[i].mode != Mode::owned_full && claims[i].mode != Mode::reference_shell)
                return {Failure::mode, i, i};
            if (claims[i].type != ASSET_TYPE_WEAPON && !dependencies::reference_recognized(claims[i].type))
                return {Failure::type, i, i};
            std::string_view name;
            if (!canonical_name(claims[i], name)) return {Failure::name, i, i};
        }
        for (size_t i = 0; i < count; ++i)
        {
            const auto current = detail::canonical_view(claims[i]);
            for (size_t j = 0; j < i; ++j)
            {
                if (claims[i].type != claims[j].type) continue;
                const auto previous = detail::canonical_view(claims[j]);
                if (current != previous) continue;
                if (claims[i].mode != claims[j].mode) return {Failure::mixed_modes, j, i};
                if (claims[i].mode == Mode::owned_full) return {Failure::duplicate_owned, j, i};
                // Repeated reference observations are legal, with provenance
                // retained by Inventory. This function does not emit rows.
            }
        }
        return {};
    }

    enum class InventoryState { incomplete, refused, complete_policy_blocked, complete_no_policy_blockers };
    struct Assessment
    {
        InventoryState state;
        size_t blocked_external;
        // Even complete_no_policy_blockers is only this finite type policy.
        // No successful result constructs a plan/token or authorizes a builder.
    };
    inline Assessment assess(const dependencies::Inventory& inventory)
    {
        if (!inventory.good()) return {InventoryState::refused, inventory.blocked_external_count()};
        if (!inventory.frozen()) return {InventoryState::incomplete, inventory.blocked_external_count()};
        const auto blocked = inventory.blocked_external_count();
        return {blocked ? InventoryState::complete_policy_blocked : InventoryState::complete_no_policy_blockers, blocked};
    }
}
