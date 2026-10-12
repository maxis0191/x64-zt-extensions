param(
    [Parameter(Mandatory)][string]$ReviewPlanPath,[Parameter(Mandatory)][string]$ReviewPlanSHA256,
    [Parameter(Mandatory)][string]$StockParametersPath,[Parameter(Mandatory)][string]$StockParametersSHA256,
    [Parameter(Mandatory)][string]$OutputPath
)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/SoundFF.Core.ps1"
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
