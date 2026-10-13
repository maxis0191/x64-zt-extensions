param([Parameter(Mandatory)][string]$StockBindingPath)
# Pure receipt fixtures: no stock read, directory creation, lease or native job.
$ErrorActionPreference='Stop'
if((Get-FileHash -LiteralPath $StockBindingPath).Hash -ine '5c07dfe9adff6527eef3478b153e38f3adf293c85aa732600818cc540ab2bde4'){throw 'Pinned pure stock provider required.'}
. $StockBindingPath
$checks=0
function Check([bool]$Value,[string]$Name){if(!$Value){throw $Name};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Name){$failed=$false;try{& $Action|Out-Null}catch{$failed=$true};Check $failed $Name}
$errors=$null;$tokens=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Recipient.Stock.ps1'),[ref]$tokens,[ref]$errors)
Check ($errors.Count -eq 0) 'Stock helper parses'
Check (@($ast.EndBlock.Statements|Where-Object {$_ -isnot [Management.Automation.Language.FunctionDefinitionAst]}).Count -eq 0) 'Stock helper import is pure'
. "$PSScriptRoot/Recipient.Stock.ps1"
$root='C:\recipient-fixture\retail';$reviewHash='9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4'
$names=@('assetfile17.pak','assetfile19.pak','assetfile37.pak','assetfile53.pak')
$sizes=@(104595492,418201636,53477412,3817508)
$review=@(for($i=0;$i -lt 4;$i++){[pscustomobject]@{RelativePath=$names[$i];Length=$sizes[$i];SHA256=([string]($i+1)*64);Operation='NTFSHardLinkImmutableStock'}})
$fixture=[pscustomobject]@{Schema='iw7.recipient-stock-observation/1';Profile='observed-cp-paks-17-19-37-53';
    ToolSource='fab935826c898806855376662a8a03317b3ad8f1';StockRoot=$root;ReviewedStockManifestSHA256=$reviewHash;
    CapturedUtc='2026-10-12T06:30:00Z';ContentVerification='DeferredUntilAdmittedRun';Inputs=@(for($i=0;$i -lt 4;$i++){
        [pscustomobject]@{Relative=('zone/'+$names[$i]);Source=($root+'\'+$names[$i]);Mode='HardLink';Bytes=$sizes[$i];
            ModifiedUtc='2026-09-29T21:46:02Z';Attributes=32;SourceId=('AAAAAAAA:'+$i.ToString('X16'));
            SHA256=$review[$i].SHA256;ReviewedStockRelative=$names[$i]}
    })}
function Clone-Fixture {$fixture|ConvertTo-Json -Depth 8|ConvertFrom-Json}
function Bind-Fixture($observation) {Get-RecipientSupplementalStockInputs $observation $review $root $reviewHash}
$valid=@(Bind-Fixture (Clone-Fixture))
Check ($valid.Count -eq 4 -and ($valid.Relative -join ',') -ceq (($names|ForEach-Object {'zone/'+$_}) -join ',')) 'Exact four ordered hardlinks'
Check (@($valid|Where-Object Mode -CNE HardLink).Count -eq 0 -and @($valid|Where-Object StockProfile -CNE RecipientSupplemental).Count -eq 0) 'Separate supplemental profile'
Check ($valid[0].ExpectedSourceId -ceq $fixture.Inputs[0].SourceId -and $valid[0].ExpectedSHA256 -ceq $fixture.Inputs[0].SHA256) 'Shared run identity and content guards receive expected fields'
foreach($mutation in @(
    {param($x) $x.Schema='iw7.ff-stock-observation/1'},
    {param($x) $x.Profile='all-retail'},
    {param($x) $x.ToolSource='0'*40},
    {param($x) $x.ReviewedStockManifestSHA256='0'*64},
    {param($x) $x.StockRoot='C:\other'},
    {param($x) $x.CapturedUtc='invalid'},
    {param($x) $x.ContentVerification='Verified'},
    {param($x) $x.Inputs=@($x.Inputs[0..2])},
    {param($x) $x.Inputs+=,$x.Inputs[0]},
    {param($x) $x.Inputs[1]=$x.Inputs[0]},
    {param($x) $x.Inputs[0].Relative='assetfile17.pak'},
    {param($x) $x.Inputs[0].Relative='zone/../assetfile17.pak'},
    {param($x) $x.Inputs[0].Source='C:\other\assetfile17.pak'},
    {param($x) $x.Inputs[0].Source=$root+'\..\retail\assetfile17.pak'},
    {param($x) $x.Inputs[0].Mode='Copy'},
    {param($x) $x.Inputs[0].Bytes--},
    {param($x) $x.Inputs[0].SHA256='F'*64},
    {param($x) $x.Inputs[0].ReviewedStockRelative='assetfile1.pak'},
    {param($x) $x.Inputs[0].SourceId='unknown'},
    {param($x) $x.Inputs[0].ModifiedUtc='invalid'},
    {param($x) $x.Inputs[0].Attributes=1},
    {param($x) $x.Inputs[0].Attributes=16},
    {param($x) $x.Inputs[0].Attributes=1024},
    {param($x) $x.Inputs[0]|Add-Member NoteProperty TargetId 'AAAAAAAA:0000000000000000'},
    {param($x) $x|Add-Member NoteProperty Restored $true},
    {param($x) $x|Add-Member NoteProperty Ready $false}
)){
    $bad=Clone-Fixture;& $mutation $bad
    Refuses {Bind-Fixture $bad} ('Refuses mutation: '+$mutation.ToString().Trim())
}
Refuses {Get-RecipientSupplementalStockInputs (Clone-Fixture) @($review+$review[0]) $root $reviewHash} 'Duplicate reviewed row'
Refuses {Get-RecipientSupplementalStockInputs (Clone-Fixture) $review $root ('0'*64)} 'Unreviewed manifest pin'
$baseline=@(
    [pscustomobject]@{Relative='main/test.ff';Mode='HardLink';Bytes=100;ExpectedSourceId='BBBBBBBB:0000000000000000';ExpectedSHA256=('A'*64)},
    [pscustomobject]@{Relative='zone/test.ff';Mode='HardLink';Bytes=100;ExpectedSourceId='BBBBBBBB:0000000000000000';ExpectedSHA256=('A'*64)},
    [pscustomobject]@{Relative='main/fileSysCheck.cfg';Mode='Copy';Bytes=77;ExpectedSourceId='BBBBBBBB:0000000000000001';ExpectedSHA256=('B'*64)})
$budget=Get-RecipientStockBudget $baseline $valid
Check ($budget.SupplementalLogicalBytes -eq 580092048 -and $budget.SupplementalLimitBytes -eq 600MB -and $budget.SupplementalCopiedBytes -eq 0) 'Supplemental byte bound and zero copies'
Check ($budget.UniqueHashReadBytes -eq 580092225 -and $budget.UniqueHashReadFiles -eq 6) 'Physical source identities deduplicate hash-read budget'
Check ($budget.StockHardLinks -eq 6 -and $budget.StockCopiedBytes -eq 77 -and !$budget.ContentVerified -and !$budget.AdditionalResidentBytesMeasured) 'No metadata-only content or resident-memory claim'
Refuses {Get-RecipientStockBudget @($baseline+$baseline[0]) $valid} 'Duplicate staged relative'
$baseline[1].Bytes=101
Refuses {Get-RecipientStockBudget $baseline $valid} 'Same identity with inconsistent bytes'
$baseline[1].Bytes=100;$baseline[1].ExpectedSHA256='F'*64
Refuses {Get-RecipientStockBudget $baseline $valid} 'Same identity with inconsistent content'
$baseline[1].ExpectedSHA256='A'*64
# Explicit 4+1 v2 receipt: invented fixture bytes/hashes, no retail file read.
$reviewFive=@($review)+@([pscustomobject]@{RelativePath='assetfile69.pak';Length=386465828;SHA256=('5'*64);Operation='NTFSHardLinkImmutableStock'})
$five=Clone-Fixture;$five.Schema='iw7.recipient-stock-observation/2';$five.Profile='observed-cp-paks-17-19-37-53-69'
$five|Add-Member NoteProperty AdditionalDependencyEvidenceSHA256 '867E858ECD4BFFDE50A04E62488E42B73F528177E0E01B51A081BC030DBBB280'
$five.Inputs+=,[pscustomobject]@{Relative='zone/assetfile69.pak';Source=($root+'\assetfile69.pak');Mode='HardLink';Bytes=386465828;
    ModifiedUtc='2026-09-29T21:46:16Z';Attributes=32;SourceId='AAAAAAAA:0000000000000004';SHA256=('5'*64);ReviewedStockRelative='assetfile69.pak'}
function Clone-Five {$five|ConvertTo-Json -Depth 8|ConvertFrom-Json}
function Bind-Five($observation) {Get-RecipientSupplementalStockInputs $observation $reviewFive $root $reviewHash}
$validFive=@(Bind-Five (Clone-Five));$budgetFive=Get-RecipientStockBudget $baseline $validFive
Check ($validFive.Count -eq 5 -and $validFive[4].Relative -ceq 'zone/assetfile69.pak' -and $validFive[4].Mode -ceq 'HardLink') 'Explicit fifth observed PAK only'
Check (@($validFive|Where-Object StockProfileId -CNE $five.Profile).Count -eq 0) 'Named v2 profile retained on every input'
Check ($budgetFive.SupplementalProfile -ceq $five.Profile -and $budgetFive.SupplementalLogicalBytes -eq 966557876 -and $budgetFive.SupplementalLimitBytes -eq 966557876) 'V2 has its exact distinct observed byte ceiling'
Check ($budgetFive.AdditionalBytesBeyondFourPAKs -eq 386465828 -and $budgetFive.SupplementalCopiedBytes -eq 0) 'Increment is explicit with zero PAK payload copies'
Check ($budgetFive.UniqueHashReadBytes -eq 966558053 -and $budgetFive.UniqueHashReadFiles -eq 7 -and $budgetFive.StockHardLinks -eq 7 -and $budgetFive.StockCopiedBytes -eq 77) 'Five-PAK identity-deduplicated fixture budget'
Check (!$budgetFive.ContentVerified -and !$budgetFive.AdditionalResidentBytesMeasured) 'V2 metadata cannot claim fresh bytes or peak memory'
foreach($mutation in @(
    {param($x) $x.Profile='observed-cp-paks-17-19-37-53'},
    {param($x) $x.Schema='iw7.recipient-stock-observation/1'},
    {param($x) $x.Profile='observed-cp-paks-17-19-37-53-69-70'},
    {param($x) $x.AdditionalDependencyEvidenceSHA256=$null},
    {param($x) $x.AdditionalDependencyEvidenceSHA256='0'*64},
    {param($x) $x.Inputs=@($x.Inputs[0..3])},
    {param($x) $x.Inputs+=,$x.Inputs[4]},
    {param($x) $x.Inputs[4]=$x.Inputs[3]},
    {param($x) $x.Inputs[4].Relative='zone/assetfile70.pak'},
    {param($x) $x.Inputs[4].Source='C:\other\assetfile69.pak'},
    {param($x) $x.Inputs[4].Mode='Copy'},
    {param($x) $x.Inputs[4].Bytes--},
    {param($x) $x.Inputs[4].SHA256='F'*64},
    {param($x) $x.Inputs[4].Attributes=1024},
    {param($x) $x.Inputs[4].SourceId='unknown'}
)){
    $bad=Clone-Five;& $mutation $bad
    Refuses {Bind-Five $bad} ('V2 refuses mutation: '+$mutation.ToString().Trim())
}
Refuses {Get-RecipientSupplementalStockInputs (Clone-Five) $review $root $reviewHash} 'V2 cannot use a reviewed set missing pak69'
$bad=Clone-Fixture;$bad.Schema='iw7.recipient-stock-observation/2'
Refuses {Bind-Fixture $bad} 'Old four-PAK observation cannot masquerade as schema2'
$badBudget=$validFive|ConvertTo-Json -Depth 6|ConvertFrom-Json
$badBudget[4].StockProfileId='observed-cp-paks-17-19-37-53'
Refuses {Get-RecipientStockBudget $baseline $badBudget} 'Mixed profile identities cannot choose a budget'
$badBudget=$validFive|ConvertTo-Json -Depth 6|ConvertFrom-Json;$badBudget[4].Bytes--
Refuses {Get-RecipientStockBudget $baseline $badBudget} 'Named five-PAK budget refuses changed logical size'
$oldAgain=@(Bind-Fixture (Clone-Fixture));$oldBudget=Get-RecipientStockBudget $baseline $oldAgain
Check ($oldAgain.Count -eq 4 -and $oldBudget.SupplementalLimitBytes -eq 600MB -and $oldBudget.SupplementalLogicalBytes -eq 580092048 -and $oldBudget.AdditionalBytesBeyondFourPAKs -eq 0) 'Original profile scope and 600 MiB budget remain unchanged'
"$checks supplemental stock checks passed; no stock content read or native execution."
