#pragma once
// Inactive raw ownership/binding only, NOT PR216/native eligibility or a token.
// Caller storage must remain valid and free of concurrent mutation during copy.
// Const access is an interface contract, not const_cast/race protection or an OS sandbox.
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace player_pair_input
{
    using std::size_t;
    enum class Role : size_t { report, weapon, attachment, csv };
    struct Pin { size_t bytes; std::string_view sha256; };
    using Inputs = std::array<std::string_view, 4>;
    using Pins = std::array<Pin, 4>;
    struct Counters { unsigned copies{}, hashes{}; }; // Diagnostics only.
    struct PinError : std::runtime_error
    {
        PinError() : std::runtime_error("Private copy Source pin differs") {}
    };
    inline constexpr std::array<size_t, 4> role_caps{65536, 2097152, 2097152, 66};
    inline constexpr size_t total_cap = 4259906;

    namespace detail
    {
    inline void need(bool value) { if (!value) throw PinError(); }
    inline size_t checked_total(size_t used, size_t amount)
    {
        need(used <= total_cap && amount <= total_cap - used);
        return used + amount;
    }
    // Extracted unchanged from J7's fixture; no new crypto/SDK/provider dependency.
    // Actual known-vector execution is still a separate future native gate.
    inline std::string sha256(std::string_view input)
    {
        static constexpr std::uint32_t k[] = {
            0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
            0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
            0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
            0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
            0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
            0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
            0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
            0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
        need(input.size() <= 2097152);
        std::vector<std::uint8_t> bytes(input.begin(), input.end());
        const auto bits = static_cast<std::uint64_t>(bytes.size()) * 8;
        bytes.push_back(0x80);
        while (bytes.size() % 64 != 56) bytes.push_back(0);
        for (unsigned i = 0; i < 8; ++i) bytes.push_back(static_cast<std::uint8_t>(bits >> (56 - 8*i)));
        std::array<std::uint32_t,8> h{0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
        const auto rotr=[](std::uint32_t n,unsigned count){return (n>>count)|(n<<(32-count));};
        for(size_t at=0;at<bytes.size();at+=64)
        {
            std::uint32_t w[64]{};
            for(unsigned i=0;i<16;++i) for(unsigned j=0;j<4;++j) w[i]=(w[i]<<8)|bytes[at+4*i+j];
            for(unsigned i=16;i<64;++i) w[i]=w[i-16]+(rotr(w[i-15],7)^rotr(w[i-15],18)^(w[i-15]>>3))+w[i-7]+(rotr(w[i-2],17)^rotr(w[i-2],19)^(w[i-2]>>10));
            auto a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],v=h[7];
            for(unsigned i=0;i<64;++i)
            {
                const auto t1=v+(rotr(e,6)^rotr(e,11)^rotr(e,25))+((e&f)^((~e)&g))+k[i]+w[i];
                const auto t2=(rotr(a,2)^rotr(a,13)^rotr(a,22))+((a&b)^(a&c)^(b&c));
                v=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
            }
            h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=v;
        }
        static constexpr char digits[]="0123456789abcdef";
        std::string result;result.reserve(64);
        for(auto value:h) for(unsigned i=0;i<8;++i) result.push_back(digits[(value>>(28-4*i))&15]);
        return result;
    }
    }

    class OwnedInput final
    {
        struct StoredPin { size_t bytes{}; std::string sha256; };
        std::array<std::string, 4> bytes_;
        std::array<StoredPin, 4> pins_;

        static size_t index(Role role)
        {
            const auto value = static_cast<size_t>(role);
            detail::need(value < role_caps.size());
            return value;
        }
        static void validate_before_copy(const Inputs& incoming, const Pins& trusted)
        {
            size_t actual_total = 0, expected_total = 0;
            for (size_t i = 0; i < role_caps.size(); ++i)
            {
                detail::need(!incoming[i].empty() && incoming[i].size() <= role_caps[i]);
                detail::need(trusted[i].bytes > 0 && trusted[i].bytes <= role_caps[i]);
                actual_total = detail::checked_total(actual_total, incoming[i].size());
                expected_total = detail::checked_total(expected_total, trusted[i].bytes);
                detail::need(incoming[i].size() == trusted[i].bytes);
                detail::need(trusted[i].sha256.size() == 64 &&
                    std::all_of(trusted[i].sha256.begin(), trusted[i].sha256.end(),
                        [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); }));
            }
        }
    public:
        // Generic caller pins bind bytes only. They never enable a new parse.
        // All role/aggregate bounds finish before any private raw or pin copy.
        OwnedInput(const Inputs& incoming, const Pins& trusted, Counters& counters)
        {
            validate_before_copy(incoming, trusted);
            for (size_t i = 0; i < role_caps.size(); ++i)
            {
                pins_[i].bytes = trusted[i].bytes;
                pins_[i].sha256.assign(trusted[i].sha256);
                bytes_[i].assign(incoming[i]);
                ++counters.copies;
            }
            // Hash the same owned copies before a caller can decode or use them.
            for (size_t i = 0; i < role_caps.size(); ++i)
            {
                ++counters.hashes;
                detail::need(bytes_[i].size() == pins_[i].bytes &&
                    detail::sha256(bytes_[i]) == pins_[i].sha256);
            }
        }
        OwnedInput(const OwnedInput&) = delete;
        OwnedInput& operator=(const OwnedInput&) = delete;
        OwnedInput(OwnedInput&&) = delete;
        OwnedInput& operator=(OwnedInput&&) = delete;

        const std::string& bytes(Role role) const { return bytes_[index(role)]; }
        Pin pin(Role role) const { const auto& value = pins_[index(role)]; return {value.bytes, value.sha256}; }
        // No decode/arena/route/permission API. Normal member unwind preserves
        // standard-memory exceptions; it proves no native fatal allocator closure.
    };
}
