// AUTHORED SOURCE ONLY: not compiled or executed. Future Windows fixture needs
// one explicit owned synthetic root argument, its own lease/budget and distinct GO.
#include "native_pair_file_ingress.hpp"
#include <cstdio>
#include <type_traits>

namespace
{
    namespace file = player_pair_file_ingress;
    using player_pair_input::Role;
    static_assert(!std::is_constructible_v<file::Guards, file::CleanupReport&>);
    static_assert(!std::is_copy_constructible_v<file::Guards> && !std::is_move_constructible_v<file::Guards>);
    static_assert(!std::is_copy_constructible_v<file::CleanupReport> && !std::is_move_constructible_v<file::CleanupReport>);
    constexpr std::array<std::string_view, 4> raw{
        "report-source\n", "weapon-source\n", "attachment-source\n", "csv-source\n"};
    constexpr std::array<std::string_view, 4> hashes{
        "65b4744a4d36ef58603ec6757f73574971b3ef8690b6422c8179e749a6626db8",
        "ad54215e37875e76afd6247b7ca7d0531b8564a886c7fc8cd76520f1770f3d6f",
        "f9fe56677a2930d88049578083a627f40b28e55a409930abeb6cf2cdf92b6e1c",
        "96a17c5522efeed666fd2418c25c07c87550cb24c47a4319950ac4241127f5a0"};
    void need(bool value) { if (!value) throw std::runtime_error("Authored file ingress witness refused"); }
    struct TempCleanup { unsigned close_failures{}; bool deletion_failed{}; };
    class CreatorHandle final
    {
        HANDLE value_;
        TempCleanup& cleanup_;
    public:
        CreatorHandle(HANDLE value, TempCleanup& cleanup) noexcept : value_(value), cleanup_(cleanup) {}
        CreatorHandle(const CreatorHandle&) = delete;
        CreatorHandle& operator=(const CreatorHandle&) = delete;
        ~CreatorHandle() noexcept { if (value_ != INVALID_HANDLE_VALUE) close(); }
        bool close() noexcept
        {
            const auto result = ::CloseHandle(value_);
            if (!result) ++cleanup_.close_failures;
            value_ = INVALID_HANDLE_VALUE;
            return result != FALSE;
        }
    };
    class SyntheticFiles final
    {
        TempCleanup& cleanup_;
        std::wstring directory_;
        std::array<std::wstring, 5> paths_;
        std::array<bool, 5> created_{};
        bool directory_created_{};
        file::Files specs_{};
        file::Identity create(std::size_t i, std::string_view bytes)
        {
            const auto handle = ::CreateFileW(paths_[i].c_str(), GENERIC_READ | GENERIC_WRITE,
                FILE_SHARE_READ, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
            need(handle != INVALID_HANDLE_VALUE);
            created_[i] = true;
            CreatorHandle owned(handle, cleanup_); // Enroll before WriteFile/metadata or assertions.
            DWORD written{};
            need(::WriteFile(handle, bytes.data(), static_cast<DWORD>(bytes.size()), &written, nullptr) != FALSE);
            need(written == bytes.size() && ::FlushFileBuffers(handle) != FALSE);
            FILE_ID_INFO id{};
            need(::GetFileInformationByHandleEx(handle, FileIdInfo, &id, static_cast<DWORD>(sizeof(id))) != FALSE);
            file::Identity result{}; result.volume = id.VolumeSerialNumber;
            for (std::size_t n = 0; n < result.file_id.size(); ++n) result.file_id[n] = id.FileId.Identifier[n];
            need(owned.close());
            return result; // Independent creator metadata captured BEFORE the product reader exists.
        }
    public:
        SyntheticFiles(std::wstring_view root, TempCleanup& cleanup) : cleanup_(cleanup), directory_(root)
        {
            directory_ += L"\\owned-file-ingress-fixture";
            need(file::detail::path(directory_ + L"\\request.raw"));
            constexpr std::array<const wchar_t*, 5> names{
                L"report.raw", L"weapon.raw", L"attachment.raw", L"csv.raw", L"foreign-report.raw"};
            for (std::size_t i = 0; i < paths_.size(); ++i) paths_[i] = directory_ + L"\\" + names[i];
        }
        SyntheticFiles(const SyntheticFiles&) = delete;
        SyntheticFiles& operator=(const SyntheticFiles&) = delete;
        void prepare()
        {
            // Fresh owned subdirectory only. No GetTempPath, search, reuse or recursive deletion.
            need(::CreateDirectoryW(directory_.c_str(), nullptr) != FALSE);
            directory_created_ = true;
            for (std::size_t i = 0; i < specs_.size(); ++i)
            {
                specs_[i].role = static_cast<Role>(i); specs_[i].path = paths_[i];
                specs_[i].bytes = raw[i].size();
                need(hashes[i].size() == specs_[i].sha256.size());
                for (std::size_t n = 0; n < hashes[i].size(); ++n) specs_[i].sha256[n] = hashes[i][n];
                specs_[i].expected = create(i, raw[i]);
            }
            const auto foreign = create(4, raw[0]);
            need(!file::same_identity(foreign, specs_[0].expected));
        }
        ~SyntheticFiles() noexcept
        {
            for (std::size_t n = paths_.size(); n != 0; --n)
                if (created_[n - 1] && !::DeleteFileW(paths_[n - 1].c_str())) cleanup_.deletion_failed = true;
            if (directory_created_ && !::RemoveDirectoryW(directory_.c_str())) cleanup_.deletion_failed = true;
        }
        const file::Files& specs() const noexcept { return specs_; }
        const std::wstring& foreign() const noexcept { return paths_[4]; }
        std::wstring missing() const { return directory_ + L"\\never-created.raw"; }
    };
    void closed(const file::CleanupReport& report, unsigned count)
    {
        const auto& state = report.observations();
        need(state.acquired == count);
        for (const auto& row : state.roles)
        {
            if (row.acquired)
                need(row.original_handle != 0 && row.close_attempted && row.close_returned &&
                    row.close_result != FALSE && row.close_error == ERROR_SUCCESS);
            else need(!row.close_attempted && !row.close_returned);
        }
    }
    void refused_before_read(const file::Files& specs, file::Operation operation, std::size_t role, unsigned acquired)
    {
        file::CleanupReport report;
        player_pair_input::Counters counters;
        bool refused = false;
        try { auto value = file::read_owned_files(specs, report, counters); }
        catch (const file::IngressError&)
        {
            refused = true;
            const auto& state = report.observations();
            need(state.primary_present && state.primary.operation == operation && state.primary.role == role);
            need(bool(report.primary_exception()));
            bool retained_primary = false;
            try { std::rethrow_exception(report.primary_exception()); }
            catch (const file::IngressError&) { retained_primary = true; }
            need(retained_primary); // Exception_ptr captures the primary; no MSVC pointer-equality assumption.
        }
        need(refused && report.observations().read_calls == 0 && counters.copies == 0 && counters.hashes == 0);
        closed(report, acquired);
    }
    void request_caps_and_paths_before_open(const file::Files& original)
    {
        auto bad = original; bad[3].role = Role::weapon;
        refused_before_read(bad, file::Operation::request, 3, 0);
        bad = original; bad[3].bytes = 67;
        refused_before_read(bad, file::Operation::request, 3, 0);
        bad = original; bad[0].bytes = 0;
        refused_before_read(bad, file::Operation::request, 0, 0);
        bad = original; bad[2].sha256[63] = 'G';
        refused_before_read(bad, file::Operation::request, 2, 0);
        constexpr std::array<const wchar_t*, 9> invalid{
            L"relative.raw", L"C:relative.raw", L"\\\\?\\C:\\x.raw", L"C:\\x.raw:stream",
            L"C:\\a\\..\\x.raw", L"C:\\NUL.txt", L"C:\\x. ", L"C:/x.raw", L"C:\\a\\\\x.raw"};
        for (const auto* path : invalid)
        { bad = original; bad[3].path = path; refused_before_read(bad, file::Operation::request, 3, 0); }
        bad = original; bad[3].path.push_back(L'\0'); bad[3].path += L"suffix";
        refused_before_read(bad, file::Operation::request, 3, 0);
        bad = original; bad[3].path.push_back(static_cast<wchar_t>(0xd800));
        refused_before_read(bad, file::Operation::request, 3, 0);
    }
    void same_handles_raw_copy_hashes(const file::Files& specs)
    {
        file::CleanupReport report;
        player_pair_input::Counters counters;
        auto ingress = file::read_owned_files(specs, report, counters);
        const auto& state = report.observations();
        need(state.acquired == 4 && state.metadata_complete == 4 && state.read_calls == 4 &&
            state.first_read_acquired == 4 && state.first_read_metadata == 4 && state.raw_copy_complete);
        need(!state.primary_present && !report.primary_exception() && counters.copies == 4 && counters.hashes == 4);
        for (std::size_t i = 0; i < specs.size(); ++i)
        {
            const auto& row = state.roles[i];
            need(row.original_handle == row.read_handle && row.read_complete && !row.close_attempted);
            need(row.read_bytes == specs[i].bytes && row.observed_bytes == specs[i].bytes && row.final_bytes == specs[i].bytes);
            need(file::same_identity(row.expected, specs[i].expected) && file::same_identity(row.observed, specs[i].expected));
            const auto role = static_cast<Role>(i);
            need(std::string_view(ingress->input().bytes(role)) == raw[i] && ingress->input().pin(role).sha256 == hashes[i]);
        }
        ingress.reset();
        closed(report, 4); // Report remains the same original object after guard destruction.
    }
    void guards_block_write_and_delete(const file::Files& specs, TempCleanup& cleanup)
    {
        file::CleanupReport report;
        player_pair_input::Counters counters;
        auto ingress = file::read_owned_files(specs, report, counters);
        for (const auto access : {DWORD{GENERIC_WRITE}, DWORD{DELETE}})
        {
            const auto attempt = ::CreateFileW(specs[0].path.c_str(), access,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
            const auto error = attempt == INVALID_HANDLE_VALUE ? ::GetLastError() : ERROR_SUCCESS;
            if (attempt != INVALID_HANDLE_VALUE) { CreatorHandle unexpected(attempt, cleanup); need(false); }
            need(error == ERROR_SHARING_VIOLATION);
        }
        ingress.reset(); closed(report, 4);
    }
    void fourth_open_failure_primary_and_cleanup(const SyntheticFiles& files)
    {
        auto bad = files.specs(); bad[3].path = files.missing();
        refused_before_read(bad, file::Operation::open, 3, 3);
    }
    void independent_volume_and_file_id(const file::Files& original)
    {
        auto bad = original; bad[0].expected.volume ^= 1;
        refused_before_read(bad, file::Operation::identity, 0, 1);
        bad = original; bad[0].expected.file_id[15] ^= 1;
        refused_before_read(bad, file::Operation::identity, 0, 1);
    }
    void same_content_foreign_and_role_alias(const SyntheticFiles& files)
    {
        auto bad = files.specs(); bad[0].path = files.foreign();
        refused_before_read(bad, file::Operation::identity, 0, 1);
        bad = files.specs(); bad[2] = bad[1]; bad[2].role = Role::attachment;
        refused_before_read(bad, file::Operation::alias, 2, 3);
    }
    void metadata_and_private_copy_pin_refusals(const file::Files& original)
    {
        auto bad = original; --bad[0].bytes;
        refused_before_read(bad, file::Operation::length, 0, 1);
        bad = original; ++bad[0].bytes;
        refused_before_read(bad, file::Operation::length, 0, 1);
        bad = original; bad[3].sha256[0] = bad[3].sha256[0] == '0' ? '1' : '0';
        file::CleanupReport report;
        player_pair_input::Counters counters;
        bool refused = false;
        try { auto value = file::read_owned_files(bad, report, counters); }
        catch (const player_pair_input::PinError&)
        {
            refused = true;
            need(report.observations().primary_present && report.observations().primary.operation == file::Operation::copy);
            bool retained = false;
            try { std::rethrow_exception(report.primary_exception()); }
            catch (const player_pair_input::PinError&) { retained = true; }
            need(retained);
        }
        need(refused && report.observations().read_calls == 4 && !report.observations().raw_copy_complete);
        need(counters.copies == 4 && counters.hashes == 4);
        closed(report, 4); // Real OwnedInput hash failure after the unique guard transfer.
    }
    void report_lifetime_and_single_use(const file::Files& specs)
    {
        file::CleanupReport report;
        const auto* original = &report.observations();
        player_pair_input::Counters counters;
        { auto value = file::read_owned_files(specs, report, counters); }
        closed(report, 4);
        bool refused = false;
        try { auto value = file::read_owned_files(specs, report, counters); }
        catch (const std::logic_error&) { refused = true; }
        need(refused && &report.observations() == original && report.observations().read_calls == 4 &&
            report.observations().raw_copy_complete && !report.observations().primary_present);
        closed(report, 4);
    }
}

int wmain(int argc, wchar_t** argv)
{
    TempCleanup cleanup;
    try
    {
        need(argc == 2); // Future recipe supplies one explicit owned root; no global temp fallback.
        {
            SyntheticFiles files(argv[1], cleanup); files.prepare();
            request_caps_and_paths_before_open(files.specs()); std::puts("PASS: request_caps_and_paths_before_open");
            same_handles_raw_copy_hashes(files.specs()); std::puts("PASS: same_handles_raw_copy_hashes");
            guards_block_write_and_delete(files.specs(), cleanup); std::puts("PASS: guards_block_write_and_delete");
            fourth_open_failure_primary_and_cleanup(files); std::puts("PASS: fourth_open_failure_primary_and_cleanup");
            independent_volume_and_file_id(files.specs()); std::puts("PASS: independent_volume_and_file_id");
            same_content_foreign_and_role_alias(files); std::puts("PASS: same_content_foreign_and_role_alias");
            metadata_and_private_copy_pin_refusals(files.specs()); std::puts("PASS: metadata_and_private_copy_pin_refusals");
            report_lifetime_and_single_use(files.specs()); std::puts("PASS: report_lifetime_and_single_use");
        }
        need(cleanup.close_failures == 0 && !cleanup.deletion_failed);
        std::puts("PASS: authored-pair-file-ingress-windows");
        return 0;
    }
    catch (const std::exception& error)
    {
        std::fprintf(stderr, "%s; synthetic_close_failures=%u synthetic_delete_failed=%u\n",
            error.what(), cleanup.close_failures, static_cast<unsigned>(cleanup.deletion_failed));
        return 2;
    }
    // No fixture branch can safely force ReadFile short/error or CloseHandle FALSE
    // without changing the production boundary. Those paths remain unexecuted and
    // unqualified; there is no injection seam or claim of fatal/OS allocator closure.
}
