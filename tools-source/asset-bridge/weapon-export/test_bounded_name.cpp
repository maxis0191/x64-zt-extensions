// Authored native causal fixture. No compile/run result is implied by this source.
#include "native_bounded_name.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>

int main()
{
    unsigned checks = 0;
    const auto check = [&](bool value) { ++checks; if (!value) throw std::runtime_error("Player-template name fixture failed"); };
    try
    {
        constexpr char expected[] = "iw7_shredder_zm";
        check(iw7_player_template_names::matches(expected, expected));
        check(!iw7_player_template_names::matches(nullptr, expected));
        check(!iw7_player_template_names::matches("iw7_dischord_zm", expected));
        check(!iw7_player_template_names::matches("iw7", expected));
        check(!iw7_player_template_names::matches("iw7_shredder_zm_suffix", expected));
        char finite_nonterminated[sizeof(expected)];
        std::memcpy(finite_nonterminated, expected, sizeof(expected));
        finite_nonterminated[sizeof(expected) - 1] = 'x';
        check(!iw7_player_template_names::matches(finite_nonterminated, expected));
        constexpr char pap[] = "shredderpap1";
        check(iw7_player_template_names::matches(pap, pap));
        check(!iw7_player_template_names::matches("shredderpap11", pap));
        if (checks != 8) throw std::runtime_error("Exact player-template name count required");
        std::printf("IW7_PLAYER_TEMPLATE_NAME_CHECKS=8\n");
        return 0;
    }
    catch (const std::exception& error) { std::fprintf(stderr, "%s\n", error.what()); return 1; }
}
