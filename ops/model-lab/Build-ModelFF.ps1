param([ValidateSet('Build','Restore')][string]$Action='Build',[Parameter(Mandatory)][string]$RunRoot,
    [string]$StockToolRoot,[string]$SourceRoot,[string]$ToolProvenance,[string]$ReaderRun,[string]$Python='python',
    [string]$CandidateRoot,[string]$CandidateArtifactSHA256,[string]$NativeJobAssembly,
    [string]$StockBindingPlan,[string]$StockBindingPlanSHA256,
    [string]$AuthorProjectSource,[string]$AuthoringPlan,[string]$AuthoringPlanSHA256,[switch]$DryRun)
$ErrorActionPreference='Stop'
$ops=Split-Path $PSScriptRoot -Parent;$repo=Split-Path $ops -Parent
. "$ops/Base-Client.Core.ps1"
. "$ops/Lab-Paths.ps1"
. "$ops/Resource-Scheduler.Core.ps1"
. "$ops/Memory-Budget.ps1"
. "$PSScriptRoot/ModelFF.Core.ps1"
$RunRoot=Assert-IW7LabPath ([IO.Path]::GetFullPath($RunRoot)) (Join-Path $repo 'runtime')
$statePath=Join-Path $RunRoot 'state.local.json';$work=Join-Path $RunRoot 'work'
if($Action -eq 'Restore'){
    $state=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if($state.Schema -cne 'iw7.model-ff-build/1' -or $state.Work -ine $work -or $state.Transaction.GameRoot -ine $work -or $state.Transaction.BackupRoot -ine (Join-Path $RunRoot 'backup')){throw 'Exact model transaction required.'}
    if($state.Restored -and $state.Transaction.Restored){return}
    if(!$state.RetainedLeaseToken){throw 'Restoration requires retained reservation; no lease bypass.'}
    if($state.SourcePlan.PSObject.Properties['geometry_profile'] -and $state.SourcePlan.geometry_profile -ceq 'iw7-authored-rigid-v1'){throw 'Authored restoration requires its same retained original host/context.'}
    if(!('IW7HudFileIdentity' -as [type])){Add-Type -Path "$ops/hud-lab/HudFileIdentity.cs"}
    Complete-ModelFFRestore $state $statePath $state.RetainedLeaseToken;return
}
if(Test-Path -LiteralPath $RunRoot){throw 'Fresh model build run required.'}
$deferredAuthored=!!$AuthorProjectSource
if($deferredAuthored){
    if(!$AuthoringPlan -or $AuthoringPlanSHA256 -cnotmatch '^[a-f0-9]{64}$' -or !$ReaderRun -or !$CandidateRoot){throw 'Explicit Source author inputs and closed writer/candidate declarations required.'}
    $AuthorProjectSource=Assert-IW7LabPath ([IO.Path]::GetFullPath($AuthorProjectSource)) ([IO.Path]::GetFullPath($AuthorProjectSource))
    $AuthoringPlan=Assert-IW7LabPath ([IO.Path]::GetFullPath($AuthoringPlan)) ([IO.Path]::GetFullPath($AuthoringPlan))
    if((Get-Item -LiteralPath $AuthoringPlan).Length -gt 64KB -or (Get-FileHash -LiteralPath $AuthoringPlan).Hash -ine $AuthoringPlanSHA256){throw 'Bounded reviewed Source author-input plan required.'}
    $authorInputs=Get-Content -LiteralPath $AuthoringPlan -Raw|ConvertFrom-Json
    Assert-ModelFFAuthorInputs $authorInputs $AuthorProjectSource
    $descriptorPath=Join-Path $AuthorProjectSource 'authoring.json'
    if((Get-Item -LiteralPath $descriptorPath).Length -gt 64KB -or
        (Get-FileHash -LiteralPath $descriptorPath).Hash -ine $authorInputs.ProjectFiles.'authoring.json'.SHA256){throw 'Reviewed original author descriptor required.'}
    $authorDescriptor=Get-Content -LiteralPath $descriptorPath -Raw|ConvertFrom-Json
    if($authorDescriptor.schema -cne 'iw7.creator-authoring/1'){throw 'Original Source descriptor required.'}
    foreach($field in 'namespace','zone','model_name','mesh_name','material_name'){Assert-ModelFFAssetName $authorDescriptor.$field}
    $source=Assert-IW7LabPath ([IO.Path]::GetFullPath($SourceRoot)) (Join-Path $repo 'runtime')
    if(Test-Path -LiteralPath $source){throw 'Fresh deferred authored stage required.'}
    $separator=[IO.Path]::DirectorySeparatorChar
    if($source -ieq $work -or $source.StartsWith($work+$separator,[StringComparison]::OrdinalIgnoreCase) -or
        $work.StartsWith($source+$separator,[StringComparison]::OrdinalIgnoreCase)){throw 'Deferred stage must be separate from the restored tool work directory.'}
    $planPath=Join-Path $source 'model-ff-plan.json'
    $plan=$null;$sourceNames=@();$artifactNames=@();$profile=$true;$authored=$true;$arena=$false;$rigid=$false;$planVersion=3
    $modelName=$authorDescriptor.model_name;$meshName=$authorDescriptor.mesh_name;$zoneName=$authorDescriptor.zone
}else{
if($AuthoringPlan -or $AuthoringPlanSHA256){throw 'Author input plan requires its explicit Source project.'}
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
}
if($DryRun){
    [ordered]@{Schema='iw7.model-ff-admission/1';RunRoot=$RunRoot;OriginalInputs=$sourceNames;
        PhysicalBytes=8GB;CommitBytes=11GB;StockDiscoveryDeferred=$true;OpaqueInputsRead=$false;
        NativeTypesLoaded=$false;LeaseAcquired=$false;SourcePlanDeferred=$deferredAuthored;Reader=$null;Ready=$false}|ConvertTo-Json -Depth 8
    return
}
$lease=$null;$originalContext=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Work=$work;
    Guards=[Collections.Generic.List[IDisposable]]::new()}
