# Execute actual source guards using authored pins; no scheduler, SDK, tlog or compiler.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$root=$PSScriptRoot;$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'Run-T7Build.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Build source parse failed'}
$node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Assert-T7ImageProvenanceTransition'},$true)
. ([scriptblock]::Create($node.Extent.Text))
$contractPath=Join-Path $root 'image-provenance-source-contract.json'
$contract=Get-Content -LiteralPath $contractPath -Raw|ConvertFrom-Json
$profile=[pscustomobject]@{ProvenanceContract=[pscustomobject]@{Path=$contractPath;Bytes=(Get-Item $contractPath).Length;SHA256=(Get-FileHash $contractPath).Hash.ToLowerInvariant()};
    PreparedMain=[pscustomobject]@{Bytes=$contract.main.bytes;SHA256=$contract.main.sha256};
    PreparedCLI=[pscustomobject]@{Bytes=$contract.cli.bytes;SHA256=$contract.cli.sha256}}
foreach($row in @(@('ProvenanceSource','selected_image_provenance.hpp'),@('ProvenanceEntry','native_image_provenance.inc'),@('ProvenanceFixture','selected_image_provenance_fixture.cpp'))){
    $expected=$contract.files.($row[1]);$profile|Add-Member -NotePropertyName $row[0] -NotePropertyValue ([pscustomobject]@{Bytes=$expected.lf_bytes;SHA256=$expected.lf_sha256})
}
$marker=[pscustomobject]@{Schema='iw7.t7-image-provenance-build/1';SourceProfile='t7-image-provenance-v1';
    BaseMainBytes=43254;BaseMainSHA256='5aef1fad310071f5e680a9f5b4dbd6a303af6ea8605fccb5dc5705cb386b761d';
    BaseCLIBytes=112377;BaseCLISHA256='c63d9552464da674d3b03c35f7edc16385fb9370b113a3925fd7bc4835fb005a';
    MainBytes=$contract.main.bytes;MainSHA256=$contract.main.sha256;CLIBytes=$contract.cli.bytes;CLISHA256=$contract.cli.sha256}
$plan=[pscustomobject]@{BuildProfile=$profile;ReuseCompile=[pscustomobject]@{ImageProvenance=$marker};Bindings=@([pscustomobject]@{
    Path=(Join-Path $root 'selected_material_observation.hpp');IsText=$true;Bytes=18583;SHA256='a8848a92b8d7918fbe91ec4b68df123b1eaab89edde9d8a7c24d5a0cfb576ffc'})}
Assert-T7ImageProvenanceTransition $plan $root
$checks=1
foreach($case in 'old-profile','old-output','array-hash','extra-field','wrong-header','missing-g2','bad-contract','bool-size'){
    $p=$plan|ConvertTo-Json -Depth 12|ConvertFrom-Json
    switch($case){
        old-profile {$p.ReuseCompile.ImageProvenance.SourceProfile='t7-material-parts-v1'}
        old-output {$p.ReuseCompile.ImageProvenance.CLISHA256='f'*64}
        array-hash {$p.ReuseCompile.ImageProvenance.CLISHA256=@($p.ReuseCompile.ImageProvenance.CLISHA256)}
        extra-field {$p.ReuseCompile.ImageProvenance|Add-Member NoteProperty Extra 'ignored'}
        wrong-header {$p.BuildProfile.ProvenanceSource.SHA256='f'*64}
        missing-g2 {$p.Bindings=@()}
        bad-contract {$p.BuildProfile.ProvenanceContract.SHA256='f'*64}
        bool-size {$p.ReuseCompile.ImageProvenance.MainBytes=$true}
    }
    $refused=$false;try{Assert-T7ImageProvenanceTransition $p $root}catch{$refused=$true}
    if(!$refused){throw "Bad provenance source transition accepted: $case"};$checks++
}
$node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Assert-T7BuildProfile'},$true)
. ([scriptblock]::Create($node.Extent.Text))
$prepared=Join-Path $root 'authored-metadata/prepared';$response=Split-Path $prepared -Parent
$profile=[ordered]@{Name='t7-image-provenance-v1';Option='-t7-iw7-image-provenance-v1';ArgumentCount=5;
    TraceSchema='iw7.t7-catalog-trace/1';ContextSchema='iw7.t7-catalog-exit-context/1';CallerSchema='iw7.t7-catalog-callers/1';
    MessageSchema='iw7.t7-catalog-message/1';PublicationSchema='iw7.t7-message-publication-build/1';ObservationSchema='iw7.t7-selected-image-provenance/1';SourceOnlyPending=$true}
$paths=[ordered]@{Wiring=(Join-Path $root 'prepare_catalog_trace.py');PreparedMain=(Join-Path $prepared 'main.cpp');
    BaseBuildPlan=(Join-Path $response 'base-plan.json');BaseBuildReceipt=(Join-Path $response 'base-receipt.json');
    PublicationWiring=(Join-Path $root 'prepare_message_publication.py');PublicationSource=(Join-Path $root 'native_message_publication.inc');PreparedCLI=(Join-Path $prepared 'zonetool.cpp');
    MainResponse=(Join-Path $response 'main.obj.rsp');CLIResponse=(Join-Path $response 'zonetool11.obj.rsp');LinkResponse=(Join-Path $response 'link.rsp');
    ProvenanceBaseWiring=(Join-Path $root 'prepare_material_parts.py');ProvenanceWiring=(Join-Path $root 'prepare_image_provenance.py');
    ProvenanceSource=(Join-Path $root 'selected_image_provenance.hpp');ProvenanceEntry=(Join-Path $root 'native_image_provenance.inc');ProvenanceFixture=(Join-Path $root 'selected_image_provenance_fixture.cpp');ProvenanceContract=$contractPath}
