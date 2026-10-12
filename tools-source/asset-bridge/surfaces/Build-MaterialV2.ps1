param(
    [Parameter(Mandatory)][string]$PreparedRoot,[Parameter(Mandatory)][string]$OriginalWriterRoot,
    [Parameter(Mandatory)][string]$CheckerRoot,[Parameter(Mandatory)][string]$ZTSource,
    [Parameter(Mandatory)][string]$CandidateRoot,[Parameter(Mandatory)][string]$SharedRepo,
    [Parameter(Mandatory)][string]$StockRoot,[Parameter(Mandatory)][string]$StockReceipt,
    [Parameter(Mandatory)][string]$StockReceiptSHA256,
    [Parameter(Mandatory)][string]$StockBindingReceipt,[Parameter(Mandatory)][string]$StockBindingReceiptSHA256,
    [Parameter(Mandatory)][string]$ReviewedStockManifest,[Parameter(Mandatory)][string]$ReviewedStockManifestSHA256,
    [Parameter(Mandatory)][string]$RunRoot,
    [Parameter(Mandatory)][string]$VCToolsRoot,[Parameter(Mandatory)][string]$WindowsSdkRoot,
    [Parameter(Mandatory)][string]$WindowsSdkVersion,[switch]$Run
)
# Read-only plan by default. -Run is an explicit, separately reviewed/admitted job.
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$pins=Get-Content -LiteralPath "$PSScriptRoot/material_v2_helpers.json" -Raw|ConvertFrom-Json
$guards=[Collections.Generic.List[IDisposable]]::new()
$hashInputs=[Collections.Generic.List[object]]::new()
foreach($entry in $pins.PSObject.Properties){
    $path=Join-Path $SharedRepo $entry.Name
    if((Get-FileHash -LiteralPath $path).Hash -ine $entry.Value){throw "Reviewed shared helper changed: $($entry.Name)"}
    $hashInputs.Add([pscustomobject]@{Path=$path;SHA256=$entry.Value})
}
. "$SharedRepo/ops/Base-Client.Core.ps1"
. "$SharedRepo/ops/Resource-Scheduler.Core.ps1"
. "$SharedRepo/ops/model-lab/ModelFF.Core.ps1"
. "$SharedRepo/sdk/modding/BeaconFF.Core.ps1"
. "$SharedRepo/tools-source/asset-bridge/common/StockBinding.Core.ps1"
. "$PSScriptRoot/MaterialV2.Core.ps1"
. "$PSScriptRoot/MaterialV2.Compiler.ps1"
$RunRoot=Resolve-IW7BasePath (Join-Path $repo 'runtime') ([IO.Path]::GetRelativePath((Join-Path $repo 'runtime'),[IO.Path]::GetFullPath($RunRoot)))
if(Test-Path -LiteralPath $RunRoot){throw 'Fresh material-v2 run directory required.'}
foreach($name in @('PreparedRoot','OriginalWriterRoot','CheckerRoot','ZTSource','CandidateRoot','SharedRepo','StockRoot','VCToolsRoot','WindowsSdkRoot')){
    $value=[IO.Path]::GetFullPath((Get-Variable $name -ValueOnly)).TrimEnd('\','/')
    $null=Resolve-IW7BasePath (Split-Path $value) (Split-Path $value -Leaf)
    if(!$value -or !(Test-Path -LiteralPath $value -PathType Container)){throw "Existing unredirected input root required: $name = $value"}
    # A run inside SharedRepo/runtime is normal. Other input trees must be separate.
    if($name -ne 'SharedRepo' -and ($RunRoot.StartsWith($value+'\',[StringComparison]::OrdinalIgnoreCase) -or
        $value.StartsWith($RunRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or $value -ieq $RunRoot)){throw 'Run and input trees overlap.'}
    Set-Variable $name $value
}
$python=(Get-Command python -ErrorAction Stop).Source
$checks=Join-Path $PSScriptRoot 'material_v2_checks.py'
function Invoke-MaterialCheck($Arguments) {
    $result=@(& $python -B $checks @Arguments)
    if($LASTEXITCODE){throw 'Material-v2 bounded check failed.'}
    ($result -join "`n")|ConvertFrom-Json
}
$sourceArgs=@('source','--prepared',$PreparedRoot,'--writer',$OriginalWriterRoot,'--checker',$CheckerRoot,
    '--receipt',(Join-Path $CandidateRoot 'build-artifact.local.json'),'--zt',$ZTSource)
$source=Invoke-MaterialCheck $sourceArgs
$compiler=Resolve-IW7BasePath $VCToolsRoot 'bin/Hostx64/x64/cl.exe'
if(!(Test-Path -LiteralPath $compiler -PathType Leaf)){throw 'Installed MSVC x64 compiler required.'}
$compilerPolicy=Get-MaterialV2CompilerPolicy $compiler
Assert-BeaconHash $compiler $compilerPolicy.CompilerSHA256
$null=Resolve-IW7BasePath (Split-Path $compilerPolicy.Telemetry) (Split-Path $compilerPolicy.Telemetry -Leaf)
Assert-BeaconHash $compilerPolicy.Telemetry $compilerPolicy.TelemetrySHA256
$hashInputs.Add([pscustomobject]@{Path=$compilerPolicy.Telemetry;SHA256=$compilerPolicy.TelemetrySHA256})
$writerRoot=Join-Path $RunRoot 'writer';$writer=Join-Path $writerRoot 'material-v2-writer.exe'
$work=Join-Path $RunRoot 'work';$dump=Join-Path $work ('dump/'+$source.zone)
$compileArgs=@(Get-MaterialV2CompilerArguments $VCToolsRoot $WindowsSdkRoot $WindowsSdkVersion $ZTSource $PreparedRoot $writerRoot)
Assert-BeaconHash $StockReceipt $StockReceiptSHA256
Assert-BeaconHash $StockBindingReceipt $StockBindingReceiptSHA256
Assert-BeaconHash $ReviewedStockManifest $ReviewedStockManifestSHA256
$stock=Read-BeaconJson $StockReceipt
$observation=Read-BeaconJson $StockBindingReceipt
$reviewed=Read-BeaconJson $ReviewedStockManifest
$inputs=@(Get-FFStockBindingInputs $stock $observation $reviewed $StockRoot $StockReceiptSHA256 $ReviewedStockManifestSHA256)
Set-MaterialV2StagingModes $inputs
$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach($entry in $inputs){$null=$seen.Add($entry.Relative)}
foreach($entry in $source.source_files.PSObject.Properties){$hashInputs.Add([pscustomobject]@{Path=(Resolve-IW7BasePath $PreparedRoot $entry.Name);SHA256=$entry.Value.sha256})}
foreach($entry in $source.writer_interface_hashes.PSObject.Properties){$hashInputs.Add([pscustomobject]@{Path=(Resolve-IW7BasePath $ZTSource $entry.Name);SHA256=$entry.Value})}
foreach($path in @($StockReceipt,$StockBindingReceipt,$ReviewedStockManifest,$compiler,$python,(Join-Path $PreparedRoot 'material-v2-plan.json'))+
    @(Get-ChildItem -LiteralPath $PSScriptRoot -File|Where-Object Extension -in '.py','.ps1','.json','.cs'|ForEach-Object FullName)){
    $hashInputs.Add([pscustomobject]@{Path=$path;SHA256=(Get-FileHash -LiteralPath $path).Hash})
}
$budgets=Get-MaterialV2Budgets
$plan=[ordered]@{Schema='iw7.material-v2-execution-plan/1';RunRoot=$RunRoot;Source=$source;StockInputs=$inputs;
    StockRoot=$StockRoot;StockBindingReceipt=$StockBindingReceipt;StockBindingReceiptSHA256=$StockBindingReceiptSHA256;
    StockReceiptSHA256=$StockReceiptSHA256;ReviewedStockManifestSHA256=$ReviewedStockManifestSHA256;
    StockContentAndIdentityRecheckPending=$true;StagingCopyBytes=[long](@($inputs|Where-Object Mode -CEQ Copy)|Measure-Object Bytes -Sum).Sum;
    Compiler=$compiler;CompilerArguments=$compileArgs;CompilerClosure=$compilerPolicy;HashInputs=$hashInputs.ToArray();SharedHelperPins=$pins;
    Phases=@('compile','write','build','verify','dump','read');WriterPhysicalBytes=$budgets.WriterPhysicalBytes;WriterCommitBytes=$budgets.WriterCommitBytes;
    FFPhysicalBytes=$budgets.FFPhysicalBytes;FFCommitBytes=$budgets.FFCommitBytes;LogBytesPerStream=2MB;NewOutputStopBytes=64MB;
    OriginalDiffuse=$source.image;RecipientNormal='park_clown_zombie_shoes_n_3e46d100_packed_nog';CPPreload=$false;
    HeavyExecutionAuthorizedByThisPlan=$false;Ready=$false}
if(!$Run){$plan|ConvertTo-Json -Depth 20;return}
if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7.MaterialDiagnostics.JobMembers' -as [type])){
    throw 'Fresh PowerShell host required for source-bound job and observer.'
}
$candidate=Assert-BeaconCandidate $CandidateRoot $source.builder.receipt_sha256
if($candidate.SHA256 -ine $source.builder.executable_sha256){throw 'Exact final full-tool executable required.'}
$state=[ordered]@{Schema='iw7.material-v2-build/1';Work=$work;Inputs=$inputs;Plan=$plan;Status='Preparing';Phases=@();
    Restored=$false;StockPreserved=$false;StockContentAndIdentityVerified=$false;RestorationStatus='Pending';CleanupError=$null;RetainedLeaseToken=$null;
    WriterLeaseReleased=$false;GeometryRoundtripVerified=$false;InventoryVerified=$false;DiffuseBytesVerified=$false;
    RecipientReferenceResolved=$false;NativeCBTSemanticsVerified=$false;PixelsVerified=$false;Ready=$false;
    MaxObservedBytes=0L;FinalObservedBytes=$null;JobCleanup=$null}
$statePath=Join-Path $RunRoot 'state.local.json'
$lease=$null;$owner=$null;$closed=$true;$saved=$false;$sourceIntact=$true
function Save-MaterialState {if(Test-Path -LiteralPath $RunRoot){$state|ConvertTo-Json -Depth 25|Set-Content -LiteralPath $statePath -Encoding utf8}}
function Measure-MaterialOutput([switch]$Final) {
    $bytes=Measure-MaterialV2OutputFiles @(Get-ChildItem -LiteralPath $RunRoot -File -Recurse -Force) $work $state.Inputs
    $state.MaxObservedBytes=[math]::Max($state.MaxObservedBytes,$bytes)
    if($Final){$state.FinalObservedBytes=$bytes}
    Assert-BeaconOutputBudget $bytes
}
function Invoke-MaterialPhase([string]$Phase,[string]$Exe,[string]$Hash,$Arguments,[string]$Cwd) {
    $logs=Join-Path $RunRoot $Phase;$specPath=Join-Path $RunRoot ($Phase+'-spec.json')
    $spec=[ordered]@{schema='iw7.material-v2-phase/1';phase=$Phase;exe=$Exe;sha256=$Hash;arguments=@($Arguments);
        cwd=$Cwd;logs=$logs;timeout=$(if($Phase -in 'write','read'){30}else{240})}
    $spec|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $specPath -Encoding utf8
    $guards.Add([IO.File]::Open($specPath,'Open','Read','Read'))
    $specHash=(Get-FileHash -LiteralPath $specPath).Hash
    $argsText=ConvertTo-MaterialV2Arguments @('-B',(Join-Path $PSScriptRoot 'material_v2_phase.py'),'--spec',$specPath,
        '--spec-sha256',$specHash,'--sdk-phase',(Join-Path $SharedRepo 'sdk/modding/beacon_tool_phase.py'))
    $script:owner=[IW7.CommunityBuild.BuildJob]::Prepare($python,$argsText,$Cwd);$script:closed=$false
    $identity=Get-BeaconJobIdentity $owner $python $Phase
    $identity.SpecSHA256=$specHash;$identity.NativeExecutableSHA256=$Hash
    if($Phase -ceq 'compile'){$identity.CompilerCompletion=[ordered]@{CompilerIdentity=$null;Completed=$false}}
    $state.Phases+=,$identity;Save-MaterialState
    $resumed=Start-MaterialV2OwnedPhase $owner $lease.Token
    $identity.StartedUtc=$resumed.StartedUtc;$identity.SchedulerAttached=$resumed.SchedulerAttached;Save-MaterialState
    Wait-MaterialV2OwnedPhase $owner $identity $resumed.StartedMonotonicMs $spec.timeout {
        param($snapshot,$changed)
        if($Phase -ceq 'compile'){
            $observation=[IW7.MaterialDiagnostics.JobMembers]::Capture($owner)
            Update-MaterialV2CompilerWitness $identity.CompilerCompletion $observation $identity.PID $compilerPolicy
            if($snapshot.RootExited -and $snapshot.ActiveProcesses -ne 0){
                $receipt=Read-BeaconJson (Join-Path $logs 'phase.json')
                $null=Complete-MaterialV2CompilerTelemetry $owner $snapshot $observation $receipt $identity.CompilerCompletion $compilerPolicy
            }
        }
        if($changed){Save-MaterialState}
        if(Test-Path -LiteralPath (Join-Path $RunRoot 'stop.request')){throw 'Coordinator requested owned stop.'}
        Measure-MaterialOutput
        $memory=Get-IW7ResourceSnapshot;if($memory.Committed -gt $memory.CommitLimit*0.85){throw 'Commit pressure exceeded85 percent.'}
    }
    $script:closed=$true;$owner.Dispose();$script:owner=$null
    Save-MaterialState;Measure-MaterialOutput
    Assert-MaterialV2PhaseResult (Read-BeaconJson (Join-Path $logs 'phase.json')) $Phase $Hash $identity
    Join-Path $logs 'stdout.log'
}
try {
    $lease=Enter-IW7ResourceLease -Scope $writerRoot -Kind Build -PhysicalBytes $plan.WriterPhysicalBytes -CommitBytes $plan.WriterCommitBytes -Owner 'Material v2 exact standalone writer'
    $state.RetainedLeaseToken=$lease.Token
    [IO.Directory]::CreateDirectory($writerRoot)|Out-Null
    foreach($entry in $hashInputs){$guards.Add([IO.File]::Open($entry.Path,'Open','Read','Read'));Assert-BeaconHash $entry.Path $entry.SHA256}
    $null=Invoke-MaterialCheck $sourceArgs
    Add-Type -LiteralPath "$SharedRepo/tools-source/asset-bridge/model/BuildJob.cs"
    Add-Type -LiteralPath "$PSScriptRoot/MaterialV2.JobMembers.cs"
    Add-Type -LiteralPath "$SharedRepo/ops/hud-lab/HudFileIdentity.cs"
    Save-MaterialState
    $null=Invoke-MaterialPhase compile $compiler (Get-FileHash -LiteralPath $compiler).Hash $compileArgs $writerRoot
    $writerHash=(Get-FileHash -LiteralPath $writer).Hash
    $guards.Add([IO.File]::Open($writer,'Open','Read','Read'))
    $writeLog=Invoke-MaterialPhase write $writer $writerHash @((Join-Path $writerRoot 'artifacts')) $writerRoot
    $state.WriterRoundtrip=Invoke-MaterialCheck @('roundtrip','--path',$writeLog)
    $state.WriterSHA256=$writerHash;$state.WriterArtifacts=@()
    foreach($name in $source.required_artifacts){
        $path=Resolve-IW7BasePath (Join-Path $writerRoot 'artifacts') $name;$file=Get-Item -LiteralPath $path
        if($file.Length -lt 1 -or $file.Length -gt 8192){throw 'Native v2 artifact outside bound.'}
        $state.WriterArtifacts+=,[pscustomobject]@{Path=$name;Bytes=$file.Length;SHA256=(Get-FileHash -LiteralPath $path).Hash}
    }
    if(@(Get-ChildItem -LiteralPath (Join-Path $writerRoot 'artifacts') -File -Recurse).Count -ne 2){throw 'Native writer emitted extra assets.'}
    Measure-MaterialOutput -Final;Save-MaterialState;Measure-MaterialOutput -Final
    Exit-IW7ResourceLease -Token $lease.Token;$lease=$null;$state.RetainedLeaseToken=$null;$state.WriterLeaseReleased=$true;Save-MaterialState
    $lease=Enter-IW7ResourceLease -Scope $work -Kind Extract -PhysicalBytes $plan.FFPhysicalBytes -CommitBytes $plan.FFCommitBytes -Owner 'Material v2 FF verify dump independent reader'
    $state.RetainedLeaseToken=$lease.Token
    $stage=@(foreach($entry in $source.source_files.PSObject.Properties|Where-Object Name -CLike 'ff-inputs/*'){
        [pscustomobject]@{Relative=$entry.Name.Substring(10);Source=(Join-Path $PreparedRoot $entry.Name);SHA256=$entry.Value.sha256}
    })+@(foreach($entry in $state.WriterArtifacts){[pscustomobject]@{Relative=$entry.Path;Source=(Join-Path $writerRoot ('artifacts/'+$entry.Path));SHA256=$entry.SHA256}})+
        @([pscustomobject]@{Relative='zonetool.exe';Source=$candidate.Path;SHA256=$candidate.SHA256})
    foreach($entry in $stage){
        if(!$seen.Add($entry.Relative)){throw 'Source/stock staging collision.'}
        $file=Get-Item -LiteralPath $entry.Source
        $state.Inputs+=,[pscustomobject]@{Relative=$entry.Relative;Source=$entry.Source;Mode='HardLink';Bytes=$file.Length;ModifiedUtc=$file.LastWriteTimeUtc.ToString('o');Attributes=[int]$file.Attributes}
    }
    foreach($entry in $state.Inputs){
        $null=Resolve-IW7BasePath (Split-Path $entry.Source -Parent) (Split-Path $entry.Source -Leaf)
        $guards.Add([IO.File]::Open($entry.Source,'Open','Read','Read'))
        $actualId=[IW7HudFileIdentity]::Read($entry.Source)
        Assert-FFStockIdentity $entry $actualId
        Set-MaterialV2SourceIdentity $entry $actualId
    }
    Assert-ModelFFInputs $state.Inputs $work -SourceOnly
    Assert-FFStockContent $inputs
    $state.StockContentAndIdentityVerified=$true;Save-MaterialState
    foreach($entry in $stage){Assert-BeaconHash $entry.Source $entry.SHA256}
    [IO.Directory]::CreateDirectory($work)|Out-Null
    $state.Transaction=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$work;MutableFiles=@($state.Inputs.Relative)+@('zone/'+$source.zone+'.ff');ProfileDirectory='unused';ProfileDirectories=@()}) (Join-Path $RunRoot 'backup')
    $saved=$true;Save-MaterialState
    foreach($entry in $state.Inputs){
        $target=Resolve-IW7BasePath $work $entry.Relative;[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
        if($entry.Mode -ceq 'Copy'){Copy-Item -LiteralPath $entry.Source -Destination $target}else{New-Item -ItemType HardLink -Path $target -Target $entry.Source|Out-Null}
        $entry|Add-Member NoteProperty TargetId ([IW7HudFileIdentity]::Read($target))
        if($entry.Mode -ceq 'HardLink' -and $entry.TargetId -cne $entry.SourceId){throw 'Staged NTFS identity differs.'}
        if($entry.Mode -ceq 'Copy'){
            Assert-MaterialV2CopyIdentity $entry $entry.TargetId
            (Get-Item -LiteralPath $target).IsReadOnly=$false
        }
    }
    Assert-ModelFFInputs $state.Inputs $work
    $tool=Join-Path $work 'zonetool.exe';$common=@('-headless','-unbuffered-io','-strict-content-sources')
    $null=Invoke-MaterialPhase build $tool $candidate.SHA256 ($common+@('-buildzone',$source.zone)) $work
    $ff=Resolve-IW7BasePath $work ('zone/'+$source.zone+'.ff');$size=(Get-Item -LiteralPath $ff).Length
    if($size -lt 1 -or $size -gt 1MB){throw 'Nonempty v2 FF at most1MiB required.'}
    Copy-Item -LiteralPath $ff -Destination (Join-Path $RunRoot 'mod.ff')
    $state.FF=[ordered]@{Bytes=$size;SHA256=(Get-FileHash -LiteralPath $ff).Hash;Path='mod.ff'}
    $verifyLog=Invoke-MaterialPhase verify $tool $candidate.SHA256 ($common+@('-verifyzone',$source.zone)) $work
    $state.Inventory=Invoke-MaterialCheck @('inventory','--path',$verifyLog);$state.InventoryVerified=$true
    $null=Invoke-MaterialPhase dump $tool $candidate.SHA256 ($common+@('-dumpzone',$source.zone)) $work
    $state.Surface=Invoke-MaterialCheck @('surface','--root',$dump,'--prepared',$PreparedRoot);$state.DiffuseBytesVerified=$true
    foreach($name in $source.required_artifacts){
        $path=Resolve-IW7BasePath $dump $name;$size=(Get-Item -LiteralPath $path).Length
        if($size -lt 1 -or $size -gt 8192){throw 'Dumped model artifact outside bound.'}
        $target=Join-Path $RunRoot ('roundtrip/'+$name);[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
        Copy-Item -LiteralPath $path -Destination $target
    }
    $readLog=Invoke-MaterialPhase read $writer $writerHash @('--verify-existing',(Join-Path $RunRoot 'roundtrip')) $writerRoot
    $state.Geometry=Invoke-MaterialCheck @('roundtrip','--path',$readLog);$state.GeometryRoundtripVerified=$true
    $state.Status='FFGeometryAndDiffuseBytesVerified';Save-MaterialState;Measure-MaterialOutput -Final
} catch {$state.Failure=$_.Exception.Message;$state.Status='Failed';throw}
finally {
    if($owner){
        $state.JobCleanup=[ordered]@{}
        $closed=Stop-MaterialV2OwnedPhase $owner $state.JobCleanup
        $owner.Dispose()
    }
    foreach($entry in $hashInputs){try{Assert-BeaconHash $entry.Path $entry.SHA256}catch{$sourceIntact=$false;$state.CleanupError=$_.Exception.Message}}
    $state.SourceHashesUnchanged=$sourceIntact;$state.JobClosureVerified=$closed
    if($closed){foreach($guard in $guards){$guard.Dispose()}}
    Save-MaterialState
    if($lease -and $closed -and $sourceIntact){
        if($saved){Complete-ModelFFRestore $state $statePath $lease.Token}
        else{Exit-IW7ResourceLease -Token $lease.Token;$state.RetainedLeaseToken=$null}
    }elseif($lease){$state.CleanupError='Closure/source proof incomplete; retain reservation and owned inputs.'}
    if(Test-Path -LiteralPath $RunRoot){
        try{Measure-MaterialOutput -Final;Save-MaterialState;Measure-MaterialOutput -Final}
        catch{$state.Status='Failed';$state.Failure=$_.Exception.Message;Save-MaterialState;throw}
    }
}
if(!$state.JobClosureVerified -or !$state.SourceHashesUnchanged -or !$state.Restored -or $state.RetainedLeaseToken){throw 'V2 cleanup incomplete; evidence and reservation retained.'}
$state|ConvertTo-Json -Depth 25