$cleanup=[pscustomobject]@{Confirmed=$true};$transactionSaved=$false
$stockGuards=[Collections.Generic.List[IDisposable]]::new()
$state=[ordered]@{Schema='iw7.model-ff-build/1';Work=$work;Inputs=@();RetainedLeaseToken=$null;
    Restored=$false;StockPreserved=$false;RestorationStatus='Pending';CleanupError=$null;Status='Preparing';
    SourcePlan=$plan;ToolSHA256=$null;InventoryVerified=$false;GeometryRoundtripVerified=$false;
    RecipientReferenceResolved=$false;SymbolsVerified=$false;Ready=$false}
$modelFFRoot=$null
if($authored){
    if(!$NativeJobAssembly -or $PSVersionTable.PSVersion.Major -lt 7 -or '-NoExit' -notin [Environment]::GetCommandLineArgs()){
        throw 'Authored ModelFF requires the retained NativeJob assembly and fresh persistent PS7 -NoExit host.'
    }
    $modelFFRoot=[pscustomobject]@{Key=('IW7.AuthoredModelFF.Root.'+[guid]::NewGuid().ToString('N'));
        Context=$originalContext;ContextVariable=(Get-Variable originalContext);State=$state;StateVariable=(Get-Variable state);
        SourceGuards=$originalContext.Guards;StockGuards=$stockGuards;Cleanup=$cleanup;
        Pins=[Collections.Generic.List[object]]::new();StockPins=[Collections.Generic.List[object]]::new();
        Publications=[Collections.Generic.List[object]]::new();
        PublicationGuards=[Collections.Generic.List[IDisposable]]::new();
        Plan=[pscustomobject]@{RunRoot=$RunRoot;OutputLimitBytes=256MB;MetadataReserveBytes=1MB};
        GroupStarted=$null;GroupDeadlineSeconds=600;PhaseStarted=$null;PhaseSeconds=0;LastPhaseStarted=$null;
        OriginalPhases=[Collections.Generic.List[object]]::new();
        CanExit=$false;Failure=$null;FinalClosureVerified=$false}
    [AppDomain]::CurrentDomain.SetData($modelFFRoot.Key,$modelFFRoot)
}
try{
    # One admission precedes every native import, stock observation, image/model
    # byte check, SDK/debugger query and executable inspection in this entry.
    $lease=Enter-IW7ResourceLease -Scope $work -Kind Extract -PhysicalBytes 8GB -CommitBytes 11GB -Owner 'Original model FF bootstrap/inventory/roundtrip'
    $state.RetainedLeaseToken=$lease.Token
    [IO.Directory]::CreateDirectory($RunRoot)|Out-Null
    if($authored){
        $originalContext.Lease=$lease
        . "$repo/tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1"
        . "$repo/tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1"
        $modelFFRoot.GroupStarted=Get-H1Clock
        function Assert-ModelFFGroupDeadline {Assert-H1Deadline $modelFFRoot.GroupStarted $modelFFRoot.GroupDeadlineSeconds}
        function Add-ModelFFHeldInput([string]$Path,[string]$Expected='',[switch]$Stock) {
            Assert-ModelFFGroupDeadline
            $path=Assert-IW7LabPath ([IO.Path]::GetFullPath($Path)) ([IO.Path]::GetFullPath($Path))
            $pin=[pscustomobject]@{Path=$path;Bytes=(Get-Item -LiteralPath $path).Length;SHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
            if($Expected -and $pin.SHA256 -ine $Expected){throw 'Admitted authored input differs.'}
            $guard=Open-H1Pin $pin
            if($Stock){$stockGuards.Add($guard);$modelFFRoot.StockPins.Add($pin)}else{$originalContext.Guards.Add($guard);$modelFFRoot.Pins.Add($pin)}
            Assert-ModelFFGroupDeadline
            $pin
        }
        function Confirm-ModelFFHeldInputs {
            for($i=0;$i -lt $modelFFRoot.Pins.Count;$i++){
                Assert-ModelFFGroupDeadline
                $guard=$originalContext.Guards[$i];$pin=$modelFFRoot.Pins[$i];$guard.Position=0
                $actual=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($guard)).ToLowerInvariant();$guard.Position=0
                if($guard.Length -ne $pin.Bytes -or $actual -cne $pin.SHA256){throw 'Held authored input changed.'}
            }
        }
        function Confirm-ModelFFStockGuards {
            for($i=0;$i -lt $modelFFRoot.StockPins.Count;$i++){
                Assert-ModelFFGroupDeadline
                $guard=$stockGuards[$i];$pin=$modelFFRoot.StockPins[$i];$guard.Position=0
                $actual=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($guard)).ToLowerInvariant();$guard.Position=0
                if($guard.Length -ne $pin.Bytes -or $actual -cne $pin.SHA256){throw 'Held current Main stock changed.'}
            }
        }
        function Publish-ModelFFReceipt($Value,[string]$Name) {
            Assert-ModelFFGroupDeadline
            $record=Write-H1Receipt $modelFFRoot.Plan $Value $RunRoot -Name $Name -PassThru
            $modelFFRoot.PublicationGuards.Add((Open-H1Pin $record));$modelFFRoot.Publications.Add($record)
            $record
        }
        if(!$deferredAuthored){
            $null=Add-ModelFFHeldInput $planPath
            foreach($name in $sourceNames){$null=Add-ModelFFHeldInput (Join-Path $source $name) $plan.source_files.$name}
        }
        foreach($name in @('ops/model-lab/Build-ModelFF.ps1','ops/model-lab/ModelFF.Core.ps1',
            'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1','tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1',
            'tools-source/asset-bridge/world/original-arena/OriginalArena.Process.ps1','ops/hud-lab/HudFileIdentity.cs')){
            $null=Add-ModelFFHeldInput (Join-Path $repo $name)
        }
    }
