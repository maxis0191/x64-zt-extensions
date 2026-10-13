param([Parameter(Mandatory)][string]$StockBindingPath)
# Pure synthetic metadata fixtures. No retail bytes, live IDs, lease or staging.
$ErrorActionPreference='Stop'
if((Get-FileHash -LiteralPath $StockBindingPath).Hash -ine '5c07dfe9adff6527eef3478b153e38f3adf293c85aa732600818cc540ab2bde4'){throw 'Pinned pure stock provider required.'}
. $StockBindingPath
. "$PSScriptRoot/Recipient.Stock.ps1"
$checks=0
function Check([bool]$Value,[string]$Name){if(!$Value){throw $Name};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Name){$failed=$false;try{& $Action|Out-Null}catch{$failed=$true};Check $failed $Name}
$proposal=Get-Content -Raw "$PSScriptRoot/asset-pak-scope-proposal-2026-10-12.json"|ConvertFrom-Json
$root='C:\recipient-fixture\retail';$reviewHash='9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4'
$profile=Get-RecipientSupplementalProfile 'doom-reviewed-all-asset-paks-20261012'
$review=@($proposal.Files|ForEach-Object {[pscustomobject]@{RelativePath=$_.Name;Length=$_.Bytes;SHA256=$_.ExpectedSHA256;Operation='NTFSHardLinkImmutableStock'}})
$assets=@(for($i=0;$i -lt 33;$i++){
    $f=$proposal.Files[$i]
    [pscustomobject]@{Name=$f.Name;Family='assetfile';Bytes=$f.Bytes;SourceId=('AAAAAAAA:'+$i.ToString('X16'));
        ModifiedUtc='2026-09-29T21:46:00Z';Attributes=32;ReviewedSHA256=$f.ExpectedSHA256;ContentVerified=$false}
})
$inventory=[pscustomobject]@{Schema='iw7.recipient-pak-inventory-proposal/1';StockRoot=$root;
    ReviewedManifestSHA256=$reviewHash;RetailPayloadBytesRead=0;Files=@($assets)+@(1..49|ForEach-Object {[pscustomobject]@{Name="imagefile$_.pak";Family='imagefile'}})}
