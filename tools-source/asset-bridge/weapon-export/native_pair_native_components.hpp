#pragma once
// Opt-in in-memory components only. No name/FILE, DB, CLI or builder route.
// This Source is uncompiled at preparation; checked cleanup is ordinary unwind.
#include "weapon_pair_json_core.hpp"
#include "native_pair_owned_session.hpp"

namespace player_pair_owned_session
{
    class NativeComponents final
    {
    public:
        using Route = std::false_type;
        using Arena = zonetool::zone_memory;
        using Weapon = zonetool::iw7::WeaponCompleteDef;
        using Attachment = zonetool::iw7::WeaponAttachment;
        using Inventory = std::false_type; // No inventory/builder publication.
        using Roots = player_pair_session::BorrowedRoots<Weapon, Attachment>;
    private:
        using Json = zonetool::iw7::pair_json::ordered_json;
        using Strings = zonetool::iw7::pair_json::ScriptStrings;
        static void need(bool value)
        {
            if (!value) throw std::logic_error("Two SAME owned native component returns required");
        }
    public:
        class WeaponMap final
        {
            friend class NativeComponents;
            const Input* raw_;
            const Arena* arena_;
            Json dom_; // Reverse destruction: map before its owned DOM.
            Strings strings_;
            Weapon* root_ = nullptr; // Allocation is owned by the SAME arena.
            WeaponMap(const Input& raw, Arena& arena)
                : raw_(&raw), arena_(&arena),
                  dom_(Json::parse(raw.bytes(player_pair_input::Role::weapon)))
            {
                root_ = zonetool::iw7::pair_json::parse_weapon_json(dom_, &arena, strings_);
                need(root_ != nullptr);
            }
        public:
            ~WeaponMap() noexcept = default;
            WeaponMap(const WeaponMap&) = delete;
            WeaponMap& operator=(const WeaponMap&) = delete;
            WeaponMap(WeaponMap&&) = delete;
            WeaponMap& operator=(WeaponMap&&) = delete;
        };
        class AttachmentMap final
        {
            friend class NativeComponents;
            const Input* raw_;
            const Arena* arena_;
            Json dom_;
            Strings strings_;
            Attachment* root_ = nullptr;
            AttachmentMap(const Input& raw, Arena& arena)
                : raw_(&raw), arena_(&arena),
                  dom_(Json::parse(raw.bytes(player_pair_input::Role::attachment)))
            {
                root_ = zonetool::iw7::pair_json::parse_attachment_json(dom_, &arena, strings_);
                need(root_ != nullptr);
            }
        public:
            ~AttachmentMap() noexcept = default;
            AttachmentMap(const AttachmentMap&) = delete;
            AttachmentMap& operator=(const AttachmentMap&) = delete;
            AttachmentMap(AttachmentMap&&) = delete;
            AttachmentMap& operator=(AttachmentMap&&) = delete;
        };
    private:
        std::size_t capacity_;
        zonetool::checked_memory_report& cleanup_; // Original external report outlives Pair.
        Arena* arena_ = nullptr;
        WeaponMap* weapon_ = nullptr;
        AttachmentMap* attachment_ = nullptr;
        // Configuration only: no arena, DOM, core or borrowed builder storage.
        NativeComponents(std::size_t capacity, zonetool::checked_memory_report& cleanup) noexcept
            : capacity_(capacity), cleanup_(cleanup) {}
        template<class G> friend std::unique_ptr<TypedOwnedPair<G, NativeComponents>> make_in_memory_owned_pair(
            std::unique_ptr<OwnedIngress<G>>&&, std::size_t, zonetool::checked_memory_report&);
        // Grant only the four construction hooks, not the Transfer constructor
        // or its ownership moves, access to this builder's private surface.
        template<class G, class C> friend std::unique_ptr<typename C::Route> detail::Transfer<G, C>::route();
        template<class G, class C> friend std::unique_ptr<typename C::Arena> detail::Transfer<G, C>::arena();
        template<class G, class C> friend std::unique_ptr<typename C::WeaponMap> detail::Transfer<G, C>::weapon();
        template<class G, class C> friend std::unique_ptr<typename C::AttachmentMap> detail::Transfer<G, C>::attachment();
        std::unique_ptr<Route> route(const Input&) { return std::make_unique<Route>(); }
        std::unique_ptr<Arena> arena(const Input&)
        {
            auto value = std::make_unique<Arena>(zonetool::checked_memory_tag{}, capacity_, cleanup_);
            arena_ = value.get();
            return value;
        }
        std::unique_ptr<WeaponMap> weapon_map(const Input& raw, Arena& arena)
        {
            need(&arena == arena_);
            // Explicit new: make_unique has no access to the private role ctor.
            auto value = std::unique_ptr<WeaponMap>(new WeaponMap(raw, arena));
            weapon_ = value.get();
            return value;
        }
        std::unique_ptr<AttachmentMap> attachment_map(const Input& raw, Arena& arena)
        {
            need(&arena == arena_);
            auto value = std::unique_ptr<AttachmentMap>(new AttachmentMap(raw, arena));
            attachment_ = value.get();
            return value;
        }
        Roots completed_returns(const Input& raw) const
        {
            need(weapon_ && attachment_ && arena_ && weapon_->root_ && attachment_->root_);
            need(weapon_->raw_ == &raw && attachment_->raw_ == &raw &&
                weapon_->arena_ == arena_ && attachment_->arena_ == arena_);
            need(&weapon_->dom_ != &attachment_->dom_ && &weapon_->strings_ != &attachment_->strings_);
            return {weapon_->root_, attachment_->root_};
        }
    public:
        // Observers above are never used by destruction, including partial unwind.
        ~NativeComponents() noexcept = default;
        NativeComponents(const NativeComponents&) = delete;
        NativeComponents& operator=(const NativeComponents&) = delete;
        NativeComponents(NativeComponents&&) = delete;
        NativeComponents& operator=(NativeComponents&&) = delete;
    };

    template<class Guards>
    std::unique_ptr<TypedOwnedPair<Guards, NativeComponents>> make_in_memory_owned_pair(
        std::unique_ptr<OwnedIngress<Guards>>&& ingress, std::size_t capacity,
        zonetool::checked_memory_report& cleanup)
    {
        NativeComponents components(capacity, cleanup);
        // REAL Transfer preflight precedes every component hook. Its moves and
        // Pair/wrapper allocations retain the existing unique-owner semantics.
        auto value = make_validated_owned_pair(std::move(ingress), components);
        value->register_component_returns(components.completed_returns(value->input()));
        return value; // Builder dies here; Pair owns all surviving component storage.
    }
}
