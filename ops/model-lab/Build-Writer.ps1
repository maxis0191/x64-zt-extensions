param([Parameter(Mandatory)][string]$PreparedRoot,[switch]$DryRun,[string]$Python='python',[string]$ToolSource,[string]$NativeJobAssembly)
$ErrorActionPreference='Stop'
$ops=Split-Path $PSScriptRoot -Parent;$repo=Split-Path $ops -Parent
. "$ops/Lab-Paths.ps1"
. "$ops/Resource-Scheduler.Core.ps1"
$source=if($ToolSource){
    $writerSourceRoot=[IO.Path]::GetFullPath($ToolSource)
    $writerSourceRoot=Assert-IW7LabPath $writerSourceRoot $writerSourceRoot
    if(!(Test-Path -LiteralPath $writerSourceRoot -PathType Container)){throw 'Existing ordinary writer tool source directory required.'}
    $writerSourceRoot
}else{Join-Path $repo 'tools/x64-zt-enemy'}
$prepared=Assert-IW7LabPath ([IO.Path]::GetFullPath($PreparedRoot)) (Join-Path $repo 'runtime')
$manifestPath=Join-Path $prepared 'writer-source.json'
if((Get-Item -LiteralPath $manifestPath).Length -gt 512KB){throw 'Bounded writer source manifest required.'}
$manifest=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifestSHA256=(Get-FileHash -LiteralPath $manifestPath).Hash
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
foreach($name in @('model-writer.exe','writer.obj','artifacts','geometry-roundtrip.json','writer-provenance.json','writer-native-run.json','discovery','compile','fixture')){
    if(Test-Path -LiteralPath (Join-Path $prepared $name)){throw 'Fresh compilation/output paths required.'}
}
if($DryRun){
    [ordered]@{Schema='iw7.model-writer-admission/1';SourcePin=$head;ToolSource=$source;PreparedRoot=$prepared;
        Compiler=$null;Arguments=$null;SDKDiscoveryDeferred=$true;NativeTypesLoaded=$false;BinaryInputsHashed=$false;
        LeaseAcquired=$false;PhysicalBytes=2GB;CommitBytes=3GB;SingleTranslationUnit=$true;GameProcess=$false;Ready=$false}|ConvertTo-Json -Depth 8
    return
}
if(!$NativeJobAssembly -or $PSVersionTable.PSVersion.Major -lt 7 -or
    '-NoExit' -notin [Environment]::GetCommandLineArgs()){throw 'Retained NativeJob assembly and fresh persistent PS7 -NoExit host required.'}
if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7.H1Diagnostics.JobMembers' -as [type])){throw 'Fresh NativeJob host required.'}
. "$repo/tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1"
. "$repo/tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1"
. "$repo/tools-source/asset-bridge/surfaces/MaterialV2.Compiler.ps1"
. "$repo/tools-source/asset-bridge/t7-iw7/T7Build.Profile.ps1"
$writerContext=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=[Collections.Generic.List[IDisposable]]::new()}
$originalContextVariable=Get-Variable writerContext
$bindings=[Collections.Generic.List[object]]::new()
$state=[ordered]@{Schema='iw7.model-writer-native-run/1';Status='Pending';LeaseToken=$null;LeaseReleased=$false;
    TreeClosureConfirmed=$true;Quarantined=$false;CleanupError=$null;Stages=[Collections.Generic.List[object]]::new();
    ToolchainFullyHermetic=$false;Ready=$false}
$plan=[pscustomobject]@{Schema='iw7.model-writer-native-plan/1';RunRoot=$prepared;Compiler=$null;Bindings=@();Inputs=@();
    Environment=$null;OutputLimitBytes=64MB;MetadataReserveBytes=1MB;GroupDeadlineSeconds=180}
