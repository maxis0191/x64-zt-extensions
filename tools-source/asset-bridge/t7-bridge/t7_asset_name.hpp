#pragma once

#include <stdexcept>
#include <string>
#include <string_view>

namespace zonetool::t7::resident_iw7
{
    // One rule for model and mesh names used by the native relative-path writers.
    // Keep valid donor spelling/separators unchanged; never sanitize or rename.
    inline std::string checked_asset_name(const std::string_view input)
    {
        const auto fail = [] { throw std::runtime_error("Unsafe T7 export asset name"); };
        if (input.empty() || input.size() > 255) fail();
        for (const unsigned char c : input)
        {
            if (c < 0x20 || c >= 0x7f || std::string_view(":<>\"|?*").find(c) != std::string_view::npos)
                fail();
        }
        std::size_t start = 0;
        while (start < input.size())
        {
            auto end = input.find_first_of("/\\", start);
            if (end == std::string_view::npos) end = input.size();
            const auto segment = input.substr(start, end - start);
            if (segment.empty() || segment == "." || segment == ".." ||
                segment.back() == '.' || segment.back() == ' ') fail();
            auto device = std::string(segment.substr(0, segment.find('.')));
            // Device aliases also remain unsafe with spaces before an extension.
            while (!device.empty() && device.back() == ' ') device.pop_back();
            for (auto& c : device) if (c >= 'a' && c <= 'z') c -= 'a' - 'A';
            if (device == "CON" || device == "PRN" || device == "AUX" || device == "NUL" ||
                device == "CONIN$" || device == "CONOUT$" || device == "CLOCK$" ||
                (device.size() == 4 && (device.substr(0, 3) == "COM" || device.substr(0, 3) == "LPT") &&
                 device[3] >= '0' && device[3] <= '9')) fail();
            if (end == input.size()) break;
            start = end + 1;
            if (start == input.size()) fail();
        }
        return std::string(input);
    }
}
