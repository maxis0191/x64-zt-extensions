param(
    [Parameter(Mandatory)][string]$SourcePackage,
    [string]$PlanPath,
    [string]$PlanSHA256
)
# Source, original-owner mocks and tiny synthetic transaction files only.
# No native types, real admission, writers, FF, stock or game are executed/read.
$ErrorActionPreference='Stop'
. "$PSScriptRoot/RigidControlAssets.Core.ps1"
. "$PSScriptRoot/Rig.Core.ps1"
. (Join-Path $SourcePackage 'ops/Base-Client.Core.ps1')
. (Join-Path $SourcePackage 'sdk/modding/BeaconFF.Core.ps1')
$checks=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuse([scriptblock]$Body){$failed=$false;try{& $Body|Out-Null}catch{$failed=$true};Check $failed 'Unsafe fixture accepted'}
function Clone($Value){$Value|ConvertTo-Json -Depth 30|ConvertFrom-Json}
if([bool]$PlanPath -ne [bool]$PlanSHA256){throw 'Optional live source plan requires both path and SHA256.'}
# Embedded literal metadata fixture: no dependence on local runtime receipts,
# prepared source, executable availability or a package manifest for CI units.
$plan=@'
{
  "Schema":"iw7.original-rig-rigid-assets-source-plan/1",
  "Variant":"RigidControl",
  "Zone":"sdk_original_rig_rigid_control",
  "RunRoot":"C:\\IW7-Work\\rca-20261014-a",
  "CPPClosure":"C:\\rigid-assets-fixture-missing\\cpp-closure.json",
  "CPPClosureSHA256":"92a1148ac17fe2f70b32c989c3b60126cce1724999bd46befe2b87a147f7d6ae",
  "Writers":[
    {"Profile":"first","Files":[{"Path":"C:\\rigid-assets-fixture-missing\\first\\rigid-writer.exe","Bytes":131584,"SHA256":"44fddfb2eb7b1bf5933f306cfb4cc8e89f8f2eb2b822422f6dfd48852390c6c7"}]},
    {"Profile":"second","Files":[{"Path":"C:\\rigid-assets-fixture-missing\\second\\rigid-writer.exe","Bytes":131584,"SHA256":"954f487b0a07b5b7bdf4fdb2942b042764081cd2a61d285fe10de047ddd48ad4"}]}
  ],
  "Phases":[
    {"Id":"emit-first","Group":"Emit","Timeout":30,"Cwd":"C:\\IW7-Work\\rca-20261014-a\\emit-work","ExecutableSHA256":"44fddfb2eb7b1bf5933f306cfb4cc8e89f8f2eb2b822422f6dfd48852390c6c7","Command":["C:\\rigid-assets-fixture-missing\\first\\rigid-writer.exe","C:\\IW7-Work\\rca-20261014-a\\native\\first"]},
    {"Id":"emit-second","Group":"Emit","Timeout":30,"Cwd":"C:\\IW7-Work\\rca-20261014-a\\emit-work","ExecutableSHA256":"954f487b0a07b5b7bdf4fdb2942b042764081cd2a61d285fe10de047ddd48ad4","Command":["C:\\rigid-assets-fixture-missing\\second\\rigid-writer.exe","C:\\IW7-Work\\rca-20261014-a\\native\\second"]},
    {"Id":"build","Group":"FF","Timeout":240,"Cwd":"C:\\IW7-Work\\rca-20261014-a\\ff-work","ExecutableSHA256":"e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04","Command":["C:\\IW7-Work\\rca-20261014-a\\ff-work\\zonetool.exe","-headless","-unbuffered-io","-strict-content-sources","-buildzone","sdk_original_rig_rigid_control"]},
    {"Id":"verify","Group":"FF","Timeout":240,"Cwd":"C:\\IW7-Work\\rca-20261014-a\\ff-work","ExecutableSHA256":"e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04","Command":["C:\\IW7-Work\\rca-20261014-a\\ff-work\\zonetool.exe","-headless","-unbuffered-io","-strict-content-sources","-verifyzone","sdk_original_rig_rigid_control"]},
    {"Id":"dump","Group":"FF","Timeout":240,"Cwd":"C:\\IW7-Work\\rca-20261014-a\\ff-work","ExecutableSHA256":"e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04","Command":["C:\\IW7-Work\\rca-20261014-a\\ff-work\\zonetool.exe","-headless","-unbuffered-io","-strict-content-sources","-dumpzone","sdk_original_rig_rigid_control"]},
    {"Id":"read-ff-first","PhaseAdapterId":"read-ff","Group":"FF","Timeout":30,"Cwd":"C:\\IW7-Work\\rca-20261014-a\\ff-work","ExecutableSHA256":"44fddfb2eb7b1bf5933f306cfb4cc8e89f8f2eb2b822422f6dfd48852390c6c7","Command":["C:\\rigid-assets-fixture-missing\\first\\rigid-writer.exe","--verify-existing","C:\\IW7-Work\\rca-20261014-a\\redump\\first"]},
    {"Id":"read-ff-second","PhaseAdapterId":"read-ff","Group":"FF","Timeout":30,"Cwd":"C:\\IW7-Work\\rca-20261014-a\\ff-work","ExecutableSHA256":"954f487b0a07b5b7bdf4fdb2942b042764081cd2a61d285fe10de047ddd48ad4","Command":["C:\\rigid-assets-fixture-missing\\second\\rigid-writer.exe","--verify-existing","C:\\IW7-Work\\rca-20261014-a\\redump\\second"]}
  ],
  "StockReceipts":{
    "baseline_sha256":"4cf67ebe1645c6c0761b9a24cb4e4630edee9c5d737742c704d624fe60cb3850",
    "binding_sha256":"aa8b4d6f560a78bb0fbd012319ebb43675edd3df5ef9660f6e2bb16d07013a4c",
    "reviewed_sha256":"9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4"
  },
  "Candidate":{"Path":"C:\\rigid-assets-fixture-missing\\zonetool.exe","SHA256":"e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04","ArtifactSHA256":"f0d4d7db132d51c789a999e33ab0ce905b2df749db453029f91356b9aa2e2165"},
  "StockInputsExpected":72,
  "ExpectedStagedInputs":78,
  "ExpectedInventory":["material,,mopw/character_park_clown_zombie_shoes","xmodelsurfs,paris_doom_skin_two_bone_first_a_lod0","xmodelsurfs,paris_doom_skin_two_bone_second_a_lod0","xmodel,paris_doom_skin_two_bone_first_a","xmodel,paris_doom_skin_two_bone_second_a","rawfile,sdk_original_rig_rigid_control"],
  "ExpectedRigid":{"Bones":1,"Roots":1,"ClientBones":0,"Surfaces":1,"LODs":1,"Vertices":8,"Triangles":6,"SurfaceFlags":130,"ModelFlags":524288,"RigidLists":1,"BlendBytes":0,"BlendCounts":[0,0,0,0,0,0,0,0],"PartBits":[2147483648,0,0,0,0,0,0,0]},
  "ExecutorPrepared":false,"EmitExecuted":false,"FFBuilt":false,"Fastfile":null,"ReadbackVerified":false,"GPUVerified":false,"PixelsVerified":false,"Ready":false
}
'@|ConvertFrom-Json
if($PlanPath){$plan=[IO.File]::ReadAllText($PlanPath)|ConvertFrom-Json}
Assert-RCAPlan $plan;Check $true 'Rigid source plan accepted'
foreach($mutation in @(
    {param($p)$p.ExpectedRigid.Bones=2}, {param($p)$p.ExpectedRigid.BlendBytes=48},
    {param($p)$p.ExpectedRigid.PartBits[0]=3221225472}, {param($p)$p.ExpectedRigid.SurfaceFlags=514},
    {param($p)$p.ExpectedInventory+=,'xanim,unexpected'}, {param($p)$p.Phases[0].Command+=,'first'},
    {param($p)$p.Phases[3].Command[4]='-buildzone'}, {param($p)$p.Phases[5].Command[1]='--anything'},
    {param($p)$p.Phases[6].ExecutableSHA256=('0'*64)}, {param($p)$p.Ready=$true},
    {param($p)$p.Fastfile='invented'}, {param($p)$p.RunRoot='C:\IW7-Work\rca-20261014-a\..\escape'}
)){$bad=Clone $plan;& $mutation $bad;Refuse {Assert-RCAPlan $bad}}
$validRoundtrip=[pscustomobject]@{schema='iw7.original-rig-rigid-control-roundtrip/1';vertices=8;triangles=6;bones=1;surfaces=1;lods=1;
    radius_engine_units=[math]::Sqrt(272);source_units_to_engine=1;shadow_cutoff_lod=6;collision_lod=255;lod0_dist=1000000;
    has_lods=$true;geometry_roundtrip_verified=$true;iw7_normal_encoding_verified=$false;ff_built=$false;pixels_verified=$false;ready=$false}
