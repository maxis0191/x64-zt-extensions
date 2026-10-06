param([Parameter(Mandatory=$true)][string]$PinnedToolRoot)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$source = (Resolve-Path -LiteralPath $PinnedToolRoot).Path
$pin = 'fab935826c898806855376662a8a03317b3ad8f1'
if ((git -C $source rev-parse HEAD) -ne $pin -or (git -C $source status --porcelain --ignore-submodules=none)) {
    throw 'Use the clean reviewed enemy ZoneTool source at fab9358.'
}
$binary = Join-Path $source 'build/bin/x64/Release/zonetool.exe'
if ((Get-FileHash -LiteralPath $binary).Hash -ne 'B11706598DAD6A5256AF458A597908EC110082C1FF80263F176A5FBD1A6F0372') {
    throw 'Unexpected baseline ZoneTool binary.'
}
$output = Join-Path $repo ('runtime/doom-tool-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $output -Force | Out-Null
. "$PSScriptRoot/Resource-Scheduler.Core.ps1"
Invoke-IW7ResourceJob -Scope $output -Kind Build -Owner 'Doom minimal texture exporter' -PhysicalBytes 4GB -CommitBytes 6GB -Body {
# Source and compiler objects only: no game files or server/client clone.
Copy-Item -LiteralPath (Join-Path $source 'src') -Destination (Join-Path $output 'src') -Recurse
New-Item -ItemType Directory -Path (Join-Path $output 'build') | Out-Null
foreach ($projectSource in Get-ChildItem -LiteralPath (Join-Path $source 'build') -Filter '*.vcxproj' -File) {
    Copy-Item -LiteralPath $projectSource.FullName -Destination (Join-Path $output ('build/' + $projectSource.Name))
}
foreach ($folder in @('src','bin','obj')) {
    Copy-Item -LiteralPath (Join-Path $source ('build/' + $folder)) -Destination (Join-Path $output ('build/' + $folder)) -Recurse
}
# Read shared dependency source only. BuildProjectReferences=false avoids writing there.
New-Item -ItemType Junction -Path (Join-Path $output 'deps') -Target (Join-Path $source 'deps') | Out-Null
$cpp = Join-Path $output 'src/zonetool/zonetool/iw7/zonetool.cpp'
$text = [IO.File]::ReadAllText($cpp)
$marker = "`tstd::string string_table_csv(const StringTable* table)"
if ($text.Split(@($marker),[StringSplitOptions]::None).Count -ne 2) { throw 'Extractor insertion marker changed.' }
$text = $text.Replace($marker, "`t#include `"doom_texture_extract.hpp`"`r`n`r`n" + $marker)
$captureMarker = '(?m)^\tvoid dump_asset\(XAsset\* asset\)\r?\n\t\{'
if ([regex]::Matches($text,$captureMarker).Count -ne 1) { throw 'Image capture marker changed.' }
$text = [regex]::Replace($text,$captureMarker,"`tvoid capture_doom_loaded_image(XAsset* asset);`r`n`tvoid dump_asset(XAsset* asset)`r`n`t{`r`n`t`tcapture_doom_loaded_image(asset);")
$marker = "`t`tif (args.size() > 1)"
if ($text.Split(@($marker),[StringSplitOptions]::None).Count -ne 2) { throw 'Argument insertion marker changed.' }
$dispatch = @'
        if (std::find(args.begin(), args.end(), "-doom-textures-source") != args.end())
        {
            try { dump_doom_texture_sources(); fflush(nullptr); std::quick_exit(EXIT_SUCCESS); }
            catch (const std::exception& error) { fprintf(stderr, "DOOM_TEXTURE_ERROR %s\n", error.what()); fflush(nullptr); std::quick_exit(EXIT_FAILURE); }
        }
        const auto doom_audit = std::find(args.begin(), args.end(), "-doom-textures-audit");
        if (doom_audit != args.end())
        {
            try
            {
                if (doom_audit + 1 == args.end()) throw std::runtime_error("Doom audit needs the prepared manifest path");
                audit_doom_texture_pack(*(doom_audit + 1), std::find(args.begin(), args.end(), "-doom-cold-order") != args.end());
                fflush(nullptr); std::quick_exit(EXIT_SUCCESS);
            }
            catch (const std::exception& error) { fprintf(stderr, "DOOM_TEXTURE_ERROR %s\n", error.what()); fflush(nullptr); std::quick_exit(EXIT_FAILURE); }
        }
'@
$text = $text.Replace($marker, $dispatch + "`r`n" + $marker)
[IO.File]::WriteAllText($cpp,$text,[Text.UTF8Encoding]::new($false))
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'doom-textures/doom_texture_extract.hpp') -Destination (Join-Path (Split-Path $cpp -Parent) 'doom_texture_extract.hpp')
$project = Join-Path $output 'build/zonetool.vcxproj'
$xml = [IO.File]::ReadAllText($project).Replace('<MultiProcessorCompilation>true</MultiProcessorCompilation>','<MultiProcessorCompilation>false</MultiProcessorCompilation>')
[IO.File]::WriteAllText($project,$xml,[Text.UTF8Encoding]::new($false))
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$installation = & $vswhere -products '*' -version '[17.0,18.0)' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1
if (!$installation) { throw 'Installed VS2022 compiler was not found.' }
$msbuild = Join-Path $installation 'MSBuild/Current/Bin/MSBuild.exe'
    & $msbuild $project /t:Build /m:1 /nr:false /v:minimal /p:Configuration=Release /p:Platform=x64 /p:BuildProjectReferences=false /p:MultiProcessorCompilation=false /p:CL_MPCount=1 /p:PreBuildEventUseInBuild=false /p:PostBuildEventUseInBuild=false *> (Join-Path $output 'build.log')
    if ($LASTEXITCODE) { Get-Content -LiteralPath (Join-Path $output 'build.log') -Tail 30; throw 'Doom extractor compilation failed.' }
}
$candidate = Join-Path $output 'build/bin/x64/Release/zonetool.exe'
[ordered]@{SourceCommit=$pin;BaselineToolSHA256=(Get-FileHash -LiteralPath $binary).Hash;OverlaySHA256=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'doom-textures/doom_texture_extract.hpp')).Hash;ToolSHA256=(Get-FileHash -LiteralPath $candidate).Hash;Runtime=$output;Binary=$candidate;Validation='Compilation only; no asset or game validation.'} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'provenance.json') -Encoding utf8
Write-Output $candidate
