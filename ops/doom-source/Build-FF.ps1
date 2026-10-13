# Separate Doom rigid wrapper: common transaction/process helpers are reused;
# original cube wrapper and its exact-count/hash allowlist remain unchanged.
param([ValidateSet('Build','Restore')][string]$Action='Build',[Parameter(Mandatory)][string]$RunRoot,
    [string]$StockToolRoot,[string]$SourceRoot,[string]$ToolProvenance,[string]$ReaderRun,[switch]$DryRun)
$ErrorActionPreference='Stop'
$ops=Split-Path $PSScriptRoot -Parent;$repo=Split-Path $ops -Parent
. "$ops/Base-Client.Core.ps1"
. "$ops/Lab-Paths.ps1"
. "$ops/Resource-Scheduler.Core.ps1"
. "$ops/Memory-Budget.ps1"
. "$PSScriptRoot/../model-lab/ModelFF.Core.ps1"
. "$PSScriptRoot/Writer.Core.ps1"
. "$PSScriptRoot/FF.Core.ps1"
if(!('IW7HudFileIdentity' -as [type])){Add-Type -Path "$ops/hud-lab/HudFileIdentity.cs"}
$RunRoot=Assert-IW7LabPath ([IO.Path]::GetFullPath($RunRoot)) (Join-Path $repo 'runtime')
$statePath=Join-Path $RunRoot 'state.local.json';$work=Join-Path $RunRoot 'work'
if($Action -eq 'Restore'){
    $state=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if($state.Schema -cne 'iw7.doom-rigid-ff-build/1' -or $state.Work -ine $work -or $state.Transaction.GameRoot -ine $work -or $state.Transaction.BackupRoot -ine (Join-Path $RunRoot 'backup')){throw 'Exact model transaction required.'}
    if($state.Restored -and $state.Transaction.Restored){return}
    if(!$state.RetainedLeaseToken){throw 'Restoration requires retained reservation; no lease bypass.'}
    Complete-ModelFFRestore $state $statePath $state.RetainedLeaseToken;return
}
if(Test-Path -LiteralPath $RunRoot){throw 'Fresh model build run required.'}
$stock=(Resolve-Path -LiteralPath $StockToolRoot).Path;$null=Assert-IW7LabPath $stock $stock
$source=Assert-IW7LabPath ((Resolve-Path -LiteralPath $SourceRoot).Path) (Join-Path $repo 'runtime')
$planPath=Join-Path $source 'doom-ff-plan.json'
if((Get-Item -LiteralPath $planPath).Length -gt 64KB){throw 'Bounded Doom FF plan required.'}
$plan=Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
$planHash=(Get-FileHash -LiteralPath $planPath).Hash
$sourceNames=@(Assert-IW7DoomFFPlan $plan)
function Assert-DoomFFImmutable {
    if((Get-FileHash -LiteralPath $planPath).Hash -cne $planHash){throw 'Doom FF plan changed after admission.'}
    Assert-IW7DoomFFSource $plan $source
    if($script:doomFFExecutionBaseline){Assert-IW7DoomWriterInputBaseline $script:doomFFExecutionBaseline}
}
$script:doomFFExecutionBaseline=$null
Assert-DoomFFImmutable
$provenance=Get-Content -LiteralPath $ToolProvenance -Raw | ConvertFrom-Json
$tool=Join-Path (Split-Path ([IO.Path]::GetFullPath($ToolProvenance)) -Parent) 'zonetool.exe'
if($provenance.SourceCommit -cne $plan.source_pin -or $provenance.Repository -cne 'https://github.com/bigmangeekf/x64-zt.git' -or
    $provenance.Status -cnotin @('TestsPassedReviewedBinary','TestsPassedReviewRequired') -or @($provenance.Tests).Count -ne 2 -or
    @($provenance.Tests | Where-Object {$_.Passed -ne $true -or $_.Name -cnotin @('filesystem_ownership_tests','sound_bank_subset_tests')}).Count -or
    @($provenance.Tests.Name | Select-Object -Unique).Count -ne 2 -or (Get-FileHash -LiteralPath $tool).Hash -ine $provenance.BinarySHA256){throw 'Pinned experimental tool source/tests/hash required.'}
