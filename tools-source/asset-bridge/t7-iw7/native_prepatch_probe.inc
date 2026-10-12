// Included once from main.cpp. Source preparation only until separately built/reviewed.
#include <array>
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cwchar>
#include <filesystem>
#include <sstream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <vector>
#include <nlohmann/json.hpp>
#include <utils/flags.hpp>

namespace zonetool::iw7
{
    void write_enemy_reference_output(const std::filesystem::path&, const std::string&);
}

namespace zonetool::t7_prepatch_probe
{
    inline constexpr char flag[] = "t7-prepatch-probe";
    inline constexpr wchar_t executable_name[] = L"BlackOps3_UnrankedDedicatedServer.exe";
    inline constexpr wchar_t output_name[] = L"t7-prepatch-probe.local.json";
    inline constexpr size_t read_limit = 4 * 1024 * 1024;
    inline constexpr size_t report_limit = 256 * 1024;
    inline constexpr size_t pdata_limit = 2 * 1024 * 1024;
    inline constexpr uintptr_t source_base = 0x140000000ull;
    inline std::filesystem::path bound_output;
    using json = nlohmann::ordered_json;
    static_assert(sizeof(void*) == 8 && sizeof(RUNTIME_FUNCTION) == 12, "T7 probe requires Windows x64");

    struct site { const char* name; uint32_t rva; uint32_t before; uint32_t length; };
    inline constexpr std::array<site, 12> sites{{
        {"DB_FindXAssetHeader", 0x1D5FB0, 0, 0x100},
        {"DB_LoadXAssets", 0x1D8740, 0, 0x100},
        {"SL_ConvertToString", 0x1632C0, 0, 0x80},
        {"boot_call", 0x502AA9, 0x20, 0x60},
        {"server_thread_ret", 0x537840, 0, 0x80},
        {"copy_info_branch_1", 0x1A18DF, 0x20, 0x60},
        {"copy_info_branch_2", 0x1A1B5B, 0x20, 0x60},
        {"image_loader_call", 0x1B1E5D, 0x20, 0x60},
        {"integrity_intact_1", 0x064DC4, 0x20, 0x60},
        {"integrity_intact_2", 0x909BD4, 0x20, 0x60},
        {"integrity_intact_3", 0x10654C1, 0x20, 0x60},
        {"integrity_split", 0x0621A8, 0x20, 0x60},
    }};

    inline void require(bool value, const char* reason)
    {
        if (!value) throw std::runtime_error(reason);
    }

    inline std::string hex(uintptr_t value)
    {
        std::ostringstream stream;
        stream << "0x" << std::hex << value;
        return stream.str();
    }

    inline std::string bytes_hex(const std::vector<uint8_t>& data)
    {
        constexpr char digits[] = "0123456789abcdef";
        std::string result;
        result.reserve(data.size() * 2);
        for (auto byte : data) { result += digits[byte >> 4]; result += digits[byte & 15]; }
        return result;
    }

    template<typename T> T field(const std::vector<uint8_t>& bytes, size_t offset = 0)
    {
        require(offset <= bytes.size() && sizeof(T) <= bytes.size() - offset, "truncated metadata field");
        T result{};
        std::memcpy(&result, bytes.data() + offset, sizeof(result));
        return result;
    }

    inline bool requested() noexcept
    try { return utils::flags::has_flag(flag); }
    catch (...) { return true; } // Flag-parser failure must reach refusal, never ordinary-mode fallback.

    // Called by main before load_binary, and rechecked at capture. No payload reads.
    inline bool validate_invocation() noexcept
    try
    {
        int argc{};
        auto argv = CommandLineToArgvW(GetCommandLineW(), &argc);
        if (!argv) return false;
        const bool exact = argc == 2 && std::wcscmp(argv[1], L"-t7-prepatch-probe") == 0;
        LocalFree(argv);
        const auto output = std::filesystem::absolute(output_name);
        std::error_code error;
        const bool exists = std::filesystem::exists(output, error);
        if (!exact || error || exists || (!bound_output.empty() && bound_output != output))
        {
            std::fputs("T7 prepatch probe requires its sole exact flag and a fresh local output.\n", stderr);
            return false;
        }
        bound_output = output;
        return true;
    }
    catch (...) { std::fputs("T7 prepatch invocation validation failed.\n", stderr); return false; }

