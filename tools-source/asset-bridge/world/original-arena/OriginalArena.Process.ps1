# Specialized caller of the existing H1 original-job owner. Import is pure.
# The caller holds one admission; no nested lease or PID adoption is introduced.
function Invoke-OriginalArenaTool($Context,[string]$Executable,[string]$SHA256,[string[]]$Arguments,
    [string]$Work,[string]$RunRoot,[string]$Phase,$Inputs,[int]$Seconds=240,[scriptblock]$OnOriginalPoll=$null) {
    if(!$Context.Closed -or !$Context.Lease){throw 'Closed previous original job and current admission required.'}
    $logs=Join-Path $RunRoot ('owned-'+$Phase)
    if(Test-Path -LiteralPath $logs){throw 'Fresh original arena phase logs required.'}
    [IO.Directory]::CreateDirectory($logs)|Out-Null
    $start=[Diagnostics.ProcessStartInfo]::new($Executable)
    $start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle='Hidden';$start.WorkingDirectory=$Work
    $start.Environment.Clear()
    foreach($key in 'SystemRoot','windir','SystemDrive','USERPROFILE','LOCALAPPDATA','APPDATA'){
        $start.Environment[$key]=[Environment]::GetEnvironmentVariable($key)
    }
    $start.Environment['PATH']=(Split-Path $Executable -Parent)+';'+[Environment]::SystemDirectory
    $start.Environment['TEMP']=$logs;$start.Environment['TMP']=$logs
    foreach($argument in $Arguments){$start.ArgumentList.Add($argument)}
    $current=[ordered]@{Stage='Fixture';Phase=$Phase;DeadlineSeconds=$Seconds;MaxObservedOutputBytes=0L;
        MaxObservedStreamBytes=0L;CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
    $plan=[pscustomobject]@{RunRoot=$RunRoot}
    # Use the same sampled output accounting as the existing FF caller. Only
    # freshly proved same-ID hardlinks are exempt; copied bootstrap is counted.
    $accountingWork=$Context.Work
    $arenaAccountingInputs=$Inputs
    $arenaExempt={
        foreach($entry in $arenaAccountingInputs){
            # Pre-alias source validation has no TargetId yet. A SourceId alone
            # must never exempt an output path or attest a staged alias.
            if($entry.Mode -cne 'HardLink' -or !$entry.PSObject.Properties['TargetId']){continue}
            if(!$entry.PSObject.Properties['SourceId'] -or $entry.SourceId -isnot [string] -or
               $entry.TargetId -isnot [string] -or $entry.SourceId -cnotmatch '^[A-F0-9]{8}:[A-F0-9]{16}$' -or
               $entry.TargetId -cne $entry.SourceId){throw 'Qualified original hardlink identities required for output exemption.'}
            $source=Resolve-IW7BasePath (Split-Path $entry.Source -Parent) (Split-Path $entry.Source -Leaf)
            $target=Resolve-IW7BasePath $accountingWork $entry.Relative
            if([IW7HudFileIdentity]::Read($source) -cne $entry.SourceId -or
               [IW7HudFileIdentity]::Read($target) -cne $entry.TargetId){throw 'Original hardlink provider or alias identity changed before output accounting.'}
            $entry.Relative
        }
    }
    $exempt=@(& $arenaExempt)
    if(!$Context.PSObject.Properties['OutputBaseline']){
        $Context|Add-Member NoteProperty OutputBaseline (Measure-BeaconOutputFiles @(Get-ChildItem -LiteralPath $RunRoot -Recurse -File -Force) $accountingWork $exempt)
    }
    $baseline=$Context.OutputBaseline
    function Test-H1Budget($Plan,$State) {
        # The counter excludes by path only; requalify the actual alias on each
        # sample so a removed/replaced path cannot inherit an earlier exemption.
        $exempt=@(& $arenaExempt)
        $bytes=Measure-BeaconOutputFiles @(Get-ChildItem -LiteralPath $RunRoot -Recurse -File -Force) $accountingWork $exempt
        $State.MaxObservedOutputBytes=[math]::Max($State.MaxObservedOutputBytes,$bytes)
        if($bytes -gt $baseline+256MB){throw 'Original arena generated output exceeds sampled 256 MiB phase allowance.'}
        foreach($name in 'stdout.log','stderr.log'){
            $path=Join-Path $logs $name
            if(Test-Path -LiteralPath $path){
                $length=(Get-Item -LiteralPath $path).Length
                $State.MaxObservedStreamBytes=[math]::Max($State.MaxObservedStreamBytes,$length)
                if($length -gt 2MB){throw 'Original arena sampled stream threshold exceeded.'}
            }
        }
        $State.LastMemoryObservation=[ordered]@{Policy='TelemetryOnly';Snapshot=(Get-IW7ResourceSnapshot)}
        if($OnOriginalPoll -and $State.Identity){& $OnOriginalPoll $Context $State $logs}
    }
    try {
        # As in Invoke-WorldStage, clear the closed previous owner BEFORE a new
        # factory attempt. Its Closed flag cannot attest an unknown new object.
        $Context.Owner=$null
        Invoke-H1OwnedStage $plan $current $Context $start $SHA256 $logs
        Test-H1Budget $plan $current
        # NativeJob.CloseConfirmed only returns after the original root exited
        # AND its original job ActiveProcesses is zero. H1 also requires exit0.
        if(!$Context.Closed -or !$current.TreeClosureConfirmed -or $current.ExitCode -ne 0){throw 'Original arena root0/Active0/exit0 required.'}
        [pscustomobject]@{Phase=$Phase;ExitCode=$current.ExitCode;Identity=$current.Identity;
            RootExited=$true;ActiveProcesses=0;JobClosed=$true;Arguments=$Arguments;ImageSHA256=$SHA256;
            Stdout=(Join-Path $logs 'stdout.log');Stderr=(Join-Path $logs 'stderr.log');OwnerEvidence=$current}
    } catch {
        # The original H1 owner remains in the caller's context even if Start
        # partially failed. A missing/unknown owner cannot qualify release.
        if(!$Context.Closed -and $Context.Owner){
            try{$Context.Owner.StopAndConfirm(5000);$Context.Closed=$Context.Owner.Closed}catch{}
        }
        if($Context.PSObject.Properties['DiagnosticContext'] -and !$Context.DiagnosticContext.Closed){$Context.Closed=$false}
        throw
    }
}
