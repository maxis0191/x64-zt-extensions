param([Parameter(Mandatory)][string]$RecipePath,[Parameter(Mandatory)][string]$RecipeSHA256,[switch]$Seal)
$ErrorActionPreference='Stop'
if((Get-Item -LiteralPath $RecipePath).Length -gt 128KB -or (Get-FileHash -LiteralPath $RecipePath).Hash -ine $RecipeSHA256){throw 'Reviewed seal recipe changed.'}
$recipe=Get-Content -LiteralPath $RecipePath -Raw|ConvertFrom-Json
if($recipe.Schema -cne 'iw7.sound-checksum-seal-recipe/1'){throw 'Exact input sealing recipe required.'}
foreach($path in @($PSCommandPath,(Join-Path $PSScriptRoot 'SealInputs.Core.ps1'))){
    $matches=@($recipe.SourcePins|Where-Object Path -IEQ $path)
    if($matches.Count -ne 1){throw 'Sealing entry/core not source-bound.'}
}
foreach($pin in $recipe.SourcePins){
    if((Get-Item -LiteralPath $pin.Path).Length -gt 256KB -or (Get-FileHash -LiteralPath $pin.Path).Hash -ine $pin.SHA256){throw 'Sealing helper source changed.'}
}
. "$PSScriptRoot/SealInputs.Core.ps1"
Assert-ChecksumSealPath $RecipePath;Assert-ChecksumSealPath $recipe.InventoryPath
if((Get-Item -LiteralPath $recipe.InventoryPath).Length -gt 4MB -or
    (Get-FileHash -LiteralPath $recipe.InventoryPath).Hash -ine $recipe.InventorySHA256){throw 'Reviewed metadata inventory changed.'}
$inventory=Get-Content -LiteralPath $recipe.InventoryPath -Raw|ConvertFrom-Json
Assert-ChecksumSealInventory $inventory
Assert-ChecksumSealPath $recipe.OutputRoot
if(Test-Path -LiteralPath $recipe.OutputRoot){throw 'Sealing requires a fresh unused output root.'}
if(!$Seal){
    [ordered]@{Status='PlanOnly';Files=$inventory.FileCount;InputBytes=$inventory.TotalBytes;SequentialReadBytes=2L*$inventory.TotalBytes;
        Categories=$inventory.Categories;PhysicalBytes=1GB;CommitBytes=2GB;ObservedDeadlineSeconds=120;OutputLimitBytes=16MB;
        OutputRoot=$recipe.OutputRoot;NoNativeBuild=$true;NoReusableInputContentRead=$true}|ConvertTo-Json -Depth 6
    return
}
# Existing scheduler only; no new native job owner, observer or probe type.
$guards=[Collections.Generic.List[IDisposable]]::new()
try {
    foreach($pin in @($recipe.SourcePins)+@([pscustomobject]@{Path=$RecipePath;SHA256=$RecipeSHA256},
        [pscustomobject]@{Path=$recipe.InventoryPath;SHA256=$recipe.InventorySHA256})){
        Assert-ChecksumSealPath $pin.Path
        $guards.Add([IO.File]::Open($pin.Path,'Open','Read','Read'))
        if((Get-FileHash -LiteralPath $pin.Path).Hash -ine $pin.SHA256){throw 'Guarded sealing source drift.'}
    }
    . $recipe.Scheduler
    Invoke-ChecksumInputSeal $recipe $inventory $RecipeSHA256|ConvertTo-Json -Depth 6
} finally {foreach($guard in $guards){$guard.Dispose()}}
