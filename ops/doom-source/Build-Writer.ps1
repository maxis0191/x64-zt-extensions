param([Parameter(Mandatory)][string]$PreparedRoot,[switch]$DryRun)
$ErrorActionPreference='Stop'
$ops=Split-Path $PSScriptRoot -Parent;$repo=Split-Path $ops -Parent
. "$ops/Lab-Paths.ps1"
. "$ops/Resource-Scheduler.Core.ps1"
. "$PSScriptRoot/Writer.Core.ps1"
$source=Join-Path $repo 'tools/x64-zt-enemy'
$prepared=Assert-IW7LabPath ([IO.Path]::GetFullPath($PreparedRoot)) (Join-Path $repo 'runtime')
$manifestPath=Assert-IW7LabPath (Join-Path $prepared 'writer-source.json') $prepared
if((Get-Item -LiteralPath $manifestPath).Length -gt 64KB){throw 'Bounded source manifest required.'}
$manifest=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifestHash=(Get-FileHash -LiteralPath $manifestPath).Hash
Assert-IW7DoomWriterManifest $manifest
$script:doomWriterInputBaseline=$null
function Assert-DoomImmutableInputs {
    if($script:doomWriterInputBaseline){Assert-IW7DoomWriterInputBaseline $script:doomWriterInputBaseline}
    if((Get-FileHash -LiteralPath $manifestPath).Hash -cne $manifestHash){throw 'Source manifest changed after admission planning.'}
    $head=& git -C $source rev-parse HEAD
    if($LASTEXITCODE -or $head -cne $manifest.source_pin){throw 'Exact pinned tool source required.'}
    $dirty=@(& git -C $source status --porcelain --untracked-files=all)
    if($LASTEXITCODE -or $dirty.Count){throw 'Changed shared tool checkout must be preserved.'}
    foreach($entry in $manifest.interface_hashes.PSObject.Properties){
        $relative=if($entry.Name -ceq '../game/shared.cpp'){'src/zonetool/game/shared.cpp'}else{'src/zonetool/zonetool/'+$entry.Name}
        $path=Assert-IW7LabPath (Join-Path $source $relative) $source
        if((Get-FileHash -LiteralPath $path).Hash -ine $entry.Value){throw 'Pinned source interface changed.'}
    }
    foreach($entry in $manifest.prepared_hashes.PSObject.Properties){
        $path=Assert-IW7LabPath (Join-Path $prepared $entry.Name) $prepared
        if((Get-Item -LiteralPath $path).Length -gt 8MB -or (Get-FileHash -LiteralPath $path).Hash -ine $entry.Value){throw 'Prepared source changed or exceeds bound.'}
    }
    foreach($pair in @(@('writer.cpp','writer_rigid.cpp'),@('half_uv.hpp','half_uv.hpp'))){
        if((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $pair[1])).Hash -ine $manifest.prepared_hashes.($pair[0])){throw 'Prepared adapter differs from reviewed source.'}
    }
    & python (Join-Path $PSScriptRoot 'verify_prepared.py') --prepared $prepared | Out-Null
    if($LASTEXITCODE){throw 'Generated header/counts/metrics differ from exact intermediate.'}
}
function Assert-DoomFreshOutputs {
    foreach($name in @('writer-input-baseline.json','doom-writer.exe','writer.obj','artifacts','geometry-roundtrip.json','writer-provenance.json','compile.log')){
        if(Test-Path -LiteralPath (Join-Path $prepared $name)){throw 'Fresh compilation/output paths required.'}
    }
}
Assert-DoomImmutableInputs
Assert-DoomFreshOutputs
$vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs=& $vswhere -products '*' -version '[17.0,18.0)' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1
if($LASTEXITCODE -or !$vs){throw 'Installed official MSVC x64 tools required.'}
$version=(Get-Content -LiteralPath (Join-Path $vs 'VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt') -Raw).Trim()
$vc=Join-Path $vs "VC/Tools/MSVC/$version"
$sdk=(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots').KitsRoot10
$sdkVersion=Get-ChildItem -LiteralPath (Join-Path $sdk 'Include') -Directory | Where-Object Name -match '^10\.0\.\d+\.0$' | Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1 -ExpandProperty Name
if(!$sdkVersion){throw 'Installed Windows SDK required.'}
$compiler=Join-Path $vc 'bin/Hostx64/x64/cl.exe'
$baselineFiles=@([pscustomobject]@{Path=$manifestPath;Scope=$prepared;MaximumBytes=64KB})
foreach($entry in $manifest.interface_hashes.PSObject.Properties){
    $relative=if($entry.Name -ceq '../game/shared.cpp'){'src/zonetool/game/shared.cpp'}else{'src/zonetool/zonetool/'+$entry.Name}
    $baselineFiles+=[pscustomobject]@{Path=(Join-Path $source $relative);Scope=$source;MaximumBytes=8MB}
}
foreach($entry in $manifest.prepared_hashes.PSObject.Properties){$baselineFiles+=[pscustomobject]@{Path=(Join-Path $prepared $entry.Name);Scope=$prepared;MaximumBytes=8MB}}
foreach($name in @('writer_rigid.cpp','half_uv.hpp','verify_prepared.py','prepare_writer.py','Writer.Core.ps1','Build-Writer.ps1')){
    $baselineFiles+=[pscustomobject]@{Path=(Join-Path $PSScriptRoot $name);Scope=$PSScriptRoot;MaximumBytes=8MB}
}
$baselineFiles+=[pscustomobject]@{Path=$compiler;Scope=$vc;MaximumBytes=64MB}
$script:doomWriterInputBaseline=New-IW7DoomWriterInputBaseline -Files $baselineFiles
Assert-DoomImmutableInputs
$include=@((Join-Path $vc 'include'),(Join-Path $sdk "Include/$sdkVersion/ucrt"),(Join-Path $sdk "Include/$sdkVersion/shared"),(Join-Path $sdk "Include/$sdkVersion/um"),(Join-Path $source 'src/zonetool'),$prepared)
$compilerArgs=@('/nologo','/std:c++20','/EHsc','/D_CRT_SECURE_NO_WARNINGS','/MD','/W4','/WX','/bigobj')
$compilerArgs+=@($include | ForEach-Object { '/I'+$_ })
$compilerArgs+=@(('/Fo'+(Join-Path $prepared 'writer.obj')),('/Fe'+(Join-Path $prepared 'doom-writer.exe')),(Join-Path $prepared 'writer.cpp'),'/link',('/LIBPATH:'+(Join-Path $vc 'lib/x64')),('/LIBPATH:'+(Join-Path $sdk "Lib/$sdkVersion/ucrt/x64")),('/LIBPATH:'+(Join-Path $sdk "Lib/$sdkVersion/um/x64")),'user32.lib','kernel32.lib')
$plan=[ordered]@{SourcePin=$manifest.source_pin;Candidate=$manifest.candidate_name;PreparedRoot=$prepared;Compiler=$compiler;Arguments=$compilerArgs;PhysicalBytes=2GB;CommitBytes=3GB;SingleTranslationUnit=$true;GameProcess=$false;Ready=$false}
if($DryRun){$plan | ConvertTo-Json -Depth 8;return}
Invoke-IW7ResourceJob -Scope $prepared -Kind Build -PhysicalBytes 2GB -CommitBytes 3GB -Owner 'Doom rigid pinned standalone writer' -Body {
    Assert-DoomImmutableInputs
    Assert-DoomFreshOutputs
    $script:doomWriterInputBaseline | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $prepared 'writer-input-baseline.json')
    $oldPath=$env:PATH
    try {
        $env:PATH=(Split-Path $compiler)+';'+$oldPath
        & $compiler @compilerArgs *> (Join-Path $prepared 'compile.log')
        if($LASTEXITCODE){throw 'Standalone compile failed; retained compile.log.'}
        Assert-DoomImmutableInputs
        $exe=Join-Path $prepared 'doom-writer.exe'
        $writerBaseline=New-IW7DoomWriterInputBaseline -Files @([pscustomobject]@{Path=$exe;Scope=$prepared;MaximumBytes=16MB})
        $rows=@(& $exe (Join-Path $prepared 'artifacts'))
        if($LASTEXITCODE){throw 'Doom geometry roundtrip failed.'}
        Assert-DoomImmutableInputs
        Assert-IW7DoomWriterInputBaseline $writerBaseline
        $roundtrip=($rows -join "`n") | ConvertFrom-Json
        Assert-IW7DoomWriterRoundtrip $manifest $roundtrip
        $assets=@(foreach($name in @("xmodel/$($manifest.candidate_name).xmb","xsurface/$($manifest.candidate_name)_lod0.xsb")){
            $path=Assert-IW7LabPath (Join-Path $prepared "artifacts/$name") $prepared
            $length=(Get-Item -LiteralPath $path).Length
            if($length -le 0 -or $length -gt 4MB){throw 'Bounded written asset required.'}
            [ordered]@{Path=$name;Bytes=$length;SHA256=(Get-FileHash -LiteralPath $path).Hash}
        })
        Assert-DoomImmutableInputs
        Assert-IW7DoomWriterInputBaseline $writerBaseline
        $roundtrip | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $prepared 'geometry-roundtrip.json')
        [ordered]@{Schema='iw7.doom-rigid-writer-build/1';SourcePin=$manifest.source_pin;Source=$manifest;
            InputBaseline=$script:doomWriterInputBaseline;InputSnapshotsMatch=$true;WriterExecutionBaseline=$writerBaseline;
            SourceManifestSHA256=$manifestHash;CompilerSHA256=$script:doomWriterInputBaseline.Files[-1].SHA256;
            WriterSHA256=$writerBaseline.Files[0].SHA256;Artifacts=$assets;Roundtrip=$roundtrip;FFBuilt=$false;PixelsVerified=$false;Ready=$false} |
            ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $prepared 'writer-provenance.json')
    } finally {$env:PATH=$oldPath}
}
