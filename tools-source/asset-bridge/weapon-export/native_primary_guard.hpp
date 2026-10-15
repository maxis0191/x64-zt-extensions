#pragma once
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstring>

// Pure decision helper. The caller supplies the existing field reads lazily;
// neither this header nor its fixture knows an engine address or asset name.
namespace iw7_player_template_primary
{
    enum class Check
    {
        none, type, inventory, class_min, class_max, class_non_player, class_item,
        clip, max_ammo, ammo_used, damage, speed, lifetime_finite, lifetime_positive,
        gun_model, world_model, animations
    };
    enum class Kind { none, signed_integer, float32_bits, presence };
    struct Failure
    {
        Check check;
        Kind kind;
        std::int32_t integer;  // Reported only for integer/presence failures.
        std::uint32_t bits;    // Reported only for an observed float failure.
    };
    inline Failure integer(Check check, std::int32_t value)
    {
        return {check, Kind::signed_integer, value, 0};
    }
    inline Failure real(Check check, float value)
    {
        static_assert(sizeof(float) == sizeof(std::uint32_t));
        std::uint32_t bits;
        std::memcpy(&bits, &value, sizeof(bits));
        return {check, Kind::float32_bits, 0, bits};
    }
    inline Failure absent(Check check)
    {
        return {check, Kind::presence, 0, 0};
    }
    template <typename Reader>
    Failure first_failure(Reader& source)
    {
        // The original code reads classification before evaluating its OR.
        const auto classification = source.classification();
        const auto type = source.type();
        if (type != 3) return integer(Check::type, type);
        const auto inventory = source.inventory();
        if (inventory != 0) return integer(Check::inventory, inventory);
        if (classification < 0) return integer(Check::class_min, classification);
        if (classification > 13) return integer(Check::class_max, classification);
        if (classification == 10) return integer(Check::class_non_player, classification);
        if (classification == 11) return integer(Check::class_item, classification);
        const auto clip = source.clip();
        if (clip <= 0) return integer(Check::clip, clip);
        const auto max_ammo = source.max_ammo();
        if (max_ammo <= 0) return integer(Check::max_ammo, max_ammo);
        const auto ammo_used = source.ammo_used();
        if (ammo_used <= 0) return integer(Check::ammo_used, ammo_used);
        const auto damage = source.damage();
        if (damage <= 0) return integer(Check::damage, damage);
        const auto speed = source.speed();
        if (speed <= 0) return integer(Check::speed, speed);
        const auto finite_lifetime = source.lifetime();
        if (!std::isfinite(finite_lifetime)) return real(Check::lifetime_finite, finite_lifetime);
        // Preserve the original second reached field read for the <= 0 test.
        const auto positive_lifetime = source.lifetime();
        if (positive_lifetime <= 0) return real(Check::lifetime_positive, positive_lifetime);
        if (!source.gun_model()) return absent(Check::gun_model);
        if (!source.world_model()) return absent(Check::world_model);
        if (!source.animations()) return absent(Check::animations);
        return {Check::none, Kind::none, 0, 0};
    }
}
