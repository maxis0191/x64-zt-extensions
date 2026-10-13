#include "selected_xpak_cli_options.hpp"
#include <iostream>

namespace
{
    using args = std::vector<std::wstring>;
    args valid()
    {
        return {L"--key", L"0123456789abcdef", L"--expected-bytes", L"18624",
            L"--out", L"C:\\private\\mesh.bin", L"--package", L"C:\\stock\\zone\\donor.xpak",
            L"AABBCCDD:0000000000000001", L"1048576"};
    }
    unsigned passed{};
    void check(bool value) { if (!value) throw std::runtime_error("Parameter assertion failed"); ++passed; }
    void refuses(const args& input)
    {
        try { (void)selected_xpak_cli::parse(input); }
        catch (const std::runtime_error&) { ++passed; return; }
        throw std::runtime_error("Expected parameter refusal");
    }
}
int main()
{
    try
    {
        const auto parsed = selected_xpak_cli::parse(valid());
        check(parsed.key == 0x0123456789abcdefull);
        check(parsed.expected == 18624 && parsed.packages.size() == 1 && !parsed.inspect);
        check(parsed.packages[0].bytes == 1048576);
        for (const auto* size : {L"1", L"18623", L"262144"})
        { auto accepted = valid(); accepted[3] = size; check(selected_xpak_cli::parse(accepted).expected > 0); }
        check(selected_xpak_cli::parse(args{L"--help"}).help);
        auto inspect = valid(); inspect.erase(inspect.begin() + 4, inspect.begin() + 6); inspect.push_back(L"--inspect");
        check(selected_xpak_cli::parse(inspect).inspect);
        for (const auto* key : {L"0123456789abcdeF", L"0x0123456789abcdef", L"123", L"g123456789abcdef"})
        { auto bad = valid(); bad[1] = key; refuses(bad); }
        for (const auto* size : {L"0", L"262145", L"018624", L"+18624", L"18446744073709551616"})
        { auto bad = valid(); bad[3] = size; refuses(bad); }
        for (const auto* size : {L"119", L"17179869185", L"-1", L"01", L"18446744073709551616"})
        { auto bad = valid(); bad[9] = size; refuses(bad); }
        for (const auto* path : {L"zone\\file.xpak", L"\\\\server\\file.xpak", L"C:\\file.xpak:ads", L"C:\\file.XPAK"})
        { auto bad = valid(); bad[7] = path; refuses(bad); }
        for (const auto* id : {L"aabbccdd:0000000000000001", L"AABBCCDD-0000000000000001", L"AABBCCDD:123", L"AABBCCDD:000000000000000G"})
        { auto bad = valid(); bad[8] = id; refuses(bad); }
        auto duplicate = valid(); duplicate.insert(duplicate.end(), {L"--key", L"0000000000000000"}); refuses(duplicate);
        duplicate = valid(); duplicate.insert(duplicate.end(), {L"--package", L"C:\\other\\file.xpak", L"AABBCCDD:0000000000000001", L"120"}); refuses(duplicate);
        duplicate = valid(); duplicate.push_back(L"--inspect"); refuses(duplicate);
        refuses(args{L"--help", L"--inspect"});
        refuses(args{});
        auto eight = valid();
        for (unsigned i = 1; i < 8; ++i)
            eight.insert(eight.end(), {L"--package", L"C:\\stock\\file" + std::to_wstring(i) + L".xpak",
                L"AAAAAAAA:000000000000000" + std::to_wstring(i), L"120"});
        check(selected_xpak_cli::parse(eight).packages.size() == 8);
        eight.insert(eight.end(), {L"--package", L"C:\\stock\\file8.xpak", L"AAAAAAAA:0000000000000008", L"120"});
        refuses(eight);
        std::cout << passed << " selected XPAK CLI parameter checks passed\n";
        return 0;
    }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
