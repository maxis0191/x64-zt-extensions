# Sound-specific receipt adapter. The original v6 closure collector is unchanged.
function Assert-ChecksumReceipt($Receipt,$Plan,$Context,[scriptblock]$ReadFile,[scriptblock]$CheckClock) {
    $flac=$Plan.schema -ceq 'iw7.sound-flac-dump-build-plan/1'
    $schema=if($flac){'iw7.sound-flac-dump-build-receipt/1'}else{'iw7.sound-checksum-build-receipt/1'}
    if($Receipt.schema -cne $schema -or $Receipt.status -cne 'NativeBuildAndCppProbesPassed' -or
        $Receipt.plan_sha256 -cne $Context.PlanSHA256 -or $Receipt.seal_sha256 -cne $Plan.seal_sha256 -or
        $Receipt.run_id -cne $Context.RunID -or $Receipt.lease_token -cne $Context.LeaseToken -or
        !(Test-AuditResidualUInt32 $Receipt.lease_owner_pid) -or !(Test-AuditResidualUInt32 $Receipt.root_pid) -or
        $Receipt.lease_owner_pid -ne $Context.LeaseOwnerPID -or $Receipt.root_pid -ne $Context.OriginalIdentity.PID -or
        $Receipt.native_cpp_probes_verified -isnot [bool] -or !$Receipt.native_cpp_probes_verified -or
        $Receipt.sab_ff_tested -isnot [bool] -or $Receipt.sab_ff_tested -or $Receipt.ready -isnot [bool] -or $Receipt.ready){
        throw 'Fresh source-bound sound build receipt required.'
    }
    $steps=if($flac){17}else{14};$includes=if($flac){9}else{8};$probes=if($flac){3}else{2}
    if($flac -and ($Receipt.flac_header_probe_verified -isnot [bool] -or !$Receipt.flac_header_probe_verified)){throw 'Native FLAC header probe missing.'}
    if(@($Receipt.steps).Count -ne $steps -or @($Plan.commands).Count -ne $steps -or $Receipt.includes.Count -ne $includes -or
        $Receipt.probes.Count -ne $probes -or $Receipt.common_members.Count -ne 13){throw 'Complete ordered sound build evidence required.'}
    $artifacts=@{candidate_exe='bin/zonetool-sound-md5.exe';candidate_pdb='bin/zonetool-sound-md5.pdb';
        common_library='common/common.lib';probe_original='probe/original.exe';probe_patched='probe/patched.exe'}
    if($flac){$artifacts.probe_flac='probe/flac-header.exe'}
    if($Receipt.artifacts.Count -ne $artifacts.Count){throw 'Exact final build artifact inventory required.'}
    foreach($role in $artifacts.Keys){
        $item=$Receipt.artifacts[$role];Assert-AuditDigest $item.sha256
        if($item.relative -cne $artifacts[$role] -or ($item.bytes -isnot [int] -and $item.bytes -isnot [long]) -or
            $item.bytes -le 0 -or $item.bytes -gt 256MB){throw 'Bounded typed artifact declaration required.'}
        # Large PDB/library verification occurs after positive original-job closure,
        # while admission and source guards remain held, outside the 2-second drain.
        # FLAC17 leaves room for the unchanged provider's compiler/residual reads:
        # 29 traces + build-receipt + compiler + optional vctip = at most 32.
        # All six artifact files, including the four EXEs, are verified by the
        # mandatory post-closure pass under admission before supervisor success.
        if(!$flac -and $role -in 'candidate_exe','probe_original','probe_patched'){
            $file=& $ReadFile (Join-Path $Plan.output $item.relative) 32MB $false
            if($file.SHA256 -cne $item.sha256 -or $file.Bytes -ne $item.bytes){throw 'Fresh native output bytes differ.'}
        }
        & $CheckClock
    }
    for($i=0;$i -lt $steps;$i++){
        $step=$Receipt.steps[$i];$command=$Plan.commands[$i]
        if($step.name -cne $command.phase -or !(Test-AuditResidualInteger $step.exit_code) -or $step.exit_code -ne 0 -or $step.normal_eof -isnot [bool] -or !$step.normal_eof){throw 'Ordered successful native phase required.'}
        $phase=if($command.kind -ceq 'probe_run'){'read'}else{'compile'}
        $expected=if($command.phase -ceq 'probe-original-run'){$Receipt.artifacts.probe_original.sha256}
            elseif($command.phase -ceq 'probe-patched-run'){$Receipt.artifacts.probe_patched.sha256}
            elseif($command.phase -ceq 'probe-flac-run'){$Receipt.artifacts.probe_flac.sha256}else{$command.executable_sha256}
        Assert-AuditDigest $step.receipt_sha256;Assert-AuditDigest $step.stdout_sha256;Assert-AuditDigest $step.stderr_sha256
        if($step.native_phase -cne $phase -or $step.executable_sha256 -cne $expected){throw 'Native executable binding differs.'}
        $logs=Join-Path $Plan.output ('logs/'+$command.phase)
        $file=& $ReadFile (Join-Path $logs 'phase.json') 16384 $true
        $native=$file.Json
        if($file.SHA256 -cne $step.receipt_sha256 -or $native.schema -cne 'iw7.material-v2-phase-result/1' -or
            $native.phase -cne $phase -or !(Test-AuditResidualInteger $native.exit_code) -or $native.exit_code -ne 0 -or $null -ne $native.failure -or
            $native.executable_sha256 -cne $expected -or !(Test-AuditResidualInteger $native.log_limit_each) -or $native.log_limit_each -ne 2MB -or
            !(Test-AuditResidualUInt32 $native.pid)){throw 'Actual existing native runner receipt differs.'}
        if($command.kind -ceq 'probe_run'){
            $probeFile=& $ReadFile (Join-Path $logs 'stdout.log') 4096 $true
            if($probeFile.SHA256 -cne $step.stdout_sha256){throw 'Actual C++ probe output hash differs.'}
            $probe=$probeFile.Json;$original=$command.phase -ceq 'probe-original-run'
            if($command.phase -ceq 'probe-flac-run'){
                Assert-FlacHeaderProbe $probe
            }else{
            $digest=if($original){'78000000000000000000000000000000'}else{'24fe5af1473ea8f4be33912348210c78'}
            if($probe.Count -ne 7 -or $probe.source_checksum -cne $digest -or
                $probe.matches_original_md5 -isnot [bool] -or $probe.matches_original_md5 -ne (!$original)){
                throw 'Genuine original/patched C++ probe digest required.'
            }
            foreach($name in 'field_matches','payload_unchanged','outside_field_unchanged'){
                if($probe[$name] -isnot [bool] -or !$probe[$name]){throw 'Native synthetic field/payload conservation failed.'}
            }
            foreach($name in 'native_ff_tested','ready'){
                if($probe[$name] -isnot [bool] -or $probe[$name]){throw 'Probe cannot promote SAB or runtime.'}
            }
            }
            Assert-AuditSameJson $probe $Receipt.probes[$command.phase] 'actual C++ probe and build report'
        }
        if($command.kind.EndsWith('compile')){
            $include=$Receipt.includes[$command.phase]
            $expectedHeader=if($command.phase -ceq 'probe-original-compile'){$Plan.original_header}else{$Plan.patched_header}
            if($command.phase -ceq 'probe-flac-compile'){$expectedHeader=Join-Path $Plan.flac.overlay 'sound_flac_metadata.hpp'}
            if($include.expected_header -ine $expectedHeader -or $include.report_sha256 -cne $step.stdout_sha256 -or
                @($include.paths).Count -lt 1 -or @($include.paths).Count -gt 2048 -or $expectedHeader.ToLowerInvariant() -cnotin $include.paths){
                throw 'Exact native include report required.'
            }
            foreach($path in $include.paths){
                if(!$Context.SealedPaths.Contains([IO.Path]::GetFullPath($path)) -or $path -ieq $Plan.shared_original_header){throw 'Unsealed or shared old header consumed.'}
            }
            $other=if($command.phase -ceq 'probe-original-compile'){$Plan.patched_header}else{$Plan.original_header}
            if($other -iin $include.paths){throw 'Wrong original/patched header consumed.'}
            if($flac -and $command.phase -in 'probe-flac-compile','compile-sound_bank'){
                $required=@('sound_flac_metadata.hpp')
                if($command.phase -ceq 'probe-flac-compile'){
                    $required+='flac_dump_cases.hpp'
                    if($Plan.patched_header -iin $include.paths){throw 'Unrelated checksum header in FLAC probe.'}
                }
                foreach($name in $required){if((Join-Path $Plan.flac.overlay $name).ToLowerInvariant() -cnotin $include.paths){throw 'Actual FLAC include missing.'}}
            }
            $includeFile=& $ReadFile (Join-Path $logs 'stdout.log') 2MB $false
            if($includeFile.SHA256 -cne $include.report_sha256){throw 'Compiler include report bytes differ.'}
            if($flac){Assert-FlacIncludeBytes $includeFile $include.paths $CheckClock}
        }
        & $CheckClock
    }
    $expectedMembers=@('binary_resource.obj','bit_buffer.obj','compression.obj','cryptography.obj','flags.obj','hook.obj',
        'io.obj','memory.obj','minidump.obj','nt.obj','signature.obj','string.obj','thread.obj')
    foreach($name in $expectedMembers){
        $member=$Receipt.common_members[$name];Assert-AuditDigest $member.sha256
        if(($member.bytes -isnot [int] -and $member.bytes -isnot [long]) -or $member.bytes -le 0 -or $member.bytes -gt 4MB){throw 'Bounded common member proof required.'}
        if($name -cne 'bit_buffer.obj'){
            $pin=$Context.SealedByPath[[IO.Path]::GetFullPath($Plan.common_objects[$name])]
            if(!$pin -or $pin.SHA256 -cne $member.sha256 -or $pin.Bytes -ne $member.bytes){throw 'One of twelve original common payloads changed.'}
        }
    }
    $Context.AcceptedReceipt=$Receipt
    [ordered]@{CompilerImage=$Plan.compiler;ToolSHA256=$Receipt.artifacts.candidate_exe.sha256;
        SourceSHA256=$Plan.seal_sha256;RunID=$Receipt.run_id;Verified=$true;NativeCppProbesVerified=$true;SABVerified=$false;Ready=$false}
}
function Complete-ChecksumBuildEvidence($Owner,$Record,[long]$StartedMs,$Plan,$Context,[scriptblock]$MeasureOutput,[bool]$Residual) {
    # Narrow dynamically scoped receipt callback. All v6 capture, guard, identity,
    # Stop, fresh-zero and monotonic-deadline logic remains the original function.
    & {
        param($Job,$Evidence,$Started,$BoundPlan,$BoundContext,$Measure,$HasResidual)
        function Assert-AuditCompletionReceipt($Receipt,$Plan,$Context,[scriptblock]$ReadFile,[scriptblock]$CheckClock) {
            Assert-ChecksumReceipt $Receipt $Plan $Context $ReadFile $CheckClock
        }
        Complete-AuditBuildEvidence $Job $Evidence $Started $BoundPlan $BoundContext $Measure $HasResidual
    } $Owner $Record $StartedMs $Plan $Context $MeasureOutput $Residual
}
