// Authored causal fixture. Native compilation/execution requires a distinct GO.
#include "native_primary_guard.hpp"
#include <cstdio>
#include <limits>
#include <stdexcept>
#include <vector>

namespace
{
    using namespace iw7_player_template_primary;
    enum class Read { classification, type, inventory, clip, max_ammo, ammo_used,
        damage, speed, lifetime, gun_model, world_model, animations };
    struct Reader
    {
        int classification_value = 5, type_value = 3, inventory_value = 0;
        int clip_value = 8, max_ammo_value = 80, ammo_used_value = 1;
        int damage_value = 100, speed_value = 4000;
        float lifetime_first = 60.0f, lifetime_second = 60.0f;
        bool gun_value = true, world_value = true, animations_value = true;
        unsigned lifetime_reads = 0, limit = 13;
        std::vector<Read> trace;
        void touch(Read field)
        {
            if (trace.size() >= limit) throw std::runtime_error("Read after first refusal");
            trace.push_back(field);
        }
        int classification() { touch(Read::classification); return classification_value; }
        int type() { touch(Read::type); return type_value; }
        int inventory() { touch(Read::inventory); return inventory_value; }
        int clip() { touch(Read::clip); return clip_value; }
        int max_ammo() { touch(Read::max_ammo); return max_ammo_value; }
        int ammo_used() { touch(Read::ammo_used); return ammo_used_value; }
        int damage() { touch(Read::damage); return damage_value; }
        int speed() { touch(Read::speed); return speed_value; }
        float lifetime() { touch(Read::lifetime); return lifetime_reads++ ? lifetime_second : lifetime_first; }
        bool gun_model() { touch(Read::gun_model); return gun_value; }
        bool world_model() { touch(Read::world_model); return world_value; }
        bool animations() { touch(Read::animations); return animations_value; }
    };
}
int main()
{
    unsigned checks = 0;
    const auto check = [&](bool value) { ++checks; if (!value) throw std::runtime_error("Primary first-refusal fixture failed"); };
    try
    {
        const std::vector<Read> complete = {Read::classification, Read::type, Read::inventory,
            Read::clip, Read::max_ammo, Read::ammo_used, Read::damage, Read::speed,
            Read::lifetime, Read::lifetime, Read::gun_model, Read::world_model, Read::animations};
        const auto expect = [&](Reader source, Failure wanted, unsigned reads)
        {
            source.limit = reads;
            const auto result = first_failure(source);
            check(result.check == wanted.check && result.kind == wanted.kind &&
                result.integer == wanted.integer && result.bits == wanted.bits);
            check(source.trace == std::vector<Read>(complete.begin(), complete.begin() + reads));
        };
        expect(Reader{}, {Check::none, Kind::none, 0, 0}, 13);
        Reader value;
        value.type_value = 1; value.inventory_value = 1; value.gun_value = false;
        expect(value, integer(Check::type, 1), 2); // Eager classification, then stop before inventory/pointers.
        value = Reader{}; value.inventory_value = 1; expect(value, integer(Check::inventory, 1), 3);
        value = Reader{}; value.classification_value = -1; expect(value, integer(Check::class_min, -1), 3);
        value = Reader{}; value.classification_value = 14; expect(value, integer(Check::class_max, 14), 3);
        value = Reader{}; value.classification_value = 10; expect(value, integer(Check::class_non_player, 10), 3);
        value = Reader{}; value.classification_value = 11; expect(value, integer(Check::class_item, 11), 3);
        value = Reader{}; value.clip_value = 0; expect(value, integer(Check::clip, 0), 4);
        value = Reader{}; value.max_ammo_value = 0; expect(value, integer(Check::max_ammo, 0), 5);
        value = Reader{}; value.ammo_used_value = 0; expect(value, integer(Check::ammo_used, 0), 6);
        value = Reader{}; value.damage_value = 0; expect(value, integer(Check::damage, 0), 7);
        value = Reader{}; value.speed_value = 0; expect(value, integer(Check::speed, 0), 8);
        value = Reader{}; value.lifetime_first = std::numeric_limits<float>::quiet_NaN();
        expect(value, real(Check::lifetime_finite, value.lifetime_first), 9);
        value = Reader{}; value.lifetime_second = 0.0f; expect(value, real(Check::lifetime_positive, 0.0f), 10);
        value = Reader{}; value.gun_value = false; expect(value, absent(Check::gun_model), 11);
        value = Reader{}; value.world_value = false; expect(value, absent(Check::world_model), 12);
        value = Reader{}; value.animations_value = false; expect(value, absent(Check::animations), 13);
        value = Reader{}; value.lifetime_first = 1.0f; value.lifetime_second = -1.0f;
        expect(value, real(Check::lifetime_positive, -1.0f), 10); // Two reached reads, as in the original guard.
        if (checks != 36) throw std::runtime_error("Exact primary-refusal check count required");
        std::printf("IW7_PLAYER_TEMPLATE_PRIMARY_CHECKS=36\n");
        return 0;
    }
    catch (const std::exception& error) { std::fprintf(stderr, "%s\n", error.what()); return 1; }
}
