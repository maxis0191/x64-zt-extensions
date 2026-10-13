// Original synthetic inputs only. Compile/link/run requires the reviewed heavy-stage GO.
#include "streamed_mesh_payload.hpp"
#include <lz4.h> // Link the pinned dependency's deps/lz4/lib/lz4.c; do not copy it here.

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <initializer_list>
#include <limits>
#include <span>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#ifdef _WIN32
#include <filesystem>
#endif

namespace xpak = zonetool::t7::selected_xpak;

namespace
{
    using bytes = std::vector<std::uint8_t>;
    constexpr std::uint32_t expected_size = 18624;
    constexpr std::uint64_t selected_key = 0x0123456789abcdefULL;
    constexpr std::uint64_t high_size_bits = 0xa500000000000000ULL;
    constexpr std::size_t header_bytes = 120, hash_offset = 128, data_offset = 193;
    unsigned copied_cases = 0, refused_cases = 0, sealing_cases = 0;

    void check(bool condition, const char* reason)
    {
        if (!condition) throw std::runtime_error(std::string("fixture: ") + reason);
    }

    template <typename T> void put(bytes& out, std::size_t offset, T value)
    {
        if (offset > out.size() || sizeof(T) > out.size() - offset)
            throw std::runtime_error("fixture field outside synthetic storage");
        for (std::size_t n = 0; n < sizeof(T); ++n)
            out[offset + n] = static_cast<std::uint8_t>(value >> (n * 8u));
    }

    bytes original_bytes(std::size_t size = expected_size)
    {
        bytes out(size);
        for (std::size_t n = 0; n < size; ++n)
            out[n] = static_cast<std::uint8_t>(((n / 64u) * 17u + (n % 11u)) & 255u);
        return out;
    }

    bytes slice(const bytes& input, std::size_t first, std::size_t size)
    {
        return bytes(input.begin() + first, input.begin() + first + size);
    }

    bytes compressed(const bytes& input)
    {
        const auto length = static_cast<int>(input.size());
        bytes out(static_cast<std::size_t>(LZ4_compressBound(length)));
        const auto written = LZ4_compress_default(reinterpret_cast<const char*>(input.data()),
            reinterpret_cast<char*>(out.data()), length, static_cast<int>(out.size()));
        check(written > 0, "real LZ4 compression failed");
        out.resize(static_cast<std::size_t>(written));
        return out;
    }

    struct block
    {
        std::uint8_t codec;
        bytes encoded;
    };

    // Padding is relative to the selected extent, whose absolute offset is deliberately unaligned.
    void append_group(bytes& extent, std::initializer_list<block> blocks, std::uint32_t opaque_offset = 0)
    {
        if (!extent.empty()) extent.resize((extent.size() + 127u) & ~std::size_t{127u}, 0x6d);
        const auto start = extent.size();
        extent.resize(start + 128u);
        put(extent, start, static_cast<std::uint32_t>(blocks.size()));
        put(extent, start + 4u, opaque_offset);
        std::size_t command = start + 8u;
        for (const auto& item : blocks)
        {
            put(extent, command, (static_cast<std::uint32_t>(item.codec) << 24u)
                | static_cast<std::uint32_t>(item.encoded.size()));
            command += 4u;
            extent.insert(extent.end(), item.encoded.begin(), item.encoded.end());
        }
    }

    bytes one_group(std::uint8_t codec, bytes body, std::uint32_t opaque_offset = 0)
    {
        bytes out;
        append_group(out, {{codec, std::move(body)}}, opaque_offset);
        return out;
    }

    struct memory_file
    {
        bytes storage;
        std::uint64_t file_size = 0;
        std::size_t payload_begin = data_offset;
        unsigned header_reads = 0, index_reads = 0, payload_reads = 0;
        std::uint64_t short_at = (std::numeric_limits<std::uint64_t>::max)();

