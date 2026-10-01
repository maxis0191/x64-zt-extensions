param([string]$ToolRoot)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
if (!$ToolRoot) { $ToolRoot = Join-Path $repo 'tools/x64-zt' }
$ToolRoot = (Resolve-Path -LiteralPath $ToolRoot).Path
$revision = '6eebdd8a34c1f1f6b970fb5b15c0d0d360b1f5e4'
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
    $capturePhysics = @'
        // Capture the serialized Havok packfile before DB registration mutates it.
        if (globals.dump && type == ASSET_TYPE_PHYSICSASSET && header->physicsAsset &&
            header->physicsAsset->name && std::string(header->physicsAsset->name) == "ragdoll_alien_queen")
        {
            physics_asset::dump(header->physicsAsset);
        }
'@
    $base = Replace-One $base 'dump_asset(&xasset);' ($capturePhysics.Replace("`r`n","`n") + "`ndump_asset(&xasset);")
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
    $base = Replace-One $base 'auto args = get_command_line_arguments();' ('auto args = get_command_line_arguments();' + "`n" + $extract.Replace("`r`n","`n"))
    Replace-One $base 'bool do_exit = false;' 'bool do_exit = std::find(args.begin(), args.end(), "-rhino-extract") != args.end();'
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
