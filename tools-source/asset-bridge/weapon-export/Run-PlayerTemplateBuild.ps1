# Specialized six/eight/ten-stage caller of existing H1 ownership and T7 artifact/link policies.
# Default reads only bounded source/metadata. No tool/game/export entry exists.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
function Read-PlayerSource([string]$Path,[string]$SHA256,[long]$Bytes=-1,[Collections.Generic.List[object]]$KeepGuards=$null) {
    if([IO.Path]::GetExtension($Path).ToLowerInvariant() -cnotin @('.json','.py','.ps1','.cs','.hpp','.cpp','.inc','.rsp','.h','.hh','.inl','.vcxproj','.txt')){throw 'Source/metadata suffix required before filesystem IO.'}
    if($SHA256 -cnotmatch '^[0-9a-f]{64}$' -or ![IO.Path]::IsPathFullyQualified($Path)){throw 'Exact source binding required.'}
    for($part=$Path;$part;$part=[IO.Path]::GetDirectoryName($part)){
        if((Get-Item -LiteralPath $part).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Linked source ancestry refused.'}
    }
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read')
    try{
        if($stream.Length -gt 2MB -or ($Bytes -ge 0 -and $stream.Length -ne $Bytes)){throw 'Source size differs.'}
        $buffer=[byte[]]::new(2MB+1);$used=0
        do{$count=$stream.Read($buffer,$used,$buffer.Length-$used);$used+=$count}while($count -gt 0 -and $used -lt $buffer.Length)
        if($used -gt 2MB){throw 'Source grew above cap before hash/decode.'}
        $raw=[byte[]]::new($used);[Array]::Copy($buffer,$raw,$used)
        if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant() -cne $SHA256){throw 'Source hash differs.'}
        $decoded=[Text.Encoding]::UTF8.GetString($raw)
        if($null -ne $KeepGuards){$stream.Position=0;$KeepGuards.Add($stream);$stream=$null}
        $decoded
    }finally{if($null -ne $stream){$stream.Dispose()}}
}
function Get-PlayerDefinitionResponse([string]$Prepared,[string]$Run){
    $stage=Join-Path $Run 'definition-compile'
    '/nologo /std:c++17 /EHsc /MT /DNDEBUG /W4 /WX /Zi /Od /Y- /I"'+$Prepared+'" /FI"'+(Join-Path $Prepared 'native_definition_fixture_binding.hpp')+
        '" /Fo"'+(Join-Path $stage 'definition.obj')+'" /Fe"'+(Join-Path $stage 'definition.exe')+'" /Fd"'+(Join-Path $stage 'compile.pdb')+
        '" /sourceDependencies "'+(Join-Path $stage 'dependencies.json')+'" "'+(Join-Path $Prepared 'test_definition_readset.cpp')+
        '" /link /INCREMENTAL:NO /DEBUG /PDB:"'+(Join-Path $stage 'definition.pdb')+'"'+"`n"
}
function Assert-PlayerDefinitionFixture($Plan){
    if(!$Plan.PSObject.Properties['DefinitionFixture'] -or $Plan.DefinitionFixture.Schema -cne 'iw7.player-definition-fixture-source/1' -or
        $Plan.NativeSourcePin -cne 'fab935826c898806855376662a8a03317b3ad8f1'){throw 'Exact real definition fixture Source contract required.'}
    $contract=$Plan.DefinitionFixture
    if(!$Plan.PSObject.Properties['CandidateBytes'] -or !$Plan.PSObject.Properties['CandidateSHA256'] -or
        $null -ne $Plan.CandidateBytes -or $null -ne $Plan.CandidateSHA256){throw 'Future neutral candidate bytes/hash must remain null.'}
    $expected=@{
        'test_definition_readset.cpp'='e003afa43e469ffb651f047135c596d0710dca75b81290d2717759dc4aa65542'
        'native_definition_access.hpp'='92eb62fd94a18397ea09de034330009aaa17d16abaf037d98e041412f4ce1890'
        'native_definition_readset.hpp'='eb6957a20506e87f75f056a040c8213d979fbd64a79765700593e9f78ff6bcb6'
        'native_definition_fields.inc'='302e324b98175981ba8ae3e071a23e125ed83353d8319ca60a9c0390f47db7e3'
        'native_definition_gate.hpp'='314667bfc966bd38ba8040a9a3b12f7cef513819659ce170f05547bd0b0e409f'
    }
    if($contract.Files -isnot [array] -or $contract.Files.Count -ne $expected.Count){throw 'All five real readset fixture Source files required.'}
    foreach($name in $expected.Keys){
        $path=Join-Path $Plan.PreparedRoot $name
        $pins=@($contract.Files|Where-Object {$_.Path -is [string] -and $_.Path -ceq $path})
        $prepared=@($Plan.PreparedBindings|Where-Object Path -CEQ $path)
        if($pins.Count -ne 1 -or $prepared.Count -ne 1 -or $pins[0].SHA256 -cne $prepared[0].SHA256 -or $pins[0].Bytes -ne $prepared[0].Bytes){throw 'Unique prepared fixture Source binding required.'}
        $text=Read-PlayerSource $pins[0].Path $pins[0].SHA256 $pins[0].Bytes
        $raw=[Text.Encoding]::UTF8.GetBytes($text.Replace("`r`n","`n"))
        if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant() -cne $expected[$name]){throw 'Real pinned 100-check fixture/readset required; metadata stubs refused.'}
    }
    # The native declaration is an EXPECTED retained input here. Do not open,
    # stat or hash it in DEFAULT. Its actual read remains behind admission.
    $native=$contract.NativeHeader
    if($native.Path -isnot [string] -or ![IO.Path]::IsPathFullyQualified($native.Path) -or $native.Path -match '["\x00-\x1f]' -or
        ($native.Bytes -isnot [int] -and $native.Bytes -isnot [long]) -or $native.Bytes -ne 354227 -or
        $native.SHA256 -isnot [string] -or $native.SHA256 -cne 'adb62e481a533d27f97829e64d9038b13c5e9cd88e6b4aee8cac339b9492921a' -or
        $native.Path.Replace('\','/') -cnotmatch '/src/zonetool/zonetool/iw7/structs\.hpp$'){throw 'Exact declared native structs input required.'}
    $retained=@($Plan.RetainedInputPins|Where-Object {[IO.Path]::GetFullPath($_.Path) -ieq [IO.Path]::GetFullPath($native.Path)})
    if($retained.Count -ne 1 -or $retained[0].Bytes -ne $native.Bytes -or $retained[0].SHA256 -cne $native.SHA256){throw 'Native fixture header must be the original retained input declaration.'}
    $bindingPath=Join-Path $Plan.PreparedRoot 'native_definition_fixture_binding.hpp'
    $binding=@($Plan.PreparedBindings|Where-Object Path -CEQ $bindingPath)
    $response=@($Plan.PreparedBindings|Where-Object Path -CEQ (Join-Path $Plan.PreparedRoot 'definition.rsp'))
    if($binding.Count -ne 1 -or $response.Count -ne 1){throw 'Pinned forced-include binding and definition response required.'}
    $expectedBinding="#pragma once`n#define IW7_NATIVE_STRUCTS_HEADER `""+$native.Path.Replace('\','/')+"`"`n"
    if((Read-PlayerSource $binding[0].Path $binding[0].SHA256 $binding[0].Bytes).Replace("`r`n","`n") -cne $expectedBinding -or
        (Read-PlayerSource $response[0].Path $response[0].SHA256 $response[0].Bytes).Replace("`r`n","`n") -cne (Get-PlayerDefinitionResponse $Plan.PreparedRoot $Plan.RunRoot)){
        throw 'Exact real fixture100 source/forced include/compiler response required.'
    }
    foreach($name in @($expected.Keys)+@('native_definition_fixture_binding.hpp')){
        $path=Join-Path $Plan.PreparedRoot $name
        if(@($Plan.OwnDirectIncludeCoverage|Where-Object {$_.Path -ceq $path -and $_.Pinned -is [bool] -and $_.Pinned}).Count -ne 1){throw 'Exact guarded fixture Source include coverage required.'}
    }
}
$plan=Read-PlayerSource $PlanPath $PlanSHA256 | ConvertFrom-Json -Depth 30
if(!$plan.PSObject.Properties['RunnerBinding'] -or $plan.RunnerBinding.Path -cne $PSCommandPath){throw 'Exact specialized runner binding required.'}
$null=Read-PlayerSource $plan.RunnerBinding.Path $plan.RunnerBinding.SHA256 $plan.RunnerBinding.Bytes
if($plan.Schema -cne 'iw7.player-template-cohort-source/1' -or $plan.Ready -or $plan.CandidateExecuted -or
   $plan.WeaponReady -or $plan.PhysicsQualified -or $plan.PAPTransactionQualified -or
   $plan.RetainedObjects -ne 412 -or $plan.LinkedObjectCount -ne 413){throw 'Exact unqualified source cohort required.'}
$names=@('name-compile','name-test','argv-compile','argv-test','iw7','link')
$primaryFixture=($null -ne $plan.PSObject.Properties['PrimaryGuardFixture'])
$pairCLI=($null -ne $plan.PSObject.Properties['PairProfileCLI'])
$definitionCLI=($null -ne $plan.PSObject.Properties['PairDefinitionsCLI'])
if($pairCLI -and ($plan.PairProfileCLI -isnot [bool] -or !$plan.PairProfileCLI -or !$primaryFixture)){throw 'Explicit pair-profile CLI requires the primary fixture profile.'}
if($definitionCLI -and ($plan.PairDefinitionsCLI -isnot [bool] -or !$plan.PairDefinitionsCLI -or !$pairCLI -or !$primaryFixture)){throw 'Explicit neutral definition CLI requires both existing fixture profiles.'}
$argvChecks=if($definitionCLI){28}elseif($pairCLI){18}else{10}
if($pairCLI -and ($plan.Stages[3].ExpectedChecks -isnot [int] -and $plan.Stages[3].ExpectedChecks -isnot [long])){throw 'Scalar integer pair argv fixture count required.'}
if($primaryFixture){
    if($plan.PrimaryGuardFixture -isnot [bool] -or !$plan.PrimaryGuardFixture){throw 'Explicit true primary-guard fixture opt-in required.'}
    $names=@('name-compile','name-test','argv-compile','argv-test','primary-compile','primary-test','iw7','link')
}
if($definitionCLI){$names=@($names[0..5])+@('definition-compile','definition-test')+@($names[6..7])}
if((@($plan.Stages.Name)-join '|') -cne ($names-join '|') -or $plan.Stages[1].ExpectedChecks -ne 8 -or $plan.Stages[3].ExpectedChecks -ne $argvChecks -or
   ($primaryFixture -and (($plan.Stages[5].ExpectedChecks -isnot [int] -and $plan.Stages[5].ExpectedChecks -isnot [long]) -or $plan.Stages[5].ExpectedChecks -ne 36)) -or
   ($definitionCLI -and (($plan.Stages[7].ExpectedChecks -isnot [int] -and $plan.Stages[7].ExpectedChecks -isnot [long]) -or $plan.Stages[7].ExpectedChecks -ne 100))){throw 'Fixed source-selected 8+10-or-18-or-28/36/100 stage sequence required.'}
if($plan.GroupDeadlineSeconds -ne 600 -or $plan.OutputLimitBytes -ne 268435456 -or $plan.MetadataReserveBytes -ne 1048576){throw 'Fixed cohort deadline/output reserve required.'}
$kinds=@('Compile','Probe','Compile','Probe','Compile','Link')
$artifacts=@('name.obj|name.exe|name.pdb|compile.pdb|dependencies.json','','argv.obj|argv.exe|argv.pdb|compile.pdb|dependencies.json','','iw7-player-cli.obj|compile.pdb|dependencies.json','zonetool-iw7-player.exe|zonetool-iw7-player.pdb|zonetool-iw7-player.lib|zonetool-iw7-player.exp')
if($primaryFixture){
    $kinds=@('Compile','Probe','Compile','Probe','Compile','Probe','Compile','Link')
    $artifacts=@($artifacts[0..3])+@('primary.obj|primary.exe|primary.pdb|compile.pdb|dependencies.json','')+@($artifacts[4..5])
}
if($definitionCLI){
    $kinds=@($kinds[0..5])+@('Compile','Probe')+@($kinds[6..7])
    $artifacts=@($artifacts[0..5])+@('definition.obj|definition.exe|definition.pdb|compile.pdb|dependencies.json','')+@($artifacts[6..7])
}
for($index=0;$index -lt $names.Count;$index++){
    $stage=$plan.Stages[$index];$probe=$kinds[$index] -ceq 'Probe'
    if((($primaryFixture -and $index -in @(4,5)) -or ($definitionCLI -and $index -in @(6,7))) -and ($stage.Name -isnot [string] -or $stage.Stage -isnot [string] -or $stage.Image -isnot [string] -or
       $stage.Arguments -isnot [array] -or $stage.Artifacts -isnot [array] -or ($probe -and $stage.ExpectedStdout -isnot [string]))){throw 'Scalar exact primary fixture stage required.'}
    if($stage.Stage -cne $kinds[$index] -or $stage.DeadlineSeconds -ne $(if($probe){15}else{120}) -or
       (@($stage.Artifacts)-join '|') -cne $artifacts[$index]){throw 'Fixed cohort phase/artifacts required.'}
    if($probe){
        $fixture=if($index -eq 1){'name'}elseif($index -eq 3){'argv'}elseif($index -eq 5){'primary'}else{'definition'}
        $expected=if($index -eq 1){"IW7_PLAYER_TEMPLATE_NAME_CHECKS=8`n"}elseif($index -eq 3){"IW7_PLAYER_TEMPLATE_ARGV_CHECKS=$argvChecks`n"}elseif($index -eq 5){"IW7_PLAYER_TEMPLATE_PRIMARY_CHECKS=36`n"}else{"IW7_PLAYER_DEFINITION_READSET_CHECKS=100`n"}
        if($stage.Image -cne (Join-Path (Join-Path $plan.RunRoot "$fixture-compile") "$fixture.exe") -or @($stage.Arguments).Count -ne 0 -or
           $stage.ExpectedStdout -cne $expected){throw 'Fixed cohort probe image/marker required.'}
    }else{
        $rsp=if($index -eq 0){'name'}elseif($index -eq 2){'argv'}elseif($primaryFixture -and $index -eq 4){'primary'}elseif($definitionCLI -and $index -eq 6){'definition'}else{$stage.Name}
        $image=if($stage.Name -ceq 'link'){Join-Path (Split-Path $plan.Compiler -Parent) 'link.exe'}else{$plan.Compiler}
        if($stage.Image -cne $image -or @($stage.Arguments).Count -ne 1 -or $stage.Arguments[0] -cne ('@'+(Join-Path $plan.PreparedRoot "$rsp.rsp"))){throw 'Fixed cohort compiler/link response required.'}
    }
}
if(!$plan.PSObject.Properties['OwnDirectIncludeCoverage'] -or @($plan.OwnDirectIncludeCoverage).Count -lt 1 -or
   @($plan.OwnDirectIncludeCoverage|Where-Object {-not $_.Pinned}).Count -gt 0 -or !$plan.RequireActualDependenciesWithinGuardedSet){throw 'Own IW7 source coverage and future exact dependency guard required.'}
$primaryModule=$false
$pairModule=$false
$definitionModule=$false
foreach($pin in @($plan.SourceBindings)+@($plan.PreparedBindings)){
    $text=Read-PlayerSource $pin.Path $pin.SHA256 $pin.Bytes
    if($pin.Path -ceq (Join-Path $plan.PreparedRoot 'src/zonetool/zonetool/iw7/zonetool.cpp')){
        $primaryModule=$text.Contains('IW7_PLAYER_TEMPLATE_PRIMARY_REFUSAL schema=1') -and $text.Contains('first_failure(reader)')
        $pairModule=$text.Contains('IW7_PLAYER_PAIR_PROFILE donor=cp_zmb') -and $text.Contains('iw7_player_template_cli::pair_selected(args)')
        $definitionModule=$text.Contains('IW7_PLAYER_PAIR_DEFINITIONS donor=cp_zmb') -and $text.Contains('iw7_player_template_cli::definitions_selected(args)') -and $text.Contains('player_definition_readset::with_pair(')
    }
}
if($primaryFixture -ne $primaryModule){throw 'Exact primary module/fixture profile pairing required.'}
if($pairCLI -ne $pairModule){throw 'Exact pair profile CLI/18-check fixture pairing required.'}
if($definitionCLI -ne $definitionModule){throw 'Exact neutral definition CLI/28-argv/100-readset fixture pairing required.'}
if($definitionCLI){Assert-PlayerDefinitionFixture $plan}
$providers=$plan.Providers
$providerPins=@(foreach($name in 'Core','CompilerCore','ObserverSource','CompilerPolicySource','Scheduler','Profile'){
    $pin=@($plan.ParentBindings|Where-Object {$_.Path -ieq $providers.$name -and $_.IsText})
    if($pin.Count -ne 1){throw 'One pinned existing source provider required.'}
    $null=Read-PlayerSource $pin[0].Path $pin[0].SHA256 $pin[0].Bytes;$pin[0]
})
if(Test-Path -LiteralPath $plan.RunRoot){throw 'Fresh owned runtime output required.'}
if(!$Run){
    [ordered]@{Schema='iw7.player-template-build-default/1';PlanSHA256=$PlanSHA256;Stages=$names.Count;NameChecksAuthored=8;ArgvChecksAuthored=$argvChecks;PrimaryChecksAuthored=$(if($primaryFixture){36}else{0});DefinitionChecksAuthored=$(if($definitionCLI){100}else{0});
        DefinitionFixtureSourceVerified=$definitionCLI;ExpectedNoEffects=$true;CandidateBytes=$null;CandidateSHA256=$null;
        NativeTypesLoaded=$false;NativeInputsHashed=$false;RunRootCreated=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json
    return
}
# The physical NoExit/dot host is checked before imports, admission or native IO.
$hostArgs=[Environment]::GetCommandLineArgs()
$commandIndex=[Array]::IndexOf($hostArgs,'-Command')
if('-NoExit' -cnotin $hostArgs -or $commandIndex -lt 0 -or $commandIndex+1 -ge $hostArgs.Length -or
   $hostArgs[$commandIndex+1] -notmatch '^\s*\.\s+' -or $MyInvocation.InvocationName -cne '.'){
    throw 'Fresh physical NoExit host with dot invocation required.'
}
$physical=Get-CimInstance Win32_Process -Filter "ProcessId=$PID"
if(!$physical -or !$physical.ExecutablePath -or !$physical.CreationDate -or $physical.CommandLine -notmatch '(?i)-NoExit\b'){
    throw 'Actual original host identity/NoExit unavailable.'
}
if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7.H1Diagnostics.JobMembers' -as [type])){throw 'Fresh host required.'}
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards}
$state=[ordered]@{Schema='iw7.player-template-build/1';PlanSHA256=$PlanSHA256;Status='Pending';Stages=[Collections.Generic.List[object]]::new();
    MaxObservedOutputBytes=0L;NativeInputsReverified=$false;MeasuredReadback=$false;FinalReadback=$false;LeaseReleased=$false;GuardsDisposed=$false;CanExit=$false;Ready=$false;
    Host=[ordered]@{PID=$PID;Image=$physical.ExecutablePath;CreatedUtc=$physical.CreationDate.ToUniversalTime().ToString('o');NoExit=$true;Dot=$true}}
$global:IW7PlayerTemplateBuild=[pscustomobject]@{Context=$context;State=$state;Plan=$plan;Guards=$guards}
$failure=$null;$created=$false
try{
    # Reverify and retain the SAME read/shareRead streams before source imports,
    # scheduler effects or admission. The bounded source reader is unchanged
    # except for transferring its verified stream to the original guard list.
    foreach($pin in @($plan.SourceBindings)+@($plan.PreparedBindings)+$providerPins+@($plan.RunnerBinding)){
        $null=Read-PlayerSource $pin.Path $pin.SHA256 $pin.Bytes $guards
    }
    . $providers.Core
    . $providers.Scheduler
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Build -PhysicalBytes 4GB -CommitBytes 6GB -Owner $(if($definitionCLI){'IW7 one-TU neutral pair definitions and 8+28+36+100 fixtures'}elseif($pairCLI){'IW7 one-TU pair profile CLI and 8+18+36 fixtures'}elseif($primaryFixture){'IW7 one-TU player template CLI and 8+10+36 fixtures'}else{'IW7 one-TU player template CLI and 8+10 fixtures'})
    $state.LeaseToken=$context.Lease.Token;$script:T7GroupStarted=Get-H1Clock
    # The source guards acquired before imports remain held through release.
    . $providers.CompilerCore
    . $providers.CompilerPolicySource
    . $providers.Profile
    foreach($pin in $plan.RetainedInputPins){Open-T7Pin $pin $context}
    foreach($pin in @($plan.ParentBindings|Where-Object {-not $_.IsText})){Open-T7Pin $pin $context}
    $assembly=@($plan.ParentBindings|Where-Object Path -IEQ $plan.JobAssembly)
    if($assembly.Count -ne 1){throw 'Exact original-job assembly binding required.'}
    Open-T7Pin $assembly[0] $context
    [Reflection.Assembly]::LoadFrom($plan.JobAssembly)|Out-Null
    Add-Type -LiteralPath $providers.ObserverSource
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$created=$true
    # H1 compiler consumers use the existing provider fields; no API is changed.
    $plan|Add-Member NoteProperty ObserverSource $providers.ObserverSource -Force
    $plan|Add-Member NoteProperty CompilerPolicySource $providers.CompilerPolicySource -Force
    $plan|Add-Member NoteProperty Bindings (@($plan.ParentBindings)+@($plan.SourceBindings)+@($plan.PreparedBindings)) -Force
    $plan|Add-Member NoteProperty Inputs @($plan.RetainedInputPins) -Force
    foreach($stage in $plan.Stages){
        if(!$context.Closed){throw 'Previous original job must be closed.'}
        # A failed new factory cannot inherit a prior closed owner's evidence.
        $context.Owner=$null
        $script:T7CurrentStage=$stage;$stageRoot=Join-Path $plan.RunRoot $stage.Name
        [IO.Directory]::CreateDirectory($stageRoot)|Out-Null
        $current=[ordered]@{Name=$stage.Name;Stage=$stage.Stage;PlanSHA256=$PlanSHA256;DeadlineSeconds=$stage.DeadlineSeconds;TreeClosureConfirmed=$false;
            MaxObservedOutputBytes=$state.MaxObservedOutputBytes;CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
        $state.Stages.Add($current)
        $image=if($stage.Stage -ceq 'Probe'){
            $compile=@($state.Stages|Where-Object Name -CEQ ($stage.Name.Replace('-test','-compile')))[0]
            @($compile.Artifacts|Where-Object Path -IEQ $stage.Image)[0]
        }else{@($plan.Bindings|Where-Object Path -IEQ $stage.Image)[0]}
        if(!$image){throw 'One original stage image pin required.'}
        $start=New-T7Start $plan $stage $stageRoot
        Invoke-T7OwnedStage $plan $current $context $start $image.SHA256 $stageRoot (Get-H1Clock)
        $current.Artifacts=@(Get-H1CompilerArtifacts $plan $context)
        if($stage.Stage -ceq 'Compile'){Assert-T7Dependencies $plan $stageRoot}
        if($stage.Stage -ceq 'Probe'){
            $stdout=Join-Path $stageRoot 'stdout.log';$stderr=Join-Path $stageRoot 'stderr.log'
            if((Get-Item -LiteralPath $stdout).Length -gt 128 -or (Get-Item -LiteralPath $stderr).Length -ne 0 -or
               [IO.File]::ReadAllText($stdout).Replace("`r`n","`n") -cne $stage.ExpectedStdout){throw 'Exact requested native fixture evidence required.'}
            $current.Checks=$stage.ExpectedChecks
        }
        $state.MaxObservedOutputBytes=[math]::Max($state.MaxObservedOutputBytes,$current.MaxObservedOutputBytes)
    }
    foreach($pin in $plan.RetainedInputPins){Open-T7Pin $pin $context}
    foreach($pin in @($plan.SourceBindings)+@($plan.PreparedBindings)+$providerPins){
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
        $null=Read-PlayerSource $pin.Path $pin.SHA256 $pin.Bytes
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    }
    $state.NativeInputsReverified=$true;$state.Status='MeasuredPassed'
}catch{$failure=$_;$state.Status='Failed';$state.Error=$_.Exception.Message}
finally{
    if(!$context.Closed -and $context.Owner){try{$context.Owner.StopAndConfirm(5000);$context.Closed=$context.Owner.Closed}catch{$state.ClosureError=$_.Exception.Message}}
    if($created -and $context.Closed -and $context.Lease){
        try{
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            $measured=Join-Path $plan.RunRoot 'measured-before-release.json'
            $raw=[Text.UTF8Encoding]::new($false).GetBytes(($state|ConvertTo-Json -Depth 20)+"`n")
            if($raw.Length -gt $plan.MetadataReserveBytes -or (Measure-H1Output $plan.RunRoot)+$raw.Length -gt $plan.OutputLimitBytes){throw 'Measured receipt exceeds reserved total output.'}
            $stream=[IO.File]::Open($measured,'CreateNew','Write','Read')
            try{$stream.Write($raw);$stream.Flush($true)}finally{$stream.Dispose()}
            $hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            $null=Read-PlayerSource $measured $hash $raw.Length
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            $state.MeasuredReadback=$true
            # This verified closure tuple exists while the exact guards and lease
            # are still retained. Failed publication/readback cannot release them.
            $before=[ordered]@{Schema='iw7.player-template-build-before-release/1';PlanSHA256=$PlanSHA256;MeasuredSHA256=$hash;
                Host=$state.Host;Status=$state.Status;OriginalRootAndJobClosed=$true;LeaseToken=$context.Lease.Token;
                GuardsHeld=$guards.Count;CandidateExecuted=$false;Ready=$false}
            $beforeFile=Join-Path $plan.RunRoot 'closure-before-release.json'
            $beforeBytes=[Text.UTF8Encoding]::new($false).GetBytes(($before|ConvertTo-Json -Depth 10)+"`n")
            if((Measure-H1Output $plan.RunRoot)+$beforeBytes.Length -gt $plan.OutputLimitBytes){throw 'Closure output budget exceeded before release.'}
            $stream=[IO.File]::Open($beforeFile,'CreateNew','Write','Read')
            try{$stream.Write($beforeBytes);$stream.Flush($true)}finally{$stream.Dispose()}
            $beforeHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($beforeBytes)).ToLowerInvariant()
            $null=Read-PlayerSource $beforeFile $beforeHash $beforeBytes.Length
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            Exit-IW7ResourceLease -Token $context.Lease.Token;$context.Lease=$null;$state.LeaseReleased=$true
            foreach($guard in $guards){$guard.Dispose()};$guards.Clear();$state.GuardsDisposed=$true
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            $closure=[ordered]@{Schema='iw7.player-template-build-closure/1';PlanSHA256=$PlanSHA256;MeasuredSHA256=$hash;
                BeforeReleaseSHA256=$beforeHash;Host=$state.Host;Status='ClosedReleasedPendingPostflight';PostReadbackDeadlineRequired=$true;
                OriginalRootAndJobClosed=$true;LeaseReleased=$true;GuardsDisposed=$true;CandidateExecuted=$false;Ready=$false}
            $final=Join-Path $plan.RunRoot 'final-closure.json';$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($closure|ConvertTo-Json -Depth 10)+"`n")
            if($raw.Length+$beforeBytes.Length+$bytes.Length -gt $plan.MetadataReserveBytes -or
               (Measure-H1Output $plan.RunRoot)+$bytes.Length -gt $plan.OutputLimitBytes){throw 'Final closure exceeds reserved output.'}
            $stream=[IO.File]::Open($final,'CreateNew','Write','Read')
            try{$stream.Write($bytes);$stream.Flush($true)}finally{$stream.Dispose()}
            $finalHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            $null=Read-PlayerSource $final $finalHash $bytes.Length
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            $state.Status=if($failure){'FailedClosed'}else{'Passed'}
            $state.FinalReadback=$true;$state.CanExit=$true
        }catch{$state.FinalizationError=$_.Exception.Message;if(!$failure){$failure=$_}}
    }
    if(!$state.CanExit){
        $state.Status=if($context.Closed -and $state.LeaseReleased){'ClosedFinalizationIncomplete'}else{'UnknownRetained'}
        $state.CanExit=$false
    }
    $state|ConvertTo-Json -Depth 20
}
if($failure){throw $failure}