$zones=@('code_pre_gfx','code_post_gfx','common','common_mp','common_cp','common_core_mp','global','global_mp','global_cp','global_core_mp','cp_zmb')
$names=@($zones | ForEach-Object {"$_.ff";"patch_$_.ff";"techsets_$_.ff"})
$inputs=@()
foreach($folder in @('main','zone')){foreach($f in @(Get-ChildItem -LiteralPath (Resolve-IW7BasePath $stock $folder) -File -Filter '*.ff')){if($f.Name -in $names){$inputs+=[pscustomobject]@{Relative=$folder+'/'+$f.Name;Source=$f.FullName;Mode='HardLink'}}}}
$inputs+=[pscustomobject]@{Relative='zone/assetfile1.pak';Source=(Resolve-IW7BasePath $stock 'zone/assetfile1.pak');Mode='HardLink'}
foreach($name in @('iw7_ship.exe','amd_ags_x64.dll','bink2w64.dll','d3dcompiler_46.dll','steam_api.dll','steam_api64.dll','Steam.dll','tlsdll.dll','main/fileSysCheck.cfg')){
    $p=Resolve-IW7BasePath $stock $name
    if(Test-Path -LiteralPath $p){$inputs+=[pscustomobject]@{Relative=$name;Source=$p;Mode='Copy'}}elseif($name -in @('iw7_ship.exe','bink2w64.dll','steam_api64.dll','main/fileSysCheck.cfg')){throw 'Required bootstrap engine/sentinel missing.'}
}
foreach($entry in $inputs){$f=Get-Item -LiteralPath $entry.Source;$null=Resolve-IW7BasePath $stock $entry.Relative
    if($entry.Mode -eq 'HardLink' -and ($f.Attributes -band [IO.FileAttributes]::ReadOnly)){throw 'Read-only stock links refused.'}
    $entry | Add-Member NoteProperty Bytes $f.Length;$entry | Add-Member NoteProperty ModifiedUtc $f.LastWriteTimeUtc.ToString('o');$entry | Add-Member NoteProperty Attributes ([int]$f.Attributes)
    $entry | Add-Member NoteProperty SourceId ([IW7HudFileIdentity]::Read($entry.Source))
}
if(!@($inputs | Where-Object Relative -eq 'main/code_pre_gfx.ff').Count){throw 'Bootstrap FF missing.'}
. "$ops/Lab-AssetProcess.ps1"
. "$ops/Agent-LabCrash.Core.ps1"
. "$ops/hud-lab/Hud-Process.ps1"
$package=Get-AppxPackage Microsoft.WinDbg;$cdb=Join-Path $package.InstallLocation 'amd64/cdb.exe'
if($package.Version -ne '1.2606.22001.0' -or (Get-FileHash -LiteralPath $cdb).Hash -cne '5F54ABAFCA3AE5638BBF807D402FABB350A64575C1DFA9FBFC7F5732DF5BEE67'){throw 'Known bounded offline diagnostics required.'}
if(!$ReaderRun){throw 'Measured Doom rigid reader run required.'}
$readerRoot=Assert-IW7LabPath ((Resolve-Path -LiteralPath $ReaderRun).Path) (Join-Path $repo 'runtime')
$readerProvenancePath=Join-Path $readerRoot 'writer-provenance.json'
if((Get-Item -LiteralPath $readerProvenancePath).Length -gt 1MB){throw 'Bounded Doom reader provenance required.'}
$r=Get-Content -LiteralPath $readerProvenancePath -Raw | ConvertFrom-Json
$reader=Join-Path $readerRoot 'doom-writer.exe'
if($r.Schema -cne 'iw7.doom-rigid-writer-build/1' -or $r.SourcePin -cne $plan.source_pin -or $r.Source.candidate_name -cne $plan.asset_name -or
    (Get-FileHash -LiteralPath $readerProvenancePath).Hash -ine $plan.writer_provenance_sha256 -or
    (Get-FileHash -LiteralPath $reader).Hash -ine $plan.reader_sha256 -or $r.WriterSHA256 -ine $plan.reader_sha256 -or
    !$r.InputSnapshotsMatch -or $r.Ready -or $r.FFBuilt -or $r.PixelsVerified){throw 'Exact measured Doom writer/reader required.'}
