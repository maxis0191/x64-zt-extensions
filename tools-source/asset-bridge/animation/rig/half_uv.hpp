#pragma once
#include <cstdint>
#include <cstring>
#include <stdexcept>
namespace doom_mesh
{
// IEEE-754 binary32 -> binary16, nearest-even, including signed zero/subnormals.
// Nonfinite and overflowing values fail closed rather than encode NaN/Inf UVs.
inline std::uint16_t half(float value)
{
    std::uint32_t bits{};std::memcpy(&bits,&value,sizeof(bits));
    const auto sign=static_cast<std::uint16_t>((bits>>16)&0x8000u);
    const auto raw=(bits>>23)&255u;auto fraction=bits&0x7fffffu;
    if(raw==255u)throw std::runtime_error("Nonfinite UV refused");
    int exponent=static_cast<int>(raw)-127+15;
    if(exponent<=0)
    {
        if(exponent < -10)return sign;
        fraction|=0x800000u;const unsigned shift=static_cast<unsigned>(14-exponent);
        const auto base=fraction>>shift;const auto tail=fraction&((1u<<shift)-1u);const auto tie=1u<<(shift-1u);
        return static_cast<std::uint16_t>(sign|static_cast<std::uint16_t>(base+(tail>tie || (tail==tie && (base&1u)))));
    }
    fraction+=0xfffu+((fraction>>13)&1u);
    if(fraction&0x800000u){fraction=0;++exponent;}
    if(exponent>=31)throw std::runtime_error("UV half overflow refused");
    return static_cast<std::uint16_t>(sign|(static_cast<unsigned>(exponent)<<10)|(fraction>>13));
}
inline std::uint32_t pack_uv(const float* uv)
{
    return half(uv[0]) | (std::uint32_t(half(uv[1]))<<16);
}
}
