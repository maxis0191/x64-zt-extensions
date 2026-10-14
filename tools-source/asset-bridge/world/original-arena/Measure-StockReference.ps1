param([Parameter(Mandatory)][string]$PackageRoot,[Parameter(Mandatory)][string]$RunRoot,
    [Parameter(Mandatory)][string]$StockBindingPlan,[Parameter(Mandatory)][string]$StockBindingPlanSHA256,
    [Parameter(Mandatory)][string]$ToolSource,[Parameter(Mandatory)][string]$CandidateRoot,
    [Parameter(Mandatory)][string]$CandidateArtifactSHA256,[Parameter(Mandatory)][string]$NativeJobAssembly,
    [string]$PlanSHA256,[switch]$LoadDiagnostic,[switch]$Run)
# Default hashes only small source/receipt files. No native type, stock reads,
# hardlinks, admission, candidate binary hash or process is created before -Run.
$ErrorActionPreference='Stop'
$PackageRoot=[IO.Path]::GetFullPath($PackageRoot);$RunRoot=[IO.Path]::GetFullPath($RunRoot)
$work=Join-Path $RunRoot 'work';$material='mopw/character_park_clown_zombie_shoes'
$native='2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1';$creator='f4e5e45df043f65811098063307d8065b3a33d30'
$toolSHA='e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04'
$ownerSHA='5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8'
function SmallPin([string]$Path,[int]$Limit=1MB){
    $Path=[IO.Path]::GetFullPath($Path);$file=Get-Item -LiteralPath $Path
    if($file.Length -le 0 -or $file.Length -gt $Limit -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Bounded regular source/receipt required.'}
    [pscustomobject]@{Path=$Path;Bytes=$file.Length;SHA256=(Get-FileHash -LiteralPath $Path).Hash.ToLowerInvariant()}
}
$bindingPin=SmallPin $StockBindingPlan
if($bindingPin.SHA256 -ine $StockBindingPlanSHA256){throw 'Exact retained 72-input binding plan required.'}
$stock=Get-Content -LiteralPath $StockBindingPlan -Raw|ConvertFrom-Json
$inputs=@($stock.stock_binding.inputs)
if($inputs.Count -ne 72 -or @($inputs|Where-Object {$_.Relative -eq 'main/fileSysCheck.cfg' -and $_.Mode -ceq 'Copy'}).Count -ne 1){throw 'Existing 72-input profile with independent copied sentinel required.'}
$package=Get-Content -LiteralPath "$PackageRoot/source-workspace.json" -Raw|ConvertFrom-Json
if($package.revisions.'iw7-mod-components' -cne $native){throw 'Current TelemetryOnly native provider required.'}
$pins=@($bindingPin,(SmallPin $PSCommandPath),(SmallPin "$PackageRoot/source-workspace.json"))
foreach($name in 'ops/Base-Client.Core.ps1','ops/Lab-Paths.ps1','ops/Resource-Scheduler.Core.ps1',
    'ops/Resource-Memory.ps1','ops/Resource-RecorderOwnedProcess.Core.ps1','ops/native/ResourceMemory.cs',
    'ops/hud-lab/HudFileIdentity.cs','ops/model-lab/ModelFF.Core.ps1','ops/model-lab/prepare_writer.py','ops/model-lab/geometry.py',
    'sdk/modding/BeaconFF.Core.ps1','tools-source/asset-bridge/common/StockBinding.Core.ps1',
    'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1','tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1',
    'tools-source/asset-bridge/world/original-arena/model_lab.py','tools-source/asset-bridge/world/original-arena/readback.py',
    'tools-source/asset-bridge/h1-fixture/inspect_fixture.py','ops/model-lab/rigid_export.py',
    'tools-source/asset-bridge/t7-iw7/readback.py','tools-source/asset-bridge/t7-iw7/boot_contract.py',
    'tools-source/asset-bridge/t7-iw7/export_contract.py','tools-source/asset-bridge/t7-iw7/streamed_contract.py',
    'tools-source/asset-bridge/world/original-arena/OriginalArena.Process.ps1'){$pins+=SmallPin "$PackageRoot/$name"}
$diagnostic=$null
if($LoadDiagnostic){
    foreach($name in 'tools-source/asset-bridge/world/original-arena/LoadDiagnostic.Core.ps1','ops/iw7_capture.py','ops/iw7_debugger.py'){$pins+=SmallPin "$PackageRoot/$name"}
    $debugger=Get-AppxPackage Microsoft.WinDbg
    if($debugger.Version -ne '1.2606.22001.0'){throw 'Existing reviewed offline debugger metadata required.'}
    $diagnostic=[ordered]@{Mode='global-mp-load-witness';TriggerMs=45000;LatestTriggerMs=60000;NoProgressMs=15000;PhaseSeconds=120;
        GlobalClosureReserveMs=10000;RequiredDiagnosticAndClosureBudgetMs=60000;
        CaptureSource="$PackageRoot/ops/iw7_capture.py";Cdb=(Join-Path $debugger.InstallLocation 'amd64/cdb.exe');
        CdbSHA256='5f54abafca3ae5638bbf807d402fabb350a64575c1dfa9fbfc7f5732df5bee67';
        CPUSeconds=5;SnapshotSeconds=15;OfflineStackSeconds=20;DumpAcceptanceBytes=32MB;
        OutputThresholdBytes=256MB;OutputEnforcement='Sampled';DumpFlags='0x1820';FullMemory=$false;
        MaterialProof=$false;NoCPOrMPSkip=$true}
}
# Keep the exact shared writer normal-encoding proof set, rather than a new list.
# Actual names are supplied by the reviewed shared writer via its small source CLI.
$python=(Get-Command python -CommandType Application|Select-Object -First 1).Source
$normalJson=& $python -I -B -c 'import importlib.util,json,sys; s=importlib.util.spec_from_file_location("w",sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print(json.dumps(m.INTERFACES[-3:]))' "$PackageRoot/ops/model-lab/prepare_writer.py"
if($LASTEXITCODE){throw 'Shared normal source contract could not be read.'}
$normal=@($normalJson|ConvertFrom-Json)
foreach($name in $normal){$pins+=SmallPin (Join-Path $ToolSource $name)}
$request=[ordered]@{schema='iw7.original-arena-reference-request/1';recipient='cp_zmb';material=$material;input_csv='requested.csv';output_csv='original_arena_material'}
$requestRaw=[Text.UTF8Encoding]::new($false).GetBytes(($request|ConvertTo-Json)+"`n")
$requestSHA=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($requestRaw)).ToLowerInvariant()
$arguments=@('-headless','-unbuffered-io','-strict-content-sources','-enemy-reference-check','cp_zmb','requested.csv','original_arena_material')
$plan=[ordered]@{Schema='iw7.original-arena-reference-plan/1';Image=(Join-Path $work 'zonetool.exe');ImageSHA256=$toolSHA;
    Arguments=$arguments;RequestSHA256=$requestSHA;OriginalOwnerAssemblySHA256=$ownerSHA;
    NativePolicyRevision=$native;CreatorSourceRevision=$creator;RunRoot=$RunRoot;SourcePackageRevisions=$package.revisions;
    CandidateRoot=[IO.Path]::GetFullPath($CandidateRoot);CandidateArtifactSHA256=$CandidateArtifactSHA256;
    NativeJobAssembly=[IO.Path]::GetFullPath($NativeJobAssembly);SourcePins=$pins;StockInputs=$inputs;
    PhysicalEstimate=8GB;CommitEstimate=11GB;DeadlineSeconds=$(if($LoadDiagnostic){120}else{240});
    Diagnostic=$diagnostic;RuntimeVerified=$false;MaterialPayloadVerified=$false}
