// New hero outfits witness (local private session only).
// A: the local player is forced to each outfit row of level.player_character_info (cp_iwz_outfits table): body,
//    head, hair, view model; first-person frame with the start pistol.
// B: script models of the heroes (body + head + hair) side by side: front / back, idle and run anims, close-ups.
// Dvars: paris_iwz_hero_ids "4,3,2", paris_iwz_outfit_view "x,y,z,yaw", paris_iwz_hero_pistol "iw7_g18_zm".

init()
{
    if ( getdvarint( "dedicated" ) )
        return;
    level thread hero_tick();
    level thread hero_watch();
}

hero_tick()
{
    for ( ;; )
    {
        print( "[IWZ local] TICK t=" + gettime() );
        wait 0.5;
    }
}

hero_watch()
{
    level waittill( "connected", player );
    player thread hero_proof();
    level waittill( "connected", other );
    level.iwz_other = other;
    print( "[IWZ hero] SECOND client connected" );
}

other_segment( org, fwd, right, yaw, ids )
{
    t = 0;
    while ( t < 90 && ( !isdefined( level.iwz_other ) || !isalive( level.iwz_other ) ) )
    {
        wait 1;
        t++;
    }
    if ( !isdefined( level.iwz_other ) || !isalive( level.iwz_other ) )
    {
        print( "[IWZ hero] SECOND client not alive after " + t + " s: real-player frames skipped" );
        return;
    }
    o = level.iwz_other;
    o.ignoreme = 1;
    wait 2;
    for ( i = 0; i < ids.size; i++ )
    {
        idx = int( ids[i] );
        o dress_player( idx );
        p = org + fwd * 110;
        g = bullettrace( p + ( 0, 0, 40 ), p - ( 0, 0, 200 ), 0, o )["position"];
        o setorigin( g );
        o freezecontrols( 1 );
        o setplayerangles( ( 0, yaw + 180, 0 ) );
        wait 2;
        self shot( "hero_player_" + idx + "_front" );
        o setplayerangles( ( 0, yaw + 90, 0 ) );
        wait 1;
        self shot( "hero_player_" + idx + "_side" );
        o setplayerangles( ( 0, yaw, 0 ) );
        wait 1;
        self shot( "hero_player_" + idx + "_back" );
    }
    o setorigin( org + fwd * -300 );
}

dvar_or( name, def )
{
    v = getdvar( name );
    if ( v == "" )
        return def;
    return v;
}

shot( name, keep_weapon )
{
    if ( !isdefined( keep_weapon ) || !keep_weapon )
        self takeallweapons();
    wait 0.3;
    executecommand( "capture_frame iwz" + name );
    wait 0.6;
    print( "[IWZ hero] SHOT " + name );
}

hero_parts( idx )
{
    info = level.player_character_info[idx];
    parts = [];
    parts["body"] = info.body_model;
    parts["view"] = info.view_model;
    parts["head"] = info.head_model;
    parts["hair"] = info.hair_model;
    return parts;
}

dress_player( idx )
{
    p = hero_parts( idx );
    self detachall();
    self setmodel( p["body"] );
    self setviewmodel( p["view"] );
    if ( isdefined( p["head"] ) )
        self attach( p["head"], "", 1 );
    if ( isdefined( p["hair"] ) )
        self attach( p["hair"], "", 1 );
    hair = "none";
    if ( isdefined( p["hair"] ) )
        hair = p["hair"];
    print( "[IWZ hero] PLAYER hero=" + idx + " model=" + self.model + " view=" + p["view"] + " head=" + p["head"] + " hair=" + hair );
}

spawn_hero( idx, pos, yaw )
{
    p = hero_parts( idx );
    return spawn_dressed( p["body"], p["head"], p["hair"], pos, yaw );
}

spawn_dressed( body, head, hair, pos, yaw )
{
    e = spawn( "script_model", pos );
    e setmodel( body );
    e.angles = ( 0, yaw, 0 );
    if ( isdefined( head ) )
    {
        // script models do not draw an attach( head, "" ) (probe runs p1/p2b): the head is its own script model
        // linked at j_spine4 (the head model's root), hair attached to the head (bone merge j_neck / j_head)
        h = spawn( "script_model", e gettagorigin( "j_spine4" ) );
        h setmodel( head );
        h linkto( e, "j_spine4", ( 0, 0, 0 ), ( 0, 0, 0 ) );
        e.iwz_head = h;
        if ( isdefined( hair ) )
        {
            // an attach() on the linked head does not draw either: hair is a third script model linked at the
            // head's j_neck (the hair model's root)
            r = spawn( "script_model", h gettagorigin( "j_neck" ) );
            r setmodel( hair );
            r linkto( h, "j_neck", ( 0, 0, 0 ), ( 0, 0, 0 ) );
            e.iwz_hair = r;
        }
    }
    else if ( isdefined( hair ) )
        e attach( hair, "", 1 );
    return e;
}
place_row( ents, org, fwd, right, dist, gap, yaw )
{
    for ( i = 0; i < ents.size; i++ )
    {
        side = ( i - ( ents.size - 1 ) / 2.0 ) * gap;
        p = org + fwd * dist + right * side;
        g = bullettrace( p + ( 0, 0, 40 ), p - ( 0, 0, 200 ), 0, self )["position"];
        ents[i].origin = g;
        ents[i].angles = ( 0, yaw, 0 );
    }
}