        std::size_t read(std::uint64_t offset, std::span<std::uint8_t> destination)
        {
            if (offset >= payload_begin) ++payload_reads;
            else if (offset >= hash_offset) ++index_reads;
            else ++header_reads;
            // A malformed request cannot turn the fixture into an arbitrary read or allocation.
            if (offset > storage.size() || destination.size() > storage.size() - offset)
                throw std::runtime_error("synthetic request outside stored bytes");
            const auto count = destination.size() - ((offset == short_at && !destination.empty()) ? 1u : 0u);
            std::copy_n(storage.data() + static_cast<std::size_t>(offset), count, destination.data());
            return count;
        }

        xpak::package package(std::string name = "synthetic-a", std::string identity = "fixture-a")
        {
            return {std::move(name), std::move(identity), file_size,
                [this](std::uint64_t offset, std::span<std::uint8_t> out) { return read(offset, out); }};
        }
    };

    memory_file make_file(const bytes& extent, std::uint64_t key = selected_key)
    {
        memory_file value;
        value.storage.resize(data_offset);
        value.storage.insert(value.storage.end(), extent.begin(), extent.end());
        value.file_size = value.storage.size();
        put(value.storage, 0u, std::uint32_t{0x4950414b});
        put(value.storage, 6u, std::uint16_t{0x000a});
        put(value.storage, 32u, std::uint64_t{data_offset});
        put(value.storage, 40u, static_cast<std::uint64_t>(extent.size()));
        put(value.storage, 48u, std::uint64_t{1});
        put(value.storage, 56u, std::uint64_t{hash_offset});
        put(value.storage, 64u, std::uint64_t{24});
        put(value.storage, hash_offset, key);
        put(value.storage, hash_offset + 8u, std::uint64_t{0});
        put(value.storage, hash_offset + 16u, high_size_bits | extent.size());
        return value;
    }

    xpak::payload read(memory_file& value, std::uint64_t key = selected_key,
        std::uint32_t expected = expected_size, xpak::lz4_decoder decoder = &LZ4_decompress_safe)
    {
        const std::array packages{value.package()};
        return xpak::read_selected_key(packages, key, expected, decoder);
    }

    template <typename Action> void refusal(const char* label, Action action)
    {
        bool refused = false;
        try { action(); }
        catch (const std::runtime_error&) { refused = true; }
        check(refused, label);
        ++refused_cases;
    }

    template <typename Change> void malformed(const char* label, const bytes& extent, Change change,
        bool forbid_payload = false)
    {
        auto value = make_file(extent);
        change(value);
        refusal(label, [&] { (void)read(value); });
        if (forbid_payload) check(value.payload_reads == 0, "invalid index caused payload read");
    }

    void roundtrip(const bytes& extent, const bytes& expected, std::vector<std::uint8_t> codecs,
        std::vector<std::uint32_t> offsets, std::uint64_t declared_hash_bytes = 24)
    {
        auto value = make_file(extent);
        put(value.storage, 64u, declared_hash_bytes);
        auto result = read(value);
        const auto& seen = result.observed;
        check(result.bytes == expected, "decoded output differs from original synthetic bytes");
        check(seen.package_name == "synthetic-a" && seen.package_identity == "fixture-a"
            && seen.file_bytes == value.file_size && seen.key == selected_key
            && seen.hash_table_offset == hash_offset && seen.hash_entry_offset == hash_offset
            && seen.payload_offset == data_offset && seen.compressed_bytes == extent.size()
            && seen.packed_entry_size == (high_size_bits | extent.size()) && seen.indexed_bytes == 24
            && seen.opcodes == codecs && seen.header_offsets == offsets,
            "observation lost selected identity, original packed bits or opaque group offsets");
        const auto before = result.bytes.front();
        value.storage[data_offset + 128u] ^= 0xffu;
        check(result.bytes.front() == before, "payload result aliases source storage");
        ++copied_cases;
    }

    int zero_decoder(const char*, char*, int, int) { return 0; }
    int failed_decoder(const char*, char*, int, int) { return -1; }
    int oversized_decoder(const char*, char*, int, int capacity) { return capacity + 1; }

