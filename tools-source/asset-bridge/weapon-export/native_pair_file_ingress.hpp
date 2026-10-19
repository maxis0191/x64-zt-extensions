#pragma once
// Windows raw-byte producer only. No CRT FILE, native parse, arena or route authority.
// Caller metadata is independent of report contents; it is not a permission token.
#if !defined(_WIN32)
#error native_pair_file_ingress.hpp requires Windows
#endif
#if !defined(NOMINMAX)
#define NOMINMAX
#include <Windows.h>
#undef NOMINMAX
#else
#include <Windows.h>
#endif
#include "native_pair_owned_session.hpp"
#include <array>
#include <cstdint>
#include <exception>
#include <memory>
#include <string>
#include <string_view>

namespace player_pair_file_ingress
{
    using Role = player_pair_input::Role;
    struct Identity
    {
        std::uint64_t volume;
        std::array<std::uint8_t, 16> file_id;
    };
    inline bool same_identity(const Identity& a, const Identity& b) noexcept
    { return a.volume == b.volume && a.file_id == b.file_id; }
    struct FileSpec
    {
        Role role;
        std::wstring path; // Literal drive-absolute UTF16, no normalization/fallback.
        std::size_t bytes;
        std::array<char, 64> sha256;
        Identity expected; // Required independent volume + full 128-bit identity.
    };
    using Files = std::array<FileSpec, 4>; // report, weapon, attachment, csv, in this order.
    enum class Operation { none, request, snapshot, guard_storage, open, type,
        attributes, identity, length, alias, buffer_storage, read, final_length, copy, complete };
    struct Primary
    {
        Operation operation = Operation::none;
        std::size_t role = 4;
        DWORD error = ERROR_SUCCESS;
    };
    struct RoleRecord
    {
        Identity expected{}, observed{};
        std::size_t expected_bytes{};
        std::uint64_t observed_bytes{}, final_bytes{};
        std::uintptr_t original_handle{}, read_handle{}; // Observation, never an owning HANDLE API.
        DWORD read_bytes{}, close_error = ERROR_SUCCESS;
        BOOL close_result = FALSE;
        bool open_attempted{}, acquired{}, metadata_complete{}, read_attempted{}, read_complete{};
        bool close_attempted{}, close_returned{};
    };
    struct Observations
    {
        std::array<RoleRecord, 4> roles{};
        unsigned acquired{}, metadata_complete{}, read_calls{}, first_read_acquired{}, first_read_metadata{};
        bool started{}, raw_copy_complete{}, primary_present{};
        Primary primary{};
    };
    class Guards;
    class CleanupReport;
    using Ingress = player_pair_owned_session::OwnedIngress<Guards>;
    std::unique_ptr<Ingress> read_owned_files(const Files&, CleanupReport&, player_pair_input::Counters&);

    class IngressError final : public std::runtime_error
    {
    public:
        IngressError() : std::runtime_error("Owned file ingress refused") {}
    };
    // This ORIGINAL report must outlive the guards/ingress. No destructor is an OS-close proof.
    class CleanupReport final
    {
        Observations observations_{};
        Primary pending_{};
        std::exception_ptr primary_exception_;
        friend class Guards;
        friend std::unique_ptr<Ingress> read_owned_files(const Files&, CleanupReport&, player_pair_input::Counters&);
        void at(Operation op, std::size_t role = 4, DWORD error = ERROR_SUCCESS) noexcept
        { pending_ = {op, role, error}; }
        [[noreturn]] void reject(Operation op, std::size_t role, DWORD error)
        { at(op, role, error); throw IngressError(); }
        void capture_primary() noexcept
        {
            if (!observations_.primary_present)
            {
                observations_.primary = pending_;
                primary_exception_ = std::current_exception();
                observations_.primary_present = true;
            }
        }
    public:
        CleanupReport() = default;
        CleanupReport(const CleanupReport&) = delete;
        CleanupReport& operator=(const CleanupReport&) = delete;
        CleanupReport(CleanupReport&&) = delete;
        CleanupReport& operator=(CleanupReport&&) = delete;
        const Observations& observations() const & noexcept { return observations_; }
        const Observations& observations() const && = delete;
        // Diagnostic only: current_exception may copy on MSVC; no caught-object address claim.
        const std::exception_ptr& primary_exception() const & noexcept { return primary_exception_; }
        const std::exception_ptr& primary_exception() const && = delete;
    };
    namespace detail
    {
        inline wchar_t upper_ascii(wchar_t c) noexcept
        { return c >= L'a' && c <= L'z' ? static_cast<wchar_t>(c - L'a' + L'A') : c; }
        inline bool word(std::wstring_view a, std::wstring_view b) noexcept
        {
            if (a.size() != b.size()) return false;
            for (std::size_t i = 0; i < a.size(); ++i) if (upper_ascii(a[i]) != b[i]) return false;
            return true;
        }
        inline bool device(std::wstring_view component) noexcept
        {
            const auto base = component.substr(0, component.find(L'.'));
            if (!base.empty() && base.back() == L' ') return true;
            if (word(base, L"CON") || word(base, L"PRN") || word(base, L"AUX") ||
                word(base, L"NUL") || word(base, L"CONIN$") || word(base, L"CONOUT$") ||
                word(base, L"CLOCK$")) return true;
            if (base.size() != 4 || (!word(base.substr(0, 3), L"COM") && !word(base.substr(0, 3), L"LPT"))) return false;
            const auto c = base[3];
            return (c >= L'1' && c <= L'9') || c == 0x00b9 || c == 0x00b2 || c == 0x00b3;
        }
        inline bool path(std::wstring_view value) noexcept
        {
            if (value.size() < 4 || value.size() > 32766 ||
                !((value[0] >= L'A' && value[0] <= L'Z') || (value[0] >= L'a' && value[0] <= L'z')) ||
                value[1] != L':' || value[2] != L'\\') return false;
            for (std::size_t i = 3; i < value.size(); ++i)
            {
                const auto c = static_cast<std::uint32_t>(value[i]);
                if (c < 32 || c == L'/' || c == L':' || c == L'"' || c == L'<' ||
                    c == L'>' || c == L'|' || c == L'?' || c == L'*') return false;
                if (c >= 0xd800 && c <= 0xdbff)
                {
                    if (++i == value.size() || value[i] < 0xdc00 || value[i] > 0xdfff) return false;
                }
                else if (c >= 0xdc00 && c <= 0xdfff) return false;
            }
            std::size_t start = 3;
            while (start < value.size())
            {
                const auto end = value.find(L'\\', start);
                const auto part = value.substr(start, end == value.npos ? value.size() - start : end - start);
                if (part.empty() || part == L"." || part == L".." || part.back() == L'.' ||
                    part.back() == L' ' || device(part)) return false;
                if (end == value.npos) return true;
                start = end + 1;
            }
            return false;
        }
    }

