# Legacy pair and bounded explicit collections; invented metadata, never retail data.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Test-T7CatalogueBootstrap.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Existing bootstrap fixture parse errors.'}
foreach($name in 'Check','Refuses','Copy-Value','Get-Item','New-Fixture'){
    $functions=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true))
    if($functions.Count -ne 1){throw ('One existing fixture helper required: '+$name)}
    . ([scriptblock]::Create($functions[0].Extent.Text))
}
$script:checks=0;$script:provider=@{};$script:ids=@{};$script:observedId='AABBCCDD:0000000000000001'
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-bootstraps-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
function Get-T7CatalogueFileId([string]$Path){$script:ids[$Path]}
function New-Pair {
    $f=New-Fixture;$first=$f.Plan.Bootstrap;$second=Copy-Value $first
    $second.Path=Join-Path $root 'core_pre_gfx.ff';$second.Bytes=22351168;$second.SHA256='1'*64
    $second.FileId='AABBCCDD:0000000000000002';$second.RelativePath='zone/core_pre_gfx.ff'
    $second.QualificationReceipt=[pscustomobject]@{Path=(Join-Path $root 'invented-core-receipt.json');Bytes=100;SHA256=('2'*64)}
    $second.QualificationScript=[pscustomobject]@{Path=(Join-Path $root 'invented-core-qualification.ps1');Bytes=100;SHA256=('3'*64)}
    $metadata=Copy-Value $f.Plan.InputMetadata[-1];$metadata.Path=$second.Path;$metadata.Bytes=$second.Bytes
    $f.Plan.InputMetadata+=@($metadata)
    $f.Plan.Bindings+=@([pscustomobject]@{Path=$second.Path;Bytes=$second.Bytes;SHA256=$second.SHA256;IsText=$false})
    foreach($pin in @($second.QualificationReceipt,$second.QualificationScript)){
        $row=Copy-Value $pin;$row|Add-Member NoteProperty IsText $true;$f.Plan.Bindings+=@($row)
    }
    foreach($row in $f.Plan.Bindings[-3..-1]){
        $script:provider[$row.Path]=[pscustomobject]@{PSIsContainer=$false;Length=$row.Bytes;Attributes='Archive';CreationTimeUtc=([datetimeoffset]$metadata.CreationUtc).UtcDateTime;LastWriteTimeUtc=([datetimeoffset]$metadata.LastWriteUtc).UtcDateTime}
    }
    $f.Plan|Add-Member NoteProperty Bootstraps @($first,$second);$f.Plan.PSObject.Properties.Remove('Bootstrap')
    $f.Plan.OutputLimitBytes+=22351168
    $receipt=Copy-Value $f.Receipt;$receipt.ScriptSHA256=$second.QualificationScript.SHA256
    $receipt.SHA256=$second.SHA256;$receipt.FileId=$second.FileId;$receipt.GuardedReadBytesPerPass=$second.Bytes
    $receipt.Input=Copy-Value $metadata
    foreach($key in 'MetadataBefore','MetadataAfter'){$receipt.$key.Bytes=$second.Bytes;$receipt.$key.FileId=$second.FileId}
    $f|Add-Member NoteProperty CoreReceipt $receipt
    $script:ids=@{};$script:ids[$first.Path]=$first.FileId;$script:ids[$second.Path]=$second.FileId
    $f
}
function New-Qualified([int]$Count=3,[string]$Policy='QualifiedCollectionV1') {
    $f=New-Fixture;$template=Copy-Value $f.Plan.Bootstrap;$metadata=Copy-Value $f.Plan.InputMetadata[-1]
    $f.Plan.InputMetadata=@($f.Plan.InputMetadata[0..3]);$f.Plan.Bindings=@($f.Plan.Bindings[0..4])
    $f.Plan.PSObject.Properties.Remove('Bootstrap')
    $f.Plan|Add-Member NoteProperty BootstrapPolicy $Policy
    $f.Plan|Add-Member NoteProperty Bootstraps @()
    $f|Add-Member NoteProperty Receipts @()
    $f.Plan.OutputLimitBytes=106059160L+$f.Plan.CandidateBytes
    for($i=0;$i -lt 17;$i++){
        $pin=[pscustomobject]@{Path=(Join-Path $root ('base-text-'+$i+'.json'));Bytes=100;SHA256=('c'*64);IsText=$true}
        $f.Plan.Bindings+=@($pin)
        $script:provider[$pin.Path]=[pscustomobject]@{PSIsContainer=$false;Length=100;Attributes='Archive'}
    }
    $script:ids=@{}
    for($i=0;$i -lt $Count;$i++){
        $b=Copy-Value $template;$b.Path=Join-Path $root ('invented_'+$i+'.ff');$b.RelativePath='zone/invented_'+$i+'.ff'
        $b.Bytes=1000;$b.FileId='AABBCCDD:'+($i+10).ToString('X16')
        $b.QualificationReceipt.Path=Join-Path $root ('qualified-'+$i+'.json')
        $b.QualificationScript.Path=Join-Path $root ('qualify-'+$i+'.ps1')
        $m=Copy-Value $metadata;$m.Path=$b.Path;$m.Bytes=$b.Bytes
        $r=Copy-Value $f.Receipt;$r.FileId=$b.FileId;$r.GuardedReadBytesPerPass=$b.Bytes;$r.Input=Copy-Value $m
        foreach($key in 'MetadataBefore','MetadataAfter'){$r.$key.Bytes=$b.Bytes;$r.$key.FileId=$b.FileId}
        $f.Plan.Bootstraps+=@($b);$f.Plan.InputMetadata+=@($m);$f.Receipts+=@($r);$f.Plan.OutputLimitBytes+=$b.Bytes
        $pins=@([pscustomobject]@{Path=$b.Path;Bytes=$b.Bytes;SHA256=$b.SHA256;IsText=$false})
        foreach($p in @($b.QualificationReceipt,$b.QualificationScript)){$copy=Copy-Value $p;$copy|Add-Member NoteProperty IsText $true;$pins+=@($copy)}
        $f.Plan.Bindings+=$pins
        foreach($p in $pins){$script:provider[$p.Path]=[pscustomobject]@{PSIsContainer=$false;Length=$p.Bytes;Attributes='Archive';CreationTimeUtc=([datetimeoffset]$m.CreationUtc).UtcDateTime;LastWriteTimeUtc=([datetimeoffset]$m.LastWriteUtc).UtcDateTime}}
        $script:ids[$b.Path]=$b.FileId
    }
    $f
}
function Set-QualifiedBytes($Fixture,[int]$Index,[long]$Bytes) {
    $b=$Fixture.Plan.Bootstraps[$Index];$old=$b.Bytes;$b.Bytes=$Bytes
    $Fixture.Plan.OutputLimitBytes+=$Bytes-$old
    ($Fixture.Plan.Bindings|Where-Object Path -CEQ $b.Path).Bytes=$Bytes
    ($Fixture.Plan.InputMetadata|Where-Object Path -CEQ $b.Path).Bytes=$Bytes
    $script:provider[$b.Path].Length=$Bytes
    $r=$Fixture.Receipts[$Index];$r.GuardedReadBytesPerPass=$Bytes;$r.Input.Bytes=$Bytes
    $r.MetadataBefore.Bytes=$Bytes;$r.MetadataAfter.Bytes=$Bytes
}
function New-InputIds($Fixture) {
    $n=100
    foreach($m in $Fixture.Plan.InputMetadata){
        $b=@($Fixture.Plan.Bootstraps|Where-Object Path -CEQ $m.Path)
        [pscustomobject]@{Path=$m.Path;FileId=$(if($b.Count){$b[0].FileId}else{'AABBCCDD:'+($n++).ToString('X16')})}
    }
}
try {
    $f=New-Pair;$items=@(Get-T7CatalogueBootstraps $f.Plan)
    Check ($items.Count -eq 2 -and $items[0].Bytes -eq 832 -and $items[1].Bytes -eq 22351168) 'Two exact bootstrap items lost.'
    Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
    Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipt $items[0].Path;$checks++
    Assert-T7CatalogueBootstrapReceipt $f.Plan $f.CoreReceipt $items[1].Path;$checks++
    Assert-T7CatalogueBootstrapIdentity $f.Plan;$checks++
    Check ($f.Plan.InputMetadata.Count -eq 6 -and $f.Plan.OutputLimitBytes -eq 150161432) 'Six-input budget differs.'
    Refuses {Get-T7CatalogueBootstrap $f.Plan} 'Single bootstrap'
    Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.CoreReceipt} 'Select one'
    Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.CoreReceipt (Join-Path $root 'unknown.ff')} 'Select one'
    Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipt $items[1].Path} 'successful'
    foreach($case in 'null','object','one','three','mixed','reordered','duplicate','unknown'){
        $f=New-Pair
        switch($case){
            null {$f.Plan.Bootstraps=$null}
            object {$f.Plan.Bootstraps=$f.Plan.Bootstraps[0]}
            one {$f.Plan.Bootstraps=@($f.Plan.Bootstraps[0])}
            three {$f.Plan.Bootstraps+=@(Copy-Value $f.Plan.Bootstraps[1])}
            mixed {$f.Plan|Add-Member NoteProperty Bootstrap (Copy-Value $f.Plan.Bootstraps[0])}
            reordered {$f.Plan.Bootstraps=@($f.Plan.Bootstraps[1],$f.Plan.Bootstraps[0])}
            duplicate {$f.Plan.Bootstraps[1]=Copy-Value $f.Plan.Bootstraps[0]}
            unknown {$f.Plan.Bootstraps[1].Path=Join-Path $root 'unknown.ff'}
        }
        Refuses {Get-T7CatalogueBootstraps $f.Plan}
    }
    foreach($field in 'Bytes','RelativePath','SHA256','FileId','HashProvenance'){
        $f=New-Pair;$f.Plan.Bootstraps[1].$field=if($field -ceq 'Bytes'){22351169}else{'unexpected'}
        Refuses {Get-T7CatalogueBootstraps $f.Plan}
    }
    $f=New-Pair;$f.Plan.Bootstraps[1].Bytes=22351169;$script:partialItems=[Collections.Generic.List[object]]::new()
    Refuses {Get-T7CatalogueBootstraps $f.Plan|ForEach-Object {$script:partialItems.Add($_)}}
    Check ($script:partialItems.Count -eq 0) 'Invalid collection published its first item before validation finished.'
    foreach($case in 'missing-metadata','missing-binary','wrong-binary-hash','missing-receipt','missing-script','shared-script','shared-receipt','budget-too-small','budget-too-large','extra-binary'){
        $f=New-Pair;$core=$f.Plan.Bootstraps[1]
        switch($case){
            missing-metadata {$f.Plan.InputMetadata=@($f.Plan.InputMetadata|Where-Object Path -CNE $core.Path)}
            missing-binary {$f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $core.Path)}
            wrong-binary-hash {($f.Plan.Bindings|Where-Object Path -CEQ $core.Path).SHA256='0'*64}
            missing-receipt {$f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $core.QualificationReceipt.Path)}
            missing-script {$f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $core.QualificationScript.Path)}
            shared-script {$core.QualificationScript=Copy-Value $f.Plan.Bootstraps[0].QualificationScript}
            shared-receipt {$core.QualificationReceipt=Copy-Value $f.Plan.Bootstraps[0].QualificationReceipt}
            budget-too-small {$f.Plan.OutputLimitBytes--}
            budget-too-large {$f.Plan.OutputLimitBytes++}
            extra-binary {$row=Copy-Value $f.Plan.Bindings[-3];$row.Path=Join-Path $root 'guessed.ff';$f.Plan.Bindings+=@($row);$script:provider[$row.Path]=$script:provider[$core.Path]}
        }
        Refuses {Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner'}
    }
    foreach($field in 'SHA256','ScriptSHA256','FileId','GuardedReadBytesPerPass','GuardedReadPasses'){
        $f=New-Pair;$f.CoreReceipt.$field='unexpected'
        Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.CoreReceipt $f.Plan.Bootstraps[1].Path}
    }
    foreach($field in 'LeaseReleased','GuardsClosed','HashReverifiedUnderGuard','MetadataAndIdentityReverifiedUnderGuard'){
        $f=New-Pair;$f.CoreReceipt.$field=$false
        Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.CoreReceipt $f.Plan.Bootstraps[1].Path} 'lifecycle'
    }
    foreach($field in 'CreationUtc','LastWriteUtc'){
        $f=New-Pair;$f.CoreReceipt.MetadataAfter.$field='2026-10-13T00:00:00Z'
        Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.CoreReceipt $f.Plan.Bootstraps[1].Path} 'metadata'
    }
    $f=New-Pair;$script:ids[$f.Plan.Bootstraps[1].Path]='AABBCCDD:0000000000000003'
    Refuses {Assert-T7CatalogueBootstrapIdentity $f.Plan} 'qualified file identity'
    $f=New-Pair;$script:provider[$f.Plan.Bootstraps[1].Path].CreationTimeUtc=[datetime]'2026-10-13T00:00:00Z'
    Refuses {Assert-T7CatalogueBootstrapIdentity $f.Plan} 'creation metadata'
    foreach($count in 1,3,8){
        $f=New-Qualified $count
        Check (@(Get-T7CatalogueBootstraps $f.Plan).Count -eq $count) 'Qualified collection count lost.'
        Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
        for($i=0;$i -lt $count;$i++){Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipts[$i] $f.Plan.Bootstraps[$i].Path;$checks++}
        Assert-T7CatalogueBootstrapIdentity $f.Plan;$checks++
        Assert-T7CatalogueDistinctInputIds $f.Plan @(New-InputIds $f);$checks++
        Check ($f.Plan.Bindings.Count -eq 22+3*$count) 'Qualified exact binding count differs.'
    }
    foreach($policy in 'QualifiedCollectionV1','QualifiedCollectionV2','QualifiedCollectionV3'){
        $f=New-Qualified 2 $policy;$oldZonePath=$f.Plan.Zone.Path
        $f.Plan.Zone.Path=Join-Path $root 'zm_common.ff';$f.Plan.Zone.Bytes=36332480
        $f.Plan.Zone.RelativePath='zone/zm_common.ff';$f.Plan.InputMetadata[3]=$f.Plan.Zone
        $script:provider[$f.Plan.Zone.Path]=Copy-Value $script:provider[$oldZonePath]
        $script:provider[$f.Plan.Zone.Path].Length=36332480
        $f.Plan.Arguments[1]='zm_common'
        $f.Plan.OutputKey='t7_iw7_catalog_74d24f210d6f255a1e1f63a978bc4cc643496107d00de87211ef84e565de1a88'
        $f.Plan.OutputLimitBytes+=19355136
        Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
        $f.Plan.OutputLimitBytes+=64MB-$f.Plan.CandidateBytes
        $f.Plan.CandidateBytes=64MB;$f.Plan.Bindings[0].Bytes=64MB;$f.Plan.InputMetadata[0].Bytes=64MB
        $script:provider[$f.Plan.CandidateSource].Length=64MB
        $expected=switch($policy){
            'QualifiedCollectionV1' {Set-QualifiedBytes $f 0 16MB;Set-QualifiedBytes $f 1 16MB;226077592L}
            'QualifiedCollectionV2' {Set-QualifiedBytes $f 0 64MB;Set-QualifiedBytes $f 1 64MB;326740888L}
            'QualifiedCollectionV3' {Set-QualifiedBytes $f 0 512MB;Set-QualifiedBytes $f 1 256MB;997829528L}
        }
        Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
        Check ($f.Plan.OutputLimitBytes -eq $expected) 'Selected Zombies zone policy ceiling differs.'
        $f.Plan.Bootstraps[0].Path=$f.Plan.Zone.Path;$f.Plan.Bootstraps[0].RelativePath=$f.Plan.Zone.RelativePath
        Refuses {Get-T7CatalogueBootstraps $f.Plan} 'Unsafe or noncanonical'
    }
    foreach($case in 'zero','nine','null','scalar','unknown-policy','null-policy','no-array','single','mixed','non-msg'){
        $f=New-Qualified
        switch($case){
            zero {$f.Plan.Bootstraps=@()}
            nine {$f=New-Qualified 9}
            null {$f.Plan.Bootstraps=$null}
            scalar {$f.Plan.Bootstraps=$f.Plan.Bootstraps[0]}
            unknown-policy {$f.Plan.BootstrapPolicy='Guessed'}
            null-policy {$f.Plan.BootstrapPolicy=$null}
            no-array {$f.Plan.PSObject.Properties.Remove('Bootstraps')}
            single {$b=$f.Plan.Bootstraps[0];$f.Plan.PSObject.Properties.Remove('Bootstraps');$f.Plan|Add-Member NoteProperty Bootstrap $b}
            mixed {$f.Plan|Add-Member NoteProperty Bootstrap $f.Plan.Bootstraps[0]}
            non-msg {$f.Plan.CandidateProfile='t7-catalog-callers'}
        }
        Refuses {Get-T7CatalogueBootstraps $f.Plan}
    }
    foreach($name in 'con.ff','nul.ff','aux.ff','prn.ff','com1.ff','lpt9.ff','UPPER.ff','with space.ff','two.dots.ff','trailing.ff.','bad:ads.ff','../outside.ff','mp_freerun_04.ff',(('a'*64)+'.ff')){
        $f=New-Qualified;$f.Plan.Bootstraps[-1].Path=Join-Path $root $name;$f.Plan.Bootstraps[-1].RelativePath='zone/'+$name
        Refuses {Get-T7CatalogueBootstraps $f.Plan}
    }
    foreach($value in @(-1,0,1.5,'1000',$null,$true,33554433,[long]::MaxValue)){
        $f=New-Qualified;$f.Plan.Bootstraps[-1].Bytes=$value
        Refuses {Get-T7CatalogueBootstraps $f.Plan} 'bytes'
    }
    $f=New-Qualified 1;Set-QualifiedBytes $f 0 32MB;Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
    $f=New-Qualified 8;Set-QualifiedBytes $f 7 (32MB-7000);Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
    $f.Plan.Bootstraps[7].Bytes++;Refuses {Get-T7CatalogueBootstraps $f.Plan} 'aggregate'
    foreach($count in 1,3,8){
        $f=New-Qualified $count 'QualifiedCollectionV2'
        Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
        Assert-T7CatalogueDistinctInputIds $f.Plan @(New-InputIds $f);$checks++
        Check (@(Get-T7CatalogueBootstraps $f.Plan).Count -eq $count) 'V2 item count differs.'
    }
    $f=New-Qualified 4 'QualifiedCollectionV2';$sizes=@(832,22351168,624640,45217664)
    for($i=0;$i -lt 4;$i++){Set-QualifiedBytes $f $i $sizes[$i]}
    Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
    for($i=0;$i -lt 4;$i++){Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipts[$i] $f.Plan.Bootstraps[$i].Path;$checks++}
    Check ($f.Plan.OutputLimitBytes -eq 196003736) 'Four-file V2 exact budget differs.'
    $f.Plan.BootstrapPolicy='QualifiedCollectionV1';Refuses {Get-T7CatalogueBootstraps $f.Plan} 'bytes'
    $f=New-Qualified 8 'QualifiedCollectionV2';Set-QualifiedBytes $f 0 64MB;Set-QualifiedBytes $f 1 (64MB-6000)
    Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
    Check ($f.Plan.OutputLimitBytes -eq 262027160) 'Exact V2 aggregate ceiling differs.'
    $f.Plan.Bootstraps[-1].Bytes++;$script:partialItems=[Collections.Generic.List[object]]::new()
    Refuses {Get-T7CatalogueBootstraps $f.Plan|ForEach-Object {$script:partialItems.Add($_)}} 'aggregate'
    Check ($script:partialItems.Count -eq 0) 'Late V2 aggregate excess leaked a partial item.'
    $f=New-Qualified 1 'QualifiedCollectionV2';Set-QualifiedBytes $f 0 64MB
    Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
    $f.Plan.Bootstraps[0].Bytes++;Refuses {Get-T7CatalogueBootstraps $f.Plan} 'bytes'
    $f=New-Qualified 2 'QualifiedCollectionV2';Set-QualifiedBytes $f 0 64MB;Set-QualifiedBytes $f 1 64MB
    $f.Plan.CandidateBytes=64MB;$f.Plan.Bindings[0].Bytes=64MB;$f.Plan.InputMetadata[0].Bytes=64MB
    $script:provider[$f.Plan.CandidateSource].Length=64MB;$f.Plan.OutputLimitBytes=307385752L
    Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
    $f.Plan.OutputLimitBytes++;Refuses {Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner'} 'budget|Fixed catalogue'
    foreach($count in 1,8,32){
        $f=New-Qualified $count 'QualifiedCollectionV3'
        Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
        Check (@(Get-T7CatalogueBootstraps $f.Plan).Count -eq $count) 'V3 explicit item count differs.'
        Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipts[-1] $f.Plan.Bootstraps[-1].Path;$checks++
        Assert-T7CatalogueDistinctInputIds $f.Plan @(New-InputIds $f);$checks++
        Check ($f.Plan.Bindings.Count -eq 22+3*$count) 'V3 exact binding count differs.'
    }
    foreach($count in 0,33){
        $f=New-Qualified $count 'QualifiedCollectionV3'
        Refuses {Get-T7CatalogueBootstraps $f.Plan} 'one through 32'
    }
    # Causal regression: the G3 candidate must reach the SAME qualified inventory
    # validator without being reclassified as a historical MSG candidate.
    $f=New-Qualified 23 'QualifiedCollectionV3'
    $f.Plan.CandidateProfile='t7-material-parts-v1'
    Check (@(Get-T7CatalogueBootstraps $f.Plan).Count -eq 23) 'G3 profile rejected by qualified inventory gate.'
    $f.Plan.CandidateProfile='ordinary-d2'
    Refuses {Get-T7CatalogueBootstraps $f.Plan} 'explicit supported profile'
    foreach($policy in 'QualifiedCollectionV1','QualifiedCollectionV2'){
        $f=New-Qualified 9 $policy
        Refuses {Get-T7CatalogueBootstraps $f.Plan} 'one through 8'
    }
    $f=New-Qualified 1 'QualifiedCollectionV3';Set-QualifiedBytes $f 0 512MB
    Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
    $f.Plan.Bootstraps[0].Bytes++;Refuses {Get-T7CatalogueBootstraps $f.Plan} 'bytes'
    $f=New-Qualified 32 'QualifiedCollectionV3'
    Set-QualifiedBytes $f 0 512MB;Set-QualifiedBytes $f 31 (256MB-30000)
    Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
    Check ($f.Plan.OutputLimitBytes -eq 933115800L) 'V3 current MSG candidate plus 768 MiB exact ceiling differs.'
    $f.Plan.Bootstraps[-1].Bytes++;$script:partialItems=[Collections.Generic.List[object]]::new()
    Refuses {Get-T7CatalogueBootstraps $f.Plan|ForEach-Object {$script:partialItems.Add($_)}} 'aggregate'
    Check ($script:partialItems.Count -eq 0) 'Late V3 aggregate excess leaked a partial collection.'
    $f=New-Qualified 2 'QualifiedCollectionV3';Set-QualifiedBytes $f 0 512MB;Set-QualifiedBytes $f 1 256MB
    $f.Plan.CandidateBytes=64MB;$f.Plan.Bindings[0].Bytes=64MB;$f.Plan.InputMetadata[0].Bytes=64MB
    $script:provider[$f.Plan.CandidateSource].Length=64MB;$f.Plan.OutputLimitBytes=978474392L
    Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
    Check ($f.Plan.OutputLimitBytes -lt 1GB) 'V3 theoretical output ceiling is not below 1 GiB.'
    foreach($value in @(-1,0,1.5,'978474392',$true,[long]::MaxValue,978474393L)){
        $bad=Copy-Value $f;$bad.Plan.OutputLimitBytes=$value
        Refuses {Assert-T7CataloguePlan $bad.Plan $bad.Repo 'synthetic-runner'} 'budget|Fixed catalogue'
    }
    foreach($value in @(-1,0,1.5,'1000',$null,$true,536870913,[long]::MaxValue)){
        $f=New-Qualified 32 'QualifiedCollectionV3';$f.Plan.Bootstraps[-1].Bytes=$value
        Refuses {Get-T7CatalogueBootstraps $f.Plan} 'bytes'
    }
    foreach($value in @(-1,0,'67108864',67108865,[long]::MaxValue)){
        $f=New-Qualified 1 'QualifiedCollectionV3';$f.Plan.CandidateBytes=$value
        Refuses {Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner'} 'candidate'
    }
    foreach($case in 'name','id','receipt','script','alias','base-path'){
        $f=New-Qualified 32 'QualifiedCollectionV3';$b=$f.Plan.Bootstraps[-1]
        switch($case){
            name {$b.Path=$f.Plan.Bootstraps[0].Path;$b.RelativePath=$f.Plan.Bootstraps[0].RelativePath}
            id {$b.FileId=$f.Plan.Bootstraps[0].FileId}
            receipt {$b.QualificationReceipt=Copy-Value $f.Plan.Bootstraps[0].QualificationReceipt}
            script {$b.QualificationScript=Copy-Value $f.Plan.Bootstraps[0].QualificationScript}
            alias {$b.RelativePath='zone/../invented_31.ff'}
            base-path {$b.QualificationScript.Path=$f.Plan.EngineSource}
        }
        $script:partialItems=[Collections.Generic.List[object]]::new()
        Refuses {Get-T7CatalogueBootstraps $f.Plan|ForEach-Object {$script:partialItems.Add($_)}}
        Check ($script:partialItems.Count -eq 0) 'Invalid 32nd V3 item published earlier items.'
    }
    $f=New-Qualified 1 'QualifiedCollectionV3'
    $f.Plan.Bindings[3].Bytes=64MB+1;$script:provider[$f.Plan.JobAssembly].Length=64MB+1
    Refuses {Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner'} 'Bound pin metadata'
    foreach($case in 'name-path','identity','receipt','script','text-source','text-base','run-root','foreign-parent','alias-case','alias-traversal','hash','provenance','text-size','extra-field'){
        $f=New-Qualified;$b=$f.Plan.Bootstraps[-1]
        switch($case){
            name-path {$b.Path=$f.Plan.Bootstraps[0].Path;$b.RelativePath=$f.Plan.Bootstraps[0].RelativePath}
            identity {$b.FileId=$f.Plan.Bootstraps[0].FileId}
            receipt {$b.QualificationReceipt=Copy-Value $f.Plan.Bootstraps[0].QualificationReceipt}
            script {$b.QualificationScript=Copy-Value $f.Plan.Bootstraps[0].QualificationScript}
            text-source {$b.QualificationScript.Path=$f.Plan.Bootstraps[0].Path}
            text-base {$b.QualificationReceipt.Path=$f.Plan.CandidateSource}
            run-root {$b.QualificationScript.Path=Join-Path $f.Plan.WorkingDirectory 'foreign.ps1'}
            foreign-parent {$b.Path=Join-Path $f.Plan.WorkingDirectory 'invented_2.ff'}
            alias-case {$b.RelativePath='zone/INVENTED_2.ff'}
            alias-traversal {$b.RelativePath='zone/../invented_2.ff'}
            hash {$b.SHA256='G'*64}
            provenance {$b.HashProvenance='Guessed'}
            text-size {$b.QualificationReceipt.Bytes=32769}
            extra-field {$b|Add-Member NoteProperty Guessed $true}
        }
        $script:partialItems=[Collections.Generic.List[object]]::new()
        Refuses {Get-T7CatalogueBootstraps $f.Plan|ForEach-Object {$script:partialItems.Add($_)}}
        Check ($script:partialItems.Count -eq 0) 'Late invalid qualified item leaked a partial collection.'
    }
    foreach($case in 'missing-metadata','missing-binary','wrong-hash','shared-receipt','missing-script','extra-binding','case-binding','budget-small','budget-large','budget-string'){
        $f=New-Qualified;$b=$f.Plan.Bootstraps[-1]
        switch($case){
            missing-metadata {$f.Plan.InputMetadata=@($f.Plan.InputMetadata|Where-Object Path -CNE $b.Path)}
            missing-binary {$f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $b.Path)}
            wrong-hash {($f.Plan.Bindings|Where-Object Path -CEQ $b.Path).SHA256='0'*64}
            shared-receipt {$b.QualificationReceipt=Copy-Value $f.Plan.Bootstraps[0].QualificationReceipt}
            missing-script {$f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $b.QualificationScript.Path)}
            extra-binding {$f.Plan.Bindings+=@(Copy-Value $f.Plan.Bindings[6])}
            case-binding {$f.Plan.Bindings[7].Path=$f.Plan.Bindings[6].Path.ToUpperInvariant()}
            budget-small {$f.Plan.OutputLimitBytes--}
            budget-large {$f.Plan.OutputLimitBytes++}
            budget-string {$f.Plan.OutputLimitBytes=[string]$f.Plan.OutputLimitBytes}
        }
        Refuses {Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner'}
    }
    foreach($field in 'LeaseReleased','GuardsClosed','HashReverifiedUnderGuard','MetadataAndIdentityReverifiedUnderGuard'){
        $f=New-Qualified;$f.Receipts[-1].$field=$false
        Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipts[-1] $f.Plan.Bootstraps[-1].Path} 'lifecycle'
    }
    $f=New-Qualified;$f.Receipts[-1].MetadataAfter.FileId='AABBCCDD:FFFFFFFFFFFFFFFF'
    Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipts[-1] $f.Plan.Bootstraps[-1].Path} 'identity'
    foreach($case in 'donor-hardlink','base-hardlink','duplicate-path','missing','qualified-mismatch','bad-id'){
        $f=New-Qualified;$inputIds=@(New-InputIds $f)
        switch($case){
            donor-hardlink {$inputIds[3].FileId=$inputIds[-1].FileId}
            base-hardlink {$inputIds[0].FileId=$inputIds[-1].FileId}
            duplicate-path {$inputIds[-1].Path=$inputIds[0].Path}
            missing {$inputIds=@($inputIds[0..($inputIds.Count-2)])}
            qualified-mismatch {$inputIds[-1].FileId='AABBCCDD:FFFFFFFFFFFFFFFF'}
            bad-id {$inputIds[-1].FileId='bad'}
        }
        Refuses {Assert-T7CatalogueDistinctInputIds $f.Plan $inputIds}
    }
    # Execute the actual runner's ID assertion and following directory statement.
    # A late collision must stop before even the first alias directory exists.
    $runnerPath=Join-Path $PSScriptRoot 'Run-T7Catalogue.ps1'
    $runnerAst=[Management.Automation.Language.Parser]::ParseFile($runnerPath,[ref]$tokens,[ref]$errors)
    if($errors.Count){throw 'Runner parse failed.'}
    $idCall=@($runnerAst.FindAll({param($n)$n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -ceq 'Assert-T7CatalogueDistinctInputIds'},$true))
    Check ($idCall.Count -eq 1) 'Exactly one runner input-ID admission assertion required.'
    $runner=Get-Content -LiteralPath $runnerPath -Raw
    $start=$runner.IndexOf($idCall[0].Extent.Text);$end=$runner.IndexOf('    $links=', $start)
    $fragment=$runner.Substring($start,$end-$start)
    $f=New-Qualified;$plan=$f.Plan;$state=[pscustomobject]@{InputFileIds=@(New-InputIds $f)}
    $state.InputFileIds[-1].FileId=$state.InputFileIds[0].FileId
    Refuses {. ([scriptblock]::Create($fragment))} 'Distinct'
    Check (!(Test-Path -LiteralPath (Join-Path $plan.WorkingDirectory 'zone'))) 'ID collision created an alias directory.'
    foreach($case in 'donor-hardlink','base-hardlink','missing','qualified-mismatch'){
        $f=New-Qualified 32 'QualifiedCollectionV3';$plan=$f.Plan;$state=[pscustomobject]@{InputFileIds=@(New-InputIds $f)}
        switch($case){
            donor-hardlink {$state.InputFileIds[3].FileId=$state.InputFileIds[-1].FileId}
            base-hardlink {$state.InputFileIds[0].FileId=$state.InputFileIds[-1].FileId}
            missing {$state.InputFileIds=@($state.InputFileIds[0..($state.InputFileIds.Count-2)])}
            qualified-mismatch {$state.InputFileIds[-1].FileId='AABBCCDD:FFFFFFFFFFFFFFFF'}
        }
        Refuses {. ([scriptblock]::Create($fragment))} 'Distinct|Complete|identity'
        Check (!(Test-Path -LiteralPath (Join-Path $plan.WorkingDirectory 'zone'))) 'Late V3 ID failure created an alias directory.'
    }
    Check ($runner.IndexOf('Assert-T7CatalogueBootstrapReceipt') -lt $runner.IndexOf('if(!$Run)') -and $start -lt $runner.IndexOf('New-T7CatalogueAlias $pin')) 'Global qualification/identity validation moved behind aliases.'
    $receiptStart=$runner.IndexOf('    $bootstraps=@(');$receiptEnd=$runner.IndexOf('    $job=', $receiptStart)
    $receiptFragment=$runner.Substring($receiptStart,$receiptEnd-$receiptStart)
    $directoryFragment=$fragment.Substring($fragment.IndexOf('[IO.Directory]'))
    $f=New-Qualified;$plan=$f.Plan;$qualifiedReceipts=@{}
    for($i=0;$i -lt 3;$i++){$qualifiedReceipts[$f.Plan.Bootstraps[$i].QualificationReceipt.Path]=$f.Receipts[$i]}
    $f.Receipts[-1].GuardsClosed=$false
    Refuses {& {
        function Read-H1SmallJson([string]$Path,[int]$Limit){$qualifiedReceipts[$Path]}
        . ([scriptblock]::Create($receiptFragment))
        . ([scriptblock]::Create($directoryFragment))
    }} 'lifecycle'
    Check (!(Test-Path -LiteralPath (Join-Path $plan.WorkingDirectory 'zone'))) 'Late failed qualification created an alias directory.'
    $f=New-Qualified 32 'QualifiedCollectionV3';$plan=$f.Plan;$qualifiedReceipts=@{}
    for($i=0;$i -lt 32;$i++){$qualifiedReceipts[$f.Plan.Bootstraps[$i].QualificationReceipt.Path]=$f.Receipts[$i]}
    $f.Receipts[-1].GuardsClosed=$false
    Refuses {& {
        function Read-H1SmallJson([string]$Path,[int]$Limit){$qualifiedReceipts[$Path]}
        . ([scriptblock]::Create($receiptFragment))
        . ([scriptblock]::Create($directoryFragment))
    }} 'lifecycle'
    Check (!(Test-Path -LiteralPath (Join-Path $plan.WorkingDirectory 'zone'))) 'Failed 32nd V3 receipt created an alias directory.'
    # Execute the actual plan-validation/receipt-read runner fragment. A late
    # size refusal must precede all further pin/receipt reads, not just aliases.
    $planStart=$runner.IndexOf('    Assert-T7CataloguePlan $plan $repo $PSCommandPath')
    $planFragment=$runner.Substring($planStart,$receiptEnd-$planStart)
    $f=New-Qualified 32 'QualifiedCollectionV3';$plan=$f.Plan;$plan.Bootstraps[-1].Bytes=[long]::MaxValue
    $script:afterPlanReads=0
    Refuses {& {
        $repo=$f.Repo
        function Open-H1Pin($Pin){$script:afterPlanReads++;throw 'UnexpectedPinRead'}
        function Read-H1SmallJson([string]$Path,[int]$Limit){$script:afterPlanReads++;throw 'UnexpectedReceiptRead'}
        . ([scriptblock]::Create($planFragment))
    }} 'bytes'
    Check ($script:afterPlanReads -eq 0) 'Invalid V3 sum reached later runner file reads.'

    # Streaming guard/dispatch uses only small authored bytes. No real FF,
    # native ID provider, admission or hardlink is involved in this test.
    $f=New-Qualified 1 'QualifiedCollectionV3';$b=$f.Plan.Bootstraps[0]
    $content=[Text.Encoding]::UTF8.GetBytes('Original V3 streaming-guard test bytes.')
    Set-QualifiedBytes $f 0 $content.Length
    $b.SHA256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($content)).ToLowerInvariant()
    $pin=@($f.Plan.Bindings|Where-Object Path -CEQ $b.Path)[0];$pin.SHA256=$b.SHA256
    [IO.File]::WriteAllBytes($b.Path,$content)
    $baseOpen=${function:Open-H1Pin};$baseBudget=${function:Test-H1Budget};$baseDeadline=${function:Assert-H1Deadline}
    try{
        foreach($policy in 'QualifiedCollectionV1','QualifiedCollectionV2'){
            $f.Plan.BootstrapPolicy=$policy
            Enable-T7CatalogueRuntimeProfile $f.Plan
            Check (${function:Open-H1Pin}.ToString() -ceq $baseOpen.ToString()) 'V1/V2 replaced the shared pin reader.'
            ${function:Test-H1Budget}=$baseBudget;${function:Assert-H1Deadline}=$baseDeadline
        }
        $f.Plan.BootstrapPolicy='QualifiedCollectionV3';Enable-T7CatalogueRuntimeProfile $f.Plan
        $guard=Open-H1Pin $pin
        try{
            Check ($guard.Length -eq $content.Length -and $guard.Position -eq 0) 'V3 streaming guard is not retained/reset.'
            Refuses {[IO.File]::AppendAllText($b.Path,'mutation')} '.'
        }finally{$guard.Dispose()}
        $aliasDir=Join-Path $f.Plan.WorkingDirectory 'zone';[IO.Directory]::CreateDirectory($aliasDir)|Out-Null
        $aliasPath=Join-Path $f.Plan.WorkingDirectory $b.RelativePath
        [IO.File]::WriteAllBytes($aliasPath,$content) # Ordinary synthetic file, not a claimed hardlink.
        $aliasPin=[pscustomobject]@{Path=$aliasPath;Bytes=$b.Bytes;SHA256=$b.SHA256}
        try{
            $guard=Open-H1Pin $aliasPin
            try{Check ($guard.Length -eq $content.Length) 'Exact V3 alias path was not dispatched.'}finally{$guard.Dispose()}
        }finally{Remove-Item -LiteralPath $aliasPath;Remove-Item -LiteralPath $aliasDir}
        foreach($case in 'bytes','hash','text','string-text'){
            $bad=Copy-Value $pin
            switch($case){bytes {$bad.Bytes++};hash {$bad.SHA256='0'*64};text {$bad.IsText=$true};string-text {$bad.IsText='false'}}
            Refuses {Open-H1Pin $bad} 'Exact V3'
        }
        $foreign=[pscustomobject]@{Path=(Join-Path $root 'never-opened.ff');Bytes=64MB+1;SHA256=('0'*64)}
        Refuses {Open-H1Pin $foreign} 'Invalid bounded binding'
        $content[0]=$content[0] -bxor 1;[IO.File]::WriteAllBytes($b.Path,$content)
        Refuses {Open-H1Pin $pin} 'V3 bound input hash/length'
        $guard=[IO.FileStream]::new($b.Path,'Open','Read','None');$guard.Dispose();$checks++
        # An exclusive guard proves the metadata mismatch refuses before open.
        $script:provider[$b.Path].Length++
        $guard=[IO.FileStream]::new($b.Path,'Open','Read','None')
        try{Refuses {Open-H1Pin $pin} 'before open'}finally{$guard.Dispose()}
    }finally{
        ${function:Open-H1Pin}=$baseOpen;${function:Test-H1Budget}=$baseBudget;${function:Assert-H1Deadline}=$baseDeadline
        Remove-Item -LiteralPath $b.Path
    }
    $legacy=New-Pair;Assert-T7CatalogueDistinctInputIds $legacy.Plan $null;$checks++
    $f=New-Pair;$zoneDir=Join-Path $f.Plan.WorkingDirectory 'zone';[IO.Directory]::CreateDirectory($zoneDir)|Out-Null
    foreach($name in 'en_core_pre_gfx.ff','core_pre_gfx.ff'){[IO.File]::WriteAllText((Join-Path $zoneDir $name),'invented text only')}
    Assert-T7CatalogueEngineOutputs $f.Plan;$checks++
    $single=Copy-Value $f.Plan;$single|Add-Member NoteProperty Bootstrap $single.Bootstraps[0];$single.PSObject.Properties.Remove('Bootstraps')
    Refuses {Assert-T7CatalogueEngineOutputs $single} 'Unexpected zone'
    [IO.File]::WriteAllText((Join-Path $zoneDir 'guessed.ff'),'invented')
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'Unexpected zone'
    Check (!('IW7ResourceMemoryV1' -as [type]) -and !('IW7HudFileIdentity' -as [type]) -and !('IW7.AnimationProbe.NativeJob' -as [type])) 'Pure tests loaded native support.'
    [ordered]@{Status='Passed';Checks=$checks;Fixtures='Legacy pair; V1/V2 1..8; V3 1..32, 512/768 MiB metadata only; tiny original streaming guards';OwnerStockRead=$false;RealLeaseAcquired=$false;NativeTypesLoaded=$false;NativeProcessStarted=$false;OperationalPlanCreated=$false}|ConvertTo-Json
}finally{
    $full=[IO.Path]::GetFullPath($root);$temp=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$full.StartsWith($temp,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($full) -cnotmatch '^t7-bootstraps-tests-[0-9a-f]{32}$'){throw 'Unexpected synthetic cleanup root.'}
    Remove-Item -LiteralPath $full -Recurse -Force
}
