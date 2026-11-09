// Hero outfit witness (local private session only): stock jock body, writer-built bodies side by side in front of
// the local player, each with the stock jock head attached, animated with stock anims; capture_frame per pose.
// Dvars: paris_iwz_outfit_models "a,b,c" (default stock / sztest / szred), paris_iwz_outfit_anims "x,y",
// paris_iwz_outfit_view "x,y,z,yaw" (camera = player position; default the spawn point).

init()
{
    if ( getdvarint( "dedicated" ) )
        return;
    level thread outfit_tick();
    level thread outfit_watch();
}

outfit_tick()
{
    for ( ;; )
    {
        print( "[IWZ local] TICK t=" + gettime() );
        wait 0.5;
    }
}

outfit_watch()
{
    level waittill( "connected", player );
    player thread outfit_proof();
}

dvar_or( name, def )
{
    v = getdvar( name );
    if ( v == "" )
        return def;
    return v;
}

shot( name )
{
    executecommand( "capture_frame iwz" + name );
    wait 0.6;
    print( "[IWZ outfit] SHOT " + name );
}

outfit_proof()
{
    self endon( "disconnect" );
    while ( !isalive( self ) )
        wait 0.2;
    wait 6;
    self.ignoreme = 1;
    self takeallweapons();
    print( "[IWZ local] SPAWNED; origin=" + self.origin );
    info = level.player_character_info[4];
    print( "[IWZ outfit] TABLE jock body=" + info.body_model + " head=" + info.head_model + " outfits=" + level.iwz_outfits + " player=" + self.model );

    org = self.origin;
    yaw = self.angles[1];
    if ( getdvar( "paris_iwz_outfit_view" ) != "" )
    {
        v = strtok( getdvar( "paris_iwz_outfit_view" ), "," );
        org = ( float( v[0] ), float( v[1] ), float( v[2] ) );
        yaw = float( v[3] );
    }
    fwd = anglestoforward( ( 0, yaw, 0 ) );
    right = anglestoright( ( 0, yaw, 0 ) );
    eye = org + ( 0, 0, 60 );
    tr = bullettrace( eye, eye + fwd * 260, 0, self );
    dist = 200;
    if ( tr["fraction"] < 1 )
        dist = int( distance( eye, tr["position"] ) - 50 );
    if ( dist < 110 )
        dist = 110;
    print( "[IWZ outfit] VIEW org=" + org + " yaw=" + yaw + " dist=" + dist + " trace=" + tr["fraction"] );

    models = strtok( dvar_or( "paris_iwz_outfit_models", "body_zmb_hero_jock,body_zmb_hero_jock_sztest,body_zmb_hero_jock_szred" ), "," );
    ents = [];
    for ( i = 0; i < models.size; i++ )
    {
        side = ( i - ( models.size - 1 ) / 2.0 ) * 40;
        p = org + fwd * dist + right * side;
        g = bullettrace( p + ( 0, 0, 40 ), p - ( 0, 0, 200 ), 0, self )["position"];
        e = spawn( "script_model", g );
        e setmodel( models[i] );
        e.angles = ( 0, yaw + 180, 0 );
        e attach( "head_zmb_hero_jock", "", 1 );
        ents[i] = e;
        print( "[IWZ outfit] MODEL " + i + " " + models[i] + " at " + g );
    }
    self setorigin( org );
    self setplayerangles( ( 6, yaw, 0 ) );
    self freezecontrols( 1 );
    wait 2;
    shot( "outfit_bind" );

    anims = strtok( dvar_or( "paris_iwz_outfit_anims", "iw7_cp_zom_hoff_dj_idle_01,zom_core_run_f_1" ), "," );
    for ( a = 0; a < anims.size; a++ )
    {
        foreach ( e in ents )
            e scriptmodelplayanim( anims[a] );
        wait 1;
        for ( k = 0; k < 4; k++ )
        {
            shot( "outfit_a" + a + "_" + k );
            wait 0.25;
        }
        print( "[IWZ outfit] ANIM " + anims[a] + " done" );
    }
    // profile view: turn the models 90 degrees (side silhouette of the inflated jacket)
    foreach ( e in ents )
        e.angles = ( 0, yaw + 90, 0 );
    wait 0.5;
    shot( "outfit_side" );
    // distance / LOD: move the row away along the view
    foreach ( far in [ 500, 1000, 2000 ] )
    {
        for ( i = 0; i < ents.size; i++ )
        {
            side = ( i - ( ents.size - 1 ) / 2.0 ) * 40;
            ents[i].origin = ( org + fwd * far + right * side ) + ( 0, 0, ents[i].origin[2] - org[2] );
            ents[i].angles = ( 0, yaw + 180, 0 );
        }
        wait 1;
        shot( "outfit_far" + far );
    }
    print( "[IWZ local] DONE" );
}
