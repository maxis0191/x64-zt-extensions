param([ValidateSet('Build','Restore')][string]$Action='Build',[Parameter(Mandatory)][string]$RunRoot,
    [string]$StockToolRoot,[string]$SourceRoot,[string]$ToolProvenance,[string]$ReaderRun,[string]$Python='python',
    [string]$CandidateRoot,[string]$CandidateArtifactSHA256,[string]$NativeJobAssembly,
    [string]$StockBindingPlan,[string]$StockBindingPlanSHA256,[switch]$DryRun)
$ErrorActionPreference='Stop'
$ops=Split-Path $PSScriptRoot -Parent;$repo=Split-Path $ops -Parent
. "$ops/Base-Client.Core.ps1"
. "$ops/Lab-Paths.ps1"
. "$ops/Resource-Scheduler.Core.ps1"
. "$ops/Memory-Budget.ps1"
. "$PSScriptRoot/ModelFF.Core.ps1"
if(!('IW7HudFileIdentity' -as [type])){Add-Type -Path "$ops/hud-lab/HudFileIdentity.cs"}
$RunRoot=Assert-IW7LabPath ([IO.Path]::GetFullPath($RunRoot)) (Join-Path $repo 'runtime')
$statePath=Join-Path $RunRoot 'state.local.json';$work=Join-Path $RunRoot 'work'
if($Action -eq 'Restore'){
    $state=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if($state.Schema -cne 'iw7.model-ff-build/1' -or $state.Work -ine $work -or $state.Transaction.GameRoot -ine $work -or $state.Transaction.BackupRoot -ine (Join-Path $RunRoot 'backup')){throw 'Exact model transaction required.'}
    if($state.Restored -and $state.Transaction.Restored){return}
    if(!$state.RetainedLeaseToken){throw 'Restoration requires retained reservation; no lease bypass.'}
    Complete-ModelFFRestore $state $statePath $state.RetainedLeaseToken;return
}
if(Test-Path -LiteralPath $RunRoot){throw 'Fresh model build run required.'}
$stock=(Resolve-Path -LiteralPath $StockToolRoot).Path;$null=Assert-IW7LabPath $stock $stock
$source=Assert-IW7LabPath ((Resolve-Path -LiteralPath $SourceRoot).Path) (Join-Path $repo 'runtime')
$planPath=Resolve-IW7BasePath $source 'model-ff-plan.json'
if((Get-Item -LiteralPath $planPath).Length -gt 1MB){throw 'Bounded model FF preparation required.'}
$plan=Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
$sourceNames=@(Get-ModelFFSourceNames $plan)
$profile='geometry_profile' -cin $plan.PSObject.Properties.Name
$arena=$profile -and $plan.geometry_profile -ceq 'iw7-original-arena-rigid-v1'
$authored=$profile -and $plan.geometry_profile -ceq 'iw7-authored-rigid-v1'
$rigid=$profile -and !$arena -and !$authored
$planVersion=if($authored){3}elseif($rigid){Get-ModelFFRigidVersion $plan}else{1}
if($planVersion -eq 1 -and (Get-Item -LiteralPath $planPath).Length -gt 64KB){throw 'Legacy model FF preparation exceeds bound.'}
$modelName=if($rigid -or $arena -or $authored){$plan.model_name}else{'paris_model_probe'}
$meshName=if($rigid -or $arena -or $authored){$plan.mesh_name}else{'paris_model_probe_lod0'}
$zoneName=if($authored){$plan.zone}else{'paris_model_probe'}
$artifactNames=@($sourceNames[0],$sourceNames[1])
if($plan.schema -cne "iw7.model-ff-plan/$planVersion" -or $plan.source_pin -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or $plan.ff_built -or $plan.ready -or
    (!$authored -and @($plan.source_files.PSObject.Properties).Count -ne 5) -or @($sourceNames | Where-Object {$_ -cnotin $plan.source_files.PSObject.Properties.Name}).Count){throw 'Pinned exact original FF source preparation required.'}