    class Guards final
    {
        CleanupReport& report_;
        std::array<HANDLE, 4> handles_{INVALID_HANDLE_VALUE, INVALID_HANDLE_VALUE,
            INVALID_HANDLE_VALUE, INVALID_HANDLE_VALUE};
        explicit Guards(CleanupReport& report) noexcept : report_(report) {}
        friend std::unique_ptr<Ingress> read_owned_files(const Files&, CleanupReport&, player_pair_input::Counters&);
        void length(std::size_t i, const FileSpec& spec, bool final)
        {
            const auto op = final ? Operation::final_length : Operation::length;
            report_.at(op, i);
            LARGE_INTEGER size{};
            if (!::GetFileSizeEx(handles_[i], &size))
            { const auto error = ::GetLastError(); report_.reject(op, i, error); }
            auto& row = report_.observations_.roles[i];
            if (size.QuadPart < 0) report_.reject(op, i, ERROR_INVALID_DATA);
            const auto observed = static_cast<std::uint64_t>(size.QuadPart);
            if (final) row.final_bytes = observed; else row.observed_bytes = observed;
            if (observed != spec.bytes) report_.reject(op, i, ERROR_BAD_LENGTH);
        }
        void acquire(const Files& specs)
        {
            for (std::size_t i = 0; i < handles_.size(); ++i)
            {
                auto& row = report_.observations_.roles[i];
                report_.at(Operation::open, i); row.open_attempted = true;
                const auto handle = ::CreateFileW(specs[i].path.c_str(), GENERIC_READ,
                    FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
                if (handle == INVALID_HANDLE_VALUE)
                { const auto error = ::GetLastError(); report_.reject(Operation::open, i, error); }
                // No fallible work between the returned original and its owner/report enrollment.
                handles_[i] = handle; row.original_handle = reinterpret_cast<std::uintptr_t>(handle);
                row.acquired = true; ++report_.observations_.acquired;
                report_.at(Operation::type, i);
                const auto type = ::GetFileType(handle);
                const auto type_error = type == FILE_TYPE_UNKNOWN ? ::GetLastError() : ERROR_SUCCESS;
                if (type != FILE_TYPE_DISK) report_.reject(Operation::type, i, type_error);
                report_.at(Operation::attributes, i);
                FILE_ATTRIBUTE_TAG_INFO attributes{};
                if (!::GetFileInformationByHandleEx(handle, FileAttributeTagInfo, &attributes, static_cast<DWORD>(sizeof(attributes))))
                { const auto error = ::GetLastError(); report_.reject(Operation::attributes, i, error); }
                if (attributes.FileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT))
                    report_.reject(Operation::attributes, i, ERROR_INVALID_DATA);
                report_.at(Operation::identity, i);
                FILE_ID_INFO identity{};
                if (!::GetFileInformationByHandleEx(handle, FileIdInfo, &identity, static_cast<DWORD>(sizeof(identity))))
                { const auto error = ::GetLastError(); report_.reject(Operation::identity, i, error); }
                row.observed.volume = identity.VolumeSerialNumber;
                for (std::size_t j = 0; j < row.observed.file_id.size(); ++j)
                    row.observed.file_id[j] = identity.FileId.Identifier[j];
                if (!same_identity(row.observed, specs[i].expected))
                    report_.reject(Operation::identity, i, ERROR_INVALID_DATA);
                for (std::size_t previous = 0; previous < i; ++previous)
                    if (same_identity(row.observed, report_.observations_.roles[previous].observed))
                        report_.reject(Operation::alias, i, ERROR_INVALID_DATA);
                length(i, specs[i], false);
                row.metadata_complete = true; ++report_.observations_.metadata_complete;
            }
        }
        void read(std::size_t i, std::string& buffer)
        {
            if (report_.observations_.metadata_complete != 4)
                report_.reject(Operation::read, i, ERROR_INVALID_DATA);
            report_.at(Operation::read, i);
            auto& state = report_.observations_; auto& row = state.roles[i];
            if (!state.read_calls)
            { state.first_read_acquired = state.acquired; state.first_read_metadata = state.metadata_complete; }
            row.read_attempted = true; row.read_handle = reinterpret_cast<std::uintptr_t>(handles_[i]);
            ++state.read_calls;
            DWORD actual{};
            const auto result = ::ReadFile(handles_[i], buffer.data(), static_cast<DWORD>(buffer.size()), &actual, nullptr);
            const auto error = result ? ERROR_SUCCESS : ::GetLastError();
            row.read_bytes = actual;
            if (!result) report_.reject(Operation::read, i, error);
            if (actual != buffer.size()) report_.reject(Operation::read, i, ERROR_HANDLE_EOF);
            row.read_complete = true; // One bounded read; no short-read retry.
        }
    public:
        Guards(const Guards&) = delete;
        Guards& operator=(const Guards&) = delete;
        Guards(Guards&&) = delete;
        Guards& operator=(Guards&&) = delete;
        ~Guards() noexcept
        {
            for (std::size_t n = handles_.size(); n != 0; --n)
            {
                const auto i = n - 1;
                if (handles_[i] == INVALID_HANDLE_VALUE) continue;
                auto& row = report_.observations_.roles[i];
                row.close_attempted = true;
                const auto result = ::CloseHandle(handles_[i]);
                const auto error = result ? ERROR_SUCCESS : ::GetLastError();
                row.close_result = result; row.close_error = error; row.close_returned = true;
                handles_[i] = INVALID_HANDLE_VALUE; // Never retry, even on FALSE. Original record remains.
            }
        }
    };

