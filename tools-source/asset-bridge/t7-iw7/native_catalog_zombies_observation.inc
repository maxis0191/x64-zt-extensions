// Opt-in source overlay for one zm_common catalogue. No substitute assets or extra DB calls.
// Inlined inside zonetool::t7; ABI comes from owner x64-zt fab9358, functions.hpp.
static_assert(ASSET_TYPE_RAWFILE == 0x2F && sizeof(XAssetHeader) == 8);
static_assert(sizeof(XZoneInfo) == 40 && sizeof(qboolean) == 4);
using zm_find_signature = XAssetHeader(XAssetType, const char*, bool, int);
using zm_load_signature = void(XZoneInfo*, unsigned int, qboolean, qboolean);
static_assert(std::is_same_v<decltype(DB_FindXAssetHeader.get()), zm_find_signature*>);
static_assert(std::is_same_v<decltype(DB_LoadXAssets.get()), zm_load_signature*>);

enum class zm_observation_phase : unsigned int
{
    installed, start, handle_params, catalogue, wait_enter, wait_return,
    load_enter, load_return, finish_enter, finish_return, zone_return, published,
    donor_load_enter, donor_load_return
};
static std::atomic_bool zm_observation_enabled{false};
static std::atomic<unsigned int> zm_observation_last_phase{0}, zm_observation_seen{0};
static std::atomic<unsigned int> zm_observation_general_bytes{0}, zm_observation_raw_bytes{0};
static std::atomic<unsigned int> zm_observation_loads{0}, zm_observation_raw_calls{0};
static std::atomic<unsigned int> zm_observation_sequence{0};
static utils::hook::detour zm_observation_find_hook, zm_observation_load_hook;
static constexpr char zm_observation_raw_name[] = "ui/uieditor/widgets/attachmentnamesdisplay.lua";

// Logging/guard reads must not change the last-error state passed to the engine.
struct zm_observation_error_guard
{
    DWORD value = GetLastError();
    int crt_value = errno;
    ~zm_observation_error_guard() { errno = crt_value; SetLastError(value); }
};

static bool zm_observation_slot(std::atomic<unsigned int>& counter, const unsigned int limit) noexcept
{
    auto current = counter.load();
    for (unsigned int attempt = 0; attempt < 8 && current < limit; ++attempt)
        if (counter.compare_exchange_weak(current, current + 1)) return true;
    return false;
}

template <typename... Args>
static void zm_observation_log(const bool raw, const char* format, Args... args) noexcept
{
    if (!zm_observation_enabled.load()) return;
    const zm_observation_error_guard restore;
    char line[512]{};
    const auto prefix = std::snprintf(line, sizeof(line),
        "[T7_ZM_OBS] schema=iw7.t7-zm-observation/1 seq=%u tid=%lu ",
        zm_observation_sequence.fetch_add(1), GetCurrentThreadId());
    if (prefix <= 0 || static_cast<size_t>(prefix) >= sizeof(line)) return;
    const auto body = std::snprintf(line + prefix, sizeof(line) - prefix, format, args...);
    if (body <= 0 || static_cast<size_t>(body) >= sizeof(line) - prefix) return;
    const auto length = static_cast<unsigned int>(prefix + body);
    const auto cost = length + 1; // reserve the possible Windows text-stream LF -> CRLF byte
    auto& counter = raw ? zm_observation_raw_bytes : zm_observation_general_bytes;
    const unsigned int limit = raw ? 1024 : 7168; // raw lookup has its own reserved budget
    if (counter.fetch_add(cost) > limit - cost) return;
    std::fwrite(line, 1, length, stderr);
    std::fflush(stderr);
}

static void zm_observation_phase_event(const zm_observation_phase value) noexcept
{
    if (!zm_observation_enabled.load()) return;
    const auto phase = static_cast<unsigned int>(value);
    zm_observation_last_phase.store(phase);
    if (zm_observation_seen.fetch_or(1u << phase) & (1u << phase)) return;
    zm_observation_log(false, "kind=phase phase=%u\n", phase);
}

static bool zm_observation_exact_raw_name(const char* name) noexcept
{
    const zm_observation_error_guard restore;
    char copy[sizeof(zm_observation_raw_name)]{};
    SIZE_T copied = 0;
    return name && ReadProcessMemory(GetCurrentProcess(), name, copy, sizeof(copy), &copied) &&
        copied == sizeof(copy) && std::memcmp(copy, zm_observation_raw_name, sizeof(copy)) == 0;
}

static XAssetHeader zm_observation_find(XAssetType type, const char* name, bool error_if_missing, int wait_time)
{
    const auto entry_error = GetLastError();
    const auto entry_errno = errno;
    const bool selected = zm_observation_enabled.load() && type == ASSET_TYPE_RAWFILE &&
        zm_observation_exact_raw_name(name) && zm_observation_slot(zm_observation_raw_calls, 4);
    if (selected)
        zm_observation_log(true, "kind=raw_enter phase=%u caller=%p type=47 error=%u wait=%d\n",
            zm_observation_last_phase.load(), _ReturnAddress(), static_cast<unsigned int>(error_if_missing), wait_time);
    errno = entry_errno; SetLastError(entry_error);
    const auto result = zm_observation_find_hook.invoke<XAssetHeader>(type, name, error_if_missing, wait_time);
    const zm_observation_error_guard restore_result;
    if (selected)
        zm_observation_log(true, "kind=raw_return phase=%u result=%p\n", zm_observation_last_phase.load(), result.data);
    return result;
}

