# Two explicit invented dependencies. Reuse existing single-item fixture helpers.
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
    $f=New-Pair;$zoneDir=Join-Path $f.Plan.WorkingDirectory 'zone';[IO.Directory]::CreateDirectory($zoneDir)|Out-Null
    foreach($name in 'en_core_pre_gfx.ff','core_pre_gfx.ff'){[IO.File]::WriteAllText((Join-Path $zoneDir $name),'invented text only')}
    Assert-T7CatalogueEngineOutputs $f.Plan;$checks++
    $single=Copy-Value $f.Plan;$single|Add-Member NoteProperty Bootstrap $single.Bootstraps[0];$single.PSObject.Properties.Remove('Bootstraps')
    Refuses {Assert-T7CatalogueEngineOutputs $single} 'Unexpected zone'
    [IO.File]::WriteAllText((Join-Path $zoneDir 'guessed.ff'),'invented')
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'Unexpected zone'
    Check (!('IW7ResourceMemoryV1' -as [type]) -and !('IW7HudFileIdentity' -as [type]) -and !('IW7.AnimationProbe.NativeJob' -as [type])) 'Pure tests loaded native support.'
    [ordered]@{Status='Passed';Checks=$checks;Fixtures='Two invented qualified bootstrap records';OwnerStockRead=$false;RealLeaseAcquired=$false;NativeTypesLoaded=$false;NativeProcessStarted=$false;OperationalPlanCreated=$false}|ConvertTo-Json
}finally{
    $full=[IO.Path]::GetFullPath($root);$temp=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$full.StartsWith($temp,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($full) -cnotmatch '^t7-bootstraps-tests-[0-9a-f]{32}$'){throw 'Unexpected synthetic cleanup root.'}
    Remove-Item -LiteralPath $full -Recurse -Force
}
