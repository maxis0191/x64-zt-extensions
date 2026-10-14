// Before the existing command loop: one bounded operation, no mixed/trailing effects.
if (iw7_player_template_cli::selected(args))
{
    try
    {
        if (!iw7_player_template_cli::exact(args))
            throw std::runtime_error("usage: -headless -iw7-player-weapon-templates cp_zmb <two-row.csv> <fresh-pack> (one operation)");
        dump_iw7_player_weapon_templates(args[3], args[4], args[5]);
        fflush(nullptr);
        std::quick_exit(EXIT_SUCCESS);
    }
    catch (const std::exception& error)
    {
        ZONETOOL_ERROR("IW7 player/PAP template export failed: %s", error.what());
    }
    catch (...)
    {
        ZONETOOL_ERROR("IW7 player/PAP template export failed with an unknown error");
    }
    fflush(nullptr);
    std::quick_exit(EXIT_FAILURE);
}
