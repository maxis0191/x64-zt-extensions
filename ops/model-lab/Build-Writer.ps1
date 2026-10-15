param([Parameter(Mandatory)][string]$PreparedRoot,[switch]$DryRun,[string]$Python='python')
$ErrorActionPreference='Stop'
$ops=Split-Path $PSScriptRoot -Parent;$repo=Split-Path $ops -Parent
. "$ops/Lab-Paths.ps1"
. "$ops/Resource-Scheduler.Core.ps1"
$source=Join-Path $repo 'tools/x64-zt-enemy'
$prepared=Assert-IW7LabPath ([IO.Path]::GetFullPath($PreparedRoot)) (Join-Path $repo 'runtime')
$manifestPath=Join-Path $prepared 'writer-source.json'
if((Get-Item -LiteralPath $manifestPath).Length -gt 512KB){throw 'Bounded writer source manifest required.'}
$manifest=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$authored='geometry_profile' -cin $manifest.PSObject.Properties.Name
if($authored){
    if($manifest.geometry_profile -cne 'iw7-authored-rigid-v1'){throw 'Unknown original writer profile.'}
    $Python=(Get-Command $Python -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    & $Python -B -S "$PSScriptRoot/prepare_writer.py" --verify-authored $prepared | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Authored writer source recipe differs.'}
}
$artifactNames=if($authored){@($manifest.artifact_paths)}else{@('xmodel/paris_model_probe.xmb','xsurface/paris_model_probe_lod0.xsb')}
$head=& git -C $source rev-parse HEAD
if($LASTEXITCODE -or $head -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or $manifest.source_pin -cne $head){throw 'Exact pinned tool source required.'}
$dirty=@(& git -C $source status --porcelain --untracked-files=all)
if($LASTEXITCODE -or $dirty.Count){throw 'Changed shared tool checkout must be preserved.'}
$shadowSource='src/zonetool/zonetool/h1/converter/iw7/assets/xmodel.cpp'
$required=@('src/zonetool/zonetool/utils/io/assetmanager.hpp','src/zonetool/zonetool/utils/io/filesystem.hpp','src/zonetool/zonetool/utils/memory.hpp','src/zonetool/zonetool/iw7/structs.hpp','src/zonetool/zonetool/iw7/assets/xmodel.cpp','src/zonetool/zonetool/iw7/assets/xsurface.cpp',$shadowSource,'src/zonetool/game/shared.cpp','src/zonetool/zonetool/h1/converter/iw7/assets/xsurface.cpp','src/zonetool/zonetool/iw7/converter/h1/assets/xsurface.cpp')
if(@($manifest.source_hashes.PSObject.Properties).Count -ne $required.Count -or @($required | Where-Object { $_ -cnotin $manifest.source_hashes.PSObject.Properties.Name }).Count){throw 'Exact writer interface provenance required.'}
if($manifest.lod0_dist -isnot [long] -and $manifest.lod0_dist -isnot [int] -and $manifest.lod0_dist -isnot [double]){throw 'Explicit numeric LOD distance candidate required.'}
if($manifest.lod0_dist -ne 1000000 -or $manifest.has_lods -isnot [bool] -or !$manifest.has_lods -or $manifest.candidate_variable -cne 'lodInfo[0].dist'){throw 'Exact single-variable LOD candidate source required.'}
foreach($entry in $manifest.source_hashes.PSObject.Properties){
    $path=Assert-IW7LabPath (Join-Path $source $entry.Name) $source
    if((Get-FileHash -LiteralPath $path).Hash -ine $entry.Value){throw 'Pinned source interface changed after preparation.'}
}
foreach($entry in @(@('writer.cpp',$manifest.writer_sha256),@('probe_geometry.hpp',$manifest.header_sha256),@('geometry.source.json',$manifest.geometry_source_sha256))){
    $path=Assert-IW7LabPath (Join-Path $prepared $entry[0]) $prepared
    if((Get-FileHash -LiteralPath $path).Hash -ine $entry[1]){throw 'Prepared original input changed.'}
}
if($manifest.schema -cne 'iw7.model-writer-source/1' -or $manifest.ready -or $manifest.compiled -or $manifest.ff_built){throw 'Uncompiled source-only preparation required.'}
if($manifest.shadow_cutoff_lod -ne 6 -or $manifest.collision_lod -ne 255 -or $manifest.shadow_sentinel_source -cne $shadowSource){throw 'Exact independent shadow/collision sentinel candidate required.'}
$vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs=& $vswhere -products '*' -version '[17.0,18.0)' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1
if($LASTEXITCODE -or !$vs){throw 'Installed official MSVC x64 tools required.'}
$version=(Get-Content -LiteralPath (Join-Path $vs 'VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt') -Raw).Trim()
$vc=Join-Path $vs "VC/Tools/MSVC/$version"
$sdk=(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots').KitsRoot10
$sdkVersion=Get-ChildItem -LiteralPath (Join-Path $sdk 'Include') -Directory | Where-Object Name -match '^10\.0\.\d+\.0$' | Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1 -ExpandProperty Name
$compiler=Join-Path $vc 'bin/Hostx64/x64/cl.exe'
foreach($name in @('model-writer.exe','writer.obj','artifacts','geometry-roundtrip.json','writer-provenance.json','compile.log')){if(Test-Path -LiteralPath (Join-Path $prepared $name)){throw 'Fresh compilation/output paths required.'}}
$include=@((Join-Path $vc 'include'),(Join-Path $sdk "Include/$sdkVersion/ucrt"),(Join-Path $sdk "Include/$sdkVersion/shared"),(Join-Path $sdk "Include/$sdkVersion/um"),(Join-Path $source 'src/zonetool'),$prepared)
$compilerArgs=@('/nologo','/std:c++20','/EHsc','/D_CRT_SECURE_NO_WARNINGS','/MD','/W4','/bigobj')
$compilerArgs+=@($include | ForEach-Object { '/I'+$_ })
$compilerArgs+=@(('/Fo'+(Join-Path $prepared 'writer.obj')),('/Fe'+(Join-Path $prepared 'model-writer.exe')),(Join-Path $prepared 'writer.cpp'),'/link',('/LIBPATH:'+(Join-Path $vc 'lib/x64')),('/LIBPATH:'+(Join-Path $sdk "Lib/$sdkVersion/ucrt/x64")),('/LIBPATH:'+(Join-Path $sdk "Lib/$sdkVersion/um/x64")),'user32.lib','kernel32.lib')
$plan=[ordered]@{SourcePin=$head;PreparedRoot=$prepared;Compiler=$compiler;Arguments=$compilerArgs;PhysicalBytes=2GB;CommitBytes=3GB;SingleTranslationUnit=$true;GameProcess=$false;Ready=$false}
if($DryRun){$plan | ConvertTo-Json -Depth 8;return}
Invoke-IW7ResourceJob -Scope $prepared -Kind Build -PhysicalBytes 2GB -CommitBytes 3GB -Owner 'Original cube pinned standalone writer' -Body {
    $oldPath=$env:PATH
    try {
        $env:PATH=(Split-Path $compiler)+';'+$oldPath
        & $compiler @compilerArgs *> (Join-Path $prepared 'compile.log')
        if($LASTEXITCODE){throw 'Standalone compile failed; retained compile.log.'}
        $exe=Join-Path $prepared 'model-writer.exe'
        $rows=@(& $exe (Join-Path $prepared 'artifacts'))
        if($LASTEXITCODE){throw 'Original geometry roundtrip failed.'}
        $roundtrip=($rows -join "`n") | ConvertFrom-Json
        if($roundtrip.schema -cne 'iw7.model-roundtrip/1' -or !$roundtrip.geometry_roundtrip_verified -or $roundtrip.ready -or $roundtrip.ff_built -or $roundtrip.pixels_verified){throw 'Roundtrip status contradiction.'}
        if($authored){
            foreach($field in @('geometry_profile','namespace','zone','model_name','mesh_name','material_reference','vertices','triangles')){
                if($field -cin @('vertices','triangles') -and $roundtrip.$field -isnot [int] -and $roundtrip.$field -isnot [long]){throw 'Integer authored roundtrip counts required.'}
                if($roundtrip.$field -cne $manifest.$field){throw "Authored roundtrip $field differs from source."}
            }
            if($roundtrip.bones -ne 1 -or $roundtrip.surfaces -ne 1 -or $roundtrip.lods -ne 1 -or
                $roundtrip.physics_serialized -isnot [bool] -or $roundtrip.physics_serialized){throw 'Authored rigid profile roundtrip differs.'}
            if($roundtrip.geometry_roundtrip_verified -isnot [bool] -or !$roundtrip.geometry_roundtrip_verified -or
                $roundtrip.read_existing_supported -isnot [bool] -or !$roundtrip.read_existing_supported -or
                $roundtrip.iw7_normal_encoding_verified -isnot [bool] -or $roundtrip.iw7_normal_encoding_verified){throw 'Authored reader/normal qualification differs.'}
        }
        if($roundtrip.shadow_cutoff_lod -ne 6 -or $roundtrip.collision_lod -ne 255){throw 'Measured shadow/collision sentinel roundtrip differs.'}
        if(($roundtrip.lod0_dist -isnot [long] -and $roundtrip.lod0_dist -isnot [int] -and $roundtrip.lod0_dist -isnot [double]) -or
            $roundtrip.lod0_dist -ne 1000000 -or $roundtrip.has_lods -isnot [bool] -or !$roundtrip.has_lods){throw 'Measured single-LOD distance or unchanged hasLods differs.'}
        $roundtrip | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $prepared 'geometry-roundtrip.json')
        $assets=@(foreach($name in $artifactNames){
            $path=Assert-IW7LabPath (Join-Path $prepared "artifacts/$name") $prepared
            [ordered]@{Path=$name;Bytes=(Get-Item -LiteralPath $path).Length;SHA256=(Get-FileHash -LiteralPath $path).Hash}
        })
        [ordered]@{Schema='iw7.model-writer-build/1';SourcePin=$head;Source=$manifest;CompilerSHA256=(Get-FileHash -LiteralPath $compiler).Hash;WriterSHA256=(Get-FileHash -LiteralPath $exe).Hash;
            Artifacts=$assets;Roundtrip=$roundtrip;FFBuilt=$false;PixelsVerified=$false;Ready=$false} | ConvertTo-Json -Depth 12 |
            Set-Content -LiteralPath (Join-Path $prepared 'writer-provenance.json')
    } finally {$env:PATH=$oldPath}
}
