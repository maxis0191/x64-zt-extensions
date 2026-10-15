# Actual runner finalizer/factory with fake publications, guards, clock and owner.
# No admission, artifact, compiler, SDK or native type is used.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$here=$PSScriptRoot;$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $here 'Run-T7Build.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner parse failed'}
$outer=@($ast.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.TryStatementAst]})
if($outer.Count -ne 1){throw 'Exactly one actual runner finalizer required'}
$body=$outer[0].Finally.Extent.Text;$finalize=[scriptblock]::Create($body.Substring(1,$body.Length-2))
$core=Join-Path (Split-Path $here -Parent) 'h1-fixture/H1Native.Core.ps1'
. $core
$realComplete=${function:Complete-H1Stage}
$realInvoke=${function:Invoke-H1OwnedStage}
. (Join-Path $here 'T7Build.Profile.ps1')
$factory=@($ast.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'New-H1Owner'},$true))
if($factory.Count -ne 1){throw 'One local checked factory required'}
$factoryCode=$factory[0].Extent.Text
$loops=@($ast.FindAll({param($n)$n -is [Management.Automation.Language.ForEachStatementAst] -and $n.Variable.VariablePath.UserPath -ceq 'stage' -and $n.Extent.Text.Contains('Invoke-T7OwnedStage')},$true))
if($loops.Count -ne 1 -or $loops[0].Body.Statements[0].Extent.Text -cne '$stageStarted=Get-H1Clock' -or
   $loops[0].Extent.Text -cnotmatch 'Invoke-T7OwnedStage .* \$stageStarted'){throw 'Actual admitted phase clock must precede every setup statement'}
$checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
$script:T7GroupStarted=0.0
function Get-H1Clock {$script:FakeClock}
function New-FakeGuard([string]$Tag){
    $g=[pscustomobject]@{Tag=$Tag;Closed=$false}
    $g|Add-Member ScriptMethod Dispose {
        $script:Events.Add('dispose:'+ $this.Tag)
        if($script:FailureAt -ceq 'dispose' -and $this.Tag -ceq 'input'){throw 'fake guard disposal failed'}
        $this.Closed=$true
    }
    return $g
}
function Exit-IW7ResourceLease($Token){
    Check ($guards.Count -eq 1 -and !$guards[0].Closed) 'Inputs were dropped before lease release'
    Check (!$created -or $context.PreReleasePublished) 'Lease released before known prepublication'
    $script:Events.Add('release');$script:Releases++
}
function Write-H1Receipt($Plan,$State,$Root,[string]$Name='receipt.json',[switch]$PassThru){
    Check ($guards.Count -eq 1 -and !$guards[0].Closed) 'Inputs were dropped before receipt publication'
    $script:Events.Add('publish:'+ $Name)
    if(($script:FailureAt -ceq 'pre-write' -and $Name -ceq 'receipt-before-release.json') -or
       ($script:FailureAt -ceq 'post-write' -and $Name -ceq 'receipt.json')){throw 'fake publication failed'}
    if($Name -ceq 'receipt.json'){
        $script:CanonicalStatus=$State.Status
        if($script:FailureAt -ceq 'late-move'){$script:FakeClock=601000.0}
    }
    [pscustomobject]@{Path=('C:\authored\'+$Name);Bytes=1;SHA256=('a'*64)}
}
function Assert-H1Path($Path){if($script:FailureAt -ceq 'late-move'){throw 'fake retirement refused before Move'};throw 'Unexpected filesystem path inspection'}
function Open-H1Pin($Pin){
    Check ($guards.Count -eq 1 -and !$guards[0].Closed) 'Inputs were dropped before publication readback'
    $script:Opens++
    if($script:FailureAt -ceq 'readback-deadline' -and $script:Opens -eq 4){$script:FakeClock=601000.0}
    if(($script:FailureAt -ceq 'pre-open' -and $script:Opens -eq 1) -or
       ($script:FailureAt -ceq 'post-open' -and $script:Opens -eq 2) -or
       ($script:FailureAt -ceq 'recheck' -and $script:Opens -eq 3)){throw 'fake publication readback failed'}
    return (New-FakeGuard $Pin.Path)
}
function Invoke-FinalizerCase([string]$Case){
    $script:FailureAt=$Case;$script:Events=[Collections.Generic.List[string]]::new()
    $script:FakeClock=1000.0;$script:Releases=0;$script:Opens=0
    $script:CanonicalStatus=$null
    $guards=[Collections.Generic.List[object]]::new();$input=New-FakeGuard 'input';$guards.Add($input)
    $owner=[pscustomobject]@{Closed=$true;ExitCode=0}
    $context=[pscustomobject]@{Owner=$owner;Closed=$true;Lease=[pscustomobject]@{Token='FAKE_NO_ADMISSION'};Guards=$guards;
        PublicationGuards=[Collections.Generic.List[object]]::new();Publications=[Collections.Generic.List[object]]::new();
        PreReleasePublished=$false;CompletionPublished=$false;CanExit=$false}
    $sameContext=$context
    $state=[ordered]@{Status='Pending';InputsReverified=$true;LeaseReleased=$false;LeaseToken='FAKE_NO_ADMISSION';Quarantined=$false}
    $plan=[pscustomobject]@{GroupDeadlineSeconds=600;RunRoot='C:\authored\NO_FILES'}
    $failure=$null;$created=$true;$launcher=$null;$priority=$null;$registration=$false;$incoming=$false
    if($Case -ceq 'known-failure'){
        try{throw 'fake compiler failure'}catch{$failure=$_};$state.Status='Failed'
    }
    if($Case -ceq 'no-owned-root'){$created=$false;$context.Owner=$null}
    . $finalize
    Check ([object]::ReferenceEquals($sameContext,$context)) 'Original context was replaced'
    if($Case -cin @('success','known-failure','no-owned-root')){
        Check ($context.CanExit -and $guards.Count -eq 0 -and $context.PublicationGuards.Count -eq 0 -and $null -eq $context.Lease) 'Known closure retained or lost guards incorrectly'
        Check ($script:Releases -eq 1) 'Known closure must release exactly once'
        if($Case -cne 'no-owned-root'){Check ($context.PreReleasePublished -and $context.CompletionPublished) 'Both publications must be known'}
        if($Case -ceq 'success'){Check ($state.Status -ceq 'Passed' -and $null -eq $failure) 'Success finalization differs'}
        if($Case -ceq 'known-failure'){Check ($state.Status -ceq 'Failed' -and $null -ne $failure) 'Known failed compiler must not become Passed'}
        if($Case -ceq 'no-owned-root'){Check (@($script:Events|Where-Object {$_ -like 'publish:*'}).Count -eq 0) 'No owned root wrote into a foreign output'}
    }else{
        Check (!$context.CanExit -and $guards.Count -eq 1 -and !$input.Closed) 'Unknown publication lost actual input guards'
        Check ([object]::ReferenceEquals($context.Owner,$owner)) 'Unknown publication lost actual owner'
        if($Case -cin @('pre-write','pre-open')){
            Check ($null -ne $context.Lease -and $script:Releases -eq 0 -and $state.Quarantined) 'Prepublication failure released lease'
        }else{
            Check ($null -eq $context.Lease -and $script:Releases -eq 1 -and $context.PublicationGuards.Count -gt 0) 'Postpublication failure lost prior held publication'
        }
        if($Case -cin @('late-move','readback-deadline')){
            Check ($state.Status -ceq 'Failed' -and $script:CanonicalStatus -ceq 'Passed' -and
                !$context.CompletionPublished -and $null -ne $failure) 'Expired/uncorrected Passed publication was treated as known completion'
        }
    }
}
foreach($case in @('success','known-failure','no-owned-root','pre-write','pre-open','post-write','post-open','recheck','dispose','late-move','readback-deadline')){Invoke-FinalizerCase $case}
function Invoke-FactoryCase([double]$Now,[double]$After,[double]$Phase,[int]$Factories,[int]$Starts,[bool]$Retained){
    $script:FakeClock=$Now;$script:AfterFactory=$After;$script:FactoryCalls=0;$script:Starts=0
    $script:T7StageStarted=$Phase;$script:T7StageDeadlineSeconds=120
    $script:FakeOwner=[pscustomobject]@{Tag='ACTUAL_FAKE_OWNER'}
    $script:FakeOwner|Add-Member ScriptMethod Start {param($A,$B,$C,$D)$script:Starts++;throw 'fake Start reached'}
    $script:T7OriginalFactory={$script:FactoryCalls++;$script:FakeClock=$script:AfterFactory;return $script:FakeOwner}
    $context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null};$t7OriginalContext=$context
    $state=[ordered]@{Stage='Compile';DeadlineSeconds=120};$plan=[pscustomobject]@{GroupDeadlineSeconds=600}
    . ([scriptblock]::Create($factoryCode))
    $caught=$null;try{& $realInvoke $plan $state $context $null ('0'*64) 'C:\authored\NO_FILES' $Phase}catch{$caught=$_}
    Check ($null -ne $caught -and $script:FactoryCalls -eq $Factories -and $script:Starts -eq $Starts) 'Factory deadline causal differs'
    Check ([object]::ReferenceEquals($context.Owner,$script:FakeOwner) -eq $Retained) 'Actual returned owner was lost on deadline'
}
Invoke-FactoryCase 599000 599000 599000 1 1 $true
Invoke-FactoryCase 601000 601000 599000 0 0 $false
Invoke-FactoryCase 121000 121000 0 0 0 $false
Invoke-FactoryCase 599000 601000 599000 1 0 $true
Invoke-FactoryCase 119000 121000 0 1 0 $true
Invoke-FactoryCase 599000 600000 599000 1 0 $true
Invoke-FactoryCase 119000 120000 0 1 0 $true
Check (!('IW7.AnimationProbe.NativeJob' -as [type])) 'Source tests loaded native job type'
[ordered]@{SourceOnly=$true;Checks=$checks;FinalizerCases=11;FactoryCases=7;ActualClockOrdering=$true;
    CPPExecuted=$false;SDKOrOpaqueBytesRead=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json -Compress
