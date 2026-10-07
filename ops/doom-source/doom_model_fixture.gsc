// Dedicated-only measured Doom rigid helmet scene object. No player model, weapon or angle writes.
init()
{
    port = getdvarint("net_port");
    if (!getdvarint("dedicated") || !getdvarint("paris_isolated_lab") ||
        !getdvarint("paris_test_probe") || !getdvarint("paris_doom_model_probe") ||
        getdvar("fs_game") != "mods/paris_enemy_doom_helmet_rigid_a" || getdvar("mapname") != "cp_zmb" ||
        port < 27100 || port > 27999 || getdvar("g_password") == "" || getdvarint("sv_cheats") != 0) return;
    precachemodel("paris_doom_helmet_rigid_a");
    precachemodel("park_clown_zombie");
    level thread connections();
    print("[Paris Doom model] ARMED; model=paris_doom_helmet_rigid_a; pixels_pending=1.");
}

connections()
{
    level endon("game_ended");
    level waittill("connected", player);
    if (!isdefined(player) || !player paris_test_protect()) return;
    state = spawnstruct();
    state.failed = false;
    state.done = false;
    state.prop = undefined;
    state.control = undefined;
    player thread heartbeat(state);
    player thread witness(state);
    player thread disconnected(state);
    level thread cleanup(state);
}

witness(state)
{
    self endon("disconnect");
    level endon("game_ended");
    self waittill("spawned_player");
    deadline = gettime() + 90000;
    stable_since = -1;
    previous_origin = self.origin;
    previous_angles = self getplayerangles();
    for (;;)
    {
        if (state.failed || !self safe() || gettime() > deadline)
        {
            state.failed = true;
            print("[Paris Doom model] FAIL readiness_or_protection;");
            return;
        }
        angles = self getplayerangles();
        ready = self isonground() && isdefined(self.controlsfrozen) && !self.controlsfrozen &&
            (!isdefined(self.hostmigrationcontrolsfrozen) || !self.hostmigrationcontrolsfrozen) &&
            scripts\engine\utility::flag_exist("introscreen_over") && scripts\engine\utility::flag("introscreen_over") &&
            scripts\engine\utility::flag_exist("intro_gesture_done") && scripts\engine\utility::flag("intro_gesture_done");
        stable = distance(self.origin, previous_origin) <= 0.25 && distance(angles, previous_angles) <= 0.1;
        if (!ready || !stable)
        {
            stable_since = -1;
            previous_origin = self.origin;
            previous_angles = angles;
        }
        else
        {
            if (stable_since < 0) stable_since = gettime();
            if (gettime() - stable_since >= 1000) break;
        }
        wait 0.05;
    }
    // Follow the existing view yaw without writing the player's angles.
    angles = self getplayerangles();
    yaw = angles[1];
    forward = anglestoforward((0, yaw, 0));
    side = anglestoforward((0, yaw + 90, 0));
    center = (self geteye()) + forward * 144 + (0, 0, 8);
    origin = center - side * 40;
    prop = spawn("script_model", origin);
    if (!isdefined(prop)) { state.failed = true; print("[Paris Doom model] FAIL spawn_object;"); return; }
    prop.angles = (0, yaw + 30, 0);
    prop setmodel("paris_doom_helmet_rigid_a");
    state.prop = prop;
    control = spawn("script_model", center + side * 40);
    if (!isdefined(control)) { prop delete(); state.failed = true; print("[Paris Doom model] FAIL spawn_control;"); return; }
    control.angles = prop.angles;
    control setmodel("park_clown_zombie");
    control.scale = 0.25;
    state.control = control;
    print("[Paris Doom model] COMPARISON_INITIAL; eye=" + (self geteye()) + "; view=" + angles + "; custom_origin=" + prop.origin + "; retail_origin=" + control.origin + "; retail=park_clown_zombie; custom_scale=1; retail_scale=0.25.");
    print("[Paris Doom model] SCRIPT_MODEL_REQUESTED; model=paris_doom_helmet_rigid_a; entity=" + prop getentitynumber() + "; pixels_pending=1.");
    print("[Paris Doom model] READY_MODEL; model=paris_doom_helmet_rigid_a; game_time_ms=" + gettime() + "; pixels_pending=1.");
    for (i = 0; i < 240; i++)
    {
        if (state.failed || !self safe()) break;
        if (i == 32)
        {
            // Swap models at the same two fixed poses to separate placement
            // from custom asset rendering. Never replace the player's model.
            prop setmodel("park_clown_zombie"); prop.scale = 0.25;
            control setmodel("paris_doom_helmet_rigid_a"); control.scale = 1;
            print("[Paris Doom model] COMPARISON_SWAPPED; game_time_ms=" + gettime() + "; custom_origin=" + control.origin + "; retail_origin=" + prop.origin + "; custom_scale=1; retail_scale=0.25.");
        }
        wait 0.25;
    }
    state.done = true;
    if (isdefined(prop)) prop delete();
    if (isdefined(control)) control delete();
}

safe()
{
    return isdefined(level.players) && level.players.size == 1 &&
        getdvarint("sv_cheats") == 0 && self paris_test_protect();
}

heartbeat(state)
{
    self endon("disconnect");
    level endon("game_ended");
    self waittill("spawned_player");
    while (!state.done && !state.failed)
    {
        if (!self safe())
        {
            state.failed = true;
            if (isdefined(state.prop)) state.prop delete();
            if (isdefined(state.control)) state.control delete();
            print("[Paris Doom model] FAIL protection_or_exclusive_client;");
            return;
        }
        print("[Paris agent heartbeat] map=cp_zmb; " + self paris_test_safety_snapshot());
        wait 0.25;
    }
}

cleanup(state)
{
    level waittill("game_ended");
    state.done = true;
    if (isdefined(state.prop)) state.prop delete();
    if (isdefined(state.control)) state.control delete();
}

disconnected(state)
{
    level endon("game_ended");
    self waittill("disconnect");
    state.done = true;
    if (isdefined(state.prop)) state.prop delete();
    if (isdefined(state.control)) state.control delete();
}
