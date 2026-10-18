#pragma once
// Inactive ordinary ownership only. A Guards object is not an OS/FILE authority.
// No native components, parser invocation, admission or activation is supplied.
#include "native_pair_session.hpp"
#include "native_pair_bodies.hpp"
#include <type_traits>

namespace player_pair_owned_session
{
    using Input = player_pair_input::OwnedInput;
    template<class Guards> class OwnedIngress;
    template<class Guards, class Components> class TypedOwnedPair;
    namespace detail
    {
        template<class Guards, class Components> class Transfer;
        inline void need(bool value)
        {
            if (!value) throw std::logic_error("Original guards and raw ownership required");
        }
        template<class Guards, class Components>
        using Pair = player_pair_session::OwnedPair<Guards, Input,
            typename Components::Route, typename Components::Arena,
            typename Components::WeaponMap, typename Components::AttachmentMap,
            typename Components::Weapon, typename Components::Attachment,
            typename Components::Inventory>;
    }

    template<class Guards>
    std::unique_ptr<OwnedIngress<Guards>> copy_with_guards(std::unique_ptr<Guards>&&,
        const player_pair_input::Inputs&, const player_pair_input::Pins&, player_pair_input::Counters&);
    template<class Guards>
    std::unique_ptr<OwnedIngress<Guards>> adopt_owned(std::unique_ptr<Guards>&&, std::unique_ptr<Input>&&);
    template<class Guards, class Components>
    std::unique_ptr<TypedOwnedPair<Guards, Components>> make_validated_owned_pair(
        std::unique_ptr<OwnedIngress<Guards>>&&, Components&);

    template<class Guards> class OwnedIngress final
    {
        static_assert(std::is_nothrow_destructible_v<Guards>, "Guard destruction must not throw");
        // Reverse destruction is raw before original guards, including ctor throws.
        std::unique_ptr<Guards> guards_;
        std::unique_ptr<Input> raw_;
        struct Copy {};
        struct Adopt {};
        OwnedIngress(Copy, std::unique_ptr<Guards>&& guards,
            const player_pair_input::Inputs& incoming, const player_pair_input::Pins& pins,
            player_pair_input::Counters& counters) : guards_(std::move(guards))
        {
            detail::need(bool(guards_)); // Before OwnedInput bounds/copy/hash.
            raw_ = std::make_unique<Input>(incoming, pins, counters);
        }
        OwnedIngress(Adopt, std::unique_ptr<Guards>&& guards, std::unique_ptr<Input>&& raw) noexcept
            : guards_(std::move(guards)), raw_(std::move(raw)) {}

        template<class G> friend std::unique_ptr<OwnedIngress<G>> copy_with_guards(
            std::unique_ptr<G>&&, const player_pair_input::Inputs&,
            const player_pair_input::Pins&, player_pair_input::Counters&);
        template<class G> friend std::unique_ptr<OwnedIngress<G>> adopt_owned(
            std::unique_ptr<G>&&, std::unique_ptr<Input>&&);
        template<class G, class C> friend class detail::Transfer;
    public:
        ~OwnedIngress() noexcept = default;
        OwnedIngress(const OwnedIngress&) = delete;
        OwnedIngress& operator=(const OwnedIngress&) = delete;
        OwnedIngress(OwnedIngress&&) = delete;
        OwnedIngress& operator=(OwnedIngress&&) = delete;
        const Input& input() const & { detail::need(bool(raw_)); return *raw_; }
        const Input& input() const && = delete;
    };

    // Bind existing caller owner variables; do not acquire owners in arguments.
    // new allocates storage before either referenced unique_ptr is moved.
    template<class Guards>
    std::unique_ptr<OwnedIngress<Guards>> copy_with_guards(std::unique_ptr<Guards>&& guards,
        const player_pair_input::Inputs& incoming, const player_pair_input::Pins& pins,
        player_pair_input::Counters& counters)
    {
        return std::unique_ptr<OwnedIngress<Guards>>(new OwnedIngress<Guards>(
            typename OwnedIngress<Guards>::Copy{}, std::move(guards), incoming, pins, counters));
    }
    template<class Guards>
    std::unique_ptr<OwnedIngress<Guards>> adopt_owned(
        std::unique_ptr<Guards>&& guards, std::unique_ptr<Input>&& raw)
    {
        auto value = std::unique_ptr<OwnedIngress<Guards>>(new OwnedIngress<Guards>(
            typename OwnedIngress<Guards>::Adopt{}, std::move(guards), std::move(raw)));
        detail::need(bool(value->guards_) && bool(value->raw_));
        return value; // No claim of guards during this already-built raw's copy.
    }

