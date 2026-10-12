$ErrorActionPreference='Stop'
. "$PSScriptRoot/SoundFF.Core.ps1"
. "$PSScriptRoot/../MaterialV2.Core.ps1"
. "$PSScriptRoot/../../../../sdk/modding/BeaconFF.Core.ps1"
$realSave=(Get-Command Save-SoundFFState).ScriptBlock
$temp=[IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetTempPath()) ('iw7-sound-accounting-'+[guid]::NewGuid().ToString('N'))))
[IO.Directory]::CreateDirectory($temp)|Out-Null
function Set-FixtureLength([string]$Path,[long]$Length){
    # Only logical file length is needed; never allocate a 64-MiB memory buffer
    # or read/hash the fixture payload. One near-limit file exists at a time.
    $stream=[IO.File]::Open($Path,'OpenOrCreate','Write','None')
    try{$stream.SetLength($Length)}finally{$stream.Dispose()}
}
try{
    foreach($case in 'Normal','NormalMetadataOverflow','PhaseFailure','ReleaseFailure','ReleaseErrorOverflow','FinalWriteFailure','PostReleaseWriteFailure','Nonconvergence','PersistentWriteFailure'){
        $root=Join-Path $temp $case;[IO.Directory]::CreateDirectory($root)|Out-Null
        $run=Join-Path $root 'run';[IO.Directory]::CreateDirectory($run)|Out-Null
        $planPath=Join-Path $root 'plan.json';[IO.File]::WriteAllText($planPath,'{}')
        $statePath=Join-Path $run 'state.local.json';$payload=Join-Path $run 'original-fixture.bin'
        $state=[ordered]@{Status='SoundSABAndFFBytesVerified';Inputs=@();Artifacts=@();Phases=@();Transaction=$null;
            Restored=$false;StockPreserved=$false;RestorationStatus='Pending';JobClosureVerified=$false;JobDisposeCompleted=$false;
            SourceHashesUnchanged=$false;ReadGuardsReleased=$false;Quarantined=$false;RetainedLeaseToken='mock-original-lease-token';
            Failure=$null;CleanupError=$null;MaxObservedBytes=0L;FinalObservedBytes=$null;OutputAccountingStatus='Pending';
            OutputAccountingError=$null;OutputBudgetError=$null;Ready=$false;PlaybackVerified=$false}
        if($case -eq 'PhaseFailure'){$state.Status='Failed';$state.Failure='Original phase failure with UTF-8: '+('é'*200)}
        $c=[pscustomobject]@{Plan=[pscustomobject]@{RunRoot=$run;Work=(Join-Path $run 'work');HashInputs=@()};PlanPath=$planPath;
            PlanSHA256=(Get-FileHash -LiteralPath $planPath).Hash;State=$state;StatePath=$statePath;Owner=$null;Closed=$true;Saved=$false;
            InputsGuarded=$false;Lease=[pscustomobject]@{Token='mock-original-lease-token'};Guards=[Collections.Generic.List[IDisposable]]::new()}
        & $realSave $c
        $initialReceipt=(Get-Item -LiteralPath $statePath).Length
        $nearLimit=$case -in 'NormalMetadataOverflow','ReleaseErrorOverflow'
        $length=if($case -eq 'NormalMetadataOverflow'){64MB-$initialReceipt-1}elseif($case -eq 'ReleaseErrorOverflow'){64MB-$initialReceipt-2048}else{999}
        Set-FixtureLength $payload $length
        $before=[long](Get-ChildItem -LiteralPath $run -File|Measure-Object Length -Sum).Sum
        if($before -ge 64MB){throw 'Initial fixture must be genuinely below 64 MiB'}
        $events=[Collections.Generic.List[string]]::new();$script:saveCalls=0;$script:releaseCalls=0;$script:releaseSucceeded=$false
        function Save-SoundFFState {param($Context)
            $script:saveCalls++
            if($case -eq 'PersistentWriteFailure' -or ($case -eq 'FinalWriteFailure' -and $script:saveCalls -eq 1) -or
                ($case -eq 'PostReleaseWriteFailure' -and $script:releaseSucceeded -and !$events.Contains('InjectedWriteFailure'))){
                $events.Add('InjectedWriteFailure');throw 'Injected state write failure'
            }
            & $realSave $Context
            if($case -eq 'Nonconvergence'){[IO.File]::AppendAllText((Join-Path $run 'growing-original-fixture.txt'),'x')}
        }
        function Exit-IW7ResourceLease {param($Token)
            $script:releaseCalls++
            $receipt=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
            $actual=[long](Get-ChildItem -LiteralPath $run -File|Measure-Object Length -Sum).Sum
            if($receipt.FinalObservedBytes -ne $actual -or $actual -gt 64MB -or $receipt.OutputBudgetError){throw 'Release lacked exact in-budget serialized receipt'}
            if($case -in 'ReleaseFailure','ReleaseErrorOverflow'){throw ('Mock release failure: '+('é'*2048))}
            $script:releaseSucceeded=$true
        }
        $threw=$false;try{Complete-SoundFFTransaction $c}catch{$threw=$true}
        if($threw -ne ($case -eq 'PersistentWriteFailure')){throw "Unexpected finalization exception in $case"}
        if($case -eq 'PersistentWriteFailure'){
            if($script:releaseCalls -or !$c.Lease -or $state.Status -ne 'Failed' -or $state.OutputAccountingStatus -ne 'Unconfirmed'){throw 'Persistent write failure released or claimed final accounting'}
        }else{
            $receipt=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
            $actual=[long](Get-ChildItem -LiteralPath $run -File|Measure-Object Length -Sum).Sum
            if($case -eq 'Nonconvergence'){
                if($receipt.OutputAccountingStatus -ne 'Unconfirmed' -or $null -ne $receipt.FinalObservedBytes -or $script:releaseCalls -or
                    $script:saveCalls -ne 9 -or !$receipt.RetainedLeaseToken -or $receipt.Status -ne 'Failed'){throw 'Nonconverging accounting did not fail bounded and retain lease'}
            }else{
                if($receipt.FinalObservedBytes -ne $actual -or $receipt.MaxObservedBytes -lt $actual -or $receipt.OutputAccountingStatus -ne 'Converged'){throw "Final serialized byte count differs in $case"}
                if($nearLimit){
                    if($actual -le 64MB -or !$receipt.OutputBudgetError -or !$receipt.Quarantined -or !$receipt.RetainedLeaseToken -or $script:releaseSucceeded){throw "Autoserialization did not prove overflow/quarantine in $case"}
                    if((Get-Item -LiteralPath $payload).Length -ne $length){throw 'Payload grew instead of serialized state'}
                    if($case -eq 'NormalMetadataOverflow' -and $script:releaseCalls){throw 'Over-budget receipt attempted lease release'}
                    if($case -eq 'ReleaseErrorOverflow' -and $script:releaseCalls -ne 1){throw 'Release-error serialization was not exercised'}
                }
                if($case -in 'ReleaseFailure','FinalWriteFailure' -and (!$receipt.Quarantined -or !$receipt.RetainedLeaseToken -or $receipt.Status -ne 'Failed' -or $script:releaseSucceeded)){throw 'Finalization failure failed to retain lease'}
                if($case -eq 'FinalWriteFailure' -and $script:releaseCalls){throw 'Failed pre-release receipt attempted release'}
                if($case -eq 'PostReleaseWriteFailure' -and (!$script:releaseSucceeded -or $receipt.RetainedLeaseToken -or $receipt.Status -ne 'Failed')){throw 'Post-release I/O failure misreported lease state'}
                if($case -in 'Normal','PhaseFailure' -and (!$script:releaseSucceeded -or $receipt.RetainedLeaseToken -or $receipt.OutputBudgetError)){throw 'Final normal/error release accounting failed'}
            }
        }
        # Exact owned file only; retain at most one near-64-MiB logical fixture.
        Remove-Item -LiteralPath $payload
    }
    if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7HudFileIdentity' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Native type loaded by accounting test'}
    '9 final-receipt accounting cases passed, including real 64-MiB autoserialization crossings, UTF-8 errors, write failures and bounded nonconvergence; no native job, lease or stock.'
}finally{
    $resolved=[IO.Path]::GetFullPath($temp)
    if(!$resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()),[StringComparison]::OrdinalIgnoreCase) -or
        (Split-Path $resolved -Leaf) -notlike 'iw7-sound-accounting-*'){throw 'Unsafe test cleanup target'}
    foreach($entry in @(Get-ChildItem -LiteralPath $resolved -Recurse -Force)){
        if($entry.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Unexpected redirected test entry'}
        if(!$entry.PSIsContainer){Remove-Item -LiteralPath $entry.FullName}
    }
    foreach($directory in @(Get-ChildItem -LiteralPath $resolved -Directory -Recurse|Sort-Object {$_.FullName.Length} -Descending)){Remove-Item -LiteralPath $directory.FullName}
    Remove-Item -LiteralPath $resolved
}
