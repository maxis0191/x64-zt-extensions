# Pure v2 argument and native-report gates; importing this file starts nothing.
function Get-MaterialV2Budgets {
    # Current RESOURCE-WORKFLOW native minimum, even for a single small writer.
    [ordered]@{WriterPhysicalBytes=4GB;WriterCommitBytes=6GB;FFPhysicalBytes=8GB;FFCommitBytes=11GB}
}
function Measure-MaterialV2OutputFiles($Files,[string]$Work,$Inputs) {
    # Only hard links reuse existing storage. Copied stock is new output too.
    $linked=@($Inputs|Where-Object Mode -CEQ 'HardLink'|ForEach-Object Relative)
    Measure-BeaconOutputFiles $Files $Work $linked
}
function Set-MaterialV2StagingModes($Inputs) {
    # The shared helper validates the historical modes. Preserve them without
    # repeating its contract; the established operational policy copies only77B.
    foreach($entry in $Inputs){
        $entry|Add-Member NoteProperty BaselineMode $entry.Mode
        $entry.Mode=if($entry.Relative -ceq 'main/fileSysCheck.cfg'){'Copy'}else{'HardLink'}
    }
}
function Assert-MaterialV2CopyIdentity($Entry,[string]$TargetId) {
    if($Entry.Mode -cne 'Copy' -or $Entry.Relative -cne 'main/fileSysCheck.cfg' -or $Entry.Bytes -ne 77 -or
       !$Entry.SourceId -or !$TargetId -or $TargetId -ceq $Entry.SourceId){throw 'Independent owned sentinel copy identity required before attribute change.'}
}
function Get-MaterialV2UtcNow {[datetime]::UtcNow}
function Start-MaterialV2OwnedPhase($Owner,[string]$LeaseToken) {
    # Caller already holds the lease/job and verifies original-handle identity.
    # CIM cannot reliably identify a never-resumed process on this host.
    $Owner.Resume()
    $started=Get-MaterialV2UtcNow;$attached=$false
    while(!$Owner.Exited -and !$attached){
        try{Add-IW7ResourceProcess -Token $LeaseToken -ProcessId $Owner.PID;$attached=$true}
        catch{
            if($_.Exception.Message -notlike 'Child identity unavailable*'){throw}
            if($Owner.Exited){break}
            if((Get-MaterialV2UtcNow) -gt $started.AddSeconds(5)){throw}
            Start-Sleep -Milliseconds 100
        }
    }
    # A short root can finish before CIM sees it. Caller still requires its exact
    # handle exit code and zero active job members before accepting phase output.
    [pscustomobject]@{StartedUtc=$started;SchedulerAttached=$attached}
}
function Set-MaterialV2SourceIdentity($Entry,[string]$Observed) {
    # ModelFF's existing SourceId field may already be supplied by the stock
    # binding. Compare it under the native read guard; never silently replace it.
    if(!$Observed){throw 'Fresh native source identity required.'}
    if($Entry.PSObject.Properties['SourceId']){
        if($Entry.SourceId -isnot [string] -or !$Entry.SourceId -or $Entry.SourceId -cne $Observed){throw 'Bound stock source identity changed.'}
    }else{$Entry|Add-Member NoteProperty SourceId $Observed}
}
function ConvertTo-MaterialV2Arguments($Arguments) {
    (@(foreach($arg in $Arguments){
        if($arg -isnot [string] -or !$arg -or $arg -match '["\x00-\x1f]' -or $arg.EndsWith('\')){throw 'Unsupported literal phase argument.'}
        '"'+$arg+'"'
    }) -join ' ')
}
function Get-MaterialV2CompilerArguments([string]$VC,[string]$SDK,[string]$Version,[string]$ZT,[string]$Prepared,[string]$Writer) {
    if($Version -cnotmatch '^10\.0\.\d+\.0$'){throw 'Exact installed Windows SDK version required.'}
    $includes=@((Join-Path $VC 'include'),(Join-Path $SDK "Include/$Version/ucrt"),(Join-Path $SDK "Include/$Version/shared"),
        (Join-Path $SDK "Include/$Version/um"),(Join-Path $ZT 'src/zonetool'),(Join-Path $Prepared 'writer-source'))
    @('/nologo','/std:c++20','/EHsc','/D_CRT_SECURE_NO_WARNINGS','/MD','/W4','/bigobj')+
        @($includes|ForEach-Object {'/I'+$_})+
        @(('/Fo'+(Join-Path $Writer 'writer.obj')),('/Fe'+(Join-Path $Writer 'material-v2-writer.exe')),
          ('/Fd'+(Join-Path $Writer 'writer.pdb')),(Join-Path $Prepared 'writer-source/writer.cpp'),'/link',
          ('/LIBPATH:'+(Join-Path $VC 'lib/x64')),('/LIBPATH:'+(Join-Path $SDK "Lib/$Version/ucrt/x64")),
          ('/LIBPATH:'+(Join-Path $SDK "Lib/$Version/um/x64")),'user32.lib','kernel32.lib')
}
function Assert-MaterialV2PhaseResult($Result,[string]$Phase,[string]$Hash,$Identity) {
    if($Result.schema -cne 'iw7.material-v2-phase-result/1' -or $Result.phase -cne $Phase -or
       $Result.executable_sha256 -ine $Hash -or $Result.failure -or
       ($Result.exit_code -isnot [int] -and $Result.exit_code -isnot [long]) -or $Result.exit_code -ne 0 -or
       $Identity.ExitCode -ne 0 -or $Identity.JobActiveAtClose -ne 0){throw 'Closed successful exact native phase required.'}
}