    class image_reader
    {
    public:
        uintptr_t base{};
        size_t image_size = 1024 * 1024; // Header bootstrap ceiling; then actual validated SizeOfImage.
        size_t requested_bytes{};
        size_t returned_bytes{};

        explicit image_reader(HMODULE module) : base(reinterpret_cast<uintptr_t>(module))
        {
            require(module != nullptr, "named game module is not mapped");
        }

        json regions(uint32_t rva, size_t length) const
        {
            require(length && rva <= image_size && length <= image_size - rva, "read exceeds image bounds");
            require(base <= UINTPTR_MAX - image_size, "image address overflow");
            auto cursor = base + rva;
            const auto end = cursor + length;
            auto result = json::array();
            while (cursor < end)
            {
                require(result.size() < 128, "memory-region bound exceeded");
                MEMORY_BASIC_INFORMATION info{};
                require(VirtualQuery(reinterpret_cast<const void*>(cursor), &info, sizeof(info)) == sizeof(info),
                    "VirtualQuery failed");
                const auto begin = reinterpret_cast<uintptr_t>(info.BaseAddress);
                require(begin <= cursor && info.RegionSize && begin <= UINTPTR_MAX - info.RegionSize,
                    "invalid memory region");
                require(info.AllocationBase == reinterpret_cast<void*>(base) && info.Type == MEM_IMAGE,
                    "range belongs to a different allocation or is not an image");
                result.push_back({{"base", hex(begin)}, {"size", info.RegionSize},
                    {"allocation_base", hex(reinterpret_cast<uintptr_t>(info.AllocationBase))},
                    {"state", info.State}, {"protect", info.Protect},
                    {"allocation_protect", info.AllocationProtect}, {"type", info.Type}});
                require(begin + info.RegionSize > cursor, "non-advancing memory region");
                cursor = (std::min)(end, begin + info.RegionSize);
            }
            return result;
        }

