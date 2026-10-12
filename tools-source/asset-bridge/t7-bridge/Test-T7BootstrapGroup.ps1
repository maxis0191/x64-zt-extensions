# Pure shared-receipt fixtures, original tiny files, fake clock/release/providers.
param([string]$ReviewedCorePath)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
if(!$ReviewedCorePath){$ReviewedCorePath=Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1'}
if([IO.Path]::GetFileName($ReviewedCorePath) -cne 'H1Native.Core.ps1' -or (Get-Item -LiteralPath $ReviewedCorePath).Length -gt 128KB){throw 'Bounded reviewed core source required.'}
. $ReviewedCorePath
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
# Preserve parameter declarations by loading the complete declarations in script scope.
foreach($spec in @(
    @('Test-T7CatalogueBootstrap.ps1',@('Check','Refuses','Copy-Value','Get-Item','New-Fixture')),
    @('Test-T7CatalogueBootstraps.ps1',@('New-Qualified','Set-QualifiedBytes','New-InputIds')),
    @('Qualify-T7BootstrapGroup.ps1',@('Assert-QualificationPathSyntax','Open-T7QualificationText','Assert-T7QualificationGroupPlan','Save-QualificationText','Assert-QualificationPersistentHost',
        'Complete-QualificationGuards','Publish-QualificationReceipt','Wait-QualificationRetention','Assert-T7QualificationMemory','Open-T7QualificationPass','Invoke-T7QualificationInputs','Publish-T7QualificationItems')))){
    $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $spec[0]),[ref]$tokens,[ref]$errors)
    if($errors.Count){throw 'Source parse failed.'}
    foreach($name in $spec[1]){
        $fn=@($ast.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true))
        if($fn.Count -ne 1){throw ('Missing function '+$name)}
        . ([scriptblock]::Create($fn[0].Extent.Text))
    }
}
$script:checks=0;$script:provider=@{};$script:ids=@{};$script:json=@{};$script:observedId='AABBCCDD:0000000000000001'
$baseRead=${function:Read-H1SmallJson}
function Read-H1SmallJson([string]$Path,[int]$Limit=128KB){if($script:json.ContainsKey($Path)){return $script:json[$Path]}; & $baseRead $Path $Limit}
function Get-T7CatalogueFileId([string]$Path){$script:ids[$Path]}
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-group-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
function New-Shared([int]$Count=3,[int]$Existing=0){
    $f=New-Qualified $Count 'QualifiedCollectionV3';$script:json=@{}
    $groupRoot=Join-Path $root 'qualification-group'
    $shared=[pscustomobject]@{
        Script=[pscustomobject]@{Path=(Join-Path $root 'Qualify-T7BootstrapGroup.ps1');Bytes=100;SHA256=('e'*64)}
        Plan=[pscustomobject]@{Path=(Join-Path $root 'shared-plan.json');Bytes=100;SHA256=('f'*64)}
        Receipt=[pscustomobject]@{Path=(Join-Path $groupRoot 'group-receipt.json');Bytes=100;SHA256=('a'*64)}}
    $f.Plan|Add-Member NoteProperty SharedQualification $shared
    $groupPlan=[pscustomobject]@{Schema='iw7.t7-bootstrap-group-plan/1';Script=(Copy-Value $shared.Script);Inputs=@();Runner=$shared.Script.Path;
        SourceDirectory=$root;RunRoot=$groupRoot;Bindings=@();HostImage='synthetic';Main=$null;PreservedPython=$null;
        PhysicalBytes=6GB;CommitBytes=8GB;DeadlineSeconds=200;RetryAuthorized=$false}
    $group=Copy-Value $f.Receipts[$Existing];$group.Schema='iw7.t7-bootstrap-group-qualification/1';$group.ScriptSHA256=$shared.Script.SHA256
    $group|Add-Member NoteProperty GroupComplete $true;$group|Add-Member NoteProperty PlanSHA256 $shared.Plan.SHA256;$group|Add-Member NoteProperty Items @()
    for($i=$Existing;$i -lt $Count;$i++){
        $b=$f.Plan.Bootstraps[$i];$old=$b.QualificationScript.Path
        $f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $old)
        $oldReceipt=$b.QualificationReceipt.Path;$b.QualificationReceipt.Path=Join-Path $groupRoot ([IO.Path]::GetFileName($b.Path)+'.receipt.json')
        ($f.Plan.Bindings|Where-Object Path -CEQ $oldReceipt).Path=$b.QualificationReceipt.Path
        $script:provider[$b.QualificationReceipt.Path]=$script:provider[$oldReceipt]
        $b.QualificationScript=Copy-Value $shared.Script;$r=$f.Receipts[$i];$r.ScriptSHA256=$shared.Script.SHA256
        $b.SHA256=($i+1).ToString('x64');$r.SHA256=$b.SHA256
        ($f.Plan.Bindings|Where-Object Path -CEQ $b.Path).SHA256=$b.SHA256
        $r|Add-Member NoteProperty QualificationGroup ([pscustomobject]@{PlanSHA256=$shared.Plan.SHA256;InputCount=($Count-$Existing);InputIndex=($i-$Existing)})
        $m=Copy-Value $r.Input;$m|Add-Member NoteProperty Name ([IO.Path]::GetFileName($b.Path));$m|Add-Member NoteProperty FileId $b.FileId
        $groupPlan.Inputs+=@($m)
        $group.Items+=@([pscustomobject]@{Path=$b.Path;Bytes=$b.Bytes;SHA256=$b.SHA256;FileId=$b.FileId;QualificationReceipt=(Copy-Value $b.QualificationReceipt)})
        $script:json[$b.QualificationReceipt.Path]=$r
    }
    foreach($p in @($shared.Script,$shared.Plan,$shared.Receipt)){
        $pin=Copy-Value $p;$pin|Add-Member NoteProperty IsText $true;$f.Plan.Bindings+=@($pin)
        $script:provider[$pin.Path]=[pscustomobject]@{PSIsContainer=$false;Length=$pin.Bytes;Attributes='Archive'}
    }
    $script:json[$shared.Plan.Path]=$groupPlan;$script:json[$shared.Receipt.Path]=$group
    $f|Add-Member NoteProperty GroupPlan $groupPlan;$f|Add-Member NoteProperty Group $group
    $f
}
function New-GroupPlan([int]$Count=3){
    $f=New-Shared $Count
    $identity=[pscustomobject]@{PID=123;CreatedUtc='2026-10-12T00:00:00Z';Image=(Join-Path $root 'preserved.exe')}
    [pscustomobject]@{Schema='iw7.t7-bootstrap-group-plan/1';Runner=(Join-Path $PSScriptRoot 'Qualify-T7BootstrapGroup.ps1');Script=(Copy-Value $f.Plan.SharedQualification.Script);
        SourceDirectory=$root;RunRoot=(Join-Path $repo 'runtime/t7-bootstrap-group-synthetic');Inputs=$f.GroupPlan.Inputs;Bindings=@();
        HostImage=[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName;Main=[pscustomobject]@{MainBaseline='Stopped';PreservedMain=$identity};
        PreservedPython=(Copy-Value $identity);PhysicalBytes=6GB;CommitBytes=8GB;DeadlineSeconds=200;RetryAuthorized=$false}
}
$script:clock=0;$script:clockStep=0;$script:releaseFails=$false;$script:releaseDelay=0;$script:releaseCalls=0;$script:highWater=$false;$script:sleeps=0
function Get-H1Clock {$value=$script:clock;$script:clock+=$script:clockStep;$value}
function Get-IW7ResourceSnapshot {[pscustomobject]@{Synthetic=$true}}
function Test-IW7ResourceBudget($Snapshot,$Physical,$Commit){[pscustomobject]@{HighWater=$script:highWater}}
function Exit-IW7ResourceLease([string]$Token){$script:releaseCalls++;$script:clock+=$script:releaseDelay;if($script:releaseFails){throw 'Synthetic release refused.'}}
function Start-Sleep([int]$Seconds){$script:sleeps++;throw 'RetentionWitness'}
function New-GroupContext {
    [pscustomobject]@{Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token='synthetic-group'};
        Guards=[Collections.Generic.List[object]]::new();PayloadGuards=[Collections.Generic.List[IO.FileStream]]::new();Rows=[Collections.Generic.List[object]]::new()}
}
function New-GroupState {
    $f=New-Fixture;$state=[ordered]@{}
    foreach($p in $f.Receipt.PSObject.Properties){$state[$p.Name]=$p.Value}
    $state.Schema='iw7.t7-bootstrap-group-qualification/1';$state.PlanSHA256='f'*64;$state.Items=@();$state.GroupComplete=$false
    $state.LeaseToken='synthetic-group';$state.LeaseReleased=$false;$state.GuardsClosed=$false
    $state
}
try{
    foreach($shape in @(@(1,0),@(2,0),@(20,8),@(32,0))){
        $f=New-Shared $shape[0] $shape[1]
        Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
        Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipts[-1] $f.Plan.Bootstraps[-1].Path;$checks++
        Check ($f.Plan.Bindings.Count -eq 22+2*$shape[0]+$shape[1]+1+2) 'Shared exact binding count differs.'
    }
    foreach($case in 'V1','V2','absent-option','null-option','unused','false-script-hash','duplicate-receipt','duplicate-name','duplicate-id','item-size','total-size','plan-collision','receipt-collision','fake-binding'){
        $f=New-Shared
        switch($case){
            V1 {$f.Plan.BootstrapPolicy='QualifiedCollectionV1'}
            V2 {$f.Plan.BootstrapPolicy='QualifiedCollectionV2'}
            absent-option {$f.Plan.PSObject.Properties.Remove('SharedQualification')}
            null-option {$f.Plan.SharedQualification=$null}
            unused {$f.Plan.SharedQualification.Script.Path=Join-Path $root 'other/Qualify-T7BootstrapGroup.ps1'}
            false-script-hash {$f.Plan.Bootstraps[-1].QualificationScript.SHA256='0'*64}
            duplicate-receipt {$f.Plan.Bootstraps[-1].QualificationReceipt=Copy-Value $f.Plan.Bootstraps[0].QualificationReceipt}
            duplicate-name {$f.Plan.Bootstraps[-1].Path=$f.Plan.Bootstraps[0].Path;$f.Plan.Bootstraps[-1].RelativePath=$f.Plan.Bootstraps[0].RelativePath}
            duplicate-id {$f.Plan.Bootstraps[-1].FileId=$f.Plan.Bootstraps[0].FileId}
            item-size {$f.Plan.Bootstraps[-1].Bytes=512MB+1}
            total-size {$f.Plan.Bootstraps[0].Bytes=512MB;$f.Plan.Bootstraps[-1].Bytes=256MB}
            plan-collision {$f.Plan.SharedQualification.Plan.Path=$f.Plan.Bootstraps[0].QualificationReceipt.Path}
            receipt-collision {$f.Plan.SharedQualification.Receipt.Path=$f.Plan.EngineSource}
            fake-binding {($f.Plan.Bindings|Where-Object Path -CEQ $f.Plan.SharedQualification.Script.Path).SHA256='0'*64}
        }
        Refuses {Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner'}
    }
    foreach($case in 'reused-row','index','count','group-hash','plan-script','plan-name','plan-id','plan-size','plan-budget','plan-root','seal-hash','seal-id','seal-name','seal-receipt','incomplete','released','guards','failed','missing-row'){
        $f=New-Shared
        switch($case){
            reused-row {$f.Receipts[-1]=Copy-Value $f.Receipts[0]}
            index {$f.Receipts[-1].QualificationGroup.InputIndex=0}
            count {$f.Receipts[-1].QualificationGroup.InputCount=2}
            group-hash {$f.Receipts[-1].QualificationGroup.PlanSHA256='0'*64}
            plan-script {$f.GroupPlan.Script.SHA256='0'*64}
            plan-name {$f.GroupPlan.Inputs[-1].Name=$f.GroupPlan.Inputs[0].Name}
            plan-id {$f.GroupPlan.Inputs[-1].FileId=$f.GroupPlan.Inputs[0].FileId}
            plan-size {$f.GroupPlan.Inputs[-1].Bytes++}
            plan-budget {$f.GroupPlan.PhysicalBytes=5GB}
            plan-root {$f.GroupPlan.RunRoot=Join-Path $root 'different-group'}
            seal-hash {$f.Group.Items[-1].SHA256=$f.Group.Items[0].SHA256}
            seal-id {$f.Group.Items[-1].FileId=$f.Group.Items[0].FileId}
            seal-name {$f.Group.Items[-1].Path=$f.Group.Items[0].Path}
            seal-receipt {$f.Group.Items[-1].QualificationReceipt=Copy-Value $f.Group.Items[0].QualificationReceipt}
            incomplete {$f.Group.GroupComplete=$false}
            released {$f.Group.LeaseReleased=$false}
            guards {$f.Group.GuardsClosed=$false}
            failed {$f.Group.Status='Failed'}
            missing-row {$f.Group.Items=@($f.Group.Items[0..1])}
        }
        Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipts[-1] $f.Plan.Bootstraps[-1].Path}
    }
    $runner=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'Run-T7Catalogue.ps1'))
    $start=$runner.IndexOf('    $bootstraps=@(');$end=$runner.IndexOf('    $job=', $start)
    $fragment=$runner.Substring($start,$end-$start)
    foreach($case in 'missing-receipt','incomplete-seal'){
        $f=New-Shared;$plan=$f.Plan
        if($case -ceq 'missing-receipt'){$script:json.Remove($plan.Bootstraps[-1].QualificationReceipt.Path)}else{$f.Group.GroupComplete=$false}
        Refuses {. ([scriptblock]::Create($fragment));[IO.Directory]::CreateDirectory((Join-Path $plan.WorkingDirectory 'zone'))|Out-Null}
        Check (!(Test-Path -LiteralPath (Join-Path $plan.WorkingDirectory 'zone'))) 'Incomplete group reached alias publication.'
    }
    $plan=New-GroupPlan;$plan.Script.Path=$plan.Runner
    Check ((Assert-T7QualificationGroupPlan $plan $repo $plan.Runner $plan.Script.SHA256) -eq 3000) 'Source-only group plan sum differs.'
    $maximum=Copy-Value $plan;$maximum.Inputs[0].Bytes=512MB;$maximum.Inputs[-1].Bytes=256MB-1000
    Check ((Assert-T7QualificationGroupPlan $maximum $repo $maximum.Runner $maximum.Script.SHA256) -eq 768MB) 'Exact 512/768 MiB metadata ceiling refused.'
    foreach($case in 'zero','33','duplicate-name','duplicate-id','bytes','aggregate','unsafe','script','retry','budget','deadline'){
        $bad=Copy-Value $plan
        switch($case){
            zero {$bad.Inputs=@()}
            33 {$bad.Inputs=@(1..33|ForEach-Object {$plan.Inputs[0]})}
            duplicate-name {$bad.Inputs[-1]=Copy-Value $bad.Inputs[0]}
            duplicate-id {$bad.Inputs[-1].FileId=$bad.Inputs[0].FileId}
            bytes {$bad.Inputs[-1].Bytes=512MB+1}
            aggregate {$bad.Inputs[0].Bytes=512MB;$bad.Inputs[-1].Bytes=256MB}
            unsafe {$bad.Inputs[-1].Name='../escape.ff'}
            script {$bad.Script.SHA256='0'*64}
            retry {$bad.RetryAuthorized=$true}
            budget {$bad.PhysicalBytes=5GB}
            deadline {$bad.DeadlineSeconds=201}
        }
        Refuses {Assert-T7QualificationGroupPlan $bad $repo $plan.Runner $plan.Script.SHA256}
    }
    # Original small files only: two real streaming reads and retained read guards.
    $script:provider=@{};$script:ids=@{};$plan.Inputs=@()
    foreach($i in 0..2){
        $path=Join-Path $root ('original_'+$i+'.ff');$bytes=[byte[]]::new(70001+$i);$bytes[0]=[byte]($i+1);$bytes[-1]=123
        [IO.File]::WriteAllBytes($path,$bytes);$m=Get-Item -LiteralPath $path
        $entry=[pscustomobject]@{Name=$m.Name;Path=$path;Bytes=$m.Length;FileId=('AABBCCDD:'+($i+1).ToString('X16'));Attributes=[string]$m.Attributes;CreationUtc=$m.CreationTimeUtc.ToString('o');LastWriteUtc=$m.LastWriteTimeUtc.ToString('o')}
        $plan.Inputs+=@($entry);$script:ids[$path]=$entry.FileId
    }
    $context=New-GroupContext;$state=New-GroupState;$script:provider=@{}
    # New-State uses an old fixture, so restore only the synthetic input IDs.
    foreach($entry in $plan.Inputs){$script:ids[$entry.Path]=$entry.FileId}
    Invoke-T7QualificationInputs $plan $context $state 0
    Check ($context.PayloadGuards.Count -eq 6 -and $context.Rows.Count -eq 3) 'Two retained handles per explicit input required.'
    Check ($context.Rows[0].SHA256 -ceq [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($plan.Inputs[0].Path))).ToLowerInvariant()) 'Streaming digest differs from original tiny bytes.'
    Refuses {[IO.File]::AppendAllText($plan.Inputs[0].Path,'mutation')}
    foreach($guard in $context.PayloadGuards){$guard.Dispose()};$context.PayloadGuards.Clear()
    $realPass=${function:Open-T7QualificationPass}
    foreach($failAt in 1,3,6){
        $context=New-GroupContext;$state=New-GroupState;$script:provider=@{};foreach($entry in $plan.Inputs){$script:ids[$entry.Path]=$entry.FileId}
        $script:passCalls=0
        function Open-T7QualificationPass($Spec,$Guards,[double]$Started){$script:passCalls++;if($script:passCalls -eq $failAt){throw 'Injected read failure'};& $realPass $Spec $Guards $Started}
        Refuses {Invoke-T7QualificationInputs $plan $context $state 0} 'Injected read failure'
        Check (!$state.GroupComplete -and $state.Items.Count -eq 0) 'Failed qualification published a partial group.'
        Complete-QualificationGuards $context $state
        Check ($state.GuardsClosed -and $context.PayloadGuards.Count -eq 0) 'Failed read guards did not close.'
    }
    ${function:Open-T7QualificationPass}=$realPass
    $context=New-GroupContext;$state=New-GroupState;$script:provider=@{};foreach($entry in $plan.Inputs){$script:ids[$entry.Path]=$entry.FileId}
    $script:ids[$plan.Inputs[-1].Path]='AABBCCDD:FFFFFFFFFFFFFFFF'
    Refuses {Invoke-T7QualificationInputs $plan $context $state 0} 'before read'
    Check ($context.PayloadGuards.Count -eq 0) 'Late identity failure opened earlier payloads.'
    foreach($entry in $plan.Inputs){$script:ids[$entry.Path]=$entry.FileId}
    $script:clock=200000
    Refuses {Open-T7QualificationPass $plan.Inputs[0] $context.PayloadGuards 0} 'deadline'
    Check ($context.PayloadGuards.Count -eq 0) 'Deadline retained a failed handle.'
    $script:clock=0;$script:highWater=$true;Refuses {Assert-T7QualificationMemory} 'high water';$script:highWater=$false
    $script:clockStep=50000
    try{Refuses {Open-T7QualificationPass $plan.Inputs[0] $context.PayloadGuards 0} 'deadline'}finally{$script:clockStep=0;$script:clock=0}
    $exclusive=[IO.FileStream]::new($plan.Inputs[0].Path,'Open','Read','None');$exclusive.Dispose();$checks++
    $image=[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    $hostArgs=@('pwsh.dll','-NoLogo','-NoProfile','-NoExit','-File','C:\synthetic\qualifier.ps1','-PlanPath','C:\synthetic\plan.json','-PlanSHA256',('f'*64),'-ScriptSHA256',('e'*64),'-Run')
    $hostProof=Assert-QualificationPersistentHost $hostArgs $image 7 $hostArgs[5] ('e'*64) $hostArgs[7] ('f'*64) $image
    Check ($hostProof.NoExit -and $hostProof.ExactArgumentsVerified) 'Persistent group host rejected.'
    foreach($index in 2,3,4,5,7,9,11,12){
        $bad=$hostArgs.Clone();$bad[$index]='wrong'
        Refuses {Assert-QualificationPersistentHost $bad $image 7 $hostArgs[5] ('e'*64) $hostArgs[7] ('f'*64) $image}
    }
    # A changed second digest is rejected, even with the same length/identity.
    $context=New-GroupContext;$state=New-GroupState;$script:provider=@{};foreach($entry in $plan.Inputs){$script:ids[$entry.Path]=$entry.FileId}
    $script:passCalls=0
    function Open-T7QualificationPass($Spec,$Guards,[double]$Started){$script:passCalls++;$r=& $realPass $Spec $Guards $Started;if($script:passCalls -eq 2){$r.SHA256='0'*64};$r}
    try{Refuses {Invoke-T7QualificationInputs $plan $context $state 0} 'two-pass hash'}finally{${function:Open-T7QualificationPass}=$realPass;Complete-QualificationGuards $context $state}
    # Metadata mismatch must win over an exclusive-open failure, before reading.
    $bad=Copy-Value $plan.Inputs[0];$bad.Bytes--
    $exclusive=[IO.FileStream]::new($bad.Path,'Open','Read','None')
    try{Refuses {Open-T7QualificationPass $bad $context.PayloadGuards 0} 'metadata'}finally{$exclusive.Dispose()}
    foreach($value in @(0,-1,536870913,[long]::MaxValue,'1',$true)){
        $bad=Copy-Value $plan.Inputs[0];$bad.Bytes=$value;$bad.Path='C:\synthetic\never-opened.ff'
        Refuses {Open-T7QualificationPass $bad $context.PayloadGuards 0} 'before open'
    }
    # Positive publication happens only after full release; the group seal is last.
    $context=New-GroupContext;$state=New-GroupState;$script:provider=@{};foreach($entry in $plan.Inputs){$script:ids[$entry.Path]=$entry.FileId}
    Invoke-T7QualificationInputs $plan $context $state 0
    Refuses {Publish-T7QualificationItems $plan $context $state 0} 'Whole group'
    Complete-QualificationGuards $context $state
    $publication=Copy-Value $plan;$publication.RunRoot=Join-Path $root 'publication';[IO.Directory]::CreateDirectory($publication.RunRoot)|Out-Null
    Publish-T7QualificationItems $publication $context $state 0
    Check ($state.GroupComplete -and $state.Items.Count -eq 3 -and $state.LeaseReleased -and $state.GuardsClosed) 'Group publication did not follow whole-group closure.'
    $sealPath=Join-Path $publication.RunRoot 'group-receipt.json'
    Check (!(Test-Path -LiteralPath $sealPath)) 'Group seal was published before the final step.'
    $late=Publish-QualificationReceipt $sealPath $state 0
    $sealed=Read-H1SmallJson $sealPath 32KB
    Check (!$late -and $sealed.GroupComplete -and $sealed.Status -ceq 'IdentityAndHashObservedCompatibilityUnknown') 'Healthy final group seal differs.'
    foreach($row in $state.Items){
        Check ((Get-FileHash -LiteralPath $row.QualificationReceipt.Path).Hash.ToLowerInvariant() -ceq $row.QualificationReceipt.SHA256) 'Group seal did not bind the actual per-item receipt.'
    }
    foreach($delay in 0,200){
        $context=New-GroupContext;$state=New-GroupState;$script:clock=199900;$script:releaseDelay=$delay
        if(!$delay){$script:clock=200000}
        Complete-QualificationGuards $context $state
        $latePath=Join-Path $root ('late-release-'+$delay+'.json')
        $late=Publish-QualificationReceipt $latePath $state 0
        Check ($late -match 'deadline' -and (Read-H1SmallJson $latePath 32KB).Status -ceq 'Failed') 'Late release published a successful seal.'
        Check ($state.GuardsClosed -and $state.LeaseReleased) 'Deadline obscured completed release.'
    }
    $script:releaseDelay=0;$script:clock=199900
    $saveText=${function:Save-QualificationText}
    function Save-QualificationText([string]$Path,$Value){& $saveText $Path $Value;$script:clock+=200}
    try{
        $context=New-GroupContext;$state=New-GroupState;Complete-QualificationGuards $context $state
        $latePath=Join-Path $root 'late-publication.json';$late=Publish-QualificationReceipt $latePath $state 0
        Check ($late -match 'deadline' -and (Read-H1SmallJson $latePath 32KB).Status -ceq 'Failed' -and (Test-Path -LiteralPath ($latePath+'.deadline-exceeded'))) 'Late final seal was not invalidated.'
    }finally{${function:Save-QualificationText}=$saveText;$script:clock=0}
    # Release refusal retains the exact context and never permits publication.
    $context=New-GroupContext;$state=New-GroupState;$script:provider=@{};foreach($entry in $plan.Inputs){$script:ids[$entry.Path]=$entry.FileId}
    Invoke-T7QualificationInputs $plan $context $state 0;$script:releaseFails=$true
    try{
        Complete-QualificationGuards $context $state
        Check ($state.Quarantined -and !$state.GuardsClosed -and $context.PayloadGuards.Count -eq 6) 'Release refusal lost live guards.'
        Check ([object]::ReferenceEquals([AppDomain]::CurrentDomain.GetData('IW7.H1.Quarantine.synthetic-group'),$context)) 'Quarantine lost original context.'
        Refuses {Publish-T7QualificationItems $plan $context $state 0} 'Whole group'
        Refuses {Wait-QualificationRetention $state} 'RetentionWitness'
    }finally{$script:releaseFails=$false;foreach($guard in $context.PayloadGuards){$guard.Dispose()};[AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.synthetic-group',$null)}
    # Execute the real DEFAULT with a nonexistent synthetic donor directory.
    # Any donor metadata/payload access would fail; only actual source text is read.
    $default=New-GroupPlan 1;$default.Script.Path=$default.Runner
    $default.Script.Bytes=(Get-Item -LiteralPath $default.Runner).Length
    $default.Script.SHA256=(Get-FileHash -LiteralPath $default.Runner).Hash.ToLowerInvariant()
    $default.SourceDirectory=Join-Path $root 'never-created';$default.Inputs[0].Path=Join-Path $default.SourceDirectory $default.Inputs[0].Name
    $paths=@('tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1','tools-source/asset-bridge/t7-bridge/T7Catalogue.Profile.ps1',
        'tools-source/asset-bridge/t7-bridge/T7Prepatch.Profile.ps1','ops/Resource-Scheduler.Core.ps1','ops/Resource-Memory.ps1',
        'ops/Resource-RecorderOwnedProcess.Core.ps1','ops/native/ResourceMemory.cs','ops/hud-lab/HudFileIdentity.cs')
    foreach($relative in $paths){$path=Join-Path $repo $relative;$default.Bindings+=@([pscustomobject]@{Path=$path;Bytes=(Get-Item -LiteralPath $path).Length;SHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant();IsText=$true})}
    $defaultPath=Join-Path $root 'default-plan.json';Save-QualificationText $defaultPath $default
    $defaultHash=(Get-FileHash -LiteralPath $defaultPath).Hash.ToLowerInvariant()
    $output=& $image -NoProfile -File $default.Runner -PlanPath $defaultPath -PlanSHA256 $defaultHash -ScriptSHA256 $default.Script.SHA256
    if($LASTEXITCODE -ne 0){throw 'Default-only source validation failed.'}
    $answer=$output|ConvertFrom-Json
    Check ($answer.Status -ceq 'QualificationGroupCheckedPendingGO' -and !$answer.DataFileOpened -and !$answer.LiveProvidersCalled -and !$answer.LeaseAcquired) 'Default group check crossed its source-only boundary.'
    Check (!(Test-Path -LiteralPath $default.RunRoot) -and !(Test-Path -LiteralPath $default.SourceDirectory)) 'Default created input or runtime paths.'
    # Two independent raw checkouts: each seals its own bytes, without production
    # normalization or dependence on a historical H1 implementation hash.
    $rawHashes=@()
    foreach($ending in 'LF','CRLF'){
        $copyRepo=Join-Path $root ('source-'+$ending)
        $qualifierRelative='tools-source/asset-bridge/t7-bridge/Qualify-T7BootstrapGroup.ps1'
        foreach($relative in @($paths)+@($qualifierRelative)){
            $destination=Join-Path $copyRepo $relative
            [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination))|Out-Null
            $sourcePath=if($relative -ceq $paths[0]){$ReviewedCorePath}else{Join-Path $repo $relative}
            $sourceBytes=[IO.File]::ReadAllBytes($sourcePath)
            if($relative -ceq $paths[0]){
                $sourceText=[Text.UTF8Encoding]::new($false,$true).GetString($sourceBytes).Replace("`r`n","`n")
                if($ending -ceq 'CRLF'){$sourceText=$sourceText.Replace("`n","`r`n")}
                $sourceBytes=[Text.UTF8Encoding]::new($false).GetBytes($sourceText)
            }
            [IO.File]::WriteAllBytes($destination,$sourceBytes)
        }
        $copyPlan=Copy-Value $default;$copyPlan.Runner=Join-Path $copyRepo $qualifierRelative
        $copyPlan.Script=[pscustomobject]@{Path=$copyPlan.Runner;Bytes=(Get-Item -LiteralPath $copyPlan.Runner).Length;SHA256=(Get-FileHash -LiteralPath $copyPlan.Runner).Hash.ToLowerInvariant()}
        $copyPlan.RunRoot=Join-Path $copyRepo 'runtime/t7-bootstrap-group-synthetic';$copyPlan.Bindings=@()
        foreach($relative in $paths){$path=Join-Path $copyRepo $relative;$copyPlan.Bindings+=@([pscustomobject]@{Path=$path;Bytes=(Get-Item -LiteralPath $path).Length;SHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant();IsText=$true})}
        $rawHashes+=@($copyPlan.Bindings[0].SHA256)
        $copyPath=Join-Path $copyRepo 'plan.json';Save-QualificationText $copyPath $copyPlan
        $copyHash=(Get-FileHash -LiteralPath $copyPath).Hash.ToLowerInvariant()
        $output=& $image -NoProfile -File $copyPlan.Runner -PlanPath $copyPath -PlanSHA256 $copyHash -ScriptSHA256 $copyPlan.Script.SHA256
        Check ($LASTEXITCODE -eq 0 -and ($output|ConvertFrom-Json).Status -ceq 'QualificationGroupCheckedPendingGO') ('Raw '+$ending+' DEFAULT failed.')
        Check (!(Test-Path -LiteralPath $copyPlan.RunRoot)) 'DEFAULT created a group root.'
        # An unpinned helper with observable import code must be refused before
        # execution. Run in this test host to prove all failed-bootstrap guards
        # have closed, independently of process exit disposing handles.
        $marker=Join-Path $copyRepo 'unexpected-core-import.txt';$copyCore=Join-Path $copyRepo $paths[0]
        [IO.File]::AppendAllText($copyCore,("`n[IO.File]::WriteAllText('"+$marker.Replace("'","''")+"','unexpected')`n"))
        $copyPlan.Bindings[0].Bytes=(Get-Item -LiteralPath $copyCore).Length # Keep the OLD raw hash.
        $badPath=Join-Path $copyRepo 'bad-core-plan.json';Save-QualificationText $badPath $copyPlan
        $badHash=(Get-FileHash -LiteralPath $badPath).Hash.ToLowerInvariant()
        Refuses {& {
            function Get-Item($LiteralPath){Microsoft.PowerShell.Management\Get-Item -LiteralPath $LiteralPath}
            & $copyPlan.Runner -PlanPath $badPath -PlanSHA256 $badHash -ScriptSHA256 $copyPlan.Script.SHA256
        }} 'Bootstrap text hash differs before H1 import'
        Check (!(Test-Path -LiteralPath $marker)) 'Unpinned core executed during bootstrap.'
        foreach($path in @($badPath,$copyPlan.Runner,$copyCore)){$guard=[IO.FileStream]::new($path,'Open','Read','None');$guard.Dispose();$checks++}
    }
    Check ($rawHashes.Count -eq 2 -and $rawHashes[0] -cne $rawHashes[1]) 'LF and CRLF did not use distinct exact raw pins.'
    Check (!('IW7ResourceMemoryV1' -as [type]) -and !('IW7HudFileIdentity' -as [type]) -and !('IW7.AnimationProbe.NativeJob' -as [type])) 'Pure tests loaded native support.'
    [ordered]@{Status='Passed';Checks=$checks;OwnerStockRead=$false;NativeTypesLoaded=$false;RealLeaseAcquired=$false;RunInvoked=$false;Fixtures='Shared V3 metadata, original small streaming files, fake release/clock'}|ConvertTo-Json
}finally{
    $full=[IO.Path]::GetFullPath($root);$temp=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$full.StartsWith($temp,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($full) -cnotmatch '^t7-group-tests-[0-9a-f]{32}$'){throw 'Unexpected group synthetic cleanup root.'}
    Remove-Item -LiteralPath $full -Recurse -Force
}
