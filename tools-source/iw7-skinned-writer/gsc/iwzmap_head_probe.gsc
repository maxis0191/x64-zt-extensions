// Head attach probe (local private session): how do head models render on script models?
// Row: stock jock body + head attached with tag "" | "j_spine4" | "tag_origin"; then the new AJ with "j_spine4" + hair "j_neck".
init()
{
    if ( getdvarint( "dedicated" ) )
        return;
    level thread probe_tick();
    level thread probe_watch();
}

probe_tick()
{
    for ( ;; )
    {
        print( "[IWZ local] TICK t=" + gettime() );
        wait 0.5;
    }
}

probe_watch()
{
    level waittill( "connected", player );
    player thread probe();
}

shot( name )
{
    self takeallweapons();
    wait 0.3;
    executecommand( "capture_frame iwz" + name );
    wait 0.6;
    print( "[IWZ probe] SHOT " + name );
}

probe()
{
    self endon( "disconnect" );
    while ( !isalive( self ) )
        wait 0.2;
    wait 6;
    print( "[IWZ local] SPAWNED; origin=" + self.origin );
    org = ( -2300, 2300, -320 );
    yaw = 0;
    fwd = anglestoforward( ( 0, yaw, 0 ) );
    right = anglestoright( ( 0, yaw, 0 ) );
    self setorigin( org );
    self setplayerangles( ( 4, yaw, 0 ) );
    self freezecontrols( 1 );
    executecommand( "cg_draw2D 0" );
    specs = [];
    specs[0] = [ "body_zmb_hero_jock", "head_zmb_hero_jock", "", "", "" ];
    specs[1] = [ "body_zmb_hero_jock", "head_zmb_hero_jock", "j_spine4", "", "" ];
    specs[2] = [ "body_zmb_hero_jock", "head_zmb_hero_jock", "tag_origin", "", "" ];
    specs[3] = [ "body_iwz_hero_aj", "head_zmb_hero_jock", "j_spine4", "hair_iwz_hero_aj", "j_neck" ];
    specs[4] = [ "body_iwz_hero_poindexter", "head_iwz_hero_poindexter", "j_spine4", "hair_iwz_hero_poindexter", "j_neck" ];
    ents = [];
    for ( i = 0; i < specs.size; i++ )
    {
        s = specs[i];
        side = ( i - ( specs.size - 1 ) / 2.0 ) * 40;
        p = org + fwd * 140 + right * side;
        g = bullettrace( p + ( 0, 0, 40 ), p - ( 0, 0, 200 ), 0, self )["position"];
        e = spawn( "script_model", g );
        e setmodel( s[0] );
        e.angles = ( 0, yaw + 180, 0 );
        e attach( s[1], s[2], 1 );
        if ( s[3] != "" )
            e attach( s[3], s[4], 1 );
        ents[i] = e;
        print( "[IWZ probe] " + i + " body=" + s[0] + " head=" + s[1] + " tag='" + s[2] + "' at " + g + " tagpos=" + e gettagorigin( "j_head" ) );
    }
    wait 3;
    self shot( "probe_row" );
    self setplayerangles( ( -6, yaw, 0 ) );
    wait 1;
    self shot( "probe_row_up" );
    foreach ( e in ents )
        e scriptmodelplayanim( "zom_core_run_f_1" );
    self setplayerangles( ( 4, yaw, 0 ) );
    wait 1;
    self shot( "probe_run" );
    print( "[IWZ local] DONE" );
}