$bindings=@($plan.Bindings)
foreach($name in $paths.Keys){
    $bytes=17;$sha='a'*64
    if($name -ceq 'BaseBuildPlan'){$sha='daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa'}
    if($name -ceq 'BaseBuildReceipt'){$sha='c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2'}
    if($name -ceq 'PreparedMain'){$bytes=$contract.main.bytes;$sha=$contract.main.sha256}
    if($name -ceq 'PreparedCLI'){$bytes=$contract.cli.bytes;$sha=$contract.cli.sha256}
    if($name -ceq 'ProvenanceContract'){$bytes=(Get-Item $contractPath).Length;$sha=(Get-FileHash $contractPath).Hash.ToLowerInvariant()}
    foreach($row in @(@('ProvenanceSource','selected_image_provenance.hpp'),@('ProvenanceEntry','native_image_provenance.inc'),@('ProvenanceFixture','selected_image_provenance_fixture.cpp'))){
        if($name -ceq $row[0]){$bytes=$contract.files.($row[1]).lf_bytes;$sha=$contract.files.($row[1]).lf_sha256}
    }
    $profile[$name]=[pscustomobject]@{Path=$paths[$name];Bytes=$bytes;SHA256=$sha}
    $bindings+=@([pscustomobject]@{Path=$paths[$name];Bytes=$bytes;SHA256=$sha;IsText=$true})
}
$compiler='C:\authored\cl.exe'
$stages=@(foreach($row in @(@('main','MainResponse'),@('zonetool11','CLIResponse'),@('link','LinkResponse'))){
    [pscustomobject]@{Name=$row[0];Image=$(if($row[0] -ceq 'link'){'C:\authored\link.exe'}else{$compiler});Arguments=@('@'+$paths[$row[1]]);
        Artifacts=@(if($row[0] -ceq 'link'){'zonetool-t7.exe','zonetool-t7.pdb','zonetool-t7.lib','zonetool-t7.exp'}else{($row[0]+'.obj'),'compile.pdb','dependencies.json'})}
})
$full=[pscustomobject]@{Compiler=$compiler;PreparedRoot=$prepared;BuildProfile=([pscustomobject]$profile);Bindings=$bindings;Stages=$stages;
    ReuseCompile=[pscustomobject]@{RecompiledMain=$true;RecompiledZonetool=$true;ImageProvenance=$marker;SelectedStreamedRenderOnlyV2=[pscustomobject]@{Schema='iw7.t7-selected-streamed-render-only-build/2';GeometryProfile='t7-iw7-selected-streamed-render-only-v2';CollisionPolicy='omit-source-rigid-collision-trees'}}}
if(!(Assert-T7BuildProfile $full $root)){throw 'Actual full source profile refused'};$checks++
foreach($case in 'pending-false','native-argcount','mixed-parts','mixed-c2','missing-base-adapter','old-stage-output'){
    $p=$full|ConvertTo-Json -Depth 15|ConvertFrom-Json
    switch($case){
        pending-false {$p.BuildProfile.SourceOnlyPending=$false}
        native-argcount {$p.BuildProfile.ArgumentCount=4}
        mixed-parts {$p.ReuseCompile|Add-Member NoteProperty MaterialParts ([pscustomobject]@{})}
        mixed-c2 {$p.ReuseCompile|Add-Member NoteProperty ZombiesAddObservationC2 ([pscustomobject]@{})}
        missing-base-adapter {$p.Bindings=@($p.Bindings|Where-Object Path -CNE $paths.ProvenanceBaseWiring)}
        old-stage-output {$p.Stages[0].Artifacts=@('previous.obj')}
    }
    $refused=$false;try{$null=Assert-T7BuildProfile $p $root}catch{$refused=$true}
    if(!$refused){throw "Invalid full producer profile accepted: $case"};$checks++
}
$gate=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst] -and
    $n.Extent.Text.StartsWith('if($null -ne $buildProfile -and $buildProfile.Name') -and
    $n.Extent.Text.Contains("Image-provenance producer is source-pending:")},$true))
if($gate.Count -ne 1){throw 'Unique source-only execution gate required'}
$body=[scriptblock]::Create($gate[0].Extent.Text)
$buildProfile=[pscustomobject]@{Name='t7-image-provenance-v1'};$Run=$true
$refused=$false;try{. $body}catch{$refused=$_.Exception.Message -like 'Image-provenance producer is source-pending:*'}
if(!$refused){throw 'Unqualified provenance -Run admitted'};$checks++
$Run=$false;$result=. $body|ConvertFrom-Json
foreach($name in 'NativeTypesLoaded','BinaryInputsHashed','ZoneHashObserved','LeaseAcquired','FilesCreated','Ready'){
    if($result.$name -isnot [bool] -or $result.$name){throw 'Source-only DEFAULT promoted execution'};$checks++
}
if($null -ne $result.CandidateBytes -or $null -ne $result.CandidateSHA256){throw 'Source-pending candidate fabricated'};$checks++
$import=$ast.Find({param($n) $n -is [Management.Automation.Language.CommandAst] -and $n.Extent.Text -ceq '. $plan.Core'},$true)
$admission=$ast.Find({param($n) $n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -ceq '$context.Lease' -and $n.Right.Extent.Text.StartsWith('Enter-IW7ResourceLease ')},$true)
if(!$import -or !$admission -or $gate[0].Extent.StartOffset -ge $import.Extent.StartOffset -or $gate[0].Extent.StartOffset -ge $admission.Extent.StartOffset){throw 'Source-only gate occurs after imports/admission'};$checks++
[ordered]@{SourceOnly=$true;Checks=$checks;CPPExecuted=$false;SDKOrToolBytesRead=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json -Compress
