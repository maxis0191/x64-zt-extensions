// AUTHORED ONLY until a separate admitted CPP operation. No real arena/pair IO.
// SDK declarations precede the test-only redirects of the production header.
#define NOMINMAX
#include <Windows.h>
#include <array>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>

namespace fixture
{
    std::array<unsigned char, 256> pool;
    struct State
    {
        bool alloc_ok = true, release_ok = true, bad_call = false;
        unsigned allocations = 0, releases = 0, null_releases = 0, messages = 0;
        DWORD allocation_error = 0x1234, release_error = 0x5678;
        LPVOID last_released = nullptr;
    } state;
    void reset() { state = State{}; pool.fill(0xA5); }
    LPVOID WINAPI allocate(LPVOID base, SIZE_T bytes, DWORD flags, DWORD protection)
    {
        ++state.allocations;
        if (base || flags != (MEM_RESERVE | MEM_COMMIT) || protection != PAGE_READWRITE) state.bad_call = true;
        if (!state.alloc_ok || !bytes || bytes > pool.size())
        {
            SetLastError(state.allocation_error);
            return nullptr;
        }
        return pool.data();
    }
    BOOL WINAPI release(LPVOID base, SIZE_T bytes, DWORD flags)
    {
        ++state.releases;
        if (!base) ++state.null_releases;
        if (base != pool.data() || bytes != 0 || flags != MEM_RELEASE) state.bad_call = true;
        state.last_released = base;
        if (!state.release_ok) { SetLastError(state.release_error); return FALSE; }
        return TRUE;
    }
    int WINAPI message(HWND, LPCSTR, LPCSTR, UINT) { ++state.messages; return 0; }
}

#define VirtualAlloc fixture::allocate
#define VirtualFree fixture::release
#define MessageBoxA fixture::message
#include "memory.hpp"
#undef VirtualAlloc
#undef VirtualFree
#undef MessageBoxA

using Arena = zonetool::zone_memory;
using Report = zonetool::checked_memory_report;
using Failure = zonetool::checked_memory_failure;
using Release = zonetool::checked_memory_release;
using Error = zonetool::checked_memory_error;
using Tag = zonetool::checked_memory_tag;

static void need(bool condition) { if (!condition) throw std::runtime_error("Fixture condition failed"); }
template<class F> static void refuses(Failure reason, F&& action)
{
    try { action(); }
    catch (const Error& error) { need(error.reason() == reason); return; }
    throw std::runtime_error("Expected checked refusal absent");
}
static void untouched() { for (auto value : fixture::pool) need(value == 0xA5); }

