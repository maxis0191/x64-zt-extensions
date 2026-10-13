# Invented metadata and dependency JSON only. No real plan, binary, build or Run.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7ResidentExport.Profile.ps1')
foreach($spec in @(@('Test-T7CatalogueTrace.ps1',@('Check','Refuses','Copy-Value','New-Pin','New-Binding','New-Fixture','Read-H1SmallJson')),
    @('Test-T7CataloguePublication.ps1',@('New-PublicationFixture')))){
    $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $spec[0]),[ref]$tokens,[ref]$errors)
    if($errors.Count){throw 'Synthetic fixture parse error.'}
    foreach($name in $spec[1]){
        $nodes=@($ast.FindAll({param($node)$node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true))
        if($nodes.Count -ne 1){throw 'Synthetic fixture helper missing.'}
        . ([scriptblock]::Create($nodes[0].Extent.Text))
    }
}
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-diagnostic-tests-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($root);$script:checks=0
function New-DiagnosticFixture {
    $f=New-PublicationFixture;$p=$f.Plan
    $p|Add-Member NoteProperty Operation 'ResidentExportV1'
    $p.ExpectedBuildPlanSHA256='4bfb8c9aa45352b0e99acc0a66eab8df93eec8bcac15b9443b766e01a8fcb9e6'
    $pin=@($p.Bindings|Where-Object Path -CEQ $p.BuildPlan)[0];$pin.Bytes=303182;$pin.SHA256=$p.ExpectedBuildPlanSHA256
    $p.ExpectedBuildReceiptSHA256='6cc2cab523115defa9ee0df2a9c5292a286236ce96d935fb374145a663510810'
    $pin=@($p.Bindings|Where-Object Path -CEQ $p.BuildReceipt)[0];$pin.Bytes=22393;$pin.SHA256=$p.ExpectedBuildReceiptSHA256
    $f.Receipt.PlanSHA256=$p.ExpectedBuildPlanSHA256
    foreach($stage in $f.Receipt.Stages){$stage.PlanSHA256=$p.ExpectedBuildPlanSHA256}
    $header=[pscustomobject]@{Path=(Join-Path $f.Build.PreparedRoot 't7_iw7_resident_model.hpp');Bytes=13545;SHA256='701e3d1eccb0e98ecccfd2012215aaf7eff8db7bd974b184e86648a138b6e3c3'}
    $p|Add-Member NoteProperty ResidentSurfaceCountDiagnostic ([pscustomobject]@{Schema='iw7.t7-resident-surface-count-diagnostic/1';Header=$header})
    $p.Bindings+=@(New-Binding $header);$f.Build.Bindings+=@(New-Binding $header)
    # The retained synthetic source plan is elsewhere, so old/new header paths differ.
    $oldSource=$f.Build.ReuseCompile.SourcePlan;$newSource=Join-Path $root 'old/compile.json'
    foreach($container in @($f.Build,$f.Base)){
        $container.ReuseCompile.SourcePlan=$newSource
        ($container.Bindings|Where-Object Path -CEQ $oldSource).Path=$newSource
    }
    $old=[pscustomobject]@{Path=(Join-Path $root 'old/prepared/t7_iw7_resident_model.hpp');Bytes=13444;SHA256='6d2da3d4f7c3d0686909dc488f3d176ee2dd250e8d43d9a3cd9bcfa701482777'}
    $f.Build.Bindings+=@(New-Binding $old)
    $dependencies=@(foreach($spec in @(@('helper',16296,'6897d27e8fe0754509e52258082d6178c8cb74fe21a8ef4b006006e97ab9dd12'),
        @('zonetool11',76744,'cfe62be9ce9bf87abd8e6713f1e1f334d76f69472500d2cb260696de26ee8273'),
        @('xpak',64444,'3d742923def4fb049d82853ac0e776ffd071228deaf1da1a624603d10dfd3908'))){
        [pscustomobject]@{Path=(Join-Path $root ($spec[0]+'/dependencies.json'));Bytes=$spec[1];SHA256=$spec[2]}
    })
    foreach($pin in $dependencies){$f.Build.Bindings+=@(New-Binding $pin)}
    $proof=[pscustomobject]@{Header='prepared/t7_iw7_resident_model.hpp';PreviousSHA256=$old.SHA256;SHA256=$header.SHA256;DependencyJSON=$dependencies;
        E7ReadSHA256='d9cdd533796a9fe14e0d5140d8adcbf5cbc932fafd4c06e18a615d15199a2185';
        E7CompileSHA256='a7083ce5b9ba2fe1421c4f8733cf1d1e0b286549dbc55a44f3ef30ceb3c05333';
        E7LinkSHA256='70455d2f32a9b034dda20fbaf48443ee68a02e552381edbf88b19d219f1f66b2';E7TranslationUnits=413;E7Objects=413}
    $f.Build.ReuseCompile|Add-Member NoteProperty ResidentSurfaceCountDiagnostic $proof
    $dep=$f.Receipt.Stages[1].Artifacts[-1].Path
    $script:json[$dep].Data|Add-Member NoteProperty Includes @($header.Path.ToLowerInvariant())
    $script:json[$p.BuildReceipt]=$f.Receipt
    $f
}
try {
    $f=New-DiagnosticFixture;Assert-T7CatalogueBuild $f.Plan $f.Receipt;$checks++
    Check ($f.Plan.CandidateBytes -eq 100) 'Synthetic candidate bytes were replaced by a real tuple.'
    foreach($change in 'missing-contract','missing-proof','wrong-schema','schema-array','wrong-operation','wrong-plan','wrong-plan-size','wrong-receipt','wrong-receipt-size','header-hash','header-size','header-path','header-unbound','old-header'){
        $f=New-DiagnosticFixture
        switch($change){
            missing-contract {$f.Plan.PSObject.Properties.Remove('ResidentSurfaceCountDiagnostic')}
            missing-proof {$f.Build.ReuseCompile.PSObject.Properties.Remove('ResidentSurfaceCountDiagnostic')}
            wrong-schema {$f.Plan.ResidentSurfaceCountDiagnostic.Schema='other'}
            schema-array {$f.Plan.ResidentSurfaceCountDiagnostic.Schema=@($f.Plan.ResidentSurfaceCountDiagnostic.Schema)}
            wrong-operation {$f.Plan.Operation='Catalogue'}
            wrong-plan {$f.Plan.ExpectedBuildPlanSHA256='1'*64;$f.Receipt.PlanSHA256='1'*64;foreach($s in $f.Receipt.Stages){$s.PlanSHA256='1'*64};($f.Plan.Bindings|Where-Object Path -CEQ $f.Plan.BuildPlan).SHA256='1'*64}
            wrong-plan-size {($f.Plan.Bindings|Where-Object Path -CEQ $f.Plan.BuildPlan).Bytes++}
            wrong-receipt {$f.Plan.ExpectedBuildReceiptSHA256='1'*64;($f.Plan.Bindings|Where-Object Path -CEQ $f.Plan.BuildReceipt).SHA256='1'*64}
            wrong-receipt-size {($f.Plan.Bindings|Where-Object Path -CEQ $f.Plan.BuildReceipt).Bytes++}
            header-hash {$f.Plan.ResidentSurfaceCountDiagnostic.Header.SHA256='1'*64}
            header-size {$f.Plan.ResidentSurfaceCountDiagnostic.Header.Bytes++}
            header-path {$old=$f.Plan.ResidentSurfaceCountDiagnostic.Header.Path;$new=Join-Path $root 'redirect/t7_iw7_resident_model.hpp';$f.Plan.ResidentSurfaceCountDiagnostic.Header.Path=$new;foreach($c in @($f.Plan,$f.Build)){($c.Bindings|Where-Object Path -CEQ $old).Path=$new}}
            header-unbound {$f.Build.Bindings=@($f.Build.Bindings|Where-Object Path -CNE $f.Plan.ResidentSurfaceCountDiagnostic.Header.Path)}
            old-header {($f.Build.Bindings|Where-Object {$_.Path -like '*old*resident_model.hpp'}).Bytes++}
        }
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'diagnostic|guarded'
    }
    foreach($field in 'Header','PreviousSHA256','SHA256','E7ReadSHA256','E7CompileSHA256','E7LinkSHA256','E7TranslationUnits','E7Objects'){
        $f=New-DiagnosticFixture;$f.Build.ReuseCompile.ResidentSurfaceCountDiagnostic.$field='changed'
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'diagnostic reuse proof'
    }
    foreach($change in 'missing','duplicate','wrong-hash','redirect'){
        $f=New-DiagnosticFixture;$proof=$f.Build.ReuseCompile.ResidentSurfaceCountDiagnostic
        switch($change){missing{$proof.DependencyJSON=$proof.DependencyJSON[0..1]} duplicate{$proof.DependencyJSON[1]=$proof.DependencyJSON[0]} wrong-hash{$proof.DependencyJSON[0].SHA256='1'*64} redirect{$proof.DependencyJSON[0].Path=Join-Path $root 'redirect/dependencies.json'}}
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'diagnostic reuse|guarded'
    }
    foreach($change in 'missing','duplicate','old','other','relative','traversal','source','unbound'){
        $f=New-DiagnosticFixture;$path=$f.Receipt.Stages[1].Artifacts[-1].Path;$doc=$script:json[$path]
        switch($change){
            missing {$doc.Data.Includes=@()}
            duplicate {$doc.Data.Includes+=@($doc.Data.Includes[0])}
            old {$doc.Data.Includes=@(Join-Path $root 'old/prepared/t7_iw7_resident_model.hpp')}
            other {$doc.Data.Includes=@(Join-Path $root 'other.hpp')}
            relative {$doc.Data.Includes=@('t7_iw7_resident_model.hpp')}
            traversal {$doc.Data.Includes=@(Join-Path $f.Build.PreparedRoot '../prepared/t7_iw7_resident_model.hpp')}
            source {$doc.Data.Source=Join-Path $root 'old.cpp'}
            unbound {$f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $path)}
        }
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'includes|required|header once|different TU|guarded'
    }
    foreach($field in 'CandidateExecuted','Quarantined','LeaseReleased','TreeClosureConfirmed','InputsReverified','Status'){
        $f=New-DiagnosticFixture;$f.Receipt.$field=if($field -cin @('CandidateExecuted','Quarantined')){$true}elseif($field -ceq 'Status'){'Failed'}else{$false}
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Closed successful'
    }
    foreach($field in 'CandidateSource','CandidateBytes','CandidateSHA256'){
        $f=New-DiagnosticFixture;$f.Plan.$field=if($field -ceq 'CandidateBytes'){101}elseif($field -ceq 'CandidateSource'){Join-Path $root 'other.exe'}else{'1'*64}
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'candidate|Candidate'
    }
    $f=New-DiagnosticFixture;$f.Receipt.Stages[2].Artifacts+=@($f.Receipt.Stages[2].Artifacts[0])
    Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'artifact guards'

    # Catalogue comparison: exactly the candidate row may change, with 26 stock rows retained.
    $f=New-DiagnosticFixture;$p=$f.Plan
    $request=[pscustomobject]@{schema='iw7.t7-iw7-resident-model-request/1';target='iw7';profile='resident-rigid-one-lod';zone='mp_freerun_04';model='p7_fre_platform_cap_02';lod=0}
    $source=[pscustomobject]@{Schema='iw7.t7-catalogue-plan/1';CandidateSource=(Join-Path $root 'old.exe');CandidateBytes=99;CandidateSHA256=('2'*64);
        EngineSource='synthetic-engine';SteamSource='synthetic-steam';Zone='synthetic-zone';Bootstraps=@('synthetic');SharedQualification='synthetic';InputMetadata=@()}
    $source.InputMetadata=@([pscustomobject]@{Path=$source.CandidateSource;Bytes=99;Attributes='Archive';LastWriteUtc='2026-10-01T00:00:00Z'})
    $source.InputMetadata+=@(1..26|ForEach-Object {[pscustomobject]@{Path=('synthetic-stock-'+$_);Bytes=$_;Attributes='Archive';LastWriteUtc='2026-10-01T00:00:00Z'}})
    foreach($field in 'EngineSource','SteamSource','Zone','Bootstraps','SharedQualification','InputMetadata'){$p|Add-Member NoteProperty $field (Copy-Value $source.$field)}
    $p.InputMetadata[0].Path=$p.CandidateSource;$p.InputMetadata[0].Bytes=$p.CandidateBytes
    $p|Add-Member NoteProperty ExportRequest $request
    foreach($field in 'SourceCataloguePlan','SourceCatalogueReceipt','SourceCatalogue','ExportRequestFile'){$p|Add-Member NoteProperty $field (New-Pin (Join-Path $root ($field+'.json')))}
    $catalogue=[pscustomobject]@{schema='iw7.t7-iw7-model-catalog/1';requested_zone='mp_freerun_04';provenance='observed_during_requested_zone_load';model_count=1;name_bytes=($request.model.Length+1);
        models=@([pscustomobject]@{name=$request.model;reference=$false;resolved_nondefault=$true;counts=[pscustomobject]@{bones=1;roots=1;cosmetic_bones=0;lods=1}});
        truncated=$false;asset_zone_ownership_verified=$false;zonetool_xpak_helper_reads_allowed=$false;engine_io_verified=$false;geometry_verified=$false;runtime_verified=$false;ready=$false}
    $r=[pscustomobject]@{Schema='iw7.t7-catalogue-run/1';PlanSHA256=$p.SourceCataloguePlan.SHA256;Status='CatalogueObservedPendingDonorReview';ExitCode=0;CatalogueOutcome='CatalogueWithNames';Quarantined=$false;
        TreeClosureConfirmed=$true;LeaseReleased=$true;InputsReverified=$true;EngineOutputsValidated=$true;OriginalInputMetadataUnchanged=$true;AliasesRetained=$true;Report=$p.SourceCatalogue}
    $script:json[$p.SourceCataloguePlan.Path]=$source;$script:json[$p.SourceCatalogueReceipt.Path]=$r
    $script:json[$p.SourceCatalogue.Path]=$catalogue;$script:json[$p.ExportRequestFile.Path]=$request
    Assert-T7ResidentExportCatalogue $p;$checks++
    $v2=Copy-Value $p;$v2.PSObject.Properties.Remove('ResidentSurfaceCountDiagnostic')
    $v2|Add-Member NoteProperty ResidentMultiSurfaceV2 ([pscustomobject]@{Schema='iw7.t7-resident-multi-surface/2'})
    Assert-T7ResidentExportCatalogue $v2;$checks++
    foreach($i in 1..26){$bad=Copy-Value $v2;$bad.InputMetadata[$i].Bytes++;Refuses {Assert-T7ResidentExportCatalogue $bad} 'noncandidate InputMetadata'}
    foreach($field in 'EngineSource','SteamSource','Zone','Bootstraps','SharedQualification'){
        $bad=Copy-Value $v2;$bad.$field='changed';Refuses {Assert-T7ResidentExportCatalogue $bad} 'source inputs changed'
    }
    $bad=Copy-Value $p;$bad.PSObject.Properties.Remove('ResidentSurfaceCountDiagnostic')
    Refuses {Assert-T7ResidentExportCatalogue $bad} 'source inputs changed'
    foreach($field in 'EngineSource','SteamSource','Zone','Bootstraps','SharedQualification'){
        $bad=Copy-Value $p;$bad.$field='changed';Refuses {Assert-T7ResidentExportCatalogue $bad} 'source inputs changed'
    }
    foreach($i in 1..26){$bad=Copy-Value $p;$bad.InputMetadata[$i].Bytes++;Refuses {Assert-T7ResidentExportCatalogue $bad} 'noncandidate InputMetadata'}
    foreach($change in 'missing','duplicate','swap','wrong-path','wrong-bytes','extra-field'){
        $bad=Copy-Value $p
        switch($change){missing{$bad.InputMetadata=$bad.InputMetadata[1..26]} duplicate{$bad.InputMetadata[1]=$bad.InputMetadata[0]} swap{$bad.InputMetadata[0],$bad.InputMetadata[1]=$bad.InputMetadata[1],$bad.InputMetadata[0]} wrong-path{$bad.InputMetadata[0].Path='other'} wrong-bytes{$bad.InputMetadata[0].Bytes++} extra-field{$bad.InputMetadata[0]|Add-Member NoteProperty extra 0}}
        Refuses {Assert-T7ResidentExportCatalogue $bad} 'metadata|catalogue fields'
    }
    [ordered]@{Status='Passed';Checks=$checks;Fixtures='Invented JSON and receipt tuples; source gates only';RealBuildQualified=$false;BinaryRead=$false;OperationalPlanCreated=$false;NativeRun=$false}|ConvertTo-Json
}finally{
    $full=[IO.Path]::GetFullPath($root);$temp=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$full.StartsWith($temp,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($full) -cnotmatch '^t7-diagnostic-tests-[0-9a-f]{32}$'){throw 'Refuse cleanup outside synthetic diagnostic root.'}
    Remove-Item -LiteralPath $full -Recurse -Force
}
