param([Parameter(Mandatory)][string]$PackageRoot,[Parameter(Mandatory)][string]$PreparedRoot,
      [Parameter(Mandatory)][string]$ToolSource,[Parameter(Mandatory)][string]$RunRoot,
      [Parameter(Mandatory)][string]$NativeJobAssembly,[string]$NativePolicyRevision='2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1',
      [string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop'
$identity=Get-Content -LiteralPath "$PackageRoot/source-workspace.json" -Raw|ConvertFrom-Json
if($NativePolicyRevision -cne '2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1' -or $identity.revisions.'iw7-mod-components' -cne $NativePolicyRevision){throw 'Exact current TelemetryOnly native policy package required'}
if((Get-Item -LiteralPath "$PreparedRoot/arena-writer-source.json").Length -gt 64KB){throw 'Bounded material-bound writer source required'}
$binding=Get-Content -LiteralPath "$PreparedRoot/arena-writer-source.json" -Raw|ConvertFrom-Json
if($binding.schema -cne 'iw7.original-arena-writer-source/1' -or $binding.material_reference -cne 'mopw/character_park_clown_zombie_shoes' -or $binding.compiled -or $binding.ff_built -or $binding.runtime_verified){throw 'Fresh measured material-bound arena source required'}
if((git -C $ToolSource rev-parse HEAD) -cne 'fab935826c898806855376662a8a03317b3ad8f1'){throw 'Pinned ZoneTool interface source required'}
if(Test-Path -LiteralPath $RunRoot){throw 'Fresh native output required'}
$guards=[Collections.Generic.List[IDisposable]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards}
$entries=[Collections.Generic.List[object]]::new()
$state=$null;$current=$null;$failed=$null
function Pin($Path,$Expected=''){
    $f=[IO.File]::Open($Path,'Open','Read','Read');$guards.Add($f)
    # Known executables stay deferred until the existing Run admission below.
    # Source files always rehash; binary metadata/digests keep Plan stable.
    $sha=if($Expected){$Expected}else{[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($f)).ToLowerInvariant()}
    if($Expected -and $sha -cne $Expected){throw 'Input pin changed'}
    $pin=[pscustomobject]@{Path=[IO.Path]::GetFullPath($Path);Bytes=$f.Length;SHA256=$sha}
    $entries.Add($pin);$pin
}
try {
    $null=Pin $PSCommandPath
    foreach($file in 'ops/Base-Client.Core.ps1','sdk/modding/BeaconFF.Core.ps1','tools-source/asset-bridge/surfaces/MaterialV2.Compiler.ps1',
                    'tools-source/asset-bridge/world/ObserverHarness.Core.ps1','tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1',
                    'tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1','tools-source/asset-bridge/t7-iw7/T7Build.Profile.ps1',
                    'tools-source/asset-bridge/world/ObserverStages.Profile.ps1') {
        $null=Pin "$PackageRoot/$file";. "$PackageRoot/$file"
    }
    foreach($file in 'source-workspace.json','ops/Resource-Scheduler.Core.ps1','ops/Resource-Memory.ps1',
                    'ops/Resource-RecorderOwnedProcess.Core.ps1','ops/native/ResourceMemory.cs',
                    'tools-source/asset-bridge/h1-fixture/H1Native.JobMembers.cs',
                    'tools-source/asset-bridge/animation/Probe-NativeJob.cs',
                    'tools-source/asset-bridge/world/original-arena/readback.py','tools-source/asset-bridge/h1-fixture/inspect_fixture.py'){
        $null=Pin "$PackageRoot/$file"
    }
    foreach($name in 'arena_writer.cpp','probe_geometry.hpp','geometry.source.json','arena-writer-source.json'){
        $pin=Pin "$PreparedRoot/$name"
        if($name -ne 'arena-writer-source.json' -and $binding.source_files.$name -cne $pin.SHA256){throw 'Measured writer source changed'}
    }
    if((git -C $ToolSource status --porcelain --untracked-files=all)){throw 'Changed retained tool sources must be preserved'}
    foreach($source in 'utils/io/assetmanager.hpp','utils/io/filesystem.hpp','utils/memory.hpp','iw7/structs.hpp','iw7/assets/xmodel.cpp','iw7/assets/xsurface.cpp'){$null=Pin "$ToolSource/src/zonetool/zonetool/$source"}
    $vc='C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207'
    $sdk='C:/Program Files (x86)/Windows Kits/10';$version='10.0.26100.0'
    $cl=[IO.Path]::GetFullPath("$vc/bin/Hostx64/x64/cl.exe")
    $link=[IO.Path]::GetFullPath("$vc/bin/Hostx64/x64/link.exe")
    $python=(Get-Command python -CommandType Application|Select-Object -First 1).Source
    $policy=Get-MaterialV2CompilerPolicy $cl
    $clPin=Pin $cl $policy.CompilerSHA256.ToLowerInvariant()
    $linkPin=Pin $link 'a364af801a8539e4324d9489313dbf001d959128451fc99a27b24676bbac058f'
    $null=Pin $policy.Telemetry $policy.TelemetrySHA256.ToLowerInvariant()
    $pythonPin=Pin $python '31073dad142bc7f3374e3122aa668270052c9ad37d0aaab803ae73f184c3a43b'
    $dll=Pin $NativeJobAssembly '5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8'
    $obj=Join-Path $RunRoot 'compile/arena.obj';$exe=Join-Path $RunRoot 'link/arena-writer.exe'
    $includes=@("$vc/include","$sdk/Include/$version/ucrt","$sdk/Include/$version/shared","$sdk/Include/$version/um","$ToolSource/src/zonetool",$PreparedRoot)
    $compile=@('/nologo','/c','/std:c++20','/EHsc','/MD','/W4','/bigobj','/D_CRT_SECURE_NO_WARNINGS')+
        @($includes|ForEach-Object{'/I'+[IO.Path]::GetFullPath($_)})+@(('/Fo'+$obj),"$PreparedRoot/arena_writer.cpp")
    $stages=@(
        [pscustomobject]@{Name='compile';Stage='Compile';Image=$cl;Arguments=$compile;DeadlineSeconds=90;Artifacts=@('arena.obj')},
        [pscustomobject]@{Name='link';Stage='Link';Image=$link;Arguments=@('/NOLOGO','/INCREMENTAL:NO',('/OUT:'+$exe),$obj,"/LIBPATH:$vc/lib/x64","/LIBPATH:$sdk/Lib/$version/ucrt/x64","/LIBPATH:$sdk/Lib/$version/um/x64",'user32.lib','kernel32.lib');DeadlineSeconds=90;Artifacts=@('arena-writer.exe')},
        [pscustomobject]@{Name='fixture';Stage='Fixture';Image=$exe;Arguments=@((Join-Path $RunRoot 'artifacts'));DeadlineSeconds=10;Artifacts=@()},
        [pscustomobject]@{Name='check';Stage='Check';Image=$python;Arguments=@('-I','-S','-B',"$PackageRoot/tools-source/asset-bridge/world/original-arena/readback.py",'--artifacts',(Join-Path $RunRoot 'artifacts'),'--geometry-source',"$PreparedRoot/geometry.source.json",'--expected-material','mopw/character_park_clown_zombie_shoes');DeadlineSeconds=5;Artifacts=@()}
    )
    $envs=[ordered]@{}
    foreach($key in 'SystemRoot','windir','SystemDrive','USERPROFILE','LOCALAPPDATA','APPDATA'){$envs[$key]=[Environment]::GetEnvironmentVariable($key)}
    $envs.PATH=(Split-Path $cl -Parent)+';'+(Split-Path $python -Parent)+';'+[Environment]::SystemDirectory
    $plan=[pscustomobject]@{Schema='iw7.original-arena-native-plan/1';RunRoot=$RunRoot;Compiler=$cl;Bindings=$entries.ToArray();Stages=$stages;
        Environment=[pscustomobject]$envs;OutputLimitBytes=64MB;MetadataReserveBytes=1MB;GroupDeadlineSeconds=120;
        OutputContract=[pscustomobject]@{StreamThresholdBytes=2MB;StrictWriteCap=$false;Enforcement='Sampled'};
        SourcePackageRevisions=$identity.revisions;CreatorSourceRevision='f4e5e45df043f65811098063307d8065b3a33d30';MaterialReference=$binding.material_reference;
        PhysicalEstimate=2GB;CommitEstimate=3GB;PhysicsSerialized=$false;FFBuilt=$false;GameProcess=$false;ToolchainFullyHermetic=$false}
    foreach($pin in $entries){Assert-H1Path $pin.Path}
    $actualPlanSHA=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes(($plan|ConvertTo-Json -Depth 20)))).ToLowerInvariant()
    if(!$Run){[ordered]@{PlanSHA256=$actualPlanSHA;Plan=$plan}|ConvertTo-Json -Depth 22;return}
    if($PlanSHA256 -cne $actualPlanSHA){throw 'Exact reviewed local recipe Plan hash required'}
    if('IW7.AnimationProbe.NativeJob' -as [type]){throw 'Fresh persistent PS7 host required'}
    . "$PackageRoot/ops/Resource-Scheduler.Core.ps1"
    $context.Lease=Enter-IW7ResourceLease -Scope $RunRoot -Kind Build -PhysicalBytes 2GB -CommitBytes 3GB -Owner 'Original arena standalone model writer/readback'
    $script:WorldGroupStarted=Get-H1Clock
    [IO.Directory]::CreateDirectory($RunRoot)|Out-Null
    $state=[ordered]@{Schema='iw7.original-arena-native-run/1';Status='Preparing';Plan=$plan;Stages=[Collections.Generic.List[object]]::new();
        NativeHarnessPassed=$false;PhysicsSerialized=$false;FFBuilt=$false;RuntimeVerified=$false;SourceHashesUnchanged=$false;JobClosureVerified=$true;
        LeaseReleased=$false;LeaseReleaseState='NotAttempted';RetainedLeaseToken=$context.Lease.Token;FinalBytes=$null}
    # Opaque cl/link/vctip/Python/NativeJob hashes are read only while the one
    # admitted Build reservation is held, before loading or starting any owner.
    foreach($pin in $entries){Assert-BeaconHash $pin.Path $pin.SHA256}
    [Reflection.Assembly]::LoadFrom($NativeJobAssembly)|Out-Null
    Add-Type -LiteralPath "$PackageRoot/tools-source/asset-bridge/h1-fixture/H1Native.JobMembers.cs"
    $buildStarted=Get-H1Clock
    foreach($stage in $stages){
        $script:WorldCurrentStage=$stage;$dir=Join-Path $RunRoot $stage.Name;[IO.Directory]::CreateDirectory($dir)|Out-Null
        $current=[ordered]@{Name=$stage.Name;Stage=$stage.Stage;PlanSHA256=$actualPlanSHA;DeadlineSeconds=$stage.DeadlineSeconds;
            MaxObservedOutputBytes=0L;MaxObservedStreamBytes=0L;TerminationRequested=$false;CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
        $state.Stages.Add($current)
        $image=if($stage.Stage -ceq 'Fixture'){$state.Stages[1].Artifacts[0]}else{@($entries|Where-Object Path -EQ $stage.Image)[0]}
        $start=New-T7Start $plan $stage $dir
        $began=if($stage.Stage -in 'Compile','Link'){$buildStarted}else{Get-H1Clock}
        Invoke-WorldStage $plan $current $context $start $image.SHA256 $dir $began
        $current.Artifacts=@(Get-H1CompilerArtifacts $plan $context)
        foreach($p in $current.Artifacts){$entries.Add($p)}
        if($stage.Stage -ceq 'Fixture'){
            foreach($asset in 'xmodel/paris_original_arena.xmb','xsurface/paris_original_arena_lod0.xsb'){
                $path=Join-Path (Join-Path $RunRoot 'artifacts') $asset
                if((Get-Item -LiteralPath $path).Length -gt 8192){throw 'Original arena artifact exceeds reader bound'}
                $null=Pin $path
            }
        }
        if($stage.Stage -ceq 'Check'){
            if((Get-Item -LiteralPath "$dir/stderr.log").Length){throw 'Independent reader stderr must be empty'}
            $checked=Read-H1SmallJson "$dir/stdout.log" 4KB
            if($checked.schema -cne 'iw7.original-arena-independent-readback/1' -or !$checked.geometry_roundtrip_verified -or
                $checked.vertices -ne 168 -or $checked.triangles -ne 84 -or !$checked.material_bound -or $checked.physics_serialized -or $checked.runtime_verified){throw 'Original material-bound geometry readback did not qualify'}
            $state.Checked=$checked
        }
    }
    $state.NativeHarnessPassed=$true;$state.Status='SyntheticHarnessPassed'
}catch{$failed=$_;if($state){$state.Status='Failed';$state.Failure=$_.Exception.Message}}
finally{
    if(!$context.Closed -and $current -and !$current.TerminationRequested){Stop-WorldStageOnFailure $context $current}
    if($state){
        $state.JobClosureVerified=$context.Closed
        try{foreach($pin in $entries){if((Get-FileHash -LiteralPath $pin.Path).Hash -ine $pin.SHA256){throw 'Bound input changed'}};$state.SourceHashesUnchanged=$true}catch{if(!$failed){$failed=$_}}
        try{Complete-WorldObserverReservation $RunRoot $state $context.Lease $guards -BeforeReleaseCheck {if(!$failed){Assert-H1Deadline $script:WorldGroupStarted 120}}}catch{if(!$failed){$failed=$_}}
    }
    if(!$context.Lease -or ($state -and $state.LeaseReleased)){foreach($guard in $guards){$guard.Dispose()}}
    else{[AppDomain]::CurrentDomain.SetData('IW7.WorldHarness.Quarantine.'+$context.Lease.Token,$context)}
}
if($failed){throw $failed}
$state|ConvertTo-Json -Depth 20
