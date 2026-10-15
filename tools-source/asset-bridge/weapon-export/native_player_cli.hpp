#pragma once
#include <algorithm>
#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace iw7_player_template_cli
{
    inline bool selected(const std::vector<std::string>& args)
    {
        return std::find(args.begin(), args.end(), "-iw7-player-weapon-templates") != args.end();
    }
    inline bool exact(const std::vector<std::string>& args)
    {
        if (args.size() != 6) return false;
        constexpr std::array<std::size_t, 6> caps{4096, 32, 64, 32, 1024, 96};
        for (std::size_t i = 0; i < args.size(); ++i)
        {
            if (args[i].empty() || args[i].size() > caps[i]) return false;
            for (const unsigned char byte : args[i])
                if (byte < 0x20 || byte == 0x7f) return false;
        }
        return args[1] == "-headless" && args[2] == "-iw7-player-weapon-templates" && args[3] == "cp_zmb";
    }
    inline bool pair_selected(const std::vector<std::string>& args)
    {
        return std::find(args.begin(), args.end(), "-iw7-player-weapon-pair-profile") != args.end();
    }
    inline bool pair_exact(const std::vector<std::string>& args)
    {
        if (args.size() != 6) return false;
        constexpr std::array<std::size_t, 6> caps{4096, 32, 64, 32, 1024, 96};
        for (std::size_t i = 0; i < args.size(); ++i)
        {
            if (args[i].empty() || args[i].size() > caps[i]) return false;
            for (const unsigned char byte : args[i])
                if (byte < 0x20 || byte == 0x7f) return false;
        }
        return args[1] == "-headless" && args[2] == "-iw7-player-weapon-pair-profile" && args[3] == "cp_zmb";
    }
}

namespace iw7_player_template_cli
{
    inline bool definitions_selected(const std::vector<std::string>& args)
    {
        return std::find(args.begin(), args.end(), "-iw7-player-weapon-pair-definitions") != args.end();
    }
    inline bool definitions_exact(const std::vector<std::string>& args)
    {
        if (args.size() != 6) return false;
        constexpr std::array<std::size_t, 6> caps{4096, 32, 64, 32, 1024, 96};
        for (std::size_t i = 0; i < args.size(); ++i)
        {
            if (args[i].empty() || args[i].size() > caps[i]) return false;
            for (const unsigned char byte : args[i]) if (byte < 0x20 || byte == 0x7f) return false;
        }
        return args[1] == "-headless" && args[2] == "-iw7-player-weapon-pair-definitions" &&
            args[3] == "cp_zmb" && args[4][0] != '-' &&
            args[5] == "paris_enemy_cp_zmb_raygun_pair_definitions_a";
    }
}
