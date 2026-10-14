// Authored native causal fixture. No compile/run result is implied by this source.
#include "native_bounded_name.hpp"
#include <cassert>
#include <cstring>

int main()
{
    constexpr char expected[] = "iw7_shredder_zm";
    assert(iw7_player_template_names::matches(expected, expected));
    assert(!iw7_player_template_names::matches(nullptr, expected));
    assert(!iw7_player_template_names::matches("iw7_dischord_zm", expected));
    assert(!iw7_player_template_names::matches("iw7", expected));
    assert(!iw7_player_template_names::matches("iw7_shredder_zm_suffix", expected));
    char finite_nonterminated[sizeof(expected)];
    std::memcpy(finite_nonterminated, expected, sizeof(expected));
    finite_nonterminated[sizeof(expected) - 1] = 'x';
    assert(!iw7_player_template_names::matches(finite_nonterminated, expected));
    constexpr char pap[] = "shredderpap1";
    assert(iw7_player_template_names::matches(pap, pap));
    assert(!iw7_player_template_names::matches("shredderpap11", pap));
    return 0;
}
