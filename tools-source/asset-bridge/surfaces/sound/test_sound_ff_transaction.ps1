param([switch]$DumpOnly,[switch]$StandardMod)
$ErrorActionPreference='Stop'
if($DumpOnly -and $StandardMod){throw 'Select one profile.'}
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
. "$PSScriptRoot/SoundFF.Core.ps1"
$actualPhase=(Get-Command Invoke-SoundFFPhase).ScriptBlock
# The real file transaction and pure contracts are reused. Process/NTFS identity,
# native class initialization, stock and admission are explicit local mocks.
foreach($relative in 'ops/Base-Client.Core.ps1','sdk/modding/BeaconFF.Core.ps1','tools-source/asset-bridge/surfaces/MaterialV2.Core.ps1'){
    . (Join-Path $repo $relative)
}
$temp=[IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetTempPath()) ('iw7-sound-cycle-'+[guid]::NewGuid().ToString('N'))))
[IO.Directory]::CreateDirectory($temp)|Out-Null
try {
    $cases=@('Success','FactoryFailure','BuildFailure','VerifyFailure','DumpFailure','ReadFailure','ReadClaimFailure','ReadArtifactFailure','UnknownClosure','DisposeFailure','SourceDrift','RestoreFailure','PostRestoreDrift','ReleaseFailure')
    if($DumpOnly){$cases=@($cases|Where-Object {$_ -notin 'BuildFailure','VerifyFailure'})}
    if($StandardMod){$cases+=@('ReadZoneFailure','ReadNamesFailure','ReadFFFailure','ReadProfileFailure','ReadSourceFailure','ReadDumpZoneFailure','ReadInventoryFailure')}
    foreach($case in $cases){
        $caseRoot=Join-Path $temp $case;[IO.Directory]::CreateDirectory($caseRoot)|Out-Null
        $fixtureSource=Join-Path $caseRoot 'source';[IO.Directory]::CreateDirectory($fixtureSource)|Out-Null
        $fixtureRun=Join-Path $caseRoot 'run';$fixtureWork=Join-Path $fixtureRun 'work'
        $fixtureExe=Join-Path $caseRoot 'original-tool.txt';[IO.File]::WriteAllText($fixtureExe,'Original mock tool')
        $fixtureData=Join-Path $fixtureSource 'original.txt';[IO.File]::WriteAllText($fixtureData,'Original mock data')
        $fixturePlanPath=Join-Path $caseRoot 'plan.json';[IO.File]::WriteAllText($fixturePlanPath,'{}')
        $events=[Collections.Generic.List[string]]::new();$statePath=Join-Path $fixtureRun 'state.local.json'
        $plan=[pscustomobject]@{RunRoot=$fixtureRun;Work=$fixtureWork;SharedRepo=$repo;Python=$fixtureExe;CandidateRoot=$caseRoot;CandidateReceiptSHA256='mock';
            PhysicalBytes=1;CommitBytes=512MB;
            StockInputs=@();HashInputs=@((Get-SoundFFPin $fixtureData));MutableOutputs=@('zone/sdk_original_sound_v1.ff','zone/sdk_original_sound_v1.sabl','zone/sdk_original_sound_v1.sabs');
            Review=[pscustomobject]@{source=$fixtureSource;source_stage_relatives=@('original.txt');phase_adapter=(Join-Path $PSScriptRoot 'sound_ff_phase.py');phase_specs=@('build','verify','dump','read'|ForEach-Object {[pscustomobject]@{phase=$_}})}}
        $dataPin=$plan.HashInputs[0];$firstPhase=if($DumpOnly){'dump'}else{'build'}
        $zone=if($StandardMod){'mod'}else{'sdk_original_sound_v1'}
        if($StandardMod){
            $plan|Add-Member NoteProperty Profile 'StandardMod'
            $plan|Add-Member NoteProperty PayloadInputs @($dataPin)
            $plan|Add-Member NoteProperty ImmutableFF ([pscustomobject]@{Artifacts=@()})
            $plan.HashInputs=@();$plan.MutableOutputs=@('ff','sabl','sabs'|ForEach-Object {'zone/mod.'+$_})
        }
        if($DumpOnly){
            $plan|Add-Member NoteProperty Profile 'DumpOnly'
            $plan|Add-Member NoteProperty PayloadInputs @($dataPin)
            $plan.HashInputs=@();$plan.MutableOutputs=@();$plan.Review.source_stage_relatives=@()
            $plan.Review.phase_specs=@('dump','read'|ForEach-Object {[pscustomobject]@{phase=$_}})
            $artifacts=@(foreach($tuple in @(@('ff',128),@('sabl',114816),@('sabs',4096))){
                $path=Join-Path $caseRoot ('preserved.'+$tuple[0]);[IO.File]::WriteAllBytes($path,[byte[]]::new($tuple[1]))
                [pscustomobject]@{Relative=('zone/sdk_original_sound_v1.'+$tuple[0]);Bytes=$tuple[1];SHA256=(Get-FileHash -LiteralPath $path).Hash;ArtifactPath=$path}
            })
            $plan|Add-Member NoteProperty ImmutableFF ([pscustomobject]@{Artifacts=$artifacts})
        }
        function Import-SoundFFHelpers {}
        function Initialize-SoundFFNativeTypes {param($Repo);$events.Add('TypesMock')}
        function Enter-IW7ResourceLease {param($Scope,$Kind,$PhysicalBytes,$CommitBytes,$Owner)
            if($Scope -ne $fixtureWork -or $Kind -ne 'Extract' -or $PhysicalBytes -ne $plan.PhysicalBytes -or $CommitBytes -ne $plan.CommitBytes){throw 'Reviewed admission estimates changed.'}
            $events.Add('Admit');[pscustomobject]@{Token='mock-token'}
        }
        function Exit-IW7ResourceLease {param($Token)
            $receipt=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
            $actualBytes=Measure-MaterialV2OutputFiles @(Get-ChildItem -LiteralPath $fixtureRun -File -Recurse -Force) $fixtureWork $receipt.Inputs
            if($receipt.FinalObservedBytes -ne $actualBytes -or $receipt.OutputAccountingStatus -ne 'Converged' -or $receipt.OutputBudgetError){throw 'Lease release preceded complete serialized-state accounting'}
            $events.Add('Release');if($case -eq 'ReleaseFailure'){throw 'Mock release failure'}
        }
        function Assert-SoundFFChecksumCandidate {param($Root,$ReceiptSHA256,$StateSHA256,$Guards)
            [pscustomobject]@{Path=$fixtureExe;SHA256=(Get-FileHash -LiteralPath $fixtureExe).Hash}
        }
        function Assert-SoundFFFlacCandidate {param($Root,$ReceiptSHA256,$StateSHA256,$Guards)
            Assert-SoundFFChecksumCandidate $Root $ReceiptSHA256 $StateSHA256 $Guards
        }
        function Get-SoundFFFileId {param($Path)
            if($Path -ieq (Join-Path $fixtureWork 'zonetool.exe')){return $fixtureExe}
            if($Path -ieq (Join-Path $fixtureWork 'original.txt')){return $fixtureData}
            if($DumpOnly){foreach($a in $artifacts){if($Path -ieq (Join-Path $fixtureWork $a.Relative)){return $a.ArtifactPath}}}
            $Path
        }
        function Assert-FFStockIdentity {param($Entry,$ActualIdentity)}
        function Assert-ModelFFInputs {param($Inputs,$Work,[switch]$SourceOnly)
            foreach($entry in $Inputs){
                $file=Get-Item -LiteralPath $entry.Source
                if($file.Length -ne $entry.Bytes -or (Get-SoundFFFileId $entry.Source) -ne $entry.SourceId){throw 'Mock source identity changed'}
                if(!$SourceOnly -and $entry.PSObject.Properties['TargetId'] -and (Get-SoundFFFileId (Join-Path $Work $entry.Relative)) -ne $entry.TargetId){throw 'Mock target identity changed'}
            }
        }
        function Assert-FFStockContent {param($Inputs)
            $events.Add('Content')
            if($case -eq 'SourceDrift' -and $events.Contains($firstPhase)){throw 'Injected source drift'}
            if($case -eq 'PostRestoreDrift' -and $events.Contains('Restore')){throw 'Injected post-restore drift'}
            foreach($entry in $Inputs){if((Get-FileHash -LiteralPath $entry.Source).Hash -ine $entry.ExpectedSHA256){throw 'Mock source content changed'}}
        }
        function Assert-ModelFFVacant {param($Work)
            $events.Add('Vacant');if($case -eq 'RestoreFailure'){throw 'Injected restore vacancy refusal'}
        }
        # Keep the actual file-level restoration, with a call marker.
        $actualRestore=(Get-Command Restore-IW7BaseTransaction).ScriptBlock
        function Restore-IW7BaseTransaction {param($Transaction)
            $events.Add('Restore');& $actualRestore $Transaction
        }
        function Stop-MaterialV2OwnedPhase {param($Owner,$Evidence)
            $events.Add('Stop');$Evidence.Closed=($case -ne 'UnknownClosure');$Evidence.Closed
        }
        function New-SoundFFJob {param($Python,$Arguments,$Work)
            $events.Add('Factory');throw 'Injected factory exception without returned owner'
        }
        function Invoke-SoundFFPhase {param($Context,$Spec)
            if($case -eq 'FactoryFailure'){& $actualPhase $Context $Spec;return}
            $events.Add($Spec.phase)
            $Context.State.Phases+=,[ordered]@{Phase=$Spec.phase;Mock=$true}
            if($Spec.phase -eq 'build'){
                if($DumpOnly){throw 'DumpOnly regenerated F'}
                [IO.Directory]::CreateDirectory((Join-Path $fixtureWork 'zone'))|Out-Null
                foreach($tuple in @(@('ff',128),@('sabl',114816),@('sabs',4096))){[IO.File]::WriteAllBytes((Join-Path $fixtureWork ('zone/'+$zone+'.'+$tuple[0])),[byte[]]::new($tuple[1]))}
            }
            if(($case -eq ($Spec.phase+'Failure')) -or ($Spec.phase -eq $firstPhase -and $case -in 'UnknownClosure','DisposeFailure')){
                $owned=[pscustomobject]@{Events=$events;Case=$case}
                $owned|Add-Member ScriptMethod Dispose {$this.Events.Add('Dispose');if($this.Case -eq 'DisposeFailure'){throw 'Injected owner disposal failure'}}
                $Context.Owner=$owned;$Context.Closed=$false
                throw 'Injected phase failure'
            }
            if($DumpOnly -and $Spec.phase -eq 'dump'){
                $target=Join-Path $fixtureWork 'dump/sdk_original_sound_v1/sound_assets/community/original_chime_v1.flac'
                [IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
                [IO.File]::WriteAllText($target,'Synthetic mock dump only')
            }
            if($Spec.phase -eq 'read'){
                $logs=Join-Path $fixtureRun 'logs/read';[IO.Directory]::CreateDirectory($logs)|Out-Null
                $r=[ordered]@{schema='iw7.original-sound-sab-read/1';status='SABBytesVerified';loaded=@{pcm_sha256='72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9'};
                    source_alias_verified=$true;source_alias_matches_sab_asset=$true;dump_alias_values_verified=$true;inventory_verified=$true;inventory_asset_count=2;dump_seek_frame_bytes_verified=$true;
                    native_alias_index_verified=$false;checksum_checksum_verified=$false;dump_standalone_flac_validated=$false;playback_verified=$false;ready=$false;streamed=@{}}
                $r.loaded.bytes=$Context.State.Artifacts[1].Bytes;$r.loaded.sha256=$Context.State.Artifacts[1].SHA256
                $r.streamed.bytes=$Context.State.Artifacts[2].Bytes;$r.streamed.sha256=$Context.State.Artifacts[2].SHA256
                if($DumpOnly){$r.dump_profile='DumpOnlyC';$r.dump_streaminfo_block_size=4096;$r.inventory_provenance='PreservedBuildF'}
                if($StandardMod){
                    $r.dump_profile='StandardModC';$r.dump_streaminfo_block_size=4096;$r.inventory_provenance='CurrentVerifyPhase'
                    $r.bank_zone='mod';$r.disk_zone='mod';$r.standard_source_verified=$true;$r.dump_bank_zone_verified=$true
                    $r.standard_filenames_verified=$true;$r.standard_filenames=@('mod.ff','mod.sabl','mod.sabs')
                    $r.fastfile=@{bytes=$Context.State.Artifacts[0].Bytes;sha256=$Context.State.Artifacts[0].SHA256}
                    switch($case){
                        'ReadZoneFailure' {$r.bank_zone='sdk_original_sound_v1'}
                        'ReadNamesFailure' {$r.standard_filenames[0]='other.ff'}
                        'ReadFFFailure' {$r.fastfile.sha256='0'*64}
                        'ReadProfileFailure' {$r.dump_profile='DumpOnlyC'}
                        'ReadSourceFailure' {$r.standard_source_verified=$false}
                        'ReadDumpZoneFailure' {$r.dump_bank_zone_verified=$false}
                        'ReadInventoryFailure' {$r.inventory_provenance='PreservedBuildF'}
                    }
                }
                if($case -eq 'ReadClaimFailure'){$r.playback_verified=$true}
                if($case -eq 'ReadArtifactFailure'){$r.loaded.sha256='0'*64}
                [IO.File]::WriteAllText((Join-Path $logs 'stdout.log'),($r|ConvertTo-Json -Depth 5))
            }
        }
        $failed=$false
        try{$null=Invoke-SoundFFTransaction $plan $fixturePlanPath (Get-FileHash -LiteralPath $fixturePlanPath).Hash}catch{$failed=$true}
        if(!(Test-Path -LiteralPath $statePath)){throw "Missing state in $case"}
        $state=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
        $actualBytes=Measure-MaterialV2OutputFiles @(Get-ChildItem -LiteralPath $fixtureRun -File -Recurse -Force) $fixtureWork $state.Inputs
        if($state.FinalObservedBytes -ne $actualBytes -or $state.MaxObservedBytes -lt $actualBytes -or $state.OutputAccountingStatus -ne 'Converged'){throw "Last state write missing from counters in $case"}
        $quarantine=$case -in 'FactoryFailure','UnknownClosure','DisposeFailure','SourceDrift','RestoreFailure','PostRestoreDrift','ReleaseFailure'
        if($failed -ne ($case -ne 'Success')){throw "Wrong overall outcome in $case : $($state.Failure) / $($state.CleanupError)"}
        if($state.Quarantined -ne $quarantine){throw "Wrong quarantine in $case : $($state.CleanupError)"}
        if($quarantine -and (!$state.RetainedLeaseToken -or $state.SourceHashesUnchanged)){throw "False integrity/release in $case"}
        if(!$quarantine -and (!$state.Restored -or !$state.StockPreserved -or $state.RetainedLeaseToken)){throw "Normal restore/release missing in $case"}
        if(!$state.ReadGuardsReleased){throw "Guard release not reported in $case"}
        $mutable=@($state.Transaction.Files.Path)
        foreach($relative in $plan.MutableOutputs){if($relative -notin $mutable){throw 'Missing FF/SAB transaction output'}}
        if($case -eq 'Success'){
            $order=if($DumpOnly){'dump,read'}else{'build,verify,dump,read'}
            if(($state.Phases.Phase -join ',') -ne $order -or $state.Artifacts.Count -ne 3){throw 'Exact phases/three artifacts required'}
            if($StandardMod -and ($state.Status -cne 'SoundStandardModBytesVerified' -or ($state.Artifacts.Relative -join ',') -cne 'zone/mod.ff,zone/mod.sabl,zone/mod.sabs')){throw 'Standard result/artifacts differ'}
            if($DumpOnly){
                if($state.Status -ne 'SoundDumpOnlyBytesVerified' -or !$state.DumpFlac){throw 'DumpOnly status/hash absent'}
                foreach($a in $artifacts){
                    if((Get-FileHash -LiteralPath $a.ArtifactPath).Hash -ne $a.SHA256 -or (Test-Path -LiteralPath (Join-Path $fixtureWork $a.Relative))){throw 'Immutable F changed or staged link not restored'}
                }
                if(($state.Artifacts.ArtifactPath -join ',') -cne ($artifacts.ArtifactPath -join ',')){throw 'DumpOnly copied/replaced F artifacts'}
            }
            foreach($relative in @('original.txt','zonetool.exe')+$plan.MutableOutputs){if(Test-Path -LiteralPath (Join-Path $fixtureWork $relative)){throw 'Actual fixture target not restored/unlinked'}}
            if($events.IndexOf('Release') -lt $events.LastIndexOf('Content')){throw 'Release preceded final source proof'}
        }
        if($case -in 'FactoryFailure','UnknownClosure','DisposeFailure','SourceDrift','RestoreFailure' -and $events.Contains('Restore')){throw 'Unproven state restored files'}
        if($case -eq 'FactoryFailure' -and (!$events.Contains('Factory') -or $events.Contains('Stop') -or $state.JobClosureVerified -or $state.Restored -or $state.Failure -notlike '*factory exception*')){throw 'Factory exception did not preserve unknown closure'}
        if($case -ne 'ReleaseFailure' -and $quarantine -and $events.Contains('Release')){throw 'Quarantined lease release attempted'}
        if($case -eq 'PostRestoreDrift' -and $state.RestorationStatus -ne 'FilesRestoredUnverified'){throw 'Post-restore uncertainty not recorded'}
        if((Get-FileHash -LiteralPath $fixtureData).Hash -ne $dataPin.SHA256){throw 'Original fixture changed'}
        # Reset the real provider before the next local function captures it.
        Set-Item -Path Function:Restore-IW7BaseTransaction -Value $actualRestore
    }
    if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7HudFileIdentity' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Unexpected native class loaded'}
    "$($cases.Count) actual transaction-flow cases passed (DumpOnly=$DumpOnly; StandardMod=$StandardMod) with mock ownership/admission and real tiny-file backup/restore; no native process or stock."
} finally {
    # Delete only the verified test root's own files, then its empty directories.
    $resolved=[IO.Path]::GetFullPath($temp)
    if(!$resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()),[StringComparison]::OrdinalIgnoreCase) -or
        (Split-Path $resolved -Leaf) -notlike 'iw7-sound-cycle-*'){throw 'Unsafe test cleanup target'}
    foreach($entry in @(Get-ChildItem -LiteralPath $resolved -Recurse -Force)){
        if($entry.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Unexpected redirect in test root'}
        if(!$entry.PSIsContainer){Remove-Item -LiteralPath $entry.FullName}
    }
    foreach($directory in @(Get-ChildItem -LiteralPath $resolved -Directory -Recurse|Sort-Object {$_.FullName.Length} -Descending)){Remove-Item -LiteralPath $directory.FullName}
    Remove-Item -LiteralPath $resolved
}
