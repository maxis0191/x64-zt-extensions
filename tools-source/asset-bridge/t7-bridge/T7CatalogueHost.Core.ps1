# Functions only. The existing runner/H1 primitives retain native ownership.
Set-StrictMode -Version Latest
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
        RunnerReturnedUtc=$null;RunnerError=$null;CanExit=$false;ClosureError=$null}
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
        if($contract.Schema -cne 'iw7.t7-catalogue-host/1' -or $contract.PlanPath -cne $PlanPath -or
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
        $state.Plan=$plan;$state.Contract=$contract
        return $state
    }catch{Close-T7CatalogueHostGuards $state;throw}
}
function Assert-T7CatalogueHostArguments($State,[string[]]$ActualArguments,$HostIdentity) {
    $expected=@($State.Contract.HostImage,'-NoLogo','-NoProfile','-NoExit','-File',$State.EntryPath,
        '-PlanPath',$State.PlanPath,'-PlanSHA256',$State.PlanSHA256,'-RunRoot',$State.RunRoot,
        '-HostContractPath',$State.ContractPath,'-HostContractSHA256',$State.ContractSHA256,'-Run')
    if($HostIdentity.Image -cne $State.Contract.HostImage -or $ActualArguments.Count -ne $expected.Count){throw 'Fresh exact NoProfile/NoExit host arguments required.'}
    for($index=0;$index -lt $expected.Count;$index++){
        if($ActualArguments[$index] -cne $expected[$index]){throw 'Fresh exact NoProfile/NoExit host arguments required.'}
    }
}
function Assert-T7CatalogueHostReceipt($State,$Receipt) {
    if($Receipt.Schema -cne 'iw7.t7-catalogue-run/1' -or $Receipt.PlanSHA256 -cne $State.PlanSHA256){throw 'Receipt belongs to another plan.'}
    foreach($name in @('TreeClosureConfirmed','LeaseReleased','InputsReverified','OriginalInputMetadataUnchanged','AliasesRetained')){
        if($Receipt.$name -isnot [bool] -or !$Receipt.$name){throw ('Receipt lacks closure proof: '+$name)}
    }
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
function Complete-T7CatalogueHost($State) {
    if([AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost') -ne $State -or
       !$State.RunnerReturned -or $State.Phase -cnotin @('Returned','ClosurePending')){throw 'Same returned host state required; no re-entry.'}
    $State.CanExit=$false
    $State.Phase='ClosurePending'
    try {
        if(!$State.Guards.Count -or @($State.Guards|Where-Object {$_.SafeFileHandle.IsClosed}).Count){throw 'Source/plan guard lost before closure.'}
        $startProof=Read-H1SmallJson ($State.RunRoot+'.host-start.json')
        $returnProof=Read-H1SmallJson ($State.RunRoot+'.host-return.json')
        foreach($proof in @($startProof,$returnProof)){
            if($proof.PlanSHA256 -cne $State.PlanSHA256 -or $proof.ContractSHA256 -cne $State.ContractSHA256 -or
               !(Test-IW7ResourceIdentity $State.Host $proof.Host)){throw 'Host start/return proof differs.'}
        }
        if($returnProof.RunnerReturned -isnot [bool] -or !$returnProof.RunnerReturned -or
           ([datetimeoffset]$returnProof.RunnerReturnedUtc).UtcTicks -ne ([datetimeoffset]$State.RunnerReturnedUtc).UtcTicks){throw 'Host return proof differs.'}
        $receipt=Read-H1SmallJson (Join-Path $State.Plan.StageRoot 'receipt.json') 512KB
        Assert-T7CatalogueHostReceipt $State $receipt
        if($null -ne [AppDomain]::CurrentDomain.GetData('IW7.H1.Quarantine.'+$receipt.LeaseToken)){throw 'Native quarantine remains; retain host.'}
        $attempt=Read-H1SmallJson (Join-Path $State.RunRoot 'attempt.json')
        if($attempt.Schema -cne 'iw7.t7-catalogue-attempt/1' -or $attempt.PlanSHA256 -cne $State.PlanSHA256 -or
           ([datetimeoffset]$attempt.StartedUtc).UtcTicks -lt ([datetimeoffset]$State.Host.CreatedUtc).UtcTicks -or
           ([datetimeoffset]$attempt.StartedUtc).UtcTicks -gt ([datetimeoffset]$receipt.StartedUtc).UtcTicks){throw 'Attempt marker differs.'}
        $status=Get-IW7ResourceStatus;$processes=@(Get-IW7ResourceProcesses)
        Assert-T7CatalogueHostObservation $State $receipt $status $processes (Get-T7CatalogueHostIdentity)
        $main=Assert-T7CatalogueMain $State.Plan
        foreach($row in $State.Plan.InputMetadata){Assert-T7CatalogueMetadata $row}
        foreach($row in @($receipt.InputFileIds)+@($receipt.Aliases)){
            if((Get-T7CatalogueFileId $row.Path) -cne $row.FileId){throw 'Original/alias file identity changed.'}
        }
        $proof=[ordered]@{Schema='iw7.t7-catalogue-host-closure/1';CapturedUtc=[DateTime]::UtcNow.ToString('o');
            Host=$State.Host;Native=$receipt.Identity;PlanSHA256=$State.PlanSHA256;ContractSHA256=$State.ContractSHA256;
            Main=$main;MetadataCount=@($State.Plan.InputMetadata).Count;FileIdsCount=2*@($State.Plan.InputMetadata).Count;
            LeaseCount=0;HeavyCount=0;QuarantinePresent=$false;RootPresent=$false;PreservedProcessesUnchanged=$true;
            RuntimeStatus=$receipt.Status;CatalogueOutcome=$receipt.CatalogueOutcome;PayloadHashesReadAfterRelease=$false;
            RunnerGuardDisposalEvidence='Pinned runner finally clears guards after native closure and release, before the observed wrapper return.';
            ActualPTYExitObserved=$false;IndependentAbsencePending=$true}
        # Publish proof before disposing wrapper guards. CanExit is not inferred from a file.
        Write-T7CatalogueHostEvidence ($State.RunRoot+'.host-postflight.json') $proof
        Close-T7CatalogueHostGuards $State
        $State.Phase='Closed';$State.CanExit=$true;$State.ClosureError=$null
        [ordered]@{Postflight='Passed';HostPID=$State.Host.PID;CanExit=$true;WrapperGuardCount=$State.Guards.Count;
            CatalogueOutcome=$receipt.CatalogueOutcome;ActualPTYExitObserved=$false;IndependentAbsencePending=$true}|ConvertTo-Json
    }catch{$State.ClosureError=$_.Exception.Message;throw}
}