    void run_generic()
    {
        for (const auto size : {std::uint32_t{1}, std::uint32_t{1024}, xpak::max_decoded_bytes})
        {
            const auto original = original_bytes(size);
            auto file = make_file(size == xpak::max_decoded_bytes ?
                one_group(3, compressed(original)) : one_group(0, original));
            const std::array packages{file.package()};
            auto result = xpak::read_bounded_selected_key(packages, selected_key, size, &LZ4_decompress_safe);
            check(result.bytes == original, "generic exact-size roundtrip differs");
            file.storage[data_offset + 128u] ^= 0xffu;
            check(result.bytes == original, "generic result aliases input");
            ++copied_cases;
        }
        auto single = make_file(one_group(0, bytes{42}));
        const std::array packages{single.package()};
        for (const auto size : {std::uint32_t{0}, xpak::max_decoded_bytes + 1u})
            refusal("generic decoded bound accepted", [&] {
                (void)xpak::read_bounded_selected_key(packages, selected_key, size, &LZ4_decompress_safe);
            });
        check(single.header_reads == 0 && single.payload_reads == 0, "generic bound refusal read input");
        for (const auto size : {std::uint32_t{1}, xpak::max_decoded_bytes})
            refusal("strict mesh wrapper accepts generic size", [&] {
                (void)xpak::read_selected_key(packages, selected_key, size, &LZ4_decompress_safe);
            });
        check(single.header_reads == 0, "strict mesh wrapper refusal read input");
        refusal("generic decoded-length mismatch accepted", [&] {
            (void)xpak::read_bounded_selected_key(packages, selected_key, 2, &LZ4_decompress_safe);
        });
        auto truncated = make_file(bytes(127));
        const std::array short_group{truncated.package()};
        refusal("generic truncated command header accepted", [&] {
            (void)xpak::read_bounded_selected_key(short_group, selected_key, 1, &LZ4_decompress_safe);
        });
        auto lz4 = make_file(one_group(3, compressed(bytes{42})));
        const std::array compressed_package{lz4.package()};
        refusal("generic oversized LZ4 return accepted", [&] {
            (void)xpak::read_bounded_selected_key(compressed_package, selected_key, 1, &oversized_decoder);
        });
    }