Assert-RCARoundtrip $validRoundtrip;Check $true 'Strict roundtrip accepted'
foreach($field in 'vertices','triangles','bones','surfaces','lods','source_units_to_engine','shadow_cutoff_lod','collision_lod','lod0_dist'){
    $bad=Clone $validRoundtrip;$bad.$field=99;Refuse {Assert-RCARoundtrip $bad}
    $bad=Clone $validRoundtrip;$bad.$field=[string]$bad.$field;Refuse {Assert-RCARoundtrip $bad}
}
foreach($field in 'geometry_roundtrip_verified','has_lods','ready','ff_built','pixels_verified','iw7_normal_encoding_verified'){
    $bad=Clone $validRoundtrip;$bad.$field=!$bad.$field;Refuse {Assert-RCARoundtrip $bad}
}
$inventory='Loading zone "sdk_original_rig_rigid_control"'+"`n"+((Get-RCAInventory|ForEach-Object {
    $p=$_ -split ',',2;'Loading asset "'+$p[1]+'" of type '+$p[0]+'.'
}) -join "`n")
Check (@(Assert-RCAInventory $inventory).Count -eq 6) 'Closed six assets accepted'
foreach($extra in 'Loading asset "paris_original_probe_bend" of type xanim.','Loading asset "ncs" of type netconststrings.',
                 'Loading asset "paris_doom_skin_two_bone_first_a" of type xmodel.','[ ERROR ] unresolved'){
    Refuse {Assert-RCAInventory ($inventory+"`n"+$extra)}
}
Refuse {Assert-RCAInventory ($inventory.Replace('xmodelsurfs.','xmodel.'))}
$driver=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'Build-RigidControlAssets.ps1'))
foreach($name in 'RigidControlAssets.Core.ps1','Build-RigidControlAssets.ps1','test_rigid_control_assets.ps1'){
    $errors=$null;$tokens=$null;$null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name),[ref]$tokens,[ref]$errors)
    Check (!$errors.Count) ($name+' parse')
}
$defaultAt=$driver.IndexOf('if(!$Run)');$admissionAt=$driver.IndexOf('Enter-IW7ResourceLease')
Check ($defaultAt -gt 0 -and $defaultAt -lt $admissionAt) 'Default returns before admission'
foreach($text in 'Add-RigGuard $Python','Add-RigGuard $writer.Files[0].Path','Add-RigGuard $plan.Candidate.Path','Get-AnimationStockInputs','Assert-BeaconCandidate','Add-Type -LiteralPath'){
    Check ($driver.IndexOf($text) -gt $admissionAt) ('Opaque/native operation after admission: '+$text)
}
Check ($driver.IndexOf('SetData($contextKey,$rcaContext)') -lt $admissionAt) 'Original context before admission'
Check ($driver.IndexOf('GetCommandLineArgs()') -lt $admissionAt -and $driver.IndexOf('$RootGO -cne') -lt $admissionAt) 'Host and separate Root GO before admission'
$identityTypeAt=$driver.IndexOf("Add-Type -LiteralPath (Join-Path `$SourcePackage 'ops/hud-lab/HudFileIdentity.cs')")
$firstIdentityGuardAt=$driver.IndexOf('foreach($path in $textPins.Keys){Add-RigGuard')
Check ($identityTypeAt -gt $admissionAt -and $identityTypeAt -lt $firstIdentityGuardAt) 'Reviewed identity type loaded under admission before NTFS guard capture'
$incompleteAt=$driver.IndexOf("throw 'Group incomplete; preserve and inspect original host context.'")
$finalContextAt=$driver.IndexOf('SetData($contextKey,$null)')
$finalFFAt=$driver.LastIndexOf("if(`$Group -ceq 'FF'){")
$finalDisposeAt=$driver.IndexOf('foreach($guard in $rcaContext.Guards){$guard.Dispose()}')
Check ($finalFFAt -gt $incompleteAt -and $finalDisposeAt -gt $finalFFAt -and $finalContextAt -gt $finalDisposeAt) 'Context disposal limited to successful final FF after failure/cleanup gate; Emit retains guards'
Check ($driver.IndexOf('$rcaContext.State.ContextReleased=$true') -gt $finalDisposeAt -and
       $driver.IndexOf('$rcaContext.State.ContextReleased=$true') -lt $finalContextAt) 'Final context release recorded only after guard disposal'
