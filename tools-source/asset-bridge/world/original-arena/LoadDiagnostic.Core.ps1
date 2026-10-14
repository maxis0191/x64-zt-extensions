# One opt-in global_mp load witness. Pure import; existing owners/admission only.
function Test-ArenaLoadDiagnosticTrigger($Evidence,[long]$ElapsedMs,[long]$Bytes,[string]$LastLine) {
    if($Evidence.Attempted){return $false}
    if($Evidence.LastBytes -ne $Bytes){$Evidence.LastBytes=$Bytes;$Evidence.LastProgressMs=$ElapsedMs}
    # 10+15+20 seconds of helpers, two 5-second closures and 5-second margin.
    # The original 120-second deadline is never extended by a late callback.
    if($ElapsedMs -gt 60000){$Evidence.Outcome='DeclinedLate';return $false}
    $ElapsedMs -ge 45000 -and ($ElapsedMs-$Evidence.LastProgressMs) -ge 15000 -and
        $LastLine -ceq '[ INFO ][ zonetool::iw7::load_zone ]: Loading zone "global_mp"...'
}
function Get-ArenaDiagnosticSeconds($Options,[int]$Nominal) {
    $remaining=[math]::Floor(($Options.StartedMs+120000-(Get-H1Clock)-10000)/1000)
    if($remaining -lt 1){throw 'Original global load deadline leaves no diagnostic/closure budget.'}
    [int][math]::Min($Nominal,$remaining)
}
function Invoke-ArenaLoadDiagnostic($Target,$State,[string]$Logs,$Options,$Evidence) {
    $stdout=Join-Path $Logs 'stdout.log'
    if(!(Test-Path -LiteralPath $stdout)){return}
    $file=Get-Item -LiteralPath $stdout
    if($file.Length -gt 2MB){throw 'Bounded original loader log required.'}
    $elapsed=[long]((Get-H1Clock)-$Options.StartedMs)
    $last=@(Get-Content -LiteralPath $stdout -Tail 1)
    if(!($last.Count -eq 1 -and (Test-ArenaLoadDiagnosticTrigger $Evidence $elapsed $file.Length $last[0]))){return}
    $Evidence.Attempted=$true;$Evidence.TriggerElapsedMs=$elapsed
    $sample=Get-H1OriginalState $Target.Owner
    if($sample.RootExited -or $sample.PID -ne $State.Identity.PID -or $sample.Image -ine $State.Identity.Image -or
       $sample.CreatedUtc -cne $State.Identity.CreatedUtc){throw 'Original live load identity required.'}
    $Evidence.Target=$State.Identity;$Evidence.OriginalSnapshot=$sample
    $diag=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$Target.Lease;Work=$Target.Work}
    $Target|Add-Member NoteProperty DiagnosticContext $diag -Force
    $dir=Join-Path $Options.RunRoot 'load-diagnostic';[IO.Directory]::CreateDirectory($dir)|Out-Null
    $cpu=Join-Path $dir 'cpu-threads.jsonl';$dump=Join-Path $dir 'load.dmp'
    try {
        # No new admission. All diagnostic children use the existing original
        # NativeJob helper and the same reservation; restore requires both jobs.
        $identityArgs=@('--pid',[string]$State.Identity.PID,'--image',$State.Identity.Image,
            '--created',$State.Identity.CreatedUtc,'--sha256',$Options.ToolSHA256,'--scenario','original-arena-global-mp-load')
        $args=@('-B','-S',$Options.CaptureSource)+$identityArgs+@('--seconds','5','--interval-ms','500','--threads','--output',$cpu)
        $Evidence.CPU=Invoke-OriginalArenaTool $diag $Options.Python $Options.PythonSHA256 $args $Target.Work $Options.RunRoot load-cpu $Options.Inputs (Get-ArenaDiagnosticSeconds $Options 10)
        $sample=Get-H1OriginalState $Target.Owner
        if($sample.RootExited){throw 'Original target exited before diagnostic snapshot; do not reopen PID.'}
        $args=@('-B','-S',$Options.CaptureSource)+$identityArgs+@('--snapshot','--output',$dump)
        $Evidence.Snapshot=Invoke-OriginalArenaTool $diag $Options.Python $Options.PythonSHA256 $args $Target.Work $Options.RunRoot load-snapshot $Options.Inputs (Get-ArenaDiagnosticSeconds $Options 15)
        $dumpFile=Get-Item -LiteralPath $dump
        if($dumpFile.Length -le 0 -or $dumpFile.Length -gt 32MB){throw 'Light minidump exceeds 32 MiB acceptance bound.'}
        $Evidence.Dump=[ordered]@{Bytes=$dumpFile.Length;SHA256=(Get-FileHash -LiteralPath $dump).Hash;Flags='0x1820';FullMemory=$false}
        $args=@('-z',$dump,'-y',$Options.Symbols,'-c','!runaway; ~* kP; lmv; .time; q')
        $Evidence.Stack=Invoke-OriginalArenaTool $diag $Options.Cdb $Options.CdbSHA256 $args $Target.Work $Options.RunRoot load-stack $Options.Inputs (Get-ArenaDiagnosticSeconds $Options 20)
        $Evidence.Outcome='Captured';$Evidence.SymbolsVerified=$false
        $Evidence.Limits='Live stack witness; not crash or dependency/root-cause proof. Dump and output limits sampled; 32 MiB dump acceptance. No debugger attaches to live target.'
    } catch {
        $Evidence.Outcome='Failed';$Evidence.Error=$_.Exception.Message
        throw
    } finally {
        $Evidence.DiagnosticClosed=$diag.Closed
        $Evidence|ConvertTo-Json -Depth 20|Set-Content -LiteralPath (Join-Path $dir 'diagnostic.json') -Encoding utf8
        if($diag.Closed -and !(Get-H1OriginalState $Target.Owner).RootExited){Register-H1Original $Target.Lease $State.Identity}
        if(!$diag.Closed){$Target.Closed=$false}
    }
    # Finish this diagnostic experiment rather than repeat the previous 240 s
    # material attempt. The caller's original catch closes its exact target job.
    throw 'Load diagnostic captured; material reference not measured.'
}
