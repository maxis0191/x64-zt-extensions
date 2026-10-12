# Prepared command for the parent's next GO. Has never been executed at commit.
# No writer/MSVC/ZoneTool/game work: one Add-Type library and short PS fixtures.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$OutputRoot,[Parameter(Mandatory)][string]$PowerShellExe)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell7 required.'}
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$output=[IO.Path]::GetFullPath($OutputRoot)
$runtime=[IO.Path]::GetFullPath((Join-Path $repo 'runtime'))+[IO.Path]::DirectorySeparatorChar
if(!$output.StartsWith($runtime,[StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $output)){throw 'Fresh witness output beneath this worktree runtime required.'}
for($p=[IO.DirectoryInfo]$output;$p;$p=$p.Parent){if($p.Exists -and ($p.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse output refused.'}}
$PowerShellExe=[IO.Path]::GetFullPath($PowerShellExe)
if(!(Test-Path -LiteralPath $PowerShellExe -PathType Leaf)){throw 'Existing PowerShell executable required.'}
$shellHash=(Get-FileHash -LiteralPath $PowerShellExe).Hash
$nodeScript=Join-Path $PSScriptRoot 'NativeJob-WitnessNode.ps1'
$jobSource=Join-Path $PSScriptRoot 'Probe-NativeJob.cs'
$runnerSource=Join-Path $PSScriptRoot 'Run-NativeProbe.ps1'
$sourceHashes=[ordered]@{}
foreach($path in @($PSCommandPath,$nodeScript,$jobSource,$runnerSource)){$sourceHashes[[IO.Path]::GetFileName($path)]=(Get-FileHash -LiteralPath $path).Hash}
# Load only the pure budget/finalization/release functions, never the runner.
$errors=$null;$tokens=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($runnerSource,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner source syntax invalid.'}
foreach($name in @('Assert-ArtifactBudget','Write-NewProbeBytes','Write-FinalProbeReceipts','Close-ProbeReservation')){
    $fn=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
    if(!$fn){throw "Missing reviewed function $name"}
    . ([scriptblock]::Create($fn.Extent.Text))
}
. (Join-Path $repo 'ops/Resource-Scheduler.Core.ps1')
$artifactLimit=32MB;$metadataReserve=1MB
$ownedJobs=[Collections.Generic.List[object]]::new()
$observers=[Collections.Generic.List[object]]::new()
$cases=[Collections.Generic.List[object]]::new()
$nonce=[guid]::NewGuid().ToString('N')
$receipt=[ordered]@{Schema='iw7.native-job-witness/1';Status='Pending';NativeWriterRebuilt=$false;GameLaunched=$false;
    SourceCommit=(& git -C $repo rev-parse HEAD).Trim();SourceSHA256=$sourceHashes;PowerShell=$PowerShellExe;PowerShellSHA256=$shellHash;
    StartedUtc=[datetime]::UtcNow.ToString('o');Cases=$cases;PhysicalBytes=4GB;CommitBytes=6GB}
function Assert-Witness([bool]$Condition,[string]$Message){if(!$Condition){throw $Message}}
function New-WitnessCase([string]$Name) {
    $root=Join-Path $output $Name;[IO.Directory]::CreateDirectory($root)|Out-Null
    $ticket=[ordered]@{Kind='iw7.native-job-fixture/1';Nonce=$nonce;ExpiresUtc=[datetime]::UtcNow.AddMinutes(3).ToString('o')}
    Write-NewProbeBytes (Join-Path $root 'fixture-ticket.json') ([Text.Encoding]::UTF8.GetBytes(($ticket | ConvertTo-Json)))
    $root
}
function Start-WitnessJob([string]$Role,[string]$Root,[string]$Library='',[string]$LibraryHash='') {
    $start=[Diagnostics.ProcessStartInfo]::new($PowerShellExe)
    $start.WorkingDirectory=$Root;$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle='Hidden'
    $argsList=@('-NoProfile','-File',$nodeScript,'-Role',$Role,'-CaseRoot',$Root,'-PowerShellExe',$PowerShellExe,'-Nonce',$nonce)
    if($Library){$argsList+=@('-HelperAssembly',$Library,'-HelperSHA256',$LibraryHash)}
    foreach($arg in $argsList){$start.ArgumentList.Add($arg)}
    $owner=[IW7.AnimationProbe.NativeJob]::new();$ownedJobs.Add($owner)
    $owner.Start($start,$shellHash,(Join-Path $Root 'root.stdout.log'),(Join-Path $Root 'root.stderr.log'))
    $owner
}
function Open-WitnessIdentity([string]$Root,[string]$Role) {
    $ready=Join-Path $Root "$Role.ready.json";$timer=[Diagnostics.Stopwatch]::StartNew()
    while(!(Test-Path -LiteralPath $ready)){
        $null=Assert-ArtifactBudget
        if($timer.Elapsed.TotalSeconds -gt 10){throw "No ready identity: $Role at $Root"}
        Start-Sleep -Milliseconds 50
    }
    $identity=Get-Content -LiteralPath $ready -Raw | ConvertFrom-Json
    Assert-Witness ($identity.Nonce -ceq $nonce -and $identity.Role -ceq $Role) 'Fixture identity ticket differs.'
    $process=[Diagnostics.Process]::GetProcessById($identity.PID)
    $observers.Add($process);$null=$process.SafeHandle
    Assert-Witness (!$process.HasExited -and $process.StartTime.ToUniversalTime().ToFileTimeUtc() -eq $identity.CreationFileTime -and
        [string]::Equals($process.MainModule.FileName,$PowerShellExe,[StringComparison]::OrdinalIgnoreCase)) 'Live original fixture identity differs.'
    [pscustomobject]@{Process=$process;Identity=$identity}
}
function Open-TreeIdentities([string]$Root) {
    foreach($role in @('Parent','Child','Grandchild')){Open-WitnessIdentity $Root $role}
}
function Signal-Witness([string]$Root,[string]$Name){Write-NewProbeBytes (Join-Path $Root $Name) ([byte[]]@(1))}
function Assert-ObserversExited($Nodes) {
    foreach($node in $Nodes){Assert-Witness ($node.Process.WaitForExit(5000)) "Original $($node.Identity.Role) handle still alive."}
}
function Assert-ForeignAlive($Owner,$Node) {
    Assert-Witness (!$Owner.TreeExited() -and !$Node.Process.HasExited) 'Foreign witness did not survive target cleanup.'
}
$lease=Enter-IW7ResourceLease -Scope $output -Kind Build -Owner 'Native animation job ownership witness only' -PhysicalBytes 4GB -CommitBytes 6GB
$failure=$null;$launcher=$null;$priority=$null
try {
    $launcher=Get-Process -Id $PID;$priority=$launcher.PriorityClass;$launcher.PriorityClass='BelowNormal'
    [IO.Directory]::CreateDirectory($output)|Out-Null
    $receipt.AdmissionSnapshot=Get-IW7ResourceSnapshot
    if('IW7.AnimationProbe.NativeJob' -as [type]){throw 'Fresh PowerShell process required.'}
    $library=Join-Path $output 'Probe-NativeJob.dll'
    Add-Type -Path $jobSource -OutputAssembly $library -ErrorAction Stop
    if(!('IW7.AnimationProbe.NativeJob' -as [type])){$null=[Reflection.Assembly]::LoadFrom($library)}
    $receipt.HelperAssemblySHA256=(Get-FileHash -LiteralPath $library).Hash
    $null=Assert-ArtifactBudget

    # Foreign means a different owned job, never an existing user's process.
    $foreignRoot=New-WitnessCase 'foreign'
    $foreign=Start-WitnessJob 'Foreign' $foreignRoot
    $foreignNode=Open-WitnessIdentity $foreignRoot 'Foreign'

    $normalRoot=New-WitnessCase 'normal'
    $normal=Start-WitnessJob 'Parent' $normalRoot
    $nodes=@(Open-TreeIdentities $normalRoot)
    Signal-Witness $normalRoot 'finish'
    $timer=[Diagnostics.Stopwatch]::StartNew()
    while(!$normal.TreeExited()){
        $null=Assert-ArtifactBudget
        if($timer.Elapsed.TotalSeconds -gt 10){throw 'Normal fixture tree did not exit.'}
        Start-Sleep -Milliseconds 50
    }
    $normal.CloseConfirmed();Assert-Witness ($normal.ExitCode -eq 0) 'Normal root exit was not zero.'
    Assert-ObserversExited $nodes
    foreach($node in $nodes){Assert-Witness ($node.Process.ExitCode -eq 0) "Normal $($node.Identity.Role) exit was not zero."}
    Assert-ForeignAlive $foreign $foreignNode
    $cases.Add([ordered]@{Name='normal-tree';Passed=$true;RootExitCode=$normal.ExitCode;Nodes=@($nodes|ForEach-Object{$_.Identity});ForeignSurvived=$true})

    $orphanRoot=New-WitnessCase 'root-exits-first'
    $orphan=Start-WitnessJob 'Parent' $orphanRoot
    $nodes=@(Open-TreeIdentities $orphanRoot)
    Signal-Witness $orphanRoot 'parent-exit'
    Assert-Witness ($nodes[0].Process.WaitForExit(5000)) 'Root did not exit first.'
    Assert-Witness (!$nodes[1].Process.HasExited -and !$nodes[2].Process.HasExited -and !$orphan.TreeExited()) 'Root exit incorrectly completed its live descendant tree.'
    $orphan.StopAndConfirm(5000);Assert-ObserversExited $nodes;Assert-ForeignAlive $foreign $foreignNode
    $cases.Add([ordered]@{Name='root-exit-and-job-termination';Passed=$true;TreeStayedOpenAfterRootExit=$true;Nodes=@($nodes|ForEach-Object{$_.Identity});ForeignSurvived=$true})

    # A still-owned outer job is a fallback only. Kill just its exact launcher
    # handle; do NOT stop the outer job until the inner kill-on-close is proved.
    $crashRoot=New-WitnessCase 'launcher-exits'
    $outer=Start-WitnessJob 'Launcher' $crashRoot $library $receipt.HelperAssemblySHA256
    $launcherNode=Open-WitnessIdentity $crashRoot 'Launcher'
    $nodes=@(Open-TreeIdentities $crashRoot)
    Assert-Witness (!$launcherNode.Process.HasExited) 'Test launcher exited before forced-close observation.'
    $launcherNode.Process.Kill()
    Assert-Witness ($launcherNode.Process.WaitForExit(5000)) 'Exact test launcher did not terminate.'
    Assert-ObserversExited $nodes
    Assert-Witness ($outer.TreeExited()) 'Inner kill-on-close left active processes in the fallback outer job.'
    $outer.CloseConfirmed();Assert-ForeignAlive $foreign $foreignNode
    $cases.Add([ordered]@{Name='launcher-kill-on-close';Passed=$true;Launcher=$launcherNode.Identity;Nodes=@($nodes|ForEach-Object{$_.Identity});OuterTerminationUsedBeforeProof=$false;ForeignSurvived=$true})

    Signal-Witness $foreignRoot 'finish'
    Assert-ObserversExited @($foreignNode)
    Assert-Witness ($foreign.TreeExited()) 'Foreign witness did not finish.'
    $foreign.CloseConfirmed()
    foreach($path in @($PSCommandPath,$nodeScript,$jobSource,$runnerSource)){
        Assert-Witness ((Get-FileHash -LiteralPath $path).Hash -ceq $sourceHashes[[IO.Path]::GetFileName($path)]) 'Witness source changed during execution.'
    }
    $receipt.Status='OwnedJobWitnessPassed'
} catch {$failure=$_;$receipt.Status='Failed';$receipt.Error=$_.Exception.Message} finally {
    try {Close-ProbeReservation $ownedJobs $receipt $lease} catch {if(!$failure){$failure=$_};$receipt.LeaseReleaseError=$_.Exception.Message}
    foreach($observer in $observers){$observer.Dispose()}
    if($launcher -and $null -ne $priority){try {$launcher.PriorityClass=$priority} catch {if(!$failure){$failure=$_}}}
    if($failure){$receipt.Status='Failed'}
    $receipt.FinishedUtc=[datetime]::UtcNow.ToString('o')
}
if(Test-Path -LiteralPath $output){
    try {Write-FinalProbeReceipts $receipt (Get-IW7ResourceStatus)} catch {if(!$failure){$failure=$_};Write-Warning "No complete final witness publication: $($_.Exception.Message)"}
}
if($failure){throw $failure}
Write-Output "Witness receipt: $(Join-Path $output 'native-receipt.json')"
