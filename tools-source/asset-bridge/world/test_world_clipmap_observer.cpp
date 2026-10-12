// Prepared native harness, NOT compiled/run in the source-only task.
// Owns only synthetic buffers and a newly reserved page in this test process.
// Fixture seeding deliberately bypasses arm signatures; emitted signature_checked
// stays false. These records must never be accepted as an engine observation.
#include "world_clipmap_observer.hpp"
#include <stdexcept>
#include <string>

namespace w = zonetool::iw7::world_clip_observer;

void check(bool value, const char* message)
{
    if (!value) throw std::runtime_error(message);
}

template <class T, std::size_t N> void put(std::array<unsigned char, N>& data, std::size_t offset, T value)
{
    check(offset + sizeof(value) <= data.size(), "fixture bounds");
    std::memcpy(data.data() + offset, &value, sizeof(value));
}

struct fixture
{
    std::array<unsigned char, 512> blob{};
    std::array<unsigned char, 384> asset{};
    const char name[32] = "maps/original_observer_probe";
    std::uintptr_t slot{};
    fixture()
    {
        put(blob, 0, 0x57E0E057u); put(blob, 4, 0x10C0C010u); put(blob, 12, 11u);
        blob[16] = 8; blob[17] = 1; blob[19] = 1;
        put(blob, 20, 3u); put(blob, 24, 2u);
        std::memcpy(blob.data() + 40, "hk_2014.2.5-r1", 15);
        const char* names[] = {"__classnames__", "__types__", "__data__"};
        for (unsigned i = 0; i < 3; ++i)
        {
            const auto base = 64 + i * 64;
            std::memcpy(blob.data() + base, names[i], std::strlen(names[i]) + 1);
            put(blob, base + 20, i == 0 ? 256u : 384u);
            for (unsigned field = 24; field <= 44; field += 4) put(blob, base + field, i == 1 ? 0u : 128u);
        }
        std::memcpy(blob.data() + 256, "HavokPhysicsShapeList", 21);
        put(asset, 0, reinterpret_cast<std::uintptr_t>(name));
        put(asset, 0xF8, static_cast<std::uint32_t>(blob.size()));
        put(asset, 0x100, reinterpret_cast<std::uintptr_t>(blob.data()));
        slot = reinterpret_cast<std::uintptr_t>(asset.data());
    }
    void fixup_owned_fixture()
    {
        put(blob, 56, 1u);
        const auto root = reinterpret_cast<std::uintptr_t>(blob.data()) + 384;
        std::memcpy(reinterpret_cast<void*>(0x144BDF458), &root, sizeof(root));
    }
};

void seed_fixture_session()
{
    w::record = {}; w::emitted.store(false); w::phase.store(1);
    constexpr char name[] = "maps/original_observer_probe";
    std::memcpy(w::record.expected, name, sizeof(name));
}

auto pointer = [](const std::uintptr_t& value) noexcept { return value; };

void positive_and_error_preservation()
{
    fixture f; seed_fixture_session();
    int calls = 0;
    errno = EDOM; SetLastError(1234);
    const auto result = w::forward(22, &f.slot, [&]
    {
        check(GetLastError() == 1234 && errno == EDOM, "before changed thread errors");
        ++calls; f.fixup_owned_fixture(); errno = ERANGE; SetLastError(5678); return f.slot;
    }, pointer);
    check(GetLastError() == 5678 && errno == ERANGE, "after changed thread errors");
    check(calls == 1 && result == f.slot && w::record.post_ok && w::record.counts_read, "positive contract");
    check(w::record.reads <= w::read_limit && !w::record.signature_ok, "fixture evidence boundary");
    w::forward(22, &f.slot, [&] { ++calls; return f.slot; }, pointer);
    check(calls == 2 && w::phase.load() == 3, "second callback did not forward exactly once");
}

void refusal_cases()
{
    for (int scenario = 0; scenario < 11; ++scenario)
    {
        fixture f; seed_fixture_session(); int calls = 0;
        switch (scenario)
        {
        case 0: put(f.blob, 0, 0u); break;
        case 1: f.blob[54] = 'X'; break; // missing version terminator
        case 2: put(f.blob, 56, 1u); break;
        case 3: put(f.blob, 20, 100000u); break;
        case 4: put(f.blob, 84, 255u); break; // overlaps section table
        case 5: put(f.blob, 36, 128u); break;
        case 6: std::memset(f.blob.data() + 256, 'X', 128); break;
        case 7: f.slot = 0; break;
        case 8: put(f.asset, 0x100, std::uintptr_t{1}); break;
        case 9: w::record.reads = w::read_limit; break;
        case 10: w::record.expected[5] = 'X'; break;
        }
        w::forward(22, &f.slot, [&] { ++calls; return f.slot; }, pointer);
        check(calls == 1 && !w::record.post_ok && w::record.refusal &&
            w::record.reads <= w::read_limit, "refusal prevented original or exceeded budget");
    }
}

void post_refusal_and_original_exception()
{
    fixture f; seed_fixture_session(); int calls = 0;
    w::forward(22, &f.slot, [&] { ++calls; return f.slot; }, pointer);
    check(calls == 1 && !w::record.post_ok, "missing post fixup accepted");
    seed_fixture_session(); calls = 0;
    try
    {
        w::forward(22, &f.slot, [&]() -> std::uintptr_t { ++calls; throw std::runtime_error("original"); }, pointer);
        check(false, "original exception swallowed");
    }
    catch (const std::runtime_error& error) { check(std::string(error.what()) == "original", "exception changed"); }
    check(calls == 1 && w::record.original_threw, "original exception retried or lost");
    seed_fixture_session(); calls = 0;
    w::forward(3, &f.slot, [&] { ++calls; return f.slot; }, pointer);
    check(calls == 1 && w::record.reads == 0 && !w::emitted.load(), "unselected asset inspected");
    check(!w::finish(), "unseen clipmap accepted");
}

void post_identity_cases()
{
    for (int scenario = 0; scenario < 3; ++scenario)
    {
        fixture f; seed_fixture_session(); int calls = 0;
        w::forward(22, &f.slot, [&]
        {
            ++calls; f.fixup_owned_fixture();
            if (scenario == 0)
            {
                const std::uintptr_t wrong = 0;
                std::memcpy(reinterpret_cast<void*>(0x144BDF458), &wrong, sizeof(wrong));
            }
            if (scenario == 1) put(f.blob, 384 + 0x70, 1000001);
            return scenario == 2 ? std::uintptr_t{0} : f.slot;
        }, pointer);
        check(calls == 1 && !w::record.post_ok && w::record.refusal &&
            w::record.reads <= w::read_limit, "post identity/count refusal failed");
    }
}

int main()
{
    // VirtualAlloc refuses an occupied address; never alter an existing mapping.
    auto* page = VirtualAlloc(reinterpret_cast<void*>(0x144BD0000), 65536, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    if (page != reinterpret_cast<void*>(0x144BD0000))
    {
        if (page) VirtualFree(page, 0, MEM_RELEASE);
        std::fputs("fixture address unavailable; no test executed\n", stderr); return 2;
    }
    int result = 0;
    try { positive_and_error_preservation(); refusal_cases(); post_refusal_and_original_exception(); post_identity_cases(); }
    catch (const std::exception& error) { std::fprintf(stderr, "FAIL: %s\n", error.what()); result = 1; }
    VirtualFree(page, 0, MEM_RELEASE);
    if (!result) std::fputs("Original synthetic observer fixture PASS; not engine evidence\n", stderr);
    return result;
}
