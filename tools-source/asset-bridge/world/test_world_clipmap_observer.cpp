// Prepared native harness, NOT compiled/run in the source-only task.
// Owns only synthetic buffers and a newly reserved page in this test process.
// Fixture seeding deliberately bypasses arm signatures; emitted signature_checked
// stays false. These records must never be accepted as an engine observation.
#include "world_clipmap_observer.hpp"
#include <stdexcept>
#include <string>
#include <io.h>
#include <fcntl.h>

namespace w = zonetool::iw7::world_clip_observer;

void check(bool value, const char* message)
{
    if (!value) throw std::runtime_error(message);
}

// Capture actual fwrite bytes without modifying the production emitter. The
// outer reviewed job still owns the hard deadline if a broken emitter blocks.
class output_capture
{
    HANDLE reader_ = nullptr;
    int saved_ = -1;
    int mode_ = -1;
public:
    unsigned records = 0;
    std::size_t largest = 0;
    output_capture()
    {
        HANDLE writer = nullptr;
        check(CreatePipe(&reader_, &writer, nullptr, 16384) != 0, "capture pipe");
        const int descriptor = _open_osfhandle(reinterpret_cast<intptr_t>(writer), _O_WRONLY | _O_BINARY);
        if (descriptor < 0) { CloseHandle(writer); CloseHandle(reader_); throw std::runtime_error("capture descriptor"); }
        std::fflush(stdout);
        saved_ = _dup(_fileno(stdout));
        if (saved_ < 0 || _dup2(descriptor, _fileno(stdout)) != 0)
        {
            if (saved_ >= 0) _close(saved_);
            _close(descriptor); CloseHandle(reader_); throw std::runtime_error("capture redirect");
        }
        _close(descriptor);
        mode_ = _setmode(_fileno(stdout), _O_BINARY);
        _setmode(saved_, _O_BINARY); // replay byte counts must not gain CRLF translation
    }
    output_capture(const output_capture&) = delete;
    output_capture& operator=(const output_capture&) = delete;
    ~output_capture()
    {
        std::fflush(stdout);
        _dup2(saved_, _fileno(stdout));
        if (mode_ >= 0) _setmode(_fileno(stdout), mode_);
        _close(saved_); CloseHandle(reader_);
    }
    std::string take(bool expected)
    {
        std::fflush(stdout);
        DWORD available = 0;
        check(PeekNamedPipe(reader_, nullptr, 0, nullptr, &available, nullptr) != 0, "capture available");
        check(expected ? available > 0 && available <= w::output_limit : available == 0, "actual output bound/count");
        if (!expected) return {};
        std::array<char, w::output_limit> bytes{};
        DWORD received = 0;
        check(ReadFile(reader_, bytes.data(), available, &received, nullptr) && received == available, "capture read");
        std::string value(bytes.data(), received);
        check(value.rfind("WORLD_CLIPMAP_OBSERVATION {", 0) == 0 && value.back() == '\n' &&
            value.find('\n') == value.size() - 1, "exactly one complete observation line");
        check(value.find("\"runtime_ready\":false") != std::string::npos, "synthetic runtime boundary");
        // Replay exactly the captured line for the independent Python JSON check.
        check(_write(saved_, value.data(), static_cast<unsigned>(value.size())) == static_cast<int>(value.size()), "capture replay");
        ++records; if (value.size() > largest) largest = value.size();
        return value;
    }
};

void expect_record(output_capture& capture, const char* status, const char* reason = nullptr)
{
    const auto line = capture.take(true);
    check(line.find(std::string("\"status\":\"") + status + "\"") != std::string::npos, "record status");
    check(line.find("\"signature_checked\":false") != std::string::npos, "fixture signatures must remain false");
    check(line.find("\"collision_validated\":false") != std::string::npos, "fixture collision boundary");
    check(line.find(std::string("\"reads\":") + std::to_string(w::record.reads) + ',') != std::string::npos &&
        w::record.reads <= w::read_limit, "emitted read accounting");
    if (reason) check(line.find(std::string("\"reason\":\"") + reason + "\"") != std::string::npos, "record reason");
    const auto reads = w::record.reads;
    w::emit(); capture.take(false);
    check(w::record.reads == reads && w::phase.load() == 3, "duplicate emit altered observation");
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

void positive_and_error_preservation(output_capture& capture)
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
    expect_record(capture, "observed", "none");
    const auto reads = w::record.reads;
    w::forward(22, &f.slot, [&] { ++calls; return f.slot; }, pointer);
    check(calls == 2 && w::phase.load() == 3 && w::record.reads == reads, "second callback did not forward exactly once");
    capture.take(false);
}