if($authored){
    if(!$ReaderRun -or !$CandidateRoot){throw 'Authored FF requires its measured native reader and strict community candidate.'}
    $Python=(Get-Command $Python -CommandType Application -ErrorAction Stop|Select-Object -First 1).Source
    & $Python -B -S "$PSScriptRoot/prepare_ff.py" --verify-authored-stage $source | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Authored source/material closure differs.'}
}elseif($arena){
    if($ReaderRun){throw 'Original arena uses its independent arena reader, not the cube native reader.'}
    $Python=(Get-Command $Python -CommandType Application -ErrorAction Stop|Select-Object -First 1).Source
    $arenaReader=Join-Path $repo 'tools-source/asset-bridge/world/original-arena/model_lab.py'
    $validation=& $Python -B -S $arenaReader verify-stage --source $source
    if($LASTEXITCODE -ne 0){throw 'Original arena source/byte validation failed.'}
}elseif($rigid){
    if($ReaderRun){throw 'Cube native reader is not the resident rigid reader.'}
    $Python=(Get-Command $Python -CommandType Application -ErrorAction Stop|Select-Object -First 1).Source
    $validation=& $Python -B -S "$PSScriptRoot/rigid_export.py" verify-stage --source $source
    if($LASTEXITCODE -ne 0){throw 'Resident derivation failed independent source/byte validation.'}
}else{
    if($plan.candidate_variable -cne 'lodInfo[0].dist'){throw 'Exact distance candidate preparation required.'}
    Assert-ModelFFDistanceCandidate $plan
}
foreach($name in $sourceNames){$p=Resolve-IW7BasePath $source $name;if((Get-FileHash -LiteralPath $p).Hash -ine $plan.source_files.$name){throw 'Original FF preparation changed.'}}
if($CandidateRoot){
    if($ToolProvenance -or $CandidateArtifactSHA256 -cnotmatch '^[a-fA-F0-9]{64}$'){throw 'One explicit community candidate artifact required.'}
    . "$repo/sdk/modding/BeaconFF.Core.ps1"
    # LIGHT reads only bounded producer metadata for both arena and resident
    # candidates. Full EXE/tlog qualification runs under the Extract lease.
    $candidateMetadata=Resolve-IW7BasePath $CandidateRoot 'build-artifact.local.json'
    if((Get-Item -LiteralPath $candidateMetadata).Length -gt 64KB){throw 'Bounded candidate metadata required.'}
    Assert-BeaconHash $candidateMetadata $CandidateArtifactSHA256
    $candidateArtifact=Read-BeaconJson $candidateMetadata 65536
    $tool=Resolve-IW7BasePath $CandidateRoot 'bin/zonetool-community.exe'
    if($candidateArtifact.schema -cne 'iw7.zonetool-community-candidate/1' -or $candidateArtifact.executable.path -ine $tool -or
       $candidateArtifact.executable.sha256 -isnot [string] -or $candidateArtifact.executable.sha256 -cnotmatch '^[a-fA-F0-9]{64}$'){
        throw 'Explicit bounded candidate producer metadata required.'
    }
    if($arena -and $candidateArtifact.executable.sha256 -cne 'e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04'){
        throw 'Explicit retained e7 original-arena candidate metadata required.'
    }
    $provenance=[pscustomobject]@{BinarySHA256=$candidateArtifact.executable.sha256}
    $symbols=Join-Path $CandidateRoot 'bin'
    $buildArguments=@('-headless','-unbuffered-io','-strict-content-sources','-buildzone',$zoneName)
    $offlineArguments=@('-headless','-unbuffered-io','-strict-content-sources','-verifyzone',$zoneName)
    $dumpArguments=@('-headless','-unbuffered-io','-strict-content-sources','-dumpzone',$zoneName)
    if($arena -and !$NativeJobAssembly){throw 'Original arena candidate requires the retained original NativeJob assembly.'}
}else{
    if(!$ToolProvenance -or $CandidateArtifactSHA256){throw 'Existing tool provenance or explicit community candidate required.'}
    $provenance=Get-Content -LiteralPath $ToolProvenance -Raw | ConvertFrom-Json
    $tool=Join-Path (Split-Path ([IO.Path]::GetFullPath($ToolProvenance)) -Parent) 'zonetool.exe'
    if($provenance.SourceCommit -cne $plan.source_pin -or $provenance.Repository -cne 'https://github.com/bigmangeekf/x64-zt.git' -or
    $provenance.Status -cnotin @('TestsPassedReviewedBinary','TestsPassedReviewRequired') -or @($provenance.Tests).Count -ne 2 -or
    @($provenance.Tests | Where-Object {$_.Passed -ne $true -or $_.Name -cnotin @('filesystem_ownership_tests','sound_bank_subset_tests')}).Count -or
        @($provenance.Tests.Name | Select-Object -Unique).Count -ne 2 -or (Get-FileHash -LiteralPath $tool).Hash -ine $provenance.BinarySHA256){throw 'Pinned experimental tool source/tests/hash required.'}
    $symbols=Split-Path $ToolProvenance -Parent
    $buildArguments=@('-headless','-unbuffered-io','-buildzone','paris_model_probe')
    $offlineArguments=@('-headless','-unbuffered-io','-verifyzone','paris_model_probe')
    $dumpArguments=@('-headless','-unbuffered-io','-dumpzone','paris_model_probe')
}
$zones=@('code_pre_gfx','code_post_gfx','common','common_mp','common_cp','common_core_mp','global','global_mp','global_cp','global_core_mp','cp_zmb')
$names=@($zones | ForEach-Object {"$_.ff";"patch_$_.ff";"techsets_$_.ff"})
$inputs=@()
$renderOnlyStock=$rigid -and $plan.geometry_profile -ceq 't7-iw7-selected-streamed-render-only-v2'
if($StockBindingPlan){
    if((!$arena -and !$renderOnlyStock) -or !$CandidateRoot -or $StockBindingPlanSHA256 -cnotmatch '^[a-fA-F0-9]{64}$' -or
        (Get-Item -LiteralPath $StockBindingPlan).Length -gt 1MB -or (Get-FileHash -LiteralPath $StockBindingPlan).Hash -ine $StockBindingPlanSHA256){throw 'Explicit bounded original-arena stock binding required.'}
    $boundStock=Get-Content -LiteralPath $StockBindingPlan -Raw|ConvertFrom-Json
    $inputs=@($boundStock.stock_binding.inputs)
    if($inputs.Count -ne 72 -or @($inputs|Where-Object {$_.Relative -eq 'main/fileSysCheck.cfg' -and $_.Mode -ceq 'Copy'}).Count -ne 1){throw 'Existing 72-input aliases and independent copied sentinel required.'}
    . "$repo/tools-source/asset-bridge/common/StockBinding.Core.ps1"
}else{
if($StockBindingPlanSHA256){throw 'Stock binding digest requires its explicit plan.'}
foreach($folder in @('main','zone')){foreach($f in @(Get-ChildItem -LiteralPath (Resolve-IW7BasePath $stock $folder) -File -Filter '*.ff')){if($f.Name -in $names){$inputs+=[pscustomobject]@{Relative=$folder+'/'+$f.Name;Source=$f.FullName;Mode='HardLink'}}}}
$inputs+=[pscustomobject]@{Relative='zone/assetfile1.pak';Source=(Resolve-IW7BasePath $stock 'zone/assetfile1.pak');Mode='HardLink'}
foreach($name in @('iw7_ship.exe','amd_ags_x64.dll','bink2w64.dll','d3dcompiler_46.dll','steam_api.dll','steam_api64.dll','Steam.dll','tlsdll.dll','main/fileSysCheck.cfg')){
    $p=Resolve-IW7BasePath $stock $name
    if(Test-Path -LiteralPath $p){$inputs+=[pscustomobject]@{Relative=$name;Source=$p;Mode='Copy'}}elseif($name -in @('iw7_ship.exe','bink2w64.dll','steam_api64.dll','main/fileSysCheck.cfg')){throw 'Required bootstrap engine/sentinel missing.'}
}
}
foreach($entry in $inputs){$f=Get-Item -LiteralPath $entry.Source;$null=Resolve-IW7BasePath $stock $entry.Relative
    if($StockBindingPlan){
        if($f.Length -ne $entry.Bytes -or $f.LastWriteTimeUtc.Ticks -ne ([datetimeoffset]$entry.ModifiedUtc).UtcDateTime.Ticks -or [int]$f.Attributes -ne $entry.Attributes -or $entry.Mode -cnotin @('Copy','HardLink')){throw 'Observed stock metadata/mode changed.'}
        $id=[IW7HudFileIdentity]::Read($entry.Source);Assert-FFStockIdentity $entry $id
        $entry|Add-Member NoteProperty SourceId $id -Force
        continue
    }
    if($entry.Mode -eq 'HardLink' -and ($f.Attributes -band [IO.FileAttributes]::ReadOnly)){throw 'Read-only stock links refused.'}
    $entry | Add-Member NoteProperty Bytes $f.Length;$entry | Add-Member NoteProperty ModifiedUtc $f.LastWriteTimeUtc.ToString('o');$entry | Add-Member NoteProperty Attributes ([int]$f.Attributes)
    $entry | Add-Member NoteProperty SourceId ([IW7HudFileIdentity]::Read($entry.Source))
}
if(!@($inputs | Where-Object Relative -eq 'main/code_pre_gfx.ff').Count){throw 'Bootstrap FF missing.'}
. "$ops/Lab-AssetProcess.ps1"
. "$ops/Agent-LabCrash.Core.ps1"
. "$ops/hud-lab/Hud-Process.ps1"
$cdb=$null
if(!$CandidateRoot -or !$arena){
    $package=Get-AppxPackage Microsoft.WinDbg;$cdb=Join-Path $package.InstallLocation 'amd64/cdb.exe'
    if($package.Version -ne '1.2606.22001.0' -or
       (!$CandidateRoot -and (Get-FileHash -LiteralPath $cdb).Hash -cne '5F54ABAFCA3AE5638BBF807D402FABB350A64575C1DFA9FBFC7F5732DF5BEE67')){throw 'Known bounded offline diagnostics required.'}
}
$reader=$null
if($ReaderRun){$readerRoot=Assert-IW7LabPath ((Resolve-Path -LiteralPath $ReaderRun).Path) (Join-Path $repo 'runtime');$readerProvenance=Join-Path $readerRoot 'writer-provenance.json'
    if((Get-Item -LiteralPath $readerProvenance).Length -gt 512KB){throw 'Bounded native reader provenance required.'}
    $r=Get-Content -LiteralPath $readerProvenance -Raw | ConvertFrom-Json
    $reader=Join-Path $readerRoot 'model-writer.exe';if($r.SourcePin -cne $plan.source_pin -or !$r.Roundtrip.read_existing_supported -or (!$authored -and (Get-FileHash -LiteralPath $reader).Hash -ine $r.WriterSHA256)){throw 'Measured original reader with existing-dump mode required.'}
    if($authored -and ((Get-FileHash -LiteralPath $readerProvenance).Hash -ine $plan.writer_provenance_sha256 -or
        $r.WriterSHA256 -ine $plan.writer_sha256 -or $r.Source.geometry_profile -cne 'iw7-authored-rigid-v1' -or
        $r.Source.geometry_source_sha256 -ine $plan.geometry_source_sha256)){throw 'Authored native reader is not bound to source geometry.'}
    if($r.Source.candidate_variable -cne 'lodInfo[0].dist'){throw 'Exact distance candidate reader required.'}
    Assert-ModelFFDistanceCandidate $r.Source
    Assert-ModelFFDistanceCandidate $r.Roundtrip}