$planRaw=[Text.UTF8Encoding]::new($false).GetBytes(($plan|ConvertTo-Json -Depth 25)+"`n")
$actualPlanSHA=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($planRaw)).ToLowerInvariant()
if(!$Run){[ordered]@{PlanSHA256=$actualPlanSHA;Plan=$plan;StockBytesRead=$false;NativeTypesLoaded=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json -Depth 28;return}
if($PlanSHA256 -cne $actualPlanSHA){throw 'Exact reviewed measurement plan digest required.'}
if(Test-Path -LiteralPath $RunRoot){throw 'Fresh reference output required.'}
if((git -C $ToolSource rev-parse HEAD) -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or (git -C $ToolSource status --porcelain --untracked-files=all)){throw 'Pinned clean retained tool source required.'}
foreach($name in 'ops/Base-Client.Core.ps1','ops/Lab-Paths.ps1','ops/Resource-Scheduler.Core.ps1','ops/model-lab/ModelFF.Core.ps1',
    'sdk/modding/BeaconFF.Core.ps1','tools-source/asset-bridge/common/StockBinding.Core.ps1',
    'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1','tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1',
    'tools-source/asset-bridge/world/original-arena/OriginalArena.Process.ps1'){. "$PackageRoot/$name"}
$null=Assert-IW7LabPath $RunRoot (Join-Path $PackageRoot 'runtime')
$lease=Enter-IW7ResourceLease -Scope $RunRoot -Kind Extract -PhysicalBytes 8GB -CommitBytes 11GB -Owner 'One original-arena nondefault stock material reference'
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$lease;Work=$work}
$guards=[Collections.Generic.List[IDisposable]]::new();$stockGuards=[Collections.Generic.List[IDisposable]]::new()
$saved=$false;$created=$false;$failure=$null
$state=[ordered]@{Schema='iw7.original-arena-reference-run/1';PlanSHA256=$actualPlanSHA;Status='Preparing';Restored=$false;
    StockPreserved=$false;SourceHashesUnchanged=$false;RetainedLeaseToken=$lease.Token;LeaseReleased=$false;RuntimeVerified=$false;MaterialPayloadVerified=$false}
