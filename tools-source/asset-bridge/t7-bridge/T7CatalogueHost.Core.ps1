# Functions only. The existing runner/H1 primitives retain native ownership.
Set-StrictMode -Version Latest
function Get-T7CatalogueHostSchema($Plan,[string]$Kind) {
    $export=[bool]($Plan.PSObject.Properties['Operation'] -and $Plan.Operation -ceq 'ResidentExportV1')
    if($Plan.PSObject.Properties['Operation'] -and ($Plan.Operation -isnot [string] -or $Plan.Operation -cnotin @('Catalogue','ResidentExportV1'))){throw 'Unknown T7 host operation.'}
    $prefix=if($export){'iw7.t7-resident-export-'}else{'iw7.t7-catalogue-'}
    $prefix+$Kind+'/1'
}
function Get-T7CatalogueHostOutcomeName($Plan) {
    if((Get-T7CatalogueHostSchema $Plan 'run') -ceq 'iw7.t7-resident-export-run/1'){'ExportOutcome'}else{'CatalogueOutcome'}
}
function Get-T7CatalogueHostIdentity {
    $process=[Diagnostics.Process]::GetCurrentProcess()
    [pscustomobject]@{PID=$PID;CreatedUtc=$process.StartTime.ToUniversalTime().ToString('o');Image=$process.MainModule.FileName}
}
function Write-T7CatalogueHostEvidence([string]$Path,$Value) {
    Assert-H1Path $Path
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 12)+"`n")
    if($bytes.Length -gt 128KB){throw 'Host evidence exceeds bound.'}
    $stream=[IO.FileStream]::new($Path,'CreateNew','Write','Read')
    try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
