// Station Zero hero outfits: the stock Spaceland character table (cp_zmb_player_character_setup) plus data-driven
// overrides. One row per hero: index (Spaceland register_player_character: 1 valley girl, 2 nerd, 3 rapper, 4 jock),
// body model, view model (first person arms), head model, hair model.
// "" keeps the stock value, "none" clears it (hair). New models must be in the map zone (xmodel rows).
init_player_characters()
{
    scripts\cp\maps\cp_zmb\cp_zmb_player_character_setup::init_player_characters();
    apply_outfits( outfit_rows() );
}

outfit_rows()
{
    rows = [];
    //            index  body                          view arms   head   hair
    rows[rows.size] = [ "4", "body_zmb_hero_jock_sztest", "",         "",    "" ];
    return rows;
}

apply_outfits( rows )
{
    level.iwz_outfits = 0;
    foreach ( row in rows )
    {
        idx = int( row[0] );
        info = level.player_character_info[idx];
        if ( !isdefined( info ) )
        {
            print( "[IWZ outfit] MISSING hero index " + idx );
            continue;
        }
        if ( row[1] != "" )
            info.body_model = outfit_model( row[1] );
        if ( row[2] != "" )
            info.view_model = outfit_model( row[2] );
        if ( row[3] != "" )
            info.head_model = outfit_model( row[3] );
        if ( row[4] == "none" )
            info.hair_model = undefined;
        else if ( row[4] != "" )
            info.hair_model = outfit_model( row[4] );
        level.iwz_outfits++;
        print( "[IWZ outfit] hero=" + idx + " body=" + info.body_model + " view=" + info.view_model + " head=" + info.head_model );
    }
}

outfit_model( name )
{
    precachemodel( name );
    return name;
}
