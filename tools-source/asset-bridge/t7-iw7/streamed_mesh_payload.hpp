#pragma once

// BO3 XPAK framing provenance: ZoneTool fab935826c898806855376662a8a03317b3ad8f1
// and Greyhound 22c3d17f7428573042b56f43af0ed2585989bebd. This selected reader
// neither discovers packages nor interprets the engine's opaque descriptors.
#include <algorithm>
#include <array>
#include <cstdint>
#include <functional>
#include <limits>
#include <span>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#ifdef _WIN32
#include <Windows.h>
#include <filesystem>
#include <iomanip>
#include <memory>
#include <mutex>
#include <sstream>
#endif

namespace zonetool::t7::selected_xpak
{
    using read_function = std::function<std::size_t(std::uint64_t, std::span<std::uint8_t>)>;
    using lz4_decoder = int (*)(const char*, char*, int, int);

    // Adapters must retain the same stable input. sealed_file views own their
    // backing handle; portable fixtures use immutable memory.
    struct package
    {
        std::string name, identity;
        std::uint64_t size;
        read_function read;
    };
    struct observation
    {
        std::string package_name, package_identity;
        std::uint64_t file_bytes{}, key{}, hash_table_offset{}, hash_entry_offset{};
        std::uint64_t payload_offset{}, compressed_bytes{}, packed_entry_size{}, indexed_bytes{};
        std::vector<std::uint8_t> opcodes;
        // Recorded without interpretation. Concatenation follows the cited readers.
        std::vector<std::uint32_t> header_offsets;
    };
    struct payload { std::vector<std::uint8_t> bytes; observation observed; };

    inline constexpr std::uint32_t expected_mesh_bytes = 18624;
    inline constexpr std::uint64_t max_index_bytes = 8u * 1024u * 1024u;
    inline constexpr std::uint64_t max_compressed_bytes = 256u * 1024u;
    inline constexpr std::size_t max_packages = 8, max_groups = 128;

