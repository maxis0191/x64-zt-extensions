// Authored finite metadata/code buffers only; no engine, PE, process or asset IO.
#include "prepatch_image_caller_range.hpp"
#include <array>
#include <iostream>
#include <vector>

int main()
{
    namespace range = zonetool::t7_prepatch_image_caller_range;
    using status = range::status;
    unsigned checks{};
    auto check = [&](bool ok) { ++checks; return ok; };
    const auto site = range::callsite_rva;
    const uint32_t image_size = 0x1000000;
    range::entry record{site - 64, site + 64, 0xF00000};
    auto select = [&](const std::vector<range::entry>& records, range::window& out) {
        return range::select(reinterpret_cast<const uint8_t*>(records.data()), records.size() * sizeof(range::entry), image_size, out);
    };
    range::window out{};
    if (!check(select({record}, out) == status::ok && out.begin == record.begin && out.end == record.end)) return 1;
    if (!check(range::select(nullptr, sizeof(record), image_size, out) == status::invalid_metadata && out.begin == 0)) return 1;
    if (!check(range::select(reinterpret_cast<const uint8_t*>(&record), 0, image_size, out) == status::invalid_metadata)) return 1;
    if (!check(range::select(reinterpret_cast<const uint8_t*>(&record), 11, image_size, out) == status::invalid_metadata)) return 1;
    if (!check(range::select(reinterpret_cast<const uint8_t*>(&record), range::pdata_limit + 12, image_size, out) == status::invalid_metadata)) return 1;
    if (!check(range::select(reinterpret_cast<const uint8_t*>(&record), sizeof(record), 0, out) == status::invalid_metadata)) return 1;
    if (!check(select({{site + 1, site + 8, 1}}, out) == status::missing)) return 1;
    if (!check(select({record, record}, out) == status::ambiguous && out.begin == 0)) return 1;
    if (!check(select({{site - 100, site + 100, 1}, record}, out) == status::ambiguous)) return 1;
    if (!check(select({{site - 64, site - 64, 1}}, out) == status::invalid_metadata)) return 1;
    if (!check(select({{site - 64, image_size + 1, 1}}, out) == status::invalid_metadata)) return 1;
    if (!check(select({{site - 64, site + 64, 0}}, out) == status::invalid_metadata)) return 1;
    if (!check(select({{site - 64, site + 64, image_size}}, out) == status::invalid_metadata)) return 1;
    if (!check(select({record, {1, 2, 1}}, out) == status::invalid_metadata)) return 1;
    if (!check(select({{site - 8192, site + 1, 1}}, out) == status::over_limit && out.begin == 0)) return 1;
    if (!check(select({{site - 8187, site + 5, 1}}, out) == status::ok && out.end - out.begin == 8192)) return 1;
    if (!check(select({{site - 1, site + 4, 1}}, out) == status::call_outside)) return 1;
    if (!check(select({{site, site + 5, 1}}, out) == status::ok)) return 1;
    std::array<uint8_t, 5> code{0xE8};
    const int32_t displacement = static_cast<int32_t>(range::known_target_rva - (site + 5));
    std::memcpy(code.data() + 1, &displacement, 4);
    if (!check(range::validate_call(code.data(), code.size(), out) == status::ok)) return 1;
    if (!check(range::validate_call(code.data(), 4, out) == status::call_outside)) return 1;
    if (!check(range::validate_call(nullptr, 5, out) == status::call_outside)) return 1;
    code[0] = 0xFF;
    if (!check(range::validate_call(code.data(), 5, out) == status::opcode)) return 1;
    code[0] = 0xE8; code[1] ^= 1;
    if (!check(range::validate_call(code.data(), 5, out) == status::target)) return 1;
    const int32_t negative = INT32_MIN;
    std::memcpy(code.data() + 1, &negative, 4);
    if (!check(range::validate_call(code.data(), 5, out) == status::target)) return 1;
    out = {site - 8192, site + 5, 1};
    if (!check(range::validate_call(code.data(), 5, out) == status::call_outside)) return 1;
    std::cout << "IW7_T7_PREPATCH_IMAGE_CALLER_CHECKS=" << checks << '\n';
    return checks == 25 ? 0 : 1;
}
