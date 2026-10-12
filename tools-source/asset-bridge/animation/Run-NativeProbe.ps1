# Revised failure/receipt paths are source-tested only. See RUNNER-CORRECTIONS.md
# before reuse; the historical native witness used the earlier runner hash.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$SourceRoot,[Parameter(Mandatory)][string]$PreparedRoot,
    [Parameter(Mandatory)][string]$OutputRoot,[Parameter(Mandatory)][string]$PythonExe)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell7 required.'}
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'ops/Resource-Scheduler.Core.ps1')
$output=[IO.Path]::GetFullPath($OutputRoot)
$runtime=[IO.Path]::GetFullPath((Join-Path $repo 'runtime'))+[IO.Path]::DirectorySeparatorChar
if(!$output.StartsWith($runtime,[StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $output)){throw 'Fresh output beneath this worktree runtime required.'}
for($p=[IO.DirectoryInfo]$output;$p;$p=$p.Parent){if($p.Exists -and ($p.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse output ancestry refused.'}}
$source=[IO.Path]::GetFullPath($SourceRoot);$prepared=[IO.Path]::GetFullPath($PreparedRoot)
$manifest=Get-Content -LiteralPath (Join-Path $prepared 'prepared.json') -Raw | ConvertFrom-Json
function Assert-ProbeInputs {
    if((& git -C $source rev-parse HEAD).Trim() -cne $manifest.zonetool_pin){throw 'ZoneTool pin changed.'}
    foreach($entry in $manifest.source_hashes.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path $source $entry.Name)).Hash -ine $entry.Value){throw "SDK hash changed: $($entry.Name)"}}
    foreach($entry in $manifest.generated_sha256.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path $prepared $entry.Name)).Hash -ine $entry.Value){throw "Prepared hash changed: $($entry.Name)"}}
    if((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'writer_probe.cpp')).Hash -ine $manifest.writer_sha256 -or
       (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'probe_native_abi.hpp')).Hash -ine $manifest.abi_sha256){throw 'Native writer/ABI source changed after preparation.'}
}
Assert-ProbeInputs
$vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs=@(& $vswhere -products '*' -version '[17.0,18.0)' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath)[0]
if(!$vs){throw 'Existing VS2022 C++ tools required.'}
$vcVersion=(Get-Content -LiteralPath (Join-Path $vs 'VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt') -Raw).Trim()
$vc=Join-Path $vs "VC/Tools/MSVC/$vcVersion"; $sdk='C:/Program Files (x86)/Windows Kits/10';$sdkVersion='10.0.26100.0'
$compiler=Join-Path $vc 'bin/Hostx64/x64/cl.exe'
foreach($path in @($compiler,(Join-Path $sdk "Include/$sdkVersion/um/Windows.h"),$PythonExe)){if(!(Test-Path -LiteralPath $path -PathType Leaf)){throw "Required installed tool missing: $path"}}
$records=[Collections.Generic.List[object]]::new()
$ownedJobs=[Collections.Generic.List[object]]::new()
$artifactLimit=32MB;$metadataReserve=1MB
$receipt=[ordered]@{Schema='iw7.original-probe-native-run/2';SourceCommit=(& git -C $repo rev-parse HEAD).Trim();StartedUtc=[datetime]::UtcNow.ToString('o');
    RunnerSHA256=(Get-FileHash -LiteralPath $PSCommandPath).Hash;JobSourceSHA256=(Get-FileHash (Join-Path $PSScriptRoot 'Probe-NativeJob.cs')).Hash;
    ResourceHelperSHA256=(Get-FileHash (Join-Path $repo 'ops/Resource-Scheduler.Core.ps1')).Hash;PhysicalBytes=4GB;CommitBytes=6GB;
    Compiler=$compiler;CompilerSHA256=(Get-FileHash $compiler).Hash;VCTools=$vcVersion;WindowsSdk=$sdkVersion;
    PreparedManifestSHA256=(Get-FileHash (Join-Path $prepared 'prepared.json')).Hash;Processes=$records;Status='Pending';RuntimeVerified=$false}
