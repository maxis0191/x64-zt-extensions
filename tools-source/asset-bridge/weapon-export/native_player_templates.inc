// Inactive IW7 support. The CLI owner must add an explicit opt-in call separately.
namespace player_weapon_templates
{
    constexpr size_t json_cap = 2 * 1024 * 1024;

    void ordinary_ancestry(const std::filesystem::path& path)
    {
        for (auto p = std::filesystem::absolute(path); !p.empty(); p = p.parent_path())
        {
            const auto attributes = GetFileAttributesW(p.c_str());
            if (attributes != INVALID_FILE_ATTRIBUTES && (attributes & FILE_ATTRIBUTE_REPARSE_POINT))
                throw std::runtime_error("Player-template linked ancestry refused");
            if (attributes == INVALID_FILE_ATTRIBUTES && GetLastError() != ERROR_FILE_NOT_FOUND &&
                GetLastError() != ERROR_PATH_NOT_FOUND)
                throw std::runtime_error("Player-template path identity unavailable");
            if (p == p.root_path()) break;
        }
    }

    std::string bounded_file(const std::filesystem::path& path, const size_t cap)
    {
        ordinary_ancestry(path);
        if (!std::filesystem::is_regular_file(path))
            throw std::runtime_error("Player-template regular file required");
        std::ifstream stream(path, std::ios::binary);
        if (!stream) throw std::runtime_error("Player-template input could not be opened");
        std::vector<char> buffer(cap + 1);
        stream.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
        const auto count = static_cast<size_t>(stream.gcount());
        if (stream.bad() || count > cap)
            throw std::runtime_error("Player-template byte cap exceeded before hash or decode");
        return std::string(buffer.data(), count);
    }

    void exact_request(const std::string& path)
    {
        const auto raw = bounded_file(path, 256);
        for (size_t i = 0; i < raw.size(); ++i)
            if (raw[i] == '\r' && (i + 1 == raw.size() || raw[i + 1] != '\n'))
                throw std::runtime_error("Player-template CSV requires LF or complete CRLF");
        std::istringstream stream(raw);
        std::vector<std::string> rows;
        std::string row;
        while (std::getline(stream, row))
        {
            if (!row.empty() && row.back() == '\r') row.pop_back();
            rows.push_back(row);
        }
        std::sort(rows.begin(), rows.end());
        if (rows != std::vector<std::string>{"attachment,shredderpap1", "weapon,iw7_shredder_zm"})
            throw std::runtime_error("Exactly the allowlisted Shredder player/PAP pair required");
    }

    struct NamedAsset
    {
        XAsset asset{};
        std::string identity;
    };

    template <size_t N>
    NamedAsset exact_asset(const XAssetType type, const char (&name)[N])
    {
        const auto* entry = db_find_x_asset_entry(type, name);
        if (!entry || entry->type != static_cast<unsigned char>(type) || !entry->header.data ||
            DB_IsXAssetDefault(type, name))
            throw std::runtime_error("Player-template asset missing or default: " + std::string(name, N - 1));
        NamedAsset result;
        result.asset.type = type;
        result.asset.header = entry->header;
        const auto* registered_name = get_asset_name(&result.asset);
        if (!iw7_player_template_names::matches(registered_name, name))
            throw std::runtime_error("Player-template database name mismatch");
        result.identity.assign(name, N - 1); // Owned allowlisted identity after bounded validation.
        return result;
    }