function Close-T7CatalogueHostGuards($State) {
    foreach($guard in $State.Guards){$guard.Dispose()}
    if(@($State.Guards|Where-Object {!$_.SafeFileHandle.IsClosed}).Count){throw 'Host guards remain open.'}
    $State.Guards.Clear()
}
function Open-T7CatalogueHostInputs([string]$PlanPath,[string]$PlanSHA256,[string]$RunRoot,
    [string]$HostContractPath,[string]$HostContractSHA256,[string]$EntryPath,[string]$Repo) {
    $guards=[Collections.Generic.List[object]]::new()
    $state=[pscustomobject]@{PlanPath=$PlanPath;PlanSHA256=$PlanSHA256;RunRoot=$RunRoot;
        ContractPath=$HostContractPath;ContractSHA256=$HostContractSHA256;EntryPath=$EntryPath;
        Plan=$null;Contract=$null;Guards=$guards;Host=$null;Phase='Prepared';RunnerReturned=$false;
        RunnerReturnedUtc=$null;RunnerError=$null;CanExit=$false;ClosureError=$null;
        IncidentAttempted=$false;IncidentCanExit=$false;IncidentError=$null}
    try {
        foreach($pair in @(@($HostContractPath,$HostContractSHA256,32KB),@($PlanPath,$PlanSHA256,128KB))){
            Assert-H1Path $pair[0];$file=Get-Item -LiteralPath $pair[0]
            if($file.PSIsContainer -or $file.Length -gt $pair[2]){throw 'Host contract/plan exceeds bound.'}
            $guards.Add((Open-H1Pin ([pscustomobject]@{Path=$pair[0];Bytes=$file.Length;SHA256=$pair[1]})))
        }
        $contract=Read-H1SmallJson $HostContractPath 32KB;$plan=Read-H1SmallJson $PlanPath
        $runner=Join-Path (Split-Path $EntryPath -Parent) 'Run-T7Catalogue.ps1'
        $core=Join-Path (Split-Path $EntryPath -Parent) 'T7CatalogueHost.Core.ps1'
        $h1=Join-Path $Repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1'
        Assert-H1Path $RunRoot;Assert-H1Path $contract.HostImage
        if($contract.Schema -cne (Get-T7CatalogueHostSchema $plan 'host') -or $contract.PlanPath -cne $PlanPath -or
           $contract.PlanSHA256 -cne $PlanSHA256 -or $contract.RunRoot -cne $RunRoot -or
           $plan.RunRoot -cne $RunRoot -or $plan.Runner -cne $runner -or
           [IO.Path]::GetDirectoryName($RunRoot) -cne (Join-Path $Repo 'runtime') -or
           $plan.StageRoot -cne (Join-Path $RunRoot 'evidence') -or
           @($contract.SourcePins).Count -ne 3 -or @($contract.PreservedProcesses).Count -gt 16){throw 'Exact host contract/plan identity required.'}
        foreach($path in @($EntryPath,$core,$h1)){
            $pins=@($contract.SourcePins|Where-Object Path -CEQ $path)
            if($pins.Count -ne 1 -or $pins[0].Bytes -le 0 -or $pins[0].Bytes -gt 1MB){throw 'Exact wrapper source pin missing.'}
            $guards.Add((Open-H1Pin $pins[0]))
        }
        $preservedIds=[Collections.Generic.HashSet[int]]::new()
        foreach($identity in $contract.PreservedProcesses){
            if($identity.PID -isnot [long] -and $identity.PID -isnot [int]){throw 'Preserved process PID must be an integer.'}
            if($identity.PID -le 0 -or !$preservedIds.Add($identity.PID)){throw 'Distinct preserved process identities required.'}
            $null=[datetimeoffset]::Parse($identity.CreatedUtc);Assert-H1Path $identity.Image
        }
        if(@($plan.Bindings).Count -gt 256){throw 'Bounded plan source collection required.'}
        foreach($pin in $plan.Bindings|Where-Object IsText){
            if($pin.Bytes -le 0 -or $pin.Bytes -gt 1MB){throw 'Bounded source binding required.'}
            $guards.Add((Open-H1Pin $pin))
        }
        foreach($path in @($runner,$h1,(Join-Path $Repo 'ops/Resource-Scheduler.Core.ps1'),
            (Join-Path $Repo 'ops/Resource-Memory.ps1'),(Join-Path $Repo 'ops/Resource-RecorderOwnedProcess.Core.ps1'),
            (Join-Path (Split-Path $EntryPath -Parent) 'T7Prepatch.Profile.ps1'),
            (Join-Path (Split-Path $EntryPath -Parent) 'T7Catalogue.Profile.ps1'))){
            if(@($plan.Bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -eq $true}).Count -ne 1){throw 'Required pinned host dependency missing.'}
        }
        if((Get-T7CatalogueHostOutcomeName $plan) -ceq 'ExportOutcome' -or
           ($plan.PSObject.Properties['CandidateProfile'] -and $plan.CandidateProfile -ceq 't7-zombies-catalogue-observation-c')){
            $exportProfile=Join-Path (Split-Path $EntryPath -Parent) 'T7ResidentExport.Profile.ps1'
            if(@($plan.Bindings|Where-Object {$_.Path -ceq $exportProfile -and $_.IsText -eq $true}).Count -ne 1){throw 'Required pinned export dependency missing.'}
        }
        $state.Plan=$plan;$state.Contract=$contract
        return $state
    }catch{Close-T7CatalogueHostGuards $state;throw}
}
function Assert-T7CatalogueHostArguments($State,[string[]]$ActualArguments,$HostIdentity) {
    $expected=@($State.Contract.HostImage,'-NoLogo','-NoProfile','-NoExit','-File',$State.EntryPath,
        '-PlanPath',$State.PlanPath,'-PlanSHA256',$State.PlanSHA256,'-RunRoot',$State.RunRoot,
        '-HostContractPath',$State.ContractPath,'-HostContractSHA256',$State.ContractSHA256,'-Run')
    if($HostIdentity.Image -cne $State.Contract.HostImage -or $ActualArguments.Count -ne $expected.Count){throw 'Fresh exact NoProfile/NoExit host arguments required.'}
    # Managed pwsh reports pwsh.dll in argv[0]; the executable is checked above.
    for($index=1;$index -lt $expected.Count;$index++){
        if($ActualArguments[$index] -cne $expected[$index]){throw 'Fresh exact NoProfile/NoExit host arguments required.'}
    }
}
function Assert-T7CatalogueHostReceipt($State,$Receipt) {
    if($Receipt.Schema -cne (Get-T7CatalogueHostSchema $State.Plan 'run') -or $Receipt.PlanSHA256 -cne $State.PlanSHA256){throw 'Receipt belongs to another plan.'}
    foreach($name in @('TreeClosureConfirmed','LeaseReleased','InputsReverified','OriginalInputMetadataUnchanged','AliasesRetained')){
        if($Receipt.$name -isnot [bool] -or !$Receipt.$name){throw ('Receipt lacks closure proof: '+$name)}
    }
    Assert-T7CatalogueHostReceiptIdentity $State $Receipt
}
function Assert-T7CatalogueHostReceiptIdentity($State,$Receipt) {
    if($Receipt.Schema -cne (Get-T7CatalogueHostSchema $State.Plan 'run') -or $Receipt.PlanSHA256 -cne $State.PlanSHA256){throw 'Receipt belongs to another plan.'}
    if($Receipt.Quarantined -isnot [bool] -or $Receipt.Quarantined -or
       $Receipt.Identity.PID -le 0 -or $Receipt.Identity.PID -eq $State.Host.PID -or
       $Receipt.Identity.Image -cne $State.Plan.Image -or $Receipt.LeaseToken -cnotmatch '^[0-9a-f]{32}$'){
        throw 'Receipt native identity or quarantine differs.'
    }
    $started=([datetimeoffset]$Receipt.StartedUtc).UtcTicks;$created=([datetimeoffset]$Receipt.Identity.CreatedUtc).UtcTicks
    $finished=([datetimeoffset]$Receipt.FinishedUtc).UtcTicks
    if($started -lt ([datetimeoffset]$State.Host.CreatedUtc).UtcTicks -or $created -lt $started -or
       $created -gt $finished -or $finished -gt ([datetimeoffset]$State.RunnerReturnedUtc).UtcTicks){throw 'Receipt native lifetime is outside this host invocation.'}
    $metadata=@($State.Plan.InputMetadata);$originals=@($Receipt.InputFileIds);$aliases=@($Receipt.Aliases)
    if($originals.Count -ne $metadata.Count -or $aliases.Count -ne $metadata.Count){throw 'Receipt identity count differs.'}
    $ids=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($item in $metadata){
        $matches=@($originals|Where-Object Path -CEQ $item.Path)
        if($matches.Count -ne 1 -or !$matches[0].FileId -or !$ids.Add($matches[0].FileId)){throw 'Receipt original identity mapping differs.'}
    }
    $links=@(@($State.Plan.CandidateSource,'t7-zonetool-candidate.exe'),@($State.Plan.EngineSource,'BlackOps3_UnrankedDedicatedServer.exe'),
        @($State.Plan.SteamSource,'steam_api64.dll'),@($State.Plan.Zone.Path,$State.Plan.Zone.RelativePath))
    foreach($bootstrap in @(Get-T7CatalogueBootstraps $State.Plan)){$links+=,@($bootstrap.Path,$bootstrap.RelativePath)}
    if($State.Plan.PSObject.Properties['SelectedStreamedStaticV1'] -or $State.Plan.PSObject.Properties['SelectedStreamedRenderOnlyV2']){
        $links+=,@($State.Plan.ExportRequestFile.Path,'streamed-request.json')
        $links+=,@($State.Plan.SelectedXpakProvider.Metadata.Path,$State.Plan.SelectedXpakProvider.RelativePath)
    }
    if($links.Count -ne $metadata.Count){throw 'Plan alias count differs.'}
    foreach($link in $links){
        $original=@($originals|Where-Object Path -CEQ $link[0])
        $alias=@($aliases|Where-Object Path -CEQ (Join-Path $State.Plan.WorkingDirectory $link[1]))
        if($original.Count -ne 1 -or $alias.Count -ne 1 -or $alias[0].FileId -cne $original[0].FileId){throw 'Receipt alias identity mapping differs.'}
    }
}
function Assert-T7CataloguePreservedProcesses($Contract,$Processes) {
    foreach($identity in $Contract.PreservedProcesses){
        $matches=@($Processes|Where-Object PID -EQ $identity.PID)
        if($matches.Count -ne 1 -or !(Test-IW7ResourceIdentity $identity $matches[0])){throw 'Preserved process identity differs.'}
    }
}
function Assert-T7CatalogueHostObservation($State,$Receipt,$Status,$Processes,$CurrentHost) {
    if(!(Test-IW7ResourceIdentity $State.Host $CurrentHost)){throw 'Same host identity required; PID reuse refused.'}
    $hosts=@($Processes|Where-Object PID -EQ $State.Host.PID)
    if($hosts.Count -ne 1 -or !(Test-IW7ResourceIdentity $State.Host $hosts[0])){throw 'Scheduler host identity differs.'}
    if(@($Status.Leases).Count){throw 'A lease remains; retain host.'}
    foreach($process in $Processes){
        if($process.PID -eq $Receipt.Identity.PID -or
           ($process.Image -and $process.Image.StartsWith($State.RunRoot+'\',[StringComparison]::OrdinalIgnoreCase)) -or
           (!$process.Image -and $process.Name -ieq [IO.Path]::GetFileName($Receipt.Identity.Image))){throw 'Native root, reused PID or ambiguous run process remains.'}
        if($process.Lab -or $process.Name -match '^(zonetool.*|t7-.*|MSBuild|cl|link|java|DepotDownloader|steamcmd)\.exe$'){throw 'Heavy process remains; retain host.'}
    }
    Assert-T7CataloguePreservedProcesses $State.Contract $Processes
}
function Assert-T7CatalogueHostReturn($State) {
    if(!$State.Guards.Count -or @($State.Guards|Where-Object {$_.SafeFileHandle.IsClosed}).Count){throw 'Source/plan guard lost before closure.'}
    $startProof=Read-H1SmallJson ($State.RunRoot+'.host-start.json')
    $returnProof=Read-H1SmallJson ($State.RunRoot+'.host-return.json')
    foreach($proof in @($startProof,$returnProof)){
        if($proof.PlanSHA256 -cne $State.PlanSHA256 -or $proof.ContractSHA256 -cne $State.ContractSHA256 -or
           !(Test-IW7ResourceIdentity $State.Host $proof.Host)){throw 'Host start/return proof differs.'}
    }
    if($returnProof.RunnerReturned -isnot [bool] -or !$returnProof.RunnerReturned -or
       ([datetimeoffset]$returnProof.RunnerReturnedUtc).UtcTicks -ne ([datetimeoffset]$State.RunnerReturnedUtc).UtcTicks){throw 'Host return proof differs.'}
}
function Get-T7CatalogueHostClosureObservation($State,$Receipt) {
    if($null -ne [AppDomain]::CurrentDomain.GetData('IW7.H1.Quarantine.'+$Receipt.LeaseToken)){throw 'Native quarantine remains; retain host.'}
    $attempt=Read-H1SmallJson (Join-Path $State.RunRoot 'attempt.json')
    if($attempt.Schema -cne (Get-T7CatalogueHostSchema $State.Plan 'attempt') -or $attempt.PlanSHA256 -cne $State.PlanSHA256 -or
       ([datetimeoffset]$attempt.StartedUtc).UtcTicks -lt ([datetimeoffset]$State.Host.CreatedUtc).UtcTicks -or
       ([datetimeoffset]$attempt.StartedUtc).UtcTicks -gt ([datetimeoffset]$Receipt.StartedUtc).UtcTicks){throw 'Attempt marker differs.'}
    $status=Get-IW7ResourceStatus;$processes=@(Get-IW7ResourceProcesses)
    Assert-T7CatalogueHostObservation $State $Receipt $status $processes (Get-T7CatalogueHostIdentity)
    $main=Assert-T7CatalogueMain $State.Plan
    foreach($row in $State.Plan.InputMetadata){Assert-T7CatalogueMetadata $row}
    foreach($row in @($Receipt.InputFileIds)+@($Receipt.Aliases)){
        if((Get-T7CatalogueFileId $row.Path) -cne $row.FileId){throw 'Original/alias file identity changed.'}
    }
    [pscustomobject]@{Main=$main;Processes=$processes}
}
function Complete-T7CatalogueHost($State) {
    $outcomeName=Get-T7CatalogueHostOutcomeName $State.Plan
    if([AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost') -ne $State -or
       !$State.RunnerReturned -or $State.Phase -cnotin @('Returned','ClosurePending')){throw 'Same returned host state required; no re-entry.'}
    $State.CanExit=$false
    $State.Phase='ClosurePending'
    try {
        Assert-T7CatalogueHostReturn $State
        $receipt=Read-H1SmallJson (Join-Path $State.Plan.StageRoot 'receipt.json') 512KB
        Assert-T7CatalogueHostReceipt $State $receipt
        $observation=Get-T7CatalogueHostClosureObservation $State $receipt
        $proof=[ordered]@{Schema=(Get-T7CatalogueHostSchema $State.Plan 'host-closure');CapturedUtc=[DateTime]::UtcNow.ToString('o');
            Host=$State.Host;Native=$receipt.Identity;PlanSHA256=$State.PlanSHA256;ContractSHA256=$State.ContractSHA256;
            Main=$observation.Main;MetadataCount=@($State.Plan.InputMetadata).Count;FileIdsCount=2*@($State.Plan.InputMetadata).Count;
            LeaseCount=0;HeavyCount=0;QuarantinePresent=$false;RootPresent=$false;PreservedProcessesUnchanged=$true;
            RuntimeStatus=$receipt.Status;($outcomeName)=$receipt.$outcomeName;PayloadHashesReadAfterRelease=$false;
            RunnerGuardDisposalEvidence='Pinned runner finally clears guards after native closure and release, before the observed wrapper return.';
            ActualPTYExitObserved=$false;IndependentAbsencePending=$true}
        # Publish proof before disposing wrapper guards. CanExit is not inferred from a file.
        Write-T7CatalogueHostEvidence ($State.RunRoot+'.host-postflight.json') $proof
        Close-T7CatalogueHostGuards $State
        $State.Phase='Closed';$State.CanExit=$true;$State.ClosureError=$null
        [ordered]@{Postflight='Passed';HostPID=$State.Host.PID;CanExit=$true;WrapperGuardCount=$State.Guards.Count;
            ($outcomeName)=$receipt.$outcomeName;ActualPTYExitObserved=$false;IndependentAbsencePending=$true}|ConvertTo-Json
    }catch{$State.ClosureError=$_.Exception.Message;throw}
}
function Complete-T7CatalogueHostIncident($State,[string]$ReceiptSHA256) {
    $outcomeName=Get-T7CatalogueHostOutcomeName $State.Plan
    # This is an explicit failure closure, never a replacement for normal Finish.
    if([AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost') -ne $State -or
       !$State.RunnerReturned -or $State.Phase -cnotin @('Returned','ClosurePending') -or
       $State.CanExit -or $State.IncidentCanExit -or $State.IncidentAttempted){
        throw 'Same returned incident host required; no re-entry after publication/disposal attempt.'
    }
    $receiptGuard=$null
    try {
        if($ReceiptSHA256 -cnotmatch '\A[0-9a-f]{64}\z'){throw 'Exact failed receipt SHA256 required.'}
        Assert-T7CatalogueHostReturn $State
        $preflightPath=$State.RunRoot+'.host-incident-preflight.json'
        $postflightPath=$State.RunRoot+'.host-incident-postflight.json'
        foreach($path in @($preflightPath,$postflightPath)){
            Assert-H1Path $path
            if(Test-Path -LiteralPath $path){throw 'Incident evidence already exists; retain host for review.'}
        }
        $receiptPath=Join-Path $State.Plan.StageRoot 'receipt.json'
        Assert-H1Path $receiptPath;$file=Get-Item -LiteralPath $receiptPath
        if($file.PSIsContainer -or $file.Length -gt 512KB){throw 'Bounded failed receipt required.'}
        # The only new hash is bounded JSON, held immutable throughout validation.
        $receiptGuard=Open-H1Pin ([pscustomobject]@{Path=$receiptPath;Bytes=$file.Length;SHA256=$ReceiptSHA256})
        $receipt=Read-H1SmallJson $receiptPath 512KB
        if($receipt.Status -cne 'Failed' -or $receipt.InputsReverified -isnot [bool] -or $receipt.InputsReverified){
            throw 'Incident closure requires Failed with InputsReverified=false.'
        }
        foreach($name in @('TreeClosureConfirmed','LeaseReleased')){
            if($receipt.$name -isnot [bool] -or !$receipt.$name){throw ('Receipt lacks incident closure proof: '+$name)}
        }
        Assert-T7CatalogueHostReceiptIdentity $State $receipt
        $observation=Get-T7CatalogueHostClosureObservation $State $receipt
        foreach($process in $observation.Processes){
            if(!$process.PSObject.Properties['ParentPID']){throw 'Incident process ancestry unavailable.'}
            if($process.ParentPID -eq $State.Host.PID -or $process.ParentPID -eq $receipt.Identity.PID -or
               $process.Name -match '^(iw7.*|BlackOps3.*)\.exe$'){
                throw 'Client or original host/native child remains; retain incident host.'
            }
        }
        $guardSnapshot=@($State.Guards|ForEach-Object {$_})
        $proof=[ordered]@{Schema=(Get-T7CatalogueHostSchema $State.Plan 'host-incident-preflight');CapturedUtc=[DateTime]::UtcNow.ToString('o');
            Host=$State.Host;Native=$receipt.Identity;PlanSHA256=$State.PlanSHA256;ContractSHA256=$State.ContractSHA256;
            ReceiptSHA256=$ReceiptSHA256;RuntimeStatus=$receipt.Status;($outcomeName)=$receipt.$outcomeName;
            InputsReverified=$false;CanExit=$false;IncidentCanExit=$false;Main=$observation.Main;
            MetadataCount=@($State.Plan.InputMetadata).Count;FileIdsCount=2*@($State.Plan.InputMetadata).Count;
            LeaseCount=0;HeavyCount=0;QuarantinePresent=$false;RootPresent=$false;DirectChildrenPresent=$false;
            ClientsPresent=$false;PreservedProcessesUnchanged=$true;OpenWrapperGuards=$guardSnapshot.Count;
            PayloadHashesReadAfterRelease=$false;FailedReceiptChanged=$false;
            RunnerGuardDisposalEvidence='Pinned runner finally clears guards after closure/release; not direct handle enumeration.';
            NativeHandleDisposalEvidence='Pinned NativeJob CloseConfirmed plus receipt; not fresh owner-object handle enumeration.';
            ActualPTYExitObserved=$false;IndependentAbsencePending=$true;Ready=$false}
        # Once publication is attempted, any partial failure requires separate review.
        $State.IncidentAttempted=$true;$State.Phase='IncidentClosing'
        Write-T7CatalogueHostEvidence $preflightPath $proof
        Close-T7CatalogueHostGuards $State
        if(@($guardSnapshot|Where-Object {!$_.SafeFileHandle.IsClosed}).Count){throw 'Incident wrapper guards remain open.'}
        $receiptGuard.Dispose()
        if(!$receiptGuard.SafeFileHandle.IsClosed){throw 'Incident receipt guard remains open.'}
        $receiptGuard=$null
        Write-T7CatalogueHostEvidence $postflightPath ([ordered]@{
            Schema=(Get-T7CatalogueHostSchema $State.Plan 'host-incident-closure');CapturedUtc=[DateTime]::UtcNow.ToString('o');
            Host=$State.Host;Native=$receipt.Identity;PlanSHA256=$State.PlanSHA256;ContractSHA256=$State.ContractSHA256;
            ReceiptSHA256=$ReceiptSHA256;PreflightPath=$preflightPath;RuntimeStatus=$receipt.Status;
            ($outcomeName)=$receipt.$outcomeName;InputsReverified=$false;CanExit=$false;
            ObservedClosedWrapperGuards=$guardSnapshot.Count;ObservedOpenWrapperGuards=0;ReceiptGuardClosed=$true;
            FailedReceiptChanged=$false;PayloadHashesReadAfterRelease=$false;ActualPTYExitObserved=$false;
            IndependentAbsencePending=$true;Ready=$false})
        $State.Phase='IncidentClosed';$State.IncidentCanExit=$true;$State.IncidentError=$null
        [ordered]@{Incident='FailedRunClosed';CanExit=$State.CanExit;IncidentCanExit=$true;
            RuntimeStatus=$receipt.Status;($outcomeName)=$receipt.$outcomeName;InputsReverified=$false;
            WrapperGuardCount=$State.Guards.Count;ActualPTYExitObserved=$false;IndependentAbsencePending=$true;Ready=$false}|ConvertTo-Json
    }catch{
        $State.IncidentCanExit=$false;$State.IncidentError=$_.Exception.Message
        if($State.IncidentAttempted){$State.Phase='IncidentFailed'}
        throw
    }finally{if($receiptGuard){$receiptGuard.Dispose()}}
}