hero_proof()
{
    self endon( "disconnect" );
    while ( !isalive( self ) )
        wait 0.2;
    wait 6;
    self.ignoreme = 1;
    print( "[IWZ local] SPAWNED; origin=" + self.origin );
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
    ids = strtok( dvar_or( "paris_iwz_hero_ids", "4,3,2" ), "," );
    pistol = dvar_or( "paris_iwz_hero_pistol", "iw7_g18_zm" );
    self setorigin( org );
    self setplayerangles( ( 4, yaw, 0 ) );
    self freezecontrols( 1 );
    if ( getdvarint( "paris_iwz_hero_nohud" ) )
        executecommand( "cg_draw2D 0" );

    // A: player forced to each hero, first person with the start pistol
    for ( i = 0; i < ids.size; i++ )
    {
        idx = int( ids[i] );
        self dress_player( idx );
        self takeallweapons();
        self giveweapon( pistol );
        self switchtoweaponimmediate( pistol );
        wait 2.5;
        self shot( "hero_fp_" + idx, 1 );
        self setplayerangles( ( 25, yaw - 20, 0 ) );
        wait 0.8;
        self shot( "hero_fpdown_" + idx, 1 );
        self setplayerangles( ( 4, yaw, 0 ) );
    }
    self takeallweapons();
    self setplayerangles( ( 8, yaw, 0 ) );
    self other_segment( org, fwd, right, yaw, ids );

    // B: script models side by side
    ents = [];
    for ( i = 0; i < ids.size; i++ )
        ents[i] = self spawn_hero( int( ids[i] ), org + fwd * 150, yaw + 180 );
    if ( getdvar( "paris_iwz_hero_ref" ) != "" )
    {
        // stock reference hero at the end of the row: "body,head[,hair]"
        r = strtok( getdvar( "paris_iwz_hero_ref" ), "," );
        hair = undefined;
        if ( r.size > 2 )
            hair = r[2];
        ents[ents.size] = spawn_dressed( r[0], r[1], hair, org + fwd * 150, yaw + 180 );
    }
    self place_row( ents, org, fwd, right, 150, 44, yaw + 180 );
    wait 2;
    self shot( "hero_row_bind" );
    anims = strtok( dvar_or( "paris_iwz_outfit_anims", "iw7_cp_zom_hoff_dj_idle_01,zom_core_run_f_1" ), "," );
    for ( a = 0; a < anims.size; a++ )
    {
        foreach ( e in ents )
            e scriptmodelplayanim( anims[a] );
        wait 1;
        for ( k = 0; k < 3; k++ )
        {
            self shot( "hero_row_a" + a + "_" + k );
            wait 0.3;
        }
    }
    // back view of the row (idle anim)
    foreach ( e in ents )
        e scriptmodelplayanim( anims[0] );
    self place_row( ents, org, fwd, right, 150, 44, yaw );
    wait 1;
    self shot( "hero_row_back" );
    // close-ups: one fresh (bind pose, no anim) model at a time, front / back / side, camera pitched down
    foreach ( e in ents )
    {
        e hide();
        if ( isdefined( e.iwz_head ) )
            e.iwz_head hide();
        if ( isdefined( e.iwz_hair ) )
            e.iwz_hair hide();
    }
    self setplayerangles( ( 12, yaw, 0 ) );
    for ( i = 0; i < ids.size; i++ )
    {
        one = [];
        one[0] = self spawn_hero( int( ids[i] ), org + fwd * 115, yaw + 180 );
        self place_row( one, org, fwd, right, 115, 0, yaw + 180 );
        wait 0.8;
        self shot( "hero_close_" + ids[i] + "_front" );
        self place_row( one, org, fwd, right, 115, 0, yaw );
        wait 0.6;
        self shot( "hero_close_" + ids[i] + "_back" );
        self place_row( one, org, fwd, right, 115, 0, yaw + 90 );
        wait 0.6;
        self shot( "hero_close_" + ids[i] + "_side" );
        one[0] scriptmodelplayanim( "zom_core_run_f_1" );
        self place_row( one, org, fwd, right, 115, 0, yaw + 180 );
        wait 0.7;
        self shot( "hero_close_" + ids[i] + "_run" );
        // face close-up: camera at head height, 40 units, after a streaming wait
        if ( isdefined( one[0].iwz_hair ) )
            one[0].iwz_hair delete();
        if ( isdefined( one[0].iwz_head ) )
            one[0].iwz_head delete();
        one[0] delete();
        one[0] = self spawn_hero( int( ids[i] ), org + fwd * 40, yaw + 180 );
        self place_row( one, org, fwd, right, 40, 0, yaw + 180 );
        self setplayerangles( ( -2, yaw, 0 ) );
        wait 3;
        self shot( "hero_face_" + ids[i] );
        self setplayerangles( ( 12, yaw, 0 ) );
        if ( isdefined( one[0].iwz_hair ) )
            one[0].iwz_hair delete();
        if ( isdefined( one[0].iwz_head ) )
            one[0].iwz_head delete();
        one[0] delete();
    }
    self setplayerangles( ( 4, yaw, 0 ) );    foreach ( e in ents )
    {
        e show();
        if ( isdefined( e.iwz_head ) )
            e.iwz_head show();
        if ( isdefined( e.iwz_hair ) )
            e.iwz_hair show();
    }
    // distance / LOD: row at 400, 900, 1600 (LOD0 <= 300, LOD1 <= 1000, LOD2 <= 10000)
    foreach ( e in ents )
        e scriptmodelplayanim( anims[0] );
    foreach ( far in [ 400, 900, 1600 ] )
    {
        self place_row( ents, org, fwd, right, far, 44, yaw + 180 );
        wait 1;
        self shot( "hero_far" + far );
    }
    print( "[IWZ local] DONE" );
}
