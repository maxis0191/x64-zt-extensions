param([Parameter(Mandatory)][string]$BuildRun,[Parameter(Mandatory)][string]$ReaderRun)
$ErrorActionPreference='Stop'
$ops=Split-Path $PSScriptRoot -Parent;$repo=Split-Path $ops -Parent
. "$ops/Base-Client.Core.ps1"
. "$ops/Lab-Paths.ps1"
. "$ops/Memory-Budget.ps1"
. "$ops/Resource-Scheduler.Core.ps1"
. "$ops/Lab-AssetProcess.ps1"
. "$PSScriptRoot/ModelFF.Core.ps1"
$run=Assert-IW7LabPath ((Resolve-Path -LiteralPath $BuildRun).Path) (Join-Path $repo 'runtime')
$readerRoot=Assert-IW7LabPath ((Resolve-Path -LiteralPath $ReaderRun).Path) (Join-Path $repo 'runtime')
$statePath=Join-Path $run 'state.local.json'
if((Get-Item -LiteralPath $statePath).Length -gt 1MB){throw 'Bounded retained build state required.'}
$state=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
if($state.Schema -cne 'iw7.model-ff-build/1' -or !$state.Restored -or !$state.StockPreserved -or $state.RestorationStatus -cne 'Confirmed' -or $state.RetainedLeaseToken -or
    !$state.InventoryVerified -or $state.Build.ExitCode -ne 0 -or $state.Offline.ExitCode -ne 0 -or $state.Dump.ExitCode -ne 0){throw 'Retained compiled/inventoried/dumped/restored FF proof required.'}
Assert-ModelFFVacant $state.Work
$ff=Resolve-IW7BasePath $run 'mod.ff'
if((Get-Item -LiteralPath $ff).Length -ne $state.FF.Bytes -or (Get-FileHash -LiteralPath $ff).Hash -ine $state.FF.SHA256){throw 'Retained FF changed.'}
$readerState=Get-Content -LiteralPath (Join-Path $readerRoot 'writer-provenance.json') -Raw|ConvertFrom-Json
$reader=Resolve-IW7BasePath $readerRoot 'model-writer.exe'
if($readerState.SourcePin -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or !$readerState.Roundtrip.read_existing_supported -or
    (Get-FileHash -LiteralPath $reader).Hash -ine $readerState.WriterSHA256){throw 'Measured existing-dump reader required.'}
$inputs=@(foreach($name in @('xmodel/paris_model_probe.xmb','xsurface/paris_model_probe_lod0.xsb')){
    $path=Resolve-IW7BasePath $run ('roundtrip/'+$name);$f=Get-Item -LiteralPath $path
    if($f.Length -gt 8192){throw 'Oversized retained original dump.'}
    [pscustomobject]@{Path=$path;Bytes=$f.Length;SHA256=(Get-FileHash -LiteralPath $path).Hash}
})
$lease=Enter-IW7ResourceLease -Scope $run -Kind Analysis -PhysicalBytes 2GB -CommitBytes 2GB -Owner 'Retained original FF semantic reader only'
$cleanup=[pscustomobject]@{Confirmed=$true}
try{
    $result=Invoke-IW7LabAssetProcess -Executable $reader -ToolArguments @('--verify-existing',(Join-Path $run 'roundtrip')) -WorkingDirectory $run -LogDirectory $run -Phase model-recovery-reader -LeaseToken $lease.Token -CleanupState $cleanup -TimeoutSeconds 30
    $verified=$null;if($result.ExitCode -eq 0){$verified=[IO.File]::ReadAllText($result.Stdout)|ConvertFrom-Json}
    foreach($entry in $inputs){if((Get-Item -LiteralPath $entry.Path).Length -ne $entry.Bytes -or (Get-FileHash -LiteralPath $entry.Path).Hash -cne $entry.SHA256){throw 'Retained reader mutated dump evidence.'}}
    $record=[ordered]@{Schema='iw7.model-retained-reader/1';OriginalBuildStatus=$state.Status;OriginalFailure=$state.Failure;FFSHA256=$state.FF.SHA256;ReaderSHA256=$readerState.WriterSHA256;Inputs=$inputs;Process=$result;Geometry=$verified;RecipientReferenceResolved=$false;PixelsVerified=$false;Ready=$false}
    $record | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath ($result.Stdout+'.evidence.json')
    if($result.ExitCode -or !$verified.geometry_roundtrip_verified){throw 'Retained geometry reader failed; separate log/evidence preserved, original state untouched.'}
    $record|ConvertTo-Json -Depth 10
}finally{if($cleanup.Confirmed){Exit-IW7ResourceLease -Token $lease.Token}else{Write-Warning 'Exact reader closure unconfirmed; reservation retained.'}}
