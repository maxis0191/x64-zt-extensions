// Authored argument vectors only; not compiled/run until a separate CPP GO.
#include "native_player_cli.hpp"
#include <cstdio>
#include <stdexcept>

int main()
{
    unsigned checks = 0;
    const auto check = [&](bool value) { ++checks; if (!value) throw std::runtime_error("Player-template argv fixture failed"); };
    const std::vector<std::string> valid{"C:\\private tool\\zonetool.exe", "-headless", "-iw7-player-weapon-templates", "cp_zmb", "requested.csv", "paris_enemy_cp_zmb_raygun_template_a_player_weapon_source"};
    try
    {
        check(iw7_player_template_cli::selected(valid) && iw7_player_template_cli::exact(valid));
        auto args = valid; args.push_back("-dumpzone"); check(!iw7_player_template_cli::exact(args));
        args = valid; args.erase(args.begin()); check(!iw7_player_template_cli::exact(args));
        args = valid; args[1] = "-dumpzone"; check(!iw7_player_template_cli::exact(args));
        args = valid; args[3] = "cp_rave"; check(!iw7_player_template_cli::exact(args));
        args = valid; args[0].clear(); check(!iw7_player_template_cli::exact(args));
        args = valid; args[4] = std::string(1025, 'a'); check(!iw7_player_template_cli::exact(args));
        args = valid; args[4] = std::string("bad\0.csv", 8); check(!iw7_player_template_cli::exact(args));
        args = valid; args[5] = std::string(97, 'a'); check(!iw7_player_template_cli::exact(args));
        args = valid; args[2] = "-enemy-weapon-dump"; check(!iw7_player_template_cli::selected(args));
        if (checks != 10) throw std::runtime_error("Exact player-template argv count required");
        std::printf("IW7_PLAYER_TEMPLATE_ARGV_CHECKS=10\n");
        return 0;
    }
    catch (const std::exception& error) { std::fprintf(stderr, "%s\n", error.what()); return 1; }
}
