// Source only until separately admitted native compilation and execution.
#include "sound_flac_metadata.hpp"
#include <cstdio>
#include <cstring>
#include <vector>
#include <limits>

namespace meta = zonetool::iw7::sound_asset_bank::flac_metadata;
#include "flac_dump_cases.hpp"

int main(int argc, char** argv)
{
    if (argc != 2 || std::strcmp(argv[1], "--verify-headers") != 0)
    {
        std::fprintf(stderr, "Expected exactly --verify-headers\n");
        return 64;
    }
    unsigned checked{};
    for (const auto& item : cases)
    {
        std::vector<std::uint8_t> bytes;
        for (std::size_t i = 0; item.hex[i]; i += 2)
        {
            const auto digit = [](char ch) -> unsigned
            {
                return static_cast<unsigned>(ch <= '9' ? ch - '0' : ch - 'a' + 10);
            };
            bytes.push_back(static_cast<std::uint8_t>(digit(item.hex[i]) * 16 + digit(item.hex[i + 1])));
        }
        const auto before = bytes;
        const auto entry_before = item.entry;
        const auto result = meta::derive(item.entry, item.null_span ? nullptr : bytes.data(), bytes.size());
        if (static_cast<bool>(result) != item.accepted || result.block_size != item.block ||
            result.header_bytes != item.header_bytes || bytes != before ||
            std::memcmp(&item.entry, &entry_before, sizeof(item.entry)) != 0)
        {
            std::fprintf(stderr, "FLAC header case failed: %s (%s)\n", item.name, result.error ? result.error : "accepted");
            return 1;
        }
        ++checked;
    }
    const auto maximum = (std::numeric_limits<std::uint64_t>::max)();
    if (!meta::contains(maximum, maximum, 0) || meta::contains(maximum, maximum, 1) ||
        meta::contains(9, 10, 0) || !meta::contains(9, 1, 8)) return 2;
    const meta::Entry wide{0xffffffffu, 18, 96000, 0, 48000, 1};
    std::uint64_t span{};
    if (meta::validate_entry(wide, span) || span != 0x100000011ull) return 3;
    std::printf("{\"schema\":\"iw7.flac-dump-header-probe/1\",\"cases\":%u,"
                "\"input_unchanged\":true,\"extent_checks\":true,"
                "\"native_dump_tested\":false,\"full_conformance\":false,\"ready\":false}\n", checked);
    return 0;
}