if($PlanPath){
$default=& "$PSScriptRoot/Build-RigidControlAssets.ps1" -PlanPath $PlanPath -PlanSHA256 $PlanSHA256 -SourcePackage $SourcePackage -Python 'C:\rca-missing-python\python.exe'|ConvertFrom-Json
Check (!$default.NativeExecutableHashesRead -and !$default.LeaseAcquired -and !$default.NativeTypesLoaded -and !$default.FFBuilt -and !$default.Ready -and $null -eq $default.Fastfile) 'Missing EXE path source default remains inert'
Check (@($default.Phases).Count -eq 7) 'Seven fixed default vectors'
# Run only the proved host refusal; no persistent -NoExit invocation is permitted here.
if([Environment]::GetCommandLineArgs() -inotcontains '-NoExit'){
    $failure=$null
    try{& "$PSScriptRoot/Build-RigidControlAssets.ps1" -PlanPath $PlanPath -PlanSHA256 $PlanSHA256 -SourcePackage $SourcePackage -Run|Out-Null}catch{$failure=$_.Exception.Message}
    Check ($failure -like '*original bundled persistent pwsh -NoExit host before admission*') 'Ordinary-host Run is refused before admission'
}
}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('rigid-assets-source-test-'+[guid]::NewGuid().ToString('N'))
try{
    [IO.Directory]::CreateDirectory($temp)|Out-Null
    $script:events=[Collections.Generic.List[string]]::new()
    function ConvertTo-AnimationArguments($Arguments){$Arguments -join ' '}
    function Add-RigGuard($Path,$Expected,$Guards,$Baselines){$script:events.Add('guard')}
    function New-RigOwnedJob($Python,$Arguments,$Work){
        Check (!$mockContext.Closed) 'Closed=false before factory'
        Check (Test-Path -LiteralPath (Join-Path $mockContext.Plan.RunRoot 'logs') -PathType Container) 'Fresh phase parent exists before any child factory'
        $script:events.Add('factory')
        if($script:factoryFailure){throw 'Synthetic factory failure'}
        $o=[pscustomobject]@{}
        $o|Add-Member ScriptMethod Resume {$script:events.Add('resume')}
        $o|Add-Member ScriptMethod Dispose {$script:events.Add('dispose')}
        $o
    }
    function Get-BeaconJobIdentity($Owner,$Python,$Phase){$script:events.Add('identity');[ordered]@{PID=123;ExitCode=$null;JobActiveAtClose=$null}}
    function Register-AnimationPhase($Owner,$Token,$Budget){$script:events.Add('register');[ordered]@{Token=$Token}}
    function Wait-RigOwnedPhase($Owner,$Identity,$Started,$Timeout,$Poll){
        $script:events.Add('wait');& $Poll ([pscustomobject]@{RootExited=$true;ActiveProcesses=0;RootExitCode=0})
        $Identity.ExitCode=0;$Identity.JobActiveAtClose=0;$Identity.JobRootExitedAtClose=$true
    }
    function Read-RigPhaseResult($Logs,$SpecPath,$SpecHash,$Identity,$Phase){
        $script:events.Add('receipt')
        if($script:receiptFailure){throw 'Synthetic missing receipt'}
        [IO.Directory]::CreateDirectory($Logs)|Out-Null
        [IO.File]::WriteAllText((Join-Path $Logs 'phase.json'),'{}');[IO.File]::WriteAllText((Join-Path $Logs 'stdout.log'),'{}')
        [pscustomobject]@{schema='iw7.rig-chain-phase-result/1';phase=$Phase;failure=$null;executable_sha256=$mockPhase.ExecutableSHA256;
            spec_sha256=$SpecHash;log_limit_each=2MB;ownership='outer original Windows job';exit_code=0}
    }
    $mockPhase=Clone $plan.Phases[0];$mockPhase.Cwd=$temp
    function New-MockContext {
        [ordered]@{Plan=[pscustomobject]@{RunRoot=$temp};SourcePackage=$temp;Python='C:\missing\python.exe';State=[ordered]@{Phases=@()};
            StatePath=(Join-Path $temp 'state.json');Guards=[Collections.Generic.List[IDisposable]]::new();Baselines=@();Closed=$true;Owner=$null;Lease=@{Token='synthetic'}}
    }
    $mockContext=New-MockContext;$script:factoryFailure=$true;$script:receiptFailure=$false
    Refuse {Invoke-RCAPhase $mockContext $mockPhase {$script:events.Add('observe')}}
    Check (!$mockContext.Closed -and !$mockContext.Owner -and $mockContext.Lease.Token -ceq 'synthetic') 'Unknown factory keeps context lease'
    Remove-Item -LiteralPath (Join-Path $temp ($mockPhase.Id+'.spec.json'))
    $mockContext=New-MockContext;$script:factoryFailure=$false;$script:receiptFailure=$true
    Refuse {Invoke-RCAPhase $mockContext $mockPhase {$script:events.Add('observe')}}
    Check ($mockContext.Closed -and $null -ne $mockContext.Owner) 'Closed job but unverified receipt retains original object'
    Remove-Item -LiteralPath (Join-Path $temp ($mockPhase.Id+'.spec.json'))
    $script:events.Clear();$mockContext=New-MockContext;$script:receiptFailure=$false
    $null=Invoke-RCAPhase $mockContext $mockPhase {$script:events.Add('observe')}
    $trace=$script:events -join ','
    Check ($trace -match 'factory,identity,resume,register,wait,observe,receipt,dispose') 'Original identity before Resume then registration, fresh wait and receipt before Dispose'
    Check ($mockContext.Closed -and !$mockContext.Owner -and $mockContext.State.Phases[0].JobActiveAtClose -eq 0) 'Successful source mock closes original object'
    # Real existing restoration primitives on tiny synthetic transaction only.
    $work=Join-Path $temp 'work';[IO.Directory]::CreateDirectory($work)|Out-Null
    $transaction=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$work;MutableFiles=@('zone/tiny.ff');ProfileDirectory='unused';ProfileDirectories=@('zone')}) (Join-Path $temp 'backup')
    [IO.Directory]::CreateDirectory((Join-Path $work 'zone'))|Out-Null;[IO.File]::WriteAllText((Join-Path $work 'zone/tiny.ff'),'tiny synthetic')
    $close=[ordered]@{Closed=$false;SourceIntact=$true;Saved=$true;Transaction=$transaction;Work=$work;Baselines=@();Inputs=@();Lease=@{Token='synthetic'};State=[ordered]@{Restored=$false;SourceInputsUnchanged=$false;RetainedLeaseToken='synthetic';LeaseReleased=$false}}
    function Assert-RigBaselines($Baselines,[switch]$Hashes){$script:events.Add('source-proof')}
    function Exit-IW7ResourceLease($Token){$script:events.Add('release')}
    function Invoke-IW7ResourceLock($Body){if($script:releaseUnconfirmed){@{Token='synthetic'}}}
    Check (!(Complete-RCAGroup $close) -and (Test-Path -LiteralPath (Join-Path $work 'zone/tiny.ff'))) 'Unknown closure prevents restoration/release'
    $close.Closed=$true;$close.SourceIntact=$false
    Check (!(Complete-RCAGroup $close) -and !$close.State.LeaseReleased) 'Unproved source prevents restoration/release'
    $close.SourceIntact=$true;$script:releaseUnconfirmed=$true
    Refuse {Complete-RCAGroup $close}
    Check ($transaction.Restored -and $close.Lease -and !$close.State.LeaseReleased) 'Unconfirmed registry release retains lease/context'
    $script:releaseUnconfirmed=$false
    Check (Complete-RCAGroup $close) 'Synthetic restoration and confirmed release'
    Check (!$close.Lease -and $close.State.Restored -and $close.State.LeaseReleased -and @(Get-ChildItem -LiteralPath $work -Force).Count -eq 0) 'Proof precedes release and transaction restores empty work'
}finally{
    # This test created its fresh GUID root; verify containment before cleanup.
    if($temp -and [IO.Path]::GetFullPath($temp).StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()),[StringComparison]::OrdinalIgnoreCase)){
        Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
    }
}
[ordered]@{Schema='iw7.original-rig-rigid-assets-source-validation/1';Checks=$checks;Passed=$true;
    NativeTypesLoaded=$false;RealLeaseAcquired=$false;WriterExecuted=$false;FFExecuted=$false;StockRead=$false;GameExecuted=$false;RuntimeAccepted=$false}|ConvertTo-Json
