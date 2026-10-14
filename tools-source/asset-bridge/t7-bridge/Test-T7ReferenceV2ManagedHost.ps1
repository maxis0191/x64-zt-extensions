# A real fresh bundled NoExit host exercises only argument validation.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$tempBase=[IO.Path]::GetFullPath([IO.Path]::GetTempPath());$root=Join-Path $tempBase ('t7-ref-v2-managed-host-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
$childFile=Join-Path $root 'host-fixture.ps1';$proofFile=Join-Path $root 'proof.json'
$profile=(Join-Path $PSScriptRoot 'T7PrepatchReferenceV2.Profile.ps1').Replace("'","''")
$child=@'
param([string]$PlanPath,[string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. '__PROFILE__'
$process=[Diagnostics.Process]::GetCurrentProcess()
$image=$process.MainModule.FileName;$entry=[Reflection.Assembly]::GetEntryAssembly().Location;$actual=@([Environment]::GetCommandLineArgs())
$plan=[pscustomobject]@{HostImage=$image;Runner=$PSCommandPath}
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body){$caught=$false;try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match 'V2') 'Unexpected refusal'};Check $caught 'Expected argument refusal'}
Assert-T7RefV2HostArguments $plan $PlanPath $PlanSHA256 $actual $image $entry;$script:checks++
Check ($actual[0] -ceq $entry -and [IO.Path]::GetFileName($entry) -ceq 'pwsh.dll') 'Managed apphost entry was not observed'
foreach($i in 1..10){$bad=@($actual);$bad[$i]='changed';Refuses {Assert-T7RefV2HostArguments $plan $PlanPath $PlanSHA256 $bad $image $entry}}
$bad=@($actual);$bad[0]=Join-Path ([IO.Path]::GetDirectoryName($image)) 'foreign.dll';Refuses {Assert-T7RefV2HostArguments $plan $PlanPath $PlanSHA256 $bad $image $entry}
Refuses {Assert-T7RefV2HostArguments $plan $PlanPath $PlanSHA256 $actual (Join-Path $env:TEMP 'foreign.exe') $entry}
Refuses {Assert-T7RefV2HostArguments $plan $PlanPath $PlanSHA256 $actual $image (Join-Path $env:TEMP 'pwsh.dll')}
Refuses {Assert-T7RefV2HostArguments $plan $PlanPath $PlanSHA256 $actual @($image) $entry}
Refuses {Assert-T7RefV2HostArguments $plan $PlanPath $PlanSHA256 $actual $image @($entry)}
$bad=@($actual);$bad[5]=@($actual[5]);Refuses {Assert-T7RefV2HostArguments $plan $PlanPath $PlanSHA256 $bad $image $entry}
$proof=[ordered]@{Schema='iw7.t7-reference-v2-real-managed-host-test/2';Checks=$script:checks;Status='Passed';HostPID=$PID;HostCreatedUtc=$process.StartTime.ToUniversalTime().ToString('o');PhysicalImage=$image;EntryAssembly=$entry;ActualArguments=$actual;NativeJobTypeLoaded=$null -ne ('IW7.AnimationProbe.NativeJob' -as [type]);MemoryTypeLoaded=$null -ne ('IW7ResourceMemoryV1' -as [type]);NativeExecuted=$false;LeaseAcquired=$false;OpaqueInputsRead=$false}
[IO.File]::WriteAllText($PlanPath,($proof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
'Source-only host argument controls passed.'
'__HOST_FIXTURE_DONE__'
'@.Replace('__PROFILE__',$profile)
[IO.File]::WriteAllText($childFile,$child,[Text.UTF8Encoding]::new($false))
$image=[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
$start=[Diagnostics.ProcessStartInfo]::new($image);$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.RedirectStandardInput=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
foreach($value in @('-NoLogo','-NoProfile','-NoExit','-File',$childFile,'-PlanPath',$proofFile,'-PlanSHA256',('a'*64),'-Run')){$start.ArgumentList.Add($value)}
$process=[Diagnostics.Process]::new();$process.StartInfo=$start
try{
    if(!$process.Start()){throw 'Fresh host did not start'}
    $originalPID=$process.Id;$originalCreation=$process.StartTime.ToUniversalTime().ToString('o')
    $stdout=$process.StandardOutput.ReadToEndAsync();$stderr=$process.StandardError.ReadToEndAsync()
    $process.StandardInput.WriteLine('exit 0');$process.StandardInput.Flush()
    if(!$process.WaitForExit(20000)){throw 'Own argument-test host deadline exceeded'}
    $out=$stdout.GetAwaiter().GetResult();$err=$stderr.GetAwaiter().GetResult()
    if($process.ExitCode -ne 0 -or $err -or !(Test-Path -LiteralPath $proofFile)){throw ('Real argument validation failed: '+$err)}
    $proof=Get-Content -LiteralPath $proofFile -Raw|ConvertFrom-Json
    if($proof.Status -cne 'Passed' -or $proof.NativeJobTypeLoaded -or $proof.MemoryTypeLoaded -or $proof.HostPID -ne $originalPID){throw 'Source-only host proof differs'}
    [ordered]@{Schema=$proof.Schema;Checks=$proof.Checks;Status='Passed';OriginalHostPID=$originalPID;OriginalHostCreatedUtc=$originalCreation;ActualHostExitCode=$process.ExitCode;ActualHasExited=$process.HasExited;ManagedArgv0=$proof.ActualArguments[0];PhysicalImage=$proof.PhysicalImage;EntryAssembly=$proof.EntryAssembly;NativeExecuted=$false;LeaseAcquired=$false;OpaqueInputsRead=$false}|ConvertTo-Json
}finally{
    if($process.Id -and !$process.HasExited){$process.Kill();$process.WaitForExit()}
    $process.Dispose();$resolved=[IO.Path]::GetFullPath($root)
    if(!$resolved.StartsWith($tempBase,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-ref-v2-managed-host-[0-9a-f]{32}$'){throw 'Refuse unverified fixture cleanup'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
