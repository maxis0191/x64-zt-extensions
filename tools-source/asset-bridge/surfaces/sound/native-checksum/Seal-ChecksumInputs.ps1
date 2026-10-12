param([Parameter(Mandatory)][string]$RecipePath,[Parameter(Mandatory)][string]$RecipeSHA256,[switch]$Seal)
$ErrorActionPreference='Stop'
# Bootstrap guards precede hash/parse/import. They are also retained in Plan.
$guards=[Collections.Generic.List[IDisposable]]::new()
$files=[Collections.Generic.Dictionary[string,IO.FileStream]]::new([StringComparer]::OrdinalIgnoreCase)
function Open-ChecksumSealBootstrap([string]$Path,[long]$Maximum) {
    if(![IO.Path]::IsPathFullyQualified($Path)){throw 'Absolute sealing bootstrap path required.'}
    $full=[IO.Path]::GetFullPath($Path)
    for($p=$full;$p;$p=Split-Path $p -Parent){
        if((Test-Path -LiteralPath $p) -and (Get-Item -LiteralPath $p -Force).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){
            throw 'Redirected sealing bootstrap path refused.'
        }
    }
    if(!$files.ContainsKey($full)){
        $stream=[IO.File]::Open($full,'Open','Read','Read')
        $guards.Add($stream);$files.Add($full,$stream)
    }
    $stream=$files[$full]
    if($stream.Length -gt $Maximum){throw 'Bounded sealing bootstrap file required.'}
    $stream
}
function Get-ChecksumSealBootstrapHash($Stream) {
    $Stream.Position=0
    [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($Stream)).ToLowerInvariant()
}
function Read-ChecksumSealBootstrapText($Stream) {
    $Stream.Position=0
    $reader=[IO.StreamReader]::new($Stream,[Text.UTF8Encoding]::new($false,$true),$true,4096,$true)
    try{$reader.ReadToEnd()}finally{$reader.Dispose()}
}
try {
    $recipeStream=Open-ChecksumSealBootstrap $RecipePath 128KB
    # Core and entry locations are known without parsing the recipe.
    $corePath=Join-Path $PSScriptRoot 'SealInputs.Core.ps1'
    $null=Open-ChecksumSealBootstrap $corePath 256KB
    $null=Open-ChecksumSealBootstrap $PSCommandPath 256KB
    if((Get-ChecksumSealBootstrapHash $recipeStream) -ine $RecipeSHA256){throw 'Reviewed seal recipe changed.'}
    $recipe=Read-ChecksumSealBootstrapText $recipeStream|ConvertFrom-Json
    if($recipe.Schema -cne 'iw7.sound-checksum-seal-recipe/1' -or @($recipe.SourcePins).Count -gt 16){throw 'Exact bounded input sealing recipe required.'}
    $inventoryStream=Open-ChecksumSealBootstrap $recipe.InventoryPath 4MB
    foreach($pin in $recipe.SourcePins){$null=Open-ChecksumSealBootstrap $pin.Path 256KB}
    foreach($path in @($PSCommandPath,$corePath,$recipe.Scheduler)){
        if(@($recipe.SourcePins|Where-Object Path -IEQ $path).Count -ne 1){throw 'Sealing entry/core/scheduler not source-bound.'}
    }
    foreach($pin in $recipe.SourcePins){
        if((Get-ChecksumSealBootstrapHash $files[[IO.Path]::GetFullPath($pin.Path)]) -ine $pin.SHA256){throw 'Guarded sealing helper source changed.'}
    }
    if((Get-ChecksumSealBootstrapHash $inventoryStream) -ine $recipe.InventorySHA256){throw 'Reviewed metadata inventory changed.'}
    $inventory=Read-ChecksumSealBootstrapText $inventoryStream|ConvertFrom-Json
    . $corePath
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
    . $recipe.Scheduler
    Invoke-ChecksumInputSeal $recipe $inventory $RecipeSHA256|ConvertTo-Json -Depth 6
} finally {foreach($guard in $guards){$guard.Dispose()}}