    namespace detail
    {
        inline void require(bool ok, const char* why) { if (!ok) throw std::runtime_error(why); }
        inline std::uint64_t add(std::uint64_t a, std::uint64_t b)
        {
            require(b <= (std::numeric_limits<std::uint64_t>::max)() - a, "XPAK offset overflow");
            return a + b;
        }
        inline void range(std::uint64_t offset, std::uint64_t bytes, std::uint64_t size)
        { require(offset <= size && bytes <= size - offset, "XPAK range outside sealed input"); }
        inline std::uint64_t word(std::span<const std::uint8_t> input, std::size_t at, unsigned width)
        {
            require(at <= input.size() && width <= input.size() - at, "XPAK truncated scalar");
            std::uint64_t value{};
            for (unsigned i = 0; i < width; ++i) value |= std::uint64_t(input[at + i]) << (8u * i);
            return value;
        }
        inline void read(const package& input, std::uint64_t at, std::span<std::uint8_t> out)
        {
            range(at, out.size(), input.size);
            require(input.read(at, out) == out.size(), "XPAK short read");
        }
        struct entry
        {
            const package* source{};
            std::uint64_t hash_offset{}, entry_offset{}, payload_offset{}, bytes{}, packed_size{};
        };
        inline payload decode(const entry& selected, std::uint64_t key, std::uint64_t index_bytes,
            std::uint32_t expected, lz4_decoder decompress)
        {
            std::vector<std::uint8_t> encoded(static_cast<std::size_t>(selected.bytes));
            read(*selected.source, selected.payload_offset, encoded);
            payload result;
            result.bytes.reserve(expected);
            auto& seen = result.observed;
            seen.package_name = selected.source->name; seen.package_identity = selected.source->identity;
            seen.file_bytes = selected.source->size; seen.key = key;
            seen.hash_table_offset = selected.hash_offset; seen.hash_entry_offset = selected.entry_offset;
            seen.payload_offset = selected.payload_offset; seen.compressed_bytes = selected.bytes;
            seen.packed_entry_size = selected.packed_size; seen.indexed_bytes = index_bytes;
            std::size_t cursor = 0;
            while (cursor < encoded.size())
            {
                require(seen.header_offsets.size() < max_groups, "XPAK command group limit");
                range(cursor, 128, encoded.size());
                const auto count = word(encoded, cursor, 4);
                require(count > 0 && count <= 30, "XPAK command count outside selected profile");
                seen.header_offsets.push_back(static_cast<std::uint32_t>(word(encoded, cursor + 4, 4)));
                const auto header = cursor; cursor += 128;
                for (std::uint64_t i = 0; i < count; ++i)
                {
                    const auto command = word(encoded, header + 8 + static_cast<std::size_t>(i) * 4, 4);
                    const auto block_bytes = static_cast<std::size_t>(command & 0xFFFFFFu);
                    const auto opcode = static_cast<std::uint8_t>(command >> 24);
                    require(block_bytes > 0, "XPAK empty command block");
                    require(opcode == 0 || opcode == 3, "XPAK unsupported selected codec");
                    range(cursor, block_bytes, encoded.size());
                    require(result.bytes.size() < expected, "XPAK output exceeds expected mesh size");
                    const auto remaining = static_cast<std::size_t>(expected) - result.bytes.size();
                    if (opcode == 0)
                    {
                        require(block_bytes <= remaining, "XPAK raw output exceeds expected mesh size");
                        result.bytes.insert(result.bytes.end(), encoded.data() + cursor,
                            encoded.data() + cursor + block_bytes);
                    }
                    else
                    {
                        require(decompress != nullptr, "XPAK LZ4 decoder not supplied");
                        // Both lengths are capped well below INT_MAX; retain the signed return.
                        std::vector<std::uint8_t> decoded(remaining);
                        const int decoded_bytes = decompress(reinterpret_cast<const char*>(encoded.data() + cursor),
                            reinterpret_cast<char*>(decoded.data()), static_cast<int>(block_bytes), static_cast<int>(remaining));
                        require(decoded_bytes > 0 && static_cast<std::size_t>(decoded_bytes) <= remaining,
                            "XPAK LZ4 failed or exceeded output capacity");
                        result.bytes.insert(result.bytes.end(), decoded.data(), decoded.data() + decoded_bytes);
                    }
                    seen.opcodes.push_back(opcode); cursor += block_bytes;
                }
                // Alignment is relative to this entry, not the allocator's pointer.
                // A final group may end at the exact extent end without unused padding.
                if (cursor != encoded.size())
                {
                    const auto aligned = add(cursor, (128u - cursor % 128u) % 128u);
                    require(aligned <= encoded.size(), "XPAK truncated group padding");
                    cursor = static_cast<std::size_t>(aligned);
                }
                require(result.bytes.size() != expected || cursor == encoded.size(), "XPAK trailing command data");
            }
            require(result.bytes.size() == expected, "XPAK decoded mesh size mismatch");
            return result;
        }
    }