Assert-IW7DoomWriterManifest $r.Source
Assert-IW7DoomWriterRoundtrip $r.Source $r.Roundtrip
$baselineFiles=@([pscustomobject]@{Path=$planPath;Scope=$source;MaximumBytes=64KB},[pscustomobject]@{Path=$readerProvenancePath;Scope=$readerRoot;MaximumBytes=1MB},
    [pscustomobject]@{Path=$reader;Scope=$readerRoot;MaximumBytes=16MB},[pscustomobject]@{Path=$tool;Scope=(Split-Path $tool -Parent);MaximumBytes=64MB})
foreach($name in $sourceNames){$baselineFiles+=[pscustomobject]@{Path=(Join-Path $source $name);Scope=$source;MaximumBytes=4MB}}
$script:doomFFExecutionBaseline=New-IW7DoomWriterInputBaseline -Files $baselineFiles
Assert-DoomFFImmutable
if($DryRun){[ordered]@{Schema='iw7.doom-rigid-ff-admission/1';RunRoot=$RunRoot;Inputs=$inputs.Relative;OriginalInputs=$sourceNames;PhysicalBytes=8GB;CommitBytes=11GB;PAKs=@('zone/assetfile1.pak');CPPreload=$false;MaterialRuntimeBound=$false;Reader=$reader;Ready=$false}|ConvertTo-Json -Depth 8;return}
$lease=Enter-IW7ResourceLease -Scope $work -Kind Extract -PhysicalBytes 8GB -CommitBytes 11GB -Owner 'Doom rigid FF bootstrap/inventory/roundtrip'
$state=[ordered]@{ExecutionBaseline=$script:doomFFExecutionBaseline;Schema='iw7.doom-rigid-ff-build/1';Work=$work;Inputs=$inputs;RetainedLeaseToken=$lease.Token;Restored=$false;StockPreserved=$false;RestorationStatus='Pending';CleanupError=$null;Status='Preparing';SourcePlan=$plan;ToolSHA256=$provenance.BinarySHA256;InventoryVerified=$false;GeometryRoundtripVerified=$false;RecipientReferenceResolved=$false;SymbolsVerified=$false;Ready=$false}
$cleanup=[pscustomobject]@{Confirmed=$true};$transactionSaved=$false
try{
    [IO.Directory]::CreateDirectory($work)|Out-Null
    $mutable=@($inputs.Relative)+$sourceNames+@('zonetool.exe',"zone/$($plan.zone).ff")
    $state.Transaction=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$work;MutableFiles=$mutable;ProfileDirectory='model-unused-profile';ProfileDirectories=@()}) (Join-Path $RunRoot 'backup');$transactionSaved=$true
    Write-ModelFFState $state $statePath
    foreach($entry in $inputs){$target=Resolve-IW7BasePath $work $entry.Relative;[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
        if($entry.Mode -eq 'HardLink'){New-Item -ItemType HardLink -Path $target -Target $entry.Source|Out-Null}else{Copy-Item -LiteralPath $entry.Source -Destination $target}
        $entry | Add-Member NoteProperty TargetId ([IW7HudFileIdentity]::Read($target));if($entry.Mode -eq 'HardLink' -and $entry.TargetId -cne $entry.SourceId){throw 'Stock NTFS link differs.'}}
    foreach($name in $sourceNames){$target=Resolve-IW7BasePath $work $name;[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null;Copy-Item -LiteralPath (Join-Path $source $name) -Destination $target
        if((Get-FileHash -LiteralPath $target).Hash -ine $plan.source_files.$name){throw 'Original FF source copy changed.'}}
    Copy-Item -LiteralPath $tool -Destination (Join-Path $work 'zonetool.exe');if((Get-FileHash -LiteralPath (Join-Path $work 'zonetool.exe')).Hash -ine $provenance.BinarySHA256){throw 'Tool copy hash differs.'}
    Assert-ModelFFInputs $inputs $work
    Assert-DoomFFImmutable
    $state.Status='Building';Write-ModelFFState $state $statePath
    $state.Build=Invoke-HudBuildProcess -Work $work -RunRoot $RunRoot -LeaseToken $lease.Token -CleanupState $cleanup -Cdb $cdb -Symbols (Split-Path $ToolProvenance -Parent) -Phase hud-build -ToolArguments @('-headless','-unbuffered-io','-buildzone',$plan.zone)
    if($state.Build.ExitCode){throw 'Doom FF build failed.'}
    Assert-DoomFFImmutable
    $ff=Resolve-IW7BasePath $work "zone/$($plan.zone).ff";Copy-Item -LiteralPath $ff -Destination (Join-Path $RunRoot 'mod.ff')
    $state.FF=[ordered]@{Path='mod.ff';Bytes=(Get-Item -LiteralPath $ff).Length;SHA256=(Get-FileHash -LiteralPath $ff).Hash};$state.Status='CompiledRetained';Write-ModelFFState $state $statePath
    $state.Offline=Invoke-HudBuildProcess -Work $work -RunRoot $RunRoot -LeaseToken $lease.Token -CleanupState $cleanup -Cdb $cdb -Symbols (Split-Path $ToolProvenance -Parent) -Phase hud-offline -ToolArguments @('-headless','-unbuffered-io','-verifyzone',$plan.zone)
    Assert-DoomFFImmutable
    if($state.Offline.ExitCode){$state.Status='OfflineUnresolved';throw 'Bootstrap reference/inventory load failed; retained FF is not recipient-linked.'}
    $rows=@(Get-IW7DoomFFInventory ([IO.File]::ReadAllText($state.Offline.Stdout)) $plan);[IO.File]::WriteAllLines((Join-Path $RunRoot 'assets.csv'),[string[]]$rows)
    $state.InventoryVerified=$true;$state.Status='BootstrapInventoryVerified';Write-ModelFFState $state $statePath
    $state.Dump=Invoke-HudBuildProcess -Work $work -RunRoot $RunRoot -LeaseToken $lease.Token -CleanupState $cleanup -Cdb $cdb -Symbols (Split-Path $ToolProvenance -Parent) -Phase hud-roundtrip -ToolArguments @('-headless','-unbuffered-io','-dumpzone',$plan.zone)
    Assert-DoomFFImmutable
    if($state.Dump.ExitCode){throw 'Bootstrap model re-dump failed.'}
    $dump=Join-Path $work ("dump/"+$plan.zone)
    foreach($name in @("xmodel/$($plan.asset_name).xmb","xsurface/$($plan.asset_name)_lod0.xsb")){$p=Resolve-IW7BasePath $dump $name;$target=Join-Path $RunRoot ('roundtrip/'+$name);[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null;Copy-Item -LiteralPath $p -Destination $target}
    if($reader){
        $state.GeometryReader=Invoke-IW7LabAssetProcess -Executable $reader -ToolArguments @('--verify-existing',(Join-Path $RunRoot 'roundtrip')) -WorkingDirectory $work -LogDirectory $RunRoot -Phase model-geometry -LeaseToken $lease.Token -CleanupState $cleanup -TimeoutSeconds 30
        if($state.GeometryReader.ExitCode -or (Get-Item -LiteralPath $state.GeometryReader.Stdout).Length -gt 1MB){throw 'FF re-dump differs from original geometry/reference.'}
        $verified=[IO.File]::ReadAllText($state.GeometryReader.Stdout)|ConvertFrom-Json;Assert-DoomFFImmutable;Assert-IW7DoomWriterRoundtrip $r.Source $verified
        $verified|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $RunRoot 'geometry-roundtrip.json');$state.GeometryRoundtripVerified=$true}
}catch{
    $state.Failure=$_.Exception.Message
    if($state.Status -eq 'CompiledRetained' -and $state.Failure -match 'recipient reference unresolved|referenced asset'){$state.Status='BootstrapRecipientReferenceUnresolved'}
    elseif($state.Status -notin @('OfflineUnresolved')){$state.Status='Failed'}
    throw
}
finally{
    if($transactionSaved){Write-ModelFFState $state $statePath
        if(!$cleanup.Confirmed){$state.CleanupError='Owned tool/diagnostic termination unconfirmed; lease retained.';Write-ModelFFState $state $statePath}
        else{Complete-ModelFFRestore $state $statePath $lease.Token}}
    # A pre-transaction failure has no borrowed files or child; release normally.
    elseif($cleanup.Confirmed){Exit-IW7ResourceLease -Token $lease.Token}
}