void refusal_cases(output_capture& capture)
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
        const auto result = w::forward(22, &f.slot, [&] { ++calls; return f.slot; }, pointer);
        check(calls == 1 && result == f.slot && !w::record.post_ok && w::record.refusal &&
            w::record.reads <= w::read_limit, "refusal prevented original or exceeded budget");
        expect_record(capture, "refused");
    }
}

void post_refusal_and_original_exception(output_capture& capture)
{
    fixture f; seed_fixture_session(); int calls = 0;
    w::forward(22, &f.slot, [&] { ++calls; return f.slot; }, pointer);
    check(calls == 1 && !w::record.post_ok, "missing post fixup accepted");
    expect_record(capture, "refused", "post_fixup_relation");
    seed_fixture_session(); calls = 0;
    try
    {
        w::forward(22, &f.slot, [&]() -> std::uintptr_t { ++calls; throw std::runtime_error("original"); }, pointer);
        check(false, "original exception swallowed");
    }
    catch (const std::runtime_error& error) { check(std::string(error.what()) == "original", "exception changed"); }
    check(calls == 1 && w::record.original_threw, "original exception retried or lost");
    expect_record(capture, "refused", "original_exception");
    seed_fixture_session(); calls = 0;
    w::forward(3, &f.slot, [&] { ++calls; return f.slot; }, pointer);
    check(calls == 1 && w::record.reads == 0 && !w::emitted.load(), "unselected asset inspected");
    capture.take(false);
    check(!w::finish(), "unseen clipmap accepted");
    expect_record(capture, "refused", "no_clipmap_observed");
}

void post_identity_cases(output_capture& capture)
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
        expect_record(capture, "refused");
    }
}

void nested_and_first_mismatch(output_capture& capture)
{
    fixture f; seed_fixture_session(); int outer = 0, inner = 0;
    const auto result = w::forward(22, &f.slot, [&]
    {
        ++outer; const auto reads = w::record.reads;
        const auto nested = w::forward(22, &f.slot, [&] { ++inner; return f.slot; }, pointer);
        check(nested == f.slot && w::record.reads == reads && !w::emitted.load(), "nested callback claimed observation");
        f.fixup_owned_fixture(); return f.slot;
    }, pointer);
    check(result == f.slot && outer == 1 && inner == 1 && w::record.post_ok, "nested forwarding contract");
    expect_record(capture, "observed", "none");
    fixture mismatch; seed_fixture_session(); int calls = 0; w::record.expected[5] = 'X';
    w::forward(22, &mismatch.slot, [&] { ++calls; return mismatch.slot; }, pointer);
    expect_record(capture, "refused", "first_clipmap_name_mismatch");
    const auto reads = w::record.reads;
    w::record.expected[5] = 'o'; // fixture-only repair: a later match must still be ignored
    w::forward(22, &mismatch.slot, [&] { ++calls; mismatch.fixup_owned_fixture(); return mismatch.slot; }, pointer);
    check(calls == 2 && w::record.reads == reads && !w::record.post_ok, "later matching CLIPMAP was searched");
    capture.take(false);
}

void read_boundaries(output_capture& capture)
{
    std::array<unsigned char, w::read_limit> source{};
    std::array<unsigned char, w::read_limit> copy{}; source.fill(0x5a);
    seed_fixture_session();
    check(w::read(reinterpret_cast<std::uintptr_t>(source.data()), copy.data(), copy.size()) &&
        copy == source && w::record.reads == w::read_limit, "exact 2 KiB read refused or mischarged");
    unsigned char canary = 0xa5;
    check(!w::read(reinterpret_cast<std::uintptr_t>(source.data()), &canary, 1) &&
        canary == 0xa5 && w::record.reads == w::read_limit, "2 KiB plus one touched memory");
    fixture f; int calls = 0;
    const auto result = w::forward(22, &f.slot, [&] { ++calls; return f.slot; }, pointer);
    check(calls == 1 && result == f.slot, "exhausted read budget prevented forwarding");
    expect_record(capture, "refused", "read_budget_or_address");
    seed_fixture_session();
    check(!w::read(reinterpret_cast<std::uintptr_t>(source.data()), &canary, w::read_limit + 1) &&
        canary == 0xa5 && w::record.reads == 0, "oversized read was attempted");
    check(!w::read((std::numeric_limits<std::uintptr_t>::max)(), &canary, 1) &&
        canary == 0xa5 && w::record.reads == 0, "overflow address was attempted");
    check(!w::read(1, &canary, 1) && w::record.reads == 1, "failed read was not charged");
    w::emit(); expect_record(capture, "refused", "read_budget_or_address");
}

