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
"$checks supplemental stock checks passed; no stock content read or native execution."
