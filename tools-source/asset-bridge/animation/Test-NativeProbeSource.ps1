# Light regression checks only: never dot-source/run the launcher, compile the
# C# helper, load Add-Type, reserve resources or create a child process.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$checks=0
function Assert-Check([bool]$Condition,[string]$Message){if(!$Condition){throw $Message};$script:checks++}
function Assert-Throws([scriptblock]$Body,[string]$Pattern){
    $caught=$false
    try {& $Body} catch {if($_.Exception.Message -notmatch $Pattern){throw};$caught=$true}
    Assert-Check $caught "Expected refusal: $Pattern"
}
$parseErrors=$null;$tokens=$null
$runnerPath=Join-Path $PSScriptRoot 'Run-NativeProbe.ps1'
$ast=[Management.Automation.Language.Parser]::ParseFile($runnerPath,[ref]$tokens,[ref]$parseErrors)
Assert-Check (!$parseErrors.Count) 'PowerShell runner syntax'
foreach($name in @('Assert-ArtifactBudget','Write-NewProbeBytes','Write-FinalProbeReceipts','Close-ProbeReservation')){
    $fn=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name},$true)
    Assert-Check ($null -ne $fn) "Missing tested function $name"
    . ([scriptblock]::Create($fn.Extent.Text))
}
# Roslyn syntax parsing only. Loading the already-installed parser is not
# Add-Type or CSharpCompilation.Emit, and invokes none of our P/Invoke methods.
$null=[Reflection.Assembly]::LoadFrom((Join-Path $PSHOME 'Microsoft.CodeAnalysis.dll'))
$null=[Reflection.Assembly]::LoadFrom((Join-Path $PSHOME 'Microsoft.CodeAnalysis.CSharp.dll'))
$cs=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Probe-NativeJob.cs') -Raw
$tree=[Microsoft.CodeAnalysis.CSharp.CSharpSyntaxTree]::ParseText($cs)
$csErrors=@($tree.GetDiagnostics() | Where-Object Severity -eq Error)
Assert-Check (!$csErrors.Count) "C# syntax: $csErrors"
$calls=@($tree.GetRoot().DescendantNodes() | Where-Object {$_ -is [Microsoft.CodeAnalysis.CSharp.Syntax.InvocationExpressionSyntax]} | ForEach-Object {$_.Expression.ToString()})
Assert-Check ($calls -contains 'TerminateJobObject' -and $calls -contains 'QueryInformationJobObject') 'Exact tree termination and accounting calls required'
Assert-Check ($cs -match 'JobList = 0x2000d' -and $cs.IndexOf('(IntPtr)JobList') -lt $cs.IndexOf('bool ok = CreateProcessW')) 'Atomic job list before creation'
Assert-Check ($cs -match 'RootExited\(\) && ActiveProcesses\(\) == 0') 'Root-only wait cannot establish tree closure'
$runner=Get-Content -LiteralPath $runnerPath -Raw
Assert-Check ($runner -notmatch 'ReadToEndAsync|\.Kill\(|\.WaitForExit\(') 'No pipe drain or root-only termination fallback'
Assert-Check ($runner.IndexOf('$lease=Enter-IW7ResourceLease') -lt $runner.IndexOf('Add-Type -Path')) 'Helper compilation must remain inside admission'