if($DryRun){[ordered]@{Schema='iw7.model-ff-admission/1';RunRoot=$RunRoot;Inputs=$inputs.Relative;OriginalInputs=$sourceNames;PhysicalBytes=8GB;CommitBytes=11GB;PAKs=@('zone/assetfile1.pak');CPPreload=$false;MaterialRuntimeBound=$false;Reader=$reader;Ready=$false}|ConvertTo-Json -Depth 8;return}
$lease=Enter-IW7ResourceLease -Scope $work -Kind Extract -PhysicalBytes 8GB -CommitBytes 11GB -Owner 'Original model FF bootstrap/inventory/roundtrip'
$state=[ordered]@{Schema='iw7.model-ff-build/1';Work=$work;Inputs=$inputs;RetainedLeaseToken=$lease.Token;Restored=$false;StockPreserved=$false;RestorationStatus='Pending';CleanupError=$null;Status='Preparing';SourcePlan=$plan;ToolSHA256=$provenance.BinarySHA256;InventoryVerified=$false;GeometryRoundtripVerified=$false;RecipientReferenceResolved=$false;SymbolsVerified=$false;Ready=$false}
if($rigid -or $arena -or $authored){$state.SourcePlanSHA256=(Get-FileHash -LiteralPath (Join-Path $source 'model-ff-plan.json')).Hash}
$cleanup=[pscustomobject]@{Confirmed=$true};$transactionSaved=$false
$originalContext=$null
$stockGuards=[Collections.Generic.List[IDisposable]]::new()
function Invoke-ModelFFTool([string]$Phase,[string[]]$Arguments) {
    if($originalContext){
        try{return Invoke-OriginalArenaTool $originalContext (Join-Path $work 'zonetool.exe') $provenance.BinarySHA256 $Arguments $work $RunRoot $Phase $inputs}
        finally{$cleanup.Confirmed=$originalContext.Closed}
    }
    Invoke-HudBuildProcess -Work $work -RunRoot $RunRoot -LeaseToken $lease.Token -CleanupState $cleanup -Cdb $cdb -Symbols $symbols -Phase $Phase -ToolArguments $Arguments
}
try{
    if($authored -and (Get-FileHash -LiteralPath $reader).Hash -ine $plan.writer_sha256){throw 'Admitted authored native reader changed.'}
    if($CandidateRoot){
        $candidate=Assert-BeaconCandidate $CandidateRoot $CandidateArtifactSHA256
        if($candidate.Path -ine $tool -or $candidate.SHA256 -ine $provenance.BinarySHA256){throw 'Admitted candidate differs from planned producer metadata.'}
        $state.CandidateQualifiedUnderLease=$true
    }
    if($CandidateRoot -and !$arena -and (Get-FileHash -LiteralPath $cdb).Hash -cne '5F54ABAFCA3AE5638BBF807D402FABB350A64575C1DFA9FBFC7F5732DF5BEE67'){
        throw 'Known bounded offline diagnostics required.'
    }
    if($StockBindingPlan){
        foreach($entry in $inputs){$stockGuards.Add([IO.File]::Open($entry.Source,'Open','Read','Read'))}
        Assert-FFStockContent $inputs
        $state.StockBindingPlanSHA256=$StockBindingPlanSHA256
        $state.StockBindingProfile=if($renderOnlyStock){'existing-72-t7-render-only-v2'}else{'existing-72-original-arena'}
    }
    if($CandidateRoot -and $arena){
        $package=Get-Content -LiteralPath (Join-Path $repo 'source-workspace.json') -Raw|ConvertFrom-Json
        if($package.revisions.'iw7-mod-components' -cne '2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1'){throw 'Current TelemetryOnly native provider required.'}
        if('IW7.AnimationProbe.NativeJob' -as [type]){throw 'Fresh PowerShell host required for the original arena owner.'}
        $assembly=Assert-IW7LabPath ((Resolve-Path -LiteralPath $NativeJobAssembly).Path) ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($NativeJobAssembly)))
        $ownerSHA='5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8'
        if((Get-FileHash -LiteralPath $assembly).Hash -ine $ownerSHA){throw 'Retained original NativeJob assembly differs.'}
        . "$repo/tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1"
        . "$repo/tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1"
        . "$repo/tools-source/asset-bridge/world/original-arena/OriginalArena.Process.ps1"
        [Reflection.Assembly]::LoadFrom($assembly)|Out-Null
        $originalContext=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$lease;Work=$work}
        $state.OriginalOwner=[ordered]@{AssemblySHA256=$ownerSHA;SourceWorkspaceSHA256=(Get-FileHash -LiteralPath (Join-Path $repo 'source-workspace.json')).Hash;NativePolicyRevision=$package.revisions.'iw7-mod-components';Policy='H1 original root/job, TelemetryOnly'}
    }
    [IO.Directory]::CreateDirectory($work)|Out-Null
    $mutable=@($inputs.Relative)+$sourceNames+@('zonetool.exe',('zone/'+$zoneName+'.ff'))
    $state.Transaction=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$work;MutableFiles=$mutable;ProfileDirectory='model-unused-profile';ProfileDirectories=@()}) (Join-Path $RunRoot 'backup');$transactionSaved=$true
    Write-ModelFFState $state $statePath
    foreach($entry in $inputs){$target=Resolve-IW7BasePath $work $entry.Relative;[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
        if($entry.Mode -eq 'HardLink'){New-Item -ItemType HardLink -Path $target -Target $entry.Source|Out-Null}else{Copy-Item -LiteralPath $entry.Source -Destination $target}
        $entry | Add-Member NoteProperty TargetId ([IW7HudFileIdentity]::Read($target));if($entry.Mode -eq 'HardLink' -and $entry.TargetId -cne $entry.SourceId){throw 'Stock NTFS link differs.'}}
    foreach($name in $sourceNames){$target=Resolve-IW7BasePath $work $name;[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null;Copy-Item -LiteralPath (Join-Path $source $name) -Destination $target
        if((Get-FileHash -LiteralPath $target).Hash -ine $plan.source_files.$name){throw 'Original FF source copy changed.'}}
    Copy-Item -LiteralPath $tool -Destination (Join-Path $work 'zonetool.exe');if((Get-FileHash -LiteralPath (Join-Path $work 'zonetool.exe')).Hash -ine $provenance.BinarySHA256){throw 'Tool copy hash differs.'}
    Assert-ModelFFInputs $inputs $work
    $state.Status='Building';Write-ModelFFState $state $statePath
    $state.Build=Invoke-ModelFFTool hud-build $buildArguments
    if($state.Build.ExitCode){throw 'Model FF build failed.'}
    $ff=Resolve-IW7BasePath $work ('zone/'+$zoneName+'.ff');Copy-Item -LiteralPath $ff -Destination (Join-Path $RunRoot 'mod.ff')
    $state.FF=[ordered]@{Path='mod.ff';Bytes=(Get-Item -LiteralPath $ff).Length;SHA256=(Get-FileHash -LiteralPath $ff).Hash};$state.Status='CompiledRetained';Write-ModelFFState $state $statePath
    $state.Offline=Invoke-ModelFFTool hud-offline $offlineArguments
    if($state.Offline.ExitCode){$state.Status='OfflineUnresolved';throw 'Bootstrap reference/inventory load failed; retained FF is not recipient-linked.'}
    $materials=if($rigid -or $arena -or $authored){@(Get-ModelFFMaterials $plan)}else{@('mopw/character_park_clown_zombie_shoes')}
    $inventoryPlan=if($authored){$plan}else{$null}
    $rows=@(Get-ModelFFInventory ([IO.File]::ReadAllText($state.Offline.Stdout)) $modelName $meshName $materials -AuthoredPlan $inventoryPlan);[IO.File]::WriteAllLines((Join-Path $RunRoot 'assets.csv'),[string[]]$rows)
    $state.InventoryVerified=$true;$state.Status='BootstrapInventoryVerified';Write-ModelFFState $state $statePath
    $state.Dump=Invoke-ModelFFTool hud-roundtrip $dumpArguments
    if($state.Dump.ExitCode){throw 'Bootstrap model re-dump failed.'}
    $dump=Join-Path $work ('dump/'+$zoneName)
    $dumpNames=if($authored){@($plan.dump_files)}else{$artifactNames}
    foreach($name in $dumpNames){$p=Resolve-IW7BasePath $dump $name;$target=Join-Path $RunRoot ('roundtrip/'+$name);[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null;Copy-Item -LiteralPath $p -Destination $target}
    if($rigid -or $arena){
        $geometryReader=if($arena){$arenaReader}else{"$PSScriptRoot/rigid_export.py"}
        $readerArguments=@('-B','-S',$geometryReader,'verify-dump','--source',$source,'--dump',(Join-Path $RunRoot 'roundtrip'),'--ff',(Join-Path $RunRoot 'mod.ff'))
        if($originalContext){
            try{$state.GeometryReader=Invoke-OriginalArenaTool $originalContext $Python (Get-FileHash -LiteralPath $Python).Hash $readerArguments $repo $RunRoot model-rigid-geometry $inputs 30}
            finally{$cleanup.Confirmed=$originalContext.Closed}
        }else{$state.GeometryReader=Invoke-IW7LabAssetProcess -Executable $Python -ToolArguments $readerArguments -WorkingDirectory $repo -LogDirectory $RunRoot -Phase model-rigid-geometry -LeaseToken $lease.Token -CleanupState $cleanup -TimeoutSeconds 30}
        $version=if($arena){1}else{Get-ModelFFRigidVersion $plan};$metadataLimit=if($version -eq 2){1MB}else{64KB}
        if($state.GeometryReader.ExitCode -ne 0 -or (Get-Item -LiteralPath $state.GeometryReader.Stdout).Length -gt $metadataLimit){throw 'Resident rigid FF readback failed.'}
        $verified=[IO.File]::ReadAllText($state.GeometryReader.Stdout)|ConvertFrom-Json
        if($arena){Assert-ModelFFOriginalArenaGeometry $verified}else{Assert-ModelFFRigidGeometry $verified}
        $schema=if($arena){'iw7.model-original-arena-roundtrip/1'}else{"iw7.model-rigid-roundtrip/$version"}
        if($verified.schema -cne $schema -or $verified.geometry_profile -cne $plan.geometry_profile -or
            $verified.geometry_roundtrip_verified -ne $true -or $verified.ready -ne $false -or
            $verified.ff.sha256 -ine $state.FF.SHA256 -or $verified.source_plan_sha256 -ine $state.SourcePlanSHA256){throw 'Resident readback receipt binding failed.'}
        Copy-Item -LiteralPath $state.GeometryReader.Stdout -Destination (Join-Path $RunRoot 'geometry-roundtrip.json')
        $state.GeometryEvidenceSHA256=(Get-FileHash -LiteralPath (Join-Path $RunRoot 'geometry-roundtrip.json')).Hash
        $state.GeometryRoundtripVerified=$true
    }
    if($reader){
        $state.GeometryReader=Invoke-IW7LabAssetProcess -Executable $reader -ToolArguments @('--verify-existing',(Join-Path $RunRoot 'roundtrip')) -WorkingDirectory $work -LogDirectory $RunRoot -Phase model-geometry -LeaseToken $lease.Token -CleanupState $cleanup -TimeoutSeconds 30
        if($state.GeometryReader.ExitCode -or (Get-Item -LiteralPath $state.GeometryReader.Stdout).Length -gt 1MB){throw 'FF re-dump differs from original geometry/reference.'}
        $verified=[IO.File]::ReadAllText($state.GeometryReader.Stdout)|ConvertFrom-Json;if(!$verified.geometry_roundtrip_verified -or $verified.ready){throw 'Original geometry reader gate failed.'}
        Assert-ModelFFDistanceCandidate $verified
        if($authored){
            if($verified.schema -cne 'iw7.model-roundtrip/1' -or $verified.geometry_roundtrip_verified -isnot [bool] -or !$verified.geometry_roundtrip_verified -or
                $verified.physics_serialized -isnot [bool] -or $verified.physics_serialized -or $verified.iw7_normal_encoding_verified -isnot [bool] -or $verified.iw7_normal_encoding_verified){throw 'Authored FF native reader qualification differs.'}
            foreach($field in @('geometry_profile','namespace','zone','model_name','mesh_name','material_reference')){
                if($verified.$field -cne $plan.$field){throw 'Authored FF geometry readback identity differs.'}
            }
            if($verified.vertices -ne $plan.selected_counts.vertices -or $verified.triangles -ne $plan.selected_counts.triangles){throw 'Authored FF geometry readback counts differ.'}
            $verified | Add-Member NoteProperty source_plan_sha256 $state.SourcePlanSHA256
            $verified | Add-Member NoteProperty ff ([pscustomobject]@{bytes=$state.FF.Bytes;sha256=$state.FF.SHA256})
            $dumpedArtifacts=@(foreach($name in $artifactNames){
                $path=Resolve-IW7BasePath (Join-Path $RunRoot 'roundtrip') $name
                [pscustomobject]@{path=$name;bytes=(Get-Item -LiteralPath $path).Length;sha256=(Get-FileHash -LiteralPath $path).Hash}
            })
            $verified | Add-Member NoteProperty dumped_artifacts $dumpedArtifacts
        }
        $verified|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $RunRoot 'geometry-roundtrip.json');$state.GeometryRoundtripVerified=$true
        if($authored){$state.GeometryEvidenceSHA256=(Get-FileHash -LiteralPath (Join-Path $RunRoot 'geometry-roundtrip.json')).Hash}}
    if($authored){
        $argsSurface=@('-B','-S',"$PSScriptRoot/prepare_ff.py",'--verify-authored-dump',$source,'--dump',(Join-Path $RunRoot 'roundtrip'),'--ff',(Join-Path $RunRoot 'mod.ff'))
        $state.SurfaceReader=Invoke-IW7LabAssetProcess -Executable $Python -ToolArguments $argsSurface -WorkingDirectory $repo -LogDirectory $RunRoot -Phase model-authored-material -LeaseToken $lease.Token -CleanupState $cleanup -TimeoutSeconds 30
        if($state.SurfaceReader.ExitCode -ne 0 -or (Get-Item -LiteralPath $state.SurfaceReader.Stdout).Length -gt 64KB){throw 'Authored material/image FF readback failed.'}
        $surface=[IO.File]::ReadAllText($state.SurfaceReader.Stdout)|ConvertFrom-Json
        if($surface.schema -cne 'iw7.authored-material-roundtrip/1' -or $surface.source_plan_sha256 -ine $state.SourcePlanSHA256 -or
            $surface.ff.sha256 -ine $state.FF.SHA256 -or $surface.image.serialized_pixel_bytes_verified -isnot [bool] -or !$surface.image.serialized_pixel_bytes_verified -or
            $surface.material_fields_verified -isnot [bool] -or !$surface.material_fields_verified -or $surface.ready -isnot [bool] -or $surface.ready){throw 'Authored surface readback receipt differs.'}
        Copy-Item -LiteralPath $state.SurfaceReader.Stdout -Destination (Join-Path $RunRoot 'surface-roundtrip.json')
        $state.SurfaceEvidenceSHA256=(Get-FileHash -LiteralPath (Join-Path $RunRoot 'surface-roundtrip.json')).Hash
        $state.MaterialFieldsVerified=$true;$state.SerializedImageBytesVerified=$true
        $state.NativeCBTSemanticsVerified=$false;$state.PixelsRenderedVerified=$false
    }
}catch{
    $state.Failure=$_.Exception.Message
    if($state.Status -eq 'CompiledRetained' -and $state.Failure -match 'recipient reference unresolved|referenced asset'){$state.Status='BootstrapRecipientReferenceUnresolved'}
    elseif($state.Status -notin @('OfflineUnresolved')){$state.Status='Failed'}
    throw
}
finally{
    if($StockBindingPlan -and $cleanup.Confirmed){
        try{Assert-ModelFFInputs $inputs $work -SourceOnly;Assert-FFStockContent $inputs}
        catch{$cleanup.Confirmed=$false;$state.CleanupError='Stock source proof incomplete; guards and reservation retained.'}
    }
    if($cleanup.Confirmed){foreach($guard in $stockGuards){$guard.Dispose()}}
    if($transactionSaved){Write-ModelFFState $state $statePath
        if(!$cleanup.Confirmed){$state.CleanupError='Owned tool/diagnostic termination unconfirmed; lease retained.';Write-ModelFFState $state $statePath
            if($originalContext){[AppDomain]::CurrentDomain.SetData('IW7.OriginalArena.FF.Quarantine.'+$lease.Token,[pscustomobject]@{Context=$originalContext;Guards=$stockGuards})}}
        else{Complete-ModelFFRestore $state $statePath $lease.Token}}
    # A pre-transaction failure has no borrowed files or child; release normally.
    elseif($cleanup.Confirmed){Exit-IW7ResourceLease -Token $lease.Token}
}
