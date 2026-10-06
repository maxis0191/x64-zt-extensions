// Private, bounded source overlay for pinned x64-zt fab9358.
// Included inside zonetool::iw7 after load_enemy_source_zones is defined.
// Output contains owner-local assets and must remain under ignored runtime.
void dump_doom_texture_sources()
{
    const std::string pack = "paris_enemy_doom_source";
    const auto output = std::filesystem::path("dump") / pack;
    if (std::filesystem::exists(output)) throw std::runtime_error("Doom source output must be fresh");
    globals.dump = globals.dump_csv = globals.verify = false;
    asset_type_filter.clear();
    globals.target_game = game::iw7;
    load_enemy_source_zones("cp_zmb");
    filesystem::set_fastfile(pack);
    std::map<std::string, XModel*> models;
    std::map<std::string, ScriptableDef*> scriptables;
    std::map<std::string, Material*> materials;
    std::map<std::string, GfxImage*> images;
    std::set<std::string> references;
    auto reference = [&](const char* type, const char* name)
    {
        if (name && *name) references.insert(std::string(type) + ",," + name);
    };
    std::function<void(XModel*)> model;
    std::function<void(ScriptableDef*)> scriptable;
    std::function<void(ScriptableEventDef*, unsigned int)> events;
    std::function<void(ScriptablePartDef*, unsigned int)> parts;
    events = [&](ScriptableEventDef* data, unsigned int count)
    {
        if (count > 4096 || (count && !data)) throw std::runtime_error("Invalid Doom scriptable events");
        for (unsigned int i = 0; i < count; ++i)
        {
            auto& event = data[i];
            switch (event.type)
            {
            case Scriptable_EventType_Model: if (event.data.model.model) model(event.data.model.model); break;
            case Scriptable_EventType_AddModel: if (event.data.addModel.model) model(event.data.addModel.model); break;
            case Scriptable_EventType_SpawnDynent: if (event.data.spawnDynent.model) model(event.data.spawnDynent.model); break;
            case Scriptable_EventType_MaterialOverride: if (event.data.materialOverride.material)
                materials.emplace(event.data.materialOverride.material->name, event.data.materialOverride.material); break;
            case Scriptable_EventType_Collision: reference("physicsasset", event.data.collision.collmapName); break;
            case Scriptable_EventType_Animation:
                if (event.data.animation.animation) reference("xanim", event.data.animation.animation->name);
                events(event.data.animation.eventsAtEnd, event.data.animation.eventAtEndCount); break;
            case Scriptable_EventType_PFX:
                if (event.data.particleFX.effectDef.u.vfx)
                    reference(event.data.particleFX.effectDef.type == FX_COMBINED_VFX ? "vfx" : "fx", event.data.particleFX.effectDef.u.vfx->name);
                break;
            case Scriptable_EventType_Rumble: if (event.data.rumble.rumbleAsset) reference("rumble", event.data.rumble.rumbleAsset->name); break;
            case Scriptable_EventType_SetMayhem: if (event.data.setMayhem.mayhem) reference("mayhem", event.data.setMayhem.mayhem->name); break;
            case Scriptable_EventType_Random: events(event.data.random.eventsA, event.data.random.eventACount); events(event.data.random.eventsB, event.data.random.eventBCount); break;
            case Scriptable_EventType_NoteTrack:
                for (unsigned int j = 0; j < event.data.noteTrack.noteTrackCount; ++j)
                    events(event.data.noteTrack.noteTracks[j].events, event.data.noteTrack.noteTracks[j].numEvents);
                break;
            case Scriptable_EventType_ClientViewSelector: events(event.data.clientViewSelector.events1p, event.data.clientViewSelector.event1pCount); events(event.data.clientViewSelector.events3p, event.data.clientViewSelector.event3pCount); break;
            case Scriptable_EventType_TeamSelector: events(event.data.teamSelector.eventsPass, event.data.teamSelector.eventPassCount); events(event.data.teamSelector.eventsFail, event.data.teamSelector.eventFailCount); break;
            case Scriptable_EventType_CompassIcon: throw std::runtime_error("Unexpected Doom compass material dependency");
            default: break;
            }
        }
    };
    parts = [&](ScriptablePartDef* data, unsigned int count)
    {
        if (count > 4096 || (count && !data)) throw std::runtime_error("Invalid Doom scriptable parts");
        for (unsigned int i = 0; i < count; ++i)
        {
            for (unsigned int j = 0; j < data[i].numStates; ++j)
            {
                auto& state = data[i].states[j];
                events(state.base.events, state.base.numEvents);
                auto* base = state.type == Scriptable_StateType_Simple ? state.data.simple.base :
                    state.type == Scriptable_StateType_Health ? state.data.health.base : state.data.scripted.base;
                if (base) events(base->events, base->numEvents);
            }
            parts(data[i].childParts, data[i].numChildParts);
        }
    };
    scriptable = [&](ScriptableDef* data)
    {
        if (!data) return;
        if (!data->name || data->numXModels > 128 || scriptables.size() > 64)
            throw std::runtime_error("Invalid Doom scriptable closure");
        if (!scriptables.emplace(data->name, data).second) return;
        for (unsigned int i = 0; i < data->numXModels; ++i) model(data->models[i]);
        parts(data->parts, data->numParts);
        scriptable(data->nextScriptableDef);
    };
    model = [&](XModel* data)
    {
        if (!data || !data->name || data->numsurfs > 4096 || models.size() > 128)
            throw std::runtime_error("Invalid Doom model closure");
        if (!models.emplace(data->name, data).second) return;
        for (unsigned int i = 0; i < data->numsurfs; ++i)
        {
            auto* material = data->materialHandles[i];
            if (!material || !material->name) throw std::runtime_error("Missing Doom surface material");
            materials.emplace(material->name, material);
        }
        for (unsigned int i = 0; i < 6; ++i) if (data->lodInfo[i].modelSurfs) reference("xmodelsurfs", data->lodInfo[i].modelSurfs->name);
        if (data->physicsAsset) reference("physicsasset", data->physicsAsset->name);
        if (data->physicsFXShape) reference("physicsfxshape", data->physicsFXShape->name);
        if (data->proceduralBones) reference("xanimproceduralbones", data->proceduralBones->name);
        scriptable(data->scriptableMoverDef);
    };
    for (const auto* name : {"park_alien_gray", "zmb_brute_mascot_body", "park_clown_zombie",
        "park_clown_zombie_blue", "park_clown_zombie_green", "park_clown_zombie_orange", "park_clown_zombie_yellow"})
    {
        auto* entry = db_find_x_asset_entry(ASSET_TYPE_XMODEL, name);
        if (!entry || entry->type != ASSET_TYPE_XMODEL || !entry->header.model || DB_IsXAssetDefault(ASSET_TYPE_XMODEL, name))
            throw std::runtime_error(std::string("Missing retail Doom model: ") + name);
        model(entry->header.model);
    }
    std::string bindings = "material,image,semantic,type_hash,format,width,height,streamed\n";
    for (const auto& [name, data] : materials)
    {
        for (unsigned int i = 0; i < data->textureCount; ++i)
        {
            const auto& binding = data->textureTable[i];
            auto* image = binding.image;
            if (!image || !image->name) throw std::runtime_error("Missing Doom material image");
            images.emplace(image->name, image);
            bindings += name + ',' + image->name + ',' + std::to_string(binding.semantic) + ',' +
                std::to_string(binding.nameHash) + ',' + std::to_string(image->imageFormat) + ',' +
                std::to_string(image->width) + ',' + std::to_string(image->height) + ',' + std::to_string(image->streamed) + '\n';
        }
    }
    globals.dump = true;
    const auto restore = gsl::finally([] { globals.dump = false; asset_type_filter.clear(); });
    for (const auto& [name, data] : models) xmodel::dump(data);
    for (const auto& [name, data] : scriptables) scriptable_def::dump(data);
    for (const auto& [name, data] : materials) material::dump(data);
    // Capture the exact effective model registry; do not invent an empty replacement.
    DB_EnumXAssets(ASSET_TYPE_NET_CONST_STRINGS, [](XAssetHeader header)
    {
        if (header.netConstStrings && header.netConstStrings->stringType == NETCONSTSTRINGTYPE_XMODEL)
            net_const_strings::dump(header.netConstStrings);
    }, false);
    std::string inventory;
    for (const auto& [name, data] : models) inventory += "xmodel," + name + '\n';
    for (const auto& [name, data] : scriptables) inventory += "scriptable," + name + '\n';
    for (const auto& [name, data] : materials) inventory += "material," + name + '\n';
    std::string image_list;
    for (const auto& [name, data] : images) image_list += name + '\n';
    utils::io::write_file((output / "closure.csv").string(), inventory);
    utils::io::write_file((output / "bindings.csv").string(), bindings);
    utils::io::write_file((output / "images.txt").string(), image_list);
    std::string reference_list;
    for (const auto& row : references) reference_list += row + '\n';
    utils::io::write_file((output / "references.csv").string(), reference_list);
    // Asset dump names are type-erased. Replacing tagged name bytes would also
    // rename a physics/animation asset sharing a model's name. Let the typed
    // retail serializer follow the actual pointers with only these names changed.
    std::map<std::string, std::string> alias_names;
    std::vector<std::pair<const char**, const char*>> original_names;
    const auto restore_names = gsl::finally([&]
    {
        for (const auto& [field, original] : original_names) *field = original;
        filesystem::set_fastfile(pack);
    });
    auto rename = [&](auto* asset)
    {
        original_names.emplace_back(&asset->name, asset->name);
        const auto entry = alias_names.emplace(asset->name, "doom_negative_"s + asset->name).first;
        asset->name = entry->second.c_str();
    };
    for (const auto& [name, data] : models) rename(data);
    for (const auto& [name, data] : scriptables) rename(data);
    for (const auto& [name, data] : materials) rename(data);
    filesystem::set_fastfile(pack + "_aliases");
    for (const auto& [name, data] : models) xmodel::dump(data);
    for (const auto& [name, data] : scriptables) scriptable_def::dump(data);
    printf("DOOM_TEXTURE_SOURCE models=%zu scriptables=%zu materials=%zu images=%zu\n", models.size(), scriptables.size(), materials.size(), images.size());
}
