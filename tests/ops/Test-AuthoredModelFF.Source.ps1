param([string]$Repo=(Resolve-Path "$PSScriptRoot/../..").Path)
$ErrorActionPreference='Stop'
. "$Repo/ops/model-lab/ModelFF.Core.ps1"
$checks=0
function Require($Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
$descriptor=[pscustomobject]@{Schema='iw7.authored-model-ff-main-stock/1';SourceRoot='C:\authored source';
    TLS=[pscustomobject]@{Path='C:\source tools\tlsdll.dll';Bytes=113152;SHA256=('a'*64)};
    Sentinel=[pscustomobject]@{Path='C:\source sentinel\fileSysCheck.cfg';Bytes=77;SHA256=('b'*64)}}
$layout=@(Get-ModelFFAuthoredStockInputs $descriptor $descriptor.SourceRoot)
Require ($layout.Count -eq 104) '104 current authored aliases required'
Require (@($layout|Where-Object Mode -CEQ HardLink).Count -eq 95) '95 immutable links required'
Require (@($layout|Where-Object Mode -CEQ Copy).Count -eq 9) '9 copied bootstrap/tool/sentinel entries required'
Require (@($layout.Source|Sort-Object -Unique).Count -eq 73) '73 current providers required, distinct from player71'
Require (@($layout|Where-Object Relative -Match '\.pak$').Count -eq 33) '33 fixed PAK names required'
Require (@($layout|Where-Object {$_.Relative -ceq 'main/cp_zmb.ff' -or $_.Relative -ceq 'zone/cp_zmb.ff'}).Count -eq 2) 'Both FF aliases required'
Require (@($layout|Where-Object {$_.PSObject.Properties.Name -contains 'SourceId'}).Count -eq 0) 'Source proposal must not inherit file IDs'
$forged=$descriptor|ConvertTo-Json -Depth 5|ConvertFrom-Json
$forged.Sentinel|Add-Member NoteProperty Identity 'historical-id'
$refused=$false;try{Get-ModelFFAuthoredStockInputs $forged $forged.SourceRoot|Out-Null}catch{$refused=$true}
Require $refused 'Historical sentinel identity must be refused'
$refused=$false;try{Get-ModelFFAuthoredStockInputs $descriptor 'C:\other source'|Out-Null}catch{$refused=$true}
Require $refused 'Different current Main root must be refused'

$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile("$Repo/ops/model-lab/Build-ModelFF.ps1",[ref]$tokens,[ref]$errors)
Require (!$errors.Count) 'Actual entry must parse'
$admission=@($ast.FindAll({param($node)$node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -ceq 'Enter-IW7ResourceLease'},$true))
Require ($admission.Count -eq 1) 'One existing admission required'
$nativeTypes=@($ast.FindAll({param($node)$node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -ceq 'Add-Type'},$true))
Require (@($nativeTypes|Where-Object {$_.Extent.StartOffset -gt $admission[0].Extent.EndOffset}).Count -eq 1) 'Build identity import must follow admission; other import is retained Restore only'
$entry=[IO.File]::ReadAllText("$Repo/ops/model-lab/Build-ModelFF.ps1")
Require ($entry.IndexOf('SetData($modelFFRoot.Key,$modelFFRoot)') -lt $admission[0].Extent.StartOffset) 'Actual root must precede admission'
$preview=@($ast.FindAll({param($node)$node -is [Management.Automation.Language.IfStatementAst] -and $node.Clauses[0].Item1.Extent.Text.Trim() -ceq '$DryRun'},$true))
Require ($preview.Count -eq 1 -and $preview[0].Extent.EndOffset -lt $admission[0].Extent.StartOffset) 'Source preview must precede admission'
$previewCommands=@($preview[0].FindAll({param($node)$node -is [Management.Automation.Language.CommandAst]},$true)|ForEach-Object GetCommandName)
Require (@($previewCommands|Where-Object {$_ -cne 'ConvertTo-Json'}).Count -eq 0) 'Preview must not inspect stock/tool/asset inputs'
$rootTry=@($ast.FindAll({param($node)$node -is [Management.Automation.Language.TryStatementAst] -and
    $node.Body.Extent.StartOffset -lt $admission[0].Extent.StartOffset -and $node.Body.Extent.EndOffset -gt $admission[0].Extent.EndOffset},$true))
Require ($rootTry.Count -eq 1) 'One complete original admission scope required'
$entryEvents=[Collections.Generic.List[string]]::new()
function Enter-IW7ResourceLease {$entryEvents.Add('admission');throw 'injected admission refusal'}
function Add-Type {$entryEvents.Add('native-type');throw 'native import must remain unreachable'}
$body=$rootTry[0].Body.Extent.Text;$refused=$false
try{& ([scriptblock]::Create($body.Substring(1,$body.Length-2)))}catch{$refused=$true}
Require ($refused -and ($entryEvents-join ',') -ceq 'admission') 'Actual admission refusal must prevent every downstream preflight effect'
Remove-Item Function:Add-Type

$projectFiles=[ordered]@{}
foreach($name in 'README.md','authoring.json','color.rgba8.json','geometry.source.json','manifest.json','second_author_script.gsc'){
    $projectFiles[$name]=[pscustomobject]@{Bytes=10;SHA256=('c'*64)}
}
$templates=[ordered]@{}
foreach($role in 'material','statebits','statebitsmap','stateinfo','cbi','cbt'){
    $templates[$role]=[pscustomobject]@{Path=('C:\source material\'+$role);Bytes=10;SHA256=('d'*64)}
}
$author=[pscustomobject]@{Schema='iw7.authored-model-ff-author-inputs/1';ProjectSource='C:\source author';
    ProjectFiles=[pscustomobject]$projectFiles;Templates=[pscustomobject]$templates;
    SDKSourceWorkspace=[pscustomobject]@{Path='C:\source sdk\source-workspace.json';Bytes=10;SHA256=('e'*64)}}
Assert-ModelFFAuthorInputs $author $author.ProjectSource;$checks++
$stageArgs=@(Get-ModelFFAuthorStageArguments 'C:\source sdk' 'C:\source author' 'C:\source writer' 'C:\fresh stage')
Require ($stageArgs.Count -eq 8 -and ($stageArgs[0..2]-join ',') -ceq '-B,-S,-c') 'Existing API must use isolated stdlib Python and four literal path arguments'
Require ($stageArgs[4] -ceq 'C:\source sdk' -and $stageArgs[7] -ceq 'C:\fresh stage') 'Author paths must remain separate ArgumentList values'
Require ($stageArgs[3].Contains('author.stage_ff_inputs(') -and $stageArgs[3].Contains('sdk.validate(manifest, stage=''plan'')') -and
    $stageArgs[3].Contains('source_plan_file')) 'Existing SDK must own staging; actual plan bytes must be measured inside that original job'
$badAuthor=$author|ConvertTo-Json -Depth 8|ConvertFrom-Json
$badAuthor.Templates.material|Add-Member NoteProperty Identity 'old-retail-id'
$refused=$false;try{Assert-ModelFFAuthorInputs $badAuthor $badAuthor.ProjectSource}catch{$refused=$true}
Require $refused 'Source author metadata must refuse old template identities'

# Execute the real restore function with pure causal collaborators. No source,
# stock, native process, identity class or reservation is consulted.
$events=[Collections.Generic.List[string]]::new()
function Assert-ModelFFVacant($Work){$events.Add('vacant')}
function Assert-ModelFFInputs($Inputs,$Work,[switch]$SourceOnly){$events.Add($(if($SourceOnly){'source'}else{'aliases'}))}
function Restore-IW7BaseTransaction($Transaction){$events.Add('restore');if($script:failRestore){throw 'injected restore failure'}}
function Write-ModelFFState($State,$Path){$events.Add('state')}
function Exit-IW7ResourceLease($Token){$events.Add('release')}
function New-State { @{Work='C:\synthetic work';Inputs=@();Transaction=@{};Restored=$false;StockPreserved=$false;
    RestorationStatus='Pending';CleanupError=$null;RetainedLeaseToken='synthetic-original'} }
$script:failRestore=$false;$state=New-State
Complete-ModelFFRestore $state 'unused' 'synthetic-original' -BeforeReleaseCheck {$events.Add('original-pins-and-publication')}
Require ($state.Restored -and $state.StockPreserved -and $null -eq $state.RetainedLeaseToken) 'Successful restoration must precede release'
Require ($events.IndexOf('restore') -lt $events.IndexOf('original-pins-and-publication') -and
    $events.IndexOf('original-pins-and-publication') -lt $events.IndexOf('release')) 'Original-pin callback must be between restore and release'
$events.Clear();$state=New-State;$refused=$false
try{Complete-ModelFFRestore $state 'unused' 'synthetic-original' -BeforeReleaseCheck {throw 'injected input/publication failure'}}catch{$refused=$true}
Require ($refused -and 'release' -cnotin $events -and $state.RetainedLeaseToken -ceq 'synthetic-original') 'Failed original-pin/publication check must retain the exact lease'
$events.Clear();$state=New-State;$script:failRestore=$true;$refused=$false
try{Complete-ModelFFRestore $state 'unused' 'synthetic-original' -BeforeReleaseCheck {$events.Add('callback')}}catch{$refused=$true}
Require ($refused -and 'release' -cnotin $events -and 'callback' -cnotin $events -and $state.RestorationStatus -ceq 'Refused') 'Failed restoration must not reach callback or release'
$script:failRestore=$false;$events.Clear();$state=New-State
Complete-ModelFFRestore $state 'unused' 'synthetic-original'
Require ('release' -cin $events -and 'original-pins-and-publication' -cnotin $events) 'Legacy default callback behavior must remain unchanged'

# Use the real H1 dispatcher and actual entry factory/deadline definitions;
# only clock and owner collaborators are synthetic. No NativeJob type loads.
. "$Repo/tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1"
$originalFFDeadline=${function:Assert-H1Deadline}
$h1Tokens=$null;$h1Errors=$null
$testAst=[Management.Automation.Language.Parser]::ParseFile("$Repo/tools-source/asset-bridge/h1-fixture/Test-H1Native.ps1",[ref]$h1Tokens,[ref]$h1Errors)
$fakeDefinition=@($testAst.FindAll({param($node)$node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'New-FakeOwner'},$true))
Require ($fakeDefinition.Count -eq 1) 'One existing Source fake owner required'
. ([scriptblock]::Create($fakeDefinition[0].Extent.Text))
foreach($name in 'Assert-H1Deadline','Assert-ModelFFGroupDeadline','New-H1Owner'){
    $definition=@($ast.FindAll({param($node)$node -is [Management.Automation.Language.FunctionDefinitionAst]},$true)|Where-Object Name -CEQ $name)
    . ([scriptblock]::Create($definition[-1].Extent.Text))
}
function Get-H1Clock {$script:modelFFClock}
function Register-H1Original($Lease,$Identity){}
function Test-H1Budget($Plan,$State){}
$originalFFFactory={$script:modelFFClock+=$script:modelFFFactoryDelay;$script:modelFFFake}
foreach($case in @(
    @{Name='baseline';Clock=0;Phase=0;Delay=0;Starts=1;Retained=$true},
    @{Name='setup-phase-boundary';Clock=30000;Phase=0;Delay=0;Starts=0;Retained=$false},
    @{Name='factory-phase-boundary';Clock=29999;Phase=0;Delay=1;Starts=0;Retained=$true},
    @{Name='setup-group-boundary';Clock=600000;Phase=599900;Delay=0;Starts=0;Retained=$false},
    @{Name='factory-group-boundary';Clock=599999;Phase=599900;Delay=1;Starts=0;Retained=$true},
    @{Name='last-phase-millisecond';Clock=590000;Phase=560001;Delay=0;Starts=1;Retained=$true}
)){
    $script:modelFFClock=[double]$case.Clock;$script:modelFFFactoryDelay=[double]$case.Delay
    $script:modelFFFake=New-FakeOwner
    $modelFFRoot=[pscustomobject]@{GroupStarted=0.0;GroupDeadlineSeconds=600;PhaseStarted=[double]$case.Phase;PhaseSeconds=30}
    $originalContext=[pscustomobject]@{Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token='synthetic-original'}}
    $stage=[ordered]@{Stage='Fixture';DeadlineSeconds=30;MaxObservedOutputBytes=0L}
    $start=[pscustomobject]@{FileName='C:\fixture.exe'}
    try{Invoke-H1OwnedStage $null $stage $originalContext $start ('a'*64) 'C:\unused'}catch{}
    Require ($script:modelFFFake.Starts -eq $case.Starts) ('Wrong Start count: '+$case.Name)
    Require ([object]::ReferenceEquals($originalContext.Owner,$script:modelFFFake) -eq $case.Retained) ('Wrong actual owner retention: '+$case.Name)
}
[ordered]@{SourceOnly=$true;Assertions=$checks;NativeProcessStarted=$false;StockRead=$false;LeaseAcquired=$false;Result='PASS'}|ConvertTo-Json -Compress
