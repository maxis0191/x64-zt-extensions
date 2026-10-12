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
$receipt=[ordered]@{Schema='iw7.original-probe-native-run/1';SourceCommit=(& git -C $repo rev-parse HEAD).Trim();StartedUtc=[datetime]::UtcNow.ToString('o');
    ResourceHelperSHA256=(Get-FileHash (Join-Path $repo 'ops/Resource-Scheduler.Core.ps1')).Hash;PhysicalBytes=4GB;CommitBytes=6GB;
    Compiler=$compiler;CompilerSHA256=(Get-FileHash $compiler).Hash;VCTools=$vcVersion;WindowsSdk=$sdkVersion;
    PreparedManifestSHA256=(Get-FileHash (Join-Path $prepared 'prepared.json')).Hash;Processes=$records;Status='Pending';RuntimeVerified=$false}
function Assert-ArtifactBudget {
    $total=0L
    foreach($file in Get-ChildItem -LiteralPath $output -Recurse -File){$total+=$file.Length}
    if($total -gt 32MB){throw '32 MiB native artifact budget exceeded.'}
    $total
}
function Invoke-ProbeChild([string]$Label,[string]$Image,[string[]]$Arguments,[int]$TimeoutSeconds=120) {
    $start=[Diagnostics.ProcessStartInfo]::new($Image)
    $start.WorkingDirectory=$output;$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle='Hidden'
    $start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
    foreach($arg in $Arguments){$start.ArgumentList.Add($arg)}
    $start.Environment.Remove('CL')|Out-Null;$start.Environment.Remove('_CL_')|Out-Null
    $start.Environment['PATH']=(Join-Path $vc 'bin/Hostx64/x64')+';'+$env:PATH
    $start.Environment['INCLUDE']=(@((Join-Path $vc 'include'))+@('ucrt','shared','um','winrt')|ForEach-Object{if($_ -in @('ucrt','shared','um','winrt')){Join-Path $sdk "Include/$sdkVersion/$_"}else{$_}})-join ';'
    $start.Environment['LIB']=@((Join-Path $vc 'lib/x64'),(Join-Path $sdk "Lib/$sdkVersion/ucrt/x64"),(Join-Path $sdk "Lib/$sdkVersion/um/x64"))-join ';'
    $child=[Diagnostics.Process]::new();$child.StartInfo=$start
    $started=$false;$stdout=$null;$stderr=$null;$logsSaved=$false
    $record=[ordered]@{Label=$Label;Image=$Image;ImageSHA256=(Get-FileHash -LiteralPath $Image).Hash;Arguments=$Arguments;StartedUtc=[datetime]::UtcNow.ToString('o')}
    $records.Add($record)
    try {
        if(!$child.Start()){throw 'Native child failed to start.'}
        $started=$true
        # Keep the original process object/handle throughout exit-code collection.
        $null=$child.SafeHandle
        $record.PID=$child.Id;$record.CreatedUtc=$child.StartTime.ToUniversalTime().ToString('o')
        if(!$child.HasExited){$record.Priority=[string]$child.PriorityClass;if($record.Priority -ne 'BelowNormal'){throw 'Child did not inherit BelowNormal priority.'}}
        $stdout=$child.StandardOutput.ReadToEndAsync();$stderr=$child.StandardError.ReadToEndAsync()
        $timer=[Diagnostics.Stopwatch]::StartNew()
        while(!$child.WaitForExit(100)){
            $null=Assert-ArtifactBudget
            if($timer.Elapsed.TotalSeconds -gt $TimeoutSeconds){throw "Timeout in $Label"}
        }
        $child.WaitForExit();$out=$stdout.GetAwaiter().GetResult();$err=$stderr.GetAwaiter().GetResult()
        if(([Text.Encoding]::UTF8.GetByteCount($out)+[Text.Encoding]::UTF8.GetByteCount($err)+(Assert-ArtifactBudget)) -gt 32MB){throw 'Diagnostic output exceeds artifact budget.'}
        [IO.File]::WriteAllText((Join-Path $output "$Label.stdout.log"),$out)
        [IO.File]::WriteAllText((Join-Path $output "$Label.stderr.log"),$err)
        $logsSaved=$true
        $record.ExitCode=$child.ExitCode;$record.ElapsedMs=$timer.ElapsedMilliseconds
        $record.PeakWorkingSet=$child.PeakWorkingSet64
        Write-Output "$Label exit=$($child.ExitCode) pid=$($record.PID) elapsedMs=$($record.ElapsedMs)"
        if($child.ExitCode -ne 0){throw "$Label failed with exit $($child.ExitCode). Preserved logs: $output"}
    } finally {
        if($started -and !$child.HasExited){$child.Kill();$null=$child.WaitForExit(5000);$record.TerminatedByRunner=$true}
        if(!$logsSaved -and $stdout -and $stderr -and $child.HasExited){
            $out=$stdout.GetAwaiter().GetResult();$err=$stderr.GetAwaiter().GetResult()
            if(([Text.Encoding]::UTF8.GetByteCount($out)+[Text.Encoding]::UTF8.GetByteCount($err)+(Assert-ArtifactBudget)) -le 32MB){
                [IO.File]::WriteAllText((Join-Path $output "$Label.stdout.log"),$out)
                [IO.File]::WriteAllText((Join-Path $output "$Label.stderr.log"),$err)
            }
            $record.ExitCode=$child.ExitCode
        }
        $child.Dispose()
    }
}
Invoke-IW7ResourceJob -Scope $output -Kind Build -Owner 'Original animation writer and independent readback' -PhysicalBytes 4GB -CommitBytes 6GB -Body {
    [IO.Directory]::CreateDirectory($output)|Out-Null
    try {
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
    } catch {$receipt.Status='Failed';$receipt.Error=$_.Exception.Message;throw} finally {
        $receipt.FinishedUtc=[datetime]::UtcNow.ToString('o')
        try {$receipt.ArtifactBytes=Assert-ArtifactBudget} catch {$receipt.ArtifactBudgetError=$_.Exception.Message}
        $receipt | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath (Join-Path $output 'native-receipt.json') -Encoding utf8
    }
}
Get-IW7ResourceStatus | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $output 'resource-after.json') -Encoding utf8
Write-Output "Receipt: $(Join-Path $output 'native-receipt.json')"
