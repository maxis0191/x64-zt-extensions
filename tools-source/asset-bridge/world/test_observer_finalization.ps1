$ErrorActionPreference='Stop'
. "$PSScriptRoot/ObserverHarness.Core.ps1"
$script:checks=0
function Check($Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuse([scriptblock]$Body){$caught=$false;try{& $Body|Out-Null}catch{$caught=$true};Check $caught 'Failure fixture was accepted'}
$script:realMeasure=(Get-Item Function:\Measure-WorldObserverOutput).ScriptBlock
$script:realWrite=(Get-Item Function:\Write-WorldObserverJson).ScriptBlock
function Measure-WorldObserverOutput([string]$Root,[switch]$Final){
    $script:measureCalls++
    if(($script:mode -ceq 'accounting-before' -and $script:measureCalls -eq 1) -or
       ($script:mode -ceq 'accounting-after' -and $script:measureCalls -eq 2)){throw 'Mock accounting failure'}
    & $script:realMeasure $Root -Final:$Final
}
function Write-WorldObserverJson([string]$Path,$Value){
    if($script:mode -ceq 'publication'){throw 'Mock receipt publication failure'}
    & $script:realWrite $Path $Value
    if($script:mode -ceq 'receipt-content'){
        $raw=[IO.File]::ReadAllText($Path)
        # Same byte length passes accounting, but must fail exact snapshot hash.
        [IO.File]::WriteAllText($Path,$raw.Replace('BeforeLeaseRelease','XeforeLeaseRelease'),[Text.UTF8Encoding]::new($false))
    }
}
function Exit-IW7ResourceLease([string]$Token){
    $script:releaseCalls++
    Check ($Token -ceq 'original-mock-token') 'Wrong lease token'
    $receipt=Get-Content -LiteralPath (Join-Path $script:root 'run.json') -Raw|ConvertFrom-Json
    Check ($receipt.ReceiptStage -ceq 'BeforeLeaseRelease' -and !$receipt.LeaseReleased -and
        $receipt.RetainedLeaseToken -ceq $Token -and $receipt.LeaseReleaseState -ceq 'NotAttempted' -and
        !$receipt.FinalReceiptVerified -and $receipt.Status -cne 'SyntheticHarnessPassed') 'Receipt predicted scheduler success'
    Check ($script:state.FinalReceiptVerified -and $script:state.FinalReceiptSHA256 -and
        $receipt.FinalBytes -eq (& $script:realMeasure $script:root -Final)) 'Release before actual receipt verification/accounting'
    Refuse {$handle=[IO.File]::Open((Join-Path $script:root 'run.json'),'Open','Write','ReadWrite');$handle.Dispose()}
    if($script:mode -ceq 'release'){throw 'Mock ambiguous scheduler failure'}
}
$testRoot=Join-Path $PSScriptRoot ('.observer-finalization-test-'+[guid]::NewGuid().ToString('N'))
try {
    [IO.Directory]::CreateDirectory($testRoot)|Out-Null
    foreach($script:mode in 'success','accounting-before','publication','accounting-after','receipt-content','release','unclosed','changed-source','failed-native','deadline-before-release'){
        $script:root=Join-Path $testRoot $script:mode
        [IO.Directory]::CreateDirectory($script:root)|Out-Null
        [IO.File]::WriteAllText((Join-Path $script:root 'original.txt'),'original text fixture')
        $script:state=[ordered]@{Status='SyntheticHarnessPassed';JobClosureVerified=$true;SourceHashesUnchanged=$true;
            NativeHarnessPassed=$true;LeaseReleased=$false;LeaseReleaseState='NotAttempted';RetainedLeaseToken='original-mock-token';FinalBytes=$null}
        if($script:mode -ceq 'unclosed'){$script:state.JobClosureVerified=$false}
        if($script:mode -ceq 'changed-source'){$script:state.SourceHashesUnchanged=$false}
        if($script:mode -ceq 'failed-native'){$script:state.Status='Failed';$script:state.NativeHarnessPassed=$false}
        $lease=@{Token='original-mock-token'}
        $guards=[Collections.Generic.List[IDisposable]]::new()
        $script:releaseCalls=0;$script:measureCalls=0
        try {
            if($script:mode -in 'success','failed-native'){
                Complete-WorldObserverReservation $script:root $script:state $lease $guards
                Check ($script:releaseCalls -eq 1 -and $script:state.LeaseReleased -and
                    $null -eq $script:state.RetainedLeaseToken -and $script:state.LeaseReleaseState -ceq 'Confirmed') 'Confirmed release flags differ'
                if($script:mode -ceq 'success'){Check ($script:state.Status -ceq 'SyntheticHarnessPassed') 'Successful result lost'}
                else{Check ($script:state.Status -ceq 'Failed' -and !$script:state.NativeHarnessPassed) 'Failed native group became success'}
                $before=[IO.File]::ReadAllText((Join-Path $script:root 'run.json'))
                Refuse {Complete-WorldObserverReservation $script:root $script:state $lease $guards}
                Check ($script:releaseCalls -eq 1 -and $script:state.LeaseReleased -and
                    [IO.File]::ReadAllText((Join-Path $script:root 'run.json')) -ceq $before) 'Retry changed confirmed outcome or immutable receipt'
            }else{
                Refuse {Complete-WorldObserverReservation $script:root $script:state $lease $guards -BeforeReleaseCheck {
                    if($script:mode -ceq 'deadline-before-release'){throw 'Mock group deadline after receipt publication'}
                }}
                $expectedCalls=if($script:mode -ceq 'release'){1}else{0}
                $expectedRelease=if($script:mode -ceq 'release'){'Unconfirmed'}else{'NotAttempted'}
                Check ($script:releaseCalls -eq $expectedCalls -and !$script:state.LeaseReleased -and
                    $script:state.RetainedLeaseToken -ceq $lease.Token -and
                    $script:state.LeaseReleaseState -ceq $expectedRelease -and $script:state.Status -ceq 'Failed' -and
                    $script:state.FinalizationFailure) 'Failure released early or misreported its lease state'
                Check ($script:state.JobClosureVerified -eq ($script:mode -cne 'unclosed') -and
                    $script:state.SourceHashesUnchanged -eq ($script:mode -cne 'changed-source')) 'Finalization rewrote closure/source evidence'
                if($script:mode -ceq 'release'){
                    Refuse {Complete-WorldObserverReservation $script:root $script:state $lease $guards}
                    Check ($script:releaseCalls -eq 1 -and $script:state.LeaseReleaseState -ceq 'Unconfirmed') 'Ambiguous release retried'
                }
            }
        }finally{foreach($guard in $guards){$guard.Dispose()}}
    }
    $tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Run-ObserverHarness.ps1'),[ref]$tokens,[ref]$errors)
    Check (!$errors.Count) 'Runner parse'
    $commands=@($ast.FindAll({param($node)$node -is [Management.Automation.Language.CommandAst]},$true)|ForEach-Object{$_.GetCommandName()})
    Check ('Exit-IW7ResourceLease' -notin $commands -and 'Complete-WorldObserverReservation' -in $commands) 'Runner bypasses finalization gate'
}finally{
    $resolved=[IO.Path]::GetFullPath($testRoot)
    $prefix=[IO.Path]::GetFullPath($PSScriptRoot)+[IO.Path]::DirectorySeparatorChar+'.observer-finalization-test-'
    if(!$resolved.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Unexpected original-text fixture cleanup root.'}
    if(Test-Path -LiteralPath $resolved){Remove-Item -LiteralPath $resolved -Recurse -Force}
}
"PASS: $checks finalization/publication/accounting/lease-order checks with original text and a fake releaser; no real lease/native operation."
