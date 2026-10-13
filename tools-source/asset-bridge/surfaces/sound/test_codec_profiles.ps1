$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Invoke-SoundCodec.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Codec syntax failed'}
foreach($name in 'Assert-CodecKnownPin','Get-CodecProfile','Assert-CodecDumpEvidence','Assert-CodecDumpOnlyEvidence'){
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
    if($Profile -ceq 'NativeDumpOnlyC'){
        $dump=Join-Path $repo 'runtime/content-surfaces/original-sound-dump-only-a'
        $p.InputFLAC=Join-Path $dump 'work/dump/sdk_original_sound_v1/sound_assets/community/original_chime_v1.flac'
        $p.NativeDumpState=Join-Path $dump 'state.local.json'
        $flacHash='1f20e4e3d2ea9160c833ba2f188950908573c9bf677e63e10edf639efd40c725'
        $p.HashInputs+=,[pscustomobject]@{Path=$p.NativeDumpState;Bytes=62517;SHA256='761ef1246010482d9451e1feae1b7e0f2e75bcd0ea678a1ce70f294184d669df'}
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
foreach($name in 'OriginalSource','NativeDumpF','NativeDumpOnlyC'){
    $p=New-ProfileFixture $name;$result=Get-CodecProfile $p
    $expected=if($name -ceq 'OriginalSource'){'ThirdPartyPCMVerified'}else{'DumpDecodedByFFmpeg'}
    if($result.Name -cne $name -or $result.SuccessStatus -cne $expected){throw 'Closed profile positive failed'}
    $checks++
}
foreach($profile in 'NativeDumpF','NativeDumpOnlyC'){
foreach($case in 'Unknown','Boolean','Missing','HashSwap','WrongPath','WrongWAV','WrongManifest','MissingState','StateHash','StateSize'){
    $p=New-ProfileFixture $profile
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
foreach($case in 'Success','Lease','Restoration','Accounting','Guards','PhaseOrder','PhaseExit','OpenJob','EOF','OldCandidate','OldHeader','OldReader','OldF',
    'WrongDumpPath','WrongDumpHash','WrongDumpBytes','WrongDumpMetadata','WrongDumpTime','ReadPromotion','Quarantine','MissingDumpProof'){
    $p=New-ProfileFixture NativeDumpOnlyC
    $pin=@($p.HashInputs|Where-Object Path -EQ $p.InputFLAC)[0]
    $pin|Add-Member NoteProperty Attributes 32
    $pin|Add-Member NoteProperty ModifiedUtc '2026-10-12T18:23:07.7335219Z'
    $e=[pscustomobject]@{Schema='iw7.original-sound-ff-result/1';Profile='DumpOnly';Status='SoundDumpOnlyBytesVerified';Work=(Join-Path (Split-Path $p.NativeDumpState) 'work');
        RetainedLeaseToken=$null;Failure=$null;CleanupError=$null;Restored=$true;StockPreserved=$true;JobClosureVerified=$true;JobDisposeCompleted=$true;
        SourceHashesUnchanged=$true;ReadGuardsReleased=$true;Quarantined=$false;Ready=$false;PlaybackVerified=$false;RestorationStatus='Confirmed';
        OutputAccountingStatus='Converged';OutputBudgetError=$null;OutputAccountingError=$null;
        ImmutableFF=[pscustomobject]@{PlanSHA256='3d90a5746a8ee698fb08715e270f2855f261b318393257f91a9e7f59e3ad39d5';StateSHA256='d0a57123f7940eee29ef42da7440dd353e63eeffbfc025d37b162f4feda9e1a9'};
        DumpFlac=[pscustomobject]@{Path=$p.InputFLAC;Bytes=96394;SHA256=$pin.SHA256;Attributes=32;ModifiedUtc=$pin.ModifiedUtc};
        Reader=[pscustomobject]@{dump_profile='DumpOnlyC';dump_streaminfo_block_size=4096;inventory_provenance='PreservedBuildF';dump_seek_frame_bytes_verified=$true;
            dump_streaminfo_rewritten=$true;dump_alias_values_verified=$true;inventory_verified=$true;dump_standalone_flac_validated=$false;
            native_alias_index_verified=$false;checksum_checksum_verified=$false;playback_verified=$false;ready=$false};
        Phases=@(foreach($name in 'dump','read'){
            [pscustomobject]@{Phase=$name;NativeExecutableSHA256=$(if($name -ceq 'dump'){'cef411cf9b4de69be02cb4017aabd964e9143e340e211188daa6b6bab366493a'}else{'4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'});
                ExitCode=0;JobActiveAtClose=0;JobRootExitedAtClose=$true;SoundReceipt=[pscustomobject]@{verified=$true;explicit_normal_pipe_returns=$true;drain_exception_types=@()}}
        })}
    switch($case){
        Lease {$e.RetainedLeaseToken='held-fixture'}
        Restoration {$e.Restored=$false}
        Accounting {$e.OutputAccountingStatus='Unconfirmed'}
        Guards {$e.ReadGuardsReleased='true'}
        PhaseOrder {$e.Phases=@($e.Phases[1],$e.Phases[0])}
        PhaseExit {$e.Phases[0].ExitCode=1}
        OpenJob {$e.Phases[1].JobActiveAtClose=1}
        EOF {$e.Phases[0].SoundReceipt.explicit_normal_pipe_returns=$false}
        OldCandidate {$e.Phases[0].NativeExecutableSHA256='4740f0c22a1a7bab0b01f7a55ec0b133263ac218825ac3c0d15b9e269fe472b0'}
        OldHeader {$e.Reader.dump_streaminfo_block_size=1024}
        OldReader {$e.Reader.dump_profile='NativeDumpF'}
        OldF {$e.ImmutableFF.StateSHA256='0'*64}
        WrongDumpPath {$e.DumpFlac.Path=$p.OriginalWAV}
        WrongDumpHash {$e.DumpFlac.SHA256='a4e9276568dfeaf42d39deefe243b1efc2b9095b2f558bcb3512b98c417154d9'}
        WrongDumpBytes {$e.DumpFlac.Bytes=96393}
        WrongDumpMetadata {$e.DumpFlac.Attributes=0}
        WrongDumpTime {$e.DumpFlac.ModifiedUtc='2026-10-12T18:23:07.7335220Z'}
        ReadPromotion {$e.Reader.playback_verified=$true}
        Quarantine {$e.Quarantined=$true}
        MissingDumpProof {$e.DumpFlac=$null}
    }
    function Get-Content {param($LiteralPath,[switch]$Raw);if($LiteralPath -cne $p.NativeDumpState){throw 'Unexpected proof read'};$e|ConvertTo-Json -Depth 8}
    $failed=$false;$failure=$null;try{Assert-CodecDumpEvidence $p}catch{$failed=$true;$failure=$_.Exception.Message}
    if($failed -ne ($case -ne 'Success')){throw ('DumpOnly evidence fixture differed: '+$case+' / '+$failure)};$checks++
}
"$checks production profile/evidence checks passed with synthetic records; no payload files or native execution."
