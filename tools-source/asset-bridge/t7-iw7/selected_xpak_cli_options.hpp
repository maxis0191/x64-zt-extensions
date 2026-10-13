#pragma once
#include <cstdint>
#include <limits>
#include <set>
#include <span>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace selected_xpak_cli
{
    inline constexpr std::uint64_t maximum_file_bytes = 16ull * 1024 * 1024 * 1024;
    inline constexpr std::uint32_t maximum_expected_bytes = 256u * 1024u;
    struct input { std::wstring path; std::string identity; std::uint64_t bytes{}; };
    struct options
    {
        bool help{}, inspect{};
        std::uint64_t key{};
        std::string key_hex;
        std::uint32_t expected{};
        std::wstring output;
        std::vector<input> packages;
    };
    inline void require(bool valid, const char* message)
    { if (!valid) throw std::runtime_error(message); }
    inline bool local_absolute(const std::wstring& value)
    {
        return value.size() >= 4 && value.size() <= 32767 &&
            ((value[0] >= L'A' && value[0] <= L'Z') || (value[0] >= L'a' && value[0] <= L'z')) &&
            value[1] == L':' && value[2] == L'\\' && value.find(L'\0') == std::wstring::npos &&
            value.find(L':', 2) == std::wstring::npos;
    }
    inline std::uint64_t decimal(const std::wstring& value)
    {
        require(!value.empty() && (value.size() == 1 || value[0] != L'0'), "Canonical unsigned decimal required");
        std::uint64_t result{};
        for (const auto c : value)
        {
            require(c >= L'0' && c <= L'9', "Unsigned decimal digits required");
            const auto digit = static_cast<unsigned>(c - L'0');
            require(result <= ((std::numeric_limits<std::uint64_t>::max)() - digit) / 10, "Decimal overflow");
            result = result * 10 + digit;
        }
        return result;
    }
    inline options parse(std::span<const std::wstring> arguments)
    {
        options result;
        if (arguments.size() == 1 && arguments[0] == L"--help") { result.help = true; return result; }
        bool key_seen = false, expected_seen = false, output_seen = false, inspect_seen = false;
        std::set<std::wstring> paths;
        std::set<std::string> identities;
        std::size_t characters = 0;
        for (const auto& arg : arguments)
        {
            require(arg.size() <= 32767 - characters, "Command line character bound exceeded");
            characters += arg.size();
        }
        for (std::size_t i = 0; i < arguments.size(); ++i)
        {
            const auto& option = arguments[i];
            if (option == L"--inspect")
            {
                require(!inspect_seen, "Duplicate --inspect"); inspect_seen = true; result.inspect = true; continue;
            }
            if (option == L"--package")
            {
                require(result.packages.size() < 8 && arguments.size() - i > 3, "--package requires PATH ID BYTES; at most eight packages");
                input file; file.path = arguments[++i];
                require(local_absolute(file.path) && file.path.ends_with(L".xpak"), "Explicit local absolute .xpak path required");
                const auto& id = arguments[++i];
                require(id.size() == 25 && id[8] == L':', "File identity requires VolumeSerial8hex:FileIndex16hex");
                for (std::size_t j = 0; j < id.size(); ++j)
                    require(j == 8 || (id[j] >= L'0' && id[j] <= L'9') || (id[j] >= L'A' && id[j] <= L'F'), "Upper-case hexadecimal file identity required");
                for (const auto c : id) file.identity.push_back(static_cast<char>(c));
                file.bytes = decimal(arguments[++i]);
                require(file.bytes >= 120 && file.bytes <= maximum_file_bytes, "Package size must be 120 bytes through 16 GiB");
                require(paths.insert(file.path).second && identities.insert(file.identity).second, "Distinct package paths and identities required");
                result.packages.push_back(std::move(file)); continue;
            }
            require(i + 1 < arguments.size(), "Option requires a value");
            const auto& value = arguments[++i];
            if (option == L"--key")
            {
                require(!key_seen && value.size() == 16, "Exactly one --key with sixteen lower-case hexadecimal digits required");
                key_seen = true;
                for (const auto c : value)
                {
                    const int digit = c >= L'0' && c <= L'9' ? static_cast<int>(c - L'0') :
                        c >= L'a' && c <= L'f' ? static_cast<int>(c - L'a') + 10 : -1;
                    require(digit >= 0, "Lower-case hexadecimal key required");
                    result.key = (result.key << 4) | static_cast<unsigned>(digit);
                    result.key_hex.push_back(static_cast<char>(c));
                }
            }
            else if (option == L"--expected-bytes")
            {
                require(!expected_seen, "Duplicate --expected-bytes"); expected_seen = true;
                const auto size = decimal(value);
                require(size > 0 && size <= maximum_expected_bytes, "Expected bytes must be 1 through 262144");
                result.expected = static_cast<std::uint32_t>(size);
            }
            else if (option == L"--out")
            {
                require(!output_seen && local_absolute(value), "Exactly one --out local absolute path required");
                output_seen = true; result.output = value;
            }
            else throw std::runtime_error("Unknown option");
        }
        require(key_seen && expected_seen && !result.packages.empty(), "--key, --expected-bytes and --package are required");
        require(result.inspect ? !output_seen : output_seen, "Use either --inspect without --out, or extraction with --out");
        return result;
    }
}
