# Synthetic pure contract tests and tiny-file hash checks only. No native helper,
# live stock inventory/content scan, process, lease or staged game input.
param()
$ErrorActionPreference='Stop';$checks=0
function Assert-Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Assert-Throws([scriptblock]$Body,[string]$Pattern){$caught=$false;try{& $Body}catch{if($_.Exception.Message -notmatch $Pattern){throw};$caught=$true};Assert-Check $caught "Expected $Pattern"}
. "$PSScriptRoot/StockBinding.Core.ps1"
. "$PSScriptRoot/../animation/AnimationFF.Core.ps1"
Assert-AnimationPureImport "$PSScriptRoot/StockBinding.Core.ps1";$checks++
$baseHash='4cf67ebe1645c6c0761b9a24cb4e4630edee9c5d737742c704d624fe60cb3850'
$reviewHash='9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../runtime/synthetic-stock-never-created'))
$names=@('main/code_pre_gfx.ff','zone/assetfile1.pak')+@(0..60|ForEach-Object {"main/tiny-$_.ff"})+
    @('iw7_ship.exe','amd_ags_x64.dll','bink2w64.dll','d3dcompiler_46.dll','steam_api.dll','steam_api64.dll','Steam.dll','tlsdll.dll','main/fileSysCheck.cfg')
$observed=@();$reviewed=@();$entries=@();$i=0
foreach($name in $names){
    $bytes=if($name -ceq 'main/fileSysCheck.cfg'){77}elseif($name -ceq 'tlsdll.dll'){113152}else{1}
    $mode=if($i -lt 63){'HardLink'}else{'Copy'};$id='D088B64A:'+(++$i).ToString('X16')
    $sha=if($name -ceq 'tlsdll.dll'){'6E00DBE90E4CCB60283FAD72A769B36542E587019A0DA9FA42CB6A0FCF91207A'}else{'A'*64}
    $relative=if($name -match '^(main|zone)/([^/]+\.ff)$' -or $name -ceq 'zone/assetfile1.pak'){[IO.Path]::GetFileName($name)}else{$name}
    $external=$name -ceq 'tlsdll.dll'
    $source=if($external){Join-Path (Split-Path $root) 'external-tls.dll'}else{Join-Path $root $relative}
    $entries+=[pscustomobject]@{Relative=$name;Bytes=$bytes;Mode=$mode;SourceId='D088B64A:FFFFFFFFFFFFFFFF'}
    $observed+=[pscustomobject]@{Relative=$name;Bytes=$bytes;Mode=$mode;Source=$source;SourceId=$id;SHA256=$sha;
        Attributes=$(if($name -ceq 'main/fileSysCheck.cfg'){33}else{32});ModifiedUtc='2026-10-12T00:00:00Z';
        ReviewedStockRelative=$(if($external){$null}else{$relative});ExternalToolDependency=$external}
    if(!$external){$reviewed+=[pscustomobject]@{RelativePath=$relative;Length=$bytes;SHA256=$sha;Operation='NTFSHardLinkImmutableStock'}}
}
$baseline=[pscustomobject]@{Schema='iw7.model-ff-build/1';Inputs=$entries;Restored=$true;StockPreserved=$true;RetainedLeaseToken=$null}
$observation=[pscustomobject]@{Schema='iw7.ff-stock-observation/1';CapturedUtc='2026-10-12T03:00:00Z';StockRoot=$root;
    BaselineReceiptSHA256=$baseHash;ReviewedStockManifestSHA256=$reviewHash;Inputs=$observed}