$loadEvidence=[ordered]@{Attempted=$false;LastBytes=-1L;LastProgressMs=0L;Outcome='NotTriggered';SymbolsVerified=$false}
try{
    foreach($pin in $pins){$guards.Add([IO.File]::Open($pin.Path,'Open','Read','Read'));Assert-BeaconHash $pin.Path $pin.SHA256}
    $candidate=Assert-BeaconCandidate $CandidateRoot $CandidateArtifactSHA256
    if($candidate.SHA256 -ine $toolSHA){throw 'Retained e7 candidate required.'}
    $guards.Add([IO.File]::Open($candidate.Path,'Open','Read','Read'))
    $guards.Add([IO.File]::Open($NativeJobAssembly,'Open','Read','Read'))
    Assert-BeaconHash $NativeJobAssembly $ownerSHA
    if('IW7.AnimationProbe.NativeJob' -as [type]){throw 'Fresh PowerShell host required.'}
    [Reflection.Assembly]::LoadFrom($NativeJobAssembly)|Out-Null
    if(!('IW7HudFileIdentity' -as [type])){Add-Type -LiteralPath "$PackageRoot/ops/hud-lab/HudFileIdentity.cs"}
    foreach($entry in $inputs){
        $null=Resolve-IW7BasePath (Split-Path $entry.Source) (Split-Path $entry.Source -Leaf)
        $stockGuards.Add([IO.File]::Open($entry.Source,'Open','Read','Read'))
        $file=Get-Item -LiteralPath $entry.Source
        if($file.Length -ne $entry.Bytes -or $file.LastWriteTimeUtc.Ticks -ne ([datetimeoffset]$entry.ModifiedUtc).UtcDateTime.Ticks -or [int]$file.Attributes -ne $entry.Attributes){throw 'Retained stock metadata changed.'}
        $id=[IW7HudFileIdentity]::Read($entry.Source);Assert-FFStockIdentity $entry $id
        $entry|Add-Member NoteProperty SourceId $id -Force
    }
    Assert-FFStockContent $inputs
    [IO.Directory]::CreateDirectory($work)|Out-Null;$created=$true
    $state.Transaction=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$work;MutableFiles=@($inputs.Relative)+@('zonetool.exe','requested.csv');ProfileDirectory='arena-unused';ProfileDirectories=@()}) (Join-Path $RunRoot 'backup');$saved=$true
    foreach($entry in $inputs){
        $target=Resolve-IW7BasePath $work $entry.Relative;[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
        if($entry.Mode -ceq 'Copy'){Copy-Item -LiteralPath $entry.Source -Destination $target}
        elseif($entry.Mode -ceq 'HardLink'){New-Item -ItemType HardLink -Path $target -Target $entry.Source|Out-Null}
        else{throw 'Retained stock mode differs.'}
        $entry|Add-Member NoteProperty TargetId ([IW7HudFileIdentity]::Read($target)) -Force
    }
    Assert-ModelFFInputs $inputs $work
    Copy-Item -LiteralPath $candidate.Path -Destination $plan.Image;Assert-BeaconHash $plan.Image $toolSHA
    [IO.File]::WriteAllBytes((Join-Path $work 'requested.csv'),[Text.UTF8Encoding]::new($false).GetBytes("material,$material`n"))
    [IO.File]::WriteAllBytes((Join-Path $RunRoot 'requested.csv'),[Text.UTF8Encoding]::new($false).GetBytes("material,$material`n"))
    [IO.File]::WriteAllBytes((Join-Path $RunRoot 'reference-request.json'),$requestRaw)
    [IO.File]::WriteAllBytes((Join-Path $RunRoot 'reference-plan.json'),$planRaw)
    $poll=$null
    if($LoadDiagnostic){
        . "$PackageRoot/tools-source/asset-bridge/world/original-arena/LoadDiagnostic.Core.ps1"
        $options=[pscustomobject]@{StartedMs=(Get-H1Clock);RunRoot=$RunRoot;CaptureSource=$diagnostic.CaptureSource;
            Python=$python;PythonSHA256=(Get-FileHash -LiteralPath $python).Hash;Cdb=$diagnostic.Cdb;CdbSHA256=$diagnostic.CdbSHA256;
            Symbols=(Join-Path $CandidateRoot 'bin');ToolSHA256=$toolSHA;Inputs=$inputs}
        $poll={param($target,$current,$logs);Invoke-ArenaLoadDiagnostic $target $current $logs $options $loadEvidence}
    }
    $state.Process=Invoke-OriginalArenaTool $context $plan.Image $toolSHA $arguments $work $RunRoot reference $inputs $plan.DeadlineSeconds $poll
    if($LoadDiagnostic){$state.Status='DiagnosticNotTriggered';$state.MaterialReferenceMeasured=$false}
    $output=Resolve-IW7BasePath $work 'enemy-catalog/original_arena_material.csv'
    if((Get-Item -LiteralPath $output).Length -gt 4096){throw 'One-row CSV bound exceeded.'}
    [IO.Directory]::CreateDirectory((Join-Path $RunRoot 'enemy-catalog'))|Out-Null
    Copy-Item -LiteralPath $output -Destination (Join-Path $RunRoot 'enemy-catalog/original_arena_material.csv')
    Copy-Item -LiteralPath $state.Process.Stdout -Destination (Join-Path $RunRoot 'stdout.log')
    Assert-ModelFFInputs $inputs $work
    foreach($pin in $pins){Assert-BeaconHash $pin.Path $pin.SHA256};$state.SourceHashesUnchanged=$true
}catch{
    $failure=$_;$state.Status='Failed';$state.Failure=$_.Exception.Message
    if($LoadDiagnostic -and $loadEvidence.Outcome -ceq 'Captured' -and $context.Closed){
        $failure=$null;$state.Status='DiagnosticCaptured';$state.MaterialReferenceMeasured=$false
    }
}
finally{
    if($LoadDiagnostic){$state.Diagnostic=$loadEvidence}
    if($context.Closed){
        try{
            foreach($pin in $pins){Assert-BeaconHash $pin.Path $pin.SHA256}
            if($saved){Assert-ModelFFInputs $inputs $work;Assert-FFStockContent $inputs}
            if($candidate){Assert-BeaconHash $candidate.Path $toolSHA}
            $state.SourceHashesUnchanged=$true
        }catch{$state.SourceHashesUnchanged=$false;if(!$failure){$failure=$_}}
    }
    if($context.Closed -and ($state.SourceHashesUnchanged -or !$saved)){
        try{
            # Follow the existing Rig finalization order: source proof while
            # locked, then dispose read guards before removing borrowed links.
            foreach($guard in $stockGuards){$guard.Dispose()}
            if($saved){$null=Restore-IW7BaseTransaction $state.Transaction;$state.Restored=$true;Assert-ModelFFInputs $inputs $work -SourceOnly;Assert-FFStockContent $inputs;$state.StockPreserved=$true}
            if(!$failure -and !$LoadDiagnostic -and $state.Restored -and $state.StockPreserved){
                $closure=[ordered]@{Schema='iw7.original-arena-reference-process/1';PlanSHA256=$actualPlanSHA;RequestSHA256=$requestSHA;
                    ImageSHA256=$toolSHA;Identity=$state.Process.Identity;Arguments=$arguments;ExitCode=$state.Process.ExitCode;
                    RootExited=$state.Process.RootExited;ActiveProcesses=$state.Process.ActiveProcesses;JobClosed=$state.Process.JobClosed;Restored=$true;StockPreserved=$true}
                $closure|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $RunRoot 'reference-closure.json') -Encoding utf8
                $snapshots=[ordered]@{}
                foreach($pair in @(@('csv','enemy-catalog/original_arena_material.csv'),@('stdout','stdout.log'),@('closure','reference-closure.json'))){
                    $file=Get-Item -LiteralPath (Join-Path $RunRoot $pair[1]);$snapshots[$pair[0]]=[ordered]@{path=$pair[1];bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
                }
                $normalProof=@(foreach($name in $normal){$path=[IO.Path]::GetFullPath((Join-Path $ToolSource $name));$pin=@($pins|Where-Object Path -IEQ $path)[0];[ordered]@{path=$name;sha256=$pin.SHA256}})
                $evidence=[ordered]@{schema='iw7.original-arena-recipient-reference/1';source_pin='fab935826c898806855376662a8a03317b3ad8f1';recipient='cp_zmb';material=$material;snapshot_only=$true;runtime_verified=$false;material_payload_verified=$false;reference_snapshot=$snapshots;normal_encoding_source=$normalProof}
                $evidence|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $RunRoot 'reference-evidence.json') -Encoding utf8
                $checkArguments=@('-I','-S','-B',"$PackageRoot/tools-source/asset-bridge/world/original-arena/model_lab.py",'verify-reference',
                    '--source',$ToolSource,'--evidence',(Join-Path $RunRoot 'reference-evidence.json'),'--measurement-root',$RunRoot)
                $state.ReferenceReader=Invoke-OriginalArenaTool $context $python (Get-FileHash -LiteralPath $python).Hash $checkArguments $PackageRoot $RunRoot reference-check @() 30
                $state.Status='ReferenceCaptured'
            }
            if($created){$state|ConvertTo-Json -Depth 20|Set-Content -LiteralPath (Join-Path $RunRoot 'state.local.json') -Encoding utf8}
            Exit-IW7ResourceLease -Token $lease.Token;$state.LeaseReleased=$true;$state.RetainedLeaseToken=$null
        }catch{if(!$failure){$failure=$_}}
    }
    if($state.LeaseReleased){foreach($guard in $guards){$guard.Dispose()};foreach($guard in $stockGuards){$guard.Dispose()}}
    else{[AppDomain]::CurrentDomain.SetData('IW7.OriginalArena.Reference.Quarantine.'+$lease.Token,[pscustomobject]@{Context=$context;Guards=$guards;StockGuards=$stockGuards;State=$state})}
}
if($failure){throw $failure}
$state|ConvertTo-Json -Depth 20
