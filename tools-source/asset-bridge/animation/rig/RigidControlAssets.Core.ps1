# Narrow consumer of the existing job, phase, resource and FF transaction primitives.
# Importing this file defines functions only; no native type or process is created.
function Get-RCAInventory {
    @('material,,mopw/character_park_clown_zombie_shoes',
      'xmodelsurfs,paris_doom_skin_two_bone_first_a_lod0','xmodelsurfs,paris_doom_skin_two_bone_second_a_lod0',
      'xmodel,paris_doom_skin_two_bone_first_a','xmodel,paris_doom_skin_two_bone_second_a',
      'rawfile,sdk_original_rig_rigid_control')
}
function Get-RCANativePairs {
    foreach($profile in 'first','second'){
        foreach($pair in @(@('xmodel',"paris_doom_skin_two_bone_${profile}_a.xmb"),@('xsurface',"paris_doom_skin_two_bone_${profile}_a_lod0.xsb"))){
            [pscustomobject]@{Profile=$profile;Relative=($pair -join '/')}
        }
    }
}
function Assert-RCAPlan($Plan) {
    if($Plan.Schema -cne 'iw7.original-rig-rigid-assets-source-plan/1' -or $Plan.Variant -cne 'RigidControl' -or
       $Plan.Zone -cne 'sdk_original_rig_rigid_control' -or $Plan.RunRoot -cnotmatch '^C:\\IW7-Work\\rca-\d{8}-[a-z0-9]{1,16}$'){
        throw 'Exact finite rigid source plan and short owned root required.'
    }
    foreach($name in 'ExecutorPrepared','EmitExecuted','FFBuilt','ReadbackVerified','GPUVerified','PixelsVerified','Ready'){
        if($Plan.$name -isnot [bool] -or $Plan.$name){throw 'Unexecuted source plan required.'}
    }
    if($null -ne $Plan.Fastfile -or $Plan.StockInputsExpected -ne 72 -or $Plan.ExpectedStagedInputs -ne 78 -or
       (@($Plan.ExpectedInventory) -join "`n") -cne ((Get-RCAInventory) -join "`n")){throw 'Exact six assets and 78 staged inputs required.'}
    $r=$Plan.ExpectedRigid
    foreach($pair in @(@('Bones',1),@('Roots',1),@('ClientBones',0),@('Surfaces',1),@('LODs',1),@('Vertices',8),@('Triangles',6),
                     @('SurfaceFlags',130),@('ModelFlags',524288),@('RigidLists',1),@('BlendBytes',0))){
        if($r.($pair[0]) -isnot [int] -and $r.($pair[0]) -isnot [long]){throw 'Integer rigid counts required.'}
        if($r.($pair[0]) -ne $pair[1]){throw 'Exact one-root rigid geometry required.'}
    }
    if((@($r.BlendCounts) -join ',') -cne '0,0,0,0,0,0,0,0' -or
       (@($r.PartBits) -join ',') -cne '2147483648,0,0,0,0,0,0,0'){throw 'No blends and exact root mask required.'}
    $writerPins=@('44fddfb2eb7b1bf5933f306cfb4cc8e89f8f2eb2b822422f6dfd48852390c6c7','954f487b0a07b5b7bdf4fdb2942b042764081cd2a61d285fe10de047ddd48ad4')
    if(@($Plan.Writers).Count -ne 2 -or @($Plan.Phases).Count -ne 7 -or
       $Plan.CPPClosureSHA256 -ine '92a1148ac17fe2f70b32c989c3b60126cce1724999bd46befe2b87a147f7d6ae' -or
       $Plan.Candidate.SHA256 -ine 'e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04' -or
       $Plan.Candidate.ArtifactSHA256 -ine 'f0d4d7db132d51c789a999e33ab0ce905b2df749db453029f91356b9aa2e2165'){throw 'Closed fixed writers and reviewed FF candidate required.'}
    foreach($pair in @(@('baseline','4cf67ebe1645c6c0761b9a24cb4e4630edee9c5d737742c704d624fe60cb3850'),
                       @('binding','aa8b4d6f560a78bb0fbd012319ebb43675edd3df5ef9660f6e2bb16d07013a4c'),
                       @('reviewed','9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4'))){
        if($Plan.StockReceipts.($pair[0]+'_sha256') -ine $pair[1]){throw 'Original stock receipt pins required without live stock reads.'}
    }
    $expected=@()
    for($i=0;$i -lt 2;$i++){
        $profile=@('first','second')[$i];$w=$Plan.Writers[$i]
        if($w.Profile -cne $profile -or $w.Files[0].Bytes -ne 131584 -or $w.Files[0].SHA256 -ine $writerPins[$i]){throw 'Exact ordered writer pins required.'}
        $expected+=,[ordered]@{Id="emit-$profile";Group='Emit';Timeout=30;Cwd=(Join-Path $Plan.RunRoot 'emit-work');
            Command=@($w.Files[0].Path,(Join-Path $Plan.RunRoot "native/$profile"));Hash=$writerPins[$i]}
    }
    foreach($verb in 'build','verify','dump'){
        $expected+=,[ordered]@{Id=$verb;Group='FF';Timeout=240;Cwd=(Join-Path $Plan.RunRoot 'ff-work');
            Command=@((Join-Path $Plan.RunRoot 'ff-work/zonetool.exe'),'-headless','-unbuffered-io','-strict-content-sources',"-${verb}zone",$Plan.Zone);Hash=$Plan.Candidate.SHA256}
    }
    for($i=0;$i -lt 2;$i++){
        $profile=@('first','second')[$i]
        $expected+=,[ordered]@{Id="read-ff-$profile";Group='FF';Timeout=30;Cwd=(Join-Path $Plan.RunRoot 'ff-work');
            Command=@($Plan.Writers[$i].Files[0].Path,'--verify-existing',(Join-Path $Plan.RunRoot "redump/$profile"));Hash=$writerPins[$i]}
    }
    for($i=0;$i -lt 7;$i++){
        $p=$Plan.Phases[$i];$e=$expected[$i]
        if($p.Id -cne $e.Id -or $p.Group -cne $e.Group -or $p.Timeout -ne $e.Timeout -or $p.Cwd -ine $e.Cwd -or
           $p.ExecutableSHA256 -ine $e.Hash -or (@($p.Command) -join "`0") -ine (@($e.Command) -join "`0")){
            throw 'Only the seven literal bounded phase vectors are permitted.'
        }
        if($i -ge 5 -and $p.PhaseAdapterId -cne 'read-ff'){throw 'Existing read-ff adapter required.'}
    }
    foreach($p in @($Plan.CPPClosure,$Plan.Candidate.Path)+@($Plan.Writers|ForEach-Object {$_.Files[0].Path})){
        if(![IO.Path]::IsPathFullyQualified($p) -or $p -match '(^|[\\/])\.\.([\\/]|$)'){throw 'Absolute canonical inputs required.'}
    }
}
function Assert-RCARoundtrip($Result) {
    if($Result.schema -cne 'iw7.original-rig-rigid-control-roundtrip/1'){throw 'Fixed rigid writer roundtrip receipt required.'}
    foreach($pair in @(@('vertices',8),@('triangles',6),@('bones',1),@('surfaces',1),@('lods',1),@('source_units_to_engine',1),
                       @('shadow_cutoff_lod',6),@('collision_lod',255),@('lod0_dist',1000000))){
        if($Result.($pair[0]) -isnot [int] -and $Result.($pair[0]) -isnot [long]){throw 'Exact integer rigid receipt fields required.'}
        if($Result.($pair[0]) -ne $pair[1]){throw 'Rigid receipt geometry differs.'}
    }
    foreach($name in 'has_lods','geometry_roundtrip_verified'){
        if($Result.$name -isnot [bool] -or !$Result.$name){throw 'Full writer readback required.'}
    }
    foreach($name in 'iw7_normal_encoding_verified','ff_built','pixels_verified','ready'){
        if($Result.$name -isnot [bool] -or $Result.$name){throw 'Writer data cannot assert FF, GPU or pixels acceptance.'}
    }
    if($Result.radius_engine_units -isnot [double] -or [math]::Abs($Result.radius_engine_units-[math]::Sqrt(272)) -gt 0.00001){throw 'Exact original radius required.'}
}
function Assert-RCAInventory([string]$Log) {
    if($Log.Length -gt 2MB -or !$Log.Contains('Loading zone "sdk_original_rig_rigid_control"') -or
       $Log -match 'could not be found|Could not find referenced|\[ ERROR \]|\[ FATAL \]'){throw 'Bounded resolved rigid inventory required.'}
    $rows=@(foreach($line in $Log -split '\r?\n'|Where-Object {$_ -match 'Loading asset '}){
        if($line -cnotmatch 'Loading asset "([^"\r\n]+)" of type ([a-z0-9]+)\.$'){throw 'Malformed inventory callback.'}
        $Matches[2]+','+$Matches[1]
    })
    if($rows.Count -ne 6 -or @($rows|Sort-Object -Unique).Count -ne 6 -or @((Get-RCAInventory)|Where-Object {$_ -cnotin $rows}).Count){
        throw 'Exact six-asset rigid inventory required; no xanim or NCS.'
    }
    $rows
}
function New-RCAPhaseSpec($Context,$Phase) {
    $system=[Environment]::GetFolderPath('Windows');$tmp=Join-Path $Phase.Cwd 'tmp'
    [ordered]@{schema='iw7.rig-chain-phase-spec/1';phase=$(if($Phase.PhaseAdapterId){$Phase.PhaseAdapterId}else{$Phase.Id});
        exe=$Phase.Command[0];sha256=$Phase.ExecutableSHA256;arguments=@($Phase.Command|Select-Object -Skip 1);cwd=$Phase.Cwd;
        logs=(Join-Path $Context.Plan.RunRoot ('logs/'+$Phase.Id));timeout=$Phase.Timeout;
        environment=[ordered]@{SystemRoot=$system;WINDIR=$system;PATH=(($system,(Join-Path $system 'System32')) -join ';');
            TEMP=$tmp;TMP=$tmp;INCLUDE=$Phase.Cwd;LIB=$Phase.Cwd;PYTHONNOUSERSITE='1';PYTHONDONTWRITEBYTECODE='1'}}
}
function Invoke-RCAPhase($Context,$Phase,[scriptblock]$Observe) {
    & $Observe
    $spec=New-RCAPhaseSpec $Context $Phase;$specPath=Join-Path $Context.Plan.RunRoot ($Phase.Id+'.spec.json')
    Write-RigNewJson $spec $specPath;$specHash=(Get-FileHash -LiteralPath $specPath).Hash
    Add-RigGuard $specPath $specHash $Context.Guards $Context.Baselines
    $args=@('-I','-B',(Join-Path $Context.SourcePackage 'tools-source/asset-bridge/animation/rig/rig_phase.py'),
        '--spec',$specPath,'--spec-sha256',$specHash,'--sdk-phase',(Join-Path $Context.SourcePackage 'sdk/modding/beacon_tool_phase.py'))
    $Context.Closed=$false # Factory failure remains unknown until original handle closure is proved.
    $Context.Owner=New-RigOwnedJob $Context.Python (ConvertTo-AnimationArguments $args) $Phase.Cwd
    $phaseIdentity=Get-BeaconJobIdentity $Context.Owner $Context.Python $Phase.Id
    $phaseIdentity['JobRootExitedAtClose']=$false;$phaseIdentity['SpecSHA256']=$specHash
    $Context.State.Phases+=,$phaseIdentity;Write-RigJson $Context.State $Context.StatePath
    $started=Get-RigMonotonicMs
    $Context.Owner.Resume()
    $phaseIdentity['ResourceRegistration']=Register-AnimationPhase $Context.Owner $Context.Lease.Token $Observe
    Wait-RigOwnedPhase $Context.Owner $phaseIdentity $started $Phase.Timeout {param($sample) & $Observe}
    $Context.Closed=$true
    $phaseReceipt=Read-RigPhaseResult $spec.logs $specPath $specHash $phaseIdentity $spec.phase
    Assert-RigPhaseResult $phaseReceipt $spec.phase $spec.sha256 $specHash $phaseIdentity
    $phaseIdentity['ReceiptSHA256']=(Get-FileHash -LiteralPath (Join-Path $spec.logs 'phase.json')).Hash
    $Context.Owner.Dispose();$Context.Owner=$null
    $text=[IO.File]::ReadAllText((Join-Path $spec.logs 'stdout.log'))
    if($text.Length -gt 2MB){throw 'Phase stdout exceeds bound.'}
    $text
}
function Complete-RCAGroup($Context) {
    if(!$Context.Closed -or !$Context.SourceIntact){return $false}
    if($Context.Saved){
        Restore-IW7BaseTransaction $Context.Transaction
        if(!$Context.Transaction.Restored){throw 'Group transaction restoration unconfirmed.'}
        if(@(Get-ChildItem -LiteralPath $Context.Work -Force).Count){throw 'Owned work not empty after restoration; preserve context.'}
    }elseif($Context.Work -and (Test-Path -LiteralPath $Context.Work) -and @(Get-ChildItem -LiteralPath $Context.Work -Force).Count){
        throw 'Unconfirmed transaction with output; preserve original context.'
    }
    Assert-RigBaselines $Context.Baselines -Hashes
    if($Context.Inputs.Count){Assert-ModelFFInputs $Context.Inputs $Context.Work -SourceOnly;Assert-FFStockContent $Context.Inputs}
    $Context.State.Restored=$true;$Context.State.SourceInputsUnchanged=$true
    if($Context.Lease){
        Exit-IW7ResourceLease -Token $Context.Lease.Token
        $token=$Context.Lease.Token
        if(@(Invoke-IW7ResourceLock {(Read-IW7ResourceState).Leases|Where-Object Token -EQ $token}).Count){throw 'Group lease release unconfirmed.'}
        $Context.Lease=$null;$Context.State.RetainedLeaseToken=$null;$Context.State.LeaseReleased=$true
    }
    return $true
}
function Add-RCARetainedFile($Context,[string]$Source,[string]$Target,[long]$Limit) {
    Assert-RigArtifact $Source $Limit
    $hash=(Get-FileHash -LiteralPath $Source).Hash
    [IO.Directory]::CreateDirectory((Split-Path $Target))|Out-Null
    if(Test-Path -LiteralPath $Target){throw 'Retained output already exists.'}
    Copy-Item -LiteralPath $Source -Destination $Target
    Add-RigGuard $Target $hash $Context.Guards $Context.Baselines
    [ordered]@{Path=$Target;Bytes=(Get-Item -LiteralPath $Target).Length;SHA256=$hash}
}
