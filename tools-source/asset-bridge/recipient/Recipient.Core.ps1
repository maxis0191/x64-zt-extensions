# Pure helpers only. Shared providers are explicitly pinned by the caller.
function Get-RecipientZoneOrder($Inputs) {
    $files=@($Inputs|ForEach-Object Relative)
    $candidates=@('techsets_global_core_mp','techsets_common_core_mp')
    foreach($zone in @('code_post_gfx','global','common','global_mp','global_cp','common_mp','common_cp','cp_zmb')){
        $candidates+=@(('techsets_'+$zone),$zone,('patch_'+$zone))
    }
    $available=@($candidates|Where-Object {('main/'+$_+'.ff') -cin $files -and ('zone/'+$_+'.ff') -cin $files})
    if('cp_zmb' -cnotin $available -or 'techsets_cp_zmb' -cnotin $available){throw 'Recipient base/techset stock absent from bound profile.'}
    $available
}
function Assert-RecipientZoneLog([string]$Log,$Expected) {
    if($Log -match '\[ ERROR \]|\[ FATAL \]|could not be found|Could not find referenced'){throw 'Native source-zone load reported errors.'}
    $observed=@(foreach($line in $Log -split '\r?\n'){
        if($line -cmatch '(?:Loading zone|zone) "([^"]+)" (?:is already loaded)'){$Matches[1]}
        elseif($line -cmatch 'Loading zone "([^"]+)"\.\.\.'){ $Matches[1] }
    })
    if(($observed -join "`n") -cne ($Expected -join "`n")){throw 'Exact source-zone order witness differs.'}
    $observed
}
function Assert-RecipientResult($Receipt,[string]$Phase,$Identity) {
    if($Receipt.schema -cne 'iw7.recipient-phase-result/1' -or $Receipt.phase -cne $Phase -or
       $Receipt.executable_sha256 -cne 'e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04' -or
       $Receipt.failure -or $Receipt.exit_code -ne 0 -or $Receipt.log_limit_each -ne 2MB -or !$Receipt.observation -or
       $Receipt.observation.closure_complete -ne $false -or $Receipt.observation.package_ready -ne $false -or
       $Identity.ExitCode -ne 0 -or $Identity.JobActiveAtClose -ne 0){throw 'Closed successful exact recipient phase required.'}
}
function Wait-RecipientPhase($Owner,$Identity,[double]$OuterSeconds,[double]$DrainSeconds,
    [scriptblock]$Elapsed,[scriptblock]$BudgetCheck,[scriptblock]$Save,
    [scriptblock]$Delay={Start-Sleep -Milliseconds 100}) {
    # Only query the original handles. The caller owns stop/disposal on failure.
    $drainStart=$null
    while($true){
        $rootExited=$Owner.Exited;$active=$Owner.Active;$seconds=[double](& $Elapsed)
        if($seconds -gt $OuterSeconds){throw 'Recipient phase deadline exceeded.'}
        if($rootExited){
            if($null -eq $drainStart){$drainStart=$seconds}
            $Identity.PostRootExitObservations+=,@{PhaseSeconds=$seconds;DrainSeconds=($seconds-$drainStart);Active=$active;RootExitCode=$Owner.ExitCode}
            & $Save
            if($active -eq 0){return}
            if($seconds-$drainStart -ge $DrainSeconds){throw 'Original job did not drain within five seconds after root exit.'}
        }
        & $BudgetCheck
        & $Delay
    }
}
function Get-RecipientPhases([switch]$ReferencesOnly) {
    'references'
    if(!$ReferencesOnly){'script'}
}
function Get-RecipientLimits([switch]$FatalTextDiagnostic) {
    if($FatalTextDiagnostic){[ordered]@{PhaseSeconds=45;OuterPhaseSeconds=50;OverallSeconds=60}}
    else{[ordered]@{PhaseSeconds=240;OuterPhaseSeconds=245;OverallSeconds=600}}
}
function New-RecipientPlan($Spec,[string]$Repo,[string]$Root,$Bindings,[switch]$ReferencesOnly,[switch]$FatalTextDiagnostic) {
    foreach($field in @('RunRoot','StockRoot','StockReceipt','StockBindingReceipt','RecipientStockBindingReceipt','ReviewedStockManifest','CandidateRoot','PythonExe','RequestRoot')){
        if(![IO.Path]::IsPathFullyQualified($Spec.$field)){throw "Absolute path required: $field"}
    }
    $runtime=Join-Path $Repo 'runtime'
    $run=Resolve-IW7BasePath $runtime ([IO.Path]::GetRelativePath($runtime,$Spec.RunRoot))
    if(Test-Path -LiteralPath $run){throw 'Fresh recipient run directory required.'}
    foreach($field in @('StockReceipt','StockBindingReceipt','RecipientStockBindingReceipt','ReviewedStockManifest','PythonExe')){Assert-BeaconHash $Spec.$field $Spec.($field+'SHA256')}
    $stock=Read-BeaconJson $Spec.StockReceipt;$observation=Read-BeaconJson $Spec.StockBindingReceipt
    $reviewed=Read-BeaconJson $Spec.ReviewedStockManifest
    $inputs=@(Get-FFStockBindingInputs $stock $observation $reviewed $Spec.StockRoot $Spec.StockReceiptSHA256 $Spec.ReviewedStockManifestSHA256)
    foreach($entry in $inputs){$entry|Add-Member NoteProperty BaselineMode $entry.Mode;$entry.Mode=if($entry.Relative -ceq 'main/fileSysCheck.cfg'){'Copy'}else{'HardLink'}}
    $supplemental=@(Get-RecipientSupplementalStockInputs (Read-BeaconJson $Spec.RecipientStockBindingReceipt) $reviewed $Spec.StockRoot $Spec.ReviewedStockManifestSHA256)
    $stockBudget=Get-RecipientStockBudget $inputs $supplemental
    $inputs+=@($supplemental)
    $requests=@(
        [ordered]@{Relative='recipient-material.csv';Source=(Join-Path $Spec.RequestRoot 'recipient-material-requests.csv');SHA256=$Spec.MaterialRequestSHA256},
        [ordered]@{Relative='recipient-scripts.txt';Source=(Join-Path $Spec.RequestRoot 'recipient-script-requests.txt');SHA256=$Spec.ScriptRequestSHA256})
    foreach($entry in $requests){Assert-BeaconHash $entry.Source $entry.SHA256;if((Get-Item -LiteralPath $entry.Source).Length -gt 4096){throw 'Recipient request too large.'}}
    $expected="material,mopw/character_park_clown_zombie_shoes`ntechset,mopw_l_sm_replace_i0c0s0o0n0p0`nimage,park_clown_zombie_shoes_n_3e46d100_packed_nog`nimage,park_clown_zombie_shoes_pink_c_park_clown_zombie_shoes_g_packed_cs`n"
    if([IO.File]::ReadAllText($requests[0].Source).Replace("`r`n","`n") -cne $expected -or
       [IO.File]::ReadAllText($requests[1].Source).Replace("`r`n","`n") -cne "scripts/engine/utility`n"){throw 'Exact recipient requests required.'}
    $candidate=Assert-BeaconCandidate $Spec.CandidateRoot $Spec.CandidateArtifactSHA256
    if($candidate.SHA256 -ine 'e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04'){throw 'E7 fulltool required.'}
    $sourceHashes=[ordered]@{}
    foreach($name in @('build-artifact.local.json','preparation.local.json','result.local.json')){
        $path=Join-Path $Spec.CandidateRoot $name;$sourceHashes[$path]=(Get-FileHash -LiteralPath $path).Hash
    }
    foreach($field in @('StockReceipt','StockBindingReceipt','RecipientStockBindingReceipt','ReviewedStockManifest','PythonExe')){$sourceHashes[$Spec.$field]=$Spec.($field+'SHA256')}
    foreach($entry in $requests){$sourceHashes[$entry.Source]=$entry.SHA256}
    foreach($name in @('recipient_phase.py','recipient_contract.py','recipient_dialog.py','Recipient.Core.ps1','Recipient.Stock.ps1','Recipient.Light.ps1','Run-RecipientClosure.ps1','provider-pins.json')){
        $path=Join-Path $Root $name;$sourceHashes[$path]=(Get-FileHash -LiteralPath $path).Hash
    }
    $limits=Get-RecipientLimits -FatalTextDiagnostic:$FatalTextDiagnostic
    [ordered]@{Schema='iw7.recipient-closure-plan/1';RunRoot=$run;Work=(Join-Path $run 'work');StockInputs=$inputs;StockBudget=$stockBudget;
        SourceZoneOrder=@(Get-RecipientZoneOrder $inputs);Candidate=$candidate;Requests=$requests;SourceHashes=$sourceHashes;
        ProviderBindings=$Bindings;PythonExe=$Spec.PythonExe;PythonSHA256=$Spec.PythonExeSHA256;
        Adapter=(Join-Path $Root 'recipient_phase.py');PhysicalBytes=8GB;CommitBytes=11GB;
        OutputStopBytes=256MB;LogBytesPerStream=2MB;PhaseSeconds=$limits.PhaseSeconds;OuterPhaseSeconds=$limits.OuterPhaseSeconds;RootExitDrainSeconds=5;OverallSeconds=$limits.OverallSeconds;
        FatalTextDiagnostic=[bool]$FatalTextDiagnostic;FatalTextCapturePhases=@('references');DiagnosticPollMilliseconds=250;DiagnosticTextBytes=16KB;DiagnosticControlLimit=8;DiagnosticMessageTimeoutMilliseconds=200;DiagnosticRecordBytes=64KB;
        Phases=@(Get-RecipientPhases -ReferencesOnly:($ReferencesOnly -or $FatalTextDiagnostic));NativeExecuted=$false;ClosureComplete=$false;Ready=$false}
}
