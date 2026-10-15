# One opt-in MP/CP load witness. Pure import; existing owners/admission only.
function Test-ArenaLoadDiagnosticTrigger($Evidence,[long]$ElapsedMs,[long]$Bytes,[string]$LastLine,
    [ValidateSet('global_mp','global_cp')][string]$Zone='global_mp') {
    if($Evidence.Attempted){return $false}
    if($Evidence.LastBytes -ne $Bytes){$Evidence.LastBytes=$Bytes;$Evidence.LastProgressMs=$ElapsedMs}
    # 10+15+20 seconds of helpers, two 5-second closures and 5-second margin.
    # The original 120-second deadline is never extended by a late callback.
    if($ElapsedMs -gt 60000){$Evidence.Outcome='DeclinedLate';return $false}
    $ElapsedMs -ge 45000 -and ($ElapsedMs-$Evidence.LastProgressMs) -ge 15000 -and
        $LastLine -ceq ('[ INFO ][ zonetool::iw7::load_zone ]: Loading zone "'+$Zone.ToLowerInvariant()+'"...')
}
function Test-ArenaReferenceModalTrigger($Evidence,[long]$ElapsedMs,[long]$Bytes,[string]$LastLine) {
    if($Evidence.Attempted){return $false}
    if($Evidence.LastBytes -ne $Bytes){$Evidence.LastBytes=$Bytes;$Evidence.LastProgressMs=$ElapsedMs}
    if($ElapsedMs -gt 220000){$Evidence.Attempted=$true;$Evidence.Outcome='DeclinedLate';return $false}
    # Any phase of this one original reference; no new zone or loader bypass.
    $ElapsedMs -ge 45000 -and ($ElapsedMs-$Evidence.LastProgressMs) -ge 15000 -and ![string]::IsNullOrWhiteSpace($LastLine)
}
function Get-ArenaDiagnosticSeconds($Options,[int]$Nominal) {
    $phase=if($Options.PSObject.Properties['ReferenceModalOnce'] -and $Options.ReferenceModalOnce){240000}else{120000}
    $remaining=[math]::Floor(($Options.StartedMs+$phase-(Get-H1Clock)-10000)/1000)
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
    $reference=($Options.PSObject.Properties['ReferenceModalOnce'] -and $Options.ReferenceModalOnce)
    $zone=if($Options.PSObject.Properties['DiagnosticZone']){$Options.DiagnosticZone}else{'global_mp'}
    if($last.Count -ne 1){return}
    $trigger=if($reference){Test-ArenaReferenceModalTrigger $Evidence $elapsed $file.Length $last[0]}else{Test-ArenaLoadDiagnosticTrigger $Evidence $elapsed $file.Length $last[0] $zone}
    if(!$trigger){return}
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
        if($Options.PSObject.Properties['ModalTextOnly'] -and $Options.ModalTextOnly){
            if($Options.PSObject.Properties['ModalRecordReader'] -and $Options.ModalRecordReader -isnot [scriptblock]){throw 'Modal record reader must be an explicit caller callback.'}
            $window=Join-Path $dir 'modal-window.json'
            $createdFiletime=([datetimeoffset]$State.Identity.CreatedUtc).UtcDateTime.ToFileTimeUtc()
            $args=@('-B','-S',$Options.ModalSource,'--pid',[string]$State.Identity.PID,'--parent-pid',[string]$PID,
                '--image',$State.Identity.Image,'--created',$State.Identity.CreatedUtc,'--created-filetime',[string]$createdFiletime,
                '--sha256',$Options.ToolSHA256,'--output',$window)
            $Evidence.Window=Invoke-OriginalArenaTool $diag $Options.Python $Options.PythonSHA256 $args $Target.Work $Options.RunRoot load-modal $Options.Inputs (Get-ArenaDiagnosticSeconds $Options 10)
            if((Get-Item -LiteralPath $window).Length -gt 64KB){throw 'Modal window record exceeds 64 KiB.'}
            if($Options.PSObject.Properties['ModalRecordReader']){
                $record=(& $Options.ModalRecordReader $window)|ConvertFrom-Json
            }else{$record=Get-Content -LiteralPath $window -Raw|ConvertFrom-Json}
            if($reference -and ($record.schema -isnot [string] -or $record.identity_verified_after -isnot [bool] -or
               $record.modal_window_observed -isnot [bool] -or ($record.modal_window_observed -and $record.title -isnot [string]))){throw 'Scalar original modal record fields required.'}
            if($record.schema -cne 'iw7.world-modal-window/1' -or $record.identity_verified_after -ne $true){throw 'Modal target/window identity not confirmed.'}
            $Evidence.ModalWindowObserved=$record.modal_window_observed
            if($record.modal_window_observed -ne $true){
                $Evidence.Outcome='NoModalWindowObserved'
                if($reference){$Evidence.ReferenceContinues=$true;return}
                throw 'No owned modal window observed in the bounded scan.'
            }
            $Evidence.Outcome='Captured';$Evidence.SymbolsVerified=$false
            if($reference){$Evidence.Caption=$record.title;$Evidence.ReferenceContinues=$false}
            $Evidence.Limits='One original-target modal snapshot; text may be absent/truncated. No new CPU, minidump or CDB operation. No interaction or material reference proof.'
        }else{
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
        }
    } catch {
        if($Evidence.Outcome -cne 'NoModalWindowObserved'){$Evidence.Outcome='Failed'}
        $Evidence.Error=$_.Exception.Message
        throw
    } finally {
        $Evidence.DiagnosticClosed=$diag.Closed
        $Evidence|ConvertTo-Json -Depth 20|Set-Content -LiteralPath (Join-Path $dir 'diagnostic.json') -Encoding utf8
        if($diag.Closed -and !(Get-H1OriginalState $Target.Owner).RootExited){Register-H1Original $Target.Lease $State.Identity}
        if(!$diag.Closed){$Target.Closed=$false}
    }
    # Finish this diagnostic experiment rather than repeat the previous 240 s
    # material attempt. The caller's original catch closes its exact target job.
    if($reference){throw 'Owned modal captured; reference not measured.'}
    throw 'Load diagnostic captured; material reference not measured.'
}