$fixture=[pscustomobject]@{Schema='iw7.recipient-stock-observation/3';Profile=$profile.Name;
    ToolSource='fab935826c898806855376662a8a03317b3ad8f1';StockRoot=$root;ReviewedStockManifestSHA256=$reviewHash;
    CapturedUtc='2026-10-12T09:00:00Z';ContentVerification='DeferredUntilAdmittedRun';
    AdditionalDependencyEvidenceSHA256=$profile.EvidenceSHA256;CompleteInventoryEvidenceSHA256=$profile.InventoryEvidenceSHA256;
    Inputs=@($assets|Where-Object Name -CNE 'assetfile1.pak'|ForEach-Object {
        [pscustomobject]@{Relative=('zone/'+$_.Name);Source=($root+'\'+$_.Name);Mode='HardLink';Bytes=$_.Bytes;
            ModifiedUtc=$_.ModifiedUtc;Attributes=$_.Attributes;SourceId=$_.SourceId;SHA256=$_.ReviewedSHA256;ReviewedStockRelative=$_.Name}
    })}
function Clone($Object){$Object|ConvertTo-Json -Depth 10|ConvertFrom-Json}
function Bind($Observation,$Inventory=$inventory){Get-RecipientSupplementalStockInputs $Observation $review $root $reviewHash $Inventory}
$valid=@(Bind (Clone $fixture))
Check ($valid.Count -eq 32 -and $valid[0].Relative -ceq 'zone/assetfile17.pak' -and $valid[-1].Relative -ceq 'zone/assetfile244.pak') 'Exact 32 supplemental names; pak1 remains baseline'
Check (($profile.Names -join ',') -ceq (($proposal.Files|Where-Object {!$_.AlreadyInBaseline}|ForEach-Object Name) -join ',')) 'Reviewed explicit list matches producer scope'
Check ($profile.Schema -ceq 'iw7.recipient-stock-observation/3' -and $profile.Bytes -eq 4695508096 -and $profile.LimitBytes -eq 4695508096) 'Distinct v3 exact budget'
Check (@($valid|Where-Object StockProfileId -CNE $profile.Name).Count -eq 0) 'Every supplemental carries explicit complete-profile identity'
foreach($mutation in @(
    {param($x) $x.Schema='iw7.recipient-stock-observation/2'},
    {param($x) $x.Profile='observed-cp-paks-17-19-37-53-69'},
    {param($x) $x.Profile='doom-reviewed-all-asset-paks'},
    {param($x) $x.AdditionalDependencyEvidenceSHA256='867E858ECD4BFFDE50A04E62488E42B73F528177E0E01B51A081BC030DBBB280'},
    {param($x) $x.CompleteInventoryEvidenceSHA256='0'*64},
    {param($x) $x.Inputs=@($x.Inputs[0..30])},
    {param($x) $x.Inputs+=,$x.Inputs[0]},
    {param($x) $x.Inputs[1]=$x.Inputs[0]},
    {param($x) $a=$x.Inputs[0];$x.Inputs[0]=$x.Inputs[1];$x.Inputs[1]=$a},
    {param($x) $x.Inputs[0].Relative='zone/imagefile17.pak'},
    {param($x) $x.Inputs[0].Relative='zone/assetfile18.pak'},
    {param($x) $x.Inputs[0].Relative='zone/assetfile1.pak'},
    {param($x) $x.Inputs[0].Source=$root+'\imagefile17.pak'},
    {param($x) $x.Inputs[0].Source=$root+'\..\retail\assetfile17.pak'},
    {param($x) $x.Inputs[0].Bytes--},
    {param($x) $x.Inputs[0].Mode='Copy'},
    {param($x) $x.Inputs[0].SourceId='AAAAAAAA:000000000000FFFF'},
    {param($x) $x.Inputs[0].SourceId=$x.Inputs[1].SourceId},
    {param($x) $x.Inputs[0].SourceId='unknown'},
    {param($x) $x.Inputs[0].SHA256='F'*64},
    {param($x) $x.Inputs[0].Attributes=0},
    {param($x) $x.Inputs[0].Attributes=1},
    {param($x) $x.Inputs[0].Attributes=1024},
    {param($x) $x.Inputs[0].ModifiedUtc='2026-09-29T21:46:01Z'},
    {param($x) $x.Inputs[0]|Add-Member NoteProperty TargetId 'AAAAAAAA:0000000000000001'},
    {param($x) $x|Add-Member NoteProperty Ready $false}
)){
    $bad=Clone $fixture;& $mutation $bad
    Refuses {Bind $bad} ('Complete profile refuses: '+$mutation.ToString().Trim())
}
Refuses {Bind $fixture $null} 'Complete profile refuses absent independent inventory'
foreach($mutation in @(
    {param($x) $x.Schema='iw7.recipient-stock-observation/3'},
    {param($x) $x.StockRoot='C:\another-root'},
    {param($x) $x.ReviewedManifestSHA256='0'*64},
    {param($x) $x.RetailPayloadBytesRead=1},
    {param($x) $x.Files=@($x.Files[0..80])},
    {param($x) $x.Files[1].Name='assetfile18.pak'},
    {param($x) $x.Files[1].Family='imagefile'},
    {param($x) $x.Files[1].SourceId=$x.Files[0].SourceId},
    {param($x) $x.Files[1].SourceId='AAAAAAAA:000000000000FFFF'},
    {param($x) $x.Files[1].Bytes--},
    {param($x) $x.Files[1].ContentVerified=$true},
    {param($x) $x.Files[1].ReviewedSHA256='F'*64},
    {param($x) $x.Files[1].ModifiedUtc='2026-09-29T21:46:01Z'}
)){
    $bad=Clone $inventory;& $mutation $bad
    Refuses {Bind $fixture $bad} ('Independent inventory refuses: '+$mutation.ToString().Trim())
}
$pak1=$assets[0]
$baseline=@([pscustomobject]@{Relative='zone/assetfile1.pak';Mode='HardLink';Bytes=$pak1.Bytes;
    ExpectedSourceId=$pak1.SourceId;ExpectedSHA256=$pak1.ReviewedSHA256;ModifiedUtc=$pak1.ModifiedUtc;Attributes=$pak1.Attributes})
Assert-RecipientCompleteBaseline $baseline $inventory $root $reviewHash;$checks++
foreach($mutation in @(
    {param($x) $x[0].ExpectedSourceId='AAAAAAAA:000000000000FFFF'},
    {param($x) $x[0].ExpectedSHA256='F'*64},
    {param($x) $x[0].Bytes--},
    {param($x) $x[0].ModifiedUtc='2026-09-29T21:46:01Z'}
)){
    $bad=@(Clone $baseline);& $mutation $bad
    Refuses {Assert-RecipientCompleteBaseline $bad $inventory $root $reviewHash} 'Baseline pak1 must match independent complete inventory'
}
Refuses {Assert-RecipientCompleteBaseline @() $inventory $root $reviewHash} 'Missing baseline pak1 refuses'
Refuses {Assert-RecipientCompleteBaseline @($baseline+$baseline) $inventory $root $reviewHash} 'Duplicate baseline pak1 refuses'
$budget=Get-RecipientStockBudget $baseline $valid
Check ($budget.UniqueHashReadBytes -eq 4705977508 -and $budget.UniqueHashReadFiles -eq 33) 'All 33 distinct PAKs counted exactly once'
Check ($budget.SupplementalLogicalBytes -eq 4695508096 -and $budget.AdditionalBytesBeyondFourPAKs -eq 4115416048 -and $budget.StockHardLinks -eq 33 -and $budget.SupplementalCopiedBytes -eq 0) 'Larger budget has exact distinct increment and no copies'
Check (!$budget.ContentVerified -and !$budget.AdditionalResidentBytesMeasured) 'Inventory is not content or memory acceptance'
$bad=@(Clone $valid);$bad[0].StockProfileId='observed-cp-paks-17-19-37-53-69'
Refuses {Get-RecipientStockBudget $baseline $bad} 'Budget refuses mixed old/new profiles'
$bad=@(Clone $valid);$bad[0].Relative='zone/imagefile17.pak'
Refuses {Get-RecipientStockBudget $baseline $bad} 'Budget independently refuses imagefile substitution'
$bad=@(Clone $valid);$bad[0].Bytes--
Refuses {Get-RecipientStockBudget $baseline $bad} 'Budget refuses lower bytes rather than silently changing ceiling'
Refuses {Assert-FFStockIdentity $valid[0] 'AAAAAAAA:000000000000FFFF'} 'Run guard refuses changed live identity before content hash/staging'
Assert-FFStockIdentity $valid[0] $valid[0].ExpectedSourceId;$checks++
"$checks complete-profile checks passed; no retail content read or native execution."