$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$testRoot=Join-Path $repo ('runtime/probe-source-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($testRoot)|Out-Null
$artifactLimit=4096L;$metadataReserve=1024L
try {
    $output=Join-Path $testRoot 'success';[IO.Directory]::CreateDirectory($output)|Out-Null
    Assert-Check ((Assert-ArtifactBudget) -eq 0) 'Empty directory is zero'
    Write-NewProbeBytes (Join-Path $output 'payload.bin') ([byte[]]::new(3072))
    Assert-Check ((Assert-ArtifactBudget) -eq 3072) 'Payload limit includes metadata reserve'
    $receipt=[ordered]@{Status='NativeSerializerAndReadbackPassed'}
    Write-FinalProbeReceipts $receipt @{Leases=@()}
    $actual=0L;Get-ChildItem -LiteralPath $output -File | ForEach-Object {$actual+=$_.Length}
    Assert-Check ($actual -le $artifactLimit -and $actual -gt 3072) 'Both final receipts counted'
    Assert-Check ((Assert-ArtifactBudget -Final) -eq $actual) 'Final disk byte count exact'
    Assert-Check ((Test-Path -LiteralPath (Join-Path $output 'native-receipt.json')) -and !(Test-Path -LiteralPath (Join-Path $output 'native-receipt.pending.json'))) 'Successful publication only by pending rename'

    $output=Join-Path $testRoot 'payload-over';[IO.Directory]::CreateDirectory($output)|Out-Null
    Write-NewProbeBytes (Join-Path $output 'payload.bin') ([byte[]]::new(3073))
    Assert-Throws {Write-FinalProbeReceipts ([ordered]@{Status='Passed'}) @{}} 'artifact budget exceeded'
    Assert-Check (!(Test-Path -LiteralPath (Join-Path $output 'native-receipt.json'))) 'Over-reserve payload cannot publish success'

    $output=Join-Path $testRoot 'metadata-over';[IO.Directory]::CreateDirectory($output)|Out-Null
    # 700 characters but 1400 UTF8 bytes: reservation must use encoded bytes.
    Assert-Throws {Write-FinalProbeReceipts ([ordered]@{Status='Passed';Error=('é'*700)}) @{}} 'reserved metadata space'
    Assert-Check (@(Get-ChildItem -LiteralPath $output -File).Count -eq 0) 'Oversized receipts rejected before either write'

    $output=Join-Path $testRoot 'late-growth';[IO.Directory]::CreateDirectory($output)|Out-Null
    $realBudget=(Get-Item Function:Assert-ArtifactBudget).ScriptBlock
    function Assert-ArtifactBudget([switch]$Final){
        if($Final -and !(Test-Path -LiteralPath (Join-Path $output 'unexpected.bin'))){Write-NewProbeBytes (Join-Path $output 'unexpected.bin') ([byte[]]::new(4096))}
        & $realBudget -Final:$Final
    }
    Assert-Throws {Write-FinalProbeReceipts ([ordered]@{Status='Passed'}) @{}} 'artifact budget exceeded'
    Assert-Check (!(Test-Path -LiteralPath (Join-Path $output 'native-receipt.json'))) 'Late file growth fails before final rename'
    Set-Item Function:Assert-ArtifactBudget $realBudget

    $script:releaseCalls=0
    function Exit-IW7ResourceLease {param($Token) $script:releaseCalls++}
    $lease=@{Token='mock-only'}
    $closed=[pscustomobject]@{Closed=$true}
    $receipt=[ordered]@{}
    Close-ProbeReservation @($closed) $receipt $lease
    Assert-Check ($script:releaseCalls -eq 1 -and $receipt.LeaseReleased) 'Confirmed trees may release'

    $stuck=[pscustomobject]@{Closed=$false}
    $stuck | Add-Member ScriptMethod StopAndConfirm {param($timeout) throw 'Simulated descendant remains active'}
    $receipt=[ordered]@{}
    Assert-Throws {Close-ProbeReservation @($closed,$stuck) $receipt $lease} 'closure unconfirmed'
    Assert-Check ($script:releaseCalls -eq 1 -and !$receipt.LeaseReleased) 'Unconfirmed descendant quarantines without invoking shared releaser'

    $noProof=[pscustomobject]@{Closed=$false}
    $noProof | Add-Member ScriptMethod StopAndConfirm {param($timeout)}
    Assert-Throws {Close-ProbeReservation @($noProof) ([ordered]@{}) $lease} 'closure unconfirmed'
    Assert-Check ($script:releaseCalls -eq 1) 'Returning from stop without proof is insufficient'

    $recoverable=[pscustomobject]@{Closed=$false}
    $recoverable | Add-Member ScriptMethod StopAndConfirm {param($timeout) $this.Closed=$true}
    $receipt=[ordered]@{}
    Close-ProbeReservation @($recoverable) $receipt $lease
    Assert-Check ($script:releaseCalls -eq 2 -and $receipt.AllOwnedTreesClosed) 'Cleanup-confirmed tree may release'
    "Passed $checks light checks. C# parsed only; no native compilation/runner/process tree test."
} finally {
    # File-by-file cleanup confined to this unique test directory, no recursive delete.
    $canonical=[IO.Path]::GetFullPath($testRoot)
    $allowed=[IO.Path]::GetFullPath((Join-Path $repo 'runtime'))+[IO.Path]::DirectorySeparatorChar
    if(!$canonical.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)){throw 'Test cleanup escaped runtime'}
    Get-ChildItem -LiteralPath $canonical -File -Recurse | ForEach-Object {Remove-Item -LiteralPath $_.FullName}
    Get-ChildItem -LiteralPath $canonical -Directory | ForEach-Object {Remove-Item -LiteralPath $_.FullName}
    Remove-Item -LiteralPath $canonical
}
