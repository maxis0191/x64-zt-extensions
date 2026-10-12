// Original in-memory fixture for the exact upstream bit_buffer implementation.
// Compile twice against separate original/patched source archives after GO.
// No ZoneTool, retail file, retained SAB, stock or game access occurs here.
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <utils/bit_buffer.hpp>
#include <utils/bit_buffer.cpp>

namespace {
constexpr std::array<std::uint8_t, 34> streaminfo{
    0x10, 0x00, 0x10, 0x00, 0x00, 0x17, 0x0b, 0x00, 0x20, 0x0b,
    0x0b, 0xb8, 0x00, 0xf0, 0x00, 0x00, 0xbb, 0x80,
    0x24, 0xfe, 0x5a, 0xf1, 0x47, 0x3e, 0xa8, 0xf4,
    0xbe, 0x33, 0x91, 0x23, 0x48, 0x21, 0x0c, 0x78};
constexpr std::array<std::uint8_t, 16> original_md5{
    0x24, 0xfe, 0x5a, 0xf1, 0x47, 0x3e, 0xa8, 0xf4,
    0xbe, 0x33, 0x91, 0x23, 0x48, 0x21, 0x0c, 0x78};
constexpr std::array<std::uint8_t, 16> observed_corrupt{
    0x78, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};

std::string hex(const std::array<std::uint8_t, 16>& bytes) {
    std::ostringstream text;
    for (const auto byte : bytes)
        text << std::hex << std::setfill('0') << std::setw(2) << unsigned(byte);
    return text.str();
}
}

int main(int argc, char** argv) {
    if (argc != 2 || (std::string(argv[1]) != "--expect-original" &&
                     std::string(argv[1]) != "--expect-observed-corrupt")) return 2;
    const bool fixed = std::string(argv[1]) == "--expect-original";
    utils::bit_buffer bits(std::string(reinterpret_cast<const char*>(streaminfo.data()), streaminfo.size()));
    // Same widths/order as iw7/assets/sound_bank.cpp STREAMINFO parsing.
    if (bits.read_bits<std::uint32_t>(16) != 4096 || bits.read_bits<std::uint32_t>(16) != 4096 ||
        bits.read_bits<std::uint32_t>(24) != 5899 || bits.read_bits<std::uint32_t>(24) != 8203 ||
        bits.read_bits<std::uint32_t>(20) != 48000 || bits.read_bits<std::uint8_t>(3) != 0 ||
        bits.read_bits<std::uint8_t>(5) != 15 || bits.read_bits<std::uint64_t>(36) != 48000) return 3;
    std::array<std::uint8_t, 16> digest{};
    bits.read_buffer(digest.data(), 128);

    // A synthetic byte envelope, not a repaired retained SAB or native bank.
    constexpr std::size_t source_offset = 110592;
    constexpr std::size_t payload_offset = 4096;
    constexpr std::size_t payload_bytes = 96348;
    std::array<std::uint8_t, 114816> envelope{};
    for (std::size_t i = 0; i < envelope.size(); ++i)
        envelope[i] = static_cast<std::uint8_t>((i * 17U + 29U) & 255U);
    const auto before = envelope;
    std::copy(digest.begin(), digest.end(), envelope.begin() + source_offset);
    const bool field_matches = std::equal(digest.begin(), digest.end(), envelope.begin() + source_offset);
    const bool payload_unchanged = std::equal(before.begin() + payload_offset,
        before.begin() + payload_offset + payload_bytes, envelope.begin() + payload_offset);
    const bool outside_unchanged = std::equal(before.begin(), before.begin() + source_offset, envelope.begin()) &&
        std::equal(before.begin() + source_offset + 16, before.end(), envelope.begin() + source_offset + 16);
    const bool expected = digest == (fixed ? original_md5 : observed_corrupt);
    std::cout << "{\"source_checksum\":\"" << hex(digest)
              << "\",\"matches_original_md5\":" << (digest == original_md5 ? "true" : "false")
              << ",\"field_matches\":" << (field_matches ? "true" : "false")
              << ",\"payload_unchanged\":" << (payload_unchanged ? "true" : "false")
              << ",\"outside_field_unchanged\":" << (outside_unchanged ? "true" : "false")
              << ",\"native_ff_tested\":false,\"ready\":false}\n";
    return expected && field_matches && payload_unchanged && outside_unchanged ? 0 : 1;
}
