# Synthetic files and injected process observations only. Never open owner stock.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Prepatch.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7ResidentExport.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern){
    $caught=$false;try{$null=& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected refusal: '+$_.Exception.Message)}
    Check $caught ('Expected refusal: '+$Pattern)
}
function Copy-Value($Value){$Value|ConvertTo-Json -Depth 20|ConvertFrom-Json}
function Pin([string]$Path){[pscustomobject]@{Path=$Path;Bytes=(Get-Item -LiteralPath $Path).Length;SHA256=(Get-FileHash -LiteralPath $Path).Hash.ToLowerInvariant();IsText=$true}}
function Save-Json($Path,$Value){[IO.File]::WriteAllText($Path,($Value|ConvertTo-Json -Depth 20))}
function Close-Guards {foreach($guard in $context.Guards){$guard.Dispose()};$context.Guards.Clear()}
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-export-tests-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($root)
$context=[pscustomobject]@{Closed=$true;Lease=[pscustomobject]@{Token='synthetic'};Guards=[Collections.Generic.List[object]]::new()}
try {
    $request=[pscustomobject]@{schema='iw7.t7-iw7-resident-model-request/1';target='iw7';profile='resident-rigid-one-lod';zone='mp_freerun_04';model='p7_fre_platform_cap_02';lod=0}
    Assert-T7ResidentExportRequest $request;$script:checks++
    $key=Get-T7ResidentExportKey $request
    Check ($key -ceq 't7_iw7_166d063bd97fb350636ad62a25f44b2d0492f33d4c7c626f23682ac2d9eae40b') 'Native/Python request key differs.'
    foreach($pair in @(@('model','nt_2020_vista_flagpole_01'),@('zone','mp_other'),@('target','h1'),@('profile','animated'),@('lod',1),@('lod',$false),@('lod','0'))){
        $r=Copy-Value $request;$r.($pair[0])=$pair[1];Refuses {Assert-T7ResidentExportRequest $r} 'Only the observed'
    }
    $r=Copy-Value $request;$r|Add-Member NoteProperty extra 0;Refuses {Assert-T7ResidentExportRequest $r} 'Exact catalogue fields'
    $r=Copy-Value $request;$r.model=@($r.model);Refuses {Assert-T7ResidentExportRequest $r} 'scalar string'
    foreach($name in @('../bad','/bad','a//b','C:bad','a\..\b','CON','aux.txt','Lpt9.x','COM0','x.','x ','bad|name',',reference',('x'*256),"x`ny")){
        Refuses {Assert-T7ResidentExportName $name} 'Unsafe export'
    }
    foreach($name in @('mesh_01','models/mesh','models\mesh','nested/name.with.dots')){Assert-T7ResidentExportName $name;$script:checks++}
    Check ((Get-T7CatalogueOperation ([pscustomobject]@{})) -ceq 'Catalogue') 'Legacy operation changed.'
    Refuses {Get-T7CatalogueOperation ([pscustomobject]@{Operation='dumpzone'})} 'Unknown T7'
    Refuses {Get-T7CatalogueOperation ([pscustomobject]@{Operation=@('ResidentExportV1')})} 'Unknown T7'
    $plan=[pscustomobject]@{Operation='ResidentExportV1';ExportRequest=$request;OutputKey=$key;RunRoot=$root;WorkingDirectory=(Join-Path $root 'work');Image=(Join-Path $root 'work/t7-zonetool-candidate.exe')}
    $start=New-T7CatalogueStart $plan
    Check (($start.ArgumentList -join '|') -ceq '-t7-iw7-model|mp_freerun_04|p7_fre_platform_cap_02|0') 'Export command differs.'
    foreach($kind in @('plan','run','attempt','host','host-closure','host-incident-preflight','host-incident-closure')){
        Check ((Get-T7CatalogueHostSchema $plan $kind) -ceq ('iw7.t7-resident-export-'+$kind+'/1')) 'Export host schema differs.'
        Check ((Get-T7CatalogueHostSchema ([pscustomobject]@{}) $kind) -ceq ('iw7.t7-catalogue-'+$kind+'/1')) 'Legacy host schema changed.'
    }
    Check ((Get-T7CatalogueHostOutcomeName $plan) -ceq 'ExportOutcome') 'Export mislabeled as catalogue.'
    Refuses {Assert-T7CatalogueHostReceipt ([pscustomobject]@{Plan=$plan;PlanSHA256=('a'*64)}) ([pscustomobject]@{Schema='iw7.t7-catalogue-run/1';PlanSHA256=('a'*64)})} 'another plan'

    $output=Join-Path (Join-Path $plan.WorkingDirectory 'dump') $key
    foreach($dir in 'xmodel','xsurface/nested'){$null=[IO.Directory]::CreateDirectory((Join-Path $output $dir))}
    $modelPath=Join-Path $output 'xmodel/p7_fre_platform_cap_02.xmb';$meshPath=Join-Path $output 'xsurface/nested/mesh.xsb'
    $manifestPath=Join-Path $output 'manifest.json'
    [IO.File]::WriteAllText($modelPath,'synthetic-model');[IO.File]::WriteAllText($meshPath,'synthetic-mesh')
    $manifest=[pscustomobject]@{schema='iw7.t7-iw7-resident-export/1';requested_zone=$request.zone;source_model=$request.model;selected_source_lod=0;
        output_model_name=$request.model;output_mesh_name='nested/mesh';output_root_key=$key;target='iw7';profile=$request.profile;
        geometry_profile='t7-iw7-resident-static-v1';root_bone_name='tag_origin';selected_counts=[pscustomobject]@{bones=1;roots=1;surfaces=1;vertices=3;triangles=1};
        material_dependencies=@('unresolved_material');model=[pscustomobject]@{relative_path='xmodel/p7_fre_platform_cap_02.xmb';bytes=(Pin $modelPath).Bytes;sha256=(Pin $modelPath).SHA256};
        mesh=[pscustomobject]@{relative_path='xsurface/nested/mesh.xsb';bytes=(Pin $meshPath).Bytes;sha256=(Pin $meshPath).SHA256};
        zonetool_xpak_helper_reads_allowed=$false;engine_io_verified=$false;dependency_payloads_verified=$false;asset_zone_ownership_verified=$false;
        serialized_parse_verified=$false;runtime_verified=$false;ready=$false}
    Assert-T7ResidentExportManifest $manifest $plan;$script:checks++
    $m=Copy-Value $manifest;$m.source_model=@($m.source_model);Refuses {Assert-T7ResidentExportManifest $m $plan} 'scalar string'
    foreach($flag in @('zonetool_xpak_helper_reads_allowed','engine_io_verified','dependency_payloads_verified','asset_zone_ownership_verified','serialized_parse_verified','runtime_verified','ready')){
        $m=Copy-Value $manifest;$m.$flag=$true;Refuses {Assert-T7ResidentExportManifest $m $plan} 'overclaims'
    }
    foreach($pair in @(@('bones',2),@('roots',0),@('surfaces',2),@('vertices',2),@('vertices',65536),@('triangles',0),@('triangles',1.5))){
        $m=Copy-Value $manifest;$m.selected_counts.($pair[0])=$pair[1];Refuses {Assert-T7ResidentExportManifest $m $plan} 'geometry count'
    }
    foreach($pair in @(@('source_model','other'),@('output_model_name','renamed'),@('selected_source_lod',1),@('output_root_key','wrong'))){
        $m=Copy-Value $manifest;$m.($pair[0])=$pair[1];Refuses {Assert-T7ResidentExportManifest $m $plan} 'request or profile'
    }
    $m=Copy-Value $manifest;$m.mesh.relative_path='xsurface/../outside.xsb';Refuses {Assert-T7ResidentExportManifest $m $plan} 'artifact path'
    $m=Copy-Value $manifest;$m.material_dependencies+=@('second');Refuses {Assert-T7ResidentExportManifest $m $plan} 'one unresolved'
    $m=Copy-Value $manifest;$m.model.bytes=1MB+1;Refuses {Assert-T7ResidentExportManifest $m $plan} 'artifact path'
    $m=Copy-Value $manifest;$m.mesh.bytes=16MB+1;Refuses {Assert-T7ResidentExportManifest $m $plan} 'artifact path'
    $m=Copy-Value $manifest;$m.mesh.sha256='bad';Refuses {Assert-T7ResidentExportManifest $m $plan} 'artifact path'
    Save-Json $manifestPath $manifest
    Assert-T7CatalogueEngineOutputs $plan;$script:checks++
    $legacy=Copy-Value $plan;$legacy.Operation='Catalogue'
    Refuses {Assert-T7CatalogueEngineOutputs $legacy} 'Unexpected engine output'
    $state=[ordered]@{ExitCode=0;ExportOutcome='NoExport'}
    Check ((Read-T7ResidentExportReport $plan $state $context) -ceq 'ExportFilesObserved') 'Bounded export refused.'
    Check ($context.Guards.Count -eq 3 -and !$state.SerializedParseVerified -and !$state.DependencyPayloadsVerified) 'Guarded bytes became readback or dependency acceptance.'
    foreach($path in @($manifestPath,$modelPath,$meshPath)){Refuses {[IO.File]::AppendAllText($path,'x')} '.'}
    Close-Guards
    $state.ExitCode=1
    Check ((Read-T7ResidentExportReport $plan $state $context) -ceq 'ValidExportFromFailedProcess') 'Nonzero exit became success.'
    Close-Guards;$state.ExitCode=0
    $context.Closed=$false;Refuses {Read-T7ResidentExportReport $plan $state $context} 'closed with admission'
    $context.Closed=$true;$context.Lease=$null;Refuses {Read-T7ResidentExportReport $plan $state $context} 'closed with admission'
    $context.Lease=[pscustomobject]@{Token='synthetic'}
    [IO.File]::WriteAllText($meshPath,'corrupted-mesh')
    Refuses {Read-T7ResidentExportReport $plan $state $context} 'hash/length';Close-Guards
    [IO.File]::WriteAllText($meshPath,'synthetic-mesh')
    [IO.File]::WriteAllText($manifestPath,'{');Refuses {Read-T7ResidentExportReport $plan $state $context} '.';Close-Guards
    Save-Json $manifestPath $manifest
    foreach($relative in @('xsurface/second.xsb','texture.iwi','xmodel/wrong.xmb')){
        $path=Join-Path $output $relative;[IO.File]::WriteAllText($path,'unexpected')
        Refuses {Get-T7ResidentExportFiles $plan} 'Only one|Unexpected export';Remove-Item -LiteralPath $path
    }
    $empty=Join-Path $output 'xsurface/unreferenced';$null=[IO.Directory]::CreateDirectory($empty)
    Refuses {Read-T7ResidentExportReport $plan $state $context} 'Unreferenced';Close-Guards;Remove-Item -LiteralPath $empty
    $other=Join-Path (Join-Path $plan.WorkingDirectory 'dump') 'other';$null=[IO.Directory]::CreateDirectory($other)
    Refuses {Get-T7ResidentExportFiles $plan} 'Unexpected export root';Remove-Item -LiteralPath $other
    $unexpected=Join-Path $plan.WorkingDirectory $key;$null=[IO.Directory]::CreateDirectory($unexpected)
    Refuses {Assert-T7CatalogueEngineOutputs $plan} 'Unexpected engine output';Remove-Item -LiteralPath $unexpected
    $link=Join-Path $output 'xsurface/junction';$null=New-Item -ItemType Junction -Path $link -Target $root
    Refuses {Get-T7ResidentExportFiles $plan} 'Reparse';Remove-Item -LiteralPath $link
    $stream=[IO.FileStream]::new($meshPath,'Open','Write','Read');try{$stream.SetLength(16MB+1)}finally{$stream.Dispose()}
    Refuses {Get-T7ResidentExportFiles $plan} 'byte cap';[IO.File]::WriteAllText($meshPath,'synthetic-mesh')
    Remove-Item -LiteralPath $manifestPath
    Check ((Read-T7ResidentExportReport $plan $state $context) -ceq 'NoExport') 'Missing manifest accepted.'

    # Source catalogue provenance and unchanged input membership, using bounded invented JSON.
    $source=[pscustomobject]@{Schema='iw7.t7-catalogue-plan/1';CandidateSource='candidate';CandidateBytes=1;CandidateSHA256=('a'*64);
        EngineSource='engine';SteamSource='steam';Zone=[pscustomobject]@{Path='donor';Bytes=1};Bootstraps=@('a','b');SharedQualification='qualified';InputMetadata=@('a','b')}
    $catalogue=[pscustomobject]@{schema='iw7.t7-iw7-model-catalog/1';requested_zone='mp_freerun_04';provenance='observed_during_requested_zone_load';model_count=1;
        name_bytes=$request.model.Length+1;models=@([pscustomobject]@{name=$request.model;reference=$false;resolved_nondefault=$true;counts=[pscustomobject]@{bones=1;roots=1;cosmetic_bones=0;lods=1}});
        truncated=$false;asset_zone_ownership_verified=$false;zonetool_xpak_helper_reads_allowed=$false;engine_io_verified=$false;geometry_verified=$false;runtime_verified=$false;ready=$false}
    $basePath=Join-Path $root 'base.json';$receiptPath=Join-Path $root 'receipt.json';$cataloguePath=Join-Path $root 'catalogue.json';$requestPath=Join-Path $root 'request.json'
    Save-Json $basePath $source;Save-Json $cataloguePath $catalogue;Save-Json $requestPath $request
    $evidence=Copy-Value $source;$evidence|Add-Member NoteProperty ExportRequest $request
    foreach($pair in @(@('SourceCataloguePlan',$basePath),@('SourceCatalogueReceipt',$receiptPath),@('SourceCatalogue',$cataloguePath),@('ExportRequestFile',$requestPath))){
        if(!(Test-Path -LiteralPath $pair[1])){[IO.File]::WriteAllText($pair[1],'{}')};$evidence|Add-Member NoteProperty $pair[0] (Pin $pair[1])
    }
    $receipt=[pscustomobject]@{Schema='iw7.t7-catalogue-run/1';PlanSHA256=$evidence.SourceCataloguePlan.SHA256;Status='CatalogueObservedPendingDonorReview';ExitCode=0;CatalogueOutcome='CatalogueWithNames';Quarantined=$false;
        TreeClosureConfirmed=$true;LeaseReleased=$true;InputsReverified=$true;EngineOutputsValidated=$true;OriginalInputMetadataUnchanged=$true;AliasesRetained=$true;Report=$evidence.SourceCatalogue}
    Save-Json $receiptPath $receipt
    Assert-T7ResidentExportCatalogue $evidence;$script:checks++
    $receipt|Add-Member NoteProperty ObservedZone ([pscustomobject]@{Path='synthetic-donor';Bytes=1;SHA256=('e'*64);FileId='synthetic-id'})
    Save-Json $receiptPath $receipt
    Assert-T7ResidentExportZone $evidence $receipt.ObservedZone;$script:checks++
    foreach($field in @('Path','Bytes','SHA256','FileId')){
        $bad=Copy-Value $receipt.ObservedZone;$bad.$field='changed'
        Refuses {Assert-T7ResidentExportZone $evidence $bad} 'donor differs'
    }
    foreach($flag in @('TreeClosureConfirmed','LeaseReleased','InputsReverified','EngineOutputsValidated','OriginalInputMetadataUnchanged','AliasesRetained')){
        $bad=Copy-Value $receipt;$bad.$flag=$false;Save-Json $receiptPath $bad;Refuses {Assert-T7ResidentExportCatalogue $evidence} 'closure proof'
    }
    $bad=Copy-Value $receipt;$bad.Report.SHA256='b'*64;Save-Json $receiptPath $bad;Refuses {Assert-T7ResidentExportCatalogue $evidence} 'report pin'
    Save-Json $receiptPath $receipt
    foreach($field in @('CandidateSource','CandidateBytes','CandidateSHA256','EngineSource','SteamSource','Zone','Bootstraps','SharedQualification','InputMetadata')){
        $bad=Copy-Value $evidence;$bad.$field='changed';Refuses {Assert-T7ResidentExportCatalogue $bad} 'source inputs changed'
    }
    $catalogue.models[0].counts.lods=2;Save-Json $cataloguePath $catalogue;Refuses {Assert-T7ResidentExportCatalogue $evidence} 'one-LOD'
    $bad=Copy-Value $request;$bad.model='other';Save-Json $requestPath $bad;Refuses {Assert-T7ResidentExportCatalogue $evidence} 'Only the observed'
    # Exercise the full common plan gate using the existing invented metadata provider.
    & {
        foreach($pair in @(@('Test-T7CatalogueBootstrap.ps1',@('Get-Item','New-Fixture')),
            @('Test-T7CatalogueBootstraps.ps1',@('New-Qualified')))){
            $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $pair[0]),[ref]$tokens,[ref]$errors)
            if($errors.Count){throw 'Existing synthetic fixture parse error.'}
            foreach($name in $pair[1]){
                $nodes=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true))
                if($nodes.Count -ne 1){throw 'Existing synthetic fixture missing.'};. ([scriptblock]::Create($nodes[0].Extent.Text))
            }
        }
        $f=New-Qualified 23 'QualifiedCollectionV3';$p=$f.Plan
        $p.Schema='iw7.t7-resident-export-plan/1';$p|Add-Member NoteProperty Operation 'ResidentExportV1'
        $p|Add-Member NoteProperty ExportRequest $request
        $p|Add-Member NoteProperty ExportModelLimitBytes 1MB;$p|Add-Member NoteProperty ExportMeshLimitBytes 16MB
        $p.CandidateProfile='t7-catalog-message-publication';$p.EngineOutputProfile='ObservedStartupManifestA';$p.ReportLimitBytes=4KB
        $p.OutputLimitBytes+=21751296-$p.CandidateBytes;$p.CandidateBytes=21751296;$p.CandidateSHA256='31b9d908d15fb5f0bf17a7b27309dc7183458d5e586dfc6e427cc8ec2b3fa647'
        $p.Bindings[0].Bytes=$p.CandidateBytes;$p.Bindings[0].SHA256=$p.CandidateSHA256;$p.InputMetadata[0].Bytes=$p.CandidateBytes
        $script:provider[$p.CandidateSource].Length=$p.CandidateBytes
        $p.RunRoot=Join-Path $f.Repo 'runtime/t7-export-platform';$p.WorkingDirectory=Join-Path $p.RunRoot 'work';$p.StageRoot=Join-Path $p.RunRoot 'evidence'
        $p.Image=Join-Path $p.WorkingDirectory 't7-zonetool-candidate.exe';$p.Arguments=@('-t7-iw7-model','mp_freerun_04','p7_fre_platform_cap_02','0');$p.OutputKey=$key
        foreach($dir in 'work','evidence','temp'){$null=[IO.Directory]::CreateDirectory((Join-Path $p.RunRoot $dir))}
        function Add-TextPin($Path,[long]$Bytes=100,[string]$Hash=('c'*64)){
            $pin=[pscustomobject]@{Path=$Path;Bytes=$Bytes;SHA256=$Hash}
            $binding=Copy-Value $pin;$binding|Add-Member NoteProperty IsText $true;$p.Bindings+=@($binding)
            $script:provider[$Path]=[pscustomobject]@{PSIsContainer=$false;Length=$Bytes};$pin
        }
        for($i=0;$i -lt 6;$i++){$null=Add-TextPin (Join-Path $root ('publication-'+$i+'.txt'))}
        $null=Add-TextPin (Join-Path $f.Repo 'tools-source/asset-bridge/t7-bridge/T7ResidentExport.Profile.ps1')
        foreach($spec in @(@('SourceCataloguePlan',59287,'718829c910020e96b94f59bf504a2ba318bcdd4f2baa80e0bc8a82526631a0d0'),
            @('SourceCatalogueReceipt',35780,'7347a78280abc12eedd8e5f02ff536e0c411cae2264bc7b50101136aac2a717e'),
            @('SourceCatalogue',1669,'d27e34f0f42ac8ccb2b675d4295b397e42636261213c149eaff942e7a7867e3f'),@('ExportRequestFile',300,('d'*64)))){
            $p|Add-Member NoteProperty $spec[0] (Add-TextPin (Join-Path $root ($spec[0]+'.json')) $spec[1] $spec[2])
        }
        $p|Add-Member NoteProperty ReadbackSources @()
        foreach($path in @('t7-iw7/readback.py','t7-iw7/boot_contract.py','t7-iw7/export_contract.py','h1-fixture/inspect_fixture.py')){
            $p.ReadbackSources+=@(Add-TextPin (Join-Path $f.Repo ('tools-source/asset-bridge/'+$path)))
        }
        Assert-T7CataloguePlan $p $f.Repo 'synthetic-runner';$script:checks++
        foreach($spec in @(@('Operation','Catalogue'),@('Operation','ResidentExportV2'),@('Schema','iw7.t7-catalogue-plan/1'),
            @('CandidateSHA256',('a'*64)),@('ReportLimitBytes',512KB),@('ExportMeshLimitBytes',32MB),@('ExportModelLimitBytes',2MB),
            @('EngineOutputProfile','ObservedStartupA'),@('OutputLimitBytes',1GB),@('BootstrapPolicy','QualifiedCollectionV2'),@('RetryAuthorized',$true))){
            $bad=Copy-Value $p;$bad.($spec[0])=$spec[1];Refuses {Assert-T7CataloguePlan $bad $f.Repo 'synthetic-runner'} '.'
        }
        foreach($name in @('SourceCataloguePlan','SourceCatalogueReceipt','SourceCatalogue','ExportRequestFile')){
            $bad=Copy-Value $p;$bad.$name.SHA256='a'*64;Refuses {Assert-T7CataloguePlan $bad $f.Repo 'synthetic-runner'} 'not guarded'
        }
        $bad=Copy-Value $p;$bad.Arguments=@('-t7-iw7-model|mp_freerun_04|p7_fre_platform_cap_02|0');Refuses {Assert-T7CataloguePlan $bad $f.Repo 'synthetic-runner'} 'Exact resident export'
        $bad=Copy-Value $p;$bad.Bindings=$bad.Bindings[1..($bad.Bindings.Count-1)];Refuses {Assert-T7CataloguePlan $bad $f.Repo 'synthetic-runner'} 'binding count'
        $bad=Copy-Value $p;$bad.ReadbackSources=$bad.ReadbackSources[0..2];Refuses {Assert-T7CataloguePlan $bad $f.Repo 'synthetic-runner'} 'Four independent'
        $bad=Copy-Value $p;$bad.Bootstraps=$bad.Bootstraps[0..21];Refuses {Assert-T7CataloguePlan $bad $f.Repo 'synthetic-runner'} 'Exact resident export'
        $bad=Copy-Value $p;$bad.SourceCatalogue.SHA256='a'*64
        ($bad.Bindings|Where-Object Path -CEQ $bad.SourceCatalogue.Path).SHA256='a'*64
        Refuses {Assert-T7CataloguePlan $bad $f.Repo 'synthetic-runner'} 'Exact observed catalogue F'
        # Entire common plan gate with invented diagnostic metadata, never a real plan.
        $diagnostic=Copy-Value $p
        foreach($spec in @(@('BuildPlan','ExpectedBuildPlanSHA256',0,303182,'4bfb8c9aa45352b0e99acc0a66eab8df93eec8bcac15b9443b766e01a8fcb9e6'),
            @('BuildReceipt','ExpectedBuildReceiptSHA256',1,22393,'6cc2cab523115defa9ee0df2a9c5292a286236ce96d935fb374145a663510810'))){
            $pin=@($diagnostic.Bindings|Where-Object {$_.Path -ceq (Join-Path $root ('base-text-'+$spec[2]+'.json'))})[0]
            $pin.Bytes=$spec[3];$pin.SHA256=$spec[4]
            $diagnostic|Add-Member NoteProperty $spec[0] $pin.Path
            $diagnostic|Add-Member NoteProperty $spec[1] $pin.SHA256
            $script:provider[$pin.Path]=[pscustomobject]@{PSIsContainer=$false;Length=$pin.Bytes}
        }
        $header=[pscustomobject]@{Path=(Join-Path $root 'diagnostic/t7_iw7_resident_model.hpp');Bytes=13545;SHA256='701e3d1eccb0e98ecccfd2012215aaf7eff8db7bd974b184e86648a138b6e3c3'}
        $diagnostic|Add-Member NoteProperty ResidentSurfaceCountDiagnostic ([pscustomobject]@{Schema='iw7.t7-resident-surface-count-diagnostic/1';Header=$header})
        $binding=Copy-Value $header;$binding|Add-Member NoteProperty IsText $true;$diagnostic.Bindings+=@($binding)
        $script:provider[$header.Path]=[pscustomobject]@{PSIsContainer=$false;Length=$header.Bytes}
        $diagnostic.CandidateBytes+=1024;$diagnostic.CandidateSHA256='9'*64;$diagnostic.OutputLimitBytes+=1024
        $diagnostic.Bindings[0].Bytes=$diagnostic.CandidateBytes;$diagnostic.Bindings[0].SHA256=$diagnostic.CandidateSHA256
        $diagnostic.InputMetadata[0].Bytes=$diagnostic.CandidateBytes;$script:provider[$diagnostic.CandidateSource].Length=$diagnostic.CandidateBytes
        Assert-T7CataloguePlan $diagnostic $f.Repo 'synthetic-runner';$script:checks++
        Check ($diagnostic.Bindings.Count -eq $p.Bindings.Count+1 -and $diagnostic.OutputLimitBytes -eq $p.OutputLimitBytes+1024) 'Diagnostic added more than one text binding or changed fixed output budgets.'
        $bad=Copy-Value $diagnostic;$bad.PSObject.Properties.Remove('ResidentSurfaceCountDiagnostic')
        Refuses {Assert-T7CataloguePlan $bad $f.Repo 'synthetic-runner'} 'Exact resident export'
        foreach($spec in @(@('Operation','Catalogue'),@('PhysicalBytes',7GB),@('CommitBytes',9GB),@('DeadlineSeconds',121),
            @('GroupDeadlineSeconds',201),@('CleanupSeconds',6),@('MutableOutputLimitBytes',65MB),@('ReportLimitBytes',4097),
            @('ExportModelLimitBytes',2MB),@('ExportMeshLimitBytes',17MB),@('OutputLimitBytes',$p.OutputLimitBytes))){
            $bad=Copy-Value $diagnostic;$bad.($spec[0])=$spec[1];Refuses {Assert-T7CataloguePlan $bad $f.Repo 'synthetic-runner'} '.'
        }
        $bad=Copy-Value $diagnostic;$bad.Bindings=$bad.Bindings[0..($bad.Bindings.Count-2)]
        Refuses {Assert-T7CataloguePlan $bad $f.Repo 'synthetic-runner'} 'not guarded'
        foreach($name in @('SourceCataloguePlan','SourceCatalogueReceipt','SourceCatalogue')){
            $bad=Copy-Value $diagnostic;$bad.$name.SHA256='a'*64
            ($bad.Bindings|Where-Object Path -CEQ $bad.$name.Path).SHA256='a'*64
            Refuses {Assert-T7CataloguePlan $bad $f.Repo 'synthetic-runner'} 'Exact observed catalogue F'
        }
    }
    [ordered]@{Status='Passed';Checks=$checks;OwnerStockRead=$false;NativeProcessStarted=$false;RealLeaseAcquired=$false}|ConvertTo-Json
    & (Join-Path $PSScriptRoot 'Test-T7ResidentExportDiagnostic.ps1')
}finally{
    Close-Guards
    $resolved=[IO.Path]::GetFullPath($root);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-export-tests-[0-9a-f]{32}$'){throw 'Refuse cleanup outside synthetic root.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