    void run()
    {
        run_generic();
        const auto original = original_bytes();
        const auto raw = one_group(0, original, 0x89abcdefu);
        const auto lz4 = one_group(3, compressed(original));
        roundtrip(raw, original, {0}, {0x89abcdefu});
        roundtrip(lz4, original, {3}, {0}); // Genuine pinned LZ4 compression/decompression roundtrip.

        bytes mixed;
        append_group(mixed, {{0, slice(original, 0, 1000)},
            {3, compressed(slice(original, 1000, expected_size - 1000))}}, 37);
        roundtrip(mixed, original, {0, 3}, {37});
        bytes groups;
        append_group(groups, {{0, slice(original, 0, 1000)}}, 7);
        append_group(groups, {{3, compressed(slice(original, 1000, expected_size - 1000))}}, 0x55667788u);
        roundtrip(groups, original, {0, 3}, {7, 0x55667788u});
        auto padded = raw;
        padded.resize((padded.size() + 127u) & ~std::size_t{127u}, 0xa5);
        roundtrip(padded, original, {0}, {0x89abcdefu});
        roundtrip(raw, original, {0}, {0x89abcdefu}, 32); // Declared index padding is charged, not scanned.

        // Every explicitly supplied index is inspected before any unique-match payload read.
        auto first = make_file(raw, selected_key + 1u), second = make_file(lz4);
        const std::array two{first.package("first", "first-id"), second.package("second", "second-id")};
        const auto result = xpak::read_selected_key(two, selected_key, expected_size, &LZ4_decompress_safe);
        check(result.bytes == original && result.observed.package_name == "second"
            && result.observed.package_identity == "second-id" && result.observed.indexed_bytes == 48
            && first.index_reads > 0 && first.payload_reads == 0 && second.index_reads > 0,
            "all-index scan or aggregate index observation failed");
        ++copied_cases;

        auto absent = make_file(raw);
        refusal("absent key accepted", [&] { (void)read(absent, selected_key + 1u); });
        check(absent.index_reads > 0 && absent.payload_reads == 0, "absent key read payload or skipped index");
        auto a = make_file(raw), b = make_file(lz4);
        const std::array ambiguous{a.package(), b.package("other", "other-id")};
        refusal("cross-package duplicate accepted", [&] {
            (void)xpak::read_selected_key(ambiguous, selected_key, expected_size, &LZ4_decompress_safe);
        });
        check(a.index_reads > 0 && b.index_reads > 0 && a.payload_reads == 0 && b.payload_reads == 0,
            "ambiguity was resolved by reading a payload");
        malformed("same-index duplicate accepted", raw, [](memory_file& f) {
            put(f.storage, 48u, std::uint64_t{2});
            put(f.storage, 64u, std::uint64_t{48});
            const bytes entry(f.storage.begin() + hash_offset, f.storage.begin() + hash_offset + 24u);
            std::copy(entry.begin(), entry.end(), f.storage.begin() + hash_offset + 24u);
        }, true);
        auto good = make_file(raw), malformed_other = make_file(lz4, selected_key + 1u);
        put(malformed_other.storage, 0u, std::uint32_t{0});
        const std::array unchecked_other{good.package(), malformed_other.package("other", "other-id")};
        refusal("later malformed package ignored", [&] {
            (void)xpak::read_selected_key(unchecked_other, selected_key, expected_size, &LZ4_decompress_safe);
        });
        check(good.payload_reads == 0 && malformed_other.payload_reads == 0,
            "unique match read before validating later package");

        malformed("bad magic accepted", raw, [](memory_file& f) { put(f.storage, 0u, std::uint32_t{0}); }, true);
        malformed("bad version accepted", raw, [](memory_file& f) { put(f.storage, 6u, std::uint16_t{9}); }, true);
        malformed("short header accepted", raw, [](memory_file& f) { f.short_at = 0; }, true);
        malformed("short index accepted", raw, [](memory_file& f) { f.short_at = hash_offset; }, true);
        malformed("short payload accepted", raw, [](memory_file& f) { f.short_at = data_offset; });
        malformed("short file header accepted", raw, [](memory_file& f) { f.file_size = header_bytes - 1; }, true);
        malformed("hash count multiplication overflow accepted", raw, [](memory_file& f) {
            put(f.storage, 48u, (std::numeric_limits<std::uint64_t>::max)());
        }, true);
        malformed("hash size/count mismatch accepted", raw, [](memory_file& f) { put(f.storage, 64u, std::uint64_t{23}); }, true);
        malformed("hash range overflow accepted", raw, [](memory_file& f) {
            put(f.storage, 56u, (std::numeric_limits<std::uint64_t>::max)() - 8u);
        }, true);
        malformed("data range overflow accepted", raw, [](memory_file& f) {
            f.file_size = (std::numeric_limits<std::uint64_t>::max)();
            put(f.storage, 32u, f.file_size - 8u);
            put(f.storage, 40u, std::uint64_t{32});
        }, true);
        malformed("entry range outside data accepted", raw, [](memory_file& f) {
            put(f.storage, hash_offset + 8u, std::uint64_t{1});
        }, true);
        malformed("entry offset overflow accepted", raw, [](memory_file& f) {
            put(f.storage, hash_offset + 8u, (std::numeric_limits<std::uint64_t>::max)());
        }, true);
        malformed("zero selected extent accepted", raw, [](memory_file& f) {
            put(f.storage, hash_offset + 16u, high_size_bits);
        }, true);
        malformed("compressed budget exceeded", raw, [](memory_file& f) {
            constexpr std::uint64_t too_many = 256u * 1024u + 1u;
            f.file_size = data_offset + too_many;
            put(f.storage, 40u, too_many);
            put(f.storage, hash_offset + 16u, high_size_bits | too_many);
        }, true);

        // Two original indexes occupy exactly 8 MiB including eight unused padding bytes.
        // Increasing only that padding by one byte must fail the aggregate admission.
        constexpr std::uint64_t entries = (4u * 1024u * 1024u) / 24u + 1u;
        std::array<memory_file, 2> large;
        for (std::size_t file = 0; file < large.size(); ++file)
        {
            auto& f = large[file];
            const auto count = entries - file;
            f = make_file({});
            f.payload_begin = hash_offset + static_cast<std::size_t>(count * 24u) + 17u;
            f.storage.reserve(f.payload_begin + raw.size());
            f.storage.resize(f.payload_begin);
            f.storage.insert(f.storage.end(), raw.begin(), raw.end());
            f.file_size = f.storage.size();
            put(f.storage, 32u, static_cast<std::uint64_t>(f.payload_begin));
            put(f.storage, 40u, static_cast<std::uint64_t>(raw.size()));
            put(f.storage, 48u, count);
            put(f.storage, 64u, count * 24u + (file ? 8u : 0u));
            for (std::uint64_t row = 0; row < count; ++row)
            {
                const auto at = hash_offset + static_cast<std::size_t>(row * 24u);
                put(f.storage, at, row + file * entries);
                put(f.storage, at + 8u, std::uint64_t{0});
                put(f.storage, at + 16u, std::uint64_t{0});
            }
        }
        put(large[0].storage, hash_offset, selected_key);
        put(large[0].storage, hash_offset + 16u, high_size_bits | raw.size());
        const std::array budget_packages{large[0].package("budget-a", "budget-a-id"),
            large[1].package("budget-b", "budget-b-id")};
        const auto exact_budget = xpak::read_selected_key(budget_packages, selected_key, expected_size, &LZ4_decompress_safe);
        check(exact_budget.bytes == original && exact_budget.observed.indexed_bytes == 8u * 1024u * 1024u - 8u,
            "exact aggregate index budget was not admitted or padding was scanned");
        ++copied_cases;
        large[0].payload_reads = large[1].payload_reads = 0;
        put(large[1].storage, 64u, (entries - 1u) * 24u + 9u);
        refusal("aggregate index budget exceeded", [&] {
            (void)xpak::read_selected_key(budget_packages, selected_key, expected_size, &LZ4_decompress_safe);
        });
        check(large[0].payload_reads == 0 && large[1].payload_reads == 0,
            "aggregate budget failure initiated payload read");

        auto profile = make_file(raw);
        refusal("wrong expected-size profile accepted", [&] { (void)read(profile, selected_key, expected_size - 1u); });
        check(profile.header_reads == 0 && profile.index_reads == 0 && profile.payload_reads == 0,
            "unsupported profile initiated input reads");
        std::array<xpak::package, 9> excessive;
        for (auto& item : excessive) item = profile.package();
        refusal("nine packages accepted", [&] {
            (void)xpak::read_selected_key(excessive, selected_key, expected_size, &LZ4_decompress_safe);
        });
        check(profile.header_reads == 0 && profile.index_reads == 0 && profile.payload_reads == 0,
            "package cap initiated input reads");
        std::array<memory_file, 8> admitted;
        std::array<xpak::package, 8> at_package_limit;
        for (std::size_t n = 0; n < admitted.size(); ++n)
        {
            admitted[n] = make_file(raw, selected_key + n);
            const auto id = std::string("limit-") + std::to_string(n);
            at_package_limit[n] = admitted[n].package(id, id);
        }
        const auto eight = xpak::read_selected_key(at_package_limit, selected_key, expected_size, &LZ4_decompress_safe);
        check(eight.bytes == original && eight.observed.indexed_bytes == 8u * 24u
            && std::all_of(admitted.begin(), admitted.end(), [](const memory_file& f) { return f.index_reads > 0; }),
            "eight valid package indexes were not admitted and scanned");
        ++copied_cases;
        refusal("empty package list accepted", [&] {
            (void)xpak::read_selected_key({}, selected_key, expected_size, &LZ4_decompress_safe);
        });

        auto count_zero = raw;
        put(count_zero, 0u, std::uint32_t{0});
        auto count_large = raw;
        put(count_large, 0u, std::uint32_t{31});
        auto unsupported = raw;
        put(unsupported, 8u, std::uint32_t{0x02000000u | expected_size});
        auto block_truncated = raw;
        put(block_truncated, 8u, std::uint32_t{expected_size + 1u});
        auto partial_padding = raw;
        partial_padding.push_back(0xa5);
        auto trailing_group = raw;
        append_group(trailing_group, {{0, bytes{1}}});
        struct bad_payload { const char* label; bytes extent; };
        const bad_payload malformed_payloads[] = {
            {"zero group count accepted", count_zero}, {"31 commands accepted", count_large},
            {"unsupported codec accepted", unsupported}, {"truncated command block accepted", block_truncated},
            {"truncated group header accepted", bytes(127u)},
            {"partial raw output accepted", one_group(0, original_bytes(expected_size - 1u))},
            {"raw output overflow accepted", one_group(0, original_bytes(expected_size + 1u))},
            {"partial terminal padding accepted", partial_padding}, {"trailing command group accepted", trailing_group},
            {"empty LZ4 block accepted", one_group(3, bytes{})}, {"invalid LZ4 block accepted", one_group(3, bytes{0xff})},
            {"partial LZ4 output accepted", one_group(3, compressed(original_bytes(expected_size - 1u)))}};
        for (const auto& test : malformed_payloads)
        {
            auto value = make_file(test.extent);
            refusal(test.label, [&] { (void)read(value); });
        }
        for (const auto decoder : {&zero_decoder, &failed_decoder, &oversized_decoder})
        {
            auto value = make_file(lz4);
            refusal("invalid signed LZ4 result accepted", [&] { (void)read(value, selected_key, expected_size, decoder); });
        }
        auto no_decoder = make_file(lz4);
        refusal("missing LZ4 decoder accepted", [&] { (void)read(no_decoder, selected_key, expected_size, nullptr); });

        bytes excessive_groups;
        for (unsigned n = 0; n < 128; ++n)
        {
            const auto start = excessive_groups.size();
            if (start) excessive_groups.resize((start + 127u) & ~std::size_t{127u}, 0x6d);
            const auto header = excessive_groups.size();
            excessive_groups.resize(header + 128u);
            put(excessive_groups, header, std::uint32_t{30});
            for (unsigned command = 0; command < 30; ++command)
                put(excessive_groups, header + 8u + command * 4u, std::uint32_t{4});
            excessive_groups.insert(excessive_groups.end(), 120u, 0x3b);
        }
        // The last of 3840 raw commands supplies the remainder without adding a 129th group.
        auto at_group_limit = excessive_groups;
        const auto last_header = 127u * 256u;
        put(at_group_limit, last_header + 8u + 29u * 4u, std::uint32_t{4u + expected_size - 128u * 120u});
        at_group_limit.insert(at_group_limit.end(), expected_size - 128u * 120u, 0x3b);
        auto boundary = make_file(at_group_limit);
        const auto complete = read(boundary);
        check(complete.bytes == bytes(expected_size, 0x3b) && complete.observed.opcodes == std::vector<std::uint8_t>(3840u, 0)
            && complete.observed.header_offsets == std::vector<std::uint32_t>(128u, 0),
            "128 groups / 3840 blocks were not admitted");
        ++copied_cases;
        append_group(excessive_groups, {{0, bytes(expected_size - 128u * 120u, 0x3b)}});
        auto too_many_groups = make_file(excessive_groups);
        refusal("129 groups / 3841 blocks accepted", [&] { (void)read(too_many_groups); });
        check(copied_cases == 13 && refused_cases == 46, "fixture case inventory changed");
    }

#ifdef _WIN32
    class owned_handle
    {
        HANDLE value_;
    public:
        explicit owned_handle(HANDLE value) : value_(value) {}
        owned_handle(const owned_handle&) = delete;
        owned_handle& operator=(const owned_handle&) = delete;
        ~owned_handle() { if (value_ != INVALID_HANDLE_VALUE) CloseHandle(value_); }
        HANDLE get() const { return value_; }
    };