    inline payload read_selected_key(std::span<const package> packages, std::uint64_t key,
        std::uint32_t expected, lz4_decoder decompress)
    {
        using namespace detail;
        require(expected == expected_mesh_bytes, "XPAK selected mesh size profile differs");
        require(!packages.empty() && packages.size() <= max_packages, "XPAK explicit package list bound");
        entry selected{}; std::size_t matches = 0;
        std::uint64_t index_budget = 0, index_read = 0;
        std::array<std::uint8_t, 24 * 1024> chunk{};
        for (std::size_t source_index = 0; source_index < packages.size(); ++source_index)
        {
            const auto& input = packages[source_index];
            require(!input.name.empty() && input.name.size() <= 1024 && !input.identity.empty() &&
                input.identity.size() <= 128 && static_cast<bool>(input.read), "XPAK sealed source identity required");
            for (std::size_t earlier = 0; earlier < source_index; ++earlier)
                require(input.identity != packages[earlier].identity, "XPAK duplicate input identity");
            std::array<std::uint8_t, 120> header{}; read(input, 0, header);
            require(word(header, 0, 4) == 0x4950414Bu && word(header, 6, 2) == 0xAu, "XPAK BO3 header/version required");
            const auto data_at = word(header, 32, 8), data_size = word(header, 40, 8);
            const auto count = word(header, 48, 8), hash_at = word(header, 56, 8), hash_size = word(header, 64, 8);
            require(count <= max_index_bytes / 24, "XPAK hash count limit");
            const auto records_size = count * 24;
            require(hash_size >= records_size && hash_size <= max_index_bytes - index_budget, "XPAK index byte limit");
            index_budget += hash_size;
            range(hash_at, hash_size, input.size); range(data_at, data_size, input.size);
            if (hash_size) require(hash_at >= 120, "XPAK hash table overlaps header");
            if (data_size) require(data_at >= 120, "XPAK data section overlaps header");
            if (hash_size && data_size)
                require(add(hash_at, hash_size) <= data_at || add(data_at, data_size) <= hash_at,
                    "XPAK hash/data sections overlap");
            std::uint64_t done = 0;
            while (done < count)
            {
                const auto rows = (std::min)(count - done, std::uint64_t(1024));
                const auto bytes = static_cast<std::size_t>(rows * 24);
                const auto table_at = add(hash_at, done * 24);
                read(input, table_at, std::span<std::uint8_t>(chunk.data(), bytes)); index_read += bytes;
                for (std::uint64_t row = 0; row < rows; ++row)
                {
                    const auto pos = static_cast<std::size_t>(row * 24);
                    const auto row_key = word(chunk, pos, 8), relative = word(chunk, pos + 8, 8);
                    const auto packed = word(chunk, pos + 16, 8);
                    const std::uint64_t size = packed & 0x00FFFFFFFFFFFFFFull;
                    range(relative, size, data_size);
                    const auto absolute = add(data_at, relative); range(absolute, size, input.size);
                    if (row_key != key) continue;
                    require(size > 0 && size <= max_compressed_bytes, "XPAK selected compressed extent limit");
                    ++matches;
                    require(matches == 1, "XPAK selected key is ambiguous");
                    selected = {&input, hash_at, add(table_at, row * 24), absolute, size, packed};
                }
                done += rows;
            }
        }
        require(matches == 1, "XPAK selected key not found in admitted packages");
        // No payload is read until every admitted index passed and the key is unique.
        return decode(selected, key, index_read, expected, decompress);
    }

#ifdef _WIN32
    // No discovery, reopening or broad extraction. Each view retains its
    // original handle, including after this wrapper has been destroyed.
    class sealed_file
    {
        struct state
        {
            HANDLE handle = INVALID_HANDLE_VALUE;
            std::string name, identity;
            std::uint64_t size{};
            FILETIME written{};
            std::mutex read_mutex;
            ~state() { if (handle != INVALID_HANDLE_VALUE) CloseHandle(handle); }
            void check_unchanged() const
            {
                BY_HANDLE_FILE_INFORMATION info{};
                LARGE_INTEGER length{};
                detail::require(GetFileInformationByHandle(handle, &info) && GetFileSizeEx(handle, &length) &&
                    length.QuadPart >= 0 && static_cast<std::uint64_t>(length.QuadPart) == size &&
                    info.ftLastWriteTime.dwLowDateTime == written.dwLowDateTime &&
                    info.ftLastWriteTime.dwHighDateTime == written.dwHighDateTime, "XPAK sealed input metadata changed");
            }
        };
        std::shared_ptr<state> state_;
    public:
        explicit sealed_file(const std::filesystem::path& path)
        {
            detail::require(path.is_absolute() && path.native().find(L'\0') == std::wstring::npos &&
                path.extension() == L".xpak" && path.native().rfind(L"\\\\", 0) != 0,
                "XPAK explicit absolute local package path required");
            for (auto at = path; !at.empty(); at = at.parent_path())
            {
                const auto attributes = GetFileAttributesW(at.c_str());
                detail::require(attributes != INVALID_FILE_ATTRIBUTES && !(attributes & FILE_ATTRIBUTE_REPARSE_POINT),
                    "XPAK reparse or inaccessible package ancestry");
                if (at == at.root_path()) break;
            }
            auto file = std::make_shared<state>();
            file->handle = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING,
                FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_RANDOM_ACCESS, nullptr);
            detail::require(file->handle != INVALID_HANDLE_VALUE, "XPAK package could not be sealed for read");
            // Bind the opened handle to the admitted path after resolution. The
            // pre-open ancestry check alone could race an intermediate junction.
            auto expected_path = L"\\\\?\\" + path.lexically_normal().make_preferred().native();
            const auto path_capacity = GetFinalPathNameByHandleW(file->handle, nullptr, 0, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
            detail::require(path_capacity > 0 && path_capacity <= 32767 && expected_path.size() <= 32767,
                "XPAK sealed resolved path unavailable or oversized");
            std::vector<wchar_t> resolved_path(static_cast<std::size_t>(path_capacity) + 1);
            const auto path_length = GetFinalPathNameByHandleW(file->handle, resolved_path.data(),
                static_cast<DWORD>(resolved_path.size()), FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
            detail::require(path_length > 0 && path_length < resolved_path.size(), "XPAK sealed resolved path truncated");
            std::wstring actual_path(resolved_path.data(), path_length);
            const auto local_drive = [](const std::wstring& value)
            {
                return value.size() >= 7 && value.compare(0, 4, L"\\\\?\\") == 0 && value[5] == L':' && value[6] == L'\\' &&
                    ((value[4] >= L'A' && value[4] <= L'Z') || (value[4] >= L'a' && value[4] <= L'z'));
            };
            detail::require(local_drive(actual_path) && local_drive(expected_path), "XPAK sealed local drive path required");
            if (actual_path[4] >= L'a' && actual_path[4] <= L'z') actual_path[4] -= L'a' - L'A';
            if (expected_path[4] >= L'a' && expected_path[4] <= L'z') expected_path[4] -= L'a' - L'A';
            // NTFS supports case-sensitive directories. Only the drive letter
            // is folded; differently cased components must not alias here.
            detail::require(actual_path == expected_path,
                "XPAK sealed handle resolved outside admitted package path");
            BY_HANDLE_FILE_INFORMATION info{}; LARGE_INTEGER length{};
            detail::require(GetFileType(file->handle) == FILE_TYPE_DISK && GetFileInformationByHandle(file->handle, &info) &&
                !(info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) &&
                GetFileSizeEx(file->handle, &length) && length.QuadPart >= 120, "XPAK ordinary sealed file identity required");
            const auto index = (std::uint64_t(info.nFileIndexHigh) << 32) | info.nFileIndexLow;
            std::ostringstream identity;
            identity << std::uppercase << std::hex << std::setfill('0') << std::setw(8) << info.dwVolumeSerialNumber
                << ':' << std::setw(16) << index;
            file->identity = identity.str(); file->name = path.filename().string();
            file->size = static_cast<std::uint64_t>(length.QuadPart); file->written = info.ftLastWriteTime;
            state_ = std::move(file);
        }
        sealed_file(const sealed_file&) = delete;
        sealed_file& operator=(const sealed_file&) = delete;
        sealed_file(sealed_file&&) = delete;
        sealed_file& operator=(sealed_file&&) = delete;
        package view() const
        {
            return {state_->name, state_->identity, state_->size, [file = state_](std::uint64_t at, std::span<std::uint8_t> out)
            {
                const std::lock_guard lock(file->read_mutex);
                detail::range(at, out.size(), file->size); file->check_unchanged();
                LARGE_INTEGER position{}; position.QuadPart = static_cast<LONGLONG>(at);
                detail::require(SetFilePointerEx(file->handle, position, nullptr, FILE_BEGIN), "XPAK sealed seek failed");
                std::size_t done = 0;
                while (done < out.size())
                {
                    const auto wanted = static_cast<DWORD>((std::min)(out.size() - done, std::size_t(65536)));
                    DWORD got = 0;
                    detail::require(ReadFile(file->handle, out.data() + done, wanted, &got, nullptr) && got == wanted,
                        "XPAK sealed read failed or truncated");
                    done += got;
                }
                file->check_unchanged(); return done;
            }};
        }
    };
#endif
}