function Get-Bound {@(Get-FFStockBindingInputs $baseline $observation $reviewed $root $baseHash $reviewHash)}
$bound=Get-Bound
Assert-Check ($bound.Count -eq 72 -and @($bound|Where-Object Mode -eq Copy).Count -eq 9) 'Historical operation modes remain 63/9'
Assert-Check (@($bound|Where-Object {$_.ExpectedSourceId -ceq 'D088B64A:FFFFFFFFFFFFFFFF'}).Count -eq 0) 'New identities are accepted through reviewed content, not invented historical identity'
$staged=@(Get-AnimationStockInputs $baseline $root $observation $reviewed $reviewHash)
Assert-Check (@($staged|Where-Object Mode -eq Copy).Count -eq 1 -and @($staged|Where-Object BaselineMode -eq Copy).Count -eq 9) 'Animation explicitly separates staging 71/1 from baseline 63/9'
Assert-Check ($staged[-1].Attributes -eq 33 -and $staged[-1].Mode -ceq 'Copy') 'Read-only sentinel is observed unchanged for independent copy'
$observation.BaselineReceiptSHA256='0'*64;Assert-Throws {Get-Bound} 'hash-bound';$observation.BaselineReceiptSHA256=$baseHash
$observation.ReviewedStockManifestSHA256='0'*64;Assert-Throws {Get-Bound} 'hash-bound';$observation.ReviewedStockManifestSHA256=$reviewHash
$observation|Add-Member NoteProperty Restored $true;Assert-Throws {Get-Bound} 'cannot claim';$observation.PSObject.Properties.Remove('Restored')
$old=$observed[1];$observed[1]=$observed[0];Assert-Throws {Get-Bound} 'relative/mode/bytes/identity';$observed[1]=$old
$observed[0].Mode='Copy';Assert-Throws {Get-Bound} 'relative/mode/bytes/identity';$observed[0].Mode='HardLink'
$observed[0].SHA256='B'*64;Assert-Throws {Get-Bound} 'reviewed retail';$observed[0].SHA256='A'*64
$observed[0].SourceId='bad';Assert-Throws {Get-Bound} 'relative/mode/bytes/identity';$observed[0].SourceId=$bound[0].ExpectedSourceId
$oldSource=$observed[0].Source;$observed[0].Source=Join-Path (Split-Path $root) 'outside.ff';Assert-Throws {Get-Bound} 'reviewed retail';$observed[0].Source=$oldSource
$observed[0].ExternalToolDependency=$true;Assert-Throws {Get-Bound} 'external TLS';$observed[0].ExternalToolDependency=$false
$oldSHA=$observed[-2].SHA256;$observed[-2].SHA256='B'*64;Assert-Throws {Get-Bound} 'external TLS';$observed[-2].SHA256=$oldSHA
$observed[0].Attributes=33;Assert-Throws {Get-Bound} 'read-only';$observed[0].Attributes=32
$observed[0].Attributes=1024;Assert-Throws {Get-Bound} 'redirected';$observed[0].Attributes=32
$observed[0]|Add-Member NoteProperty TargetId 'invented';Assert-Throws {Get-Bound} 'relative/mode/bytes/identity';$observed[0].PSObject.Properties.Remove('TargetId')
Assert-FFStockIdentity $bound[0] $bound[0].ExpectedSourceId;$checks++
Assert-Throws {Assert-FFStockIdentity $bound[0] 'D088B64A:FFFFFFFFFFFFFFFF'} 'NTFS identity changed'
Assert-Throws {Assert-FFStockContent @($bound[0])} 'Guarded observed source identity'

$tiny=Join-Path ([IO.Path]::GetTempPath()) ('stock-binding-pure-'+[guid]::NewGuid().ToString('N')+'.txt')
try{
    [IO.File]::WriteAllText($tiny,'tiny original fixture')
    $hash=(Get-FileHash -LiteralPath $tiny).Hash
    $entry=[pscustomobject]@{Source=$tiny;SourceId='D088B64A:0000000000000001';ExpectedSourceId='D088B64A:0000000000000001';ExpectedSHA256=$hash}
    Assert-FFStockContent @($entry);$checks++
    $conflict=$entry.PSObject.Copy();$conflict.ExpectedSHA256='B'*64
    Assert-Throws {Assert-FFStockContent @($entry,$conflict)} 'content changed'
    [IO.File]::WriteAllText($tiny,'changed fixture')
    Assert-Throws {Assert-FFStockContent @($entry)} 'content changed'
}finally{Remove-Item -LiteralPath $tiny -ErrorAction SilentlyContinue}
[pscustomobject]@{Checks=$checks;NativeLoaded=$false;StockInventoried=$false;LeaseAcquired=$false}|ConvertTo-Json
