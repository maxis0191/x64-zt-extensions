#pragma once
#include <cstddef>

namespace iw7_player_template_names
{
    template <std::size_t N>
    bool matches(const char* observed, const char (&expected)[N])
    {
        static_assert(N > 1 && N <= 64, "Finite allowlisted name including its NUL required");
        if (!observed || expected[N - 1] != '\0') return false;
        for (std::size_t i = 0; i < N; ++i)
        {
            if (observed[i] != expected[i]) return false;
            if (observed[i] == '\0') return i == N - 1;
        }
        return false;
    }
}
