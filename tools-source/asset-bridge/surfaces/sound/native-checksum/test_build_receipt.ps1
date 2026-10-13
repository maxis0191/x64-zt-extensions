param([Parameter(Mandatory)][string]$ProviderRoot,[switch]$Flac)
$ErrorActionPreference='Stop'
foreach($entry in @(@('completion','9710dd10beaa1db17d0bca51916679145f5d76460bc3c43463f888bc9aff3ad0'),
    @('residual_policy','86c2d8f3f6c79e5dd644f11741521f74b3ccd6960f45189ba41da38f17ef3888'))){
    $path=Join-Path $ProviderRoot ($entry[0]+'.ps1')
    if((Get-FileHash -LiteralPath $path).Hash -ine $entry[1]){throw 'Exact receipt provider required.'};. $path
}
. "$PSScriptRoot/BuildReceipt.Core.ps1"
if($Flac){. "$PSScriptRoot/FlacBuild.Profile.ps1"}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('sound-build-receipt-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
$checks=0
function SaveFixture([string]$Path,$Value,[switch]$Raw){
    [IO.Directory]::CreateDirectory((Split-Path $Path -Parent))|Out-Null
    $bytes=if($Raw){[byte[]]$Value}else{[Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Depth 20))}
    [IO.File]::WriteAllBytes($Path,$bytes)
    @{Bytes=$bytes.Length;SHA256=Get-AuditByteHash $bytes}
}
try {
    $plan=@{output=$temp;compiler=(Join-Path $temp 'cl.exe');seal_sha256=('a'*64);commands=@();common_objects=@{};
        original_header=(Join-Path $temp 'original/bit_buffer.hpp');patched_header=(Join-Path $temp 'patched/bit_buffer.hpp');
        shared_original_header=(Join-Path $temp 'shared/bit_buffer.hpp')}
    $context=@{PlanSHA256=('b'*64);RunID=('c'*32);LeaseToken='fixture';LeaseOwnerPID=123;OriginalIdentity=@{PID=321};
        AcceptedReceipt=$null;SealedPaths=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase);SealedByPath=@{}}
    [void]$context.SealedPaths.Add($plan.original_header);[void]$context.SealedPaths.Add($plan.patched_header)
    if($Flac){
        $plan.schema='iw7.sound-flac-dump-build-plan/1';$plan.flac=@{overlay=(Join-Path $temp 'overlay')}
        foreach($name in 'sound_flac_metadata.hpp','flac_dump_cases.hpp'){
            [void]$context.SealedPaths.Add((Join-Path $plan.flac.overlay $name))
        }
    }
    $receipt=@{schema='iw7.sound-checksum-build-receipt/1';status='NativeBuildAndCppProbesPassed';plan_sha256=$context.PlanSHA256;
        seal_sha256=$plan.seal_sha256;run_id=$context.RunID;lease_token=$context.LeaseToken;lease_owner_pid=123;root_pid=321;
        native_cpp_probes_verified=$true;sab_ff_tested=$false;ready=$false;steps=@();includes=@{};probes=@{};common_members=@{};artifacts=@{}}
    $artifacts=@{candidate_exe='bin/zonetool-sound-md5.exe';candidate_pdb='bin/zonetool-sound-md5.pdb';common_library='common/common.lib';
        probe_original='probe/original.exe';probe_patched='probe/patched.exe'}
    if($Flac){$receipt.schema='iw7.sound-flac-dump-build-receipt/1';$receipt.flac_header_probe_verified=$true;$artifacts.probe_flac='probe/flac-header.exe'}
    foreach($role in $artifacts.Keys){
        $hash=SaveFixture (Join-Path $temp $artifacts[$role]) ([byte[]](1,2,3)) -Raw
        $receipt.artifacts[$role]=@{relative=$artifacts[$role];bytes=$hash.Bytes;sha256=$hash.SHA256}
    }
    $names=@('probe-original-compile','probe-original-link','probe-original-run','probe-patched-compile','probe-patched-link','probe-patched-run',
        'compile-loadedsound','compile-loadedsound1','compile-loadedsound2','compile-loadedsound3','compile-sound_bank','compile-common-bit-buffer','archive-common','link-candidate')
    if($Flac){$names=@($names[0..5])+@('probe-flac-compile','probe-flac-link','probe-flac-run')+@($names[6..13])}
    foreach($name in $names){
        $kind=if($name.EndsWith('-run')){'probe_run'}elseif($name.EndsWith('-compile') -or $name.StartsWith('compile-')){'candidate_compile'}else{'candidate_link'}
        $phase=if($kind -ceq 'probe_run'){'read'}else{'compile'}
        $exesha=if($name -ceq 'probe-original-run'){$receipt.artifacts.probe_original.sha256}
            elseif($name -ceq 'probe-patched-run'){$receipt.artifacts.probe_patched.sha256}
            elseif($name -ceq 'probe-flac-run'){$receipt.artifacts.probe_flac.sha256}else{'d'*64}
        $plan.commands+=@{phase=$name;kind=$kind;executable_sha256=$exesha}
        $logs=Join-Path $temp ('logs/'+$name)
        $native=@{schema='iw7.material-v2-phase-result/1';phase=$phase;exit_code=0;failure=$null;executable_sha256=$exesha;log_limit_each=2MB;pid=222}
        $file=SaveFixture (Join-Path $logs 'phase.json') $native
        $stdout=if($kind -ceq 'probe_run'){
            $original=$name -ceq 'probe-original-run'
            $probe=@{source_checksum=$(if($original){'78000000000000000000000000000000'}else{'24fe5af1473ea8f4be33912348210c78'});
                matches_original_md5=(!$original);field_matches=$true;payload_unchanged=$true;outside_field_unchanged=$true;native_ff_tested=$false;ready=$false}
            if($name -ceq 'probe-flac-run'){
                $probe=@{schema='iw7.flac-dump-header-probe/1';cases=103;input_unchanged=$true;extent_checks=$true;
                    native_dump_tested=$false;full_conformance=$false;ready=$false}
            }
            $receipt.probes[$name]=$probe;SaveFixture (Join-Path $logs 'stdout.log') $probe
        }else{SaveFixture (Join-Path $logs 'stdout.log') ([byte[]](4,5,6)) -Raw}
        $receipt.steps+=@{name=$name;exit_code=0;normal_eof=$true;native_phase=$phase;executable_sha256=$exesha;
            receipt_sha256=$file.SHA256;stdout_sha256=$stdout.SHA256;stderr_sha256=('e'*64)}
        if($kind.EndsWith('compile')){
            $header=if($name -ceq 'probe-original-compile'){$plan.original_header}else{$plan.patched_header}
            if($name -ceq 'probe-flac-compile'){$header=Join-Path $plan.flac.overlay 'sound_flac_metadata.hpp'}
            $paths=@($header.ToLowerInvariant())
            if($name -ceq 'probe-flac-compile'){$paths+=(Join-Path $plan.flac.overlay 'flac_dump_cases.hpp').ToLowerInvariant()}
            if($Flac -and $name -ceq 'compile-sound_bank'){$paths+=(Join-Path $plan.flac.overlay 'sound_flac_metadata.hpp').ToLowerInvariant()}
            $paths=@($paths|Sort-Object)
            if($Flac){
                $text=($paths|ForEach-Object {'Note: including file: '+$_}) -join "`n"
                $stdout=SaveFixture (Join-Path $logs 'stdout.log') ([Text.Encoding]::UTF8.GetBytes($text)) -Raw
                $receipt.steps[-1].stdout_sha256=$stdout.SHA256
            }
            $receipt.includes[$name]=@{expected_header=$header;paths=$paths;report_sha256=$stdout.SHA256}
        }
    }
    foreach($name in 'binary_resource.obj','bit_buffer.obj','compression.obj','cryptography.obj','flags.obj','hook.obj','io.obj','memory.obj','minidump.obj','nt.obj','signature.obj','string.obj','thread.obj'){
        $path=Join-Path $temp ('old/'+$name);$plan.common_objects[$name]=$path
        $context.SealedByPath[$path]=@{SHA256=('f'*64);Bytes=3}
        $receipt.common_members[$name]=@{sha256=('f'*64);bytes=3}
    }
    $baseline=$receipt|ConvertTo-Json -Depth 20
    $null=SaveFixture (Join-Path $temp 'build-receipt.json') @{fixture='completion collector already opened this'}
    $null=SaveFixture (Join-Path $temp 'compiler-image.bin') ([byte[]](8,7,6)) -Raw
    $null=SaveFixture (Join-Path $temp 'residual-image.bin') ([byte[]](6,7,8)) -Raw
    $fixtureBytes=@{}
    foreach($f in Get-ChildItem -LiteralPath $temp -File -Recurse){$fixtureBytes[$f.FullName]=[IO.File]::ReadAllBytes($f.FullName)}
    $cases=@('success','stale-plan','stale-lease','untyped-pid','reordered-step','untyped-exit','untyped-eof','promotion',
        'changed-artifact','incomplete-steps','wrong-header','unsealed-header','changed-common','untyped-native-exit','false-native-field')
    if($Flac){$cases=@($cases|Where-Object {$_ -cne 'changed-artifact'})+@('natural-budget','residual-budget','missing-flac-probe','flac-promoted','flac-count','flac-include-missing','false-include-paths')}
    foreach($case in $cases){
        foreach($path in $fixtureBytes.Keys){[IO.File]::WriteAllBytes($path,$fixtureBytes[$path])}
        $r=ConvertFrom-Json -InputObject $baseline -AsHashtable -DateKind String
        switch($case){
            'stale-plan' {$r.plan_sha256='0'*64}
            'stale-lease' {$r.lease_token='other'}
            'untyped-pid' {$r.root_pid='321'}
            'reordered-step' {$r.steps[0].name='probe-patched-compile'}
            'untyped-exit' {$r.steps[0].exit_code='0'}
            'untyped-eof' {$r.steps[0].normal_eof=1}
            'promotion' {$r.ready=$true}
            'changed-artifact' {$r.artifacts.candidate_exe.sha256='0'*64}
            'incomplete-steps' {$r.steps=@($r.steps|Select-Object -Skip 1)}
            'wrong-header' {$r.includes['probe-original-compile'].expected_header=$plan.patched_header}
            'unsealed-header' {$r.includes['probe-original-compile'].paths+=,(Join-Path $temp 'unknown.h')}
            'changed-common' {$r.common_members['thread.obj'].sha256='0'*64}
            'untyped-native-exit' {
                $path=Join-Path $temp 'logs/probe-original-compile/phase.json'
                $n=Get-Content -Raw -LiteralPath $path|ConvertFrom-Json -AsHashtable;$n.exit_code='0'
                $pin=SaveFixture $path $n;$r.steps[0].receipt_sha256=$pin.SHA256
            }
            'false-native-field' {
                $path=Join-Path $temp 'logs/probe-original-run/stdout.log'
                $p=$r.probes['probe-original-run'];$p.field_matches=$false
                $pin=SaveFixture $path $p;$r.steps[2].stdout_sha256=$pin.SHA256
            }
            'missing-flac-probe' {$r.flac_header_probe_verified=$false}
            'flac-promoted' {
                $p=$r.probes['probe-flac-run'];$p.full_conformance=$true
                $pin=SaveFixture (Join-Path $temp 'logs/probe-flac-run/stdout.log') $p;$r.steps[8].stdout_sha256=$pin.SHA256
            }
            'flac-count' {
                $p=$r.probes['probe-flac-run'];$p.cases='103'
                $pin=SaveFixture (Join-Path $temp 'logs/probe-flac-run/stdout.log') $p;$r.steps[8].stdout_sha256=$pin.SHA256
            }
            'flac-include-missing' {$r.includes['probe-flac-compile'].paths=@((Join-Path $plan.flac.overlay 'sound_flac_metadata.hpp').ToLowerInvariant())}
            'false-include-paths' {
                # Rebind the real trace hash but lie about its decoded path list.
                $pin=SaveFixture (Join-Path $temp 'logs/probe-original-compile/stdout.log') ([Text.Encoding]::UTF8.GetBytes('Note: including file: C:\unreviewed.hpp')) -Raw
                $r.steps[0].stdout_sha256=$pin.SHA256;$r.includes['probe-original-compile'].report_sha256=$pin.SHA256
            }
        }
        $state=@{Guards=[Collections.Generic.List[object]]::new();Files=@{};Bytes=0L}
        $reader={param($Path,$Maximum,$AsJson) Open-AuditCompletionFile $Path $Maximum $AsJson $state {}}
        $failure=$null
        try{
            if($Flac){$null=& $reader (Join-Path $temp 'build-receipt.json') 2MB $true}
            $verified=Assert-ChecksumReceipt $r $plan $context $reader {}
            if($case -in 'natural-budget','residual-budget'){
                $null=& $reader (Join-Path $temp 'compiler-image.bin') 32MB $false
                if($case -ceq 'residual-budget'){$null=& $reader (Join-Path $temp 'residual-image.bin') 32MB $false}
            }
        }catch{$failure=$_.Exception.Message}
        finally{Close-AuditCompletionFiles $state}
        $checks++
        if($case -in 'success','natural-budget','residual-budget'){
            $expectedGuards=if(!$Flac){27}elseif($case -ceq 'natural-budget'){31}elseif($case -ceq 'residual-budget'){32}else{30}
            if($failure -or !$verified.NativeCppProbesVerified -or $verified.Ready -or $state.Guards.Count -ne $expectedGuards){throw "Positive receipt adapter failed: $failure; guards=$($state.Guards.Count)"}
        }elseif(!$failure){throw "Invalid receipt accepted: $case"}
    }
    [ordered]@{Cases=$cases.Count;Assertions=$checks;Flac17=[bool]$Flac;NativeTypesLoaded=$false;RealReservations=0}|ConvertTo-Json
}finally{
    $resolved=[IO.Path]::GetFullPath($temp);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notlike 'sound-build-receipt-*'){throw 'Unsafe fixture cleanup path'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
