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
        if (!is_valid_asset_type(type)) throw std::runtime_error(std::string("Unknown stock reference type: ") + type);
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
        if (data->proceduralBones) reference("proceduralbones", data->proceduralBones->name);
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

// Headless engine round-trip evidence, separate from renderer/client acceptance.
// Cold order loads the custom FF before the map to expose unresolved stock refs.
bool doom_capture_pixels = false;
std::map<std::string, nlohmann::json> doom_loaded_pixels;
void capture_doom_loaded_image(XAsset* asset)
{
    if (!doom_capture_pixels || !asset || asset->type != ASSET_TYPE_IMAGE || !asset->header.image) return;
    const auto* image = asset->header.image;
    if (!image->name || !std::string_view(image->name).starts_with("doom_negative_")) return;
    if (!image->pixelData || image->streamed) throw std::runtime_error("Doom resident pixels unavailable at registration");
    // TEMP blocks are reused after consumption. Hash at registration, before
    // another asset/zone can overwrite the pointer retained in GfxImage.
    doom_loaded_pixels[image->name] = {{"width",image->width},{"height",image->height},
        {"mips",image->levelCount},{"bytes",image->dataLen1},{"format",image->imageFormat},
        {"sha256",utils::string::to_lower(utils::cryptography::sha256::compute(image->pixelData,image->dataLen1,true))}};
}
void audit_doom_texture_pack(const std::string& manifest_path, const bool cold)
{
    const auto manifest = nlohmann::json::parse(utils::io::read_file(manifest_path));
    globals.dump = globals.dump_csv = globals.verify = false;
    doom_loaded_pixels.clear();
    auto load_pack = []
    {
        doom_capture_pixels = true;
        const auto restore_capture = gsl::finally([] { doom_capture_pixels = false; });
        load_zone("paris_enemy_doom_negative", DB_LOAD_SYNC);
    };
    if (cold) load_pack();
    load_enemy_source_zones("cp_zmb");
    if (!cold) load_pack();
    auto require = [](const bool valid, const std::string& field)
    {
        if (!valid) throw std::runtime_error("Doom round-trip mismatch: " + field);
    };
    const auto stock_name = manifest.at("stock_model_registry").at("name").get<std::string>();
    auto* stock_registry = db_find_x_asset_header(ASSET_TYPE_NET_CONST_STRINGS, stock_name.c_str(), 0).netConstStrings;
    const auto& stock_strings = manifest.at("stock_model_registry").at("strings");
    require(stock_registry && stock_registry->sourceType == NETCONSTSTRINGSOURCE_MAP && stock_registry->entryCount == stock_strings.size(), "retail map registry count");
    for (unsigned int i = 0; i < stock_registry->entryCount; ++i)
        require(stock_registry->stringList[i] && stock_strings[i].get<std::string>() == stock_registry->stringList[i], "unchanged retail map registry");
    auto* registry = db_find_x_asset_header(ASSET_TYPE_NET_CONST_STRINGS, "ncs_mdl_doom_negative", 0).netConstStrings;
    require(registry && registry->stringType == NETCONSTSTRINGTYPE_XMODEL && registry->sourceType == NETCONSTSTRINGSOURCE_COMMON &&
        registry->stringList && registry->entryCount == manifest.at("models").size(), "dedicated common model registry");
    for (const auto& value : manifest.at("models"))
    {
        const auto name = "doom_negative_" + value.get<std::string>();
        bool found = false;
        for (unsigned int i = 0; i < registry->entryCount; ++i)
            if (registry->stringList[i] && name == registry->stringList[i]) found = true;
        require(found, name + ": retained network registry");
    }
    unsigned int surface_count = 0;
    for (const auto& value : manifest.at("models"))
    {
        const auto name = value.get<std::string>();
        const auto alias = "doom_negative_" + name;
        auto* original = db_find_x_asset_header(ASSET_TYPE_XMODEL, name.c_str(), 0).model;
        auto* clone = db_find_x_asset_header(ASSET_TYPE_XMODEL, alias.c_str(), 0).model;
        require(original && clone && original != clone && !DB_IsXAssetDefault(ASSET_TYPE_XMODEL, alias.c_str()), alias);
        require(clone->numsurfs == original->numsurfs && clone->numBones == original->numBones, alias + ": topology");
        require(clone->physicsAsset == original->physicsAsset && clone->physicsFXShape == original->physicsFXShape &&
            clone->proceduralBones == original->proceduralBones, alias + ": stock physics/bones");
        for (unsigned int i = 0; i < 6; ++i)
            require(clone->lodInfo[i].modelSurfs == original->lodInfo[i].modelSurfs, alias + ": stock LOD " + std::to_string(i));
        for (unsigned int i = 0; i < original->numsurfs; ++i)
        {
            auto* stock_material = original->materialHandles[i];
            auto* cloned_material = clone->materialHandles[i];
            require(stock_material && cloned_material && stock_material != cloned_material &&
                std::string(cloned_material->name) == "doom_negative_"s + stock_material->name, alias + ": material " + std::to_string(i));
            require(cloned_material->techniqueSet == stock_material->techniqueSet, alias + ": stock shader");
            require(cloned_material->stateFlags == stock_material->stateFlags && cloned_material->constantCount == stock_material->constantCount &&
                (!stock_material->constantCount || (cloned_material->constantTable && stock_material->constantTable &&
                    std::memcmp(cloned_material->constantTable,stock_material->constantTable,stock_material->constantCount * sizeof(MaterialConstantDef)) == 0)),
                alias + ": stock material constants/state flags");
            require(cloned_material->textureCount == stock_material->textureCount, alias + ": bindings");
            for (unsigned int j = 0; j < stock_material->textureCount; ++j)
            {
                const auto& original_binding = stock_material->textureTable[j];
                const auto& cloned_binding = cloned_material->textureTable[j];
                require(cloned_binding.semantic == original_binding.semantic && cloned_binding.nameHash == original_binding.nameHash,
                    alias + ": binding semantics");
                if (original_binding.semantic != 2 && original_binding.semantic != 14)
                    require(cloned_binding.image == original_binding.image, alias + ": stock non-color image");
            }
            ++surface_count;
        }
    }
    size_t resident_bytes = 0;
    for (const auto& value : manifest.at("images"))
    {
        const auto name = value.at("name").get<std::string>();
        auto* image = db_find_x_asset_header(ASSET_TYPE_IMAGE, name.c_str(), 0).image;
        require(image && !DB_IsXAssetDefault(ASSET_TYPE_IMAGE, name.c_str()), name);
        const auto format = value.at("format").get<unsigned int>();
        const auto expected_format = format == 29 || format == 72 || format == 78 || format == 99 || format == 91 ? 29 : 28;
        require(!image->streamed && image->imageFormat == expected_format &&
            image->width == value.at("width").get<unsigned int>() && image->height == value.at("height").get<unsigned int>() &&
            image->levelCount == value.at("mips").get<unsigned int>() && image->dataLen1 == value.at("bytes").get<unsigned int>(), name + ": resident mip layout");
        require(doom_loaded_pixels.contains(name), name + ": pre-registration capture");
        const auto& captured = doom_loaded_pixels.at(name);
        require(captured.at("width") == value.at("width") && captured.at("height") == value.at("height") &&
            captured.at("mips") == value.at("mips") && captured.at("bytes") == value.at("bytes") && captured.at("format") == expected_format,
            name + ": captured layout");
        require(captured.at("sha256") == value.at("pixels_sha256"), name + ": every loaded pixel byte");
        resident_bytes += image->dataLen1;
    }
    printf("DOOM_TEXTURE_ROUNDTRIP order=%s models=%zu surfaces=%u images=%zu resident_bytes=%zu pixel_capture=pre-registration rendering_verified=0\n",
        cold ? "mod-before-map" : "map-before-mod", manifest.at("models").size(), surface_count, manifest.at("images").size(), resident_bytes);
}
