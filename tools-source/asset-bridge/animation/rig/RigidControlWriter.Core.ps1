# Narrow original-ribbon compiler adapter. All process, resource, identity,
# telemetry and transaction implementations remain the existing providers.
function Get-RCWProviderPins {
    [ordered]@{
        'ops/Base-Client.Core.ps1'='e504a87334fae8f294458c72d7980c3e9b00d3c6549b969d1dfb41f26ca70605'
        'sdk/modding/BeaconFF.Core.ps1'='b80047875a39731ea54838459fb71e0dca580c5e42284bd2749dc4b39c3a08a8'
        'ops/hud-lab/HudFileIdentity.cs'='61255ad8bbb6b4e2437291d3083811a56c1217ab68484bb1f22a4d5148616dbd'
        'ops/Resource-Scheduler.Core.ps1'='2b2991299b0bce525bf6b39d59e4735bcd84d485e798fb29ad9b2ce09a789253'
        'ops/Resource-Memory.ps1'='6a708d2e7fa9803628bfbf5c670068d63d22a2d2cfc157994afa82d56ac9c241'
        'ops/Resource-RecorderOwnedProcess.Core.ps1'='23d6f589a6f973f6d9c56a2ff3dcb66c4df6a0aa9fe0a7125048dd9061f93c54'
        'ops/native/ResourceMemory.cs'='b159804d12ca504cd592f4cdee191a9b68353e9e0117f9045a28a522b25692e9'
        'tools-source/asset-bridge/model/BuildJob.cs'='f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387'
        'tools-source/asset-bridge/animation/AnimationFF.Core.ps1'='2cc1cf0536af0885fceec8de536c2d44402371c0bd889ed3110865225bd7db97'
        'tools-source/asset-bridge/animation/rig/Rig.Core.ps1'='a69b49fd11119e0ce6808f2bb408b0297d5fbe60e1f9778c625179e64cce7eeb'
        'tools-source/asset-bridge/animation/rig/Rig.Compiler.ps1'='4a0bf1bef388f4bd09df535a6f1a87581683c2914d3ca0675a786a260b30e3ac'
        'tools-source/asset-bridge/animation/rig/Rig.JobMembers.cs'='5a02254764277b62f752792f1ec4f5b93b85237b171a3381a78d58f6af190e91'
        'tools-source/asset-bridge/animation/rig/rig_phase.py'='bcc545543f0c330c28f755ff164054595551d0ac85ff6d85c48b271a20bd8861'
        'sdk/modding/beacon_tool_phase.py'='a2ab493cf551a43eea3797e5e8437e41aa8f0246d770838956d8984b68c4701d'
    }
}
function Assert-RCWPlan($Plan) {
    $fields=@('schema','source_package','source_package_manifest_sha256','prepared_source','prepared_manifest_sha256',
        'native_source','native_source_pin','run_root','python','python_sha256','compiler','compiler_sha256',
        'sdk_root','sdk_version','core_sha256','operator_sha256','root_go','compiled','native_writer_executed','ff_built','ready')
    if(@($Plan.PSObject.Properties).Count -ne $fields.Count -or @($fields|Where-Object {$_ -cnotin $Plan.PSObject.Properties.Name}).Count){throw 'Exact rigid writer operator plan fields required.'}
    if($Plan.schema -cne 'iw7.original-rig-rigid-writer-operator-plan/1' -or
       $Plan.native_source_pin -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
       $Plan.compiler_sha256 -cne 'fe251ef50a1545b1b0835ee17b1e785459712b38d79e45b5c1d3d28970a36619' -or
       $Plan.python_sha256 -cne '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a' -or
       $Plan.prepared_manifest_sha256 -cne '5811ef3ebcd5948eb394ab4a720ec37de4f9a902788774da10d47b8d59a55b5b' -or
       $Plan.sdk_version -cne '10.0.26100.0'){throw 'Exact original rigid source, Python and compiler pins required.'}
    foreach($name in 'root_go','compiled','native_writer_executed','ff_built','ready'){
        if($Plan.$name -isnot [bool] -or $Plan.$name){throw 'Unexecuted source plan required; Run needs separate Root GO.'}
    }
    foreach($name in $fields|Where-Object {$_ -like '*sha256'}){
        if($Plan.$name -isnot [string] -or $Plan.$name -cnotmatch '^[a-f0-9]{64}$'){throw 'Exact lowercase SHA256 required.'}
    }
    foreach($name in 'source_package','prepared_source','native_source','run_root','python','compiler','sdk_root'){
        $value=$Plan.$name
        if($value -isnot [string] -or ![IO.Path]::IsPathFullyQualified($value) -or $value -match '(^|[\\/])\.\.([\\/]|$)'){throw 'Absolute canonical operator path required.'}
        $null=Resolve-IW7BasePath (Split-Path $value) (Split-Path $value -Leaf)
    }
    if($Plan.run_root -cnotmatch '^C:\\IW7-Work\\rcw-\d{8}-[a-z0-9]{1,16}$' -or $Plan.run_root.Length -gt 64){throw 'Fresh short owned rcw run root required.'}
    if(Test-Path -LiteralPath $Plan.run_root){throw 'Existing operator run root refused.'}
    if([IO.Path]::GetFileName($Plan.compiler) -ine 'cl.exe' -or [IO.Path]::GetFileName($Plan.python) -ine 'python.exe'){throw 'Exact compiler and Python executable names required.'}
}
function Get-RCWCommands($Plan) {
    $vc=([IO.FileInfo]$Plan.compiler).Directory.Parent.Parent.Parent.FullName
    $includes=@((Join-Path $vc 'include'))+@('ucrt','shared','um','winrt'|ForEach-Object {Join-Path $Plan.sdk_root ('Include/'+$Plan.sdk_version+'/'+$_)})
    $libs=@((Join-Path $vc 'lib/x64'))+@('ucrt','um'|ForEach-Object {Join-Path $Plan.sdk_root ('Lib/'+$Plan.sdk_version+'/'+$_+'/x64')})
    $env=[ordered]@{SystemRoot=[Environment]::GetFolderPath('Windows');WINDIR=[Environment]::GetFolderPath('Windows');
        PATH=((Split-Path $Plan.compiler),(Join-Path ([Environment]::GetFolderPath('Windows')) 'System32'),[Environment]::GetFolderPath('Windows') -join ';');
        TEMP=(Join-Path $Plan.run_root 'build/tmp');TMP=(Join-Path $Plan.run_root 'build/tmp');
        INCLUDE=($includes -join ';');LIB=($libs -join ';');PYTHONNOUSERSITE='1';PYTHONDONTWRITEBYTECODE='1'}
    $phases=@(foreach($profile in 'first','second'){
        $cwd=Join-Path $Plan.run_root ('build/'+$profile);$src=Join-Path $Plan.run_root 'source'
        $compilerArguments=@('/nologo','/std:c++20','/EHsc','/MD','/W4','/WX','/bigobj','/X','/D_CRT_SECURE_NO_WARNINGS',
            ('/I'+(Join-Path $Plan.native_source 'src/zonetool')),('/I'+(Join-Path $src $profile)),('/I'+$src),
            (Join-Path $src 'writer.cpp'),('/Fo'+(Join-Path $cwd 'writer.obj')),('/Fe'+(Join-Path $cwd 'rigid-writer.exe')),('/Fd'+(Join-Path $cwd 'writer.pdb')))
        $compilerArguments+=@($includes|ForEach-Object {'/I'+$_})+@('/link','/INCREMENTAL:NO')+@($libs|ForEach-Object {'/LIBPATH:'+$_})+@('kernel32.lib','user32.lib')
        [pscustomobject]@{Profile=$profile;Spec=[ordered]@{schema='iw7.rig-chain-phase-spec/1';phase='compile';exe=$Plan.compiler;sha256=$Plan.compiler_sha256;
            arguments=$compilerArguments;cwd=$cwd;logs=(Join-Path $Plan.run_root ('logs/compile-'+$profile));timeout=120;environment=$env}}
    })
    [pscustomobject]@{Phases=$phases;FreezeRoots=@((Split-Path $Plan.compiler),(Join-Path $vc 'include'),(Join-Path $vc 'lib/x64'),
        (Join-Path $Plan.sdk_root ('Include/'+$Plan.sdk_version)),(Join-Path $Plan.sdk_root ('Lib/'+$Plan.sdk_version)),(Join-Path $Plan.native_source 'src/zonetool'))}
}
function Invoke-RCWPhase($Context,$Phase,[string]$SpecPath,[string]$SpecSHA256,[scriptblock]$Observe) {
    $phaseArguments=@('-I','-B',(Join-Path $Context.Plan.source_package 'tools-source/asset-bridge/animation/rig/rig_phase.py'),
        '--spec',$SpecPath,'--spec-sha256',$SpecSHA256,'--sdk-phase',(Join-Path $Context.Plan.source_package 'sdk/modding/beacon_tool_phase.py'))
    $Context.Closed=$false # A failed factory is not proof of a closed native object.
    $Context.Owner=New-RigOwnedJob $Context.Plan.python (ConvertTo-AnimationArguments $phaseArguments) $Phase.Spec.cwd
    $identity=Get-BeaconJobIdentity $Context.Owner $Context.Plan.python ('compile-'+$Phase.Profile)
    $identity['JobRootExitedAtClose']=$false;$identity['SpecSHA256']=$SpecSHA256
    $evidence=[ordered]@{CompilerIdentity=$null;LastObservation=$null;Completed=$false}
    $identity['CompilerClosure']=$evidence;$Context.State.Phases+=,$identity
    & $Context.Save
    $started=Get-RigMonotonicMs
    $poll={
        & $Observe
        $members=Get-RigOriginalJobMembers $Context.Owner
        Update-RigCompilerWitness $evidence $members $identity.PID $Context.Policy
    }
    $Context.Owner.Resume()
    $identity['ResourceRegistration']=Register-AnimationPhase $Context.Owner $Context.Lease.Token $poll
    & $Context.Save
    Wait-RigOwnedPhase $Context.Owner $identity $started 120 {
        param($sample)
        & $poll
        if($sample.RootExited -and $sample.ActiveProcesses -gt 0){
            $receipt=Read-RigPhaseResult $Phase.Spec.logs $SpecPath $SpecSHA256 $identity compile -RootExitCode $sample.RootExitCode
            $null=Complete-RigCompilerTelemetry $Context.Owner $sample $evidence.LastObservation $receipt $evidence $Context.Policy
        }
    }
    $Context.Closed=$true
    $receipt=Read-RigPhaseResult $Phase.Spec.logs $SpecPath $SpecSHA256 $identity compile
    Assert-RigPhaseResult $receipt compile $Context.Plan.compiler_sha256 $SpecSHA256 $identity
    $identity['ReceiptSHA256']=(Get-FileHash -LiteralPath (Join-Path $Phase.Spec.logs 'phase.json')).Hash
    $Context.Owner.Dispose();$Context.Owner=$null
}
function Complete-RCWContext($Context) {
    if(!$Context.Closed -or !$Context.SourceIntact){return $false}
    if($Context.Saved){
        Restore-IW7BaseTransaction $Context.Transaction
        if(!$Context.Transaction.Restored -or @(Get-ChildItem -LiteralPath (Join-Path $Context.Plan.run_root 'build') -Force).Count){throw 'Build restoration incomplete; keep guards and lease.'}
    }elseif($Context.Created -and (Test-Path -LiteralPath (Join-Path $Context.Plan.run_root 'build')) -and
        @(Get-ChildItem -LiteralPath (Join-Path $Context.Plan.run_root 'build') -Force).Count){throw 'Unconfirmed transaction with build content; retain original context.'}
    $Context.State.Restored=$true
    if($Context.Lease){
        Exit-IW7ResourceLease -Token $Context.Lease.Token
        $token=$Context.Lease.Token
        $remaining=@(Invoke-IW7ResourceLock { (Read-IW7ResourceState).Leases|Where-Object Token -EQ $token })
        if($remaining.Count){throw 'Lease release is not confirmed.'}
        $Context.Lease=$null;$Context.State.RetainedLeaseToken=$null;$Context.State.LeaseReleased=$true
    }
    foreach($guard in $Context.Guards){$guard.Dispose()};$Context.Guards.Clear()
    return $true
}