    // Own exactly one newly created directory and one CREATE_NEW file. Never recurse or overwrite.
    class synthetic_temp_package
    {
        std::filesystem::path directory_, file_;
        bool directory_created_ = false, file_created_ = false;

        void cleanup() noexcept
        {
            if (file_created_)
            {
                if (!DeleteFileW(file_.c_str())) std::fputs("synthetic fixture file cleanup failed\n", stderr);
                else file_created_ = false;
            }
            if (directory_created_)
            {
                if (!RemoveDirectoryW(directory_.c_str())) std::fputs("synthetic fixture directory cleanup failed\n", stderr);
                else directory_created_ = false;
            }
        }

    public:
        explicit synthetic_temp_package(const bytes& input)
        {
            try
            {
                std::array<wchar_t, 32768> temporary{};
                const auto length = GetTempPathW(static_cast<DWORD>(temporary.size()), temporary.data());
                check(length > 0 && length < temporary.size(), "Windows temporary path unavailable");
                const std::filesystem::path proposed(std::wstring(temporary.data(), length));
                check(proposed.is_absolute(), "Windows temporary path is not absolute");
                // TMP may use short names, junctions or different casing. Admit the final local DOS path.
                owned_handle parent_handle(CreateFileW(proposed.c_str(), FILE_READ_ATTRIBUTES,
                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
                    FILE_FLAG_BACKUP_SEMANTICS, nullptr));
                check(parent_handle.get() != INVALID_HANDLE_VALUE, "Windows temporary directory could not be opened");
                BY_HANDLE_FILE_INFORMATION parent_info{};
                check(GetFileInformationByHandle(parent_handle.get(), &parent_info)
                    && (parent_info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY), "Windows temporary parent is not a directory");
                const auto capacity = GetFinalPathNameByHandleW(parent_handle.get(), nullptr, 0,
                    FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
                check(capacity > 0 && capacity <= 32767, "Windows temporary directory final path unavailable");
                std::vector<wchar_t> resolved(static_cast<std::size_t>(capacity) + 1u);
                const auto resolved_length = GetFinalPathNameByHandleW(parent_handle.get(), resolved.data(),
                    static_cast<DWORD>(resolved.size()), FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
                check(resolved_length > 0 && resolved_length < resolved.size(), "Windows temporary directory final path truncated");
                const std::wstring final_path(resolved.data(), resolved_length);
                check(final_path.size() >= 7 && final_path.compare(0, 4, L"\\\\?\\") == 0
                    && final_path[5] == L':' && final_path[6] == L'\\'
                    && ((final_path[4] >= L'A' && final_path[4] <= L'Z') || (final_path[4] >= L'a' && final_path[4] <= L'z')),
                    "Windows temporary directory final path is not a local DOS drive path");
                const std::filesystem::path parent(final_path.substr(4));
                const auto prefix = std::wstring(L"selected-xpak-fixture-") + std::to_wstring(GetCurrentProcessId())
                    + L"-" + std::to_wstring(GetTickCount64()) + L"-";
                for (unsigned attempt = 0; attempt < 32 && !directory_created_; ++attempt)
                {
                    directory_ = parent / (prefix + std::to_wstring(attempt));
                    if (CreateDirectoryW(directory_.c_str(), nullptr)) directory_created_ = true;
                    else check(GetLastError() == ERROR_ALREADY_EXISTS, "synthetic fixture directory creation failed");
                }
                check(directory_created_, "unique synthetic fixture directory unavailable");
                file_ = directory_ / L"synthetic.xpak";
                owned_handle output(CreateFileW(file_.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW,
                    FILE_ATTRIBUTE_NORMAL, nullptr));
                check(output.get() != INVALID_HANDLE_VALUE, "synthetic XPAK creation failed");
                file_created_ = true;
                std::size_t done = 0;
                while (done < input.size())
                {
                    const auto wanted = static_cast<DWORD>((std::min)(input.size() - done, std::size_t{65536}));
                    DWORD written = 0;
                    check(WriteFile(output.get(), input.data() + done, wanted, &written, nullptr) && written == wanted,
                        "synthetic XPAK write failed");
                    done += written;
                }
                check(FlushFileBuffers(output.get()) != 0, "synthetic XPAK flush failed");
            }
            catch (...) { cleanup(); throw; }
        }
        synthetic_temp_package(const synthetic_temp_package&) = delete;
        synthetic_temp_package& operator=(const synthetic_temp_package&) = delete;
        ~synthetic_temp_package() { cleanup(); }
        const std::filesystem::path& path() const { return file_; }

        void remove_verified()
        {
            check(file_created_ && DeleteFileW(file_.c_str()), "released synthetic XPAK could not be deleted");
            file_created_ = false;
            check(directory_created_ && RemoveDirectoryW(directory_.c_str()), "empty synthetic fixture directory could not be removed");
            directory_created_ = false;
        }
    };

    void write_must_be_denied(const std::filesystem::path& path)
    {
        const auto raw_handle = CreateFileW(path.c_str(), GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        const auto error = GetLastError();
        owned_handle attempted(raw_handle); // Close even an unexpected successful write-open before unwinding.
        check(raw_handle == INVALID_HANDLE_VALUE && error == ERROR_SHARING_VIOLATION,
            "sealed package view allowed an ordinary write-open");
    }

    void run_sealing()
    {
        const auto original = original_bytes();
        const auto synthetic = make_file(one_group(0, original));
        synthetic_temp_package temporary(synthetic.storage);
        {
            xpak::package retained{};
            std::string identity;
            {
                xpak::sealed_file owner(temporary.path());
                retained = owner.view();
                identity = retained.identity;
                const std::array views{retained};
                const auto first = xpak::read_selected_key(views, selected_key, expected_size, &LZ4_decompress_safe);
                check(first.bytes == original && first.observed.package_name == "synthetic.xpak"
                    && first.observed.package_identity == identity && !identity.empty()
                    && first.observed.file_bytes == synthetic.storage.size(), "sealed synthetic XPAK read failed");
                write_must_be_denied(temporary.path());
            } // The wrapper is gone; the callback must retain the same sealed handle.
            const std::array views{retained};
            const auto after_owner = xpak::read_selected_key(views, selected_key, expected_size, &LZ4_decompress_safe);
            check(after_owner.bytes == original && after_owner.observed.package_identity == identity,
                "package callback did not survive sealed_file wrapper destruction");
            write_must_be_denied(temporary.path());
        } // All package views and callback copies are gone.
        {
            owned_handle released(CreateFileW(temporary.path().c_str(), GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr));
            check(released.get() != INVALID_HANDLE_VALUE, "destroyed package views retained the sealed handle");
        }
        temporary.remove_verified();
        ++sealing_cases;
        check(sealing_cases == 1, "Windows sealing case inventory changed");
    }
#endif
}

int main(int argc, char**)
{
    if (argc != 1) { std::fputs("selected XPAK fixture requires no arguments\n", stderr); return 2; }
    try
    {
        run();
#ifdef _WIN32
        run_sealing();
#endif
        std::printf("{\"schema\":\"iw7.t7-selected-xpak-fixture/1\",\"status\":\"synthetic-pass\","
            "\"copied_cases\":%u,\"refused_cases\":%u,\"sealing_cases\":%u,\"expected_bytes\":%u,"
            "\"retail_files_read\":false,\"engine_observed\":false}\n", copied_cases, refused_cases, sealing_cases, expected_size);
        return 0;
    }
    catch (const std::exception& error)
    {
        std::fprintf(stderr, "selected XPAK fixture failed: %s\n", error.what());
        return 1;
    }
}