    namespace detail
    {
        template<class Guards, class Components> class Transfer final
        {
            std::unique_ptr<OwnedIngress<Guards>> ingress_;
            Components& components_; // Used during construction only; never stored in Pair.
            const Input* raw_view_ = nullptr;
            typename Components::Arena* arena_view_ = nullptr;
        public:
            Transfer(std::unique_ptr<OwnedIngress<Guards>>&& ingress, Components& components)
                : ingress_(std::move(ingress)), components_(components)
            {
                need(bool(ingress_));
                need(bool(ingress_->guards_) && bool(ingress_->raw_));
                raw_view_ = ingress_->raw_.get();
                // Both owners remain here for the entire REAL preflight. No
                // callback/verdict and no validation between the later moves.
                iw7::neutral::player_pair_bodies::validate_owned_pair_bodies(*raw_view_);
            }
            Transfer(const Transfer&) = delete;
            Transfer& operator=(const Transfer&) = delete;
            std::unique_ptr<Guards> guards() noexcept { return std::move(ingress_->guards_); }
            std::unique_ptr<Input> raw() noexcept { return std::move(ingress_->raw_); }
            const Input* view() const noexcept { return raw_view_; }
            std::unique_ptr<typename Components::Route> route() { return components_.route(*raw_view_); }
            std::unique_ptr<typename Components::Arena> arena()
            {
                auto value = components_.arena(*raw_view_);
                arena_view_ = value.get();
                return value;
            }
            std::unique_ptr<typename Components::WeaponMap> weapon()
            { return components_.weapon_map(*raw_view_, *arena_view_); }
            std::unique_ptr<typename Components::AttachmentMap> attachment()
            { return components_.attachment_map(*raw_view_, *arena_view_); }
        };
    }

    template<class Guards, class Components> class TypedOwnedPair final
    {
        static_assert(std::is_nothrow_destructible_v<typename Components::Route> &&
            std::is_nothrow_destructible_v<typename Components::Arena> &&
            std::is_nothrow_destructible_v<typename Components::WeaponMap> &&
            std::is_nothrow_destructible_v<typename Components::AttachmentMap> &&
            std::is_nothrow_destructible_v<typename Components::Inventory>, "Components must unwind without throwing");
        std::unique_ptr<detail::Pair<Guards, Components>> pair_;
        const Input* raw_view_; // Pointee owned exclusively by pair_, not the adapter.
        TypedOwnedPair(std::unique_ptr<detail::Pair<Guards, Components>>&& pair, const Input* raw) noexcept
            : pair_(std::move(pair)), raw_view_(raw) {}
        template<class G, class C> friend std::unique_ptr<TypedOwnedPair<G, C>> make_validated_owned_pair(
            std::unique_ptr<OwnedIngress<G>>&&, C&);
    public:
        ~TypedOwnedPair() noexcept = default;
        TypedOwnedPair(const TypedOwnedPair&) = delete;
        TypedOwnedPair& operator=(const TypedOwnedPair&) = delete;
        TypedOwnedPair(TypedOwnedPair&&) = delete;
        TypedOwnedPair& operator=(TypedOwnedPair&&) = delete;
        const Input& input() const & noexcept { return *raw_view_; }
        const Input& input() const && = delete;
    };

    template<class Guards, class Components>
    std::unique_ptr<TypedOwnedPair<Guards, Components>> make_validated_owned_pair(
        std::unique_ptr<OwnedIngress<Guards>>&& ingress, Components& components)
    {
        detail::Transfer<Guards, Components> transfer(std::move(ingress), components);
        auto pair = std::make_unique<detail::Pair<Guards, Components>>(transfer);
        return std::unique_ptr<TypedOwnedPair<Guards, Components>>(new TypedOwnedPair<Guards, Components>(
            std::move(pair), transfer.view()));
    }
    // Only ordinary unwinding is covered. A noexcept destructor is not proof
    // of OS release; an existing cleanup report must outlive its components.
    // No FILE/route/native Factory or fatal allocator closure is implemented.
}
