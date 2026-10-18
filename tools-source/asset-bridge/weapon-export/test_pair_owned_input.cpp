// AUTHORED, NOT COMPILED/EXECUTED. Requires a new reviewed/admitted native GO.
// Standard-memory raw ownership only; no JSON/native types, SDK, arena or FILE.
#include "native_pair_owned_input.hpp"
#include <cstdlib>
#include <iostream>
#include <limits>
#include <memory>
#include <new>
#include <type_traits>
#include <utility>

namespace input = player_pair_input;
namespace allocation_fault
{
    // Finite fixture-only fault in real standard allocations, not a fake owner.
    struct Failure : std::bad_alloc {};
    bool armed = false;
    std::size_t remaining = 0, live = 0;
}
void* operator new(std::size_t bytes)
{
    if (allocation_fault::armed)
    {
        if (!allocation_fault::remaining) throw allocation_fault::Failure();
        --allocation_fault::remaining;
    }
    if (void* result = std::malloc(bytes ? bytes : 1)) { ++allocation_fault::live; return result; }
    throw std::bad_alloc();
}
void operator delete(void* pointer) noexcept
{
    if (pointer) { --allocation_fault::live; std::free(pointer); }
}
void* operator new[](std::size_t bytes) { return ::operator new(bytes); }
void operator delete[](void* pointer) noexcept { ::operator delete(pointer); }
void operator delete(void* pointer, std::size_t) noexcept { ::operator delete(pointer); }
void operator delete[](void* pointer, std::size_t) noexcept { ::operator delete(pointer); }

