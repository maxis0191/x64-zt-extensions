[CmdletBinding(DefaultParameterSetName='Build')]
param(
    [Parameter(Mandatory,ParameterSetName='Build')][string]$ReviewPlanPath,
    [Parameter(Mandatory,ParameterSetName='Build')][string]$ReviewPlanSHA256,
    [Parameter(Mandatory,ParameterSetName='Build')][string]$StockParametersPath,
    [Parameter(Mandatory,ParameterSetName='Build')][string]$StockParametersSHA256,
    [Parameter(Mandatory)][string]$OutputPath,
    [Parameter(Mandatory,ParameterSetName='DumpOnly')][switch]$DumpOnly,
    [Parameter(Mandatory,ParameterSetName='DumpOnly')][string]$ImmutablePlanPath,
    [Parameter(Mandatory,ParameterSetName='DumpOnly')][string]$ImmutableStatePath,
    [Parameter(Mandatory,ParameterSetName='DumpOnly')][string]$CandidateRoot,
    [Parameter(Mandatory,ParameterSetName='DumpOnly')][string]$RunRoot
)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/SoundFF.Core.ps1"
if($DumpOnly){
    # Qualification is checked before other input reads or any output creation.
    $receiptSHA='dfe3d7d1ed0d9b3c4ad334fc64d1f3f277508c468df034f05cffd2505f3944f4'
    $stateSHA='99c5c35fe43ad90bb192db8902dc718402fb901dd2cc6f6689d790e82a5ba149'
    $candidate=Assert-SoundFFFlacCandidate $CandidateRoot $receiptSHA $stateSHA
    $evidence=[pscustomobject]@{PlanPath=$ImmutablePlanPath;PlanSHA256='3d90a5746a8ee698fb08715e270f2855f261b318393257f91a9e7f59e3ad39d5';
        StatePath=$ImmutableStatePath;StateSHA256='d0a57123f7940eee29ef42da7440dd353e63eeffbfc025d37b162f4feda9e1a9'}
    $f=Read-SoundFFImmutableF $evidence
    Assert-SoundFFPath $OutputPath;Assert-SoundFFPath $RunRoot
    if(Test-Path -LiteralPath $OutputPath){throw 'Fresh dump Plan required.'}
    $payload=@($f.Plan.HashInputs|Where-Object {[IO.Path]::GetExtension($_.Path) -iin @('.exe','.wav','.flac')})
    $pins=[Collections.Generic.List[object]]::new()
    foreach($old in $f.Plan.HashInputs){
        if($old.Path -iin $payload.Path -or $old.Path.StartsWith($f.Plan.CandidateRoot+'\',[StringComparison]::OrdinalIgnoreCase)){continue}
        if(!$old.Path.StartsWith($PSScriptRoot+'\',[StringComparison]::OrdinalIgnoreCase)){Assert-SoundFFPin $old}
        $pins.Add((Get-SoundFFPin $old.Path))
    }
    $inventory=Join-Path $f.Plan.RunRoot 'logs/verify/stdout.log'
    if((Get-Item -LiteralPath $inventory).Length -gt 256KB){throw 'Bounded preserved inventory required.'}
    foreach($path in @($ImmutablePlanPath,$ImmutableStatePath,$inventory,(Join-Path $CandidateRoot 'build-receipt.json'),(Join-Path $CandidateRoot 'supervisor-state.json'))){
        $pins.Add((Get-SoundFFPin $path))
    }
    $evidence|Add-Member NoteProperty InventoryPath $inventory
    $evidence|Add-Member NoteProperty InventorySHA256 ((Get-FileHash -LiteralPath $inventory).Hash)
    $evidence|Add-Member NoteProperty Artifacts @($f.State.Artifacts)
    $work=Join-Path $RunRoot 'work';$zone='sdk_original_sound_v1';$pythonPin=@($payload|Where-Object Path -IEQ $f.Plan.Python)[0]
    $phases=@(
        [pscustomobject]@{schema='iw7.material-v2-phase/1';phase='dump';exe=(Join-Path $work 'zonetool.exe');sha256=$candidate.SHA256;
            arguments=@('-headless','-unbuffered-io','-strict-content-sources','-dumpzone',$zone);cwd=$work;logs=(Join-Path $RunRoot 'logs/dump');timeout=240},
        [pscustomobject]@{schema='iw7.material-v2-phase/1';phase='read';exe=$f.Plan.Python;sha256=$pythonPin.SHA256.ToLowerInvariant();
            arguments=@('-B',(Join-Path $PSScriptRoot 'read_sab.py'),'--source',$f.Plan.Review.source,'--banks',(Join-Path $work 'zone'),
                '--contract',(Join-Path $PSScriptRoot 'sab_contract.json'),'--dump',(Join-Path $work ('dump/'+$zone)),
                '--inventory',$inventory,'--dump-profile','DumpOnlyC');cwd=$work;logs=(Join-Path $RunRoot 'logs/read');timeout=30})
    $review=[pscustomobject]@{source=$f.Plan.Review.source;stock_root=$f.Plan.Review.stock_root;candidate_root=$CandidateRoot;
        existing_candidate=[pscustomobject]@{path=$candidate.Path;bytes=$candidate.Bytes;sha256=$candidate.SHA256};
        phase_adapter=(Join-Path $PSScriptRoot 'sound_ff_phase.py');source_stage_relatives=@();phase_specs=$phases}
    $plan=[pscustomobject][ordered]@{Schema='iw7.original-sound-ff-execution/1';Profile='DumpOnly';Review=$review;RunRoot=$RunRoot;Work=$work;
        SharedRepo=$f.Plan.SharedRepo;Python=$f.Plan.Python;CandidateRoot=$CandidateRoot;CandidateReceiptSHA256=$receiptSHA;CandidateStateSHA256=$stateSHA;
        ImmutableFF=$evidence;StockInputs=$f.Plan.StockInputs;HashInputs=@($pins|Sort-Object Path);PayloadInputs=$payload;
        PhysicalBytes=8GB;CommitBytes=11GB;OutputStopBytes=64MB;LogBytesPerStream=2MB;CleanupMs=15000;MutableOutputs=@();
        HeavyExecutionAuthorizedByPlan=$false;Ready=$false}
    Assert-SoundFFExecutionPlan $plan $PSScriptRoot
    $json=$plan|ConvertTo-Json -Depth 25
    if([Text.Encoding]::UTF8.GetByteCount($json) -gt 256KB){throw 'Dump Plan exceeds 256 KiB.'}
    $stream=[IO.File]::Open($OutputPath,'CreateNew','Write','None')
    try{$raw=[Text.UTF8Encoding]::new($false).GetBytes($json+[Environment]::NewLine);$stream.Write($raw,0,$raw.Length)}finally{$stream.Dispose()}
    [pscustomobject]@{Path=$OutputPath;SHA256=(Get-FileHash -LiteralPath $OutputPath).Hash;Profile='DumpOnly';NativeExecuted=$false;PayloadRead=$false;Ready=$false}|ConvertTo-Json
    return
}
Assert-SoundFFPath $ReviewPlanPath;Assert-SoundFFPath $StockParametersPath;Assert-SoundFFPath $OutputPath
if(Test-Path -LiteralPath $OutputPath){throw 'Fresh execution plan output required.'}
Assert-SoundFFPin ([pscustomobject]@{Path=$ReviewPlanPath;SHA256=$ReviewPlanSHA256})
Assert-SoundFFPin ([pscustomobject]@{Path=$StockParametersPath;SHA256=$StockParametersSHA256})
$review=Get-Content -LiteralPath $ReviewPlanPath -Raw|ConvertFrom-Json
$parameters=Get-Content -LiteralPath $StockParametersPath -Raw|ConvertFrom-Json
if($review.schema -cne 'iw7.original-sound-ff-review-plan/1' -or $review.physical_bytes -ne 8GB -or $review.commit_bytes -ne 11GB -or
    $review.native_authorized -isnot [bool] -or $review.native_authorized){throw 'Source-reviewed 8/11 sound plan required.'}
$repo=$review.shared_repo
$pins=[Collections.Generic.List[object]]::new()
foreach($entry in $review.input_pins){Assert-SoundFFPin $entry;$pins.Add($entry)}
foreach($path in @($ReviewPlanPath,$StockParametersPath)+@('Prepare-SoundFF.ps1','Build-SoundFF.ps1','SoundFF.Core.ps1'|ForEach-Object {Join-Path $PSScriptRoot $_})){
    $pins.Add((Get-SoundFFPin $path))
}
Assert-SoundFFHelperSources $PSScriptRoot $repo $pins
foreach($relative in 'ops/Base-Client.Core.ps1','sdk/modding/BeaconFF.Core.ps1','tools-source/asset-bridge/common/StockBinding.Core.ps1','tools-source/asset-bridge/surfaces/MaterialV2.Core.ps1'){
    . (Join-Path $repo $relative)
}
foreach($name in 'StockReceipt','StockBindingReceipt','ReviewedStockManifest'){
    $path=$parameters.$name;$hash=$parameters.($name+'SHA256')
    Assert-SoundFFPin ([pscustomobject]@{Path=$path;SHA256=$hash});$pins.Add((Get-SoundFFPin $path))
}
if($parameters.StockRoot -ine $review.stock_root){throw 'Historical stock root differs.'}
$baseline=Read-BeaconJson $parameters.StockReceipt;$observation=Read-BeaconJson $parameters.StockBindingReceipt;$reviewed=Read-BeaconJson $parameters.ReviewedStockManifest
$stock=@(Get-FFStockBindingInputs $baseline $observation $reviewed $parameters.StockRoot $parameters.StockReceiptSHA256 $parameters.ReviewedStockManifestSHA256)
Set-MaterialV2StagingModes $stock
$candidateRoot=[IO.Path]::GetFullPath($review.candidate_root)
$candidateReceipt=Join-Path $candidateRoot 'build-receipt.json'
$candidate=Assert-SoundFFChecksumCandidate $candidateRoot $review.candidate_receipt_sha256 $review.candidate_state_sha256
if($candidate.Path -ine $review.existing_candidate.path -or $candidate.SHA256 -cne $review.existing_candidate.sha256){throw 'Reviewed candidate differs.'}
foreach($entry in @([pscustomobject]@{Path=$candidateReceipt;SHA256=$review.candidate_receipt_sha256},
    [pscustomobject]@{Path=(Join-Path $candidateRoot 'supervisor-state.json');SHA256=$review.candidate_state_sha256})){
    Assert-SoundFFPin $entry;$pins.Add((Get-SoundFFPin $entry.Path))
}
$unique=@{};foreach($pin in $pins){$key=[IO.Path]::GetFullPath($pin.Path);if($unique.ContainsKey($key) -and $unique[$key].SHA256 -ine $pin.SHA256){throw 'Conflicting source pin.'};$unique[$key]=Get-SoundFFPin $key}
$plan=[ordered]@{Schema='iw7.original-sound-ff-execution/1';Review=$review;RunRoot=$review.run_root;Work=(Join-Path $review.run_root 'work');
    SharedRepo=$repo;Python=$review.phase_specs[-1].exe;CandidateRoot=$candidateRoot;CandidateReceiptSHA256=(Get-FileHash -LiteralPath $candidateReceipt).Hash;
    CandidateStateSHA256=$review.candidate_state_sha256;
    StockInputs=$stock;HashInputs=@($unique.Values|Sort-Object Path);PhysicalBytes=8GB;CommitBytes=11GB;OutputStopBytes=64MB;
    LogBytesPerStream=2MB;CleanupMs=15000;MutableOutputs=@($review.owned_future_outputs);HeavyExecutionAuthorizedByPlan=$false;Ready=$false}
Assert-SoundFFExecutionPlan $plan $PSScriptRoot
$json=$plan|ConvertTo-Json -Depth 25
if([Text.Encoding]::UTF8.GetByteCount($json) -gt 256KB){throw 'Execution plan exceeds 256 KiB.'}
$stream=[IO.File]::Open($OutputPath,'CreateNew','Write','None')
try{$raw=[Text.UTF8Encoding]::new($false).GetBytes($json+[Environment]::NewLine);$stream.Write($raw,0,$raw.Length)}finally{$stream.Dispose()}
[pscustomobject]@{Path=$OutputPath;SHA256=(Get-FileHash -LiteralPath $OutputPath).Hash;NativeExecuted=$false;StockStaged=$false;Ready=$false}|ConvertTo-Json