    inline std::unique_ptr<Ingress> read_owned_files(const Files& supplied, CleanupReport& report,
        player_pair_input::Counters& counters)
    {
        if (report.observations_.started) throw std::logic_error("Original ingress report already used");
        report.observations_.started = true;
        try
        {
            std::size_t total = 0;
            for (std::size_t i = 0; i < supplied.size(); ++i)
            {
                report.at(Operation::request, i);
                const auto& spec = supplied[i];
                if (static_cast<std::size_t>(spec.role) != i || !detail::path(spec.path) ||
                    !spec.bytes || spec.bytes > player_pair_input::role_caps[i] ||
                    spec.bytes > player_pair_input::total_cap - total)
                    report.reject(Operation::request, i, ERROR_INVALID_PARAMETER);
                total += spec.bytes;
                for (const auto c : spec.sha256)
                    if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')))
                        report.reject(Operation::request, i, ERROR_INVALID_PARAMETER);
            }
            report.at(Operation::snapshot);
            const Files specs = supplied; // All caller paths/pins/expected identities frozen before I/O.
            for (std::size_t i = 0; i < specs.size(); ++i)
            { report.observations_.roles[i].expected = specs[i].expected; report.observations_.roles[i].expected_bytes = specs[i].bytes; }
            report.at(Operation::guard_storage);
            auto guards = std::unique_ptr<Guards>(new Guards(report));
            guards->acquire(specs); // All four metadata checks precede every content read.
            std::array<std::string, 4> buffers;
            for (std::size_t i = 0; i < buffers.size(); ++i)
            { report.at(Operation::buffer_storage, i); buffers[i].resize(specs[i].bytes); }
            for (std::size_t i = 0; i < buffers.size(); ++i) guards->read(i, buffers[i]);
            for (std::size_t i = 0; i < buffers.size(); ++i) guards->length(i, specs[i], true);
            player_pair_input::Inputs inputs{}; player_pair_input::Pins pins{};
            for (std::size_t i = 0; i < inputs.size(); ++i)
            { inputs[i] = buffers[i]; pins[i] = {specs[i].bytes, {specs[i].sha256.data(), specs[i].sha256.size()}}; }
            report.at(Operation::copy);
            auto result = player_pair_owned_session::copy_with_guards(std::move(guards), inputs, pins, counters);
            report.observations_.raw_copy_complete = true;
            report.at(Operation::complete);
            return result;
        }
        catch (...) { report.capture_primary(); throw; } // Close results never replace this primary.
    }
    // Input metadata must stay unmodified throughout validation AND snapshot. Read completion does not
    // assert close success. Failed CloseHandle leaves its SAME external row observable.
    // No proof of ancestor reparses, global aliases, existing mappings or native FILE gates.
}