function Assert-ArtifactBudget([switch]$Final) {
    $total=0L
    foreach($file in Get-ChildItem -LiteralPath $output -Recurse -File){$total+=$file.Length}
    $limit=if($Final){$artifactLimit}else{$artifactLimit-$metadataReserve}
    if($total -gt $limit){throw "Native artifact budget exceeded: $total > $limit bytes."}
    $total
}
function Write-NewProbeBytes([string]$Path,[byte[]]$Bytes) {
    $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try {$stream.Write($Bytes,0,$Bytes.Length)} finally {$stream.Dispose()}
}
function Write-FinalProbeReceipts($Receipt,$ResourceStatus) {
    $Receipt.ArtifactBytesBeforeReceipts=Assert-ArtifactBudget
    $Receipt.ArtifactLimitBytes=$artifactLimit;$Receipt.FinalMetadataReserveBytes=$metadataReserve
    $encoding=[Text.UTF8Encoding]::new($false)
    $nativeBytes=$encoding.GetBytes(($Receipt | ConvertTo-Json -Depth 14))
    $resourceBytes=$encoding.GetBytes(($ResourceStatus | ConvertTo-Json -Depth 7))
    if([long]$nativeBytes.Length+$resourceBytes.Length -gt $metadataReserve){throw 'Final receipts exceed reserved metadata space; no success receipt published.'}
    $pending=Join-Path $output 'native-receipt.pending.json'
    $final=Join-Path $output 'native-receipt.json'
    $resourcePath=Join-Path $output 'resource-after.json'
    foreach($path in @($pending,$final,$resourcePath)){if(Test-Path -LiteralPath $path){throw 'Final receipt path already exists.'}}
    Write-NewProbeBytes $pending $nativeBytes
    Write-NewProbeBytes $resourcePath $resourceBytes
    # Both complete serialized receipts now count toward the cap. Renaming in
    # the same directory adds no bytes. Never publish success before this check.
    $null=Assert-ArtifactBudget -Final
    [IO.File]::Move($pending,$final)
    $null=Assert-ArtifactBudget -Final
}
function Close-ProbeReservation($OwnedJobs,$Receipt,$Lease) {
    $Receipt.LeaseReleased=$false
    foreach($owned in $OwnedJobs){
        if(!$owned.Closed){try {$owned.StopAndConfirm(5000)} catch {$Receipt.TreeCleanupError=$_.Exception.Message}}
    }
    $Receipt.AllOwnedTreesClosed=@($OwnedJobs | Where-Object { !$_.Closed }).Count -eq 0
    if(!$Receipt.AllOwnedTreesClosed){
        $Receipt.LeaseRetainedReason='Exact owned process tree closure unconfirmed.'
        throw $Receipt.LeaseRetainedReason
    }
    # The shared releaser alone does not track c1xx/other descendants by name.
    # It may run only after every exact owner proved an empty job and closed.
    Exit-IW7ResourceLease -Token $Lease.Token
    $Receipt.LeaseReleased=$true
}
function Invoke-ProbeChild([string]$Label,[string]$Image,[string[]]$Arguments,[int]$TimeoutSeconds=120) {
    $start=[Diagnostics.ProcessStartInfo]::new($Image)
    $start.WorkingDirectory=$output;$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle='Hidden'
    foreach($arg in $Arguments){$start.ArgumentList.Add($arg)}
    $start.Environment.Remove('CL')|Out-Null;$start.Environment.Remove('_CL_')|Out-Null
    $start.Environment['PATH']=(Join-Path $vc 'bin/Hostx64/x64')+';'+$env:PATH
    $start.Environment['INCLUDE']=(@((Join-Path $vc 'include'))+@('ucrt','shared','um','winrt')|ForEach-Object{if($_ -in @('ucrt','shared','um','winrt')){Join-Path $sdk "Include/$sdkVersion/$_"}else{$_}})-join ';'
    $start.Environment['LIB']=@((Join-Path $vc 'lib/x64'),(Join-Path $sdk "Lib/$sdkVersion/ucrt/x64"),(Join-Path $sdk "Lib/$sdkVersion/um/x64"))-join ';'
    $child=[IW7.AnimationProbe.NativeJob]::new()
    $ownedJobs.Add($child) # Retained even when Start or cleanup throws.
    $record=[ordered]@{Label=$Label;Image=$Image;ImageSHA256=(Get-FileHash -LiteralPath $Image).Hash;Arguments=$Arguments;StartedUtc=[datetime]::UtcNow.ToString('o')}
    $records.Add($record)
    try {
        $child.Start($start,$record.ImageSHA256,(Join-Path $output "$Label.stdout.log"),(Join-Path $output "$Label.stderr.log"))
        $record.PID=$child.PID;$record.CreatedUtc=[datetime]::FromFileTimeUtc($child.CreationFileTime).ToString('o')
        $record.KernelImage=$child.Image;$record.Priority='BelowNormal';$record.Ownership='atomic-job-at-creation'
        $timer=[Diagnostics.Stopwatch]::StartNew()
        while(!$child.TreeExited()){
            $null=Assert-ArtifactBudget
            if($timer.Elapsed.TotalSeconds -gt $TimeoutSeconds){throw "Timeout in $Label"}
            Start-Sleep -Milliseconds 100
        }
        $child.CloseConfirmed() # Root handle signaled AND job ActiveProcesses=0.
        $null=Assert-ArtifactBudget
        $record.ExitCode=$child.ExitCode;$record.ElapsedMs=$timer.ElapsedMilliseconds
        $record.TreeClosureConfirmed=$child.Closed
        Write-Output "$Label exit=$($child.ExitCode) pid=$($record.PID) elapsedMs=$($record.ElapsedMs)"
        if($child.ExitCode -ne 0){throw "$Label failed with exit $($child.ExitCode). Preserved logs: $output"}
    } finally {
        $record.PID=$child.PID;$record.CreationFileTime=$child.CreationFileTime
        try {if(!$child.Closed){$record.TerminatedByRunner=$true;$child.StopAndConfirm(5000)}} finally {
            $record.TreeClosureConfirmed=$child.Closed
            if($child.Closed){$record.ExitCode=$child.ExitCode}
        }
    }
}
$lease=Enter-IW7ResourceLease -Scope $output -Kind Build -Owner 'Original animation writer and independent readback' -PhysicalBytes 4GB -CommitBytes 6GB
$launcher=$null;$originalPriority=$null;$failure=$null
try {
    $launcher=Get-Process -Id $PID;$originalPriority=$launcher.PriorityClass;$launcher.PriorityClass='BelowNormal'
    [IO.Directory]::CreateDirectory($output)|Out-Null
    if('IW7.AnimationProbe.NativeJob' -as [type]){throw 'Fresh PowerShell process required for the reviewed job helper.'}
    Add-Type -Path (Join-Path $PSScriptRoot 'Probe-NativeJob.cs') -ErrorAction Stop
        Assert-ProbeInputs
        $receipt.AdmissionSnapshot=Get-IW7ResourceSnapshot
        $receipt.LauncherPID=$PID;$receipt.LauncherPriority=[string](Get-Process -Id $PID).PriorityClass
        $exe=Join-Path $output 'writer_probe.exe'
        $arguments=@('/nologo','/std:c++20','/EHsc','/MD','/O1','/W3',('/I'+(Join-Path $source 'src/zonetool')),('/I'+$prepared),('/I'+$PSScriptRoot),
            (Join-Path $PSScriptRoot 'writer_probe.cpp'),('/Fo'+(Join-Path $output 'writer_probe.obj')),('/Fe'+$exe),'/link','/INCREMENTAL:NO')
        Invoke-ProbeChild 'compile' $compiler $arguments
        Assert-ProbeInputs
        Invoke-ProbeChild 'emit' $exe @((Join-Path $output 'emission'),'1') 30
        $xab=Join-Path $output 'emission/xanim/paris_original_probe_bend.xab'
        if((Get-Item -LiteralPath $xab).Length -gt 64KB){throw 'XAB exceeds 64 KiB.'}
        Invoke-ProbeChild 'readback' $PythonExe @('-B',(Join-Path $PSScriptRoot 'read_probe.py'),$xab,'--expected-frequency','1') 30
        $receipt.Readback=Get-Content -LiteralPath (Join-Path $output 'readback.stdout.log') -Raw | ConvertFrom-Json
        if($receipt.Readback.status -cne 'original-probe-data-pass'){throw 'Independent reader did not pass.'}
        $receipt.XabSHA256=(Get-FileHash -LiteralPath $xab).Hash;$receipt.XabBytes=(Get-Item -LiteralPath $xab).Length
        $receipt.ExecutableSHA256=(Get-FileHash -LiteralPath $exe).Hash;$receipt.Status='NativeSerializerAndReadbackPassed'
        Assert-ProbeInputs
} catch {$failure=$_;$receipt.Status='Failed';$receipt.Error=$_.Exception.Message} finally {
    try {Close-ProbeReservation $ownedJobs $receipt $lease} catch {if(!$failure){$failure=$_};$receipt.LeaseReleaseError=$_.Exception.Message}
    if($launcher -and $null -ne $originalPriority){
        try {$launcher.PriorityClass=$originalPriority} catch {if(!$failure){$failure=$_};$receipt.PriorityRestoreError=$_.Exception.Message}
    }
    if($failure){$receipt.Status='Failed'}
    $receipt.FinishedUtc=[datetime]::UtcNow.ToString('o')
}
if(Test-Path -LiteralPath $output){
    try {Write-FinalProbeReceipts $receipt (Get-IW7ResourceStatus)} catch {if(!$failure){$failure=$_};Write-Warning "No complete final receipt publication: $($_.Exception.Message)"}
}
if($failure){throw $failure}
Write-Output "Receipt: $(Join-Path $output 'native-receipt.json')"