static void checked_constructor_null_unwinds_without_message_or_exit()
{
    Report report;
    fixture::state.alloc_ok = false;
    refuses(Failure::allocation, [&] { Arena arena(Tag{}, 8, report); });
    need(report.bound() && report.owner() && !report.original_pool() && report.capacity() == 8);
    need(report.primary() == Failure::allocation && report.primary_error() == 0x1234);
    need(report.release() == Release::not_attempted && report.release_attempts() == 0);
    need(fixture::state.allocations == 1 && fixture::state.releases == 0);
}
static void checked_capacity_refusal_precedes_write_and_position_change()
{
    Report report;
    {
        Arena arena(Tag{}, 8, report);
        refuses(Failure::capacity, [&] { arena.manual_allocate<char>(9); });
        untouched();
        refuses(Failure::not_live, [&] { arena.allocate<char>(1); });
        need(report.primary() == Failure::capacity);
    }
    need(fixture::state.releases == 1);
}
static void checked_multiplication_overflow_refuses()
{
    Report report;
    Arena arena(Tag{}, 16, report);
    refuses(Failure::overflow, [&] { arena.manual_allocate<char>(2, (std::numeric_limits<std::size_t>::max)()); });
    untouched();
    need(report.primary() == Failure::overflow);
}
static void checked_used_and_remaining_capacity_refuse_safely()
{
    // The ordinary helper exercises corrupt-used arithmetic without corrupting
    // an actual arena's private state or treating metadata as pool authority.
    refuses(Failure::capacity, [] { zonetool::checked_memory_bytes(1, 1, 9, 8); });
    Report report;
    Arena arena(Tag{}, 7, report);
    need(arena.manual_allocate<char>(3) == reinterpret_cast<char*>(fixture::pool.data()));
    need(arena.manual_allocate<char>(3) == reinterpret_cast<char*>(fixture::pool.data()) + 3);
    refuses(Failure::capacity, [&] { arena.manual_allocate<char>(2); });
    need(fixture::pool[6] == 0xA5 && report.primary() == Failure::capacity);
}
static void checked_zero_count_preserves_legacy_null_behavior_while_live()
{
    Report report;
    Arena arena(Tag{}, 8, report);
    need(arena.manual_allocate<char>((std::numeric_limits<std::size_t>::max)(), 0) == nullptr);
    need(arena.allocate<char>(0) == nullptr);
    untouched();
    need(arena.allocate<char>() == reinterpret_cast<char*>(fixture::pool.data()));
    need(report.primary() == Failure::none);
}
static void checked_success_preserves_packed_offsets_and_zero_ranges()
{
    Report report;
    Arena arena(Tag{}, 16, report);
    auto base = reinterpret_cast<char*>(fixture::pool.data());
    need(arena.manual_allocate<char>(1) == base);
    // Raw address comparison, no unaligned typed dereference or padding.
    need(reinterpret_cast<void*>(arena.allocate<unsigned>(1)) == base + 1);
    for (std::size_t i = 0; i < 1 + sizeof(unsigned); ++i) need(fixture::pool[i] == 0);
    need(fixture::pool[1 + sizeof(unsigned)] == 0xA5);
    arena.clear();
    need(arena.duplicate_string("a") == base);
    need(std::strcmp(base, "a") == 0);
    need(arena.duplicate_string(std::string("b")) == base + 2);
}
static void checked_source_copy_refuses_pool_alias()
{
    Report report;
    Arena arena(Tag{}, 8, report);
    refuses(Failure::copy, [&] { Arena alias(arena); });
    need(fixture::state.allocations == 1 && fixture::state.releases == 0);
    need(arena.allocate<char>() == reinterpret_cast<char*>(fixture::pool.data()));
    static_assert(!std::is_copy_assignable<Arena>::value, "Mutex already deletes assignment");
}
static void checked_free_then_destructor_success_one_release()
{
    Report report;
    const void* original_owner;
    {
        Arena arena(Tag{}, 8, report);
        original_owner = &arena;
        arena.free();
        need(report.release() == Release::succeeded && report.release_result_available());
        need(report.release_result() && report.release_error() == 0);
    }
    need(fixture::state.releases == 1 && fixture::state.null_releases == 0);
    need(report.owner() == original_owner && report.original_pool() == fixture::pool.data());
    need(report.release_attempts() == 1 && report.primary() == Failure::none);
}
static void checked_free_then_destructor_failure_sticky_one_release()
{
    Report report;
    fixture::state.release_ok = false;
    {
        Arena arena(Tag{}, 8, report);
        arena.free();
        need(report.release() == Release::failed && report.release_result_available());
        need(!report.release_result() && report.release_error() == 0x5678);
        fixture::state.release_ok = true;
        fixture::state.release_error = 0x9999;
        SetLastError(0xABCD);
    }
    need(fixture::state.releases == 1 && report.release_attempts() == 1);
    need(report.release() == Release::failed && report.release_error() == 0x5678);
    need(report.original_pool() == fixture::pool.data() && !report.cleanup_exception());
}
static void checked_repeated_free_success_and_failure_never_retry_or_free_null()
{
    for (bool success : {true, false})
    {
        fixture::reset();
        fixture::state.release_ok = success;
        Report report;
        {
            Arena arena(Tag{}, 8, report);
            arena.free(); arena.free(); arena.free();
            need(report.release_attempts() == 1);
        }
        need(fixture::state.releases == 1 && fixture::state.null_releases == 0);
        need(fixture::state.last_released == fixture::pool.data());
        need(report.release() == (success ? Release::succeeded : Release::failed));
    }
}
static void checked_terminal_operations_refuse_before_any_use()
{
    for (bool success : {true, false})
    {
        fixture::reset();
        fixture::state.release_ok = success;
        Report report;
        Arena arena(Tag{}, 8, report);
        arena.free();
        refuses(Failure::not_live, [&] { arena.allocate<char>(0); });
        refuses(Failure::not_live, [&] { arena.manual_allocate<char>(0, 0); });
        refuses(Failure::not_live, [&] { arena.clear(); });
        refuses(Failure::not_live, [&] { arena.print_statistics(); });
        refuses(Failure::not_live, [&] { arena.duplicate_string(reinterpret_cast<const char*>(1)); });
        refuses(Failure::not_live, [&] { arena.duplicate_string(std::string("unused")); });
        refuses(Failure::copy, [&] { Arena alias(arena); });
        untouched();
        need(fixture::state.releases == 1 && report.primary() == Failure::none);
    }
    // A primary allocation refusal also poisons all uses until cleanup.
    fixture::reset();
    Report report;
    Arena arena(Tag{}, 1, report);
    refuses(Failure::capacity, [&] { arena.manual_allocate<char>(2); });
    refuses(Failure::not_live, [&] { arena.allocate<char>(0); });
    refuses(Failure::not_live, [&] { arena.clear(); });
    refuses(Failure::copy, [&] { Arena alias(arena); });
    need(fixture::state.releases == 0);
}
static void checked_report_survives_destruction_preserves_primary_and_release_error()
{
    Report report;
    fixture::state.release_ok = false;
    const void* owner = nullptr;
    try
    {
        Arena arena(Tag{}, 8, report);
        owner = &arena;
        arena.manual_allocate<char>(9);
        throw std::runtime_error("Expected primary refusal absent");
    }
    catch (const Error& error) { need(error.reason() == Failure::capacity); }
    need(report.primary() == Failure::capacity && report.primary_error() == 0);
    need(report.release() == Release::failed && report.release_error() == 0x5678);
    need(report.owner() == owner && report.original_pool() == fixture::pool.data());
    need(report.release_attempts() == 1 && fixture::state.releases == 1);
    fixture::state.release_ok = true;
    SetLastError(0xEEEE);
    refuses(Failure::report_reuse, [&] { Arena another(Tag{}, 8, report); });
    need(fixture::state.allocations == 1 && fixture::state.releases == 1);
    need(report.release() == Release::failed && report.release_error() == 0x5678);
}