    struct PrimaryReader
    {
        const WeaponCompleteDef* weapon;
        const WeaponDef* def;
        int classification() const { return static_cast<int>(def->weapClass); }
        int type() const { return static_cast<int>(def->weapType); }
        int inventory() const { return static_cast<int>(def->inventoryType); }
        int clip() const { return weapon->iClipSize; }
        int max_ammo() const { return def->iMaxAmmo; }
        int ammo_used() const { return def->iAmmoUsedPerShot; }
        int damage() const { return def->damage; }
        int speed() const { return def->iProjectileSpeed; }
        float lifetime() const { return def->projLifetime; }
        bool gun_model() const { return def->gunXModel != nullptr; }
        bool world_model() const { return def->worldModel != nullptr; }
        bool animations() const { return def->szXAnims != nullptr; }
    };
    void report_primary_failure(const iw7_player_template_primary::Failure& failure)
    {
        using Check = iw7_player_template_primary::Check;
        struct Spec { const char* key; const char* container; size_t offset; };
        const auto spec = [&]() -> Spec
        {
            switch (failure.check)
            {
            case Check::type: return {"weapType", "WeaponDef", offsetof(WeaponDef, weapType)};
            case Check::inventory: return {"inventoryType", "WeaponDef", offsetof(WeaponDef, inventoryType)};
            case Check::class_min: return {"weapClass_min", "WeaponDef", offsetof(WeaponDef, weapClass)};
            case Check::class_max: return {"weapClass_max", "WeaponDef", offsetof(WeaponDef, weapClass)};
            case Check::class_non_player: return {"weapClass_non_player", "WeaponDef", offsetof(WeaponDef, weapClass)};
            case Check::class_item: return {"weapClass_item", "WeaponDef", offsetof(WeaponDef, weapClass)};
            case Check::clip: return {"iClipSize", "WeaponCompleteDef", offsetof(WeaponCompleteDef, iClipSize)};
            case Check::max_ammo: return {"iMaxAmmo", "WeaponDef", offsetof(WeaponDef, iMaxAmmo)};
            case Check::ammo_used: return {"iAmmoUsedPerShot", "WeaponDef", offsetof(WeaponDef, iAmmoUsedPerShot)};
            case Check::damage: return {"damage", "WeaponDef", offsetof(WeaponDef, damage)};
            case Check::speed: return {"iProjectileSpeed", "WeaponDef", offsetof(WeaponDef, iProjectileSpeed)};
            case Check::lifetime_finite: return {"projLifetime_finite", "WeaponDef", offsetof(WeaponDef, projLifetime)};
            case Check::lifetime_positive: return {"projLifetime_positive", "WeaponDef", offsetof(WeaponDef, projLifetime)};
            case Check::gun_model: return {"gunXModel", "WeaponDef", offsetof(WeaponDef, gunXModel)};
            case Check::world_model: return {"worldModel", "WeaponDef", offsetof(WeaponDef, worldModel)};
            case Check::animations: return {"szXAnims", "WeaponDef", offsetof(WeaponDef, szXAnims)};
            default: throw std::runtime_error("Primary refusal key unavailable");
            }
        }();
        char line[256];
        const auto count = failure.kind == iw7_player_template_primary::Kind::float32_bits
            ? std::snprintf(line, sizeof(line), "IW7_PLAYER_TEMPLATE_PRIMARY_REFUSAL schema=1 predicate=%s kind=float32_bits value_bits=0x%08X container=%s source_offset=0x%zX\n",
                spec.key, static_cast<unsigned>(failure.bits), spec.container, spec.offset)
            : std::snprintf(line, sizeof(line), "IW7_PLAYER_TEMPLATE_PRIMARY_REFUSAL schema=1 predicate=%s kind=%s value=%d container=%s source_offset=0x%zX\n",
                spec.key, failure.kind == iw7_player_template_primary::Kind::presence ? "presence" : "int32",
                static_cast<int>(failure.integer), spec.container, spec.offset);
        if (count > 0 && static_cast<size_t>(count) < sizeof(line)) std::printf("%s", line);
        // No format failure, callback or diagnostic outcome permits the asset.
    }
    void compatible_pair(WeaponCompleteDef* weapon, WeaponAttachment* pap)
    {
        if (!weapon || !weapon->weapDef || !pap)
            throw std::runtime_error("Complete player/PAP source pointers required");
        const auto* def = weapon->weapDef;
        static_assert(static_cast<int>(WEAPTYPE_PROJECTILE) == 3 && static_cast<int>(WEAPINVENTORY_PRIMARY) == 0);
        static_assert(offsetof(WeaponDef, weapType) == 0x22C && offsetof(WeaponDef, inventoryType) == 0x240 && offsetof(WeaponDef, weapClass) == 0x234);
        static_assert(offsetof(WeaponCompleteDef, weapDef) == 0x08 && offsetof(WeaponCompleteDef, iClipSize) == 0xBC && offsetof(WeaponDef, iMaxAmmo) == 0x4A4 && offsetof(WeaponDef, iAmmoUsedPerShot) == 0x4C0);
        static_assert(offsetof(WeaponDef, damage) == 0x4D0 && offsetof(WeaponDef, iProjectileSpeed) == 0x690 && offsetof(WeaponDef, projLifetime) == 0x6A4);
        static_assert(offsetof(WeaponDef, gunXModel) == 0x08 && offsetof(WeaponDef, worldModel) == 0x38 && offsetof(WeaponDef, szXAnims) == 0x1C0);
        PrimaryReader reader{weapon, def};
        const auto failure = iw7_player_template_primary::first_failure(reader);
        if (failure.check != iw7_player_template_primary::Check::none)
        {
            report_primary_failure(failure);
            throw std::runtime_error("Reloadable player primary projectile fields not established");
        }
        if (!pap->papAttachment || pap->weaponType != WEAPTYPE_PROJECTILE)
            throw std::runtime_error("Native projectile PAP attachment fields not established");
        const std::array<unsigned int, 6> counts = {weapon->numAttachments, weapon->numAttachments2,
            weapon->numAttachments3, weapon->numAttachments4, weapon->numAttachments5, weapon->numAttachments6};
        const std::array<WeaponAttachment**, 6> lists = {weapon->attachments, weapon->attachments2,
            weapon->attachments3, weapon->attachments4, weapon->attachments5, weapon->attachments6};
        unsigned int occurrences = 0;
        for (size_t slot = 0; slot < lists.size(); ++slot)
        {
            if (counts[slot] > 64 || (counts[slot] && !lists[slot]))
                throw std::runtime_error("Bounded complete native attachment list required");
            for (unsigned int i = 0; i < counts[slot]; ++i)
            {
                const auto* attachment = lists[slot][i];
                if (attachment == pap) ++occurrences;
                else if (attachment &&
                    iw7_player_template_names::matches(attachment->szInternalName, "shredderpap1"))
                    throw std::runtime_error("PAP list points to a different registration than the exact database asset");
            }
        }
        if (occurrences != 1)
            throw std::runtime_error("Exact PAP registration must occur once in the player's base definition");
    }
}

