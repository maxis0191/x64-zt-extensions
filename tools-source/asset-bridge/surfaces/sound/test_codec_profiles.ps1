$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Invoke-SoundCodec.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Codec syntax failed'}
foreach($name in 'Assert-CodecKnownPin','Get-CodecProfile','Assert-CodecDumpEvidence'){
    $nodes=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true))
    if($nodes.Count -ne 1){throw 'Production profile function missing'}
    . ([scriptblock]::Create($nodes[0].Extent.Text))
}
function New-ProfileFixture([string]$Profile){
    $repo=Join-Path ([IO.Path]::GetTempPath()) 'iw7-codec-pure-nonexistent'
    $source=Join-Path $repo 'runtime/content-surfaces/original-sound-source-b'
    $dump=Join-Path $repo 'runtime/content-surfaces/original-sound-sab-ff-b'
    $p=[pscustomobject]@{SharedRepo=$repo;InputProfile=$Profile;Codec=(Join-Path $repo 'ffmpeg.exe');Python=(Join-Path $repo 'python.exe');
        OriginalWAV=(Join-Path $source 'original/source.wav');SourceManifest=(Join-Path $source 'sound-source.json');
        InputFLAC=(Join-Path $source 'sound_assets/community/original_chime_v1.flac');NativeDumpState=$null;HashInputs=@()}
    $flacHash='9f807b3f4dfee213dfd44e3f60b9109075327b233f321bdf38f594c3a0c47bbb'
    if($Profile -ceq 'NativeDumpF'){
        $p.InputFLAC=Join-Path $dump 'work/dump/sdk_original_sound_v1/sound_assets/community/original_chime_v1.flac'
        $p.NativeDumpState=Join-Path $dump 'state.local.json'
        $flacHash='a4e9276568dfeaf42d39deefe243b1efc2b9095b2f558bcb3512b98c417154d9'
        $p.HashInputs+=,[pscustomobject]@{Path=$p.NativeDumpState;Bytes=65117;SHA256='d0a57123f7940eee29ef42da7440dd353e63eeffbfc025d37b162f4feda9e1a9'}
    }
    foreach($row in @(
        @($p.Codec,242496512,'ad8f211bc894755e0061c55ab280ae00e8d3d4f15a8cc4372b24cfa247b5942e'),
        @($p.Python,104952,'4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'),
        @($p.OriginalWAV,96044,'299727b757b46804ca52144133b7e72405f13ddcdaf8aea30a497afc62ca9cb4'),
        @($p.SourceManifest,3158,'06a2bf8650ba235e176746efe29b00f383e26144cd24ff5dd1774c28f9d71a01'),
        @($p.InputFLAC,96394,$flacHash)
    )){$p.HashInputs+=,[pscustomobject]@{Path=$row[0];Bytes=$row[1];SHA256=$row[2]}}
    $p
}
$checks=0
foreach($name in 'OriginalSource','NativeDumpF'){
    $p=New-ProfileFixture $name;$result=Get-CodecProfile $p
    $expected=if($name -ceq 'OriginalSource'){'ThirdPartyPCMVerified'}else{'DumpDecodedByFFmpeg'}
    if($result.Name -cne $name -or $result.SuccessStatus -cne $expected){throw 'Closed profile positive failed'}
    $checks++
}
foreach($case in 'Unknown','Boolean','Missing','HashSwap','WrongPath','WrongWAV','WrongManifest','MissingState','StateHash','StateSize'){
    $p=New-ProfileFixture NativeDumpF
    switch($case){
        Unknown {$p.InputProfile='Other'}
        Boolean {$p.InputProfile=$true}
        Missing {$p.InputProfile=$null}
        HashSwap {($p.HashInputs|Where-Object Path -EQ $p.InputFLAC).SHA256='9f807b3f4dfee213dfd44e3f60b9109075327b233f321bdf38f594c3a0c47bbb'}
        WrongPath {$p.InputFLAC=$p.OriginalWAV}
        WrongWAV {($p.HashInputs|Where-Object Path -EQ $p.OriginalWAV).SHA256='0'*64}
        WrongManifest {($p.HashInputs|Where-Object Path -EQ $p.SourceManifest).SHA256='0'*64}
        MissingState {$p.NativeDumpState=$null}
        StateHash {($p.HashInputs|Where-Object Path -EQ $p.NativeDumpState).SHA256='0'*64}
        StateSize {($p.HashInputs|Where-Object Path -EQ $p.NativeDumpState).Bytes=65116}
    }
    $failed=$false;try{Get-CodecProfile $p|Out-Null}catch{$failed=$true}
    if(!$failed){throw ('Profile accepted '+$case)};$checks++
}
$p=New-ProfileFixture NativeDumpF
foreach($case in 'Success','OpenLease','Unrestored','WrongWork','Failure','BooleanString','PromotedAlias','PromotedChecksum','PromotedFLAC'){
    $e=[pscustomobject]@{Schema='iw7.original-sound-ff-result/1';Status='SoundSABAndFFBytesVerified';Work=(Join-Path (Split-Path $p.NativeDumpState) 'work');
        RetainedLeaseToken=$null;Failure=$null;CleanupError=$null;Restored=$true;StockPreserved=$true;JobClosureVerified=$true;
        JobDisposeCompleted=$true;SourceHashesUnchanged=$true;ReadGuardsReleased=$true;Quarantined=$false;Ready=$false;PlaybackVerified=$false;
        Reader=[pscustomobject]@{dump_seek_frame_bytes_verified=$true;dump_streaminfo_rewritten=$true;dump_standalone_flac_validated=$false;native_alias_index_verified=$false;checksum_checksum_verified=$false}}
    switch($case){
        OpenLease {$e.RetainedLeaseToken='still-held'}
        Unrestored {$e.Restored=$false}
        WrongWork {$e.Work='different'}
        Failure {$e.Failure='failed'}
        BooleanString {$e.Reader.dump_streaminfo_rewritten='true'}
        PromotedAlias {$e.Reader.native_alias_index_verified=$true}
        PromotedChecksum {$e.Reader.checksum_checksum_verified=$true}
        PromotedFLAC {$e.Reader.dump_standalone_flac_validated=$true}
    }
    function Get-Content {param($LiteralPath,[switch]$Raw);if($LiteralPath -cne $p.NativeDumpState){throw 'Unexpected proof read'};$e|ConvertTo-Json -Depth 5}
    $failed=$false;try{Assert-CodecDumpEvidence $p}catch{$failed=$true}
    if($failed -ne ($case -ne 'Success')){throw ('Evidence fixture differed: '+$case)};$checks++
}
"$checks production profile/evidence checks passed with synthetic records; no payload files or native execution."