function Invoke-ModelFFTool([string]$Phase,[string[]]$Arguments,[string]$Executable,[string]$SHA256,[string]$WorkingDirectory,[int]$Seconds=240) {
    if($authored){$modelFFRoot.PhaseStarted=Get-H1Clock;$modelFFRoot.PhaseSeconds=$Seconds;Assert-ModelFFGroupDeadline}
    if(!$Executable){$Executable=Join-Path $work 'zonetool.exe';$SHA256=$provenance.BinarySHA256}
    if(!$WorkingDirectory){$WorkingDirectory=$work}
    if($originalContext){
        $poll=$null
        if($authored){
            $poll={param($context,$current,$logs)
                Assert-ModelFFGroupDeadline
                if(!@($modelFFRoot.OriginalPhases|Where-Object {[object]::ReferenceEquals($_,$current)}).Count){$modelFFRoot.OriginalPhases.Add($current)}
            }
        }
        try{return Invoke-OriginalArenaTool $originalContext $Executable $SHA256 $Arguments $WorkingDirectory $RunRoot $Phase $inputs $Seconds $poll}
        finally{
            $cleanup.Confirmed=$originalContext.Closed
            if($authored -and $originalContext.Closed){$modelFFRoot.LastPhaseStarted=$modelFFRoot.PhaseStarted;$modelFFRoot.PhaseStarted=$null}
        }
    }
    Invoke-HudBuildProcess -Work $work -RunRoot $RunRoot -LeaseToken $lease.Token -CleanupState $cleanup -Cdb $cdb -Symbols $symbols -Phase $Phase -ToolArguments $Arguments
}
    if($authored -or $arena){$Python=(Get-Command $Python -CommandType Application -ErrorAction Stop|Select-Object -First 1).Source}
    if($authored){. "$repo/sdk/modding/BeaconFF.Core.ps1"}
    if($CandidateRoot -and ($arena -or $authored)){
        $package=Get-Content -LiteralPath (Join-Path $repo 'source-workspace.json') -Raw|ConvertFrom-Json
        $memoryPolicyPins=if($authored){@('2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1','93fd16b1b7e9da0b46b0348973baa55cd363b1ca')}else{@('2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1')}
        if($package.revisions.'iw7-mod-components' -cnotin $memoryPolicyPins){throw 'Current TelemetryOnly native provider required.'}
        if('IW7.AnimationProbe.NativeJob' -as [type]){throw 'Fresh PowerShell host required for the original arena owner.'}
        $assembly=Assert-IW7LabPath ((Resolve-Path -LiteralPath $NativeJobAssembly).Path) ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($NativeJobAssembly)))
        $ownerSHA='5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8'
        if((Get-FileHash -LiteralPath $assembly).Hash -ine $ownerSHA){throw 'Retained original NativeJob assembly differs.'}
        . "$repo/tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1"
        . "$repo/tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1"
        . "$repo/tools-source/asset-bridge/world/original-arena/OriginalArena.Process.ps1"
        if($authored){$null=Add-ModelFFHeldInput $assembly $ownerSHA}
        [Reflection.Assembly]::LoadFrom($assembly)|Out-Null
        if(!$authored){$originalContext=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$lease;Work=$work}}
        $state.OriginalOwner=[ordered]@{AssemblySHA256=$ownerSHA;SourceWorkspaceSHA256=(Get-FileHash -LiteralPath (Join-Path $repo 'source-workspace.json')).Hash;NativePolicyRevision=$package.revisions.'iw7-mod-components';Policy='H1 original root/job, TelemetryOnly'}
        if($authored){
            $pythonPin=Add-ModelFFHeldInput $Python
            $originalFFFactory=${function:New-H1Owner}
            $originalFFDeadline=${function:Assert-H1Deadline}
            function Assert-H1Deadline($Started,$Seconds){
                & $originalFFDeadline $Started $Seconds
                & $originalFFDeadline $modelFFRoot.GroupStarted $modelFFRoot.GroupDeadlineSeconds
                if($null -ne $modelFFRoot.PhaseStarted){& $originalFFDeadline $modelFFRoot.PhaseStarted $modelFFRoot.PhaseSeconds}
            }
            function Assert-ModelFFGroupDeadline {
                & $originalFFDeadline $modelFFRoot.GroupStarted $modelFFRoot.GroupDeadlineSeconds
                if($null -ne $modelFFRoot.PhaseStarted){& $originalFFDeadline $modelFFRoot.PhaseStarted $modelFFRoot.PhaseSeconds}
            }
            function New-H1Owner {
                Assert-ModelFFGroupDeadline
                $originalOwner=& $originalFFFactory
                $originalContext.Owner=$originalOwner
                Assert-ModelFFGroupDeadline
                $originalOwner
            }
        }
    }
    if($deferredAuthored){
        $null=Add-ModelFFHeldInput $AuthoringPlan $AuthoringPlanSHA256
        $sdkPin=$authorInputs.SDKSourceWorkspace
        if((Get-Item -LiteralPath $sdkPin.Path).Length -ne $sdkPin.Bytes){throw 'Reviewed SDK Source receipt size differs.'}
        $null=Add-ModelFFHeldInput $sdkPin.Path $sdkPin.SHA256
        $sdkToolsRoot=Split-Path $sdkPin.Path -Parent
        $sdkSources=Read-H1SmallJson $sdkPin.Path 1MB
        if($sdkSources.schema -cne 'iw7.source-workspace/1' -or $sdkSources.product -cne 'iw7-creator-sdk' -or
            $sdkSources.revisions.'iw7-creator-sdk' -cne '2f9f584549ba7b009b35699a59582f4390102994' -or
            $sdkSources.revisions.'x64-zt-extensions' -cne '8f55ac7819d93f5bcede273aea3e478ae9438a12'){
            throw 'Exact SDK29/producer172 Source stage implementation required.'
        }
        foreach($relative in @('sdk/modding/creator_authoring.py','sdk/modding/Finalize-BeaconProject.py','sdk/modding/manifest.py',
            'sdk/modding/manifest.schema.json','sdk/modding/capabilities.json','ops/Validate-ModPackage.py','ops/modding/Distribution-Compat.py',
            'ops/model-lab/geometry.py','ops/model-lab/prepare_writer.py','ops/model-lab/writer.cpp','ops/model-lab/prepare_ff.py',
            'tools-source/asset-bridge/surfaces/authored_dds_material.py','tools-source/asset-bridge/surfaces/inspect_content.py',
            'tools-source/asset-bridge/t7-iw7/resident_image.py')){
            $row=@($sdkSources.files|Where-Object path -CEQ $relative)
            if($row.Count -ne 1){throw 'Unique SDK stage transitive Source export required.'}
            $null=Add-ModelFFHeldInput (Join-Path $sdkToolsRoot $relative) $row[0].sha256
        }
        $authorProject=Join-Path $RunRoot 'author-project'
        [IO.Directory]::CreateDirectory($authorProject)|Out-Null
        foreach($entry in $authorInputs.ProjectFiles.PSObject.Properties){
            $original=Resolve-IW7BasePath $AuthorProjectSource $entry.Name
            if((Get-Item -LiteralPath $original).Length -ne $entry.Value.Bytes){throw 'Original author Source size differs.'}
            $null=Add-ModelFFHeldInput $original $entry.Value.SHA256
            $target=Join-Path $authorProject $entry.Name
            Copy-Item -LiteralPath $original -Destination $target
            $null=Add-ModelFFHeldInput $target $entry.Value.SHA256
        }
        $copiedDescriptor=Read-H1SmallJson (Join-Path $authorProject 'authoring.json') 64KB
        if($copiedDescriptor.script_source -cnotin $authorInputs.ProjectFiles.PSObject.Properties.Name -or
            (@($copiedDescriptor.material_template.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'cbi,cbt,material,statebits,statebitsmap,stateinfo'){
            throw 'Copied Source descriptor must declare its actual script and six template roles.'
        }
        foreach($entry in $authorInputs.Templates.PSObject.Properties){
            $pin=$entry.Value
            if((Get-Item -LiteralPath $pin.Path).Length -ne $pin.Bytes){throw 'Material template role size differs.'}
            $null=Add-ModelFFHeldInput $pin.Path $pin.SHA256
            $target=Resolve-IW7BasePath $authorProject $copiedDescriptor.material_template.($entry.Name)
            if(Test-Path -LiteralPath $target){throw 'Fresh owned template destination required.'}
            [IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
            Copy-Item -LiteralPath $pin.Path -Destination $target
            $null=Add-ModelFFHeldInput $target $pin.SHA256
        }
        $writerRootPath=Assert-IW7LabPath ([IO.Path]::GetFullPath($ReaderRun)) ([IO.Path]::GetFullPath($ReaderRun))
        $writerRecipePath=Join-Path $writerRootPath 'writer-source.json'
        if((Get-Item -LiteralPath $writerRecipePath).Length -gt 512KB){throw 'Bounded original writer recipe required.'}
        $null=Add-ModelFFHeldInput $writerRecipePath
        $writerRecipe=Read-H1SmallJson $writerRecipePath 512KB
        foreach($entry in $writerRecipe.source_files.PSObject.Properties){
            $null=Add-ModelFFHeldInput (Resolve-IW7BasePath $writerRootPath $entry.Name) $entry.Value
        }
        $writerProvenancePath=Join-Path $writerRootPath 'writer-provenance.json'
        if((Get-Item -LiteralPath $writerProvenancePath).Length -gt 512KB){throw 'Bounded original writer provenance required.'}
        $null=Add-ModelFFHeldInput $writerProvenancePath
        $writerPrepublication=Read-H1SmallJson $writerProvenancePath 512KB
        if('NativeReleasePending' -cin $writerPrepublication.PSObject.Properties.Name){
            foreach($item in @(@('writer-native-run.json',1MB),@('writer-closure.json',64KB))){
                $path=Join-Path $writerRootPath $item[0]
                if((Get-Item -LiteralPath $path).Length -gt $item[1]){throw 'Bounded original native publication required.'}
                $null=Add-ModelFFHeldInput $path
            }
        }
        foreach($name in $writerRecipe.artifact_paths){
            $path=Resolve-IW7BasePath $writerRootPath ('artifacts/'+$name)
            if((Get-Item -LiteralPath $path).Length -gt 8192){throw 'Bounded original rigid writer artifact required.'}
            $null=Add-ModelFFHeldInput $path
        }
        [IO.Directory]::CreateDirectory((Split-Path $source))|Out-Null
        $stageArguments=@(Get-ModelFFAuthorStageArguments $sdkToolsRoot $authorProject $writerRootPath $source)
        $state.AuthorStage=Invoke-ModelFFTool authored-stage $stageArguments -Executable $Python -SHA256 $pythonPin.SHA256 -WorkingDirectory $sdkToolsRoot -Seconds 60
        $stageReport=Read-H1SmallJson $state.AuthorStage.Stdout 1MB
        if($stageReport.api -cne 'creator-original-authoring/1' -or $stageReport.ff_inputs_staged -isnot [bool] -or !$stageReport.ff_inputs_staged -or
            $stageReport.opaque_inputs_read -isnot [bool] -or !$stageReport.opaque_inputs_read){throw 'Actual SDK stage result required.'}
        foreach($flag in 'native_compiled','ff_built','build_verified','runtime_ready','owner_accepted'){
            if($stageReport.$flag -isnot [bool] -or $stageReport.$flag){throw 'SDK stage cannot promote native FF or runtime claims.'}
        }
        if($stageReport.source_plan_file.path -cne $planPath -or (Get-Item -LiteralPath $planPath).Length -ne $stageReport.source_plan_file.bytes){throw 'Original SDK stage plan publication differs.'}
        $null=Add-ModelFFHeldInput $planPath $stageReport.source_plan_file.sha256
        $plan=Read-H1SmallJson $planPath 1MB
        Assert-ModelFFAuthoredPlan $plan
        if($plan.namespace -cne $authorDescriptor.namespace -or $plan.zone -cne $zoneName -or
            $plan.model_name -cne $modelName -or $plan.mesh_name -cne $meshName -or $plan.material_reference -cne $authorDescriptor.material_name){throw 'Actual staged author identity differs.'}
        $sourceNames=@(Get-ModelFFSourceNames $plan);$artifactNames=@($sourceNames[0],$sourceNames[1]);$state.SourcePlan=$plan
        foreach($name in $sourceNames){$null=Add-ModelFFHeldInput (Resolve-IW7BasePath $source $name) $plan.source_files.$name}
        foreach($file in @(Get-ChildItem -LiteralPath (Join-Path $source 'evidence') -File -Recurse)){$null=Add-ModelFFHeldInput $file.FullName}
    }
    if(!('IW7HudFileIdentity' -as [type])){Add-Type -Path "$ops/hud-lab/HudFileIdentity.cs"}
    $stock=(Resolve-Path -LiteralPath $StockToolRoot).Path;$null=Assert-IW7LabPath $stock $stock
if($authored){
    if(!$ReaderRun -or !$CandidateRoot){throw 'Authored FF requires its measured native reader and strict community candidate.'}
    $Python=(Get-Command $Python -CommandType Application -ErrorAction Stop|Select-Object -First 1).Source
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
    if((!$arena -and !$renderOnlyStock -and !$authored) -or !$CandidateRoot -or $StockBindingPlanSHA256 -cnotmatch '^[a-fA-F0-9]{64}$' -or
        (Get-Item -LiteralPath $StockBindingPlan).Length -gt 1MB -or (Get-FileHash -LiteralPath $StockBindingPlan).Hash -ine $StockBindingPlanSHA256){throw 'Explicit bounded original-arena stock binding required.'}
    $boundStock=Get-Content -LiteralPath $StockBindingPlan -Raw|ConvertFrom-Json
    if($authored){$inputs=@(Get-ModelFFAuthoredStockInputs $boundStock $stock)}else{
        $inputs=@($boundStock.stock_binding.inputs)
        if($inputs.Count -ne 72 -or @($inputs|Where-Object {$_.Relative -eq 'main/fileSysCheck.cfg' -and $_.Mode -ceq 'Copy'}).Count -ne 1){throw 'Existing 72-input aliases and independent copied sentinel required.'}
        . "$repo/tools-source/asset-bridge/common/StockBinding.Core.ps1"
    }
}else{
if($authored){throw 'Authored FF requires its explicit current Main/fixed33 Source descriptor.'}
if($StockBindingPlanSHA256){throw 'Stock binding digest requires its explicit plan.'}
foreach($folder in @('main','zone')){foreach($f in @(Get-ChildItem -LiteralPath (Resolve-IW7BasePath $stock $folder) -File -Filter '*.ff')){if($f.Name -in $names){$inputs+=[pscustomobject]@{Relative=$folder+'/'+$f.Name;Source=$f.FullName;Mode='HardLink'}}}}
$inputs+=[pscustomobject]@{Relative='zone/assetfile1.pak';Source=(Resolve-IW7BasePath $stock 'zone/assetfile1.pak');Mode='HardLink'}
foreach($name in @('iw7_ship.exe','amd_ags_x64.dll','bink2w64.dll','d3dcompiler_46.dll','steam_api.dll','steam_api64.dll','Steam.dll','tlsdll.dll','main/fileSysCheck.cfg')){
    $p=Resolve-IW7BasePath $stock $name
    if(Test-Path -LiteralPath $p){$inputs+=[pscustomobject]@{Relative=$name;Source=$p;Mode='Copy'}}elseif($name -in @('iw7_ship.exe','bink2w64.dll','steam_api64.dll','main/fileSysCheck.cfg')){throw 'Required bootstrap engine/sentinel missing.'}
}
}
foreach($entry in $inputs){$f=Get-Item -LiteralPath $entry.Source;$null=Resolve-IW7BasePath $stock $entry.Relative
    if($StockBindingPlan -and !$authored){
        if($f.Length -ne $entry.Bytes -or $f.LastWriteTimeUtc.Ticks -ne ([datetimeoffset]$entry.ModifiedUtc).UtcDateTime.Ticks -or [int]$f.Attributes -ne $entry.Attributes -or $entry.Mode -cnotin @('Copy','HardLink')){throw 'Observed stock metadata/mode changed.'}
        $id=[IW7HudFileIdentity]::Read($entry.Source);Assert-FFStockIdentity $entry $id
        $entry|Add-Member NoteProperty SourceId $id -Force
        continue
    }
    if($entry.Mode -eq 'HardLink' -and ($f.Attributes -band [IO.FileAttributes]::ReadOnly)){throw 'Read-only stock links refused.'}
    $entry | Add-Member NoteProperty Bytes $f.Length;$entry | Add-Member NoteProperty ModifiedUtc $f.LastWriteTimeUtc.ToString('o');$entry | Add-Member NoteProperty Attributes ([int]$f.Attributes)
    $entry | Add-Member NoteProperty SourceId ([IW7HudFileIdentity]::Read($entry.Source))
    if($authored){
        $expected=if('DeclaredSHA256' -cin $entry.PSObject.Properties.Name){$entry.DeclaredSHA256}else{''}
        if('DeclaredBytes' -cin $entry.PSObject.Properties.Name -and $entry.Bytes -ne $entry.DeclaredBytes){throw 'Current tool/sentinel declared size differs.'}
        $held=@($modelFFRoot.StockPins|Where-Object {$_.Path -ceq $entry.Source})
        $pin=if($held.Count){$held[0]}else{Add-ModelFFHeldInput $entry.Source $expected -Stock}
        if([IW7HudFileIdentity]::Read($entry.Source) -cne $entry.SourceId){throw 'Current Main provider changed before its guard.'}
        $entry|Add-Member NoteProperty ExpectedSHA256 $pin.SHA256
    }
}
if(!@($inputs | Where-Object Relative -eq 'main/code_pre_gfx.ff').Count){throw 'Bootstrap FF missing.'}
. "$ops/Lab-AssetProcess.ps1"
. "$ops/Agent-LabCrash.Core.ps1"
. "$ops/hud-lab/Hud-Process.ps1"
$cdb=$null
if(!$CandidateRoot -or (!$arena -and !$authored)){
    $package=Get-AppxPackage Microsoft.WinDbg;$cdb=Join-Path $package.InstallLocation 'amd64/cdb.exe'
    if($package.Version -ne '1.2606.22001.0' -or
       (!$CandidateRoot -and (Get-FileHash -LiteralPath $cdb).Hash -cne '5F54ABAFCA3AE5638BBF807D402FABB350A64575C1DFA9FBFC7F5732DF5BEE67')){throw 'Known bounded offline diagnostics required.'}
}
$reader=$null
if($ReaderRun){
    $readerAbsolute=[IO.Path]::GetFullPath($ReaderRun)
    $readerBoundary=if($authored){$readerAbsolute}else{Join-Path $repo 'runtime'}
    $readerRoot=Assert-IW7LabPath ((Resolve-Path -LiteralPath $ReaderRun).Path) $readerBoundary
    $readerProvenance=Join-Path $readerRoot 'writer-provenance.json'
    if((Get-Item -LiteralPath $readerProvenance).Length -gt 512KB){throw 'Bounded native reader provenance required.'}
    $r=Get-Content -LiteralPath $readerProvenance -Raw | ConvertFrom-Json
    $reader=Join-Path $readerRoot 'model-writer.exe';if($r.SourcePin -cne $plan.source_pin -or !$r.Roundtrip.read_existing_supported -or (!$authored -and (Get-FileHash -LiteralPath $reader).Hash -ine $r.WriterSHA256)){throw 'Measured original reader with existing-dump mode required.'}
    if($authored -and ((Get-FileHash -LiteralPath $readerProvenance).Hash -ine $plan.writer_provenance_sha256 -or
        $r.WriterSHA256 -ine $plan.writer_sha256 -or $r.Source.geometry_profile -cne 'iw7-authored-rigid-v1' -or
        $r.Source.geometry_source_sha256 -ine $plan.geometry_source_sha256)){throw 'Authored native reader is not bound to source geometry.'}
    if($r.Source.candidate_variable -cne 'lodInfo[0].dist'){throw 'Exact distance candidate reader required.'}
    Assert-ModelFFDistanceCandidate $r.Source
    Assert-ModelFFDistanceCandidate $r.Roundtrip}
$state.Inputs=$inputs;$state.ToolSHA256=$provenance.BinarySHA256
if($rigid -or $arena -or $authored){$state.SourcePlanSHA256=(Get-FileHash -LiteralPath (Join-Path $source 'model-ff-plan.json')).Hash}
if(!$authored -and !$arena){$originalContext=$null}
    if($authored -and (Get-FileHash -LiteralPath $reader).Hash -ine $plan.writer_sha256){throw 'Admitted authored native reader changed.'}
    if($authored){$null=Add-ModelFFHeldInput $reader $plan.writer_sha256}
    if($CandidateRoot){
        $candidate=Assert-BeaconCandidate $CandidateRoot $CandidateArtifactSHA256
        if($candidate.Path -ine $tool -or $candidate.SHA256 -ine $provenance.BinarySHA256){throw 'Admitted candidate differs from planned producer metadata.'}
        $state.CandidateQualifiedUnderLease=$true
        if($authored){$null=Add-ModelFFHeldInput $candidate.Path $candidate.SHA256}
    }
    if($CandidateRoot -and !$arena -and !$authored -and (Get-FileHash -LiteralPath $cdb).Hash -cne '5F54ABAFCA3AE5638BBF807D402FABB350A64575C1DFA9FBFC7F5732DF5BEE67'){
        throw 'Known bounded offline diagnostics required.'
    }
    if($StockBindingPlan -and !$authored){
        foreach($entry in $inputs){$stockGuards.Add([IO.File]::Open($entry.Source,'Open','Read','Read'))}
        Assert-FFStockContent $inputs
        $state.StockBindingPlanSHA256=$StockBindingPlanSHA256
        $state.StockBindingProfile=if($renderOnlyStock){'existing-72-t7-render-only-v2'}else{'existing-72-original-arena'}
    }
    if($authored){
        try{$sourceCheck=Invoke-ModelFFTool authored-source @('-B','-S',"$PSScriptRoot/prepare_ff.py",'--verify-authored-stage',$source) `
            -Executable $Python -SHA256 $pythonPin.SHA256 -WorkingDirectory $repo -Seconds 30}
        finally{$cleanup.Confirmed=$originalContext.Closed}
        $state.SourceValidation=$sourceCheck
        if($sourceCheck.ExitCode -ne 0){throw 'Authored source/material closure differs.'}
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
        if($authored){
            try{$state.GeometryReader=Invoke-ModelFFTool model-geometry @('--verify-existing',(Join-Path $RunRoot 'roundtrip')) -Executable $reader -SHA256 $plan.writer_sha256 -Seconds 30}
            finally{$cleanup.Confirmed=$originalContext.Closed}
        }else{$state.GeometryReader=Invoke-IW7LabAssetProcess -Executable $reader -ToolArguments @('--verify-existing',(Join-Path $RunRoot 'roundtrip')) -WorkingDirectory $work -LogDirectory $RunRoot -Phase model-geometry -LeaseToken $lease.Token -CleanupState $cleanup -TimeoutSeconds 30}
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
        try{$state.SurfaceReader=Invoke-ModelFFTool model-authored-material $argsSurface -Executable $Python -SHA256 $pythonPin.SHA256 -WorkingDirectory $repo -Seconds 30}
        finally{$cleanup.Confirmed=$originalContext.Closed}
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
    if($modelFFRoot){$modelFFRoot.Failure=$_}
    $state.Failure=$_.Exception.Message
    if($state.Status -eq 'CompiledRetained' -and $state.Failure -match 'recipient reference unresolved|referenced asset'){$state.Status='BootstrapRecipientReferenceUnresolved'}
    elseif($state.Status -notin @('OfflineUnresolved')){$state.Status='Failed'}
    throw
}
finally{
    if($authored){$cleanup.Confirmed=$originalContext.Closed}
    if($StockBindingPlan -and $cleanup.Confirmed){
        try{Assert-ModelFFInputs $inputs $work -SourceOnly;if(!$authored){Assert-FFStockContent $inputs}else{Confirm-ModelFFHeldInputs;Confirm-ModelFFStockGuards}}
        catch{$cleanup.Confirmed=$false;$state.CleanupError='Stock source proof incomplete; guards and reservation retained.'}
    }
    if($cleanup.Confirmed -and !$authored){foreach($guard in $stockGuards){$guard.Dispose()}}
    if($cleanup.Confirmed -and $authored){
        # Windows share-delete rules require releasing only the stock handles
        # before unlinking their borrowed aliases. Keep code/payload guards and
        # the same admission/context; restore still checks original stock IDs.
        foreach($guard in $stockGuards){$guard.Dispose()};$stockGuards.Clear()
    }
    if($transactionSaved){Write-ModelFFState $state $statePath
        if(!$cleanup.Confirmed){$state.CleanupError='Owned tool/diagnostic termination unconfirmed; lease retained.';Write-ModelFFState $state $statePath
            if($originalContext){[AppDomain]::CurrentDomain.SetData('IW7.OriginalArena.FF.Quarantine.'+$lease.Token,[pscustomobject]@{Context=$originalContext;Guards=$stockGuards})}}
        else{
            $beforeRelease=if($authored){{
                Confirm-ModelFFHeldInputs
                # Restore has proved the original source IDs/metadata. Reopen
                # against those same measured byte pins for the final proof;
                # this never reconstructs a job owner or adopts another input.
                foreach($pin in $modelFFRoot.StockPins){$stockGuards.Add((Open-H1Pin $pin))}
                Assert-ModelFFInputs $inputs $work -SourceOnly
                Confirm-ModelFFStockGuards
                Assert-ModelFFGroupDeadline
                $snapshot=[ordered]@{Schema='iw7.authored-model-ff-native-run/1';NativeRootKey=$modelFFRoot.Key;
                    State=$state;OriginalContextClosed=$originalContext.Closed;LeaseReleased=$false;ReleasePending=$true;Ready=$false}
                $null=Publish-ModelFFReceipt $snapshot 'authored-native-run.json'
                foreach($guard in $stockGuards){$guard.Dispose()};$stockGuards.Clear()
                foreach($guard in $originalContext.Guards){$guard.Dispose()};$originalContext.Guards.Clear()
            }}else{$null}
            Complete-ModelFFRestore $state $statePath $lease.Token -BeforeReleaseCheck $beforeRelease
            if($authored){$originalContext.Lease=$null}
        }}
    # A pre-transaction failure has no borrowed files or child; release normally.
    elseif($cleanup.Confirmed -and $lease){
        if($authored){
            Confirm-ModelFFHeldInputs
            $snapshot=[ordered]@{Schema='iw7.authored-model-ff-native-run/1';NativeRootKey=$modelFFRoot.Key;
                State=$state;OriginalContextClosed=$originalContext.Closed;LeaseReleased=$false;
                ReleasePending=$true;TransactionStarted=$false;Ready=$false}
            $null=Publish-ModelFFReceipt $snapshot 'authored-native-run.json'
            Write-ModelFFState $state $statePath
            foreach($guard in $stockGuards){$guard.Dispose()};$stockGuards.Clear()
            foreach($guard in $originalContext.Guards){$guard.Dispose()};$originalContext.Guards.Clear()
        }
        Exit-IW7ResourceLease -Token $lease.Token
        if($authored){$originalContext.Lease=$null;$state.RetainedLeaseToken=$null}
    }
}
if($authored){
    if(!$originalContext.Closed -or $originalContext.Lease -or $originalContext.Guards.Count -or $stockGuards.Count){throw 'Retain the same authored FF root/context/guards.'}
    $nativeRecord=@($modelFFRoot.Publications|Where-Object {$_.Path -ceq (Join-Path $RunRoot 'authored-native-run.json')})
    if($nativeRecord.Count -ne 1){throw 'One original authored native publication required.'}
    $closure=[ordered]@{Schema='iw7.authored-model-ff-closure/1';NativeRootKey=$modelFFRoot.Key;
        NativeRunSHA256=$nativeRecord[0].SHA256;OriginalJobClosed=$true;InputGuardsClosed=$true;
        TransactionRestored=$state.Restored;StockPreserved=$state.StockPreserved;LeaseReleased=$true;Ready=$false}
    $null=Publish-ModelFFReceipt $closure 'authored-closure.json'
    foreach($record in $modelFFRoot.Publications){$check=Open-H1Pin $record;$check.Dispose()}
    foreach($guard in $modelFFRoot.PublicationGuards){$guard.Dispose()};$modelFFRoot.PublicationGuards.Clear()
    $modelFFRoot.FinalClosureVerified=$true;$modelFFRoot.CanExit=$true
}