void output_boundaries(output_capture& capture)
{
    struct guarded { unsigned char before = 0xa5; char data[w::output_limit]{}; unsigned char after = 0x5a; } buffer;
    std::size_t used = 0;
    w::append(buffer.data, used, "%0*d", static_cast<int>(w::output_limit - 1), 0);
    check(used == w::output_limit - 1 && buffer.data[w::output_limit - 1] == 0, "append exact available bytes");
    w::append(buffer.data, used, "X");
    check(used == w::output_limit && buffer.before == 0xa5 && buffer.after == 0x5a &&
        buffer.data[w::output_limit - 1] == 0, "append overflow escaped fixed buffer");
    w::append(buffer.data, used, "must not write");
    check(buffer.before == 0xa5 && buffer.after == 0x5a && used == w::output_limit, "append after refusal wrote");

    seed_fixture_session();
    std::memset(w::record.expected, 'A', sizeof(w::record.expected) - 1);
    std::memset(w::record.root_class, 'B', sizeof(w::record.root_class) - 1);
    std::memset(w::record.digest, 'f', sizeof(w::record.digest) - 1);
    w::record.reads = w::read_limit; w::record.size = w::blob_limit;
    w::record.root_section = w::record.root_offset = w::record.flags_before = w::record.flags_after = UINT32_MAX;
    w::record.name_count = w::record.tag_count = INT32_MIN;
    for (auto& s : w::record.sections) s = {UINT32_MAX, UINT32_MAX, UINT32_MAX, UINT32_MAX, UINT32_MAX, UINT32_MAX, UINT32_MAX};
    w::fail("synthetic_max_width"); w::emit(); expect_record(capture, "refused", "synthetic_max_width");

    seed_fixture_session();
    // Deliberately impossible production diagnostic to force the defensive fallback.
    std::array<char, w::output_limit + 1> oversized{}; oversized.fill('R'); oversized.back() = 0;
    w::record.refusal = oversized.data(); w::emit();
    const auto fallback = capture.take(true);
    check(fallback == "WORLD_CLIPMAP_OBSERVATION {\"status\":\"refused\",\"reason\":\"metadata_budget\",\"runtime_ready\":false}\n",
        "oversized record was not replaced with bounded refusal");
    w::emit(); capture.take(false);
    w::record.refusal = nullptr;
}

int main()
{
    if (_setmode(_fileno(stdout), _O_BINARY) < 0)
    { std::fputs("binary transcript unavailable; no test executed\n", stderr); return 2; }
    // VirtualAlloc refuses an occupied address; never alter an existing mapping.
    auto* page = VirtualAlloc(reinterpret_cast<void*>(0x144BD0000), 65536, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    if (page != reinterpret_cast<void*>(0x144BD0000))
    {
        if (page) VirtualFree(page, 0, MEM_RELEASE);
        std::fputs("fixture address unavailable; no test executed\n", stderr); return 2;
    }
    int result = 0;
    try
    {
        unsigned records = 0; std::size_t largest = 0;
        {
            output_capture capture;
            positive_and_error_preservation(capture); refusal_cases(capture);
            post_refusal_and_original_exception(capture); post_identity_cases(capture);
            nested_and_first_mismatch(capture); read_boundaries(capture); output_boundaries(capture);
            records = capture.records; largest = capture.largest;
        }
        check(records == 24 && largest <= w::output_limit, "complete harness record coverage");
        std::printf("WORLD_CLIPMAP_HARNESS {\"schema\":\"iw7.world-clipmap-harness/1\",\"records\":%u,"
            "\"largest_record_bytes\":%llu,\"read_limit\":2048,\"output_limit\":4096,"
            "\"fixture_only\":true,\"engine_observed\":false,\"status\":\"passed\"}\n",
            records, static_cast<unsigned long long>(largest));
    }
    catch (const std::exception& error) { std::fprintf(stderr, "FAIL: %s\n", error.what()); result = 1; }
    VirtualFree(page, 0, MEM_RELEASE);
    if (!result) std::fputs("Original synthetic observer fixture PASS; not engine evidence\n", stderr);
    return result;
}
