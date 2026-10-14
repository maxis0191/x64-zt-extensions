// C2 observes only the existing DB_AddXAsset call; no new detour or asset lookup.
static_assert(ASSET_TYPE_RAWFILE == 0x2F && sizeof(XAssetHeader) == 8);
static std::atomic_bool c2_add_enabled{false};
static std::atomic_bool c2_add_refusal{false};
static std::atomic<unsigned int> c2_add_calls{0}, c2_add_sequence{0};
static constexpr char c2_add_target[] = "ui/uieditor/widgets/attachmentnamesdisplay.lua";
static constexpr char c2_add_target_hex[] = "75692f7569656469746f722f776964676574732f6174746163686d656e746e616d6573646973706c61792e6c7561";

struct c2_add_error_guard
{
    DWORD value = GetLastError();
    int crt_value = errno;
    ~c2_add_error_guard() { errno = crt_value; SetLastError(value); }
};

struct c2_add_call
{
    bool selected = false;
    unsigned int id = 0;
    bool reference_prefix = false;
};

struct c2_add_fastfile
{
    const char* state = "pointer_unreadable";
    unsigned int nul = 0;
    char hex[129]{};
};

// This global is already read by db_finish_load_x_file_stub. It is not an
// atomic snapshot or proof that this file supplies the requested asset.
static c2_add_fastfile c2_add_fastfile_context() noexcept
{
    const c2_add_error_guard restore;
    c2_add_fastfile out;
    const char* pointer = nullptr;
    SIZE_T copied = 0;
    if (!ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<void*>(0x1468FD4A8),
        &pointer, sizeof(pointer), &copied) || copied != sizeof(pointer)) return out;
    if (!pointer) { out.state = "null"; return out; }
    unsigned char name[64]{};
    copied = 0;
    if (!ReadProcessMemory(GetCurrentProcess(), pointer, name, sizeof(name), &copied) ||
        copied != sizeof(name)) { out.state = "name_unreadable"; return out; }
    static constexpr char digits[] = "0123456789abcdef";
    unsigned int length = 0;
    for (; length < sizeof(name) && name[length]; ++length)
    {
        out.hex[length * 2] = digits[name[length] >> 4];
        out.hex[length * 2 + 1] = digits[name[length] & 15];
    }
    out.nul = length < sizeof(name);
    out.state = out.nul ? "read" : "prefix";
    return out;
}

// A record is submitted once, with no retry, stream lock or lock held across
// the original call. Short/interrupted output remains incomplete evidence.
template <typename... Args>
static void c2_add_log(const char* format, Args... args) noexcept
{
    const c2_add_error_guard restore;
    char line[512]{};
    const auto prefix = std::snprintf(line, sizeof(line),
        "[T7_ZM_ADD] schema=iw7.t7-zm-add-observation/1 seq=%u tid=%lu ",
        c2_add_sequence.fetch_add(1), GetCurrentThreadId());
    if (prefix <= 0 || static_cast<size_t>(prefix) >= sizeof(line)) return;
    const auto body = std::snprintf(line + prefix, sizeof(line) - prefix, format, args...);
    if (body <= 0 || static_cast<size_t>(body) >= sizeof(line) - prefix) return;
    DWORD written = 0;
    WriteFile(GetStdHandle(STD_ERROR_HANDLE), line, static_cast<DWORD>(prefix + body), &written, nullptr);
}

// Only this added read-only getter is guarded; never catch the original DB add.
// Keep the SEH leaf free of C++ objects requiring unwinding.
static bool c2_add_get_name(XAsset* asset, const char** name) noexcept
{
    __try { *name = get_asset_name(asset); return true; }
    __except (EXCEPTION_EXECUTE_HANDLER) { *name = nullptr; return false; }
}

static bool c2_add_exact_name(const char* name, bool& reference_prefix, const char*& refusal) noexcept
{
    const c2_add_error_guard restore;
    char first = 0;
    SIZE_T copied = 0;
    if (!name || !ReadProcessMemory(GetCurrentProcess(), name, &first, 1, &copied) || copied != 1)
    { refusal = "prefix_unreadable"; return false; }
    reference_prefix = first == ',';
    char copy[sizeof(c2_add_target) + 1]{};
    const auto length = sizeof(c2_add_target) + static_cast<size_t>(reference_prefix);
    copied = 0;
    if (!ReadProcessMemory(GetCurrentProcess(), name, copy, length, &copied) || copied != length)
    { refusal = "name_unreadable"; return false; }
    return std::memcmp(copy + static_cast<size_t>(reference_prefix), c2_add_target, sizeof(c2_add_target)) == 0;
}

static c2_add_call c2_add_begin(XAsset& asset, void* caller)
{
    const c2_add_error_guard restore;
    c2_add_call call;
    if (!c2_add_enabled.load() || asset.type != ASSET_TYPE_RAWFILE) return call;
    // Reuse the source's typed name getter; never assume a RawFile layout.
    const char* name = nullptr;
    const char* refusal = nullptr;
    if (!c2_add_get_name(&asset, &name)) refusal = "getter_exception";
    const bool exact = !refusal && c2_add_exact_name(name, call.reference_prefix, refusal);
    if (refusal && !c2_add_refusal.exchange(true))
        c2_add_log("kind=selection_refused type=47 read_state=%s target=unknown\n", refusal);
    if (!exact) return call;
    auto current = c2_add_calls.load();
    for (unsigned int attempt = 0; attempt < 8 && current < 4; ++attempt)
        if (c2_add_calls.compare_exchange_weak(current, current + 1))
        {
            call.id = current;
            call.selected = true;
            break;
        }
    if (!call.selected) return call;
    const auto ff = c2_add_fastfile_context();
    c2_add_log("kind=add_enter call=%u type=47 reference_prefix=%u name_hex=%s%s caller=%p asset=%p ff_state=%s ff_nul=%u ff_name_hex=%s ff_atomic=0\n",
        call.id, static_cast<unsigned int>(call.reference_prefix), call.reference_prefix ? "2c" : "", c2_add_target_hex, caller, asset.header.data,
        ff.state, ff.nul, ff.hex);
    return call;
}

static void c2_add_end(const c2_add_call& call, XAssetHeader result) noexcept
{
    const c2_add_error_guard restore;
    if (!call.selected) return;
    const auto ff = c2_add_fastfile_context();
    c2_add_log("kind=add_return call=%u reference_prefix=%u result=%p ff_state=%s ff_nul=%u ff_name_hex=%s ff_atomic=0\n",
        call.id, static_cast<unsigned int>(call.reference_prefix), result.data, ff.state, ff.nul, ff.hex);
}

static void c2_add_enable() noexcept
{
    const c2_add_error_guard restore;
    int count = 0;
    auto* args = CommandLineToArgvW(GetCommandLineW(), &count);
    if (!args) return;
    const bool selected = count == 3 && std::wcscmp(args[1], L"-t7-iw7-catalog") == 0 &&
        std::wcscmp(args[2], L"zm_common") == 0;
    LocalFree(args);
    if (!selected) return;
    c2_add_log("kind=enabled\n");
    c2_add_enabled.store(true);
}