        std::vector<uint8_t> read(uint32_t rva, size_t length)
        {
            require(requested_bytes <= read_limit && length <= read_limit - requested_bytes,
                "cumulative memory-read budget exceeded");
            const auto spans = regions(rva, length);
            for (const auto& span : spans)
            {
                const auto protection = span.at("protect").get<DWORD>();
                require(span.at("state").get<DWORD>() == MEM_COMMIT &&
                    !(protection & (PAGE_GUARD | PAGE_NOACCESS)), "unreadable or guarded region");
            }
            requested_bytes += length; // Count the request even if the API only returns a prefix.
            std::vector<uint8_t> bytes(length);
            SIZE_T received{};
            const auto ok = ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<const void*>(base + rva),
                bytes.data(), length, &received);
            returned_bytes += received;
            require(ok && received == length, "ReadProcessMemory failed or returned a partial read");
            return bytes;
        }
    };

    // Caller MUST immediately pass this result to the existing exit_hook; never continue post_unpack.
    inline int capture() noexcept
    try
    {
        static std::atomic_flag captured = ATOMIC_FLAG_INIT;
        if (captured.test_and_set() || bound_output.empty() || !validate_invocation()) return 2;
        auto report = json{{"schema", "iw7.t7-prepatch-memory-observation/1"},
            {"phase", "first_dpi_before_component_post_unpack"},
            {"source_base", hex(source_base)}, {"read_limit", read_limit}, {"report_limit", report_limit},
            {"window_count", sites.size()}, {"window_observations", 0},
            {"requested_bytes", 0}, {"returned_bytes", 0},
            {"pid", GetCurrentProcessId()}, {"thread_id", GetCurrentThreadId()},
            {"capture_complete", false}, {"boot_authorized", false}, {"abi_proven", false},
            {"runtime_compatibility_proven", false}, {"windows", json::array()}};
        bool complete = false;
        try
        {
            FILETIME creation{}, exit{}, kernel{}, user{};
            require(GetProcessTimes(GetCurrentProcess(), &creation, &exit, &kernel, &user) != FALSE,
                "cannot identify current process generation");
            report["creation_filetime"] = std::to_string((static_cast<uint64_t>(creation.dwHighDateTime) << 32) |
                creation.dwLowDateTime);
            // GetModuleHandle observes an existing mapping; it never loads the payload.
            const auto module = GetModuleHandleW(executable_name);
            image_reader reader(module);
            report["module_base"] = hex(reader.base);
            report["base_matches_source"] = reader.base == source_base;
            std::array<wchar_t, 32768> module_path{};
            const auto path_length = GetModuleFileNameW(module, module_path.data(), static_cast<DWORD>(module_path.size()));
            require(path_length && path_length < module_path.size(), "cannot identify mapped module path");
            report["module_path"] = std::filesystem::path(module_path.data()).generic_string();
            try
            {
                const auto dos = field<IMAGE_DOS_HEADER>(reader.read(0, sizeof(IMAGE_DOS_HEADER)));
                require(dos.e_magic == IMAGE_DOS_SIGNATURE && dos.e_lfanew >= 0 && dos.e_lfanew <= 0xF0000,
                    "invalid mapped DOS header");
                const auto nt = static_cast<uint32_t>(dos.e_lfanew);
                const auto coff = reader.read(nt, 4 + sizeof(IMAGE_FILE_HEADER));
                require(field<DWORD>(coff) == IMAGE_NT_SIGNATURE, "invalid mapped PE signature");
                const auto file = field<IMAGE_FILE_HEADER>(coff, 4);
                require(file.Machine == IMAGE_FILE_MACHINE_AMD64 && file.NumberOfSections && file.NumberOfSections <= 96 &&
                    file.SizeOfOptionalHeader >= sizeof(IMAGE_OPTIONAL_HEADER64) && file.SizeOfOptionalHeader <= 4096,
                    "unsupported mapped PE header");
                const auto optional = field<IMAGE_OPTIONAL_HEADER64>(reader.read(nt + 24, file.SizeOfOptionalHeader));
                require(optional.Magic == IMAGE_NT_OPTIONAL_HDR64_MAGIC && optional.SizeOfImage >= 4096 &&
                    optional.SizeOfImage <= 1024 * 1024 * 1024 && optional.NumberOfRvaAndSizes >= 4 &&
                    optional.NumberOfRvaAndSizes <= 16, "invalid mapped optional header");
                reader.image_size = optional.SizeOfImage;
                report["pe"] = {{"size_of_image", optional.SizeOfImage}, {"preferred_base", hex(optional.ImageBase)},
                    {"entrypoint_rva", optional.AddressOfEntryPoint}, {"timestamp", file.TimeDateStamp},
                    {"dll_characteristics", optional.DllCharacteristics}, {"sections", json::array()}};
                const auto sections = reader.read(nt + 24 + file.SizeOfOptionalHeader,
                    file.NumberOfSections * sizeof(IMAGE_SECTION_HEADER));
                for (size_t i = 0; i < file.NumberOfSections; ++i)
                {
                    const auto section = field<IMAGE_SECTION_HEADER>(sections, i * sizeof(IMAGE_SECTION_HEADER));
                    const auto size = (std::max)(section.Misc.VirtualSize, section.SizeOfRawData);
                    require(section.VirtualAddress <= reader.image_size && size <= reader.image_size - section.VirtualAddress,
                        "mapped section exceeds image");
                    char name[9]{};
                    std::memcpy(name, section.Name, 8);
                    report["pe"]["sections"].push_back({{"name", std::string(name)},
                        {"rva", section.VirtualAddress}, {"virtual_size", section.Misc.VirtualSize},
                        {"raw_size", section.SizeOfRawData}, {"characteristics", section.Characteristics}});
                }
                std::vector<uint8_t> pdata;
                const auto directory = optional.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXCEPTION];
                if (directory.VirtualAddress || directory.Size)
                {
                    require(directory.VirtualAddress && directory.Size && directory.Size <= pdata_limit &&
                        directory.Size % sizeof(RUNTIME_FUNCTION) == 0, "invalid mapped pdata extent");
                    pdata = reader.read(directory.VirtualAddress, directory.Size);
                    DWORD previous_end{};
                    for (size_t off = 0; off < pdata.size(); off += sizeof(RUNTIME_FUNCTION))
                    {
                        const auto fn = field<RUNTIME_FUNCTION>(pdata, off);
                        require(fn.BeginAddress >= previous_end && fn.BeginAddress < fn.EndAddress &&
                            fn.EndAddress <= reader.image_size && fn.UnwindData && fn.UnwindData < reader.image_size,
                            "invalid or overlapping mapped pdata ranges");
                        previous_end = fn.EndAddress;
                    }
                }
                report["pdata_records"] = pdata.size() / sizeof(RUNTIME_FUNCTION);
                complete = true;
                for (const auto& site : sites)
                {
                    auto row = json{{"site", site.name}, {"rva", site.rva},
                        {"window_rva", site.rva - site.before}, {"window_bytes", site.length},
                        {"runtime_function", nullptr}};
                    try
                    {
                        row["regions"] = reader.regions(site.rva - site.before, site.length);
                        row["bytes_hex"] = bytes_hex(reader.read(site.rva - site.before, site.length));
                        for (size_t off = 0; off < pdata.size(); off += sizeof(RUNTIME_FUNCTION))
                        {
                            const auto fn = field<RUNTIME_FUNCTION>(pdata, off);
                            if (fn.BeginAddress <= site.rva && site.rva < fn.EndAddress)
                            {
                                row["runtime_function"] = {{"begin_rva", fn.BeginAddress}, {"end_rva", fn.EndAddress},
                                    {"unwind_rva", fn.UnwindData},
                                    {"unwind_header_hex", bytes_hex(reader.read(fn.UnwindData, 4))},
                                    {"unwind_format_validated", false}};
                                break;
                            }
                        }
                    }
                    catch (const std::exception& error) { row["error"] = error.what(); complete = false; }
                    report["windows"].push_back(std::move(row));
                }
            }
            catch (const std::exception& error) { report["metadata_error"] = error.what(); complete = false; }
            report["requested_bytes"] = reader.requested_bytes;
            report["returned_bytes"] = reader.returned_bytes;
        }
        catch (const std::exception& error) { report["capture_error"] = error.what(); complete = false; }
        report["capture_complete"] = complete;
        report["window_observations"] = report["windows"].size();
        report["status"] = complete ? "captured_for_offline_review" : "incomplete_stop";
        try
        {
            const auto serialized = report.dump(2) + "\n";
            require(serialized.size() <= report_limit, "bounded report size exceeded");
            // Existing CREATE_NEW + exclusive handle + exact flushed readback writer.
            zonetool::iw7::write_enemy_reference_output(bound_output, serialized);
            std::fputs(complete ? "T7 prepatch capture complete; review required; exiting.\n" :
                "T7 prepatch capture incomplete; exiting.\n", stdout);
        }
        catch (const std::exception& error)
        {
            std::fprintf(stderr, "T7 prepatch report refused: %s\n", error.what());
            return 2;
        }
        return complete ? 0 : 2;
    }
    catch (...) { std::fputs("T7 prepatch capture failed; exit required.\n", stderr); return 2; }
}
