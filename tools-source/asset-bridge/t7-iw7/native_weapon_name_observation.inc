// Unused opt-in support for a future audited startup scope. No new hook/load/lookup.
// Requires the unchanged C2 typed-name SEH getter and error guard before this module.
static_assert(ASSET_TYPE_WEAPON == 0x17 && ASSET_TYPE_WEAPONDEF == 0x18 &&
    ASSET_TYPE_WEAPON_VARIANT == 0x19 && ASSET_TYPE_WEAPON_FULL == 0x1A && sizeof(XAssetHeader) == 8);
static std::atomic_bool weapon_names_enabled{false}, weapon_names_started{false};
static std::atomic_bool weapon_names_finished{false}, weapon_names_overflow{false}, weapon_names_write_failed{false};
static std::atomic<unsigned int> weapon_names_calls{0}, weapon_names_returns{0}, weapon_names_sequence{0};
static constexpr unsigned int weapon_names_max_calls = 8, weapon_names_name_bytes = 96;

struct weapon_names_call
{
    bool selected = false;
    unsigned int id = 0, type = 0;
};

template <typename... Args>
static bool weapon_names_log(const char* format, Args... args) noexcept
{
    const c2_add_error_guard restore;
    char line[512]{};
    const auto prefix = std::snprintf(line, sizeof(line),
        "[T7_WEAPON_NAMES] schema=iw7.t7-weapon-name-observation/1 seq=%u tid=%lu ",
        weapon_names_sequence.fetch_add(1), GetCurrentThreadId());
    if (prefix <= 0 || static_cast<size_t>(prefix) >= sizeof(line))
    { weapon_names_write_failed.store(true); return false; }
    const auto body = std::snprintf(line + prefix, sizeof(line) - prefix, format, args...);
    if (body <= 0 || static_cast<size_t>(body) >= sizeof(line) - prefix)
    { weapon_names_write_failed.store(true); return false; }
    DWORD written = 0;
    const auto length = static_cast<DWORD>(prefix + body);
    const bool ok = WriteFile(GetStdHandle(STD_ERROR_HANDLE), line, length, &written, nullptr) && written == length;
    if (!ok) weapon_names_write_failed.store(true);
    return ok;
}

// Caller must establish the fresh qualified scope and a separate runtime GO.
// No CLI, build profile or current runtime calls this function.
[[maybe_unused]] static bool weapon_names_enable() noexcept
{
    const c2_add_error_guard restore;
    if (weapon_names_started.exchange(true)) return false;
    if (!weapon_names_log("kind=enabled scope=historical_f23_startup weapon_presence=unknown\n")) return false;
    weapon_names_enabled.store(true);
    return true;
}

[[maybe_unused]] static weapon_names_call weapon_names_begin(XAsset& asset, void* caller) noexcept
{
    const c2_add_error_guard restore;
    weapon_names_call call;
    const auto type = static_cast<unsigned int>(asset.type);
    if (!weapon_names_enabled.load() || type < 0x17 || type > 0x1A) return call;
    auto current = weapon_names_calls.load();
    for (unsigned int attempt = 0; attempt < 8 && current < weapon_names_max_calls; ++attempt)
        if (weapon_names_calls.compare_exchange_weak(current, current + 1))
        { call.selected = true; call.id = current; call.type = type; break; }
    if (!call.selected)
    {
        if (!weapon_names_overflow.exchange(true)) weapon_names_log("kind=overflow\n");
        return call;
    }
    const char* name = nullptr;
    const char* state = "getter_exception";
    unsigned char copied_name[weapon_names_name_bytes]{};
    char hex[weapon_names_name_bytes * 2 + 1]{};
    unsigned int length = 0, nul = 0, reference = 0;
    if (c2_add_get_name(&asset, &name))
    {
        state = name ? "unreadable" : "null";
        SIZE_T copied = 0;
        if (name && ReadProcessMemory(GetCurrentProcess(), name, copied_name, sizeof(copied_name), &copied) &&
            copied == sizeof(copied_name))
        {
            static constexpr char digits[] = "0123456789abcdef";
            for (; length < sizeof(copied_name) && copied_name[length]; ++length)
            {
                hex[length * 2] = digits[copied_name[length] >> 4];
                hex[length * 2 + 1] = digits[copied_name[length] & 15];
            }
            nul = length < sizeof(copied_name);
            reference = length && copied_name[0] == ',';
            state = nul ? "read" : "prefix";
        }
    }
    weapon_names_log("kind=enter call=%u type=%u read=%s length=%u nul=%u reference=%u name_hex=%s caller=%p header_present=%u\n",
        call.id, call.type, state, length, nul, reference, length ? hex : "-", caller,
        static_cast<unsigned int>(asset.header.data != nullptr));
    return call;
}

// Original DB-add invocation belongs to the existing caller and stays outside
// every SEH/exception boundary, exactly once. Only its scalar return is observed.
[[maybe_unused]] static void weapon_names_end(const weapon_names_call& call, XAssetHeader result) noexcept
{
    const c2_add_error_guard restore;
    if (!call.selected || call.id >= weapon_names_max_calls) return;
    const auto bit = 1u << call.id;
    if (weapon_names_returns.fetch_or(bit) & bit)
    { weapon_names_write_failed.store(true); return; }
    weapon_names_log("kind=return call=%u type=%u result_present=%u\n", call.id, call.type,
        static_cast<unsigned int>(result.data != nullptr));
}

// Caller supplies a proven observation boundary; this function does not wait,
// retain engine allocations, resolve defaults or declare the scope complete.
[[maybe_unused]] static void weapon_names_finish() noexcept
{
    const c2_add_error_guard restore;
    weapon_names_enabled.store(false);
    if (!weapon_names_started.load() || weapon_names_finished.exchange(true)) return;
    unsigned int returned = 0;
    const auto mask = weapon_names_returns.load();
    for (unsigned int i = 0; i < weapon_names_max_calls; ++i) returned += (mask >> i) & 1u;
    weapon_names_log("kind=finished entered=%u returned=%u overflow=%u write_failed=%u\n",
        weapon_names_calls.load(), returned, static_cast<unsigned int>(weapon_names_overflow.load()),
        static_cast<unsigned int>(weapon_names_write_failed.load()));
}