int main()
{
    struct Case { const char* name; void (*run)(); };
    const Case cases[] = {
        {"checked_constructor_null_unwinds_without_message_or_exit", checked_constructor_null_unwinds_without_message_or_exit},
        {"checked_capacity_refusal_precedes_write_and_position_change", checked_capacity_refusal_precedes_write_and_position_change},
        {"checked_multiplication_overflow_refuses", checked_multiplication_overflow_refuses},
        {"checked_used_and_remaining_capacity_refuse_safely", checked_used_and_remaining_capacity_refuse_safely},
        {"checked_zero_count_preserves_legacy_null_behavior_while_live", checked_zero_count_preserves_legacy_null_behavior_while_live},
        {"checked_success_preserves_packed_offsets_and_zero_ranges", checked_success_preserves_packed_offsets_and_zero_ranges},
        {"checked_source_copy_refuses_pool_alias", checked_source_copy_refuses_pool_alias},
        {"checked_free_then_destructor_success_one_release", checked_free_then_destructor_success_one_release},
        {"checked_free_then_destructor_failure_sticky_one_release", checked_free_then_destructor_failure_sticky_one_release},
        {"checked_repeated_free_success_and_failure_never_retry_or_free_null", checked_repeated_free_success_and_failure_never_retry_or_free_null},
        {"checked_terminal_operations_refuse_before_any_use", checked_terminal_operations_refuse_before_any_use},
        {"checked_report_survives_destruction_preserves_primary_and_release_error", checked_report_survives_destruction_preserves_primary_and_release_error},
    };
    unsigned passed = 0;
    for (const auto& test : cases)
    {
        fixture::reset();
        try
        {
            test.run();
            need(!fixture::state.bad_call && fixture::state.messages == 0 && fixture::state.null_releases == 0);
            ++passed;
            std::cout << "PASS " << test.name << '\n';
        }
        catch (const std::exception& error) { std::cerr << "FAIL " << test.name << ": " << error.what() << '\n'; return 1; }
    }
    std::cout << "IW7_PAIR_CHECKED_MEMORY_FIXTURE=12\n";
    return passed == 12 ? 0 : 2;
}
