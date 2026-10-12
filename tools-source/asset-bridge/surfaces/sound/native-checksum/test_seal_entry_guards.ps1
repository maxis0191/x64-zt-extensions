$ErrorActionPreference='Stop'
$root=Join-Path ([IO.Path]::GetTempPath()) ('sound-seal-entry-test-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
$global:ChecksumSealEntryFixture=@{Checks=0;Denied=[Collections.Generic.List[string]]::new()}
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$global:ChecksumSealEntryFixture.Checks++}
try {
    $global:ChecksumSealEntryFixture.Entry=Join-Path $root 'Seal-ChecksumInputs.ps1';$global:ChecksumSealEntryFixture.Core=Join-Path $root 'SealInputs.Core.ps1'
    [IO.File]::Copy((Join-Path $PSScriptRoot 'Seal-ChecksumInputs.ps1'),$global:ChecksumSealEntryFixture.Entry)
    [IO.File]::Copy((Join-Path $PSScriptRoot 'SealInputs.Core.ps1'),$global:ChecksumSealEntryFixture.Core)
    $scheduler=Join-Path $root 'scheduler.ps1';[IO.File]::WriteAllText($scheduler,'# fixture, never imported in Plan')
    $inputFile=Join-Path $root 'small-input.txt';[IO.File]::WriteAllText($inputFile,'data');$f=Get-Item -LiteralPath $inputFile
    $global:ChecksumSealEntryFixture.InventoryPath=Join-Path $root 'inventory.json'
    $inventory=[ordered]@{Schema='iw7.sound-checksum-input-inventory/1';FileCount=1;TotalBytes=4L;Categories=@{};
        Inputs=@([ordered]@{Path=$inputFile;Bytes=4L;Attributes=[int]$f.Attributes;ModifiedUtcTicks=$f.LastWriteTimeUtc.Ticks;
            Category='fixture';ExpectedSHA256=$null})}
    [IO.File]::WriteAllText($global:ChecksumSealEntryFixture.InventoryPath,($inventory|Microsoft.PowerShell.Utility\ConvertTo-Json -Depth 8))
    $global:ChecksumSealEntryFixture.RecipePath=Join-Path $root 'recipe.json'
    $recipe=[ordered]@{Schema='iw7.sound-checksum-seal-recipe/1';InventoryPath=$global:ChecksumSealEntryFixture.InventoryPath;
        InventorySHA256=(Get-FileHash -LiteralPath $global:ChecksumSealEntryFixture.InventoryPath).Hash;OutputRoot=(Join-Path $root 'must-not-exist');Scheduler=$scheduler;
        SourcePins=@(foreach($p in @($global:ChecksumSealEntryFixture.Entry,$global:ChecksumSealEntryFixture.Core,$scheduler)){[ordered]@{Path=$p;SHA256=(Get-FileHash -LiteralPath $p).Hash}})}
    [IO.File]::WriteAllText($global:ChecksumSealEntryFixture.RecipePath,($recipe|Microsoft.PowerShell.Utility\ConvertTo-Json -Depth 8))
    $recipeHash=(Get-FileHash -LiteralPath $global:ChecksumSealEntryFixture.RecipePath).Hash
    $coreHash=(Get-FileHash -LiteralPath $global:ChecksumSealEntryFixture.Core).Hash
    function Add-Type {throw 'Plan loaded a native type'}
    function Enter-IW7ResourceLease {throw 'Plan entered admission'}
    function Get-CimInstance {throw 'Plan queried CIM'}
    function Start-Process {throw 'Plan started a process'}
    function Try-IntervalWrite([string]$Path,[string]$Name){
        $denied=$false
        try{[IO.File]::WriteAllText($Path,'fixture mutation at check/import interval')}
        catch [IO.IOException]{$denied=$true}
        Check $denied ('Guard must already exist at '+$Name)
        $global:ChecksumSealEntryFixture.Denied.Add($Name)
    }
    function ConvertFrom-Json {
        param([Parameter(ValueFromPipeline)][string]$InputObject)
        process {
            $data=Microsoft.PowerShell.Utility\ConvertFrom-Json -InputObject $InputObject
            if($data.Schema -ceq 'iw7.sound-checksum-seal-recipe/1'){
                # Recipe already hashed; core has not yet been hashed/imported.
                Try-IntervalWrite $global:ChecksumSealEntryFixture.RecipePath 'recipe-before-parse-return'
                Try-IntervalWrite $global:ChecksumSealEntryFixture.Core 'core-before-first-hash'
            }
            if($data.Schema -ceq 'iw7.sound-checksum-input-inventory/1'){
                # All source and inventory hashes have passed; import is next.
                Try-IntervalWrite $global:ChecksumSealEntryFixture.Core 'core-after-hash-before-import'
                Try-IntervalWrite $global:ChecksumSealEntryFixture.InventoryPath 'inventory-after-hash-before-parse-return'
            }
            $data
        }
    }
    function ConvertTo-Json {
        param([Parameter(ValueFromPipeline)]$InputObject,[int]$Depth)
        process {
            if($InputObject.Status -ceq 'PlanOnly'){
                Try-IntervalWrite $global:ChecksumSealEntryFixture.RecipePath 'recipe-at-plan-output'
                Try-IntervalWrite $global:ChecksumSealEntryFixture.Core 'core-at-plan-output'
                Try-IntervalWrite $global:ChecksumSealEntryFixture.InventoryPath 'inventory-at-plan-output'
            }
            Microsoft.PowerShell.Utility\ConvertTo-Json -InputObject $InputObject -Depth $Depth
        }
    }
    $result=(& $global:ChecksumSealEntryFixture.Entry -RecipePath $global:ChecksumSealEntryFixture.RecipePath -RecipeSHA256 $recipeHash|Out-String)|Microsoft.PowerShell.Utility\ConvertFrom-Json
    Check ($result.Status -ceq 'PlanOnly' -and !(Test-Path -LiteralPath $recipe.OutputRoot)) 'Default Plan remains passive'
    Check ($global:ChecksumSealEntryFixture.Denied.Count -eq 7 -and (Get-FileHash -LiteralPath $global:ChecksumSealEntryFixture.Core).Hash -ceq $coreHash) 'Every targeted interval denied writes and preserved source'
    [IO.File]::WriteAllText($global:ChecksumSealEntryFixture.Core,'fixture may change only after Plan guards dispose')
    Check ((Get-FileHash -LiteralPath $global:ChecksumSealEntryFixture.Core).Hash -cne $coreHash) 'All Plan guards released on return'
    Check (!(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7.AnimationRig.JobMembers' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]))) 'No native types loaded'
    [ordered]@{Checks=$global:ChecksumSealEntryFixture.Checks;DeniedMutationIntervals=$global:ChecksumSealEntryFixture.Denied.Count;NativeCommands=0;LiveReservations=0}|Microsoft.PowerShell.Utility\ConvertTo-Json
} finally {
    foreach($file in Get-ChildItem -LiteralPath $root -Recurse -File){Remove-Item -LiteralPath $file.FullName -Force}
    foreach($directory in Get-ChildItem -LiteralPath $root -Recurse -Directory|Sort-Object FullName -Descending){[IO.Directory]::Delete($directory.FullName)}
    [IO.Directory]::Delete($root)
    Remove-Variable -Name ChecksumSealEntryFixture -Scope Global
}
