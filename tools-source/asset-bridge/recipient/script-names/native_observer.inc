// Insert before dump_enemy_scripts in the pinned private zonetool.cpp overlay.
// No stock, shared source, or E7 mutation is performed by this source file.
void observe_recipient_script_names(const std::string& donor_zone)
{
    static_assert(ASSET_TYPE_SCRIPTFILE == recipient_script_names::script_type);
    if (donor_zone != "cp_zmb")
        throw std::runtime_error("Script-name observation only permits cp_zmb");
    auto output = prepare_enemy_reference_output("sdk_beacon_script_names");
    output.replace_extension(".json"); // CREATE_NEW in the existing writer remains authoritative.
    if (!zone_exists(donor_zone))
        throw std::runtime_error("Script-name observation donor fastfile is missing");
    globals.dump = false;
    globals.dump_csv = false;
    globals.verify = false;
    asset_type_filter.clear();
    globals.target_game = game::iw7;
    load_enemy_source_zones(donor_zone);

    recipient_script_names::observation observed;
    const auto metadata = [](ScriptFile* script)
    {
        if (!script) throw std::runtime_error("Script-name metadata has no header");
        const auto content = recipient_script_names::bounded_name(script->name);
        const auto database = recipient_script_names::bounded_name(get_asset_name(ASSET_TYPE_SCRIPTFILE, script));
        return recipient_script_names::metadata{content, database, script->compressedLen,
            script->len, script->bytecodeLen, DB_IsXAssetDefault(ASSET_TYPE_SCRIPTFILE, database.c_str())};
    };
    std::exception_ptr enum_error;
    DB_EnumXAssets(ASSET_TYPE_SCRIPTFILE, [&](XAssetHeader header)
    {
        // Do not unwind through the engine enumerator. After refusal no further
        // name/metadata reads occur, though the engine may keep issuing callbacks.
        if (enum_error) return;
        try
        {
            auto* script = header.scriptfile;
            observed.enumerate(script, script ? script->name : nullptr, [&] { return metadata(script); });
        }
        catch (...) { enum_error = std::current_exception(); }
    }, false);
    if (enum_error) std::rethrow_exception(enum_error);

    for (std::size_t key = 0; key < recipient_script_names::keys.size(); ++key)
    {
        const auto* entry = db_find_x_asset_entry(ASSET_TYPE_SCRIPTFILE, recipient_script_names::keys[key]);
        auto* script = entry && entry->type == ASSET_TYPE_SCRIPTFILE ? entry->header.scriptfile : nullptr;
        observed.direct(key, entry != nullptr, entry ? entry->type : -1, script, [&] { return metadata(script); });
    }
    const auto result = observed.json();
    write_enemy_reference_output(output, result);
    printf("RECIPIENT_SCRIPT_NAMES map=cp_zmb bytes=%zu output=%s\n", result.size(), output.string().c_str());
    fflush(stdout);
}
