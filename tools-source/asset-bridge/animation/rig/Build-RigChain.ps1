param(
    [Parameter(Mandatory)][string]$PlanPath,
    [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$PlanSHA256,
    [switch]$Run
)
# Specialized, sequential executor. Default performs source/metadata inspection
# only. -Run must be invoked by the coordinator after the separate execution GO.
$ErrorActionPreference='Stop'
$PlanPath=[IO.Path]::GetFullPath($PlanPath)
if((Get-Item -LiteralPath $PlanPath).Length -gt 1MB -or (Get-FileHash -LiteralPath $PlanPath).Hash -ine $PlanSHA256){throw 'Bounded hash-bound plan required.'}
$plan=[IO.File]::ReadAllText($PlanPath)|ConvertFrom-Json
$planner=Join-Path $PSScriptRoot 'plan_rig_chain.py'
if($plan.python.sha256 -ine '31073dad142bc7f3374e3122aa668270052c9ad37d0aaab803ae73f184c3a43b' -or
   (Get-FileHash -LiteralPath $plan.python.path).Hash -ine $plan.python.sha256 -or
   (Get-FileHash -LiteralPath $planner).Hash -ine $plan.plan_source_sha256){throw 'Pinned Python and local recipe source required.'}
# Only a source reader runs here. No native type, lease, SDK hash or stock read.
$checked=& $plan.python.path -I -B $planner --check-plan $PlanPath --check-plan-sha256 $PlanSHA256
if($LASTEXITCODE -ne 0){throw "Rig recipe revalidation failed: $checked"}
$plan=($checked -join "`n")|ConvertFrom-Json
$animationCore=Join-Path (Split-Path $PSScriptRoot) 'AnimationFF.Core.ps1'
$stockCore=Join-Path (Split-Path (Split-Path $PSScriptRoot)) 'common/StockBinding.Core.ps1'
foreach($path in @($animationCore,$stockCore,(Join-Path $PSScriptRoot 'Rig.Core.ps1'),(Join-Path $PSScriptRoot 'Rig.Compiler.ps1'))){
    if((Get-FileHash -LiteralPath $path).Hash -ine $plan.execution_input_hashes.$path){throw 'Local executor/provider binding differs.'}
}
. $animationCore
foreach($path in @($stockCore,(Join-Path $PSScriptRoot 'Rig.Core.ps1'),(Join-Path $PSScriptRoot 'Rig.Compiler.ps1'))){Assert-AnimationPureImport $path;. $path}
$bindings=@{};foreach($p in $plan.provider_bindings.PSObject.Properties){$bindings[$p.Name]=$p.Value}
foreach($name in @('ops/Base-Client.Core.ps1','sdk/modding/BeaconFF.Core.ps1','ops/model-lab/ModelFF.Core.ps1')){
    Assert-AnimationPureImport $bindings[$name].Path;. $bindings[$name].Path
}
$recipe=$plan.compiler_environment_recipe
$toolchain=@(Get-RigToolchainInventory $recipe.freeze_roots)
$policy=Get-RigCompilerPolicy $plan.compiler_receipt.Compiler
Assert-BeaconHash $policy.Telemetry $policy.TelemetrySHA256
if(!$Run){
    [ordered]@{Schema='iw7.rig-executor-plan/1';RecipeSHA256=$PlanSHA256;RunRoot=$plan.run_root;
        Phases=$plan.phases;CompilerClosure=$policy;ToolchainMetadataFiles=$toolchain.Count;
        ToolchainMetadataBytes=[long](($toolchain|Measure-Object Bytes -Sum).Sum);
        ToolchainHashesPending=$true;NativeTypesLoaded=$false;LeaseAcquired=$false;StockFilesRead=$false;
        ExecutionValidated=$false;Ready=$false}|ConvertTo-Json -Depth 12
    return
}
foreach($type in @('IW7.CommunityBuild.BuildJob','IW7.AnimationRig.JobMembers','IW7HudFileIdentity','IW7ResourceMemoryV1')){
    if($type -as [type]){throw 'A fresh PowerShell host is required for source-bound helpers.'}
}
$runRoot=$plan.run_root;$work=Join-Path $runRoot 'work';$statePath=Join-Path $runRoot 'state.local.json'
$rigRoot=$PSScriptRoot
$guards=[Collections.Generic.List[IDisposable]]::new();$baselines=[Collections.Generic.List[object]]::new()
$sdkGuards=[Collections.Generic.List[IDisposable]]::new();$sdkBaselines=[Collections.Generic.List[object]]::new()
$lease=$null;$owner=$null;$closed=$true;$saved=$false;$created=$false;$group='native';$sourceIntact=$false
$state=[ordered]@{Schema='iw7.original-rig-chain-run/1';RecipeSHA256=$PlanSHA256;Work=$work;Inputs=@();Phases=@();
    Status='Preparing';Failure=$null;Restored=$false;StockPreserved=$false;RestorationStatus='Pending';
    CleanupError=$null;RetainedLeaseToken=$null;NativeLeaseReleased=$false;CompilerClosurePolicy=$policy;
    NativeDataVerified=$false;NativeSourceInputsUnchanged=$false;SourceInputsUnchanged=$false;InventoryVerified=$false;OfflineDataRoundtripVerified=$false;
    MaterialBindingVerified=$false;EngineWeightDirectionVerified=$false;RuntimeVerified=$false;Ready=$false;
    MaxObservedBytes=0L;FinalObservedBytes=$null}
$pins=[ordered]@{}
foreach($item in $bindings.Values){$pins[$item.Path]=$item.SHA256}
foreach($item in $plan.execution_input_hashes.PSObject.Properties){$pins[$item.Name]=$item.Value}
foreach($item in $plan.local_source_hashes_for_future_guards.PSObject.Properties){$pins[$item.Name]=$item.Value}
$pins[$PlanPath]=$PlanSHA256;$pins[$plan.python.path]=$plan.python.sha256
$pins[$plan.job_source.path]=$plan.job_source.sha256;$pins[$plan.candidate.Path]=$plan.candidate.SHA256
$pins[$policy.Telemetry]=$policy.TelemetrySHA256
$groupClock=[Diagnostics.Stopwatch]::StartNew()
function Save-RigState {if($created){Write-RigJson $state $statePath}}
function Measure-RigOutput {
    $exempt=@($state.Inputs|Where-Object {$_.Mode -ceq 'HardLink' -and $_.TargetId -and $_.TargetId -ceq $_.SourceId}|ForEach-Object Relative)
    $bytes=Measure-BeaconOutputFiles @(Get-ChildItem -LiteralPath $runRoot -File -Recurse -Force) $work $exempt
    $state.MaxObservedBytes=[math]::Max($state.MaxObservedBytes,$bytes)
    $limit=if($group -ceq 'native'){$plan.limits.native_artifact_stop_bytes}else{$plan.limits.ff_output_stop_bytes}
    if($bytes -lt 0 -or $bytes -gt $limit){throw 'Rig generated output exceeded the group bound.'}
    return $bytes
}
function Assert-RigRunningBudget {
    $seconds=if($group -ceq 'native'){300}else{$plan.limits.ff_group_seconds}
    if($groupClock.Elapsed.TotalSeconds -gt $seconds){throw 'Rig group deadline expired.'}
    if(Test-Path -LiteralPath (Join-Path $runRoot 'stop.request')){throw 'Coordinator requested owned stop.'}
    $null=Measure-RigOutput
    $memory=Get-IW7ResourceSnapshot
    if($memory.Committed -gt $memory.CommitLimit*0.85){throw 'Commit pressure exceeded 85 percent.'}
}
function Assert-RigSources {
    Assert-RigBaselines $baselines -Hashes
    if($group -ceq 'native'){
        Assert-RigToolchainInventory $toolchain $recipe.freeze_roots
        Assert-RigBaselines $sdkBaselines -Hashes
    }
    if($state.Inputs.Count){Assert-ModelFFInputs $state.Inputs $work -SourceOnly;Assert-FFStockContent $state.Inputs}
}
function Invoke-RigPhase([string]$Name,[string]$Hash) {
    Assert-RigRunningBudget
    # Fixed recipe, reconstituted from source above, never user-supplied argv.
    $phase=@($plan.phases|Where-Object id -CEQ $Name)
    if($phase.Count -ne 1 -or $phase[0].group -cne $group){throw 'Exact sequential phase required.'}
    $phase=$phase[0]
    if($group -ceq 'native'){Assert-RigToolchainInventory $toolchain $recipe.freeze_roots}
    Assert-RigBaselines $baselines
    $seconds=switch -Exact ($Name){compile {120} build {240} verify {240} dump {240} default {30}}
    $logs=Join-Path $runRoot $Name;$specPath=Join-Path $runRoot ($Name+'.spec.json')
    $spec=[ordered]@{schema='iw7.rig-chain-phase-spec/1';phase=$Name;exe=$phase.command[0];sha256=$Hash;
        arguments=@($phase.command|Select-Object -Skip 1);cwd=$phase.working_directory;logs=$logs;timeout=$seconds;environment=$environment}
    Write-RigNewJson $spec $specPath
    $specHash=(Get-FileHash -LiteralPath $specPath).Hash
    Add-RigGuard $specPath $specHash $guards $baselines
    $arguments=@('-I','-B',(Join-Path $rigRoot 'rig_phase.py'),'--spec',$specPath,'--spec-sha256',$specHash,
        '--sdk-phase',$bindings['sdk/modding/beacon_tool_phase.py'].Path)
    $quoted=ConvertTo-AnimationArguments $arguments
    # Prepare can fail after creating a native object; no returned object is NOT
    # evidence of closure. Retain guards/reservation if the factory is unknown.
    $script:closed=$false
    $script:owner=New-RigOwnedJob $plan.python.path $quoted $phase.working_directory
    $identity=Get-BeaconJobIdentity $owner $plan.python.path $Name
    $identity['JobRootExitedAtClose']=$false;$identity['SpecSHA256']=$specHash
    $state.Phases+=,$identity;Save-RigState
    $compilerEvidence=[ordered]@{CompilerIdentity=$null;LastObservation=$null;Completed=$false}
    if($Name -ceq 'compile'){$identity['CompilerClosure']=$compilerEvidence}
    $started=Get-RigMonotonicMs
    $observe={
        Assert-RigRunningBudget
        if($Name -ceq 'compile'){
            $observation=Get-RigOriginalJobMembers $owner
            Update-RigCompilerWitness $compilerEvidence $observation $identity.PID $policy
        }
    }
    $owner.Resume()
    $identity['ResourceRegistration']=Register-AnimationPhase $owner $lease.Token $observe
    Wait-RigOwnedPhase $owner $identity $started $seconds {
        param($sample)
        & $observe
        if($Name -ceq 'compile' -and $sample.RootExited -and $sample.ActiveProcesses -gt 0){
            $receipt=Read-BeaconJson (Join-Path $logs 'phase.json')
            $null=Complete-RigCompilerTelemetry $owner $sample $compilerEvidence.LastObservation $receipt $compilerEvidence $policy
        }
    }
    $script:closed=$true;$owner.Dispose();$script:owner=$null
    Save-RigState;Assert-RigRunningBudget
    $receipt=Read-BeaconJson (Join-Path $logs 'phase.json')
    Assert-RigPhaseResult $receipt $Name $Hash $specHash $identity
    $identity['ReceiptSHA256']=(Get-FileHash -LiteralPath (Join-Path $logs 'phase.json')).Hash
    Save-RigState
    [IO.File]::ReadAllText((Join-Path $logs 'stdout.log'))
}
try {
    # Hold source files while importing the admitted providers. SDK files are
    # inventoried above but hashed/guarded only after native admission below.
    foreach($path in $pins.Keys){$guards.Add([IO.File]::Open($path,'Open','Read','Read'));Assert-BeaconHash $path $pins[$path]}
    . $bindings['ops/Resource-Scheduler.Core.ps1'].Path
    $lease=Enter-IW7ResourceLease -Scope $runRoot -Kind Build -PhysicalBytes $plan.limits.native_proposed_physical_bytes -CommitBytes $plan.limits.native_proposed_commit_bytes -Owner 'Original rig native writer and independent read'
    $state.RetainedLeaseToken=$lease.Token
    Add-Type -LiteralPath $plan.job_source.path
    Add-Type -LiteralPath $bindings['ops/hud-lab/HudFileIdentity.cs'].Path
    Add-Type -LiteralPath (Join-Path $PSScriptRoot 'Rig.JobMembers.cs')
    foreach($path in $pins.Keys){Add-RigGuard $path $pins[$path] $guards $baselines}
    Assert-RigToolchainInventory $toolchain $recipe.freeze_roots
    foreach($item in $toolchain){Add-RigGuard $item.Path $null $sdkGuards $sdkBaselines}
    Assert-RigToolchainInventory $toolchain $recipe.freeze_roots
    if(Test-Path -LiteralPath $runRoot){throw 'Fresh rig run root appeared during admission; preserve it.'}
    New-Item -ItemType Directory -Path $runRoot -ErrorAction Stop|Out-Null;$created=$true
    [IO.Directory]::CreateDirectory((Join-Path $runRoot 'build/tmp'))|Out-Null
    $sdkManifest=Join-Path $runRoot 'toolchain-freeze.local.json'
    Write-RigNewJson @($sdkBaselines) $sdkManifest
    $state.ToolchainFreeze=[ordered]@{Path=$sdkManifest;SHA256=(Get-FileHash -LiteralPath $sdkManifest).Hash;Files=$sdkBaselines.Count}
    Add-RigGuard $sdkManifest $state.ToolchainFreeze.SHA256 $guards $baselines
    $windows=[Environment]::GetFolderPath('Windows')
    $null=Resolve-IW7BasePath (Split-Path $windows) (Split-Path $windows -Leaf)
    $environment=[ordered]@{SystemRoot=$windows;WINDIR=$windows;
        PATH=((Split-Path $policy.Compiler),(Join-Path $windows 'System32'),$windows -join ';');
        TEMP=(Join-Path $runRoot 'build/tmp');TMP=(Join-Path $runRoot 'build/tmp');
        INCLUDE=($recipe.include_paths -join ';');LIB=($recipe.library_paths -join ';');
        PYTHONNOUSERSITE='1';PYTHONDONTWRITEBYTECODE='1'}
    $state.Environment=$environment;$state.Status='Compiling';Save-RigState
    $null=Invoke-RigPhase compile $policy.CompilerSHA256
    $writer=Join-Path $runRoot 'build/two-bone-writer.exe'
    Assert-RigArtifact $writer 32MB
    $writerHash=(Get-FileHash -LiteralPath $writer).Hash
    Add-RigGuard $writer $writerHash $guards $baselines
    $state.Writer=[ordered]@{SHA256=$writerHash;Bytes=(Get-Item -LiteralPath $writer).Length}
    foreach($profile in 'first','second'){
        $emission=(Invoke-RigPhase ('emit-'+$profile) $writerHash)|ConvertFrom-Json
        Assert-RigEmission $emission $profile
        foreach($input in @($plan.staged_profile_inputs|Where-Object {$_.source -like "*/native/$profile/*" -or $_.source -like "*\native\$profile\*"})){
            Assert-RigArtifact $input.source 64KB
            Add-RigGuard $input.source $null $guards $baselines
        }
    }
    Assert-RigNativeInventory $plan
    $readback=(Invoke-RigPhase read-native $plan.python.sha256)|ConvertFrom-Json
    Assert-RigReader $readback
    Assert-RigReaderBindings $readback $plan
    $state.NativeReadback=$readback;$state.NativeDataVerified=$true
    Assert-RigSources
    $state.NativeSourceInputsUnchanged=$true
    # SDK guards can close only after the complete native group and final proof.
    foreach($guard in $sdkGuards){$guard.Dispose()};$sdkGuards.Clear()
    Exit-IW7ResourceLease -Token $lease.Token
    $state.RetainedLeaseToken=$null;$lease=$null;$state.NativeLeaseReleased=$true;Save-RigState

    $group='ff';$groupClock.Restart()
    $lease=Enter-IW7ResourceLease -Scope $work -Kind Extract -PhysicalBytes $plan.limits.ff_physical_bytes -CommitBytes $plan.limits.ff_commit_bytes -Owner 'Original rig FF build inventory dump independent read'
    $state.RetainedLeaseToken=$lease.Token;Save-RigState
    Assert-RigBaselines $baselines -Hashes
    $candidateRoot=Split-Path (Split-Path $plan.candidate.Path)
    $null=Assert-BeaconCandidate $candidateRoot $plan.candidate.ArtifactSHA256
    $stock=$plan.stock_receipts
    foreach($pair in @(@($stock.baseline,$stock.baseline_sha256),@($stock.binding,$stock.binding_sha256),@($stock.reviewed,$stock.reviewed_sha256))){Assert-BeaconHash $pair[0] $pair[1]}
    $state.Inputs=@(Get-AnimationStockInputs (Read-BeaconJson $stock.baseline) $stock.root (Read-BeaconJson $stock.binding) (Read-BeaconJson $stock.reviewed) $stock.reviewed_sha256)
    $csvEntry=@($plan.staged_profile_inputs|Where-Object mode -CEQ CreateNew)[0]
    [IO.Directory]::CreateDirectory((Split-Path $csvEntry.source))|Out-Null
    Write-RigNewText $plan.zone_csv $csvEntry.source
    Add-RigGuard $csvEntry.source $csvEntry.sha256 $guards $baselines
    foreach($input in $plan.staged_profile_inputs){
        $file=Get-Item -LiteralPath $input.source
        $state.Inputs+=,[pscustomobject]@{Relative=$input.relative;Source=$file.FullName;Mode='HardLink';Bytes=$file.Length;
            ModifiedUtc=$file.LastWriteTimeUtc.ToString('o');Attributes=[int]$file.Attributes}
    }
    if($state.Inputs.Count -ne 79){throw 'Exactly 79 staged entries required.'}
    foreach($entry in $state.Inputs){
        $null=Resolve-IW7BasePath (Split-Path $entry.Source) (Split-Path $entry.Source -Leaf)
        $guards.Add([IO.File]::Open($entry.Source,'Open','Read','Read'))
        $sourceId=[IW7HudFileIdentity]::Read($entry.Source)
        Assert-FFStockIdentity $entry $sourceId;Set-RigSourceIdentity $entry $sourceId
    }
    Assert-FFStockContent $state.Inputs;Assert-ModelFFInputs $state.Inputs $work -SourceOnly
    [IO.Directory]::CreateDirectory($work)|Out-Null
    $state.Transaction=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$work;MutableFiles=@($state.Inputs.Relative)+@('zone/sdk_original_rig_probe.ff');ProfileDirectory='unused';ProfileDirectories=@()}) (Join-Path $runRoot 'backup')
    $saved=$true;Save-RigState
    foreach($entry in $state.Inputs){
        $target=Resolve-IW7BasePath $work $entry.Relative
        [IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
        if($entry.Mode -ceq 'Copy'){Copy-Item -LiteralPath $entry.Source -Destination $target}else{New-Item -ItemType HardLink -Path $target -Target $entry.Source|Out-Null}
        $entry|Add-Member NoteProperty TargetId ([IW7HudFileIdentity]::Read($target))
        if($entry.Mode -ceq 'HardLink' -and $entry.TargetId -cne $entry.SourceId){throw 'Staged hardlink identity differs.'}
        if($entry.Mode -ceq 'Copy'){
            Assert-RigCopyIdentity $entry $entry.TargetId
            $copy=Get-Item -LiteralPath $target;if($copy.IsReadOnly){$copy.IsReadOnly=$false}
        }
    }
    Assert-ModelFFInputs $state.Inputs $work
    $state.Status='BuildingFF';Save-RigState
    $buildLog=Invoke-RigPhase build $plan.candidate.SHA256
    if($buildLog -match 'could not be found|Could not find referenced|\[ ERROR \]|\[ FATAL \]' -or
       !$buildLog.Contains('Parsing xanim "paris_original_probe_bend"...')){throw 'Original rig build parsing failed.'}
    $ff=Resolve-IW7BasePath $work 'zone/sdk_original_rig_probe.ff'
    Assert-RigArtifact $ff 1MB
    Copy-Item -LiteralPath $ff -Destination (Join-Path $runRoot 'mod.ff')
    $state.FF=[ordered]@{Bytes=(Get-Item -LiteralPath $ff).Length;SHA256=(Get-FileHash -LiteralPath $ff).Hash;Path='mod.ff'}
    $rows=@(Get-RigInventory (Invoke-RigPhase verify $plan.candidate.SHA256))
    Write-RigNewText (($rows -join "`n")+"`n") (Join-Path $runRoot 'assets.csv')
    $state.InventoryVerified=$true;Save-RigState
    $null=Invoke-RigPhase dump $plan.candidate.SHA256
    foreach($dump in $plan.retain_redumps_before_restore){
        Assert-RigArtifact $dump.source $dump.max_bytes
        [IO.Directory]::CreateDirectory((Split-Path $dump.retained))|Out-Null
        Copy-Item -LiteralPath $dump.source -Destination $dump.retained
        Add-RigGuard $dump.retained $null $guards $baselines
    }
    $readback=(Invoke-RigPhase read-ff $plan.python.sha256)|ConvertFrom-Json
    Assert-RigReader $readback -FF;Assert-RigReaderBindings $readback $plan -FF
    $state.FFReadback=$readback;$state.OfflineDataRoundtripVerified=$true
    $state.Status='OfflineRigDataVerified';Save-RigState
} catch {$state.Failure=$_.Exception.Message;$state.Status='Failed';throw}
finally {
    if($owner){
        $state.StopEvidence=[ordered]@{}
        $closed=Stop-RigOwnedPhase $owner $state.StopEvidence
        if($closed){$owner.Dispose();$owner=$null}
    }
    try{Assert-RigSources;$sourceIntact=$true;$state.SourceInputsUnchanged=$true}catch{$sourceIntact=$false;$state.CleanupError=$_.Exception.Message}
    if($closed -and $sourceIntact){
        foreach($guard in $sdkGuards){$guard.Dispose()};$sdkGuards.Clear()
        try{
            $done=Complete-RigGroup $state $closed $sourceIntact $saved $guards {
                Complete-ModelFFRestore $state $statePath $lease.Token
            } {
                if($lease){Exit-IW7ResourceLease -Token $lease.Token;$state.RetainedLeaseToken=$null}
            }
            if($done){$lease=$null}
        }catch{
            $state.CleanupError=$_.Exception.Message;$state.Status='Failed'
        }
    }
    if(!$closed -or !$sourceIntact -or $state.RetainedLeaseToken){
        $state.Status='Failed'
        $state.CleanupError='Closure, source proof or restoration incomplete; preserve guards and reservation. '+$state.CleanupError
        [AppDomain]::CurrentDomain.SetData(('IW7.Rig.Quarantine.'+$state.RetainedLeaseToken),@{Owner=$owner;Guards=$guards;SdkGuards=$sdkGuards;State=$state})
    }
    if($created){
        try{Save-RigFinalCounters $state {Save-RigState} {Measure-RigOutput}}
        catch{$state.Status='Failed';$state.Failure=$_.Exception.Message;Save-RigState;throw}
    }
}
if($state.RetainedLeaseToken -or !$state.Restored -or !$state.StockPreserved){throw 'Rig chain cleanup incomplete.'}
$state|ConvertTo-Json -Depth 35