void dump_iw7_player_weapon_templates(const std::string& donor_zone, const std::string& input_path,
    const std::string& pack_name)
{
    if (donor_zone != "cp_zmb" || !is_safe_enemy_token(pack_name) || pack_name.size() > 128 ||
        !pack_name.starts_with("paris_enemy_cp_zmb_") || !pack_name.ends_with("_player_weapon_source"))
        throw std::runtime_error("Finite Spaceland player-template output token required");
    player_weapon_templates::exact_request(input_path);
    const auto output = std::filesystem::path("dump") / pack_name;
    player_weapon_templates::ordinary_ancestry(output);
    if (std::filesystem::exists(output) || !zone_exists(donor_zone))
        throw std::runtime_error("Fresh output and the legitimate Spaceland donor are required");

    const auto old_dump = globals.dump, old_csv = globals.dump_csv, old_verify = globals.verify;
    const auto old_target = globals.target_game;
    const auto old_filter = asset_type_filter;
    const auto restore = gsl::finally([&]
    {
        globals.dump = old_dump; globals.dump_csv = old_csv; globals.verify = old_verify;
        globals.target_game = old_target; asset_type_filter = old_filter;
    });
    globals.dump = false; globals.dump_csv = false; globals.verify = false;
    globals.target_game = game::iw7;
    asset_type_filter.clear();
    load_enemy_source_zones(donor_zone);
    auto weapon = player_weapon_templates::exact_asset(ASSET_TYPE_WEAPON, "iw7_shredder_zm");
    auto pap = player_weapon_templates::exact_asset(ASSET_TYPE_ATTACHMENT, "shredderpap1");
    player_weapon_templates::compatible_pair(weapon.asset.header.weapon, pap.asset.header.attachment);

    std::filesystem::create_directories(output.parent_path());
    if (!std::filesystem::create_directory(output))
        throw std::runtime_error("Exclusive fresh player-template directory required");
    std::filesystem::create_directory(output / "weapons");
    std::filesystem::create_directory(output / "attachments");
    filesystem::set_fastfile(pack_name);
    globals.dump = true;
    asset_type_filter = {ASSET_TYPE_WEAPON, ASSET_TYPE_ATTACHMENT};
    ordered_json manifest = {{"schema", "iw7.player-weapon-templates/1"}, {"donor", donor_zone},
        {"native_source_pin", "fab935826c898806855376662a8a03317b3ad8f1"},
        {"weapon", weapon.identity}, {"pap_attachment", pap.identity},
        {"engine_weapon_type", "projectile"}, {"bo3_assets_authenticated", false},
        {"weapon_granted", false}, {"projectile_damage_verified", false},
        {"retail_pap_transaction_verified", false}, {"gameplay_accepted", false}, {"files", ordered_json::array()}};
    const std::array<std::pair<player_weapon_templates::NamedAsset*, const char*>, 2> assets = {{{&weapon, "weapons/iw7_shredder_zm.json"},
        {&pap, "attachments/shredderpap1.json"}}};
    for (const auto& item : assets)
    {
        dump_asset(&item.first->asset); // Existing full native serializers; no sparse authoring.
        const auto bytes = player_weapon_templates::bounded_file(output / item.second, player_weapon_templates::json_cap);
        if (bytes.empty()) throw std::runtime_error("Player-template serializer emitted an empty file");
        const auto data = ordered_json::parse(bytes);
        if (!data.is_object() || !data.contains("szInternalName") ||
            data["szInternalName"] != item.first->identity)
            throw std::runtime_error("Player-template JSON identity differs from its native source");
        manifest["files"].push_back({{"path", item.second}, {"bytes", bytes.size()},
            {"sha256", utils::cryptography::sha256::compute(reinterpret_cast<const uint8_t*>(bytes.data()), bytes.size(), true)}});
    }
    const auto receipt = manifest.dump(2) + "\n";
    if (receipt.size() > 16384) throw std::runtime_error("Player-template manifest bound exceeded");
    const auto path = output / "player-template-manifest.json";
    utils::io::write_file(path.string(), receipt);
    if (player_weapon_templates::bounded_file(path, 16384) != receipt)
        throw std::runtime_error("Player-template manifest readback differs");
    printf("IW7_PLAYER_WEAPON_TEMPLATES donor=cp_zmb weapon=iw7_shredder_zm pap=shredderpap1 count=2 output=%s\n", output.string().c_str());
    fflush(stdout);
}
