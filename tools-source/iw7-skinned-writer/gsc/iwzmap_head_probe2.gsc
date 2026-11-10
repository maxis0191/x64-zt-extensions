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
    names = strtok( getdvar( "paris_iwz_probe_models" ), "," );
    for ( i = 0; i < names.size; i++ )
    {
        side = ( i - ( names.size - 1 ) / 2.0 ) * 26;
        p = org + fwd * 110 + right * side + ( 0, 0, 30 );
        level thread probe_one( names[i], p, yaw + 180 );
        wait 0.2;
    }
    wait 3;
    self shot( "probe2_row" );    print( "[IWZ local] DONE" );
}

probe_one( name, p, yaw )
{
    e = spawn( "script_model", p );
    e.angles = ( 0, yaw, 0 );
    print( "[IWZ probe] try " + name );
    e setmodel( name );
    print( "[IWZ probe] set " + name + " model=" + e.model );
}