param([string]$ToolRoot)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
if (!$ToolRoot) { $ToolRoot = Join-Path $repo 'tools/x64-zt' }
$ToolRoot = (Resolve-Path -LiteralPath $ToolRoot).Path
$revision = 'a4cec149f0dd34aa13e37e8f7ab754af11e122ec'
git -C $ToolRoot merge-base --is-ancestor $revision HEAD
if ($LASTEXITCODE) { throw 'Unexpected ZoneTool ancestry.' }
function Write-Overlay([string]$Relative, [scriptblock]$Transform) {
    $base = ((git -C $ToolRoot show ($revision + ':' + $Relative)) -join "`n").TrimEnd() + "`n"
    $generated = & $Transform $base
    $target = Join-Path $ToolRoot $Relative
    $current = [IO.File]::ReadAllText($target).Replace("`r`n", "`n").TrimEnd() + "`n"
    $stamp = $target + '.rhino-overlay.sha256'
    $currentHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
    $owned = (Test-Path -LiteralPath $stamp) -and ([IO.File]::ReadAllText($stamp).Trim() -eq $currentHash)
    if ($current -ne $base -and $current -ne $generated -and !$owned) { throw "Unowned tool edit: $Relative" }
    [IO.File]::WriteAllText($target, $generated, [Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText($stamp, (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash)
}
function Replace-One([string]$Text, [string]$Marker, [string]$Replacement) {
    if (($Text.Split([string[]]@($Marker),[StringSplitOptions]::None)).Count -ne 2) { throw "Upstream marker mismatch: $Marker" }
    $Text.Replace($Marker,$Replacement)
}
Copy-Item -LiteralPath "$repo/src/custom_scripts/cp/experiments/zonetool_rhino.hpp" -Destination "$ToolRoot/src/zonetool/zonetool/iw7/zonetool_rhino.hpp"
Write-Overlay 'src/zonetool/component/exception.cpp' {
    param($base)
    $base = Replace-One $base '#include <utils/io.hpp>' "#include <utils/io.hpp>`n#include <utils/flags.hpp>"
    $marker = 'utils::thread::suspend_other_threads();'
    if (($base.Split([string[]]@($marker), [StringSplitOptions]::None)).Count -ne 3) { throw 'Unexpected ZoneTool exception dialog count.' }
    $headless = @'
            if (utils::flags::has_flag("headless"))
            {
                utils::io::write_file("zonetool-headless-error.txt", error_str);
                fprintf(stderr, "%s", error_str.c_str());
                fflush(nullptr);
                TerminateProcess(GetCurrentProcess(), exception_data.code);
                return;
            }
'@
    $base.Replace($marker, $headless.Replace("`r`n", "`n") + "`n" + $marker)
}
Write-Overlay 'src/zonetool/zonetool/iw7/zone.cpp' {
    param($base)
    $base = Replace-One $base '#include "zonetool.hpp"' "#include `"zonetool.hpp`"`n#include `"zonetool_rhino.hpp`""
    $base = Replace-One $base 'ADD_ASSET(ASSET_TYPE_DDL, ddl);' "ADD_ASSET(ASSET_TYPE_ANIMCLASS, rhino_anim_class);`n`t`t`tADD_ASSET(ASSET_TYPE_BEHAVIOR_TREE, rhino_behavior_tree);`n`t`t`tADD_ASSET(ASSET_TYPE_DDL, ddl);"
    $base = Replace-One $base 'ADD_ASSET(ASSET_TYPE_NAVMESH, nav_mesh);' ('ADD_ASSET(ASSET_TYPE_NAVMESH, nav_mesh);' + "`n" + '            if (name_.starts_with("paris_rhino") && !get_asset_pointer(type, name)) throw std::runtime_error("Unsupported dependency in Rhino-only pack");')
    $guard = @'
        if (name_.starts_with("paris_rhino"))
        {
            const std::unordered_set<int> forbidden{ASSET_TYPE_CLIPMAP, ASSET_TYPE_COMWORLD, ASSET_TYPE_GFXWORLD,
                ASSET_TYPE_GFXWORLD_TRANSIENT_ZONE, ASSET_TYPE_FXWORLD, ASSET_TYPE_GLASSWORLD,
                ASSET_TYPE_MAP_ENTS, ASSET_TYPE_ADDON_MAP_ENTS, ASSET_TYPE_PATHDATA, ASSET_TYPE_NAVMESH};
            std::string inventory;
            for (auto& asset : m_assets)
            {
                if (forbidden.contains(asset->type())) throw std::runtime_error("Map/world asset forbidden in Rhino-only pack");
                inventory += std::string(type_to_string(static_cast<XAssetType>(asset->type()))) + "," + asset->name() + "\n";
            }
            utils::io::write_file(name_ + ".assets.csv", inventory);
        }
'@
    Replace-One $base 'buf->init_streams(MAX_XFILE_COUNT);' ($guard.Replace("`r`n","`n") + "`nbuf->init_streams(MAX_XFILE_COUNT);")
}
Write-Overlay 'src/zonetool/zonetool/iw7/zonetool.cpp' {
    param($base)
    $base = Replace-One $base "namespace zonetool::iw7`n{" "namespace zonetool::iw7`n{`n    SndBank* isolate_rhino_bank(SndBank* donor, zone_memory* mem);"
    $capturePhysics = @'
        // Common/code shaders load before handle_params enables normal dumping.
        // Capture their bytecode at registration too, before temporary storage is reused.
        if (utils::flags::has_flag("rhino-extract") && type == ASSET_TYPE_PIXELSHADER && header->pixelShader)
            pixel_shader::dump(header->pixelShader);
        // Capture the serialized Havok packfile before DB registration mutates it.
        if (globals.dump && type == ASSET_TYPE_PHYSICSASSET && header->physicsAsset &&
            header->physicsAsset->name && std::string(header->physicsAsset->name) == "ragdoll_alien_queen")
        {
            physics_asset::dump(header->physicsAsset);
        }
'@
    $base = Replace-One $base 'dump_asset(&xasset);' ($capturePhysics.Replace("`r`n","`n") + "`ndump_asset(&xasset);")
    $base = Replace-One $base '// enable dumping' ('if (utils::flags::has_flag("rhino-extract")) filesystem::set_fastfile("paris_rhino");' + "`n`t`t// enable dumping")
    $extract = @'
        if (std::find(args.begin(), args.end(), "-rhino-extract") != args.end())
        {
            if (std::filesystem::exists("dump"))
            {
                for (const auto& entry : std::filesystem::recursive_directory_iterator("dump"))
                {
                    if (!entry.is_regular_file()) continue;
                    const auto file = entry.path().filename().string();
                    if (file == "ragdoll_alien_queen" || file == "ragdoll_alien_queen.hkx")
                        std::filesystem::remove(entry.path());
                }
            }
            filesystem::set_fastfile("paris_rhino");
            globals.target_game = game::iw7;
            globals.dump = true;
            asset_type_filter = {ASSET_TYPE_IMAGE, ASSET_TYPE_VERTEXSHADER, ASSET_TYPE_HULLSHADER,
                ASSET_TYPE_DOMAINSHADER, ASSET_TYPE_PIXELSHADER, ASSET_TYPE_COMPUTESHADER};
            for (const auto* zone : {"code_post_gfx", "global", "common", "global_mp", "global_cp", "common_mp", "common_cp", "cp_final"})
            {
                for (const auto& candidate : {std::string("techsets_") + zone, std::string(zone), std::string("patch_") + zone})
                    if (zone_exists(candidate)) load_zone(candidate, DB_LOAD_SYNC);
            }
            auto* acl = db_find_x_asset_header_safe(ASSET_TYPE_NET_CONST_STRINGS, "ncs_acl_level").netConstStrings;
            bool rhino_registered = acl && acl->stringType == NETCONSTSTRINGTYPE_ANIMCLASS &&
                acl->sourceType == NETCONSTSTRINGSOURCE_MAP;
            if (rhino_registered)
            {
                rhino_registered = false;
                for (unsigned int i = 0; i < acl->entryCount; ++i)
                    if (acl->stringList[i] && std::string(acl->stringList[i]) == "alien_rhino_animclass") rhino_registered = true;
            }
            if (!rhino_registered) throw std::runtime_error("Beast ncs_acl_level does not register alien_rhino_animclass");

            std::vector<std::filesystem::path> physics_roots;
            if (std::filesystem::exists("dump"))
            {
                for (const auto& entry : std::filesystem::recursive_directory_iterator("dump"))
                {
                    if (entry.is_regular_file() && entry.path().filename() == "ragdoll_alien_queen")
                    {
                        const auto hkx = std::filesystem::path(entry.path().string() + ".hkx");
                        if (std::filesystem::exists(hkx)) physics_roots.push_back(entry.path());
                    }
                }
            }
            if (physics_roots.size() != 1) throw std::runtime_error("Expected exactly one freshly dumped Rhino physicsasset pair");
            std::filesystem::create_directories("zonetool/paris_rhino/physicsasset");
            std::filesystem::copy_file(physics_roots[0], "zonetool/paris_rhino/physicsasset/ragdoll_alien_queen",
                std::filesystem::copy_options::overwrite_existing);
            std::filesystem::copy_file(std::filesystem::path(physics_roots[0].string() + ".hkx"),
                "zonetool/paris_rhino/physicsasset/ragdoll_alien_queen.hkx",
                std::filesystem::copy_options::overwrite_existing);
            globals.dump = false;
            asset_type_filter.clear();
            // The CSV lists shaders before their techsets. Refresh their source files
            // from the early DB-registration dumps before any asset parse can run.
            const auto pixel_sources = std::filesystem::path("zonetool/paris_rhino/techsets/ps");
            for (const auto& entry : std::filesystem::directory_iterator(pixel_sources))
            {
                if (!entry.is_regular_file() || entry.path().extension() != ".cso") continue;
                const auto fresh = std::filesystem::path(filesystem::get_dump_path()) / "techsets/ps" / entry.path().filename();
                const auto bytes = utils::io::read_file(fresh.string());
                if (!std::filesystem::exists(fresh) || (!bytes.empty() && (bytes.size() < 32 || bytes.compare(0, 4, "DXBC"))))
                    throw std::runtime_error(std::string("Fresh pixel shader dump invalid: ") + fresh.string());
                std::filesystem::copy_file(fresh, entry.path(), std::filesystem::copy_options::overwrite_existing);
            }
            auto* table = db_find_x_asset_header_safe(ASSET_TYPE_STRINGTABLE, "mp/dlc4_agent_definition.csv").stringTable;
            if (!table || table->columnCount < 14) throw std::runtime_error("Rhino definition table missing");
            std::string row;
            int matches = 0;
            for (int r = 0; r < table->rowCount; ++r)
            {
                auto* cells = table->values + r * table->columnCount;
                if (!cells[2].string || std::string(cells[2].string) != "alien_rhino") continue;
                ++matches;
                for (int c = 0; c < table->columnCount; ++c)
                {
                    if (c) row += ',';
                    row += '"';
                    for (const char* p = cells[c].string ? cells[c].string : ""; *p; ++p)
                    { if (*p == '"') row += '"'; row += *p; }
                    row += '"';
                }
                row += '\n';
            }
            if (matches != 1) throw std::runtime_error("Expected exactly one Rhino definition");
            utils::io::write_file("zonetool/paris_rhino/mp/paris_rhino_definition.csv", row);
        }
'@
    $audioInspect = @'
        if (std::find(args.begin(), args.end(), "-rhino-audio-inspect") != args.end() ||
            std::find(args.begin(), args.end(), "-rhino-audio-inspect-zmb") != args.end())
        {
            const bool spaceland = std::find(args.begin(), args.end(), "-rhino-audio-inspect-zmb") != args.end();
            for (const auto* zone : {"code_post_gfx", "global", "common", "global_mp", "global_cp", "common_mp", "common_cp", spaceland ? "cp_zmb" : "cp_final"})
                for (const auto& candidate : {std::string("techsets_") + zone, std::string(zone), std::string("patch_") + zone})
                    if (zone_exists(candidate)) load_zone(candidate, DB_LOAD_SYNC);
            DB_EnumXAssets(ASSET_TYPE_SOUND_BANK, [](XAssetHeader header)
            {
                auto* bank = header.soundBank;
                printf("RHINO_BANK name=%s zone=%s aliases=%u\n", bank->name ? bank->name : "<null>", bank->zone ? bank->zone : "<null>", bank->aliasCount);
                for (unsigned int i = 0; i < bank->aliasCount; ++i)
                {
                    const auto& list = bank->alias[i];
                    for (int h = 0; list.head && h < list.count; ++h)
                    {
                        const auto& alias = list.head[h];
                        printf("RHINO_AUDIO_HEAD bank=%s alias=%s head=%d file=%s secondary=%s stop=%s context=%u:%u\n",
                            bank->name ? bank->name : "", list.aliasName ? list.aliasName : "", h,
                            alias.assetFileName ? alias.assetFileName : "", alias.secondaryAliasName ? alias.secondaryAliasName : "",
                            alias.stopAliasName ? alias.stopAliasName : "", alias.contextType, alias.contextValue);
                    }
                    if (bank->alias[i].aliasName && std::string(bank->alias[i].aliasName).starts_with("queen_"))
                        printf("RHINO_ALIAS %s\n", bank->alias[i].aliasName);
                }
            }, false);
            if (!spaceland)
            {
                zone_memory audit_memory(1024 * 1024);
                auto* donor = db_find_x_asset_header_safe(ASSET_TYPE_SOUND_BANK, "cp_final.all").soundBank;
                const auto donor_snapshot = *donor;
                auto* isolated = isolate_rhino_bank(donor, &audit_memory);
                if (memcmp(donor, &donor_snapshot, sizeof(SndBank)))
                    throw std::runtime_error("Rhino isolation changed the retail donor bank");
                for (unsigned int i = 0; i < isolated->aliasCount; ++i)
                    printf("RHINO_AUDIO_SELECTED %s heads=%d\n", isolated->alias[i].aliasName, isolated->alias[i].count);
                printf("RHINO_AUDIO_AUDIT_OK index_verified=1 donor_unchanged=1 donor_aliases=%u sound_zones=%u music=%u ducks=%u\n",
                    donor->aliasCount, isolated->soundTable.zoneCount, isolated->musicSetCount, isolated->duckCount);
            }
            fflush(stdout);
            std::quick_exit(EXIT_SUCCESS);
        }
'@
    $base = Replace-One $base 'auto args = get_command_line_arguments();' ('auto args = get_command_line_arguments();' + "`n" + $audioInspect.Replace("`r`n","`n") + "`n" + $extract.Replace("`r`n","`n"))
    Replace-One $base 'bool do_exit = false;' 'bool do_exit = std::find(args.begin(), args.end(), "-rhino-extract") != args.end();'
}
Write-Overlay 'src/zonetool/zonetool/iw7/assets/sound_bank.cpp' {
    param($base)
    $isolatedBank = @'
    // Keep retail SAB addressing (zone/language/asset ids), but register only
    // the Rhino aliases under a unique bank name. Never edit the DB donor.
    SndBank* isolate_rhino_bank(SndBank* donor, zone_memory* mem)
    {
        if (!donor || !donor->alias || !donor->aliasCount || !donor->zone ||
            !donor->gameLanguage || !donor->soundLanguage)
            throw std::runtime_error("Rhino donor sound bank is incomplete");
        std::unordered_map<std::string, unsigned int> by_name;
        std::unordered_map<SndStringHash, unsigned int> by_id;
        std::vector<unsigned int> selected;
        std::unordered_set<unsigned int> included;
        for (unsigned int i = 0; i < donor->aliasCount; ++i)
        {
            const auto& list = donor->alias[i];
            if (!list.aliasName || !list.head || list.count <= 0 ||
                !by_name.emplace(list.aliasName, i).second || !by_id.emplace(list.id, i).second)
                throw std::runtime_error("Invalid or ambiguous Rhino donor alias list");
            if (std::string(list.aliasName).starts_with("queen_"))
            { included.insert(i); selected.push_back(i); }
        }
        if (selected.empty()) throw std::runtime_error("Rhino donor has no queen aliases");
        for (size_t p = 0; p < selected.size(); ++p)
        {
            const auto& list = donor->alias[selected[p]];
            for (int h = 0; h < list.count; ++h)
            {
                const auto& alias = list.head[h];
                const auto dependency = [&](const char* name, SndStringHash id)
                {
                    if ((!name || !*name) && !id) return;
                    auto found = by_name.end();
                    if (name && *name) found = by_name.find(name);
                    const auto hash_found = by_id.find(id);
                    if (found == by_name.end() && hash_found == by_id.end())
                        throw std::runtime_error("Rhino alias dependency is outside donor bank; inspect before adding it");
                    const auto index = found != by_name.end() ? found->second : hash_found->second;
                    if (id && donor->alias[index].id != id)
                        throw std::runtime_error("Rhino alias dependency name/hash mismatch");
                    // Fail closed if retail changes would import player dialogue.
                    if (!std::string(donor->alias[index].aliasName).starts_with("queen_") &&
                        std::string(donor->alias[index].aliasName) != "alien_footstep_mvmt")
                        throw std::runtime_error("Rhino dependency needs explicit review: non-queen alias");
                    if (included.insert(index).second) selected.push_back(index);
                };
                dependency(alias.secondaryAliasName, alias.secondaryId);
                dependency(alias.stopAliasName, alias.stopAliasID);
            }
        }
        if (selected.size() >= std::numeric_limits<unsigned short>::max())
            throw std::runtime_error("Rhino alias index exceeds retail capacity");
        auto* bank = mem->allocate<SndBank>();
        *bank = *donor;
        bank->name = mem->duplicate_string("paris_rhino_queen.all");
        bank->aliasCount = static_cast<unsigned int>(selected.size());
        bank->alias = mem->allocate<SndAliasList>(bank->aliasCount);
        for (unsigned int i = 0; i < bank->aliasCount; ++i)
        {
            bank->alias[i] = donor->alias[selected[i]];
            bank->alias[i].head = mem->allocate<SndAlias>(bank->alias[i].count);
            memcpy(bank->alias[i].head, donor->alias[selected[i]].head, sizeof(SndAlias) * bank->alias[i].count);
        }
        // Rebuild exactly the retail bucket/overflow representation against
        // the new count; copying the donor index addresses unrelated lists.
        bank->aliasIndex = mem->allocate<SndIndexEntry>(bank->aliasCount);
        memset(bank->aliasIndex, 0xFF, sizeof(SndIndexEntry) * bank->aliasCount);
        std::vector<bool> indexed(bank->aliasCount, false);
        constexpr auto empty = std::numeric_limits<unsigned short>::max();
        for (unsigned short i = 0; i < bank->aliasCount; ++i)
        {
            const auto bucket = bank->alias[i].id % bank->aliasCount;
            if (bank->aliasIndex[bucket].value == empty)
            { bank->aliasIndex[bucket].value = i; indexed[i] = true; }
        }
        for (unsigned short i = 0; i < bank->aliasCount; ++i)
        {
            if (indexed[i]) continue;
            auto tail = static_cast<unsigned short>(bank->alias[i].id % bank->aliasCount);
            while (bank->aliasIndex[tail].next != empty) tail = bank->aliasIndex[tail].next;
            unsigned short free = empty;
            for (unsigned int j = 0; j < bank->aliasCount; ++j)
                if (bank->aliasIndex[j].value == empty) { free = static_cast<unsigned short>(j); break; }
            if (free == empty) throw std::runtime_error("Rhino alias index exhausted");
            bank->aliasIndex[tail].next = free;
            bank->aliasIndex[free].value = i;
        }
        for (unsigned short i = 0; i < bank->aliasCount; ++i)
        {
            auto slot = static_cast<unsigned short>(bank->alias[i].id % bank->aliasCount);
            unsigned int steps = 0;
            while (slot != empty && bank->aliasIndex[slot].value != i && steps++ < bank->aliasCount)
                slot = bank->aliasIndex[slot].next;
            if (slot == empty || steps >= bank->aliasCount)
                throw std::runtime_error("Rhino alias index verification failed");
        }
        std::unordered_set<SndStringHash> required_ducks;
        for (unsigned int i = 0; i < bank->aliasCount; ++i)
            for (int h = 0; h < bank->alias[i].count; ++h)
                if (bank->alias[i].head[h].duck) required_ducks.insert(bank->alias[i].head[h].duck);
        std::vector<SndDuck> ducks;
        for (unsigned int i = 0; i < donor->duckCount; ++i)
            if (required_ducks.contains(donor->ducks[i].id))
            {
                if (donor->ducks[i].duckAlias && !by_id.contains(donor->ducks[i].duckAlias))
                    throw std::runtime_error("Rhino duck alias is outside donor bank; review dependency");
                if (donor->ducks[i].duckAlias && !included.contains(by_id.at(donor->ducks[i].duckAlias)))
                    throw std::runtime_error("Rhino duck requires an unselected alias; review dependency");
                ducks.push_back(donor->ducks[i]);
            }
        bank->duckCount = static_cast<unsigned int>(ducks.size());
        bank->ducks = ducks.empty() ? nullptr : mem->allocate<SndDuck>(ducks.size());
        if (!ducks.empty()) memcpy(bank->ducks, ducks.data(), sizeof(SndDuck) * ducks.size());
        // No donor ambient zones, mixes, music or reverb tables may override
        // Spaceland. Only selected-alias ducks are retained; global duck ids
        // continue to resolve in the unchanged common bank.
        bank->soundTable = {};
        bank->sendEffectCount = 0; bank->sendEffects = nullptr;
        bank->musicSetCount = 0; bank->musicSets = nullptr;
        printf("RHINO_AUDIO_ISOLATED bank=%s donor_aliases=%u aliases=%u\n", bank->name, donor->aliasCount, bank->aliasCount);
        return bank;
    }

'@
    $base = Replace-One $base 'void sound_bank::init(const std::string& name, zone_memory* mem)' ($isolatedBank.Replace("`r`n", "`n") + "`n`tvoid sound_bank::init(const std::string& name, zone_memory* mem)")
    $uniqueInit = @'
        if (name == "paris_rhino_queen.all")
        {
            if (!filesystem::get_fastfile().starts_with("paris_rhino"))
                throw std::runtime_error("Isolated Rhino bank requested outside Rhino pack");
            auto* donor = db_find_x_asset_header_safe(ASSET_TYPE_SOUND_BANK, "cp_final.all").soundBank;
            if (DB_IsXAssetDefault(ASSET_TYPE_SOUND_BANK, "cp_final.all"))
                throw std::runtime_error("Missing retail cp_final.all donor");
            this->asset_ = isolate_rhino_bank(donor, mem);
            return;
        }
'@
    $base = Replace-One $base 'this->asset_ = parse(name, mem);' ($uniqueInit.Replace("`r`n", "`n") + "`n`t`tthis->asset_ = parse(name, mem);")
    $marker = "void sound_bank::prepare(zone_buffer* buf, zone_memory* mem)`n`t{"
    $guard = @'
        if (filesystem::get_fastfile().starts_with("paris_rhino"))
        {
            if (name_ != "paris_rhino_queen.all" || !asset_ || !asset_->name ||
                std::string(asset_->name) != "paris_rhino_queen.all")
                throw std::runtime_error("Full donor/unreviewed bank forbidden in Rhino pack");
            if (!asset_ || !asset_->zone || !asset_->gameLanguage || !asset_->soundLanguage || !asset_->alias || !asset_->aliasCount)
                throw std::runtime_error("Missing retail Rhino soundbank: default/empty assets cannot be packed");
            if (asset_->soundTable.zoneCount || asset_->musicSetCount || asset_->sendEffectCount)
                throw std::runtime_error("Donor map audio metadata forbidden in Rhino pack");
            const std::unordered_set<std::string> required{"queen_attack_pounding", "queen_attack_pounding_second",
                "queen_attack_pounding_third", "queen_charge", "queen_charge_start", "queen_charge_start_v2",
                "queen_charge_start_v3", "queen_charge_to_stop", "queen_death", "queen_footstep", "queen_posture_01", "queen_posture_02"};
            std::unordered_set<std::string> found;
            for (unsigned int i = 0; i < asset_->aliasCount; ++i)
            {
                if (!asset_->alias[i].aliasName ||
                    (!std::string(asset_->alias[i].aliasName).starts_with("queen_") &&
                     std::string(asset_->alias[i].aliasName) != "alien_footstep_mvmt"))
                    throw std::runtime_error("Unrelated alias forbidden in Rhino pack");
                if (asset_->alias[i].aliasName && required.contains(asset_->alias[i].aliasName)) found.insert(asset_->alias[i].aliasName);
            }
            if (found.size() != required.size()) throw std::runtime_error("Retail Rhino sound aliases incomplete");
        }
'@
    Replace-One $base $marker ($marker + "`n" + $guard.Replace("`r`n","`n"))
}
Write-Overlay 'src/zonetool/zonetool/iw7/assets/techset.cpp' {
    param($base)
    foreach ($shader in @('vertex', 'hull', 'domain', 'pixel')) {
        $field = $shader + 'Shader'
        $marker = 'zone->add_asset_of_type(ASSET_TYPE_' + $shader.ToUpper() + 'SHADER, techniquePass.' + $field + '->name);'
        $abbrev = @{vertex='vs';hull='hs';domain='ds';pixel='ps'}[$shader]
        $copy = 'if (filesystem::get_fastfile().starts_with("paris_rhino")) { ' + $shader + '_shader::dump(techniquePass.' + $field + '); const auto relative = std::string("techsets/' + $abbrev + '/") + techniquePass.' + $field + '->name + ".cso"; const auto destination = std::string("zonetool/") + filesystem::get_fastfile() + "/" + relative; std::filesystem::create_directories(std::filesystem::path(destination).parent_path()); std::filesystem::copy_file(filesystem::get_dump_path() + relative, destination, std::filesystem::copy_options::overwrite_existing); }'
        $base = Replace-One $base $marker ($copy + "`n`t`t`t`t`t" + $marker)
    }
    $base
}
Write-Overlay 'src/zonetool/zonetool/iw7/assets/pixelshader.cpp' {
    param($base)
    $guard = @'
        // Pixel program storage can be reused after asset loading. Never overwrite
        // a valid early dump with stale bytes from a later dependency traversal.
        if (asset->prog.loadDef.programSize && (!asset->prog.loadDef.program ||
            asset->prog.loadDef.programSize < 32 || std::memcmp(asset->prog.loadDef.program, "DXBC", 4)))
        {
            printf("RHINO_SHADER stale pixel dump skipped: %s\n", asset->name);
            return;
        }
'@
    $base = Replace-One $base "void pixel_shader::dump(MaterialPixelShader* asset)`n`t{" ("void pixel_shader::dump(MaterialPixelShader* asset)`n`t{`n" + $guard.Replace("`r`n", "`n"))
    $check = @'
        if (buffer_size && (buffer_size < 32 || std::memcmp(buffer.data(), "DXBC", 4)))
            throw std::runtime_error(std::string("Invalid pixel shader bytecode: ") + name);
'@
    Replace-One $base 'const auto buffer = file.read_bytes(buffer_size);' ('const auto buffer = file.read_bytes(buffer_size);' + "`n" + $check.Replace("`r`n", "`n"))
}
Write-Overlay 'src/zonetool/zonetool/iw7/assets/gfximage.cpp' {
    param($base)
    $portableDump = @'
        if (asset->streamed && utils::flags::has_flag("rhino_portable_images") &&
            std::string(asset->name).starts_with("alien_queen_body_a_"))
        {
            dump_streamed_image(asset, false);
            const auto source = filesystem::get_dump_path() + "streamed_images/";
            const auto destination = std::string("zonetool/paris_rhino/streamed_images/");
            std::filesystem::create_directories(destination);
            const auto name = clean_name(asset->name);
            std::filesystem::copy_file(source + name + ".iw7Image", destination + name + ".iw7Image",
                std::filesystem::copy_options::overwrite_existing);
            int streams = 0;
            for (int i = 0; i < 4; ++i)
            {
                const auto file = name + "_stream" + std::to_string(i) + ".pixels";
                if (!std::filesystem::exists(source + file)) continue;
                std::filesystem::copy_file(source + file, destination + file,
                    std::filesystem::copy_options::overwrite_existing);
                ++streams;
            }
            if (!streams) throw std::runtime_error("No freshly decoded Rhino texture streams");
            ZONETOOL_INFO("Portable Rhino image %s: %d streams", asset->name, streams);
            return;
        }
'@
    $base = Replace-One $base 'void gfx_image::dump(GfxImage* asset)' ('void gfx_image::dump(GfxImage* asset)')
    $marker = "void gfx_image::dump(GfxImage* asset)`n`t{"
    $base = Replace-One $base $marker ($marker + "`n" + $portableDump.Replace("`r`n","`n"))
    $preferPortable = @'
        if (utils::flags::has_flag("rhino_portable_images") &&
            filesystem::get_fastfile() == "paris_rhino" && name.starts_with("alien_queen_body_a_"))
        {
            this->asset_ = this->parse_streamed_image(name, mem);
            if (!this->asset_) throw std::runtime_error("Portable Rhino image missing");
            if (this->asset_->pixelData) throw std::runtime_error("Unexpected resident pixels in streamed Rhino image");
            memset(&this->asset_->texture, 0, sizeof(this->asset_->texture));
            return;
        }
'@
    Replace-One $base 'this->asset_ = this->parse(name, mem);' ($preferPortable.Replace("`r`n","`n") + "`n`t`tthis->asset_ = this->parse(name, mem);")
}
$vswhere = "${env:ProgramFiles(x86)}/Microsoft Visual Studio/Installer/vswhere.exe"
$installation = & $vswhere -products '*' -version '[17.0,18.0)' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1
if (!$installation) { throw 'VS2022 C++/ATL toolchain not found.' }
Push-Location $ToolRoot
try {
    & ./tools/premake5.exe vs2022
    if ($LASTEXITCODE) { throw 'ZoneTool project generation failed.' }
    & "$installation/MSBuild/Current/Bin/MSBuild.exe" build/x64-zt.sln /m:3 /nr:false /v:minimal /p:Configuration=Release /p:Platform=x64
    if ($LASTEXITCODE) { throw 'Rhino ZoneTool build failed.' }
} finally { Pop-Location }
