# Default checks source/metadata only. Native execution needs a reviewed exact
# plan and separate coordinator GO; no ZoneTool/game launch exists in this runner.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell 7 required.'}
if($PlanSHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Exact reviewed plan SHA256 required.'}
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards;
    PublicationGuards=[Collections.Generic.List[object]]::new();Publications=[Collections.Generic.List[object]]::new();
    PreReleasePublished=$false;CompletionPublished=$false;CanExit=$false}
$state=$null;$failure=$null;$created=$false;$launcher=$null;$priority=$null
function Open-T7Bootstrap($Path,[long]$Bytes,[string]$SHA256) {
    if(![IO.Path]::IsPathFullyQualified($Path) -or [IO.Path]::GetFullPath($Path) -cne $Path){throw 'Canonical bootstrap path required.'}
    for($part=$Path;$part;$part=[IO.Path]::GetDirectoryName($part)) {
        if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Bootstrap reparse path refused.'}
    }
    if($Bytes -le 0 -or $Bytes -gt 32MB -or $SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Invalid source binding.'}
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read');$guards.Add($stream)
    if($stream.Length -ne $Bytes){throw 'Bootstrap length differs.'}
    $hash=[Security.Cryptography.SHA256]::Create()
    try{$actual=[Convert]::ToHexString($hash.ComputeHash($stream)).ToLowerInvariant()}finally{$hash.Dispose()}
    if($actual -cne $SHA256){throw 'Bootstrap source differs.'}
    $stream.Position=0;return $stream
}
function Assert-T7MaterialPartsTransition($Plan,[string]$SourceRoot) {
    $profile=$Plan.BuildProfile;$marker=$Plan.ReuseCompile.MaterialParts
    if((@($marker.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'BaseCLIBytes,BaseCLISHA256,BaseMainBytes,BaseMainSHA256,CLIBytes,CLISHA256,MainBytes,MainSHA256,Schema,SourceProfile'){
        throw 'Exact parts transition fields required.'
    }
    foreach($name in 'Schema','SourceProfile','BaseMainSHA256','BaseCLISHA256','MainSHA256','CLISHA256'){
        if($marker.$name -isnot [string]){throw 'Parts marker text scalar required.'}
    }
    foreach($name in 'BaseMainBytes','BaseCLIBytes','MainBytes','CLIBytes'){
        if($marker.$name -isnot [int] -and $marker.$name -isnot [long]){throw 'Parts marker integer size required.'}
    }
    if($marker.Schema -cne 'iw7.t7-material-parts-build/1' -or $marker.SourceProfile -cne 't7-material-parts-v1' -or
       $marker.BaseMainBytes -ne 43254 -or $marker.BaseMainSHA256 -cne '5aef1fad310071f5e680a9f5b4dbd6a303af6ea8605fccb5dc5705cb386b761d' -or
       $marker.BaseCLIBytes -ne 112377 -or $marker.BaseCLISHA256 -cne 'c63d9552464da674d3b03c35f7edc16385fb9370b113a3925fd7bc4835fb005a'){
        throw 'Exact E5-to-parts source transition required.'
    }
    $path=Join-Path $SourceRoot 'material-parts-source-contract.json'
    $pin=$profile.PartsContract
    if($pin.Path -isnot [string] -or $pin.Path -cne $path -or
       ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -le 0 -or $pin.Bytes -gt 16KB -or
       $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or
       (Get-Item -LiteralPath $path).Length -ne $pin.Bytes -or (Get-FileHash -LiteralPath $path).Hash -ine $pin.SHA256){
        throw 'Pinned bounded parts source contract required.'
    }
    $contract=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
    if((@($contract.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'cli,files,main,schema,source_profile' -or
       $contract.schema -isnot [string] -or $contract.schema -cne 'iw7.t7-material-parts-source/1' -or
       $contract.source_profile -isnot [string] -or $contract.source_profile -cne 't7-material-parts-v1' -or
       (@($contract.files.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'native_material_parts.inc,selected_material_parts_observation_fixture.cpp,selected_material_parts_observation.hpp'){
        throw 'Exact parts source contract schema/inventory required.'
    }
    foreach($row in @(@('main','PreparedMain','MainBytes','MainSHA256'),@('cli','PreparedCLI','CLIBytes','CLISHA256'))){
        $output=$contract.($row[0]);$source=$profile.($row[1])
        if((@($output.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'bytes,sha256' -or
           ($output.bytes -isnot [int] -and $output.bytes -isnot [long]) -or $output.bytes -le 0 -or $output.bytes -gt 128KB -or
           $output.sha256 -isnot [string] -or $output.sha256 -cnotmatch '^[0-9a-f]{64}$' -or
           $marker.($row[2]) -ne $output.bytes -or $marker.($row[3]) -cne $output.sha256 -or
           $source.Bytes -ne $output.bytes -or $source.SHA256 -cne $output.sha256){throw 'Parts generated output pin differs.'}
    }
    foreach($row in @(@('PartsSource','selected_material_parts_observation.hpp'),@('PartsEntry','native_material_parts.inc'),@('PartsFixture','selected_material_parts_observation_fixture.cpp'))){
        $expected=$contract.files.($row[1]);$source=$profile.($row[0])
        if((@($expected.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'lf_bytes,lf_sha256' -or
           ($expected.lf_bytes -isnot [int] -and $expected.lf_bytes -isnot [long]) -or $expected.lf_bytes -le 0 -or $expected.lf_bytes -gt 64KB -or
           $expected.lf_sha256 -isnot [string] -or $expected.lf_sha256 -cnotmatch '^[0-9a-f]{64}$' -or
           $source.Bytes -ne $expected.lf_bytes -or $source.SHA256 -cne $expected.lf_sha256){throw 'Parts explicit source pin differs.'}
    }
    $g2=Join-Path $SourceRoot 'selected_material_observation.hpp'
    if(@($Plan.Bindings|Where-Object {$_.Path -ceq $g2 -and $_.IsText -is [bool] -and $_.IsText -and
        $_.Bytes -eq 18583 -and $_.SHA256 -ceq 'a8848a92b8d7918fbe91ec4b68df123b1eaab89edde9d8a7c24d5a0cfb576ffc'}).Count -ne 1){
        throw 'Unchanged G2 observer binding required.'
    }
}
function Assert-T7ImageProvenanceTransition($Plan,[string]$SourceRoot) {
    $profile=$Plan.BuildProfile;$marker=$Plan.ReuseCompile.ImageProvenance
    if((@($marker.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'BaseCLIBytes,BaseCLISHA256,BaseMainBytes,BaseMainSHA256,CLIBytes,CLISHA256,MainBytes,MainSHA256,Schema,SourceProfile'){
        throw 'Exact provenance transition fields required.'
    }
    foreach($name in 'Schema','SourceProfile','BaseMainSHA256','BaseCLISHA256','MainSHA256','CLISHA256'){
        if($marker.$name -isnot [string]){throw 'Provenance marker text scalar required.'}
    }
    foreach($name in 'BaseMainBytes','BaseCLIBytes','MainBytes','CLIBytes'){
        if($marker.$name -isnot [int] -and $marker.$name -isnot [long]){throw 'Provenance marker integer size required.'}
    }
    if($marker.Schema -cne 'iw7.t7-image-provenance-build/1' -or $marker.SourceProfile -cne 't7-image-provenance-v1' -or
       $marker.BaseMainBytes -ne 43254 -or $marker.BaseMainSHA256 -cne '5aef1fad310071f5e680a9f5b4dbd6a303af6ea8605fccb5dc5705cb386b761d' -or
       $marker.BaseCLIBytes -ne 112377 -or $marker.BaseCLISHA256 -cne 'c63d9552464da674d3b03c35f7edc16385fb9370b113a3925fd7bc4835fb005a'){
        throw 'Exact E5-to-provenance source transition required.'
    }
    $path=Join-Path $SourceRoot 'image-provenance-source-contract.json'
    $pin=$profile.ProvenanceContract
    if($pin.Path -isnot [string] -or $pin.Path -cne $path -or
       ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -le 0 -or $pin.Bytes -gt 16KB -or
       $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or
       (Get-Item -LiteralPath $path).Length -ne $pin.Bytes -or (Get-FileHash -LiteralPath $path).Hash -ine $pin.SHA256){
        throw 'Pinned bounded provenance source contract required.'
    }
    $contract=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
    if((@($contract.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'cli,files,main,schema,source_profile' -or
       $contract.schema -isnot [string] -or $contract.schema -cne 'iw7.t7-image-provenance-source/1' -or
       $contract.source_profile -isnot [string] -or $contract.source_profile -cne 't7-image-provenance-v1' -or
       (@($contract.files.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'native_image_provenance.inc,selected_image_provenance_fixture.cpp,selected_image_provenance.hpp'){
        throw 'Exact provenance source contract schema/inventory required.'
    }
    foreach($row in @(@('main','PreparedMain','MainBytes','MainSHA256'),@('cli','PreparedCLI','CLIBytes','CLISHA256'))){
        $output=$contract.($row[0]);$source=$profile.($row[1])
        if($Plan.ReuseCompile.PSObject.Properties['ImageMetadata']){
            $extension=$Plan.ReuseCompile.ImageMetadata
            $source=[pscustomobject]@{Bytes=$extension.('Base'+$row[2]);SHA256=$extension.('Base'+$row[3])}
        }
        if((@($output.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'bytes,sha256' -or
           ($output.bytes -isnot [int] -and $output.bytes -isnot [long]) -or $output.bytes -le 0 -or $output.bytes -gt 128KB -or
           $output.sha256 -isnot [string] -or $output.sha256 -cnotmatch '^[0-9a-f]{64}$' -or
           $marker.($row[2]) -ne $output.bytes -or $marker.($row[3]) -cne $output.sha256 -or
           $source.Bytes -ne $output.bytes -or $source.SHA256 -cne $output.sha256){throw 'Provenance generated output pin differs.'}
    }
    foreach($row in @(@('ProvenanceSource','selected_image_provenance.hpp'),@('ProvenanceEntry','native_image_provenance.inc'),@('ProvenanceFixture','selected_image_provenance_fixture.cpp'))){
        $expected=$contract.files.($row[1]);$source=$profile.($row[0])
        if((@($expected.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'lf_bytes,lf_sha256' -or
           ($expected.lf_bytes -isnot [int] -and $expected.lf_bytes -isnot [long]) -or $expected.lf_bytes -le 0 -or $expected.lf_bytes -gt 64KB -or
           $expected.lf_sha256 -isnot [string] -or $expected.lf_sha256 -cnotmatch '^[0-9a-f]{64}$' -or
           $source.Bytes -ne $expected.lf_bytes -or $source.SHA256 -cne $expected.lf_sha256){throw 'Provenance explicit source pin differs.'}
    }
    $g2=Join-Path $SourceRoot 'selected_material_observation.hpp'
    if(@($Plan.Bindings|Where-Object {$_.Path -ceq $g2 -and $_.IsText -is [bool] -and $_.IsText -and
        $_.Bytes -eq 18583 -and $_.SHA256 -ceq 'a8848a92b8d7918fbe91ec4b68df123b1eaab89edde9d8a7c24d5a0cfb576ffc'}).Count -ne 1){
        throw 'Unchanged G2 observer binding required.'
    }
}
function Assert-T7ImageMetadataTransition($Plan,[string]$SourceRoot) {
    $profile=$Plan.BuildProfile;$marker=$Plan.ReuseCompile.ImageMetadata
    if((@($marker.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'BaseCLIBytes,BaseCLISHA256,BaseMainBytes,BaseMainSHA256,CLIBytes,CLISHA256,MainBytes,MainSHA256,Schema,SourceProfile' -or
       $marker.Schema -isnot [string] -or $marker.Schema -cne 'iw7.t7-image-metadata-build/1' -or
       $marker.SourceProfile -isnot [string] -or $marker.SourceProfile -cne 't7-image-metadata-v1' -or
       $profile.MetadataSchema -isnot [string] -or $profile.MetadataSchema -cne 'iw7.t7-selected-image-metadata/1' -or
       $profile.MetadataOption -isnot [string] -or $profile.MetadataOption -cne '-t7-iw7-image-metadata-v1'){
        throw 'Exact finite metadata extension marker required.'
    }
    foreach($name in 'BaseMainBytes','BaseCLIBytes','MainBytes','CLIBytes'){
        if($marker.$name -isnot [int] -and $marker.$name -isnot [long]){throw 'Metadata marker integer size required.'}
    }
    foreach($name in 'BaseMainSHA256','BaseCLISHA256','MainSHA256','CLISHA256'){
        if($marker.$name -isnot [string] -or $marker.$name -cnotmatch '^[0-9a-f]{64}$'){throw 'Metadata marker hash required.'}
    }
    $base=$Plan.ReuseCompile.ImageProvenance
    if($marker.BaseMainBytes -ne $base.MainBytes -or $marker.BaseMainSHA256 -cne $base.MainSHA256 -or
       $marker.BaseCLIBytes -ne $base.CLIBytes -or $marker.BaseCLISHA256 -cne $base.CLISHA256){throw 'Metadata must extend the exact F2 output pair.'}
    $path=Join-Path $SourceRoot 'image-metadata-source-contract.json';$pin=$profile.MetadataContract
    if($pin.Path -isnot [string] -or $pin.Path -cne $path -or
       ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -le 0 -or $pin.Bytes -gt 16KB -or
       $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or
       (Get-Item -LiteralPath $path).Length -ne $pin.Bytes -or (Get-FileHash -LiteralPath $path).Hash -ine $pin.SHA256){throw 'Pinned bounded metadata source contract required.'}
    $contract=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
    $sourceRows=@(@('MetadataPartsSource','selected_material_parts_observation.hpp'),
        @('MetadataBuilder','selected_image_header_metadata.hpp'),@('MetadataBuilderFixture','selected_image_header_metadata_fixture.cpp'),
        @('MetadataReadGuard','selected_image_metadata_read_guard.hpp'),
        @('MetadataGuardFixture','selected_image_metadata_guard_fixture.cpp'),
        @('MetadataSource','selected_image_metadata.hpp'),@('MetadataEntry','native_image_metadata.inc'))
    if((@($contract.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'cli,files,guarded_observer,main,schema,source_profile' -or
       $contract.schema -isnot [string] -or $contract.schema -cne 'iw7.t7-image-metadata-source/1' -or
       $contract.source_profile -isnot [string] -or $contract.source_profile -cne 't7-image-metadata-v1' -or
       (@($contract.files.PSObject.Properties.Name|Sort-Object)-join ',') -cne (@($sourceRows|ForEach-Object {$_[1]}|Sort-Object)-join ',')){
        throw 'Exact metadata source schema/inventory required.'
    }
    foreach($row in $sourceRows){
        $expected=$contract.files.($row[1]);$actual=$profile.($row[0])
        if((@($expected.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'lf_bytes,lf_sha256' -or
           ($expected.lf_bytes -isnot [int] -and $expected.lf_bytes -isnot [long]) -or $expected.lf_bytes -le 0 -or $expected.lf_bytes -gt 16KB -or
           $expected.lf_sha256 -isnot [string] -or $expected.lf_sha256 -cnotmatch '^[0-9a-f]{64}$' -or
           $actual.Bytes -ne $expected.lf_bytes -or $actual.SHA256 -cne $expected.lf_sha256){throw 'Metadata explicit source pin differs.'}
    }
    foreach($row in @(@('main','PreparedMain','MainBytes','MainSHA256'),@('cli','PreparedCLI','CLIBytes','CLISHA256'))){
        $expected=$contract.($row[0]);$actual=$profile.($row[1]);$cap=if($row[0] -ceq 'main'){64KB}else{160KB}
        if($Plan.ReuseCompile.PSObject.Properties['RegistrationMetadata']){
            $extension=$Plan.ReuseCompile.RegistrationMetadata
            $actual=[pscustomobject]@{Bytes=$extension.('Base'+$row[2]);SHA256=$extension.('Base'+$row[3])}
        }
        if((@($expected.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'bytes,sha256' -or
           ($expected.bytes -isnot [int] -and $expected.bytes -isnot [long]) -or $expected.bytes -le 0 -or $expected.bytes -gt $cap -or
           $expected.sha256 -isnot [string] -or $expected.sha256 -cnotmatch '^[0-9a-f]{64}$' -or
           $actual.Bytes -ne $expected.bytes -or $actual.SHA256 -cne $expected.sha256 -or
           $marker.($row[2]) -ne $expected.bytes -or $marker.($row[3]) -cne $expected.sha256){throw 'Metadata generated output pin differs.'}
    }
    $guarded=$contract.guarded_observer;$guardedPin=$profile.MetadataGuardedObserver
    if((@($guarded.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'bytes,sha256' -or
       ($guarded.bytes -isnot [int] -and $guarded.bytes -isnot [long]) -or $guarded.bytes -le 0 -or $guarded.bytes -gt 32KB -or
       $guarded.sha256 -isnot [string] -or $guarded.sha256 -cnotmatch '^[0-9a-f]{64}$' -or
       $guardedPin.Bytes -ne $guarded.bytes -or $guardedPin.SHA256 -cne $guarded.sha256){throw 'Same guarded observer output pin required.'}
    if(!$Plan.ReuseCompile.PSObject.Properties['RegistrationMetadata']){Assert-T7ImageMetadataFixtureStages $Plan $SourceRoot}
}
function Assert-T7ImageMetadataFixtureStages($Plan,[string]$SourceRoot) {
    $profile=$Plan.BuildProfile;$native=$profile.MetadataFixtureNativeRoot
    if(($profile.MetadataMapperChecks -isnot [int] -and $profile.MetadataMapperChecks -isnot [long]) -or $profile.MetadataMapperChecks -ne 54 -or
       ($profile.MetadataGuardChecks -isnot [int] -and $profile.MetadataGuardChecks -isnot [long]) -or $profile.MetadataGuardChecks -ne 13 -or
       $native -isnot [string] -or ![IO.Path]::IsPathFullyQualified($native) -or [IO.Path]::GetFullPath($native) -cne $native){throw 'Exact metadata fixture source/check profile required.'}
    for($part=$native;$part;$part=[IO.Path]::GetDirectoryName($part)){
        if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Metadata fixture native source reparse refused.'}
    }
    $structs=Join-Path $native 'src/zonetool/zonetool/t7/structs.hpp'
    # Retained Windows input identities use prepare_build.key()'s lowercase paths.
    if(@($Plan.Inputs|Where-Object Path -IEQ $structs).Count -ne 1){throw 'Metadata fixture native headers must be in sealed inputs.'}
    $compile=@($Plan.Stages|Where-Object Name -CEQ 'metadata-fixture-compile')
    $probe=@($Plan.Stages|Where-Object Name -CEQ 'metadata-fixture-test')
    $root=Join-Path $Plan.RunRoot 'metadata-fixture-compile'
    $response=Join-Path (Split-Path $Plan.PreparedRoot -Parent) 'metadata-fixture.rsp'
    if($compile.Count -ne 1 -or $probe.Count -ne 1 -or $compile[0].Stage -cne 'Compile' -or $compile[0].Image -cne $Plan.Compiler -or
       $compile[0].DeadlineSeconds -ne 120 -or (@($compile[0].Arguments)-join '|') -cne ('@'+$response) -or
       (@($compile[0].Artifacts)-join ',') -cne 'metadata-fixture.obj,metadata-fixture.exe,metadata-fixture.pdb,dependencies.json' -or
       $probe[0].Stage -cne 'Probe' -or $probe[0].Image -cne (Join-Path $root 'metadata-fixture.exe') -or
       $probe[0].DeadlineSeconds -ne 15 -or @($probe[0].Arguments).Count -or @($probe[0].Artifacts).Count){throw 'Exact original H1 metadata fixture stages required.'}
    $arguments=@('/nologo','/std:c++20','/EHsc','/W4','/WX','/MT','/Od','/Z7','/external:W0',
        ('/external:I'+(Join-Path $native 'src/zonetool')),('/external:I'+(Join-Path $native 'deps/json/single_include/nlohmann')),
        ('/I'+$SourceRoot),('/I'+$Plan.PreparedRoot),'/sourceDependencies',(Join-Path $root 'dependencies.json'),
        ('/Fo'+(Join-Path $root 'metadata-fixture.obj')),('/Fe'+(Join-Path $root 'metadata-fixture.exe')),
        (Join-Path $SourceRoot 'selected_image_metadata_guard_fixture.cpp'),'/link','/INCREMENTAL:NO','/DEBUG',('/PDB:'+(Join-Path $root 'metadata-fixture.pdb')))
    $pin=$profile.MetadataFixtureResponse
    if($pin.Path -isnot [string] -or $pin.Path -cne $response -or
       ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -le 0 -or $pin.Bytes -gt 16KB -or
       $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or
       (Get-Item -LiteralPath $response).Length -ne $pin.Bytes -or (Get-FileHash -LiteralPath $response).Hash -ine $pin.SHA256){throw 'Pinned finite metadata fixture response required.'}
    $actual=Split-T7ResponseArguments ([IO.File]::ReadAllText($response))
    if(($actual-join "`0") -cne ($arguments-join "`0")){throw 'Exact metadata fixture compile arguments required.'}
}
function Assert-T7RegistrationMetadataTransition($Plan,[string]$SourceRoot) {
    $p=$Plan.BuildProfile;$m=$Plan.ReuseCompile.RegistrationMetadata
    if($m.Schema -isnot [string] -or $m.SourceProfile -isnot [string] -or $p.RegistrationSchema -isnot [string]){
        throw 'Registration schema/profile text scalars required.'
    }
    $keys='BaseCLIBytes,BaseCLISHA256,BaseMainBytes,BaseMainSHA256,CLIBytes,CLISHA256,CPPQualified,MainBytes,MainSHA256,Ready,Schema,SourceOnlyPending,SourceProfile'
    if((@($m.PSObject.Properties.Name|Sort-Object)-join ',') -cne $keys -or
       $m.Schema -cne 'iw7.t7-registration-image-metadata-build/1' -or $m.SourceProfile -cne 't7-registration-image-header-metadata-v1' -or
       $m.SourceOnlyPending -isnot [bool] -or !$m.SourceOnlyPending -or $m.CPPQualified -isnot [bool] -or $m.CPPQualified -or
       $m.Ready -isnot [bool] -or $m.Ready -or $p.RegistrationSchema -cne 'iw7.t7-registration-image-header-metadata/1' -or
       ($p.RegistrationFixtureChecks -isnot [int] -and $p.RegistrationFixtureChecks -isnot [long]) -or $p.RegistrationFixtureChecks -ne 39 -or
       $p.RegistrationCPPQualified -isnot [bool] -or $p.RegistrationCPPQualified){throw 'Exact pending registration build/fixture marker required.'}
    foreach($name in 'BaseMainBytes','BaseCLIBytes','MainBytes','CLIBytes'){
        if(($m.$name -isnot [int] -and $m.$name -isnot [long]) -or $m.$name -le 0){throw 'Registration integer source size required.'}
    }
    foreach($name in 'BaseMainSHA256','BaseCLISHA256','MainSHA256','CLISHA256'){
        if($m.$name -isnot [string] -or $m.$name -cnotmatch '^[0-9a-f]{64}$'){throw 'Registration source hash required.'}
    }
    $base=$Plan.ReuseCompile.ImageMetadata
    if($m.BaseMainBytes -ne $base.MainBytes -or $m.BaseMainSHA256 -cne $base.MainSHA256 -or
       $m.BaseCLIBytes -ne $base.CLIBytes -or $m.BaseCLISHA256 -cne $base.CLISHA256){throw 'Registration must extend exact metadata source pair.'}
    $pin=$p.RegistrationContract;$path=Join-Path $SourceRoot 'registration-image-metadata-source-contract.json'
    if($pin.Path -isnot [string] -or $pin.Path -cne $path -or
       ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -le 0 -or $pin.Bytes -gt 16KB -or
       $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or
       (Get-Item -LiteralPath $path).Length -ne $pin.Bytes -or (Get-FileHash -LiteralPath $path).Hash -ine $pin.SHA256){throw 'Pinned registration contract required.'}
    $c=Get-Content -Raw -LiteralPath $path|ConvertFrom-Json
    if($c.schema -cne 'iw7.t7-registration-image-metadata-source/1' -or $c.source_profile -cne 't7-registration-image-header-metadata-v1' -or
       $c.report_schema -cne 'iw7.t7-registration-image-header-metadata/1' -or $c.native_option -cne '-t7-iw7-image-registration-metadata-v1' -or
       $c.source_only_pending -isnot [bool] -or !$c.source_only_pending -or $c.cpp_qualified -isnot [bool] -or $c.cpp_qualified -or
       $c.native_observed -isnot [bool] -or $c.native_observed -or $c.ready -isnot [bool] -or $c.ready -or
       $c.image_header_bytes -ne 264 -or $c.completed_header_copies -ne 2 -or $c.registration_header_bytes_copied -ne 528 -or
       $c.fixture_expected_checks -ne 39 -or $c.fixture_stdout -cne "IW7_T7_REGISTRATION_HEADER_CHECKS=39`n"){throw 'Exact registration source/copy contract required.'}
    foreach($row in @(@('RegistrationCapture','registration_image_header_capture.hpp'),
        @('RegistrationEntry','native_image_registration_metadata.inc'),@('RegistrationFixture','registration_image_header_fixture.cpp'))){
        $expected=$c.files.($row[1]);$actual=$p.($row[0])
        if($actual.Path -cne (Join-Path $SourceRoot $row[1]) -or $actual.Bytes -ne $expected.bytes -or
           $actual.SHA256 -cne $expected.sha256){throw 'Registration source pin differs.'}
    }
    foreach($row in @(@('main','PreparedMain','MainBytes','MainSHA256'),@('cli','PreparedCLI','CLIBytes','CLISHA256'))){
        $expected=$c.($row[0]);$actual=$p.($row[1]);$cap=if($row[0] -ceq 'main'){64KB}else{192KB}
        if($Plan.ReuseCompile.PSObject.Properties['IncomingObservation']){
            $extension=$Plan.ReuseCompile.IncomingObservation
            $actual=[pscustomobject]@{Bytes=$extension.('Base'+$row[2]);SHA256=$extension.('Base'+$row[3])}
        }elseif($Plan.ReuseCompile.PSObject.Properties['RegistrationBindingsObservation']){
            $extension=$Plan.ReuseCompile.RegistrationBindingsObservation
            $actual=[pscustomobject]@{Bytes=$extension.('Base'+$row[2]);SHA256=$extension.('Base'+$row[3])}
        }
        if($expected.bytes -le 0 -or $expected.bytes -gt $cap -or $actual.Bytes -ne $expected.bytes -or
           $actual.SHA256 -cne $expected.sha256 -or $m.($row[2]) -ne $expected.bytes -or $m.($row[3]) -cne $expected.sha256){throw 'Registration generated output pin differs.'}
    }
    if($p.RegistrationObserver.Bytes -ne $c.derived_observer.bytes -or $p.RegistrationObserver.SHA256 -cne $c.derived_observer.sha256){throw 'Same derived observer must compile in fixture and CLI.'}
    $native=$p.MetadataFixtureNativeRoot
    if($native -isnot [string] -or ![IO.Path]::IsPathFullyQualified($native) -or [IO.Path]::GetFullPath($native) -cne $native){throw 'Exact registration native header root required.'}
    for($part=$native;$part;$part=[IO.Path]::GetDirectoryName($part)){if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Registration native source reparse refused.'}}
    if(@($Plan.Inputs|Where-Object Path -IEQ (Join-Path $native 'src/zonetool/zonetool/t7/structs.hpp')).Count -ne 1){throw 'Registration fixture native header must be sealed.'}
    $compile=@($Plan.Stages|Where-Object Name -CEQ 'registration-fixture-compile');$probe=@($Plan.Stages|Where-Object Name -CEQ 'registration-fixture-test')
    $root=Join-Path $Plan.RunRoot 'registration-fixture-compile';$response=Join-Path (Split-Path $Plan.PreparedRoot -Parent) 'registration-fixture.rsp'
    if($compile.Count -ne 1 -or $probe.Count -ne 1 -or $compile[0].Stage -cne 'Compile' -or $compile[0].Image -cne $Plan.Compiler -or
       $compile[0].DeadlineSeconds -ne 120 -or (@($compile[0].Arguments)-join '|') -cne ('@'+$response) -or
       (@($compile[0].Artifacts)-join ',') -cne 'registration-fixture.obj,registration-fixture.exe,registration-fixture.pdb,dependencies.json' -or
       $probe[0].Stage -cne 'Probe' -or $probe[0].Image -cne (Join-Path $root 'registration-fixture.exe') -or
       $probe[0].DeadlineSeconds -ne 15 -or @($probe[0].Arguments).Count -or @($probe[0].Artifacts).Count){throw 'Exact H1 registration fixture stages required.'}
    $fixtureArguments=@('/nologo','/std:c++20','/EHsc','/W4','/WX','/MT','/Od','/Z7','/external:W0',
        ('/external:I'+(Join-Path $native 'src/zonetool')),('/external:I'+(Join-Path $native 'deps/json/single_include/nlohmann')),
        ('/I'+$SourceRoot),('/I'+$Plan.PreparedRoot),'/sourceDependencies',(Join-Path $root 'dependencies.json'),
        ('/Fo'+(Join-Path $root 'registration-fixture.obj')),('/Fe'+(Join-Path $root 'registration-fixture.exe')),
        $(if($Plan.ReuseCompile.PSObject.Properties['RegistrationBindingsObservation']){Join-Path $Plan.PreparedRoot 'registration_bindings_combined_fixture.cpp'}else{Join-Path $SourceRoot $(if($Plan.ReuseCompile.PSObject.Properties['IncomingObservation']){'incoming_image_event_fixture.cpp'}else{'registration_image_header_fixture.cpp'})}),'/link','/INCREMENTAL:NO','/DEBUG',('/PDB:'+(Join-Path $root 'registration-fixture.pdb')))
    $pin=$p.RegistrationResponse
    if($pin.Path -isnot [string] -or $pin.Path -cne $response -or
       ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -le 0 -or $pin.Bytes -gt 16KB -or
       $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or
       (Get-Item -LiteralPath $response).Length -ne $pin.Bytes -or (Get-FileHash -LiteralPath $response).Hash -ine $pin.SHA256 -or
       ((Split-T7ResponseArguments ([IO.File]::ReadAllText($response)))-join "`0") -cne ($fixtureArguments-join "`0")){throw 'Exact pinned registration fixture response required.'}
}
function Assert-T7RegistrationFixtureOutput([string]$StageRoot,$StageState) {
    $stdout=Join-Path $StageRoot 'stdout.log';$stderr=Join-Path $StageRoot 'stderr.log'
    if((Get-Item -LiteralPath $stdout).Length -gt 128 -or (Get-Item -LiteralPath $stderr).Length -ne 0 -or
       ([IO.File]::ReadAllText($stdout)).Replace("`r`n","`n") -cne "IW7_T7_REGISTRATION_HEADER_CHECKS=39`n"){
        throw 'Exactly 39 actual registration-header checks required before main/CLI compilation.'
    }
    $StageState.Checks=39;$StageState.EngineInvoked=$false
}
function Assert-T7IncomingMetadataTransition($Plan,[string]$SourceRoot) {
    $p=$Plan.BuildProfile;$m=$Plan.ReuseCompile.IncomingObservation
    if($m.Schema -isnot [string] -or $m.SourceProfile -isnot [string] -or $p.IncomingSchema -isnot [string] -or
       $p.Name -isnot [string] -or $p.Option -isnot [string] -or $p.ObservationSchema -isnot [string]){
        throw 'Incoming schema/profile text scalars required.'
    }
    foreach($role in 'IncomingWiring','IncomingContract','IncomingMembers','IncomingModule','IncomingEntry','IncomingFixture',
        'IncomingCapture','IncomingObserver','IncomingBaselineFixture'){
        if(!$p.PSObject.Properties[$role]){throw "Closed scalar incoming source pin required: $role."}
        $pin=$p.$role
        if($pin -isnot [pscustomobject] -or (@($pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
           $pin.Path -isnot [string] -or [string]::IsNullOrWhiteSpace($pin.Path) -or
           ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -le 0 -or $pin.Bytes -gt 64KB -or
           $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$'){
            throw "Closed scalar incoming source pin required: $role."
        }
    }
    if((@($m.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'BaseCLIBytes,BaseCLISHA256,BaseMainBytes,BaseMainSHA256,CLIBytes,CLISHA256,CPPQualified,MainBytes,MainSHA256,Ready,Schema,SourceOnlyPending,SourceProfile' -or
       $m.Schema -cne 'iw7.t7-incoming-image-build/1' -or $m.SourceProfile -cne 't7-incoming-image-header-observation-v1' -or
       $p.IncomingSchema -cne 'iw7.t7-incoming-image-header-observation/1' -or
       $m.SourceOnlyPending -isnot [bool] -or !$m.SourceOnlyPending -or $m.CPPQualified -isnot [bool] -or $m.CPPQualified -or
       $m.Ready -isnot [bool] -or $m.Ready -or $p.IncomingCPPQualified -isnot [bool] -or $p.IncomingCPPQualified -or
       ($p.IncomingFixtureChecks -isnot [int] -and $p.IncomingFixtureChecks -isnot [long]) -or $p.IncomingFixtureChecks -ne 48){throw 'Exact pending incoming source marker required.'}
    foreach($name in 'BaseMainBytes','BaseCLIBytes','MainBytes','CLIBytes'){
        if(($m.$name -isnot [int] -and $m.$name -isnot [long]) -or $m.$name -le 0){throw 'Incoming integer source size required.'}
    }
    foreach($name in 'BaseMainSHA256','BaseCLISHA256','MainSHA256','CLISHA256'){
        if($m.$name -isnot [string] -or $m.$name -cnotmatch '^[0-9a-f]{64}$'){throw 'Incoming source hash required.'}
    }
    $base=$Plan.ReuseCompile.RegistrationMetadata
    if($m.BaseMainBytes -ne $base.MainBytes -or $m.BaseMainSHA256 -cne $base.MainSHA256 -or
       $m.BaseCLIBytes -ne $base.CLIBytes -or $m.BaseCLISHA256 -cne $base.CLISHA256){throw 'Incoming must extend the exact CPP39 source pair.'}
    $pin=$p.IncomingContract;$path=Join-Path $SourceRoot 'incoming-image-source-contract.json'
    if($pin.Path -isnot [string] -or $pin.Path -cne $path -or
       ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -le 0 -or $pin.Bytes -gt 16KB -or
       $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or
       (Get-Item $path).Length -ne $pin.Bytes -or (Get-FileHash $path).Hash -ine $pin.SHA256){throw 'Pinned incoming source contract required.'}
    $c=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
    foreach($name in 'schema','source_profile','native_option','report_schema','target_name'){
        if($c.$name -isnot [string]){throw 'Incoming contract text scalar required.'}
    }
    if($c.schema -cne 'iw7.t7-incoming-image-source/1' -or $c.source_profile -cne 't7-incoming-image-header-observation-v1' -or
       $c.native_option -cne '-t7-iw7-incoming-image-header-v1' -or $c.report_schema -cne $p.IncomingSchema -or
       $c.target_name -cne '$camo_base_normal' -or $c.fixture_legacy_checks -ne 39 -or $c.fixture_incoming_checks -ne 48 -or
       $c.fixture_stdout -cne "IW7_T7_REGISTRATION_HEADER_CHECKS=39`nIW7_T7_INCOMING_IMAGE_CHECKS=48`n" -or
       $c.source_only_pending -isnot [bool] -or !$c.source_only_pending -or $c.cpp_qualified -isnot [bool] -or $c.cpp_qualified -or
       $c.native_observed -isnot [bool] -or $c.native_observed -or $c.ready -isnot [bool] -or $c.ready){throw 'Exact incoming source/fixture contract required.'}
    foreach($row in @(@('main','PreparedMain','MainBytes','MainSHA256'),@('cli','PreparedCLI','CLIBytes','CLISHA256'))){
        $expected=$c.($row[0]);$actual=$p.($row[1]);$cap=if($row[0] -ceq 'main'){64KB}else{192KB}
        if($expected.bytes -le 0 -or $expected.bytes -gt $cap -or $actual.Bytes -ne $expected.bytes -or $actual.SHA256 -cne $expected.sha256 -or
           $m.($row[2]) -ne $expected.bytes -or $m.($row[3]) -cne $expected.sha256){throw 'Incoming main/CLI output pin differs.'}
    }
    foreach($row in @(@('IncomingMembers','incoming_image_capture_members.inc'),@('IncomingModule','incoming_image_event_observation.hpp'),
        @('IncomingEntry','native_incoming_image_metadata.inc'),@('IncomingFixture','incoming_image_event_fixture.cpp'))){
        $expected=$c.files.($row[1]);$actual=$p.($row[0])
        if($actual.Path -cne (Join-Path $SourceRoot $row[1]) -or $actual.Bytes -ne $expected.bytes -or $actual.SHA256 -cne $expected.sha256){throw 'Incoming source file pin differs.'}
    }
    foreach($row in @(@('IncomingCapture','derived_capture'),@('IncomingObserver','derived_observer'),@('IncomingBaselineFixture','derived_baseline_fixture'))){
        $expected=$c.($row[1]);$actual=$p.($row[0])
        if($actual.Bytes -ne $expected.bytes -or $actual.SHA256 -cne $expected.sha256){throw 'Incoming derived source pin differs.'}
    }
    # Existing registration stage validator checks the SAME fixed stage/RSP profile,
    # choosing only the explicit new source fixture for this exact incoming marker.
}
function Assert-T7IncomingFixtureOutput([string]$StageRoot,$StageState) {
    $stdout=Join-Path $StageRoot 'stdout.log';$stderr=Join-Path $StageRoot 'stderr.log'
    $expected="IW7_T7_REGISTRATION_HEADER_CHECKS=39`nIW7_T7_INCOMING_IMAGE_CHECKS=48`n"
    if((Get-Item $stdout).Length -gt 128 -or (Get-Item $stderr).Length -ne 0 -or
       ([IO.File]::ReadAllText($stdout)).Replace("`r`n","`n") -cne $expected){throw 'Exactly 39 legacy and 48 incoming actual checks required before main/CLI compilation.'}
    $StageState.LegacyRegistrationChecks=39;$StageState.IncomingChecks=48;$StageState.EngineInvoked=$false
}
function Assert-T7ImageFixtureProof($Profile,$Bindings) {
    foreach($row in @(
        @('ProvenanceSource',15069,'d8b3f07f787f03dbda7c0305e2aad685c131130fbe43a839145e869858925c16'),
        @('ProvenanceEntry',1254,'360bcf806e2d69f3ecba2d2422b99c8c86a775397438117607115ed0d8b5573e'),
        @('ProvenanceFixture',14892,'f123c92c219c6d133882cadda2c8f62967de9bb86f2de0f55d0b468384d5f574'))){
        $api=$Profile.($row[0])
        if(($api.Bytes -isnot [int] -and $api.Bytes -isnot [long]) -or $api.Bytes -ne $row[1] -or
           $api.SHA256 -isnot [string] -or $api.SHA256 -cne $row[2]){throw 'H proof cannot qualify another provenance API source.'}
    }
    $proof=$Profile.FixtureProof
    if((@($proof.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Closure,ExpectedChecks,PreExit,Receipt,Schema,SourceCommit,Stdout' -or
       $proof.Schema -isnot [string] -or $proof.Schema -cne 'iw7.t7-image-fixture-proof/1' -or
       $proof.SourceCommit -isnot [string] -or $proof.SourceCommit -cne '678bf7dde6a99207654256c1e53ebaaec286ffe1' -or
       ($proof.ExpectedChecks -isnot [int] -and $proof.ExpectedChecks -isnot [long]) -or $proof.ExpectedChecks -ne 53){
        throw 'Exact measured H fixture proof required.'
    }
    $root=Split-Path (Split-Path $proof.Receipt.Path -Parent) -Parent
    $rows=@(
        @('Receipt','image-provenance-fixture-h/receipt.local.json',11759,'7e612f958494f52f236dd8a48c3b5d69437eb25ca5fe73036e3b0974243762a6'),
        @('PreExit','image-provenance-fixture-h.preexit.local.json',4479,'c8eebce6a47af7c35f572f8ec4457a8e32d035fb9f577c26467a9ad5e1305e7e'),
        @('Closure','image-provenance-fixture-h.closure.local.json',369,'5203527eed2c6e92575845a57e65aa0d8b6b3f30759e751e64d8e5436b1e75b8'),
        @('Stdout','image-provenance-fixture-h/test.stdout.log',76,'6a704c3d42c843b585a02f93dc12dd82156dce6c7b441cf9374e94bb4e926f8f'))
    $documents=@{}
    foreach($row in $rows){
        $pin=$proof.($row[0]);$expected=Join-Path $root $row[1]
        if((@($pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
           $pin.Path -isnot [string] -or $pin.Path -cne $expected -or
           ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -ne $row[2] -or
           $pin.SHA256 -isnot [string] -or $pin.SHA256 -cne $row[3] -or
           @($Bindings|Where-Object {$_.Path -ceq $pin.Path -and $_.IsText -is [bool] -and $_.IsText -and
               $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256}).Count -ne 1){throw 'Exact finite H proof binding required.'}
        $stream=Open-T7Bootstrap $pin.Path $pin.Bytes $pin.SHA256
        if($row[0] -cne 'Stdout'){
            $reader=[IO.StreamReader]::new($stream,[Text.Encoding]::UTF8,$true,4096,$true)
            try{$documents[$row[0]]=$reader.ReadToEnd()|ConvertFrom-Json -Depth 25}finally{$reader.Dispose()}
        }
    }
    $receipt=$documents.Receipt;$preexit=$documents.PreExit;$closure=$documents.Closure
    if($receipt.SourceCommit -cne $proof.SourceCommit -or $receipt.FixtureSynthetic -isnot [bool] -or !$receipt.FixtureSynthetic -or
       $receipt.EngineInvoked -isnot [bool] -or $receipt.EngineInvoked -or $receipt.Quarantined -isnot [bool] -or $receipt.Quarantined -or
       $receipt.ExpectedChecks -ne 53 -or $receipt.FixtureSHA256 -cne 'c0c60d905c9afcbe70f6dfbab062a3b08a9f49b70aeb37336966ef8a666746cb'){
        throw 'Actual synthetic H source qualification required.'
    }
    foreach($document in @($receipt,$preexit)){
        foreach($name in 'Passed','TreeClosureConfirmed','InputsReverified','LeaseReleased','CompletionPublished'){
            if($document.$name -isnot [bool] -or !$document.$name){throw 'Closed and published H proof required.'}
        }
    }
    if($preexit.SameOriginalAppDomain -isnot [bool] -or !$preexit.SameOriginalAppDomain -or
       $preexit.OwnerClosed -isnot [bool] -or !$preexit.OwnerClosed -or $preexit.CanExit -isnot [bool] -or !$preexit.CanExit -or
       ($preexit.Guards -isnot [int] -and $preexit.Guards -isnot [long]) -or $preexit.Guards -ne 0 -or
       (@($receipt.Phases.Phase)-join ',') -cne 'compile,test' -or
       @($receipt.Phases|Where-Object {($_.ExitCode -isnot [int] -and $_.ExitCode -isnot [long]) -or $_.ExitCode -ne 0 -or
           $_.TreeClosureConfirmed -isnot [bool] -or !$_.TreeClosureConfirmed}).Count){throw 'Actual original H context and phase closure required.'}
    $hostProof=$receipt.Host
    if($preexit.Host.PID -ne $hostProof.PID -or $preexit.Host.CreationFileTime -ne $hostProof.CreationFileTime -or
       $hostProof.ActualHostProof.NoExitVerified -isnot [bool] -or !$hostProof.ActualHostProof.NoExitVerified -or
       $hostProof.ActualHostProof.VerifiedBeforeImportsAndAdmission -isnot [bool] -or !$hostProof.ActualHostProof.VerifiedBeforeImportsAndAdmission -or
       $closure.Passed -isnot [bool] -or !$closure.Passed -or $closure.FixtureExecuted -isnot [bool] -or !$closure.FixtureExecuted -or
       $closure.ExpectedChecks -ne 53 -or (@($closure.PhaseExits)-join ',') -cne '0,0' -or
       $closure.ActualPTYSession -ne 96124 -or $closure.ActualPTYExit -ne 0 -or
       @($closure.RemainingOwn).Count -or @($closure.HeavyProcesses).Count -or @($closure.Leases).Count -or
       $hostProof.PID -notin $closure.ExpectedIDs -or $hostProof.Parent.PID -notin $closure.ExpectedIDs){
        throw 'Actual terminal exit and fresh empty H closure required.'
    }
    return @($rows|ForEach-Object {$proof.($_[0]).Path})
}
function Import-T7BindingsBuildSource($Plan,[string]$SourceRoot) {
    foreach($row in @(@('BindingsBuildContract','registration-bindings-build-source-contract.json',16384),@('BindingsBuildValidator','RegistrationBindingsBuild.Source.ps1',32768))){
        $pin=$Plan.BuildProfile.($row[0])
        if($pin -isnot [pscustomobject] -or (@($pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
           $pin.Path -isnot [string] -or $pin.Path -cne (Join-Path $SourceRoot $row[1]) -or
           ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -le 0 -or $pin.Bytes -gt $row[2] -or
           $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Typed fixed bindings Source bootstrap pin required.'}
        $sealed=@($Plan.Bindings|Where-Object {$_.Path -is [string] -and $_.Path -ceq $pin.Path})
        if($sealed.Count -ne 1 -or ($sealed[0].Bytes -isnot [int] -and $sealed[0].Bytes -isnot [long]) -or
           $sealed[0].SHA256 -isnot [string] -or $sealed[0].Bytes -ne $pin.Bytes -or $sealed[0].SHA256 -cne $pin.SHA256 -or
           $sealed[0].IsText -isnot [bool] -or !$sealed[0].IsText){throw 'Bindings bootstrap must be sealed once as Source text before import.'}
    }
    $contractPin=$Plan.BuildProfile.BindingsBuildContract
    $null=Open-T7Bootstrap $contractPin.Path $contractPin.Bytes $contractPin.SHA256
    $c=Get-Content -LiteralPath $contractPin.Path -Raw|ConvertFrom-Json
    foreach($name in 'producer','source_pins','generated'){if($c.$name -isnot [pscustomobject]){throw 'Non-NULL Source sub-pin group required before helper import.'}}
    $wanted=[Collections.Generic.List[object]]::new();$wanted.Add($c.validator)
    foreach($name in 'producer','source_pins','generated'){foreach($property in $c.$name.PSObject.Properties){$wanted.Add($property.Value)}}
    foreach($expected in $wanted){
        if($expected -isnot [pscustomobject] -or (@($expected.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'bytes,sha256' -or
           ($expected.bytes -isnot [int] -and $expected.bytes -isnot [long]) -or $expected.bytes -le 0 -or $expected.bytes -gt 192KB -or
           $expected.sha256 -isnot [string] -or $expected.sha256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Required typed non-NULL Source sub-pin before helper import.'}
    }
    $pin=$Plan.BuildProfile.BindingsBuildValidator
    if($pin.Bytes -ne $c.validator.bytes -or $pin.SHA256 -cne $c.validator.sha256){throw 'Helper Source pin differs before import.'}
    $null=Open-T7Bootstrap $pin.Path $pin.Bytes $pin.SHA256
    . $pin.Path # Both original Source guards stay held; no helper runs before sub-pin checks.
}
function Assert-T7BuildProfile($Plan,[string]$SourceRoot) {
    $profile=if($Plan.PSObject.Properties.Name -contains 'BuildProfile'){$Plan.BuildProfile}else{$null}
    $recompiled=$Plan.PSObject.Properties.Name -contains 'ReuseCompile' -and $null -ne $Plan.ReuseCompile -and
        $Plan.ReuseCompile.PSObject.Properties.Name -contains 'RecompiledMain' -and
        $Plan.ReuseCompile.RecompiledMain -is [bool] -and $Plan.ReuseCompile.RecompiledMain
    $cliMarker=$Plan.PSObject.Properties.Name -contains 'ReuseCompile' -and $null -ne $Plan.ReuseCompile -and
        $Plan.ReuseCompile.PSObject.Properties.Name -contains 'RecompiledZonetool'
    $zombies=$null -ne $profile -and $profile.Name -ceq 't7-zombies-catalogue-observation-c'
    $add=$null -ne $profile -and $profile.Name -ceq 't7-zombies-catalogue-observation-c2'
    $reference=$null -ne $profile -and $profile.Name -ceq 't7-prepatch-reference-v2'
    $link=$null -ne $profile -and $profile.Name -ceq 't7-prepatch-link-v3'
    $linkMarker=$null -ne $Plan.PSObject.Properties['ReuseCompile'] -and $null -ne $Plan.ReuseCompile -and $null -ne $Plan.ReuseCompile.PSObject.Properties['PrepatchLinkV3']
    if($link -ne $linkMarker){throw 'Prepatch V3 profile and marker must be paired.'}
    $parts=$null -ne $profile -and $profile.Name -ceq 't7-material-parts-v1'
    $partsMarker=$null -ne $Plan.PSObject.Properties['ReuseCompile'] -and $null -ne $Plan.ReuseCompile -and $null -ne $Plan.ReuseCompile.PSObject.Properties['MaterialParts']
    if($parts -ne $partsMarker){throw 'Parts profile and finite transition must be paired.'}
    $incoming=$null -ne $profile -and $profile.Name -ceq 't7-incoming-image-header-observation-v1'
    $incomingMarker=$null -ne $Plan.PSObject.Properties['ReuseCompile'] -and $null -ne $Plan.ReuseCompile -and $null -ne $Plan.ReuseCompile.PSObject.Properties['IncomingObservation']
    if($incoming -ne $incomingMarker){throw 'Incoming profile and source transition must be paired.'}
    $registrationBindings=$null -ne $profile -and $profile.Name -ceq 't7-registration-material-bindings-v1'
    $bindingsMarker=$null -ne $Plan.PSObject.Properties['ReuseCompile'] -and $null -ne $Plan.ReuseCompile -and $null -ne $Plan.ReuseCompile.PSObject.Properties['RegistrationBindingsObservation']
    if($registrationBindings -ne $bindingsMarker -or ($registrationBindings -and $incomingMarker)){throw 'Exclusive bindings profile and source transition must be paired.'}
    $registration=$null -ne $profile -and $profile.Name -cin @('t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1')
    $registrationMarker=$null -ne $Plan.PSObject.Properties['ReuseCompile'] -and $null -ne $Plan.ReuseCompile -and $null -ne $Plan.ReuseCompile.PSObject.Properties['RegistrationMetadata']
    if($registration -ne $registrationMarker){throw 'Registration profile and finite marker must be paired.'}
    $provenance=$null -ne $profile -and $profile.Name -cin @('t7-image-provenance-v1','t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1')
    $provenanceMarker=$null -ne $Plan.PSObject.Properties['ReuseCompile'] -and $null -ne $Plan.ReuseCompile -and $null -ne $Plan.ReuseCompile.PSObject.Properties['ImageProvenance']
    if($provenance -ne $provenanceMarker -or ($provenance -and $partsMarker)){throw 'Exclusive provenance profile and finite transition must be paired.'}
    $metadata=$null -ne $Plan.PSObject.Properties['ReuseCompile'] -and $null -ne $Plan.ReuseCompile -and $null -ne $Plan.ReuseCompile.PSObject.Properties['ImageMetadata']
    if($metadata -and !$provenance){throw 'Metadata extension requires the provenance profile.'}
    if($registration -and !$metadata){throw 'Registration requires the exact metadata base.'}
    if($provenance){
        foreach($name in 'ZombiesObservationC','ZombiesAddObservationC2','PrepatchReferenceV2','PrepatchLinkV3','ResidentSurfaceCountDiagnostic','SelectedStreamedStaticV1'){
            if($Plan.ReuseCompile.PSObject.Properties[$name]){throw 'Provenance cannot mix other observation/export markers.'}
        }
    }
    $referenceMarker=$null -ne $Plan.PSObject.Properties['ReuseCompile'] -and $null -ne $Plan.ReuseCompile -and $null -ne $Plan.ReuseCompile.PSObject.Properties['PrepatchReferenceV2']
    if($reference -ne $referenceMarker){throw 'Prepatch V2 profile and marker must be paired.'}
    $publication=$null -ne $profile -and $profile.Name -cin @('t7-catalog-message-publication','t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2','t7-material-parts-v1','t7-image-provenance-v1','t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1')
    if($cliMarker -and !$publication){throw 'CLI rebuild marker requires the publication profile.'}
    if($publication -and (!$cliMarker -or $Plan.ReuseCompile.RecompiledZonetool -isnot [bool] -or
        !$Plan.ReuseCompile.RecompiledZonetool)){throw 'Publication requires both fresh translation units.'}
    if($null -eq $profile) {
        if($recompiled){throw 'Recompiled main requires the explicit diagnostic profile.'}
        return $false
    }
    if(!$recompiled){throw 'Explicit profile requires a main rebuild.'}
    if($profile.Name -ceq 't7-prepatch-probe') {
        if($profile.Option -cne '-t7-prepatch-probe' -or $profile.ArgumentCount -ne 2 -or
           $profile.Report -cne 't7-prepatch-probe.local.json'){throw 'Exact pre-patch profile required.'}
        $paths=@{
            Helper=(Join-Path $Plan.PreparedRoot 'native_prepatch_probe.inc')
            Wiring=(Join-Path $SourceRoot 'prepare_prepatch.py')
            PreparedMain=(Join-Path $Plan.PreparedRoot 'main.cpp')
        }
    } elseif($link) {
        foreach($name in 'Name','Option','Report','ObservationSchema') {
            if($profile.$name -isnot [string]){throw "Prepatch V3 text scalar required: profile.$name"}
        }
        foreach($name in 'SourcePlan','Receipt','SourcePlanSHA256','ReceiptSHA256') {
            if($Plan.ReuseCompile.$name -isnot [string]){throw "Prepatch V3 text scalar required: reuse.$name"}
        }
        if((@($profile.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'ArgumentCount,BaseBuildPlan,BaseBuildReceipt,BaseHelper,BaseV2BuildPlan,BaseV2Main,BaseWiring,Helper,Name,ObservationSchema,Option,PreparedMain,Report,Wiring' -or
           $profile.Option -cne '-t7-prepatch-link-v3' -or $profile.ArgumentCount -ne 2 -or
           ($profile.ArgumentCount -isnot [int] -and $profile.ArgumentCount -isnot [long]) -or
           $profile.Report -cne 't7-prepatch-link-v3.local.json' -or $profile.ObservationSchema -cne 'iw7.t7-prepatch-link-observation/3' -or
           $Plan.SourceCommit -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or (@($Plan.Stages.Name)-join ',') -cne 'main,link'){
            throw 'Exact three-row prepatch V3 main/link profile required.'
        }
        foreach($name in 'RecompiledZonetool','ResidentMultiSurfaceV2','SelectedStreamedStaticV1','SelectedStreamedRenderOnlyV2','ZombiesObservationC','ZombiesAddObservationC2','ResidentSurfaceCountDiagnostic','MaterialParts','ImageProvenance','PrepatchReferenceV2'){
            if($Plan.ReuseCompile.PSObject.Properties[$name]){throw 'Prepatch V3 cannot mix diagnostic/export markers.'}
        }
        $marker=$Plan.ReuseCompile.PrepatchLinkV3
        if((@($marker.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'BaseMainBytes,BaseMainSHA256,HelperBytes,HelperSHA256,MainBytes,MainSHA256,RetainedMainBytes,RetainedMainSHA256,Schema,SourceProfile'){
            throw 'Exact prepatch V3 marker fields required.'
        }
        foreach($name in 'Schema','SourceProfile','BaseMainSHA256','MainSHA256','RetainedMainSHA256','HelperSHA256'){
            if($marker.$name -isnot [string]){throw "Prepatch V3 text scalar required: marker.$name"}
        }
        foreach($name in 'BaseMainBytes','MainBytes','RetainedMainBytes','HelperBytes'){
            if($marker.$name -isnot [int] -and $marker.$name -isnot [long]){throw 'Prepatch V3 integer lengths required.'}
        }
        if($marker.Schema -cne 'iw7.t7-prepatch-link-build/3' -or $marker.SourceProfile -cne 't7-prepatch-link-v3' -or
           $marker.RetainedMainBytes -ne 12854 -or $marker.RetainedMainSHA256 -cne '40de5fda829cec32a5d75359f58e69c84db7d8ee54f198cf6befa2a6ebe6f86e' -or
           $marker.BaseMainBytes -ne 14524 -or $marker.BaseMainSHA256 -cne 'e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28' -or
           $marker.MainBytes -ne 14469 -or $marker.MainSHA256 -cne '84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989' -or
           $marker.HelperBytes -ne 15827 -or $marker.HelperSHA256 -cne 'cf839e18a68adb4ed3aae82d683ef110ab595fa8c172584e47ca4d11bb8db48d'){
            throw 'Exact prepatch V3 source transition required.'
        }
        $paths=@{
            Helper=(Join-Path $Plan.PreparedRoot 'native_prepatch_link_v3.inc');Wiring=(Join-Path $SourceRoot 'prepare_prepatch_link_v3.py')
            BaseHelper=(Join-Path $SourceRoot 'native_prepatch_reference_v2.inc');BaseWiring=(Join-Path $SourceRoot 'prepare_prepatch_reference.py')
            BaseBuildPlan=$Plan.ReuseCompile.SourcePlan;BaseBuildReceipt=$Plan.ReuseCompile.Receipt
            BaseV2BuildPlan=$profile.BaseV2BuildPlan.Path
            BaseV2Main=(Join-Path (Split-Path $profile.BaseV2BuildPlan.Path -Parent) 'prepared/main.cpp')
            PreparedMain=(Join-Path $Plan.PreparedRoot 'main.cpp')
        }
        $expected=@{
            Helper=@(15827,'cf839e18a68adb4ed3aae82d683ef110ab595fa8c172584e47ca4d11bb8db48d')
            Wiring=@(2236,'66f70ca5a979745288232d76496a339e08d639ddf34560aada6e6b63c5bcffa1')
            BaseHelper=@(15785,'0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a')
            BaseWiring=@(3665,'89f3f26699f1240400c4bd96f2987963374658e55a8501cab7dc2543a84ceace')
            BaseBuildPlan=@(292575,'422e79898fa2b16defc8193182fe146e2db5d73aeb4516c2bd2aaf87c409c4de')
            BaseBuildReceipt=@(26199,'af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897')
            BaseV2BuildPlan=@(303783,'0aca63cb09e8ecfc96dee34e1fdf94f8cb66e400f8a190ffdefd38bec3a2c549')
            BaseV2Main=@(14524,'e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28')
            PreparedMain=@(14469,'84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989')
        }
        if($Plan.ReuseCompile.SourcePlanSHA256 -cne $expected.BaseBuildPlan[1] -or $Plan.ReuseCompile.ReceiptSHA256 -cne $expected.BaseBuildReceipt[1]){
            throw 'Frozen C compilation evidence required for V3.'
        }
        foreach($name in $paths.Keys){
            $pin=$profile.$name
            if($pin.Path -isnot [string] -or $pin.SHA256 -isnot [string] -or ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long])){throw 'Prepatch V3 typed source pin required.'}
            if((@($pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or $pin.Bytes -ne $expected[$name][0] -or $pin.SHA256 -cne $expected[$name][1]){
                throw 'Frozen prepatch V3 text pin differs.'
            }
        }
    } elseif($reference) {
        foreach($name in 'Name','Option','Report','ObservationSchema') {
            if($profile.$name -isnot [string]){throw "Prepatch V2 text scalar required: profile.$name"}
        }
        foreach($name in 'SourcePlan','Receipt','SourcePlanSHA256','ReceiptSHA256') {
            if($Plan.ReuseCompile.$name -isnot [string]){throw "Prepatch V2 text scalar required: reuse.$name"}
        }
        if((@($profile.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'ArgumentCount,BaseBuildPlan,BaseBuildReceipt,BaseHelper,BaseWiring,Helper,Name,ObservationSchema,Option,PreparedMain,Report,Wiring' -or
           $profile.Option -cne '-t7-prepatch-reference-v2' -or $profile.ArgumentCount -ne 2 -or
           ($profile.ArgumentCount -isnot [int] -and $profile.ArgumentCount -isnot [long]) -or
           $profile.Report -cne 't7-prepatch-reference-v2.local.json' -or
           $profile.ObservationSchema -cne 'iw7.t7-prepatch-reference-observation/2' -or
           $Plan.SourceCommit -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
           (@($Plan.Stages.Name)-join ',') -cne 'main,link'){throw 'Exact two-function prepatch V2 profile required.'}
        foreach($other in 'RecompiledZonetool','ResidentMultiSurfaceV2','SelectedStreamedStaticV1','SelectedStreamedRenderOnlyV2','ZombiesObservationC','ZombiesAddObservationC2','ResidentSurfaceCountDiagnostic') {
            if($Plan.ReuseCompile.PSObject.Properties[$other]){throw 'Prepatch V2 cannot mix with CLI/catalogue/export markers.'}
        }
        $marker=$Plan.ReuseCompile.PrepatchReferenceV2
        foreach($name in 'Schema','SourceProfile','BaseMainSHA256','MainSHA256','RetainedMainSHA256','HelperSHA256') {
            if($marker.$name -isnot [string]){throw "Prepatch V2 text scalar required: marker.$name"}
        }
        if((@($marker.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'BaseMainBytes,BaseMainSHA256,HelperBytes,HelperSHA256,MainBytes,MainSHA256,RetainedMainBytes,RetainedMainSHA256,Schema,SourceProfile' -or
           $marker.Schema -cne 'iw7.t7-prepatch-reference-build/2' -or $marker.SourceProfile -cne 't7-prepatch-reference-v2' -or
           $marker.BaseMainBytes -ne 13160 -or $marker.BaseMainSHA256 -cne '55081db20863f291f4f1fea8c1c995995e5e548b56acf043201fbb2e361f3934' -or
           $marker.RetainedMainBytes -ne 12854 -or $marker.RetainedMainSHA256 -cne '40de5fda829cec32a5d75359f58e69c84db7d8ee54f198cf6befa2a6ebe6f86e' -or
           $marker.MainBytes -ne 14524 -or $marker.MainSHA256 -cne 'e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28' -or
           $marker.HelperBytes -ne 15785 -or $marker.HelperSHA256 -cne '0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a') {throw 'Exact prepatch V2 source transition required.'}
        foreach($name in 'BaseMainBytes','MainBytes','HelperBytes','RetainedMainBytes') {
            if($marker.$name -isnot [int] -and $marker.$name -isnot [long]){throw 'Prepatch V2 integer lengths required.'}
        }
        $paths=@{
            Helper=(Join-Path $Plan.PreparedRoot 'native_prepatch_reference_v2.inc')
            Wiring=(Join-Path $SourceRoot 'prepare_prepatch_reference.py')
            BaseHelper=(Join-Path $SourceRoot 'native_prepatch_probe.inc')
            BaseWiring=(Join-Path $SourceRoot 'prepare_prepatch.py')
            BaseBuildPlan=$Plan.ReuseCompile.SourcePlan
            BaseBuildReceipt=$Plan.ReuseCompile.Receipt
            PreparedMain=(Join-Path $Plan.PreparedRoot 'main.cpp')
        }
        $expected=@{
            Helper=@(15785,'0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a')
            Wiring=@(3665,'89f3f26699f1240400c4bd96f2987963374658e55a8501cab7dc2543a84ceace')
            BaseHelper=@(16281,'a9f458d2783c845af6958c896bda07fa4b92a5ea23a14c9e5d1201fe234a2018')
            BaseWiring=@(3078,'162763ab503a7971bc56753e3aba9fc1c76bf181881f9bddf45718456467e129')
            PreparedMain=@(14524,'e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28')
            BaseBuildPlan=@(292575,'422e79898fa2b16defc8193182fe146e2db5d73aeb4516c2bd2aaf87c409c4de')
            BaseBuildReceipt=@(26199,'af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897')
        }
        if($Plan.ReuseCompile.SourcePlanSHA256 -cne $expected.BaseBuildPlan[1] -or
           $Plan.ReuseCompile.ReceiptSHA256 -cne $expected.BaseBuildReceipt[1]){throw 'Frozen C compilation evidence required for V2.'}
        foreach($name in $paths.Keys) {
            foreach($field in 'Path','SHA256') {
                if($profile.$name.$field -isnot [string]){throw "Prepatch V2 text scalar required: pin.$name.$field"}
            }
            if($profile.$name.Bytes -isnot [int] -and $profile.$name.Bytes -isnot [long]){throw 'Prepatch V2 integer pin length required.'}
            if((@($profile.$name.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
               $profile.$name.Bytes -ne $expected[$name][0] -or $profile.$name.SHA256 -cne $expected[$name][1]){throw 'Frozen prepatch V2 text pin differs.'}
        }
    } elseif($profile.Name -cin @('t7-catalog-trace','t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2','t7-material-parts-v1','t7-image-provenance-v1','t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1')) {
        $fields='ArgumentCount,BaseBuildPlan,BaseBuildReceipt,Name,Option,PreparedMain,TraceSchema,Wiring'
        if($profile.Name -cin @('t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2','t7-material-parts-v1','t7-image-provenance-v1','t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1')) {
            if($profile.ContextSchema -cne 'iw7.t7-catalog-exit-context/1'){throw 'Exact exit-context schema required.'}
            $fields='ArgumentCount,BaseBuildPlan,BaseBuildReceipt,ContextSchema,Name,Option,PreparedMain,TraceSchema,Wiring'
        }
        if($profile.Name -cin @('t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2','t7-material-parts-v1','t7-image-provenance-v1','t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1')) {
            if($profile.CallerSchema -cne 'iw7.t7-catalog-callers/1'){throw 'Exact caller schema required.'}
            $fields='ArgumentCount,BaseBuildPlan,BaseBuildReceipt,CallerSchema,ContextSchema,Name,Option,PreparedMain,TraceSchema,Wiring'
        }
        if($profile.Name -cin @('t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2','t7-material-parts-v1','t7-image-provenance-v1','t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1')) {
            if($profile.MessageSchema -cne 'iw7.t7-catalog-message/1'){throw 'Exact message schema required.'}
            $fields='ArgumentCount,BaseBuildPlan,BaseBuildReceipt,CallerSchema,ContextSchema,MessageSchema,Name,Option,PreparedMain,TraceSchema,Wiring'
        }
        if($publication) {
            if($profile.PublicationSchema -cne 'iw7.t7-message-publication-build/1') {throw 'Exact publication build schema required.'}
            $fields=(@($fields.Split(','))+@('PublicationSchema','PublicationWiring','PublicationSource','PreparedCLI',
                'MainResponse','CLIResponse','LinkResponse')|Sort-Object)-join ','
            $expectedOrder=if($registration){'registration-fixture-compile,registration-fixture-test,main,zonetool11,link'}elseif($metadata){'metadata-fixture-compile,metadata-fixture-test,main,zonetool11,link'}else{'main,zonetool11,link'}
            if((@($Plan.Stages.Name)-join ',') -cne $expectedOrder) {throw 'Publication requires its exact fixture/main/CLI/link order.'}
        }
        if($zombies) {
            if($profile.ObservationSchema -cne 'iw7.t7-zm-observation/1' -or
               !$Plan.ReuseCompile.PSObject.Properties['ZombiesObservationC']){throw 'Explicit Zombies observation source marker required.'}
            $fields=(@($fields.Split(','))+@('ObservationSchema','ObserverSource','ObserverAdapter')|Sort-Object)-join ','
        }
        if($add) {
            if($profile.ObservationSchema -cne 'iw7.t7-zm-add-observation/1' -or
               !$Plan.ReuseCompile.PSObject.Properties['ZombiesAddObservationC2']){throw 'Explicit C2 source marker required.'}
            $fields=(@($fields.Split(','))+@('ObservationSchema','ObserverSource','ObserverAdapter')|Sort-Object)-join ','
        }
        if($parts){
            if($profile.Option -isnot [string] -or $profile.Option -cne '-t7-iw7-material-parts-v1' -or
               ($profile.ArgumentCount -isnot [int] -and $profile.ArgumentCount -isnot [long]) -or
               $profile.ArgumentCount -ne 5 -or $profile.ObservationSchema -isnot [string] -or
               $profile.ObservationSchema -cne 'iw7.t7-selected-material-observation/3') {throw 'Exact metadata-only parts option/schema required.'}
            $fields=(@($fields.Split(','))+@('ObservationSchema','PartsWiring','PartsSource','PartsEntry','PartsContract','PartsFixture')|Sort-Object)-join ','
            Assert-T7MaterialPartsTransition $Plan $SourceRoot
        }
        if($provenance){
            if($profile.Option -isnot [string] -or $profile.Option -cne $(if($registrationBindings){'-t7-iw7-registration-material-bindings-v1'}elseif($incoming){'-t7-iw7-incoming-image-header-v1'}elseif($registration){'-t7-iw7-image-registration-metadata-v1'}else{'-t7-iw7-image-provenance-v1'}) -or
               ($profile.ArgumentCount -isnot [int] -and $profile.ArgumentCount -isnot [long]) -or $profile.ArgumentCount -ne 5 -or
               $profile.ObservationSchema -isnot [string] -or $profile.ObservationSchema -cne $(if($registrationBindings){'iw7.t7-registration-material-bindings/1'}elseif($incoming){'iw7.t7-incoming-image-header-observation/1'}elseif($registration){'iw7.t7-registration-image-header-metadata/1'}else{'iw7.t7-selected-image-provenance/1'}) -or
               $profile.SourceOnlyPending -isnot [bool]){throw 'Exact source-pending provenance profile required.'}
            $fields=(@($fields.Split(','))+@('ObservationSchema','ProvenanceBaseWiring','ProvenanceWiring','ProvenanceSource','ProvenanceEntry','ProvenanceContract','ProvenanceFixture','SourceOnlyPending')|Sort-Object)-join ','
            if(!$profile.SourceOnlyPending){
                if(!$profile.PSObject.Properties['FixtureProof']){throw 'Measured H proof required before enabling CPP.'}
                $null=Assert-T7ImageFixtureProof $profile $Plan.Bindings
                $fields=(@($fields.Split(','))+@('FixtureProof')|Sort-Object)-join ','
            }elseif($profile.PSObject.Properties['FixtureProof']){throw 'Pending provenance cannot claim a fixture qualification.'}
            Assert-T7ImageProvenanceTransition $Plan $SourceRoot
            if($metadata){
                $fields=(@($fields.Split(','))+@('MetadataSchema','MetadataOption','MetadataWiring','MetadataContract','MetadataPartsSource','MetadataBuilder','MetadataBuilderFixture','MetadataSource','MetadataEntry','MetadataReadGuard',
                    'MetadataGuardFixture','MetadataGuardedObserver','MetadataFixtureResponse','MetadataFixtureNativeRoot','MetadataMapperChecks','MetadataGuardChecks')|Sort-Object)-join ','
                Assert-T7ImageMetadataTransition $Plan $SourceRoot
            }
            if($registration){
                $fields=(@($fields.Split(','))+@('RegistrationSchema','RegistrationFixtureChecks','RegistrationCPPQualified',
                    'RegistrationWiring','RegistrationContract','RegistrationCapture','RegistrationEntry','RegistrationFixture','RegistrationObserver','RegistrationResponse')|Sort-Object)-join ','
                Assert-T7RegistrationMetadataTransition $Plan $SourceRoot
            }
            if($incoming){
                $fields=(@($fields.Split(','))+@('IncomingSchema','IncomingFixtureChecks','IncomingCPPQualified',
                    'IncomingWiring','IncomingContract','IncomingMembers','IncomingModule','IncomingEntry','IncomingFixture','IncomingCapture','IncomingObserver','IncomingBaselineFixture')|Sort-Object)-join ','
                Assert-T7IncomingMetadataTransition $Plan $SourceRoot
            }
            if($registrationBindings){
                Import-T7BindingsBuildSource $Plan $SourceRoot
                Assert-T7BindingsBuildTransition $Plan $SourceRoot
                $fields=(@($fields.Split(','))+@(Get-T7BindingsBuildFields)|Sort-Object)-join ','
            }
        }
        if($profile.Option -cne $(if($registrationBindings){'-t7-iw7-registration-material-bindings-v1'}elseif($incoming){'-t7-iw7-incoming-image-header-v1'}elseif($registration){'-t7-iw7-image-registration-metadata-v1'}elseif($provenance){'-t7-iw7-image-provenance-v1'}elseif($parts){'-t7-iw7-material-parts-v1'}else{'-t7-iw7-catalog'}) -or
           $profile.ArgumentCount -ne $(if($parts -or $provenance){5}else{3}) -or
           $profile.TraceSchema -cne 'iw7.t7-catalog-trace/1' -or
           (@($profile.PSObject.Properties.Name|Sort-Object)-join ',') -cne $fields -or
           $profile.BaseBuildPlan.SHA256 -cne 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa' -or
           $profile.BaseBuildReceipt.SHA256 -cne 'c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2'){
            throw 'Exact catalogue trace profile and ordinary D2 proof required.'
        }
        $paths=@{
            Wiring=(Join-Path $SourceRoot 'prepare_catalog_trace.py')
            PreparedMain=(Join-Path $Plan.PreparedRoot 'main.cpp')
            BaseBuildPlan=$profile.BaseBuildPlan.Path
            BaseBuildReceipt=$profile.BaseBuildReceipt.Path
        }
        if($publication) {
            $responseRoot=Split-Path $Plan.PreparedRoot -Parent
            $paths.PublicationWiring=Join-Path $SourceRoot 'prepare_message_publication.py'
            $paths.PublicationSource=Join-Path $SourceRoot 'native_message_publication.inc'
            $paths.PreparedCLI=Join-Path $Plan.PreparedRoot 'zonetool.cpp'
            $paths.MainResponse=Join-Path $responseRoot 'main.obj.rsp'
            $paths.CLIResponse=Join-Path $responseRoot 'zonetool11.obj.rsp'
            $paths.LinkResponse=Join-Path $responseRoot 'link.rsp'
            foreach($row in @(@('main','MainResponse'),@('zonetool11','CLIResponse'),@('link','LinkResponse'))) {
                $stage=@($Plan.Stages|Where-Object Name -CEQ $row[0])[0]
                if(@($stage.Arguments).Count -ne 1 -or $stage.Arguments[0] -cne ('@'+$paths[$row[1]])) {
                    throw 'Publication stage must use its pinned response file.'
                }
                $image=if($row[0] -ceq 'link'){Join-Path (Split-Path $Plan.Compiler -Parent) 'link.exe'}else{$Plan.Compiler}
                if($stage.Image -cne $image){throw 'Publication stage image differs.'}
                $artifacts=@(if($row[0] -ceq 'link'){'zonetool-t7.exe','zonetool-t7.pdb','zonetool-t7.lib','zonetool-t7.exp'}
                    else{($row[0]+'.obj'),'compile.pdb','dependencies.json'})
                if((@($stage.Artifacts)-join ',') -cne ($artifacts-join ',')) {throw 'Publication stage artifact guards differ.'}
            }
        }
        if($zombies) {
            $paths.ObserverSource=Join-Path $SourceRoot 'native_catalog_zombies_observation.inc'
            $paths.ObserverAdapter=Join-Path $SourceRoot 'prepare_catalog_zombies_observation.py'
        }
        if($add) {
            $paths.ObserverSource=Join-Path $SourceRoot 'native_catalog_add_observation.inc'
            $paths.ObserverAdapter=Join-Path $SourceRoot 'prepare_catalog_add_observation.py'
        }
        if($parts){
            $paths.PartsWiring=Join-Path $SourceRoot 'prepare_material_parts.py'
            $paths.PartsSource=Join-Path $SourceRoot 'selected_material_parts_observation.hpp'
            $paths.PartsEntry=Join-Path $SourceRoot 'native_material_parts.inc'
            $paths.PartsContract=Join-Path $SourceRoot 'material-parts-source-contract.json'
            $paths.PartsFixture=Join-Path $SourceRoot 'selected_material_parts_observation_fixture.cpp'
        }
        if($provenance){
            $paths.ProvenanceBaseWiring=Join-Path $SourceRoot 'prepare_material_parts.py'
            $paths.ProvenanceWiring=Join-Path $SourceRoot 'prepare_image_provenance.py'
            $paths.ProvenanceSource=Join-Path $SourceRoot 'selected_image_provenance.hpp'
            $paths.ProvenanceEntry=Join-Path $SourceRoot 'native_image_provenance.inc'
            $paths.ProvenanceContract=Join-Path $SourceRoot 'image-provenance-source-contract.json'
            $paths.ProvenanceFixture=Join-Path $SourceRoot 'selected_image_provenance_fixture.cpp'
            if($metadata){
                $paths.MetadataWiring=Join-Path $SourceRoot 'prepare_image_metadata.py'
                $paths.MetadataContract=Join-Path $SourceRoot 'image-metadata-source-contract.json'
                $paths.MetadataPartsSource=Join-Path $SourceRoot 'selected_material_parts_observation.hpp'
                $paths.MetadataBuilder=Join-Path $SourceRoot 'selected_image_header_metadata.hpp'
                $paths.MetadataBuilderFixture=Join-Path $SourceRoot 'selected_image_header_metadata_fixture.cpp'
                $paths.MetadataReadGuard=Join-Path $SourceRoot 'selected_image_metadata_read_guard.hpp'
                $paths.MetadataGuardFixture=Join-Path $SourceRoot 'selected_image_metadata_guard_fixture.cpp'
                $paths.MetadataGuardedObserver=Join-Path $Plan.PreparedRoot 'selected_material_metadata_guarded.hpp'
                $paths.MetadataFixtureResponse=Join-Path (Split-Path $Plan.PreparedRoot -Parent) 'metadata-fixture.rsp'
                $paths.MetadataSource=Join-Path $SourceRoot 'selected_image_metadata.hpp'
                $paths.MetadataEntry=Join-Path $SourceRoot 'native_image_metadata.inc'
            }
            if($registration){
                $paths.RegistrationWiring=Join-Path $SourceRoot 'prepare_image_registration_metadata.py'
                $paths.RegistrationContract=Join-Path $SourceRoot 'registration-image-metadata-source-contract.json'
                $paths.RegistrationCapture=Join-Path $SourceRoot 'registration_image_header_capture.hpp'
                $paths.RegistrationEntry=Join-Path $SourceRoot 'native_image_registration_metadata.inc'
                $paths.RegistrationFixture=Join-Path $SourceRoot 'registration_image_header_fixture.cpp'
                $paths.RegistrationObserver=Join-Path $Plan.PreparedRoot 'selected_image_registration_observer.hpp'
                $paths.RegistrationResponse=Join-Path (Split-Path $Plan.PreparedRoot -Parent) 'registration-fixture.rsp'
            }
            if($incoming){
                $paths.IncomingWiring=Join-Path $SourceRoot 'prepare_incoming_image_metadata.py'
                $paths.IncomingContract=Join-Path $SourceRoot 'incoming-image-source-contract.json'
                $paths.IncomingMembers=Join-Path $SourceRoot 'incoming_image_capture_members.inc'
                $paths.IncomingModule=Join-Path $SourceRoot 'incoming_image_event_observation.hpp'
                $paths.IncomingEntry=Join-Path $SourceRoot 'native_incoming_image_metadata.inc'
                $paths.IncomingFixture=Join-Path $SourceRoot 'incoming_image_event_fixture.cpp'
                $paths.IncomingCapture=Join-Path $Plan.PreparedRoot 'selected_image_incoming_capture.hpp'
                $paths.IncomingObserver=Join-Path $Plan.PreparedRoot 'selected_image_incoming_observer.hpp'
                $paths.IncomingBaselineFixture=Join-Path $Plan.PreparedRoot 'incoming_registration_baseline_fixture.cpp'
            }
        }
    } else {
        throw 'Unknown T7 build profile.'
    }
    foreach($name in $paths.Keys) {
        $pin=$profile.$name
        $limit=if($name -ceq 'BaseBuildPlan' -or ($link -and $name -ceq 'BaseV2BuildPlan')){2MB}elseif($name -ceq 'BaseBuildReceipt'){128KB}
               elseif($name -ceq 'LinkResponse'){256KB}elseif($name -ceq 'PublicationSource'){16KB}
               elseif($name -ceq 'PreparedCLI' -and $registration){192KB}
               elseif($name -ceq 'PreparedCLI' -and $metadata){160KB}
               elseif($name -ceq 'PreparedCLI' -and $Plan.ReuseCompile.PSObject.Properties.Name -contains 'SelectedStreamedRenderOnlyV2' -and
                   $Plan.ReuseCompile.SelectedStreamedRenderOnlyV2.Schema -ceq 'iw7.t7-selected-streamed-render-only-build/2' -and
                   $Plan.ReuseCompile.SelectedStreamedRenderOnlyV2.GeometryProfile -ceq 't7-iw7-selected-streamed-render-only-v2' -and
                   $Plan.ReuseCompile.SelectedStreamedRenderOnlyV2.CollisionPolicy -ceq 'omit-source-rigid-collision-trees'){128KB}
               elseif($name -ceq 'PreparedCLI' -and $Plan.ReuseCompile.PSObject.Properties.Name -contains 'SelectedStreamedStaticV1' -and
                   $Plan.ReuseCompile.SelectedStreamedStaticV1.Schema -ceq 'iw7.t7-selected-streamed-static-build/1' -and
                   $Plan.ReuseCompile.SelectedStreamedStaticV1.GeometryProfile -ceq 't7-iw7-selected-streamed-static-v1'){128KB}else{64KB}
        if($pin.Path -cne $paths[$name] -or $pin.Bytes -le 0 -or $pin.Bytes -gt $limit -or
           $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Diagnostic source pin differs.'}
        $match=@($Plan.Bindings|Where-Object {$_.Path -ceq $pin.Path -and $_.IsText -is [bool] -and $_.IsText -and
            $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256})
        if($match.Count -ne 1){throw 'Diagnostic source pin is not guarded by the build.'}
    }
    return $true
}
function Assert-T7OSResourceContext($Plan) {
    $tz='C:\WINDOWS\SYSTEM32\TZRES.DLL'
    $old='f3f5ef83a67c503991d728f62cf039cbb52a18d6eb82197dec23ede8f0996108'
    $new='1398cf1d866e49a8ba351e2a30a7803b50c8b595d17f776abe8d2ec4a9c6fb10'
    $inputs=@($Plan.Inputs|Where-Object {$_.Path -eq $tz})
    if(!$Plan.PSObject.Properties['OSResourceContext']){
        if($inputs.Count -gt 1 -or ($inputs.Count -eq 1 -and ($inputs[0].Path -isnot [string] -or $inputs[0].Path -cne $tz -or
           ($inputs[0].Bytes -isnot [int] -and $inputs[0].Bytes -isnot [long]) -or
           $inputs[0].Bytes -ne 12288 -or $inputs[0].SHA256 -isnot [string] -or $inputs[0].SHA256 -cne $old))){throw 'Historical OS pin requires an explicit qualified context.'}
        return $null
    }
    $context=$Plan.OSResourceContext
    if($null -eq $context -or $Plan.BuildProfile.Name -isnot [string] -or $Plan.BuildProfile.Name -cnotin @('t7-material-parts-v1','t7-prepatch-link-v3','t7-image-provenance-v1','t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1') -or
       (@($context.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'After,Before,Evidence,KBFileAttributionVerified,Name,ProductVersion,Schema,SignatureStatus,SignatureType,SignerThumbprint,SourceOSDate'){
        throw 'Exact opt-in OS context fields/profile required.'
    }
    $texts=@{Schema='iw7.t7-os-resource-context/1';Name='windows-tzres-20261014';SourceOSDate='2026-10-14';
        ProductVersion='10.0.26100.9711';SignatureStatus='Valid';SignatureType='Catalog';SignerThumbprint='667BBA1E1F478221AA65DE4F75187A751B03A453'}
    foreach($name in $texts.Keys){if($context.$name -isnot [string] -or $context.$name -cne $texts[$name]){throw 'Exact dated Microsoft OS context required.'}}
    if($context.KBFileAttributionVerified -isnot [bool] -or $context.KBFileAttributionVerified){throw 'Unproven KB attribution must remain false.'}
    foreach($row in @(@('Before',$old),@('After',$new))){
        $pin=$context.($row[0])
        if((@($pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
           $pin.Path -isnot [string] -or $pin.Path -cne $tz -or
           ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -ne 12288 -or
           $pin.SHA256 -isnot [string] -or $pin.SHA256 -cne $row[1]){throw 'Exact single TZRES transition required.'}
    }
    $proof=$context.Evidence
    if((@($proof.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
       $proof.Path -isnot [string] -or ($proof.Bytes -isnot [int] -and $proof.Bytes -isnot [long]) -or
       $proof.Bytes -ne 8907 -or $proof.SHA256 -isnot [string] -or
       $proof.SHA256 -cne '5a282c19995af210fd9d7c55a8692d87d4456526352fe21034a8f07d83a9fd9d' -or
       @($Plan.Bindings|Where-Object {$_.Path -eq $proof.Path}).Count -ne 1 -or
       @($Plan.Bindings|Where-Object {$_.Path -is [string] -and $_.Path -ceq $proof.Path -and ($_.Bytes -is [int] -or $_.Bytes -is [long]) -and $_.Bytes -eq 8907 -and
          $_.SHA256 -is [string] -and $_.SHA256 -ceq $proof.SHA256 -and $_.IsText -is [bool] -and $_.IsText}).Count -ne 1){throw 'Exact guarded OS qualification proof required.'}
    if($inputs.Count -ne 1 -or $inputs[0].Path -isnot [string] -or $inputs[0].Path -cne $tz -or
       ($inputs[0].Bytes -isnot [int] -and $inputs[0].Bytes -isnot [long]) -or
       $inputs[0].Bytes -ne 12288 -or $inputs[0].SHA256 -isnot [string] -or $inputs[0].SHA256 -cne $new){throw 'Unique qualified TZRES Input required.'}
    $stream=Open-T7Bootstrap $proof.Path $proof.Bytes $proof.SHA256
    $reader=[IO.StreamReader]::new($stream,[Text.Encoding]::UTF8,$true,4096,$true)
    try{$observed=$reader.ReadToEnd()|ConvertFrom-Json -Depth 15}finally{$reader.Dispose()}
    $r=$observed.OSResource
    if($observed.Schema -cne 'iw7.t7-os-resource-qualification/1' -or $observed.Status -cne 'ObservationComplete' -or
       $observed.GuardsDisposed -isnot [bool] -or !$observed.GuardsDisposed -or
       $observed.LeaseReleased -isnot [bool] -or !$observed.LeaseReleased -or
       $observed.Ready -isnot [bool] -or $observed.Ready -or @($observed.Postflight.Leases).Count -ne 0 -or
       $r.Path -cne $tz -or $r.HistoricalBytes -ne 12288 -or $r.HistoricalSHA256 -cne $old -or
       $r.ObservedBytes -ne 12288 -or $r.ObservedSHA256 -cne $new -or $r.ProductVersion -cne $texts.ProductVersion -or
       $r.SignatureStatus -cne 'Valid' -or $r.SignatureType -cne 'Catalog' -or
       $r.SignerSubject -cne 'CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US' -or
       $r.SignerThumbprint -cne $texts.SignerThumbprint -or
       $r.ContractAccepted -isnot [bool] -or $r.ContractAccepted -or $r.PinAdopted -isnot [bool] -or $r.PinAdopted){throw 'Closed measured OS proof differs.'}
    return $proof.Path
}
function Assert-T7InputBindings($Plan) {
    # This runs before binary metadata is queried or a provider is loaded.
    # Only the finite opt-in text proof is opened here. Legacy128 and sealed E2/v2144 remain unchanged;
    # the explicit selected-streamed marker adds five exact source bindings.
    $osProofPath=Assert-T7OSResourceContext $Plan
    # The one finite proof binding is guarded above; all historical source/input
    # cardinality and bijection checks below continue over their unchanged set.
    $bindings=@($Plan.Bindings|Where-Object {!$osProofPath -or $_.Path -cne $osProofPath});$inputs=@($Plan.Inputs)
    if($null -ne $Plan.PSObject.Properties['BuildProfile'] -and $null -ne $Plan.BuildProfile -and
       $Plan.BuildProfile.Name -cin @('t7-image-provenance-v1','t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1') -and $Plan.BuildProfile.PSObject.Properties['FixtureProof']){
        $fixturePaths=@(Assert-T7ImageFixtureProof $Plan.BuildProfile $Plan.Bindings)
        $bindings=@($bindings|Where-Object {$_.Path -cnotin $fixturePaths})
    }
    $reuse=if($Plan.PSObject.Properties.Name -contains 'ReuseCompile'){$Plan.ReuseCompile}else{$null}
    $reference=$null -ne $reuse -and $null -ne $reuse.PSObject.Properties['PrepatchReferenceV2']
    $referenceProfile=$null -ne $Plan.PSObject.Properties['BuildProfile'] -and $null -ne $Plan.BuildProfile -and $Plan.BuildProfile.Name -ceq 't7-prepatch-reference-v2'
    if($reference -or $referenceProfile){$null=Assert-T7BuildProfile $Plan ([IO.Path]::GetDirectoryName($Plan.Runner))}
    $link=$null -ne $reuse -and $null -ne $reuse.PSObject.Properties['PrepatchLinkV3']
    $linkProfile=$null -ne $Plan.PSObject.Properties['BuildProfile'] -and $null -ne $Plan.BuildProfile -and $Plan.BuildProfile.Name -ceq 't7-prepatch-link-v3'
    if($link -or $linkProfile){$null=Assert-T7BuildProfile $Plan ([IO.Path]::GetDirectoryName($Plan.Runner))}
    $zombies=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'ZombiesObservationC'
    $add=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'ZombiesAddObservationC2'
    $parts=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'MaterialParts'
    $partsProfile=$null -ne $Plan.BuildProfile -and $Plan.BuildProfile.Name -ceq 't7-material-parts-v1'
    if($parts -ne $partsProfile){throw 'Parts marker/profile pairing required before inputs.'}
    $provenance=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'ImageProvenance'
    $metadata=$provenance -and $reuse.PSObject.Properties.Name -contains 'ImageMetadata'
    $registration=$provenance -and $reuse.PSObject.Properties.Name -contains 'RegistrationMetadata'
    $incoming=$registration -and $reuse.PSObject.Properties.Name -contains 'IncomingObservation'
    $registrationBindings=$registration -and $reuse.PSObject.Properties.Name -contains 'RegistrationBindingsObservation'
    $provenanceProfile=$null -ne $Plan.BuildProfile -and $Plan.BuildProfile.Name -cin @('t7-image-provenance-v1','t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1')
    if($provenance -ne $provenanceProfile -or ($provenance -and ($parts -or $zombies -or $add -or $reference -or $link))){throw 'Exclusive provenance marker/profile pairing required before inputs.'}
    if($provenance){$null=Assert-T7BuildProfile $Plan ([IO.Path]::GetDirectoryName($Plan.Runner))}
    if($parts){$null=Assert-T7BuildProfile $Plan ([IO.Path]::GetDirectoryName($Plan.Runner))}
    if($parts -and ($zombies -or $add -or $reuse.PSObject.Properties['PrepatchReferenceV2'])){throw 'Parts transition cannot mix with other diagnostic markers.'}
    if($zombies -and $add){throw 'C and C2 observation markers are exclusive.'}
    $observed=$zombies -or $add
    if($bindings.Count -gt $(if($registrationBindings){187}elseif($incoming){182}elseif($registration){173}elseif($metadata){166}elseif($provenance){155}elseif($parts){154}elseif($observed){151}else{149}) -or $inputs.Count -gt 2048 -or
        @($bindings.Path|Sort-Object -Unique).Count -ne $bindings.Count -or
        @($inputs.Path|Sort-Object -Unique).Count -ne $inputs.Count){throw 'Input set bound/uniqueness differs.'}
    if(@($bindings|Where-Object {$_.IsText -isnot [bool]}).Count){throw 'Binding text/binary classification required.'}
    $v2=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'ResidentMultiSurfaceV2'
    $streamedV1=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'SelectedStreamedStaticV1'
    $renderOnly=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'SelectedStreamedRenderOnlyV2'
    if(($parts -or $provenance) -and (!$renderOnly -or $streamedV1)){throw 'Parts requires the exact retained E5 source family.'}
    if($renderOnly -and ($streamedV1 -or $zombies)){throw 'Render-only and frozen V1/C markers are exclusive.'}
    if($add -and (!$renderOnly -or $streamedV1)){throw 'C2 requires the explicit render-only V2 marker.'}
    $streamed=$streamedV1 -or $renderOnly
    if(!$v2) {
        if($observed -or $parts -or $provenance){throw 'Observation requires the current selected-streamed publication proof.'}
        if($streamed){throw 'Selected-streamed marker requires the exact common geometry proof.'}
        if($bindings.Count -gt 128){throw 'Legacy input binding limit is 128.'}
        return
    }
    if($Plan.SourceCommit -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
        $Plan.BuildProfile.Name -cne $(if($registrationBindings){'t7-registration-material-bindings-v1'}elseif($incoming){'t7-incoming-image-header-observation-v1'}elseif($registration){'t7-registration-image-header-metadata-v1'}elseif($provenance){'t7-image-provenance-v1'}elseif($parts){'t7-material-parts-v1'}elseif($add){'t7-zombies-catalogue-observation-c2'}elseif($zombies){'t7-zombies-catalogue-observation-c'}else{'t7-catalog-message-publication'}) -or
        $Plan.BuildProfile.PublicationSchema -cne 'iw7.t7-message-publication-build/1' -or
        $reuse.RecompiledMain -isnot [bool] -or !$reuse.RecompiledMain -or
        $reuse.RecompiledZonetool -isnot [bool] -or !$reuse.RecompiledZonetool -or
        $reuse.PSObject.Properties.Name -contains 'ResidentSurfaceCountDiagnostic' -or
        $bindings.Count -ne $(if($registrationBindings){187}elseif($incoming){182}elseif($registration){173}elseif($metadata){166}elseif($provenance){155}elseif($parts){154}elseif($observed){151}elseif($streamed){149}else{144}) -or $inputs.Count -ne 1146 -or
        @($bindings|Where-Object IsText).Count -ne $(if($registrationBindings){181}elseif($incoming){176}elseif($registration){167}elseif($metadata){160}elseif($provenance){149}elseif($parts){148}elseif($observed){145}elseif($streamed){143}else{138})){throw 'Exact multisurface publication input profile required.'}
    $observerRoot=[IO.Path]::GetDirectoryName($Plan.Runner)
    if($zombies) {
        $observation=$reuse.ZombiesObservationC
        if(!$streamed -or $Plan.BuildProfile.ObservationSchema -cne 'iw7.t7-zm-observation/1' -or
           (@($observation.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'BaseCLIBytes,BaseCLISHA256,CLIBytes,CLISHA256,Schema,SourceProfile' -or
           $observation.Schema -cne 'iw7.t7-zm-observation-build/1' -or
           $observation.SourceProfile -cne 't7-zombies-catalogue-observation-c' -or
           $observation.BaseCLIBytes -ne 107785 -or $observation.BaseCLISHA256 -cne 'c480fbd39525df09bd5677026678743c73fa66eb3ca0752e78729eee2f4dcc50' -or
           $observation.CLIBytes -ne 118485 -or $observation.CLISHA256 -cne '917c2f9025185d23a8b2b683157144c2da62fe747f17f11e0f8c1abcf66be987'){
            throw 'Exact reviewed Zombies observation transition required.'
        }
        foreach($source in @(
            @('ObserverSource','native_catalog_zombies_observation.inc',9668,'50361fbd5deb38b7410e31b995b1dcd7cdf6e43f04dc81835ed213f74155d181'),
            @('ObserverAdapter','prepare_catalog_zombies_observation.py',7613,'1bf133356025893ff59c4d3de7e3614ac60f00a098f16b4b707e0eaa012da445'))) {
            $path=Join-Path $observerRoot $source[1];$pin=$Plan.BuildProfile.($source[0])
            if((@($pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
               $pin.Path -cne $path -or $pin.Bytes -ne $source[2] -or $pin.SHA256 -cne $source[3] -or
               @($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -and
                   $_.Bytes -eq $source[2] -and $_.SHA256 -ceq $source[3]}).Count -ne 1){throw 'Approved Zombies observation source binding required.'}
        }
    }
    if($add) {
        $observation=$reuse.ZombiesAddObservationC2
        if($Plan.BuildProfile.ObservationSchema -cne 'iw7.t7-zm-add-observation/1' -or
           (@($observation.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'BaseCLIBytes,BaseCLISHA256,CLIBytes,CLISHA256,Schema,SourceProfile' -or
           $observation.Schema -cne 'iw7.t7-zm-add-observation-build/1' -or
           $observation.SourceProfile -cne 't7-zombies-catalogue-observation-c2' -or
           $observation.BaseCLIBytes -ne 112377 -or $observation.BaseCLISHA256 -cne 'c63d9552464da674d3b03c35f7edc16385fb9370b113a3925fd7bc4835fb005a' -or
           $observation.CLIBytes -ne 119139 -or $observation.CLISHA256 -cne '19af683d0c609d43cefc7c93dd3d7fa6f7ae1a6f5b90d2945d37b1830bda1111'){
            throw 'Exact reviewed C2 source transition required.'
        }
        foreach($source in @(
            @('ObserverSource','native_catalog_add_observation.inc',6397,'fe37357ad1f3162f24ae79af51f325763b81e05851eb263f8681b5558835f11d'),
            @('ObserverAdapter','prepare_catalog_add_observation.py',6156,'cf6551b918e21d0046136ea3e328494960b70a62334bc3f2727e0a52fee5ec6f'))) {
            $path=Join-Path $observerRoot $source[1];$pin=$Plan.BuildProfile.($source[0])
            if((@($pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
               $pin.Path -cne $path -or $pin.Bytes -ne $source[2] -or $pin.SHA256 -cne $source[3] -or
               @($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -and
                   $_.Bytes -eq $source[2] -and $_.SHA256 -ceq $source[3]}).Count -ne 1){throw 'Approved C2 source binding required.'}
        }
    }
    if($streamed) {
        if($renderOnly) {
            $marker=$reuse.SelectedStreamedRenderOnlyV2
            if(!$marker -or (@($marker.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'CollisionPolicy,GeometryProfile,Schema' -or
                $marker.Schema -cne 'iw7.t7-selected-streamed-render-only-build/2' -or
                $marker.GeometryProfile -cne 't7-iw7-selected-streamed-render-only-v2' -or
                $marker.CollisionPolicy -cne 'omit-source-rigid-collision-trees'){throw 'Exact render-only source marker required.'}
            $sourcePins=@(
                @('streamed_mesh_payload.hpp',18512,'53265601cec86ba6e0b731e54d9c706f41d390756f4e4566ace70bd5fbd25adf'),
                @('t7_iw7_streamed_model.hpp',11951,'04007fa53fc6a3cc0307a589e7f28cebfa1c2a37c6071e0a2cb9ded412782453'),
                @('native_streamed_export.inc',10919,'f4fdc95d6a29bbe36c9140beff11567ab3ecc4d87f3c28e1e4e7fa4a25ec92c7'),
                @('streamed_contract.py',10366,'cc584cf6d2ff82be77b9ef0e926cda75ac7768f85e906d6eef22c2f8c2572df4'),
                @('test_streamed_contract.py',$(if($add -or $parts -or ($reuse.PSObject.Properties.Name -contains 'ImageProvenance')){17443}else{13768}),
                    $(if($add -or $parts -or ($reuse.PSObject.Properties.Name -contains 'ImageProvenance')){'9146f69c84c4178341010f7b6d7c10c4226ce4c7ec524b5fcdf4da742a95ac30'}else{'86392ae7934213692ae4c9453579d4b006d2665d6a80aaf52e39a41edc18bb3c'})) )
        } else {
            $marker=$reuse.SelectedStreamedStaticV1
            if(!$marker -or (@($marker.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'GeometryProfile,Schema' -or
                $marker.Schema -cne 'iw7.t7-selected-streamed-static-build/1' -or
                $marker.GeometryProfile -cne 't7-iw7-selected-streamed-static-v1'){throw 'Exact selected-streamed source marker required.'}
        $sourcePins=@(
            @('streamed_mesh_payload.hpp',18512,'53265601cec86ba6e0b731e54d9c706f41d390756f4e4566ace70bd5fbd25adf'),
            @('t7_iw7_streamed_model.hpp',11289,'5eeaa89565bcfb2c5a1d899f78a47787584a1472caae9e84f04af1b8c886e5a0'),
            @('native_streamed_export.inc',9823,'60916d49cb4490f0cc508b699d9adaa02a780229fa5e69e3c66297f50c3b0123'),
            @('streamed_contract.py',7996,'b7d68593b93975832cfa6362c2f782187772c2255cd59c78ab5aae66d759518f'),
            @('test_streamed_contract.py',8796,'fe25379d80cc1ec328836a0e75652046c01b9ddadba3dba73c8e7a550bed1d16'))
        }
        foreach($source in $sourcePins) {
            $path=Join-Path $observerRoot $source[0]
            if(@($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -and
                $_.Bytes -eq $source[1] -and $_.SHA256 -ceq $source[2]}).Count -ne 1){throw 'Exact selected-streamed source binding required.'}
        }
    }
    $materialHeader=if($renderOnly){@('selected_material_observation.hpp',18583,'a8848a92b8d7918fbe91ec4b68df123b1eaab89edde9d8a7c24d5a0cfb576ffc')}elseif($streamed){@('selected_material_observation.hpp',16489,'0ea84735fca2502033cc48a4eede6a19e1bd1283ba1975829f763c16e5ef343a')}
        else{@('selected_material_observation.hpp',12765,'a935803571f04b3a2cad7346824bf3194f5d44aeada15b224a3faa75ea292d7f')}
    $materialFixture=if($renderOnly){@('selected_material_observation_fixture.cpp',20260,'b3de68880b6f8c717c2e70ed44497ae2f95f37db7e73bbf34ef014d8e5b6fc6f')}elseif($streamed){@('selected_material_observation_fixture.cpp',13721,'cb27d4df66f3a186de3e0f5faedf7bf713610a2da0fc599861e5a4838ea2dfed')}
        else{@('selected_material_observation_fixture.cpp',8146,'f011131feeb5495b3bfb0a1e86ad34aad20fc7869ec775c861290df6e3e1a05b')}
    foreach($observer in @(
        @('resident_image_copy.hpp',6366,'96291c23f132e09285d4ea3171c9107ac525d8628403014eae85a895f99c324e'),
        $materialHeader,$materialFixture)) {
        $path=Join-Path $observerRoot $observer[0]
        if(@($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -and
            $_.Bytes -eq $observer[1] -and $_.SHA256 -ceq $observer[2]}).Count -ne 1){
            throw 'Exact read-only selected-metadata source binding required.'
        }
    }
    # Check classification by the retained six-tool metadata inventory too.
    # Counts alone must not permit an EXE to become a pre-admission text read.
    $binaryRows=[Collections.Generic.List[string]]::new()
    foreach($pin in $bindings) {
        if($pin.IsText) {
            if([IO.Path]::GetExtension($pin.Path) -in @('.exe','.dll','.obj','.pdb','.lib','.res','.pch')){
                throw 'Opaque build input cannot be a text binding.'
            }
        } else {$binaryRows.Add([IO.Path]::GetFileName($pin.Path).ToLowerInvariant()+'|'+$pin.Bytes+'|'+$pin.SHA256+"`n")}
    }
    $binaryRows.Sort([StringComparer]::Ordinal);$binaryBytes=[Text.Encoding]::UTF8.GetBytes(($binaryRows -join ''))
    if($binaryBytes.Length -ne 494 -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($binaryBytes)).ToLowerInvariant() -cne
        '3d5bcf2d88a865efba3e9fea62c90949a7b44330631689946f733de3497cb89d'){throw 'Exact six binary metadata bindings required.'}
    $proof=$reuse.ResidentMultiSurfaceV2;$headers=$proof.AdditionalHeaderInputs
    $readSHA='d9cdd533796a9fe14e0d5140d8adcbf5cbc932fafd4c06e18a615d15199a2185'
    $compileSHA='a7083ce5b9ba2fe1421c4f8733cf1d1e0b286549dbc55a44f3ef30ceb3c05333'
    $linkSHA='70455d2f32a9b034dda20fbaf48443ee68a02e552381edbf88b19d219f1f66b2'
    if($proof.Schema -cne 'iw7.t7-resident-multi-surface-build/2' -or
        $proof.Header -cne 'prepared/t7_iw7_resident_model.hpp' -or
        $proof.PreviousSHA256 -cne '6d2da3d4f7c3d0686909dc488f3d176ee2dd250e8d43d9a3cd9bcfa701482777' -or
        $proof.SHA256 -cne '857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4' -or
        $proof.E7ReadSHA256 -cne $readSHA -or $proof.E7CompileSHA256 -cne $compileSHA -or
        $proof.E7LinkSHA256 -cne $linkSHA -or $proof.E7TranslationUnits -ne 413 -or $proof.E7Objects -ne 413 -or
        $headers.Count -ne 66 -or $headers.Bytes -ne 87204 -or @($headers.Inputs).Count -ne 66 -or
        $headers.E7ReadSHA256 -cne $readSHA -or $headers.E7CompileSHA256 -cne $compileSHA -or
        $headers.CompilerContextMatchesCLI -isnot [bool] -or !$headers.CompilerContextMatchesCLI){
        throw 'Complete pinned multisurface dependency proof required.'
    }
    $suffix='\src\zonetool\zonetool\iw7\assets\xsurface.cpp'
    $tu=$headers.E7TranslationUnit
    if(![IO.Path]::IsPathFullyQualified($tu) -or [IO.Path]::GetFullPath($tu) -cne $tu -or
        !$tu.EndsWith($suffix,[StringComparison]::Ordinal)){throw 'Exact IW7 writer source context required.'}
    $native=$tu.Substring(0,$tu.Length-$suffix.Length)
    $rows=[Collections.Generic.List[string]]::new();$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($pin in $headers.Inputs) {
        if(![IO.Path]::IsPathFullyQualified($pin.Path) -or [IO.Path]::GetFullPath($pin.Path) -cne $pin.Path -or
            !$seen.Add($pin.Path) -or $pin.Bytes -le 0 -or $pin.Bytes -gt 16KB -or
            $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Canonical unique bounded header pin required.'}
        $relative=[IO.Path]::GetRelativePath($native,$pin.Path).Replace('\','/').ToLowerInvariant()
        $rows.Add($relative+'|'+$pin.Bytes+'|'+$pin.SHA256+"`n")
        $input=@($inputs|Where-Object {$_.Path -ceq $pin.Path -and $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256})
        $binding=@($bindings|Where-Object {$_.Path -ceq $pin.Path -and $_.Bytes -eq $pin.Bytes -and
            $_.SHA256 -ceq $pin.SHA256 -and $_.IsText})
        if($input.Count -ne 1 -or $binding.Count -ne 1){throw 'Header proof/Inputs/text Bindings bijection differs.'}
    }
    # Canonical sorted relative-path|raw-bytes|SHA256 LF rows from the reviewed
    # MULTISURFACE_HEADER_PINS table. Do not duplicate or discover native files.
    $rows.Sort([StringComparer]::Ordinal);$bytes=[Text.Encoding]::UTF8.GetBytes(($rows -join ''))
    if($bytes.Length -ne 7676 -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() -cne
        '5ee7ea0b46848bca9f4d365d0035cf070b2f57c6723019ab1288a54a93a7297b'){throw 'Reviewed 66-header pin inventory differs.'}
    $pch=$headers.PCHExcludedForPreparedYMinus
    if(![IO.Path]::IsPathFullyQualified($pch) -or [IO.Path]::GetFullPath($pch) -cne $pch -or
        !$pch.EndsWith('\obj\community.pch',[StringComparison]::Ordinal)){throw 'Exact excluded E7 PCH required.'}
    $obj=Split-Path $pch -Parent
    foreach($row in @(@('CL.read.1.tlog',$readSHA,15206288,15206288),
        @('CL.command.1.tlog',$compileSHA,1,4MB),@('link.command.1.tlog',$linkSHA,1,256KB))) {
        $path=Join-Path $obj ('tlog/'+$row[0])
        if(@($bindings|Where-Object {$_.Path -ieq $path -and $_.IsText -and $_.SHA256 -ceq $row[1] -and
            $_.Bytes -ge $row[2] -and $_.Bytes -le $row[3]}).Count -ne 1){throw 'Sealed E7 journal text binding absent.'}
    }
    if(@($proof.DependencyJSON).Count -ne 3 -or @($reuse.StageRoots).Count -ne 1){throw 'Exact retained dependency proof required.'}
    $oldRun=Split-Path $reuse.StageRoots[0] -Parent
    $depPins=@(@('helper',16296,'6897d27e8fe0754509e52258082d6178c8cb74fe21a8ef4b006006e97ab9dd12'),
        @('zonetool11',76744,'cfe62be9ce9bf87abd8e6713f1e1f334d76f69472500d2cb260696de26ee8273'),
        @('xpak',64444,'3d742923def4fb049d82853ac0e776ffd071228deaf1da1a624603d10dfd3908'))
    foreach($row in $depPins) {
        $path=Join-Path $oldRun ($row[0]+'/dependencies.json')
        foreach($set in @(@($proof.DependencyJSON),$bindings)) {
            if(@($set|Where-Object {$_.Path -ceq $path -and $_.Bytes -eq $row[1] -and $_.SHA256 -ceq $row[2]}).Count -ne 1){
                throw 'Pinned C dependency JSON or binding differs.'
            }
        }
        if(@($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText}).Count -ne 1){throw 'C dependency JSON must be text.'}
    }
    if(@($proof.SourceTransitions).Count -ne 3){throw 'Exact three source transitions required.'}
    $rows.Clear()
    foreach($row in $proof.SourceTransitions) {
        $rows.Add((@($row.Path,$row.PreviousBytes,$row.PreviousSHA256,$row.Bytes,$row.SHA256,$row.WiredBytes,$row.WiredSHA256)-join '|')+"`n")
        $path=Join-Path (Split-Path $Plan.PreparedRoot -Parent) $row.Path
        $wiredBytes=$row.WiredBytes;$wiredSHA=$row.WiredSHA256
        if($parts -and $row.Path -ceq 'prepared/main.cpp'){
            $wiredBytes=$reuse.MaterialParts.MainBytes;$wiredSHA=$reuse.MaterialParts.MainSHA256
        }
        if($parts -and $row.Path -ceq 'prepared/zonetool.cpp'){
            $wiredBytes=$reuse.MaterialParts.CLIBytes;$wiredSHA=$reuse.MaterialParts.CLISHA256
        }
        if($provenance -and $row.Path -ceq 'prepared/main.cpp'){$wiredBytes=$reuse.ImageProvenance.MainBytes;$wiredSHA=$reuse.ImageProvenance.MainSHA256}
        if($provenance -and $row.Path -ceq 'prepared/zonetool.cpp'){$wiredBytes=$reuse.ImageProvenance.CLIBytes;$wiredSHA=$reuse.ImageProvenance.CLISHA256}
        if($metadata -and $row.Path -ceq 'prepared/main.cpp'){$wiredBytes=$reuse.ImageMetadata.MainBytes;$wiredSHA=$reuse.ImageMetadata.MainSHA256}
        if($metadata -and $row.Path -ceq 'prepared/zonetool.cpp'){$wiredBytes=$reuse.ImageMetadata.CLIBytes;$wiredSHA=$reuse.ImageMetadata.CLISHA256}
        if($registration -and $row.Path -ceq 'prepared/main.cpp'){$wiredBytes=$reuse.RegistrationMetadata.MainBytes;$wiredSHA=$reuse.RegistrationMetadata.MainSHA256}
        if($registration -and $row.Path -ceq 'prepared/zonetool.cpp'){$wiredBytes=$reuse.RegistrationMetadata.CLIBytes;$wiredSHA=$reuse.RegistrationMetadata.CLISHA256}
        if($incoming -and $row.Path -ceq 'prepared/main.cpp'){$wiredBytes=$reuse.IncomingObservation.MainBytes;$wiredSHA=$reuse.IncomingObservation.MainSHA256}
        if($incoming -and $row.Path -ceq 'prepared/zonetool.cpp'){$wiredBytes=$reuse.IncomingObservation.CLIBytes;$wiredSHA=$reuse.IncomingObservation.CLISHA256}
        if($observed -and $row.Path -ceq 'prepared/zonetool.cpp') {
            if($wiredBytes -ne $observation.BaseCLIBytes -or $wiredSHA -cne $observation.BaseCLISHA256){throw 'Zombies observation base transition differs.'}
            $wiredBytes=$observation.CLIBytes;$wiredSHA=$observation.CLISHA256
        }
        if(@($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -and $_.Bytes -eq $wiredBytes -and
            $_.SHA256 -ceq $wiredSHA}).Count -ne 1){throw 'Wired v2 transition binding differs.'}
    }
    $rows.Sort([StringComparer]::Ordinal);$bytes=[Text.Encoding]::UTF8.GetBytes(($rows -join ''))
    $transitionBytes=if($streamed){716}else{714}
    $transitionSHA=if($renderOnly){'09f477a869eabe0794118dff29a8412773b30ab4602ea7c18190ea748768a395'}elseif($streamed){'76570ca356d90c45c04b7cd4c8e46ff8126fc1cdb9c0919562dbb265955bee6b'}else{
        'e1b572bfacbce89260ffce52d21c26e15f2ae2aa5172256cd063797b9a0f1b1c'}
    if($bytes.Length -ne $transitionBytes -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() -cne
        $transitionSHA){throw 'Reviewed versioned source transitions differ.'}
}
function Split-T7ResponseArguments([string]$Text) {
    # Deliberately bounded MSVC response syntax: space/tab separators and quoted
    # segments within arguments. Escaped/doubled or unclosed quotes are refused,
    # not guessed; the generator never needs them for these file destinations.
    if($Text -match '[\x00-\x08\x0a-\x1f\x7f]|\\+"|""' -or $Text.Contains('@')) {
        throw 'Unsupported or indirect publication response syntax.'
    }
    $arguments=[Collections.Generic.List[string]]::new()
    $token=[Text.StringBuilder]::new();$quoted=$false
    foreach($character in $Text.ToCharArray()) {
        if($character -eq '"') {$quoted=!$quoted;continue}
        if(!$quoted -and ($character -eq ' ' -or $character -eq "`t")) {
            if($token.Length){$arguments.Add($token.ToString());$null=$token.Clear()}
        } else {$null=$token.Append($character)}
    }
    if($quoted){throw 'Unclosed publication response quote.'}
    if($token.Length){$arguments.Add($token.ToString())}
    return ,$arguments.ToArray()
}
function Assert-T7ResponseOutputs([string[]]$Arguments,[System.Collections.IDictionary]$Outputs) {
    $seen=@{}
    for($index=0;$index -lt $Arguments.Count;$index++) {
        $argument=$Arguments[$index]
        if($argument -notmatch '^[-/]'){continue}
        $option=$argument.Substring(1)
        # This existing linker flag shares PDB's prefix but takes no filename.
        if($option -ieq 'PDBCompress'){continue}
        foreach($name in $Outputs.Keys) {
            if(!$option.StartsWith($name,[StringComparison]::OrdinalIgnoreCase)){continue}
            if($seen.ContainsKey($name)){throw 'Duplicate publication output option.'}
            $seen[$name]=$true
            $value=$option.Substring($name.Length)
            if($value.StartsWith(':')){$value=$value.Substring(1)}
            if(!$value) {
                $index++
                if($index -ge $Arguments.Count){throw 'Missing publication output value.'}
                $value=$Arguments[$index]
            }
            if($value -cne $Outputs[$name]){throw 'Publication output must belong to its exact fresh stage.'}
            break
        }
    }
    if($seen.Count -ne $Outputs.Count){throw 'Missing publication output option.'}
}
function Assert-T7PublicationResponses($Plan,[string]$MainResponse,[string]$CLIResponse,[string]$LinkResponse) {
    # Pure text validation, only for the new profile. The caller already guards
    # these exact response files by length/hash; no binary input is read here.
    foreach($row in @(@('main','main.cpp',$MainResponse),@('zonetool11','zonetool.cpp',$CLIResponse))) {
        $name=$row[0];$text=$row[2];$stageRoot=Join-Path $Plan.RunRoot $name
        $arguments=Split-T7ResponseArguments $text.TrimEnd("`r","`n")
        Assert-T7ResponseOutputs $arguments ([ordered]@{
            Fo=(Join-Path $stageRoot ($name+'.obj'));Fd=(Join-Path $stageRoot 'compile.pdb')
            sourceDependencies=(Join-Path $stageRoot 'dependencies.json')
        })
        if(!$arguments.Count -or $arguments[-1] -cne (Join-Path $Plan.PreparedRoot $row[1])) {throw 'Exact prepared compile source required.'}
    }
    $lines=@($LinkResponse.TrimEnd("`r","`n") -split "`r?`n")
    if($lines.Count -ne 414 -or $lines[0] -match '(?i)\.obj\b|@') {throw 'Exact direct 413-object link required.'}
    $linkRoot=Join-Path $Plan.RunRoot 'link'
    Assert-T7ResponseOutputs (Split-T7ResponseArguments $lines[0]) ([ordered]@{
        OUT=(Join-Path $linkRoot 'zonetool-t7.exe');PDB=(Join-Path $linkRoot 'zonetool-t7.pdb')
        IMPLIB=(Join-Path $linkRoot 'zonetool-t7.lib')
    })
    $objects=@();$unique=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($line in $lines[1..413]) {
        if($line -notmatch '^"([^"\r\n]+\.obj)"$') {throw 'Direct quoted link object required.'}
        $path=$Matches[1]
        if(!$unique.Add($path)){throw 'Duplicate publication link object.'}
        $objects+=$path
    }
    foreach($name in 'main','zonetool11') {
        $objectMatches=@($objects|Where-Object {[IO.Path]::GetFileName($_) -ieq ($name+'.obj')})
        $expected=Join-Path (Join-Path $Plan.RunRoot $name) ($name+'.obj')
        if($objectMatches.Count -ne 1 -or $objectMatches[0] -cne $expected) {throw 'Publication link refuses a retained main or CLI object.'}
    }
    if(@($Plan.ReuseCompile.StageRoots).Count -ne 1){throw 'Publication retains only xpak dependencies.'}
    $objectMatches=@($objects|Where-Object {[IO.Path]::GetFileName($_) -ieq 'xpak.obj'})
    if($objectMatches.Count -ne 1 -or $objectMatches[0] -cne (Join-Path $Plan.ReuseCompile.StageRoots[0] 'xpak.obj')) {
        throw 'Exact retained xpak object required.'
    }
}
try {
    $planSize=(Get-Item -LiteralPath $PlanPath).Length
    if($planSize -gt 2MB){throw 'Plan exceeds 2 MiB.'}
    $planStream=Open-T7Bootstrap $PlanPath $planSize $PlanSHA256
    $reader=[IO.StreamReader]::new($planStream,[Text.Encoding]::UTF8,$true,4096,$true)
    try{$plan=$reader.ReadToEnd()|ConvertFrom-Json -Depth 25}finally{$reader.Dispose()}
    if($plan.Schema -cne 'iw7.t7-minimal-build-plan/1' -or $plan.Runner -cne $PSCommandPath -or
       $plan.Profile -cne (Join-Path $PSScriptRoot 'T7Build.Profile.ps1')){throw 'Exact T7 runner/profile required.'}
    if($plan.PhysicalBytes -ne 4GB -or $plan.CommitBytes -ne 6GB -or $plan.GroupDeadlineSeconds -ne 600 -or
       $plan.OutputLimitBytes -ne 256MB -or $plan.MetadataReserveBytes -ne 1MB -or $plan.CleanupSeconds -ne 5 -or
       $plan.ReusedObjects -ne 410 -or $plan.ReusedProjectLibraries -ne 18 -or $plan.ReusedResources -ne 1){throw 'Fixed minimal build limits differ.'}
    $reuse=$plan.PSObject.Properties.Name -contains 'ReuseCompile' -and $null -ne $plan.ReuseCompile
    $recompiled=Assert-T7BuildProfile $plan $PSScriptRoot
    $buildProfile=if($recompiled){$plan.BuildProfile}else{$null}
    $incoming=$null -ne $buildProfile -and $buildProfile.Name -ceq 't7-incoming-image-header-observation-v1'
    $registrationBindings=$null -ne $buildProfile -and $buildProfile.Name -ceq 't7-registration-material-bindings-v1'
    $registration=$null -ne $buildProfile -and $buildProfile.Name -cin @('t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1')
    $publication=$null -ne $buildProfile -and $buildProfile.Name -cin @('t7-catalog-message-publication','t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2','t7-material-parts-v1','t7-image-provenance-v1','t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1')
    $names=@(if($publication){'main','zonetool11','link'}elseif($recompiled){'main','link'}elseif($reuse){'link'}else{'helper','probe','main','zonetool11','xpak','link'})
    if($registration){
        $names=@('registration-fixture-compile','registration-fixture-test')+$names
    }elseif($null -ne $buildProfile -and $buildProfile.PSObject.Properties['MetadataSchema']){
        $names=@('metadata-fixture-compile','metadata-fixture-test')+$names
    }
    if($null -ne $buildProfile -and $buildProfile.Name -cin @('t7-image-provenance-v1','t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1')){
        if($Run -and $buildProfile.SourceOnlyPending){throw 'Image-provenance producer is source-pending: measured H proof and separate full-CLI CPP GO required.'}
        if(!$Run){
            $check=[ordered]@{SourceProfile=$buildProfile.Name;SourceOnlyPending=$buildProfile.SourceOnlyPending;CPPEnabled=!$buildProfile.SourceOnlyPending;
                CandidateBytes=$null;CandidateSHA256=$null;NativeTypesLoaded=$false;BinaryInputsHashed=$false;ZoneHashObserved=$false;
                LeaseAcquired=$false;FilesCreated=$false;Ready=$false}
            if($buildProfile.Name -cin @('t7-registration-image-header-metadata-v1','t7-incoming-image-header-observation-v1','t7-registration-material-bindings-v1')){
                $check.BaseProvenanceSourceOnlyPending=$buildProfile.SourceOnlyPending;$check.SourceOnlyPending=$true
                $check.RegistrationCPPQualified=$false;$check.RegistrationFixtureRequired=39;$check.FixtureFirstEnforced=$true
            }
            if($buildProfile.Name -ceq 't7-incoming-image-header-observation-v1'){
                $check.CPPEnabled=$false;$check.CPPRecipeNeedsQualification=$true
                $check.IncomingCPPQualified=$false;$check.IncomingFixtureRequired=48
            }
            if($buildProfile.Name -ceq 't7-registration-material-bindings-v1'){
                $check.CPPEnabled=$false;$check.CPPRecipeNeedsQualification=$true
                $check.RegistrationBindingsCPPQualified=$false;$check.BindingsFixtureRequired=41;$check.TotalFixtureRequired=80
            }
            $check|ConvertTo-Json -Compress
            return
        }
    }
    if(@($plan.Stages).Count -ne $names.Count -or (@($plan.Stages.Name)-join ',') -cne ($names-join ',')){throw 'Exact full, retained-link or diagnostic main/link stages required.'}
    Assert-T7InputBindings $plan
    foreach($pin in $plan.Bindings) {
        if($pin.IsText -isnot [bool]){throw 'Binding text/binary classification required.'}
        if($pin.IsText){
            if(!$Run -or ![string]::Equals([IO.Path]::GetExtension($pin.Path),'.tlog',[StringComparison]::OrdinalIgnoreCase)){$null=Open-T7Bootstrap $pin.Path $pin.Bytes $pin.SHA256}
        }
        elseif((Get-Item -LiteralPath $pin.Path).Length -ne $pin.Bytes){throw 'Binary metadata changed.'}
    }
    foreach($required in @($plan.Runner,$plan.Profile,$plan.Core,$plan.CompilerCore,$plan.ObserverSource,$plan.CompilerPolicySource,$plan.Scheduler)) {
        if(@($plan.Bindings|Where-Object {$_.Path -ceq $required -and $_.IsText}).Count -ne 1){throw 'Exact source provider pin missing.'}
    }
    if($publication) {
        Assert-T7PublicationResponses $plan ([IO.File]::ReadAllText($plan.BuildProfile.MainResponse.Path)) `
            ([IO.File]::ReadAllText($plan.BuildProfile.CLIResponse.Path)) ([IO.File]::ReadAllText($plan.BuildProfile.LinkResponse.Path))
    }
    . $plan.Core
    $runtime=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../runtime'))
    Assert-H1Path $plan.RunRoot
    if([IO.Path]::GetDirectoryName($plan.RunRoot) -cne $runtime -or (Test-Path -LiteralPath $plan.RunRoot)){throw 'Fresh output directly under owned runtime required.'}
    foreach($stage in $plan.Stages) {
        $expectedType=if($stage.Name -cin @('probe','metadata-fixture-test','registration-fixture-test')){'Probe'}elseif($stage.Name -ceq 'link'){'Link'}else{'Compile'}
        $expectedSeconds=if($expectedType -ceq 'Probe'){15}else{120}
        if($stage.Stage -cne $expectedType -or $stage.DeadlineSeconds -ne $expectedSeconds){throw 'Fixed stage profile differs.'}
        Assert-H1Path $stage.Image
    }
    foreach($pin in $plan.Inputs) {
        Assert-H1Path $pin.Path
        if((Get-Item -LiteralPath $pin.Path).Length -ne $pin.Bytes){throw 'Recorded input metadata differs.'}
    }
    if($reuse) {
        $prior=Read-H1SmallJson $plan.ReuseCompile.Receipt
        if($prior.Schema -cne 'iw7.t7-minimal-build/1' -or $prior.Status -cne 'Failed' -or
           $prior.TreeClosureConfirmed -isnot [bool] -or !$prior.TreeClosureConfirmed -or
           $prior.LeaseReleased -isnot [bool] -or !$prior.LeaseReleased -or
           $prior.Quarantined -isnot [bool] -or $prior.Quarantined -or
           $prior.PlanSHA256 -cne $plan.ReuseCompile.SourcePlanSHA256 -or $plan.ReuseCompile.Checks -ne 51){throw 'Retained compile proof differs.'}
        foreach($name in 'helper','probe','main','zonetool11','xpak') {
            $row=@($prior.Stages|Where-Object Name -CEQ $name)
            if($row.Count -ne 1 -or $row[0].ExitCode -ne 0 -or !$row[0].TreeClosureConfirmed){throw 'Retained sub-stage was not successful and closed.'}
        }
        if(@($prior.Stages|Where-Object Name -CEQ 'probe')[0].Checks -ne 51){throw 'Retained name probe differs.'}
        foreach($required in @($plan.ReuseCompile.Receipt,$plan.ReuseCompile.SourcePlan)) {
            if(@($plan.Bindings|Where-Object {$_.Path -ceq $required -and $_.IsText}).Count -ne 1){throw 'Retained receipt/plan binding absent.'}
        }
        $priorPlan=Read-H1SmallJson $plan.ReuseCompile.SourcePlan 2MB
        $retainedNames=@(if($publication){'xpak'}elseif($recompiled){'zonetool11','xpak'}else{'main','zonetool11','xpak'})
        $retainedRoots=@($retainedNames|ForEach-Object {Join-Path $priorPlan.RunRoot $_})
        if((@($plan.ReuseCompile.StageRoots)-join '|') -cne ($retainedRoots-join '|')){throw 'Exact retained dependency roots required.'}
    }
    if(!$Run) {
        [ordered]@{Schema='iw7.t7-minimal-build-check/1';PlanSHA256=$PlanSHA256;Stages=@($plan.Stages).Count;ReusedCompilation=$reuse;BuildProfile=$buildProfile;
            ExpectedInputs=@($plan.Inputs).Count;MissingExpectedPins=@($plan.MissingExpectedPins).Count;
            NativeTypesLoaded=$false;BinaryInputsHashed=$false;LeaseAcquired=$false;RunRootCreated=$false;Ready=$false}|ConvertTo-Json
        return
    }
    if($plan.InputPinsComplete -isnot [bool] -or !$plan.InputPinsComplete -or @($plan.MissingExpectedPins).Count){throw 'Complete reviewed expected input pins required before native GO.'}
    if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7.H1Diagnostics.JobMembers' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Fresh PowerShell host required.'}
    . $plan.Scheduler
    $state=[ordered]@{Schema='iw7.t7-minimal-build/1';PlanSHA256=$PlanSHA256;Status='Pending';Ready=$false;BuildProfile=$buildProfile;
        EstimatesAreMeasured=$false;TreeClosureConfirmed=$true;LeaseReleased=$false;Quarantined=$false;
        MaxObservedOutputBytes=0L;CompilerTelemetry=[ordered]@{Completed=$false};Stages=[Collections.Generic.List[object]]::new()}
    if($registration){$state.RegistrationFixturePassed=$false;$state.RegistrationCPPQualified=$false}
    if($incoming){$state.IncomingFixturePassed=$false;$state.IncomingCPPQualified=$false}
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Build -PhysicalBytes $plan.PhysicalBytes -CommitBytes $plan.CommitBytes -Owner 'T7 three TU build and name helper'
    $state.LeaseToken=$context.Lease.Token;$script:T7GroupStarted=Get-H1Clock
    if(Test-Path -LiteralPath $plan.RunRoot){throw 'Output appeared during admission.'}
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$created=$true
    # Run defers retained tlog contents until this existing group is admitted.
    foreach($pin in @($plan.Bindings|Where-Object {$_.IsText -and [string]::Equals([IO.Path]::GetExtension($_.Path),'.tlog',[StringComparison]::OrdinalIgnoreCase)})){
        $null=Open-T7Bootstrap $pin.Path $pin.Bytes $pin.SHA256
    }
    . $plan.CompilerPolicySource
    . $plan.CompilerCore
    . $plan.Profile
    # Local to this runner: retain the ACTUAL factory result before a deadline
    # check can throw. Shared H1 and other consumers keep their existing policy.
    $script:T7OriginalFactory=${function:New-H1Owner}
    $t7OriginalContext=$context
    function New-H1Owner {
        Assert-H1Deadline $script:T7StageStarted $script:T7StageDeadlineSeconds
        $originalOwner=& $script:T7OriginalFactory
        $t7OriginalContext.Owner=$originalOwner
        Assert-H1Deadline $script:T7StageStarted $script:T7StageDeadlineSeconds
        $originalOwner
    }
    $launcher=Get-Process -Id $PID;$priority=$launcher.PriorityClass;$launcher.PriorityClass='BelowNormal'
    # No binary contents are read until the one account-wide reservation exists.
    foreach($pin in @($plan.Inputs)+@($plan.Bindings|Where-Object {!$_.IsText})){Open-T7Pin $pin $context}
    if($reuse){foreach($root in $plan.ReuseCompile.StageRoots){Assert-T7Dependencies $plan $root}}
    $null=[Reflection.Assembly]::LoadFrom($plan.JobAssembly)
    Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    Add-Type -LiteralPath $plan.ObserverSource
    Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    foreach($stage in $plan.Stages) {
        $stageStarted=Get-H1Clock # Includes directory, identity and StartInfo setup.
        $script:T7StageStarted=$stageStarted;$script:T7StageDeadlineSeconds=$stage.DeadlineSeconds
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
        if(!$context.Closed){throw 'Previous original job not closed.'}
        $script:T7CurrentStage=$stage
        $stageRoot=Join-Path $plan.RunRoot $stage.Name
        [IO.Directory]::CreateDirectory($stageRoot)|Out-Null
        $stageState=[ordered]@{Stage=$stage.Stage;Name=$stage.Name;PlanSHA256=$PlanSHA256;DeadlineSeconds=$stage.DeadlineSeconds;
            MaxObservedOutputBytes=$state.MaxObservedOutputBytes;TreeClosureConfirmed=$false;
            CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
        $state.Stages.Add($stageState)
        $image=if($stage.Stage -ceq 'Probe'){@($state.Stages[0].Artifacts|Where-Object Path -CEQ $stage.Image)[0]}
               else{@($plan.Bindings|Where-Object Path -CEQ $stage.Image)[0]}
        $start=New-T7Start $plan $stage $stageRoot
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
        Invoke-T7OwnedStage $plan $stageState $context $start $image.SHA256 $stageRoot $stageStarted
        $stageState.Artifacts=@(Get-H1CompilerArtifacts $plan $context)
        if($stageState.CompilerTelemetry.Completed) {
            foreach($prior in $stageState.CompilerTelemetry.Artifacts) {
                $now=@($stageState.Artifacts|Where-Object Path -CEQ $prior.Path)
                if($now.Count -ne 1 -or $now[0].SHA256 -cne $prior.SHA256 -or $now[0].Bytes -ne $prior.Bytes){throw 'Artifact changed across compiler cleanup.'}
            }
        }
        if($stage.Stage -ceq 'Compile'){Assert-T7Dependencies $plan $stageRoot}
        if($stage.Stage -ceq 'Probe') {
            $stdout=Join-Path $stageRoot 'stdout.log';$stderr=Join-Path $stageRoot 'stderr.log'
            $limit=if($stage.Name -ceq 'metadata-fixture-test'){256}else{128}
            if((Get-Item -LiteralPath $stdout).Length -gt $limit -or (Get-Item -LiteralPath $stderr).Length -ne 0){throw 'Fixture output differs.'}
            $observed=[IO.File]::ReadAllText($stdout)
            if($stage.Name -ceq 'registration-fixture-test'){
                if($registrationBindings){Assert-T7BindingsFixtureOutput $stageRoot $stageState;$state.RegistrationBindingsFixturePassed=$true}
                elseif($incoming){Assert-T7IncomingFixtureOutput $stageRoot $stageState;$state.IncomingFixturePassed=$true}
                else{Assert-T7RegistrationFixtureOutput $stageRoot $stageState}
                $state.RegistrationFixturePassed=$true
            }elseif($stage.Name -ceq 'metadata-fixture-test'){
                $expected="PASS copied image metadata fixture: 54 checks; authored only.`nPASS selected metadata read guard fixture: 13 checks; no engine.`n"
                if($observed.Replace("`r`n","`n") -cne $expected){throw 'Exactly 54 mapper and 13 actual guarded-reader checks required before CLI compilation.'}
                $stageState.MapperChecks=54;$stageState.GuardChecks=13;$stageState.EngineInvoked=$false
            }else{
                if($observed -cne "T7_ASSET_NAME_CHECKS=51`n" -and $observed -cne "T7_ASSET_NAME_CHECKS=51`r`n"){throw 'Exactly 51 native name checks required.'}
                $stageState.Checks=51
            }
        }
        Test-H1Budget $plan $stageState
        Assert-H1Deadline $stageStarted $stage.DeadlineSeconds
        $state.MaxObservedOutputBytes=[math]::Max($state.MaxObservedOutputBytes,$stageState.MaxObservedOutputBytes)
    }
    foreach($pin in $plan.Inputs){Open-T7Pin $pin $context}
    foreach($pin in $plan.Bindings){$guard=Open-H1Pin $pin;try{}finally{$guard.Dispose()};Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds}
    Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    $state.ElapsedMs=(Get-H1Clock)-$script:T7GroupStarted
    $state.InputsReverified=$true;$state.CandidateExecuted=$false
}catch{
    $failure=$_
    if($state){$state.Status='Failed';$state.Error=$_.Exception.Message}
}finally{
    if($state){
        Complete-H1Stage $context $state -BeforeReleaseCheck {
            if(!$created){
                if($context.Owner -or !$context.Closed){throw 'No owned output root but original job may exist.'}
                return # Admission failed before any owned output/job; never write into a foreign root.
            }
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            if(!$failure){$state.Status='PendingRelease'}
            $before=Write-H1Receipt $plan $state $plan.RunRoot -Name 'receipt-before-release.json' -PassThru
            $context.PublicationGuards.Add((Open-H1Pin $before))
            $context.Publications.Add($before)
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            $context.PreReleasePublished=$true
        }
    }
    if($launcher -and $null -ne $priority){try{$launcher.PriorityClass=$priority}catch{if(!$failure){$failure=$_};$state.Status='Failed'}}
    if($state -and $created) {
        $finalReceipt=$null
        try {
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            if(!$failure -and $context.Closed -and !$context.Lease){
                $state.Status='Passed'
                if($registration){$state.RegistrationCPPQualified=$state.RegistrationFixturePassed -and $state.InputsReverified}
                if($incoming){$state.IncomingCPPQualified=$state.IncomingFixturePassed -and $state.InputsReverified}
            }
        }catch{
            if(!$failure){$failure=$_}
            if($state.Status -cne 'Quarantined'){$state.Status='Failed'}
            $state.GroupDeadlineError=$_.Exception.Message
        }
        $state.ElapsedMs=(Get-H1Clock)-$script:T7GroupStarted
        $state.FinishedUtc=[datetime]::UtcNow.ToString('o')
        try{$finalReceipt=Write-H1Receipt $plan $state $plan.RunRoot -PassThru}catch{
            if($registration){$state.RegistrationCPPQualified=$false;$state.Status='Failed'}
            if($incoming){$state.IncomingCPPQualified=$false}
            if(!$failure){$failure=$_};Write-Warning $_.Exception.Message
        }
        if(!$failure) {
            try{Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds}
            catch {
                $failure=$_;$state.Status='Failed';$state.GroupDeadlineError=$_.Exception.Message
                $finalReceipt=$null # The late Passed pin is invalid even if retirement/republication fails.
                if($registration){$state.RegistrationCPPQualified=$false}
                if($incoming){$state.IncomingCPPQualified=$false}
                $state.ElapsedMs=(Get-H1Clock)-$script:T7GroupStarted
                # A slow publication must not leave a canonical Passed receipt.
                # Preserve the late attempt, then publish failure diagnostics.
                try {
                    $receipt=Join-Path $plan.RunRoot 'receipt.json'
                    $late=Join-Path $plan.RunRoot 'receipt.deadline-exceeded.json'
                    Assert-H1Path $receipt;Assert-H1Path $late
                    [IO.File]::Move($receipt,$late)
                    $finalReceipt=Write-H1Receipt $plan $state $plan.RunRoot -PassThru
                }catch{Write-Warning ('Late receipt failure: '+$_.Exception.Message)}
            }
        }
        if($finalReceipt -and $context.Closed -and !$context.Lease -and $context.PreReleasePublished){
            try{
                $context.PublicationGuards.Add((Open-H1Pin $finalReceipt))
                $context.Publications.Add($finalReceipt)
                foreach($publication in $context.Publications){$verified=Open-H1Pin $publication;$verified.Dispose()}
                Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
                $context.CompletionPublished=$true
            }catch{
                if(!$failure){$failure=$_};$state.Status='Failed';$state.FinalizationError=$_.Exception.Message
                if($registration){$state.RegistrationCPPQualified=$false}
                if($incoming){$state.IncomingCPPQualified=$false}
            }
        }
    }
    # Keep the same input/publication guards and original context on any unknown
    # publication. A released lease alone is never permission to drop the guards.
    if($context.Closed -and !$context.Lease -and (!$created -or $context.CompletionPublished)){
        try{
            foreach($guard in $guards){$guard.Dispose()};$guards.Clear()
            foreach($guard in $context.PublicationGuards){$guard.Dispose()};$context.PublicationGuards.Clear()
            $context.CanExit=$true
        }catch{if(!$failure){$failure=$_};if($state){$state.FinalizationError=$_.Exception.Message}}
    }
}
if($failure){throw $failure}
if(!$state.LeaseReleased -or $state.Status -cne 'Passed' -or !$context.CanExit){throw 'Build did not close, publish and release successfully; retain original context.'}
[ordered]@{Status=$state.Status;Receipt=(Join-Path $plan.RunRoot 'receipt.json');CandidateExecuted=$false;Ready=$false}|ConvertTo-Json
