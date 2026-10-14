// Offline, explicitly selected raw payloads only. Native build/run needs the owner's heavy-stage GO.
#ifndef _WIN32
#error This executable requires the existing Win32 sealed-file adapter.
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include "streamed_mesh_payload.hpp"
#include "selected_xpak_cli_options.hpp"
#include <lz4.h>
#include <bcrypt.h>
#include <array>
#include <filesystem>
#include <iostream>
#include <iomanip>
#include <sstream>
#pragma comment(lib, "bcrypt.lib")

namespace xpak = zonetool::t7::selected_xpak;
namespace fs = std::filesystem;
using selected_xpak_cli::require;

namespace
{
    std::string utf8(const std::wstring& value)
    {
        require(value.size() <= 32767, "Path character bound exceeded");
        const auto length = static_cast<int>(value.size());
        const int size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), length, nullptr, 0, nullptr, nullptr);
        require(size > 0, "Cannot encode path as UTF-8");
        std::string out(static_cast<std::size_t>(size), '\0');
        require(WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), length, out.data(), size, nullptr, nullptr) == size,
            "Path encoding changed");
        return out;
    }
    std::string quoted(const std::string& value)
    {
        std::ostringstream out; out << '"';
        for (const unsigned char c : value)
        {
            if (c == '"' || c == '\\') out << '\\' << static_cast<char>(c);
            else if (c < 32) out << "\\u00" << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(c) << std::dec;
            else out << static_cast<char>(c);
        }
        out << '"'; return out.str();
    }
    std::wstring expected_dos(const fs::path& path)
    {
        auto value = std::wstring(L"\\\\?\\") + path.lexically_normal().make_preferred().native();
        require(value.size() >= 7 && value[5] == L':' && value[6] == L'\\', "Local absolute drive path required");
        if (value[4] >= L'a' && value[4] <= L'z') value[4] -= L'a' - L'A';
        return value;
    }
    std::wstring resolved_dos(HANDLE handle)
    {
        const auto capacity = GetFinalPathNameByHandleW(handle, nullptr, 0, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
        require(capacity > 0 && capacity <= 32767, "Resolved output path unavailable");
        std::vector<wchar_t> buffer(static_cast<std::size_t>(capacity) + 1);
        const auto length = GetFinalPathNameByHandleW(handle, buffer.data(), static_cast<DWORD>(buffer.size()),
            FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
        require(length > 0 && length < buffer.size(), "Resolved output path truncated");
        std::wstring value(buffer.data(), length);
        require(value.size() >= 7 && value.compare(0, 4, L"\\\\?\\") == 0 && value[5] == L':' && value[6] == L'\\',
            "Resolved local drive path required");
        if (value[4] >= L'a' && value[4] <= L'z') value[4] -= L'a' - L'A';
        return value;
    }
    void ordinary_ancestry(const fs::path& path)
    {
        for (auto at = path; !at.empty(); at = at.parent_path())
        {
            const auto attributes = GetFileAttributesW(at.c_str());
            require(attributes != INVALID_FILE_ATTRIBUTES && !(attributes & FILE_ATTRIBUTE_REPARSE_POINT),
                "Reparse or inaccessible output ancestry");
            if (at == at.root_path()) break;
        }
    }
    bool within(const fs::path& path, const fs::path& root)
    {
        const auto value = expected_dos(path), base = expected_dos(root);
        return selected_xpak_cli::lexical_path_within(value, base);
    }
    bool zone_name(std::wstring value)
    {
        for (auto& c : value) if (c >= L'A' && c <= L'Z') c += L'a' - L'A';
        return value == L"zone";
    }
    void output_name(const fs::path& path)
    {
        const auto name = path.filename().native();
        require(!name.empty() && name.size() <= 64 && name != L"." && name != L".." &&
            name.back() != L'.', "Portable output filename of at most 64 characters required");
        for (const auto c : name)
            require((c >= L'a' && c <= L'z') || (c >= L'A' && c <= L'Z') ||
                (c >= L'0' && c <= L'9') || c == L'_' || c == L'-' || c == L'.', "Portable output filename required");
        auto stem = name.substr(0, name.find(L'.'));
        for (auto& c : stem) if (c >= L'a' && c <= L'z') c -= L'a' - L'A';
        require(stem != L"CON" && stem != L"PRN" && stem != L"AUX" && stem != L"NUL" &&
            !(stem.size() == 4 && (stem.substr(0, 3) == L"COM" || stem.substr(0, 3) == L"LPT") &&
                stem[3] >= L'1' && stem[3] <= L'9'), "Reserved device output filename refused");
    }
    class output_parent
    {
        HANDLE handle_ = INVALID_HANDLE_VALUE;
    public:
        output_parent(const fs::path& output, const selected_xpak_cli::options& options)
        {
            output_name(output);
            const auto parent = output.parent_path();
            ordinary_ancestry(parent);
            for (const auto& input : options.packages)
            {
                const auto directory = fs::path(input.path).lexically_normal().parent_path();
                const auto protected_root = zone_name(directory.filename().native()) ? directory.parent_path() : directory;
                require(!within(output, protected_root), "Output must be outside the input package/game directory");
            }
            handle_ = CreateFileW(parent.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING,
                FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
            require(handle_ != INVALID_HANDLE_VALUE, "Cannot retain existing output directory");
            try
            {
                require(resolved_dos(handle_) == expected_dos(parent), "Output directory resolved outside admitted path");
                BY_HANDLE_FILE_INFORMATION info{};
                require(GetFileInformationByHandle(handle_, &info) && (info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) &&
                    !(info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT), "Ordinary output directory required");
            }
            catch (...) { CloseHandle(handle_); handle_ = INVALID_HANDLE_VALUE; throw; }
        }
        output_parent(const output_parent&) = delete;
        output_parent& operator=(const output_parent&) = delete;
        ~output_parent() { if (handle_ != INVALID_HANDLE_VALUE) CloseHandle(handle_); }
    };
    class new_output
    {
        HANDLE handle_ = INVALID_HANDLE_VALUE;
        bool committed_ = false;
        void close() noexcept
        {
            if (handle_ == INVALID_HANDLE_VALUE) return;
            if (!committed_)
            {
                FILE_DISPOSITION_INFO discard{}; discard.DeleteFile = TRUE;
                if (!SetFileInformationByHandle(handle_, FileDispositionInfo, &discard, sizeof(discard)))
                    std::cerr << "An owned partial output could not be marked for deletion; preserve it and use a fresh output name.\n";
            }
            CloseHandle(handle_); handle_ = INVALID_HANDLE_VALUE;
        }
    public:
        explicit new_output(const fs::path& path)
        {
            handle_ = CreateFileW(path.c_str(), GENERIC_READ | GENERIC_WRITE | DELETE, 0, nullptr, CREATE_NEW,
                FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
            require(handle_ != INVALID_HANDLE_VALUE, "Output already exists or cannot be created");
            try
            {
                require(GetFileType(handle_) == FILE_TYPE_DISK && resolved_dos(handle_) == expected_dos(path),
                    "New output resolved outside admitted path");
                BY_HANDLE_FILE_INFORMATION info{};
                require(GetFileInformationByHandle(handle_, &info) &&
                    !(info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)),
                    "Ordinary new output file required");
            }
            catch (...) { close(); throw; }
        }
        new_output(const new_output&) = delete;
        new_output& operator=(const new_output&) = delete;
        ~new_output() { close(); }
        void write(std::span<const std::uint8_t> bytes)
        {
            require(bytes.size() <= 1024u * 1024u, "Output byte bound exceeded");
            std::size_t done = 0;
            while (done < bytes.size())
            {
                DWORD written{};
                require(WriteFile(handle_, bytes.data() + done, static_cast<DWORD>(bytes.size() - done), &written, nullptr) &&
                    written > 0 && written <= bytes.size() - done, "Output write failed");
                done += written;
            }
            LARGE_INTEGER length{};
            require(GetFileSizeEx(handle_, &length) && length.QuadPart >= 0 &&
                static_cast<std::uint64_t>(length.QuadPart) == bytes.size() && FlushFileBuffers(handle_), "Output flush/length verification failed");
        }
        void commit() noexcept { committed_ = true; }
    };
    std::string sha256(std::span<const std::uint8_t> bytes)
    {
        BCRYPT_ALG_HANDLE algorithm = nullptr;
        BCRYPT_HASH_HANDLE hash = nullptr;
        // Keep the provider's hash-object storage alive through failure cleanup.
        std::vector<std::uint8_t> object;
        try
        {
            require(BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) >= 0, "SHA-256 provider unavailable");
            ULONG object_size{}, returned{};
            require(BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH, reinterpret_cast<PUCHAR>(&object_size),
                sizeof(object_size), &returned, 0) >= 0 && returned == sizeof(object_size) && object_size > 0 && object_size <= 1024u * 1024u,
                "SHA-256 object size unavailable");
            object.resize(object_size);
            require(BCryptCreateHash(algorithm, &hash, object.data(), object_size, nullptr, 0, 0) >= 0, "SHA-256 initialization failed");
            require(bytes.size() <= xpak::max_decoded_bytes &&
                BCryptHashData(hash, const_cast<PUCHAR>(bytes.data()), static_cast<ULONG>(bytes.size()), 0) >= 0, "SHA-256 update failed");
            std::array<std::uint8_t, 32> digest{};
            require(BCryptFinishHash(hash, digest.data(), static_cast<ULONG>(digest.size()), 0) >= 0, "SHA-256 finish failed");
            BCryptDestroyHash(hash); hash = nullptr;
            BCryptCloseAlgorithmProvider(algorithm, 0); algorithm = nullptr;
            std::ostringstream out; out << std::hex << std::setfill('0');
            for (const auto byte : digest) out << std::setw(2) << static_cast<unsigned>(byte);
            return out.str();
        }
        catch (...)
        {
            if (hash) BCryptDestroyHash(hash);
            if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
            throw;
        }
    }
    std::string metadata(const selected_xpak_cli::options& options, const xpak::payload& payload)
    {
        const auto& seen = payload.observed;
        std::wstring provider;
        for (const auto& input : options.packages) if (input.identity == seen.package_identity) provider = input.path;
        require(!provider.empty(), "Selected provider is not in the admitted list");
        std::ostringstream out;
        out << "{\n\"schema\":\"iw7.selected-xpak-cli-result/1\",\n\"profile\":\"bounded-raw-payload-v1\",\n"
            << "\"key_hex\":" << quoted(options.key_hex) << ",\n\"expected_decoded_bytes\":" << options.expected
            << ",\n\"source_path\":" << quoted(utf8(provider)) << ",\n\"source_file_identity\":" << quoted(seen.package_identity)
            << ",\n\"source_file_bytes\":" << seen.file_bytes << ",\n\"hash_table_offset\":" << seen.hash_table_offset
            << ",\n\"hash_entry_offset\":" << seen.hash_entry_offset << ",\n\"payload_offset\":" << seen.payload_offset
            << ",\n\"compressed_bytes\":" << seen.compressed_bytes << ",\n\"packed_entry_size_decimal\":"
            << quoted(std::to_string(seen.packed_entry_size)) << ",\n\"indexed_record_bytes\":" << seen.indexed_bytes
            << ",\n\"decoded_bytes\":" << payload.bytes.size() << ",\n\"decoded_sha256\":" << quoted(sha256(payload.bytes))
            << ",\n\"opcodes\":[";
        for (std::size_t i = 0; i < seen.opcodes.size(); ++i) { if (i) out << ','; out << static_cast<unsigned>(seen.opcodes[i]); }
        out << "],\n\"opaque_group_header_offsets\":[";
        for (std::size_t i = 0; i < seen.header_offsets.size(); ++i) { if (i) out << ','; out << seen.header_offsets[i]; }
        out << "],\n\"admitted_packages\":[";
        for (std::size_t i = 0; i < options.packages.size(); ++i)
        {
            if (i) out << ',';
            const auto& input = options.packages[i];
            out << "{\"path\":" << quoted(utf8(input.path)) << ",\"identity\":" << quoted(input.identity) << ",\"bytes\":" << input.bytes << '}';
        }
        out << "],\n\"input_metadata_rechecked_by_reader\":true,\n\"atomic_snapshot_proven\":false,\n"
            << "\"geometry_verified\":false,\n\"runtime_verified\":false,\n\"whole_package_hash_measured\":false\n}\n";
        return out.str();
    }
    void help()
    {
        std::cout << "Selected XPAK raw payload tool (Windows)\n"
            << "  selected-xpak --key HEX16 --expected-bytes N --out ABSFILE --package ABSXPAK ID BYTES [--package ...]\n"
            << "  selected-xpak --inspect --key HEX16 --expected-bytes N --package ABSXPAK ID BYTES [--package ...]\n"
            << "N: 1..262144 exact decoded bytes; at most 8 explicit packages, aggregate index <=8 MiB.\n"
            << "ID: upper-case VolumeSerial8hex:FileIndex16hex. Package sizes: 120 bytes..16 GiB.\n"
            << "Extraction creates ABSFILE and ABSFILE.json, never overwrites; parent must exist outside input game/package roots.\n"
            << "Inspection also decodes the selected payload; it prints provenance and writes no output files.\n"
            << "No package discovery, engine, whole-package hash, geometry/FF/runtime qualification.\n";
    }
}
int wmain(int argc, wchar_t* argv[])
{
    try
    {
        std::vector<std::wstring> arguments;
        for (int i = 1; i < argc; ++i) arguments.emplace_back(argv[i]);
        const auto options = selected_xpak_cli::parse(arguments);
        if (options.help) { help(); return 0; }
        std::vector<xpak::package> packages;
        for (const auto& input : options.packages)
        {
            xpak::sealed_file file{fs::path(input.path)};
            auto view = file.view();
            require(view.identity == input.identity && view.size == input.bytes, "Opened package differs from admitted identity/length");
            packages.push_back(std::move(view));
        }
        const auto output = fs::path(options.output).lexically_normal();
        std::unique_ptr<output_parent> parent;
        if (!options.inspect) parent = std::make_unique<output_parent>(output, options);
        const auto payload = xpak::read_bounded_selected_key(packages, options.key, options.expected, &LZ4_decompress_safe);
        const auto receipt = metadata(options, payload);
        if (options.inspect) { std::cout << receipt; return 0; }
        const auto sidecar = fs::path(output.native() + L".json");
        new_output raw(output), json(sidecar);
        raw.write(payload.bytes);
        json.write({reinterpret_cast<const std::uint8_t*>(receipt.data()), receipt.size()});
        raw.commit(); json.commit();
        std::cout << "{\"payload\":" << quoted(utf8(output.native())) << ",\"metadata\":" << quoted(utf8(sidecar.native()))
            << ",\"decoded_bytes\":" << payload.bytes.size() << "}\n";
        return 0;
    }
    catch (const std::exception& error) { std::cerr << "selected-xpak: " << error.what() << '\n'; return 1; }
}
