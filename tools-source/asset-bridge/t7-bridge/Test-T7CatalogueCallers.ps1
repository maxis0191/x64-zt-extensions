# Contract tests with invented AB bytes/function ranges. No native types, jobs,
# leases, owner files, build receipts or executable runtime plans are produced.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern='.') {
    $caught=$false
    try{$null=& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected error: '+$_.Exception.Message)}
    Check $caught ('Expected refusal: '+$Pattern)
}
$targets=@('0000000140584FD8','00000001401DA015','0000000140526D02')
$prefix='[T7_CATALOG_CALLER] schema=iw7.t7-catalog-callers/1 '
$trace="[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase=enabled stdout_unbuffered=1 stderr_unbuffered=1 tid=42`n"+
    "[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase=exit_hook code=0 tid=73 return_address=0000000140AC00C4`n"
$exitPrefix='[T7_CATALOG_EXIT] schema=iw7.t7-catalog-exit-context/1 kind='
$memory=$exitPrefix+'memory code=0 tid=73 ra=0000000140AC00C4 status=ok start=0000000140AC0084 requested=256 read=256 module=0000000140000000 allocation=0000000140000000 region=0000000140AC0000 region_size=4096 state=4096 protect=32 type=131072 error=0 data='+('AB'*256)
$fn=$exitPrefix+'function code=0 tid=73 ra=0000000140AC00C4 status=ok image=0000000140000000 record=0000000140FE0000 read=12 begin=00AC0000 end=00AC0100 unwind=00FE1122 error=0'
$addresses=@('0000000140001111')+$targets+@($targets[0])
function Stack-Line([string[]]$Frames=$addresses,[string]$Status='ok') {
    $data=if($Frames.Count){$Frames -join ','}else{'-'}
    $exitPrefix+"stack code=0 tid=73 ra=0000000140AC00C4 status=$Status count=$($Frames.Count) error=0 addresses=$data"
}
function Legacy([string]$Stack=(Stack-Line)) {$trace+$memory+"`n"+$Stack+"`n"+$fn+"`n"}
function Caller-Line([int]$Index=0,[hashtable]$Change=@{}) {
    $ra=[Convert]::ToUInt64($targets[$Index],16);$begin=$ra-0x140000000L-128
    $fields=[ordered]@{code=0;tid=73;exit_ra='0000000140AC00C4';index=$Index;ra=$targets[$Index];status='ok';frame=($Index+1);
        module='0000000140000000';image='0000000140000000';record='0000000140FE1000';record_read=12;
        begin=$begin.ToString('X8');end=($begin+256).ToString('X8');unwind='00FE1122';start=($ra-128).ToString('X16');
        requested=256;read=256;scope='full';allocation='0000000140000000';region='0000000140000000';region_size=268435456;
        state=4096;protect=32;type=131072;error=0;data=''}
    foreach($key in $Change.Keys){$fields[$key]=$Change[$key]}
    if(!$Change.ContainsKey('data')){$fields.data=if($fields.read -gt 0){'AB'*$fields.read}else{'-'}}
    $prefix+(@(foreach($key in $fields.Keys){[string]$key+'='+[string]$fields[$key]}) -join ' ')
}
function Refusal-Fields([string]$Status) {
    @{status=$Status;frame=-1;module='0000000000000000';image='0000000000000000';record='0000000000000000';record_read=0;
      begin='00000000';end='00000000';unwind='00000000';start='0000000000000000';requested=0;read=0;scope='none';
      allocation='0000000000000000';region='0000000000000000';region_size=0;state=0;protect=0;type=0;error=0}
}
function Envelope([string[]]$Rows,[string]$Before=(Legacy)) {$Before+($Rows -join "`n")+"`n"}
$rows=@((Caller-Line 0),(Caller-Line 1),(Caller-Line 2));$full=Envelope $rows
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-callers-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
$context=[pscustomobject]@{Guards=[Collections.Generic.List[object]]::new()}
function Close-Guards {foreach($guard in $context.Guards){$guard.Dispose()};$context.Guards.Clear()}
try {
    $r=ConvertFrom-T7CatalogueCallers $full
    Check ($r.Outcome -ceq 'TraceObserved' -and $r.ContextOutcome -ceq 'Observed' -and $r.CallersOutcome -ceq 'Observed') 'Three complete callers lost.'
    Check ($r.Callers.Captures.Count -eq 3 -and $r.Callers.Captures[0].Frame -eq 1 -and $r.Callers.Captures[0].DataHex -ceq ('AB'*256)) 'Caller fields lost.'
    Check ((ConvertFrom-T7CatalogueCallers ($full.Replace("`n","`r`n"))).CallersOutcome -ceq 'Observed') 'CRLF lost.'
    foreach($text in @('', $trace, (Legacy))) {Check ((ConvertFrom-T7CatalogueCallers $text).CallersOutcome -ceq 'Absent') 'No caller became Observed.'}
    foreach($count in 1,2){Check ((ConvertFrom-T7CatalogueCallers (Envelope $rows[0..($count-1)])).CallersOutcome -ceq 'Partial') 'Missing caller overclaimed.'}
    $r=ConvertFrom-T7CatalogueCallers $full.TrimEnd("`n")
    Check ($r.CallersOutcome -ceq 'Partial' -and $r.Callers.Captures.Count -eq 2 -and $r.Callers.IncompleteTrailingLine) 'Truncation lost prior captures.'
    foreach($cut in @(5,($prefix.Length+3),100,($rows[0].Length-1))) {
        $r=ConvertFrom-T7CatalogueCallers ((Legacy)+$rows[0].Substring(0,$cut))
        Check ($r.CallersOutcome -ceq 'Partial' -and $r.ContextOutcome -ceq 'Observed') 'Recognizable truncated caller lost.'
    }
    # The original incomplete EXIT handling remains available before callers begin.
    foreach($cut in 3,5,30) {
        Check ((ConvertFrom-T7CatalogueCallers ($trace+$memory.Substring(0,$cut))).ContextOutcome -ceq 'Partial') 'Legacy partial context lost.'
    }
    $without0=Legacy (Stack-Line @('0000000140001111',$targets[1],$targets[2]))
    $absent=Caller-Line 0 (Refusal-Fields 'absent')
    Check ((ConvertFrom-T7CatalogueCallers (Envelope @($absent) $without0)).Callers.Captures[0].Status -ceq 'absent') 'Absent caller was hidden.'
    foreach($status in 'empty','invalid_count','exception') {
        $unavailable=@(foreach($i in 0..2){Caller-Line $i (Refusal-Fields 'stack_unavailable')})
        $r=ConvertFrom-T7CatalogueCallers (Envelope $unavailable (Legacy (Stack-Line @() $status)))
        Check ($r.CallersOutcome -ceq 'Partial' -and $r.Callers.Captures.Count -eq 3) 'Unavailable stack became complete or lost.'
    }
    Refuses {ConvertFrom-T7CatalogueCallers (Envelope @($absent))} 'frame|presence'
    Refuses {ConvertFrom-T7CatalogueCallers (Envelope @($rows[0]) $without0)} 'frame|presence'
    Refuses {ConvertFrom-T7CatalogueCallers (Envelope @((Caller-Line 0 @{frame=4})))} 'first matching'
    $lastStack=@('0000000140001111')*7+@($targets[0])
    Check ((ConvertFrom-T7CatalogueCallers (Envelope @((Caller-Line 0 @{frame=7})) (Legacy (Stack-Line $lastStack)))).Callers.Captures[0].Frame -eq 7) 'Frame seven lost.'
    foreach($change in @(@{read=1;status='partial';error=299},@{read=255;status='partial'},@{read=0;status='read_failed';error=5},@{read=256;status='read_failed';error=5})) {
        Check ((ConvertFrom-T7CatalogueCallers (Envelope @((Caller-Line 0 $change)))).CallersOutcome -ceq 'Partial') 'RPM diagnostic lost.'
    }
    # Serialization clamp and SEH do not invent valid function bounds.
    $clamp=@{status='read_failed';error=13;requested=0;read=0;start='0000000000000000';scope='none'}
    Check ((ConvertFrom-T7CatalogueCallers (Envelope @((Caller-Line 0 $clamp)))).CallersOutcome -ceq 'Partial') 'Serializer clamp lost.'
    foreach($read in 0,1,256) {
        $exception=@{status='exception';error=3221225477;begin='00000000';end='00000000';unwind='00000000';read=$read}
        Check ((ConvertFrom-T7CatalogueCallers (Envelope @((Caller-Line 0 $exception)))).CallersOutcome -ceq 'Partial') 'SEH bounded data lost.'
    }
    foreach($status in 'module_missing','module_mismatch','query_failed','region_invalid','not_found','record_partial','record_read_failed','record_invalid','exception') {
        $change=Refusal-Fields $status;$change.frame=1
        if($status -ceq 'record_partial'){$change.record_read=11}
        Check ((ConvertFrom-T7CatalogueCallers (Envelope @((Caller-Line 0 $change)))).Callers.Captures[0].Status -ceq $status) 'Pre-read refusal lost.'
    }
    $regionFailure=@{status='region_invalid';start='0000000000000000';requested=0;read=0;scope='none'}
    Check ((ConvertFrom-T7CatalogueCallers (Envelope @((Caller-Line 0 $regionFailure)))).Callers.Captures[0].RecordReadBytes -eq 12) 'Post-RF region refusal lost.'
    $invalid=@{status='record_invalid';begin='00FFFFFF';start='0000000000000000';requested=0;read=0;scope='none'}
    Check ((ConvertFrom-T7CatalogueCallers (Envelope @((Caller-Line 0 $invalid)))).Callers.Captures[0].begin -eq 0xFFFFFF) 'Invalid complete RF evidence lost.'
    # 512-byte window, function-clipped window, region-clipped window, and exact full function.
    $ra=[Convert]::ToUInt64($targets[0],16);$rva=$ra-0x140000000L
    $windows=@(
        @{begin=($rva-1024).ToString('X8');end=($rva+1024).ToString('X8');start=($ra-448).ToString('X16');requested=512;read=512;scope='window'},
        @{begin=($rva-50).ToString('X8');end=($rva+900).ToString('X8');start=($ra-50).ToString('X16');requested=114;read=114;scope='window'},
        @{region=($ra-60).ToString('X16');region_size=90;start=($ra-60).ToString('X16');requested=90;read=90;scope='window'},
        @{begin=($rva-448).ToString('X8');end=($rva+64).ToString('X8');start=($ra-448).ToString('X16');requested=512;read=512;scope='full'},
        @{begin=($rva-1).ToString('X8');end=$rva.ToString('X8');start=($ra-1).ToString('X16');requested=1;read=1;scope='full'}
    )
    foreach($window in $windows) {
        $line=Caller-Line 0 $window
        Check ((ConvertFrom-T7CatalogueCallers (Envelope @($line))).Callers.Captures[0].Requested -eq $window.requested) 'Exact window lost.'
        Refuses {ConvertFrom-T7CatalogueCallers (Envelope @($line.Replace('start='+$window.start,'start='+$ra.ToString('X16'))))} 'window'
    }
    $badChanges=@(
        @{code=2147483648},@{tid=4294967296},@{code=1},@{tid=74},@{exit_ra='0000000140AC00C5'},@{index=1},@{ra='0000000140584FD9'},
        @{frame=-2},@{frame=8},@{record_read=13},@{record_read=11},@{requested=513},@{read=257},@{read=255},@{scope='window'},
        @{start='0000000000000000'},@{requested=0;read=0},@{module='0000000000000000'},@{image='0000000140001000'},
        @{allocation='0000000140001000'},@{record='0000000000000000'},@{state=8192},@{protect=0},@{protect=1},@{protect=288},@{protect=512},
        @{region_size=0},@{region_size='18446744073709551616'},@{region='FFFFFFFFFFFFFFFF';region_size=10},@{error=1},
        @{begin=$rva.ToString('X8')},@{end=($rva-1).ToString('X8')},@{type=4294967296},@{data='AB'},@{data='ab'*256},@{data='-'},
        @{read=0;status='partial'},@{read=256;status='partial'},@{read=1;status='read_failed'},@{read=1;status='query_failed'},
        @{status='exception'},@{status='record_partial'},@{status='record_read_failed'},@{status='unknown'},@{scope='unknown'},@{tid='073'}
    )
    foreach($change in $badChanges){Refuses {ConvertFrom-T7CatalogueCallers (Envelope @((Caller-Line 0 $change)))}}
    foreach($field in 'module','image','record','allocation','region') {
        $bad=Refusal-Fields 'absent';$bad[$field]='0000000140000000'
        Refuses {ConvertFrom-T7CatalogueCallers (Envelope @((Caller-Line 0 $bad)) $without0)} 'Uncaptured'
    }
    $bad=Refusal-Fields 'absent';$bad.error=1
    Refuses {ConvertFrom-T7CatalogueCallers (Envelope @((Caller-Line 0 $bad)) $without0)} 'Uncaptured'
    foreach($bad in @((Envelope @($rows[1])),(Envelope @($rows[0],$rows[0])),(Envelope @($rows[0],$rows[2])),
        (Envelope $rows $trace),($full+$rows[0]+"`n"),($full+$trace),($full+"`n"),([char]0xfeff+$full),
        ($full.Replace('schema=iw7.t7-catalog-callers/1','schema=iw7.t7-catalog-callers/2')),
        ((Legacy)+$prefix+('x'*2048)),((Legacy)+"ordinary stderr`n"),((Envelope @($rows[0]))+$rows[0].Substring(0,150)))) {
        Refuses {ConvertFrom-T7CatalogueCallers $bad}
    }
    Refuses {ConvertFrom-T7CatalogueTrace $full}
    Refuses {ConvertFrom-T7CatalogueExitContext $full}
    Assert-T7CatalogueTraceSize 't7-catalog-callers' 8192;$checks++
    Refuses {Assert-T7CatalogueTraceSize 't7-catalog-callers' 8193} 'cap exceeded'
    Refuses {Assert-T7CatalogueTraceSize 't7-catalog-exit-context' 4097} 'cap exceeded'
    Refuses {Assert-T7CatalogueTraceSize 't7-catalog-trace' 1536} 'cap exceeded'
    # Three maximum 512-byte payloads still fit the actual combined wire bounds.
    $maxRows=@(foreach($i in 0..2){$address=[Convert]::ToUInt64($targets[$i],16);$offset=$address-0x140000000L
        Caller-Line $i @{begin=($offset-1024).ToString('X8');end=($offset+1024).ToString('X8');start=($address-448).ToString('X16');requested=512;read=512;scope='window'}})
    $maxText=Envelope $maxRows
    Check ([Text.Encoding]::ASCII.GetByteCount($maxText) -le 8192 -and !@($maxRows|Where-Object {($_.Length+2) -gt 2048}).Count) 'Maximum synthetic context exceeds wire caps.'
    Check ((ConvertFrom-T7CatalogueCallers $maxText).CallersOutcome -ceq 'Observed') 'Maximum caller payloads lost.'
    # Guarded private ingestion leaves catalogue qualification completely separate.
    $plan=[pscustomobject]@{CandidateProfile='t7-catalog-callers';StageRoot=$root};$state=[ordered]@{CatalogueOutcome='NoCatalogue'}
    Read-T7CatalogueTrace $plan $state $context
    Check ($state.TraceOutcome -ceq 'NoTrace' -and $state.ExitContextOutcome -ceq 'Absent' -and $state.CallersOutcome -ceq 'Absent') 'Absent file overclaimed.'
    $log=Join-Path $root 'stderr.log';[IO.File]::WriteAllText($log,$full,[Text.UTF8Encoding]::new($false))
    Read-T7CatalogueTrace $plan $state $context
    Check ($state.CallersOutcome -ceq 'Observed' -and $state.CatalogueOutcome -ceq 'NoCatalogue' -and $context.Guards.Count -eq 1) 'Observed callers changed catalogue outcome.'
    Refuses {[IO.File]::AppendAllText($log,'x')}
    Close-Guards
    [IO.File]::WriteAllBytes($log,[byte[]]::new(8193))
    Refuses {Read-T7CatalogueTrace $plan $state $context} 'cap exceeded'
    Check ($context.Guards.Count -eq 0 -and $state.CallersOutcome -ceq 'PresentUnqualified' -and $state.CatalogueOutcome -ceq 'NoCatalogue') 'Oversized callers inspected or accepted.'
    [ordered]@{Status='Passed';Checks=$checks;NativeTypesLoaded=$false;RealLeaseAcquired=$false;NativeProcessStarted=$false;OwnerStockRead=$false;MemoryBytes='InventedABOnly'}|ConvertTo-Json
}finally {
    Close-Guards
    $resolved=[IO.Path]::GetFullPath($root);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notmatch '^t7-callers-tests-[0-9a-f]{32}$'){throw 'Refuse cleanup outside exact synthetic callers root.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