// Copy at most two 40-byte request headers and 64 bytes per name. No FF or RawFile payload read.
static void zm_observation_zone_row(XZoneInfo* zones, const unsigned int index) noexcept
{
    const zm_observation_error_guard restore;
    XZoneInfo row{};
    SIZE_T copied = 0;
    const auto address = reinterpret_cast<uintptr_t>(zones);
    const auto offset = static_cast<uintptr_t>(index) * sizeof(row);
    if (!zones || address > UINTPTR_MAX - offset ||
        !ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<void*>(address + offset), &row, sizeof(row), &copied) ||
        copied != sizeof(row))
    {
        zm_observation_log(false, "kind=zone index=%u status=unreadable\n", index);
        return;
    }
    unsigned char name[64]{};
    char hex[129]{};
    copied = 0;
    const bool readable = row.name && ReadProcessMemory(GetCurrentProcess(), row.name, name, sizeof(name), &copied) &&
        copied == sizeof(name);
    static constexpr char digits[] = "0123456789abcdef";
    unsigned int length = 0;
    if (readable)
        for (; length < sizeof(name) && name[length]; ++length)
        {
            hex[2 * length] = digits[name[length] >> 4];
            hex[2 * length + 1] = digits[name[length] & 15];
        }
    zm_observation_log(false, "kind=zone index=%u status=%s nul=%u name_hex=%s alloc=%llu free=%llu alloc_slot=%llu free_slot=%llu\n",
        index, readable ? "read" : "unreadable", static_cast<unsigned int>(readable && length < sizeof(name)), hex,
        static_cast<unsigned long long>(row.allocFlags), static_cast<unsigned long long>(row.freeFlags),
        static_cast<unsigned long long>(row.allocSlot), static_cast<unsigned long long>(row.freeSlot));
}

static void zm_observation_load(XZoneInfo* zones, unsigned int count, qboolean sync, qboolean suppress_sync)
{
    const auto entry_error = GetLastError();
    const auto entry_errno = errno;
    const bool selected = zm_observation_enabled.load() && zm_observation_slot(zm_observation_loads, 4);
    zm_observation_phase_event(zm_observation_phase::load_enter);
    if (selected)
    {
        zm_observation_log(false, "kind=load_enter phase=%u caller=%p count=%u sync=%d suppress=%d\n",
            zm_observation_last_phase.load(), _ReturnAddress(), count, static_cast<int>(sync), static_cast<int>(suppress_sync));
        for (unsigned int i = 0; i < count && i < 2; ++i) zm_observation_zone_row(zones, i);
    }
    errno = entry_errno; SetLastError(entry_error);
    zm_observation_load_hook.invoke<void>(zones, count, sync, suppress_sync);
    const zm_observation_error_guard restore_result;
    zm_observation_phase_event(zm_observation_phase::load_return);
    if (selected)
    {
        zm_observation_log(false, "kind=load_return phase=%u\n", zm_observation_last_phase.load());
    }
}

static void zm_observation_install()
{
    const zm_observation_error_guard restore;
    int count = 0;
    auto* args = CommandLineToArgvW(GetCommandLineW(), &count);
    if (!args) return;
    const bool selected = count == 3 && std::wcscmp(args[1], L"-t7-iw7-catalog") == 0 &&
        std::wcscmp(args[2], L"zm_common") == 0;
    LocalFree(args);
    if (!selected) return;
    const auto module = GetModuleHandleW(L"BlackOps3_UnrankedDedicatedServer.exe");
    if (game::get_mode() != game::t7 || reinterpret_cast<uintptr_t>(module) != 0x140000000ULL)
        throw std::runtime_error("Zombies observer requires the pinned T7 module/base");
    for (const auto address : {0x1401D5FB0ULL, 0x1401D8740ULL})
    {
        MEMORY_BASIC_INFORMATION region{};
        const auto page = VirtualQuery(reinterpret_cast<void*>(address), &region, sizeof(region));
        const auto start = reinterpret_cast<uintptr_t>(region.BaseAddress);
        const auto protection = region.Protect & 0xff;
        if (page != sizeof(region) || region.AllocationBase != module || region.State != MEM_COMMIT ||
            (region.Protect & PAGE_GUARD) || (protection != PAGE_EXECUTE && protection != PAGE_EXECUTE_READ &&
            protection != PAGE_EXECUTE_READWRITE && protection != PAGE_EXECUTE_WRITECOPY) ||
            address < start || address - start >= region.RegionSize || region.RegionSize - (address - start) < 16)
            throw std::runtime_error("Zombies observer code site outside pinned executable mapping");
    }
    try
    {
        zm_observation_find_hook.create(0x1401D5FB0, &zm_observation_find);
        zm_observation_load_hook.create(0x1401D8740, &zm_observation_load);
    }
    catch (...)
    {
        zm_observation_load_hook.clear();
        zm_observation_find_hook.clear();
        throw;
    }
    zm_observation_enabled.store(true);
    zm_observation_phase_event(zm_observation_phase::installed);
}
