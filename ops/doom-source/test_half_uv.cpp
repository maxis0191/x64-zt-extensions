#include "half_uv.hpp"
#include <cassert>
#include <cmath>
#include <limits>
#include <iostream>
int main()
{
    using doom_mesh::half;
    assert(half(0.0f)==0 && half(-0.0f)==0x8000);
    assert(half(1.0f)==0x3c00 && half(-1.0f)==0xbc00);
    assert(half(0.5f)==0x3800 && half(16.0f)==0x4c00);
    assert(half(std::ldexp(1.0f,-24))==1 && half(std::ldexp(1.0f,-14))==0x0400);
    assert(half(std::ldexp(1.0f,-25))==0 && half(3*std::ldexp(1.0f,-25))==2);
    assert(half(1.0f+std::ldexp(1.0f,-11))==0x3c00);
    assert(half(1.0f+3*std::ldexp(1.0f,-11))==0x3c02);
    assert(half(65504.0f)==0x7bff);
    for(float v:{std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity(),65536.0f})
    {bool refused=false;try{half(v);}catch(...){refused=true;}assert(refused);}
    const float uv[]{0.5f,-1.0f};assert(doom_mesh::pack_uv(uv)==0xbc003800u);
    std::cout<<"UV half: signed/normal/subnormal/ties-even/layout/overflow PASS\n";
}