static void check(bool value) { if (!value) throw std::runtime_error("Owned input fixture refused"); }
template<class F> static void refuses(F call)
{
    bool failed = false;
    try { call(); } catch (const input::PinError&) { failed = true; }
    check(failed);
}
struct Data
{
    std::array<std::string, 4> raw, hashes;
    input::Inputs incoming;
    input::Pins pins;
    Data()
    {
        // Arbitrary authored bytes prove ownership only, never parse eligibility.
        for (std::size_t i = 0; i < raw.size(); ++i)
        {
            raw[i] = std::string(i == 3 ? 66 : 128, static_cast<char>('a' + i));
            hashes[i] = input::detail::sha256(raw[i]);
            incoming[i] = raw[i]; pins[i] = {raw[i].size(), hashes[i]};
        }
    }
};
static void known_vectors()
{
    check(input::detail::sha256("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    check(input::detail::sha256("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    check(input::detail::sha256(std::string(1000000, 'a')) == "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
}
static void every_role_bound_precedes_copies()
{
    Data data;
    for (std::size_t role = 0; role < 4; ++role)
    {
        auto incoming = data.incoming; incoming[role] = {};
        input::Counters empty;
        refuses([&] { input::OwnedInput owner(incoming, data.pins, empty); });
        check(empty.copies == 0 && empty.hashes == 0);

        const std::string oversized(input::role_caps[role] + 1, 'x');
        incoming = data.incoming; incoming[role] = oversized;
        input::Counters large;
        refuses([&] { input::OwnedInput owner(incoming, data.pins, large); });
        check(large.copies == 0 && large.hashes == 0);
        for (const auto length : {std::size_t(0), input::role_caps[role] + 1})
        {
            auto pins = data.pins; pins[role].bytes = length;
            input::Counters expected;
            refuses([&] { input::OwnedInput owner(data.incoming, pins, expected); });
            check(expected.copies == 0 && expected.hashes == 0);
        }
    }
}
static void actual_bounded_addition()
{
    // Fixed role caps sum to the total cap, so an all-role-valid input cannot
    // exceed it. Exercise the SAME production addition at its own boundaries.
    check(input::detail::checked_total(0, input::total_cap) == input::total_cap);
    check(input::detail::checked_total(input::total_cap - 1, 1) == input::total_cap);
    refuses([] { input::detail::checked_total(input::total_cap, 1); });
    refuses([] { input::detail::checked_total((std::numeric_limits<std::size_t>::max)(), 1); });
    refuses([] { input::detail::checked_total(1, (std::numeric_limits<std::size_t>::max)()); });
}
static void pins_and_roles_refuse()
{
    Data data;
    for (const auto digest : {std::string(64, 'A'), std::string(63, 'a')})
    {
        auto pins = data.pins; pins[3].sha256 = digest; input::Counters counters;
        refuses([&] { input::OwnedInput owner(data.incoming, pins, counters); });
        check(counters.copies == 0 && counters.hashes == 0);
    }
    auto short_pin = data.pins; --short_pin[3].bytes; input::Counters lengths;
    refuses([&] { input::OwnedInput owner(data.incoming, short_pin, lengths); });
    check(lengths.copies == 0 && lengths.hashes == 0);

    std::string changed = data.raw[2]; changed[0] = 'z';
    auto incoming = data.incoming; incoming[2] = changed; input::Counters mutation;
    refuses([&] { input::OwnedInput owner(incoming, data.pins, mutation); });
    check(mutation.copies == 4 && mutation.hashes == 3);
    incoming = data.incoming; std::swap(incoming[0], incoming[1]); input::Counters swapped;
    refuses([&] { input::OwnedInput owner(incoming, data.pins, swapped); });
    check(swapped.copies == 4 && swapped.hashes == 1);
    auto pins = data.pins; std::swap(pins[0], pins[1]); input::Counters swapped_pins;
    refuses([&] { input::OwnedInput owner(data.incoming, pins, swapped_pins); });
    check(swapped_pins.copies == 4 && swapped_pins.hashes == 1);
}
static void private_storage_outlives_caller()
{
    static_assert(!std::is_copy_constructible_v<input::OwnedInput> && !std::is_move_constructible_v<input::OwnedInput>);
    static_assert(!std::is_convertible_v<input::OwnedInput, bool>);
    static_assert(std::is_same_v<decltype(std::declval<const input::OwnedInput&>().bytes(input::Role::report)), const std::string&>);
    std::unique_ptr<input::OwnedInput> owner;
    input::Counters counters;
    {
        Data data;
        owner = std::make_unique<input::OwnedInput>(data.incoming, data.pins, counters);
        for (std::size_t i = 0; i < 4; ++i)
        {
            data.raw[i].assign(1, 'x'); data.hashes[i].assign(64, '0');
            data.pins[i] = {1, data.hashes[i]}; data.incoming[i] = data.raw[i];
        }
    }
    for (std::size_t i = 0; i < 4; ++i)
    {
        const auto role = static_cast<input::Role>(i);
        const std::string expected(i == 3 ? 66 : 128, static_cast<char>('a' + i));
        check(owner->bytes(role) == expected);
        check(owner->pin(role).bytes == expected.size());
        check(owner->pin(role).sha256 == input::detail::sha256(expected));
    }
    check(counters.copies == 4 && counters.hashes == 4);
    refuses([&] { owner->bytes(static_cast<input::Role>(4)); });
}
static void partial_standard_memory_failure_unwinds()
{
    Data data;
    for (const std::size_t fail_after : {std::size_t(0), std::size_t(3)})
    {
        input::Counters counters; const auto before = allocation_fault::live;
        bool original_type = false;
        allocation_fault::remaining = fail_after; allocation_fault::armed = true;
        try { input::OwnedInput owner(data.incoming, data.pins, counters); }
        catch (const allocation_fault::Failure&) { original_type = true; }
        catch (...) { allocation_fault::armed = false; throw; }
        allocation_fault::armed = false;
        check(original_type && allocation_fault::live == before && counters.hashes == 0);
        check(fail_after == 0 ? counters.copies == 0 : counters.copies > 0);
    }
}
int main()
{
    const struct { const char* name; void (*run)(); } cases[] = {
        {"sha256_known_vectors", known_vectors}, {"every_role_before_copy", every_role_bound_precedes_copies},
        {"actual_bounded_addition", actual_bounded_addition}, {"pins_and_roles", pins_and_roles_refuse},
        {"private_storage_lifetime", private_storage_outlives_caller}, {"standard_memory_unwind", partial_standard_memory_failure_unwinds}};
    try { for (const auto& test : cases) { test.run(); std::cout << "PASS " << test.name << '\n'; }
        std::cout << "IW7_PAIR_OWNED_INPUT=6\n"; return 0; }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 2; }
}