$provenance=$null;$failure=$null
function Add-ModelWriterPin([string]$Path,[string]$Expected='') {
    Assert-H1Path $Path
    $item=Get-Item -LiteralPath $Path
    $pin=[pscustomobject]@{Path=$Path;Bytes=$item.Length;SHA256=(Get-FileHash -LiteralPath $Path).Hash.ToLowerInvariant()}
    if($Expected -and $pin.SHA256 -ine $Expected){throw 'Admitted model writer binding changed.'}
    $writerContext.Guards.Add((Open-H1Pin $pin));$bindings.Add($pin);$plan.Bindings=$bindings.ToArray()
    $pin
}
function Invoke-ModelWriterPhase([string]$Name,[string]$Kind,[string]$Image,[string]$SHA,[string[]]$Arguments,[string[]]$Artifacts,[int]$Seconds) {
    if(!$writerContext.Closed -or !$writerContext.Lease){throw 'Previous original job closure and the same admission required.'}
    $dir=Join-Path $prepared $Name;[IO.Directory]::CreateDirectory($dir)|Out-Null
    $script:T7CurrentStage=[pscustomobject]@{Name=$Name;Stage=$Kind;Image=$Image;Arguments=$Arguments;Artifacts=$Artifacts}
    $current=[ordered]@{Name=$Name;Stage=$Kind;PlanSHA256=([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData(
        [Text.Encoding]::UTF8.GetBytes(($plan|ConvertTo-Json -Depth 12 -Compress))))).ToLowerInvariant();
        DeadlineSeconds=$Seconds;MaxObservedOutputBytes=0L;CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
    $state.Stages.Add($current)
    $start=New-T7Start $plan $script:T7CurrentStage $dir
    $writerContext.Owner=$null # A closed prior owner cannot attest a failed new factory.
    Invoke-T7OwnedStage $plan $current $writerContext $start $SHA $dir (Get-H1Clock)
    if(!$writerContext.Closed -or !$current.TreeClosureConfirmed -or $current.ExitCode -ne 0){throw 'Model writer original job did not qualify.'}
    if($Kind -ceq 'Compile'){$current.Artifacts=@(Get-H1CompilerArtifacts $plan $writerContext)}
    $current
}
try {
    $writerContext.Lease=Enter-IW7ResourceLease -Scope $prepared -Kind Build -PhysicalBytes 2GB -CommitBytes 3GB -Owner 'Pinned standalone model writer H1 original jobs'
    $state.LeaseToken=$writerContext.Lease.Token;$script:T7GroupStarted=Get-H1Clock
    # Every opaque read, native import and VS/SDK probe is after this ONE admission.
    $assembly=[IO.Path]::GetFullPath($NativeJobAssembly)
    $null=Add-ModelWriterPin $assembly '5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8'
    foreach($entry in $manifest.source_hashes.PSObject.Properties){$null=Add-ModelWriterPin (Join-Path $source $entry.Name) $entry.Value}
    foreach($entry in @(@('writer-source.json',$manifestSHA256),@('writer.cpp',$manifest.writer_sha256),
        @('probe_geometry.hpp',$manifest.header_sha256),@('geometry.source.json',$manifest.geometry_source_sha256))){
        $null=Add-ModelWriterPin (Join-Path $prepared $entry[0]) $entry[1]
    }
    foreach($name in @('tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1','tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1',
        'tools-source/asset-bridge/h1-fixture/H1Native.JobMembers.cs','tools-source/asset-bridge/t7-iw7/T7Build.Profile.ps1',
        'tools-source/asset-bridge/surfaces/MaterialV2.Compiler.ps1','ops/model-lab/Build-Writer.ps1')){$null=Add-ModelWriterPin (Join-Path $repo $name)}
    $null=[Reflection.Assembly]::LoadFrom($assembly)
    Add-Type -LiteralPath "$repo/tools-source/asset-bridge/h1-fixture/H1Native.JobMembers.cs"
    $environment=[ordered]@{}
    foreach($key in 'SystemRoot','windir','SystemDrive','USERPROFILE','LOCALAPPDATA','APPDATA'){$environment[$key]=[Environment]::GetEnvironmentVariable($key)}
    $environment.PATH=[Environment]::SystemDirectory;$plan.Environment=[pscustomobject]$environment
    $vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    $wherePin=Add-ModelWriterPin $vswhere
    $discovery=Invoke-ModelWriterPhase 'discovery' 'Fixture' $vswhere $wherePin.SHA256 @('-products','*','-version','[17.0,18.0)','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath') @() 15
    $vs=@(Get-Content -LiteralPath (Join-Path $prepared 'discovery/stdout.log') | Where-Object {$_}) | Select-Object -First 1
    if(!$vs){throw 'Installed official MSVC x64 tools required.'}
    $version=(Get-Content -LiteralPath (Join-Path $vs 'VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt') -Raw).Trim()
    $vc=Join-Path $vs "VC/Tools/MSVC/$version"
    $sdk=(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots').KitsRoot10
    $sdkVersion=Get-ChildItem -LiteralPath (Join-Path $sdk 'Include') -Directory | Where-Object Name -match '^10\.0\.\d+\.0$' | Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1 -ExpandProperty Name
    $compiler=Join-Path $vc 'bin/Hostx64/x64/cl.exe';$plan.Compiler=$compiler
    $policy=Get-MaterialV2CompilerPolicy $compiler
    $clPin=Add-ModelWriterPin $compiler $policy.CompilerSHA256
    $null=Add-ModelWriterPin $policy.Telemetry $policy.TelemetrySHA256
    $plan.Environment.PATH=(Split-Path $compiler)+';'+[Environment]::SystemDirectory
    $include=@((Join-Path $vc 'include'),(Join-Path $sdk "Include/$sdkVersion/ucrt"),(Join-Path $sdk "Include/$sdkVersion/shared"),(Join-Path $sdk "Include/$sdkVersion/um"),(Join-Path $source 'src/zonetool'),$prepared)
    $compilerArgs=@('/nologo','/std:c++20','/EHsc','/D_CRT_SECURE_NO_WARNINGS','/MD','/W4','/bigobj')+@($include|ForEach-Object{'/I'+$_})
    $compilerArgs+=@(('/Fo'+(Join-Path $prepared 'compile/writer.obj')),('/Fe'+(Join-Path $prepared 'compile/model-writer.exe')),
        (Join-Path $prepared 'writer.cpp'),'/link',('/LIBPATH:'+(Join-Path $vc 'lib/x64')),('/LIBPATH:'+(Join-Path $sdk "Lib/$sdkVersion/ucrt/x64")),('/LIBPATH:'+(Join-Path $sdk "Lib/$sdkVersion/um/x64")),'user32.lib','kernel32.lib')
    $compiled=Invoke-ModelWriterPhase 'compile' 'Compile' $compiler $clPin.SHA256 $compilerArgs @('writer.obj','model-writer.exe') 120
    $exe=Join-Path $prepared 'model-writer.exe'
    Copy-Item -LiteralPath (Join-Path $prepared 'compile/model-writer.exe') -Destination $exe
    Copy-Item -LiteralPath (Join-Path $prepared 'compile/writer.obj') -Destination (Join-Path $prepared 'writer.obj')
    $compiledExecutable=@($compiled.Artifacts|Where-Object {$_.Path -eq (Join-Path $prepared 'compile/model-writer.exe')})
    if($compiledExecutable.Count -ne 1){throw 'One measured original compiler executable artifact required.'}
    $writerPin=Add-ModelWriterPin $exe $compiledExecutable[0].SHA256
    $fixture=Invoke-ModelWriterPhase 'fixture' 'Fixture' $exe $writerPin.SHA256 @((Join-Path $prepared 'artifacts')) @() 30
    $roundtrip=Read-H1SmallJson (Join-Path $prepared 'fixture/stdout.log') 1MB
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
    foreach($asset in $assets){$null=Add-ModelWriterPin (Join-Path $prepared ('artifacts/'+$asset.Path)) $asset.SHA256}
    $provenance=[ordered]@{Schema='iw7.model-writer-build/1';SourcePin=$head;ToolSource=$source;Source=$manifest;
        CompilerSHA256=$clPin.SHA256;WriterSHA256=$writerPin.SHA256;Artifacts=$assets;Roundtrip=$roundtrip;FFBuilt=$false;PixelsVerified=$false;Ready=$false}
    $state.Status='NativeRoundtripPassed'
}catch{$failure=$_;$state.Status='Failed';$state.Failure=$_.Exception.Message}
finally {
    if($writerContext.Lease){
        Complete-H1Stage $writerContext $state -BeforeReleaseCheck {
            Confirm-H1BoundInputs $plan
            foreach($guard in $writerContext.Guards){$guard.Dispose()}
            $writerContext.Guards.Clear()
        }
    }
    $state.TreeClosureConfirmed=$writerContext.Closed
    if($writerContext.Lease){
        [AppDomain]::CurrentDomain.SetData(('IW7.ModelWriter.Quarantine.'+$writerContext.Lease.Token),
            [pscustomobject]@{Context=$writerContext;ContextVariable=$originalContextVariable;Guards=$writerContext.Guards;State=$state;Plan=$plan})
    }
    $state|ConvertTo-Json -Depth 16|Set-Content -LiteralPath (Join-Path $prepared 'writer-native-run.json')
}
if($failure){throw $failure}
if(!$state.LeaseReleased -or !$writerContext.Closed -or $writerContext.Lease -or $writerContext.Guards.Count){throw 'Original writer context has not fully closed; same host/context must be retained.'}
$provenance|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $prepared 'writer-provenance.json')
