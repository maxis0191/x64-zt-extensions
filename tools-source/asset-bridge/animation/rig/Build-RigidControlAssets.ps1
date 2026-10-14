param(
    [Parameter(Mandatory)][string]$PlanPath,
    [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$PlanSHA256,
    [string]$SourcePackage=(Join-Path (Split-Path (Split-Path (Split-Path (Split-Path $PSScriptRoot)))) 'runtime/rigid-control-command-inputs-20261014-a'),
    [string]$PreparedSource='C:\Users\ezvalo\Documents\IW7-Runtime\original-rig-rigid-control-source-20261014-a',
    [string]$Python='C:\Users\ezvalo\AppData\Local\Programs\Python\Python312\python.exe',
    [ValidateSet('Emit','FF')][string]$Group='Emit',
    [string]$RootGO,
    [switch]$Run
)
$ErrorActionPreference='Stop'
$contextKey='IW7.RigidControlAssets.HostContext'
$sourceGuards=[Collections.Generic.List[IDisposable]]::new()
$sourceBaselines=[Collections.Generic.List[object]]::new()
$rcaContext=$null
try {
    # Read only text sources/receipts in plan mode. Executable paths may be absent.
    $PlanPath=[IO.Path]::GetFullPath($PlanPath)
    $sourceGuards.Add([IO.File]::Open($PlanPath,'Open','Read','Read'))
    if((Get-Item -LiteralPath $PlanPath).Length -gt 64KB -or (Get-FileHash -LiteralPath $PlanPath).Hash -ine $PlanSHA256){throw 'Bounded hash-bound source plan required.'}
    $plan=[IO.File]::ReadAllText($PlanPath)|ConvertFrom-Json
    $core=Join-Path $PSScriptRoot 'RigidControlAssets.Core.ps1'
    $sourceGuards.Add([IO.File]::Open($core,'Open','Read','Read'));$sourceGuards.Add([IO.File]::Open($PSCommandPath,'Open','Read','Read'))
    . $core
    Assert-RCAPlan $plan
    $manifestPath=Join-Path $SourcePackage 'source-workspace.json'
    $sourceGuards.Add([IO.File]::Open($manifestPath,'Open','Read','Read'))
    if((Get-FileHash -LiteralPath $manifestPath).Hash -ine 'ffdfa56d3db82aa9e305a9605fcc7ab4f45a48a1973ecaf74bfa070e34427af8'){throw 'Frozen source provider package required.'}
    $manifest=[IO.File]::ReadAllText($manifestPath)|ConvertFrom-Json
    $providerNames=@('ops/Base-Client.Core.ps1','sdk/modding/BeaconFF.Core.ps1','ops/model-lab/ModelFF.Core.ps1',
        'tools-source/asset-bridge/common/StockBinding.Core.ps1','tools-source/asset-bridge/animation/AnimationFF.Core.ps1',
        'tools-source/asset-bridge/animation/rig/Rig.Core.ps1','ops/Resource-Scheduler.Core.ps1','ops/Resource-Memory.ps1',
        'ops/Resource-RecorderOwnedProcess.Core.ps1','ops/native/ResourceMemory.cs','ops/hud-lab/HudFileIdentity.cs',
        'tools-source/asset-bridge/model/BuildJob.cs','tools-source/asset-bridge/animation/rig/Rig.JobMembers.cs',
        'tools-source/asset-bridge/animation/rig/rig_phase.py','sdk/modding/beacon_tool_phase.py')
    $textPins=[ordered]@{};$textPins[$PlanPath]=$PlanSHA256
    $textPins[$core]=(Get-FileHash -LiteralPath $core).Hash;$textPins[$PSCommandPath]=(Get-FileHash -LiteralPath $PSCommandPath).Hash
    $textPins[$manifestPath]='ffdfa56d3db82aa9e305a9605fcc7ab4f45a48a1973ecaf74bfa070e34427af8'
    foreach($name in $providerNames){
        $row=@($manifest.files|Where-Object path -CEQ $name)
        if($row.Count -ne 1){throw ('Missing exact text provider: '+$name)}
        $path=Join-Path $SourcePackage $name;$sourceGuards.Add([IO.File]::Open($path,'Open','Read','Read'))
        if((Get-FileHash -LiteralPath $path).Hash -ine $row[0].sha256){throw ('Provider source changed: '+$name)}
        $textPins[$path]=$row[0].sha256
    }
    foreach($name in $providerNames|Where-Object {$_ -like '*.ps1' -and $_ -notin 'ops/Resource-Scheduler.Core.ps1','ops/Resource-Memory.ps1','ops/Resource-RecorderOwnedProcess.Core.ps1'}){
        $path=Join-Path $SourcePackage $name;$errors=$null;$tokens=$null
        $ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
        if($errors.Count -or @($ast.EndBlock.Statements|Where-Object {$_ -isnot [Management.Automation.Language.FunctionDefinitionAst]}).Count){throw 'Pure function provider required.'}
        . $path
    }
    $sourceManifestPath=Join-Path $PreparedSource 'source-manifest.json'
    $sourceGuards.Add([IO.File]::Open($sourceManifestPath,'Open','Read','Read'))
    Assert-BeaconHash $sourceManifestPath '5811ef3ebcd5948eb394ab4a720ec37de4f9a902788774da10d47b8d59a55b5b'
    $textPins[$sourceManifestPath]='5811ef3ebcd5948eb394ab4a720ec37de4f9a902788774da10d47b8d59a55b5b'
    $sourceManifest=Read-BeaconJson $sourceManifestPath
    if($sourceManifest.schema -cne 'iw7.original-rig-rigid-control-source-manifest/1' -or !$sourceManifest.source_only -or $sourceManifest.compiled -or $sourceManifest.ff_built){throw 'Original source-only rigid manifest required.'}
    foreach($row in $sourceManifest.generated.PSObject.Properties){
        $path=Resolve-IW7BasePath $PreparedSource $row.Name;$sourceGuards.Add([IO.File]::Open($path,'Open','Read','Read'))
        Assert-BeaconHash $path $row.Value.sha256;$textPins[$path]=$row.Value.sha256
    }
    # This exact source performs complete rigid/packed/root/bounds/material assertions.
    # Its stdout intentionally makes no claim of shader interpretation or runtime draw.
    Assert-BeaconHash $plan.CPPClosure $plan.CPPClosureSHA256
    $sourceGuards.Add([IO.File]::Open($plan.CPPClosure,'Open','Read','Read'));$textPins[$plan.CPPClosure]=$plan.CPPClosureSHA256
    $cppClosure=Read-BeaconJson $plan.CPPClosure
    if($cppClosure.Schema -cne 'iw7.original-rig-rigid-writer-cpp-closure/1' -or $cppClosure.Status -cne 'CompilePassedRestored' -or
       !$cppClosure.SourceInputsUnchanged -or !$cppClosure.Restored -or !$cppClosure.LeaseReleased -or
       !$cppClosure.AllOwnedProcessesAbsent -or !$cppClosure.HeavyProcessesAbsent -or $cppClosure.RegistryLeaseCount -ne 0 -or
       $cppClosure.OriginalPTYExitCode -ne 0 -or (@($cppClosure.Writers|ConvertTo-Json -Depth 8 -Compress) -join '') -cne (@($plan.Writers|ConvertTo-Json -Depth 8 -Compress) -join '')){throw 'Closed exact compiled writer pair required.'}
    if(!$Run){
        [ordered]@{Schema='iw7.original-rig-rigid-assets-default/1';PlanSHA256=$PlanSHA256;Group=$Group;RunRoot=$plan.RunRoot;
            Phases=$plan.Phases;ExpectedInventory=(Get-RCAInventory);SourcePins=$textPins;
            NativeExecutableHashesRead=$false;NativeTypesLoaded=$false;LeaseAcquired=$false;EmitExecuted=$false;
            Fastfile=$null;FFBuilt=$false;ReadbackVerified=$false;GPUVerified=$false;PixelsVerified=$false;Ready=$false}|ConvertTo-Json -Depth 15
        return
    }
    $bundledHost='C:\Users\ezvalo\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    if([Environment]::GetCommandLineArgs() -inotcontains '-NoExit' -or [Environment]::ProcessPath -ine $bundledHost){throw 'Run requires the original bundled persistent pwsh -NoExit host before admission.'}
    if($RootGO -cne ($Group+':'+$PlanSHA256.ToLowerInvariant())){throw 'Separate exact Root GO required for this group before admission.'}
    $rcaContext=[AppDomain]::CurrentDomain.GetData($contextKey)
    if($Group -ceq 'Emit'){
        if($rcaContext -or (Test-Path -LiteralPath $plan.RunRoot)){throw 'Existing context/run root preserved; no new emission.'}
        foreach($type in 'IW7.CommunityBuild.BuildJob','IW7.AnimationRig.JobMembers','IW7HudFileIdentity','IW7ResourceMemoryV1'){
            if($type -as [type]){throw 'Fresh source-bound original host required.'}
        }
        $rcaState=[ordered]@{Schema='iw7.original-rig-rigid-assets-run/1';HostPID=$PID;PlanSHA256=$PlanSHA256;RunRoot=$plan.RunRoot;
            Status='Preparing';Group=$Group;Phases=@();Groups=@();Native=@();Redumps=@();Readbacks=@();Fastfile=$null;Failure=$null;CleanupError=$null;
            SourceInputsUnchanged=$false;Restored=$false;LeaseReleased=$false;RetainedLeaseToken=$null;
            EmitExecuted=$false;InventoryVerified=$false;ReadbackVerified=$false;FFBuilt=$false;ContextReleased=$false;GPUVerified=$false;PixelsVerified=$false;Ready=$false}
        $rcaContext=[ordered]@{Plan=$plan;PlanSHA256=$PlanSHA256;SourcePackage=$SourcePackage;Python=$Python;HostPID=$PID;
            State=$rcaState;StatePath=(Join-Path $plan.RunRoot 'state.local.json');Guards=$sourceGuards;Baselines=$sourceBaselines;
            Owner=$null;Closed=$true;Lease=$null;SourceIntact=$false;Transaction=$null;Saved=$false;Inputs=@();Work=$null;Created=$false;TextPins=$textPins}
        [AppDomain]::CurrentDomain.SetData($contextKey,$rcaContext) # Original context exists before admission/factory.
        $sourceGuards=$null
    }else{
        if(!$rcaContext -or $rcaContext.HostPID -ne $PID -or $rcaContext.PlanSHA256 -ine $PlanSHA256 -or
           $rcaContext.SourcePackage -ine $SourcePackage -or $rcaContext.Python -ine $Python -or !$rcaContext.State.EmitExecuted -or
           !$rcaContext.Closed -or $rcaContext.Owner -or $rcaContext.Lease -or !$rcaContext.State.Restored -or $rcaContext.State.Failure -or $rcaContext.State.FFBuilt){
            throw 'FF requires the successfully closed/restored Emit context in its original host.'
        }
        foreach($path in $textPins.Keys){if(!$rcaContext.TextPins.Contains($path) -or $rcaContext.TextPins[$path] -ine $textPins[$path]){throw 'Original operator/provider text changed between groups.'}}
        foreach($guard in $sourceGuards){$guard.Dispose()};$sourceGuards=$null
    }
}finally{if($sourceGuards){foreach($guard in $sourceGuards){$guard.Dispose()}}}

$rcaContext.Work=Join-Path $plan.RunRoot $(if($Group -ceq 'Emit'){'emit-work'}else{'ff-work'})
$rcaContext.State.Group=$Group;$rcaContext.State.Restored=$false;$rcaContext.State.LeaseReleased=$false
$rcaContext.Saved=$false;$rcaContext.Transaction=$null;$rcaContext.SourceIntact=$false
$groupClock=[Diagnostics.Stopwatch]::StartNew()
function Assert-RCAWorkingBudget {
    if($groupClock.Elapsed.TotalSeconds -gt 900 -or (Test-Path -LiteralPath (Join-Path $plan.RunRoot 'stop.request'))){throw 'Finite group stopped/expired.'}
    Assert-RigBaselines $rcaContext.Baselines
    if($rcaContext.Inputs.Count){Assert-ModelFFInputs $rcaContext.Inputs $rcaContext.Work -SourceOnly}
    $files=@(Get-ChildItem -LiteralPath $plan.RunRoot -File -Recurse -Force)
    $exempt=@($rcaContext.Inputs|Where-Object {$_.Mode -ceq 'HardLink' -and $_.TargetId -and $_.TargetId -ceq $_.SourceId}|ForEach-Object Relative)
    $bytes=Measure-BeaconOutputFiles $files $rcaContext.Work $exempt
    if($bytes -gt 64MB){throw 'Rigid consumer output exceeded 64MiB.'}
}
try {
    . (Join-Path $SourcePackage 'ops/Resource-Scheduler.Core.ps1')
    # Keep the established full FF estimate as telemetry; it is not a headroom gate.
    $physicalEstimate=if($Group -ceq 'Emit'){2GB}else{8GB}
    $commitEstimate=if($Group -ceq 'Emit'){3GB}else{11GB}
    $rcaContext.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind $(if($Group -ceq 'Emit'){'Build'}else{'Extract'}) -PhysicalBytes $physicalEstimate -CommitBytes $commitEstimate -Owner ('Original rigid '+$Group+' group')
    $rcaContext.State.RetainedLeaseToken=$rcaContext.Lease.Token
    if(!$rcaContext.Created){
        [IO.Directory]::CreateDirectory((Split-Path $plan.RunRoot))|Out-Null
        New-Item -ItemType Directory -Path $plan.RunRoot -ErrorAction Stop|Out-Null;$rcaContext.Created=$true
        # Add-RigGuard records NTFS identity and therefore needs this reviewed type.
        Add-Type -LiteralPath (Join-Path $SourcePackage 'tools-source/asset-bridge/model/BuildJob.cs')
        Add-Type -LiteralPath (Join-Path $SourcePackage 'ops/hud-lab/HudFileIdentity.cs')
        Add-Type -LiteralPath (Join-Path $SourcePackage 'tools-source/asset-bridge/animation/rig/Rig.JobMembers.cs')
        foreach($path in $textPins.Keys){Add-RigGuard $path $textPins[$path] $rcaContext.Guards $rcaContext.Baselines}
        Add-RigGuard $Python '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a' $rcaContext.Guards $rcaContext.Baselines
        foreach($writer in $plan.Writers){Add-RigGuard $writer.Files[0].Path $writer.Files[0].SHA256 $rcaContext.Guards $rcaContext.Baselines}
    }
    [IO.Directory]::CreateDirectory($rcaContext.Work)|Out-Null
    if($Group -ceq 'FF'){
        foreach($name in 'baseline','binding','reviewed'){
            $receipt=$plan.StockReceipts.$name;$hash=$plan.StockReceipts.($name+'_sha256')
            Add-RigGuard $receipt $hash $rcaContext.Guards $rcaContext.Baselines
        }
        $rcaContext.Inputs=@(Get-AnimationStockInputs (Read-BeaconJson $plan.StockReceipts.baseline) $plan.StockReceipts.root `
            (Read-BeaconJson $plan.StockReceipts.binding) (Read-BeaconJson $plan.StockReceipts.reviewed) $plan.StockReceipts.reviewed_sha256)
        # Opaque candidate bytes/stock are qualified only inside this FF reservation.
        Add-RigGuard $plan.Candidate.Path $plan.Candidate.SHA256 $rcaContext.Guards $rcaContext.Baselines
        $candidateRoot=Split-Path (Split-Path $plan.Candidate.Path)
        $artifactPath=Join-Path $candidateRoot 'build-artifact.local.json'
        Add-RigGuard $artifactPath $plan.Candidate.ArtifactSHA256 $rcaContext.Guards $rcaContext.Baselines
        $artifactReceipt=Read-BeaconJson $artifactPath
        Add-RigGuard (Join-Path $candidateRoot 'preparation.local.json') $artifactReceipt.preparation_sha256 $rcaContext.Guards $rcaContext.Baselines
        Add-RigGuard (Join-Path $candidateRoot 'result.local.json') $artifactReceipt.result_sha256 $rcaContext.Guards $rcaContext.Baselines
        $candidate=Assert-BeaconCandidate (Split-Path (Split-Path $plan.Candidate.Path)) $plan.Candidate.ArtifactSHA256
        if($candidate.Path -ine $plan.Candidate.Path -or $candidate.SHA256 -ine $plan.Candidate.SHA256){throw 'Reviewed exact candidate tuple required.'}
        $additional=@([pscustomobject]@{Relative='zonetool.exe';Source=$plan.Candidate.Path;Mode='HardLink'})
        foreach($pair in Get-RCANativePairs){$additional+=,[pscustomobject]@{Relative=$pair.Relative;Source=(Join-Path $plan.RunRoot ('native/'+$pair.Profile+'/'+$pair.Relative));Mode='HardLink'}}
        $additional+=,[pscustomobject]@{Relative=('zone_source/'+$plan.Zone+'.csv');Source=(Join-Path $PreparedSource ('zone_source/'+$plan.Zone+'.csv'));Mode='HardLink'}
        foreach($entry in $additional){
            $f=Get-Item -LiteralPath $entry.Source;$entry|Add-Member NoteProperty Bytes $f.Length
            $entry|Add-Member NoteProperty ModifiedUtc $f.LastWriteTimeUtc.ToString('o');$entry|Add-Member NoteProperty Attributes ([int]$f.Attributes)
        }
        $rcaContext.Inputs+=@($additional)
        if($rcaContext.Inputs.Count -ne 78){throw 'Exactly 78 staged inputs required.'}
        foreach($entry in $rcaContext.Inputs){
            Add-RigGuard $entry.Source $null $rcaContext.Guards $rcaContext.Baselines
            $id=[IW7HudFileIdentity]::Read($entry.Source);Assert-FFStockIdentity $entry $id;Set-RigSourceIdentity $entry $id
        }
        Assert-FFStockContent $rcaContext.Inputs;Assert-ModelFFInputs $rcaContext.Inputs $rcaContext.Work -SourceOnly
    }
    $directories=@('tmp')
    if($Group -ceq 'FF'){$directories+=@('dump')+@($rcaContext.Inputs.Relative|Where-Object {$_ -match '/'}|ForEach-Object {($_ -split '/')[0]}|Sort-Object -Unique)}
    $mutables=@($rcaContext.Inputs.Relative)
    if($Group -ceq 'FF'){$mutables+=('zone/'+$plan.Zone+'.ff')}
    $rcaContext.Transaction=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$rcaContext.Work;MutableFiles=$mutables;ProfileDirectory='unused';ProfileDirectories=$directories}) (Join-Path $plan.RunRoot ('backup-'+$Group))
    $rcaContext.Saved=$true
    [IO.Directory]::CreateDirectory((Join-Path $rcaContext.Work 'tmp'))|Out-Null
    foreach($entry in $rcaContext.Inputs){
        $target=Resolve-IW7BasePath $rcaContext.Work $entry.Relative;[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
        if($entry.Mode -ceq 'Copy'){Copy-Item -LiteralPath $entry.Source -Destination $target}else{New-Item -ItemType HardLink -Path $target -Target $entry.Source|Out-Null}
        $targetID=[IW7HudFileIdentity]::Read($target);$entry|Add-Member NoteProperty TargetId $targetID
        if($entry.Mode -ceq 'HardLink' -and $targetID -cne $entry.SourceId){throw 'Staged hardlink identity differs.'}
        if($entry.Mode -ceq 'Copy'){Assert-RigCopyIdentity $entry $targetID;$copy=Get-Item -LiteralPath $target;if($copy.IsReadOnly){$copy.IsReadOnly=$false}}
    }
    if($rcaContext.Inputs.Count){Assert-ModelFFInputs $rcaContext.Inputs $rcaContext.Work}
    foreach($phase in $plan.Phases|Where-Object Group -CEQ $Group){
        $rcaContext.State.Status=$phase.Id;Write-RigJson $rcaContext.State $rcaContext.StatePath
        $phaseText=Invoke-RCAPhase $rcaContext $phase {Assert-RCAWorkingBudget}
        if($phase.Id -like 'emit-*'){
            $profile=$phase.Id.Substring(5);$roundtrip=$phaseText|ConvertFrom-Json;Assert-RCARoundtrip $roundtrip
            $files=@(foreach($pair in Get-RCANativePairs|Where-Object Profile -CEQ $profile){
                $p=Join-Path $plan.RunRoot ('native/'+$profile+'/'+$pair.Relative);Assert-RigArtifact $p 64KB
                $hash=(Get-FileHash -LiteralPath $p).Hash;Add-RigGuard $p $hash $rcaContext.Guards $rcaContext.Baselines
                [ordered]@{Path=$p;Bytes=(Get-Item -LiteralPath $p).Length;SHA256=$hash}
            })
            if(@(Get-ChildItem -LiteralPath (Join-Path $plan.RunRoot ('native/'+$profile)) -File -Recurse -Force).Count -ne 2){throw 'Only one native model/surface pair permitted.'}
            $rcaContext.State.Native+=,[ordered]@{Profile=$profile;Roundtrip=$roundtrip;Files=$files}
        }elseif($phase.Id -ceq 'verify'){
            $rows=@(Assert-RCAInventory $phaseText);Write-RigNewText (($rows -join "`n")+"`n") (Join-Path $plan.RunRoot 'assets.csv')
            $rcaContext.State.InventoryVerified=$true
        }elseif($phase.Id -ceq 'dump'){
            foreach($kind in 'xmodel','xsurface'){
                $dumpKind=Join-Path $rcaContext.Work ('dump/'+$plan.Zone+'/'+$kind)
                if(@(Get-ChildItem -LiteralPath $dumpKind -File -Recurse -Force).Count -ne 2){throw 'Exact closed two-model redump inventory required.'}
            }
            $rcaContext.State['RetainedFF']=Add-RCARetainedFile $rcaContext (Join-Path $rcaContext.Work ('zone/'+$plan.Zone+'.ff')) (Join-Path $plan.RunRoot 'retained/mod.ff') 1MB
            foreach($pair in Get-RCANativePairs){
                $redumpFile=Add-RCARetainedFile $rcaContext (Join-Path $rcaContext.Work ('dump/'+$plan.Zone+'/'+$pair.Relative)) `
                    (Join-Path $plan.RunRoot ('redump/'+$pair.Profile+'/'+$pair.Relative)) 64KB
                $rcaContext.State.Redumps+=,[ordered]@{Profile=$pair.Profile;Relative=$pair.Relative;File=$redumpFile}
            }
        }elseif($phase.Id -like 'read-ff-*'){
            $roundtrip=$phaseText|ConvertFrom-Json;Assert-RCARoundtrip $roundtrip
            $rcaContext.State.Readbacks+=,[ordered]@{Profile=$phase.Id.Substring(8);Roundtrip=$roundtrip}
        }
    }
    if($Group -ceq 'Emit'){$rcaContext.State.EmitExecuted=$true}else{
        if(!$rcaContext.State.InventoryVerified -or $rcaContext.State.Readbacks.Count -ne 2 -or $rcaContext.State.Redumps.Count -ne 4 -or !$rcaContext.State.RetainedFF){throw 'Complete true FF tuple required.'}
        $rcaContext.State.ReadbackVerified=$true
    }
    $rcaContext.State.Status=$Group+'Passed'
}catch{$rcaContext.State.Failure=$_.Exception.Message;$rcaContext.State.Status='Failed';throw}
finally {
    if($rcaContext.Owner){
        $stopProof=[ordered]@{};$rcaContext.Closed=Stop-RigOwnedPhase $rcaContext.Owner $stopProof
        $rcaContext.State['StopEvidence']=$stopProof
        if($rcaContext.Closed){$rcaContext.Owner.Dispose();$rcaContext.Owner=$null}
    }
    try{
        Assert-RigBaselines $rcaContext.Baselines -Hashes
        if($rcaContext.Inputs.Count){Assert-ModelFFInputs $rcaContext.Inputs $rcaContext.Work;Assert-FFStockContent $rcaContext.Inputs}
        $rcaContext.SourceIntact=$true
        if(Complete-RCAGroup $rcaContext){
            $rcaContext.State.Groups+=,[ordered]@{Group=$Group;Restored=$true;LeaseReleased=$true;Closed=$true;Passed=(!$rcaContext.State.Failure)}
            if($Group -ceq 'FF' -and !$rcaContext.State.Failure -and $rcaContext.State.ReadbackVerified){
                $rcaContext.State.Fastfile=$rcaContext.State.RetainedFF;$rcaContext.State.FFBuilt=$true
                $rcaContext.State.Status='FFInventoryRigidRoundtripPassedRestored'
            }elseif(!$rcaContext.State.Failure){$rcaContext.State.Status='EmitPassedRestored'}
        }else{$rcaContext.State.CleanupError='Closure/source proof incomplete; original context, handles, guards and lease retained.'}
    }catch{$rcaContext.State.CleanupError=$_.Exception.Message}
    if($rcaContext.Created){Write-RigJson $rcaContext.State $rcaContext.StatePath}
    # Keep the original AppDomain context and guards through both separate groups.
    # Failed/unknown cleanup is recoverable only in this exact persistent host.
}
if($rcaContext.Lease -or !$rcaContext.State.Restored -or $rcaContext.State.Failure -or $rcaContext.State.CleanupError){throw 'Group incomplete; preserve and inspect original host context.'}
if($Group -ceq 'FF'){
    # Successful Emit needs its guards for FF; successful FF ends the finite pair.
    foreach($guard in $rcaContext.Guards){$guard.Dispose()}
    $rcaContext.State.ContextReleased=$true
    Write-RigJson $rcaContext.State $rcaContext.StatePath
    [AppDomain]::CurrentDomain.SetData($contextKey,$null)
}
$rcaContext.State|ConvertTo-Json -Depth 20
