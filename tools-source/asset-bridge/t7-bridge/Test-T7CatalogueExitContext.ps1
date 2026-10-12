# Only invented memory bytes and addresses. No runtime payload, native types or lease.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern='.'){
    $caught=$false
    try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected error: '+$_.Exception.Message)}
    Check $caught ('Expected refusal: '+$Pattern)
}
$prefix='[T7_CATALOG_EXIT] schema=iw7.t7-catalog-exit-context/1 kind='
$trace="[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase=enabled stdout_unbuffered=1 stderr_unbuffered=1 tid=42`n"+
    "[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase=exit_hook code=0 tid=73 return_address=0000000140AC00C4`n"
function Memory-Line([string]$Status='ok',[int]$Read=256,[uint]$ErrorCode=0) {
    $data=if($Read){'AB'*$Read}else{'-'}
    $prefix+"memory code=0 tid=73 ra=0000000140AC00C4 status=$Status start=0000000140AC0084 requested=256 read=$Read module=0000000140000000 allocation=0000000140000000 region=0000000140AC0000 region_size=4096 state=4096 protect=32 type=131072 error=$ErrorCode data=$data"
}
function Stack-Line([string]$Status='ok',[int]$Count=2,[uint]$ErrorCode=0) {
    $addresses=if($Count){(@(for($i=0;$i -lt $Count;$i++){'0000000140001234'}) -join ',')}else{'-'}
    $prefix+"stack code=0 tid=73 ra=0000000140AC00C4 status=$Status count=$Count error=$ErrorCode addresses=$addresses"
}
function Function-Line([string]$Status='ok',[int]$Read=12,[uint]$ErrorCode=0) {
    $rvas=if($Status -cin @('ok','record_invalid') -and $Read -eq 12){'begin=00AC0000 end=00AC0100 unwind=00FE1122'}else{'begin=00000000 end=00000000 unwind=00000000'}
    $prefix+"function code=0 tid=73 ra=0000000140AC00C4 status=$Status image=0000000140000000 record=0000000140FE0000 read=$Read $rvas error=$ErrorCode"
}
function Envelope([string[]]$Captures) {$trace+($Captures -join "`n")+"`n"}
$memory=Memory-Line;$stack=Stack-Line;$fn=Function-Line
$full=Envelope @($memory,$stack,$fn)
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-context-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
$context=[pscustomobject]@{Guards=[Collections.Generic.List[object]]::new()}
function Close-Guards {foreach($guard in $context.Guards){$guard.Dispose()};$context.Guards.Clear()}
try {
    $r=ConvertFrom-T7CatalogueExitContext $full
    Check ($r.Outcome -ceq 'TraceObserved' -and $r.ContextOutcome -ceq 'Observed' -and $r.Context.Captures.Count -eq 3) 'Complete context lost.'
    Check ($r.Context.Captures[0].DataHex -ceq ('AB'*256) -and $r.Context.Captures[1].Addresses.Count -eq 2 -and $r.Context.Captures[2].begin -eq 0xAC0000) 'Context fields changed.'
    Check ((ConvertFrom-T7CatalogueExitContext ($full.Replace("`n","`r`n"))).ContextOutcome -ceq 'Observed') 'CRLF lost.'
    Check ((ConvertFrom-T7CatalogueExitContext $trace).ContextOutcome -ceq 'Absent') 'Markers alone became context.'
    Check ((ConvertFrom-T7CatalogueExitContext '').ContextOutcome -ceq 'Absent') 'Empty context changed.'
    foreach($lines in @(@{Rows=@($memory)},@{Rows=@($stack,$fn)},@{Rows=@($memory,$fn)})) {
        Check ((ConvertFrom-T7CatalogueExitContext (Envelope $lines.Rows)).ContextOutcome -ceq 'Partial') 'Missing capture became complete.'
    }
    foreach($cut in @(5,($prefix.Length+3),($prefix.Length+30),($memory.Length-10),$memory.Length)) {
        $r=ConvertFrom-T7CatalogueExitContext ($trace+$memory.Substring(0,$cut))
        Check ($r.ContextOutcome -ceq 'Partial' -and $r.Context.IncompleteTrailingLine -and $r.Context.Captures.Count -eq 0) 'Truncated final capture overclaimed.'
    }
    $r=ConvertFrom-T7CatalogueExitContext ($full.TrimEnd("`n"))
    Check ($r.ContextOutcome -ceq 'Partial' -and $r.Context.Captures.Count -eq 2) 'Truncation discarded prior complete captures.'
    foreach($status in 'module_missing','module_mismatch','address_invalid','query_failed','region_invalid') {
        $r=ConvertFrom-T7CatalogueExitContext (Envelope @((Memory-Line $status 0 5),$stack,$fn))
        Check ($r.ContextOutcome -ceq 'Partial' -and $r.Context.Captures[0].Status -ceq $status -and $r.Context.Captures[0].Error -eq 5) 'Memory failure hidden.'
    }
    foreach($case in @(@{Status='partial';Read=1},@{Status='partial';Read=255},@{Status='read_failed';Read=0},@{Status='read_failed';Read=256},@{Status='exception';Read=2})) {
        Check ((ConvertFrom-T7CatalogueExitContext (Envelope @((Memory-Line $case.Status $case.Read 5),$stack,$fn))).ContextOutcome -ceq 'Partial') 'Memory partial/error rejected.'
    }
    foreach($status in 'empty','invalid_count','exception') {
        Check ((ConvertFrom-T7CatalogueExitContext (Envelope @($memory,(Stack-Line $status 0),$fn))).ContextOutcome -ceq 'Partial') 'Stack failure hidden.'
    }
    Check ((ConvertFrom-T7CatalogueExitContext (Envelope @($memory,(Stack-Line 'ok' 8),$fn))).Context.Captures[1].Addresses.Count -eq 8) 'Eight stack addresses lost.'
    foreach($status in 'not_found','module_mismatch','query_failed','region_invalid') {
        Check ((ConvertFrom-T7CatalogueExitContext (Envelope @($memory,$stack,(Function-Line $status 0 5)))).ContextOutcome -ceq 'Partial') 'Function lookup failure hidden.'
    }
    foreach($case in @(@{Status='partial';Read=1},@{Status='partial';Read=11},@{Status='read_failed';Read=0},@{Status='read_failed';Read=12},@{Status='exception';Read=12},@{Status='record_invalid';Read=0},@{Status='record_invalid';Read=12})) {
        Check ((ConvertFrom-T7CatalogueExitContext (Envelope @($memory,$stack,(Function-Line $case.Status $case.Read 5)))).ContextOutcome -ceq 'Partial') 'Function partial/error rejected.'
    }
    $badMemory=@(
        $memory.Replace('read=256','read=255'),$memory.Replace('read=256','read=257'),$memory.Replace('requested=256','requested=512'),
        $memory.Replace('start=0000000140AC0084','start=0000000140AC0085'),$memory.Replace('module=0000000140000000','module=0000000000000000'),
        $memory.Replace('allocation=0000000140000000','allocation=0000000140001000'),$memory.Replace('region_size=4096','region_size=255'),
        $memory.Replace('region=0000000140AC0000','region=0000000140AC0085'),$memory.Replace('state=4096','state=8192'),
        $memory.Replace('protect=32','protect=1'),$memory.Replace('protect=32','protect=288'),$memory.Replace('error=0','error=1'),
        $memory.Replace('data=AB','data=ab'),$memory.Replace('region_size=4096','region_size=18446744073709551616'),
        $memory.Replace('type=131072','type=4294967296'),$memory.Replace('state=4096','state=04096'),
        (Memory-Line 'partial' 0),(Memory-Line 'partial' 256),(Memory-Line 'read_failed' 2),(Memory-Line 'query_failed' 1)
    )
    foreach($bad in $badMemory){Refuses {ConvertFrom-T7CatalogueExitContext (Envelope @($bad,$stack,$fn))}}
    foreach($bad in @((Stack-Line 'ok' 0),(Stack-Line 'ok' 9),(Stack-Line 'empty' 1),$stack.Replace('count=2','count=1'),$stack.Replace('0000000140001234','000000014000abcd'))) {
        Refuses {ConvertFrom-T7CatalogueExitContext (Envelope @($memory,$bad,$fn))}
    }
    foreach($bad in @($fn.Replace('read=12','read=13'),$fn.Replace('begin=00AC0000','begin=00AD0000'),$fn.Replace('end=00AC0100','end=00AC00C3'),
        $fn.Replace('image=0000000140000000','image=0000000140001000'),$fn.Replace('record=0000000140FE0000','record=0000000000000000'),
        $fn.Replace('status=ok','status=read_failed'),(Function-Line 'partial' 0),(Function-Line 'partial' 12),(Function-Line 'read_failed' 5),
        (Function-Line 'record_invalid' 5),(Function-Line 'not_found' 12))) {
        Refuses {ConvertFrom-T7CatalogueExitContext (Envelope @($memory,$stack,$bad))}
    }
    foreach($bad in @($full.Replace('kind=memory code=0','kind=memory code=1'),$full.Replace('kind=memory code=0 tid=73','kind=memory code=0 tid=74'),
        $full.Replace(' ra=0000000140AC00C4',' ra=0000000140AC00C5'),$full.Replace('kind=memory','kind=unknown'),$full.Replace('status=ok','status=unknown'),
        (Envelope @($memory,$memory,$fn)),(Envelope @($stack,$memory,$fn)),($memory+"`n"+$trace),($trace+"ordinary stderr`n"),
        ([char]0xfeff+$full),($full+"`n"),($full+($trace*4)),($trace+$prefix+'unknown'),($full+$prefix+'function code='),
        ($trace+$prefix+'memory '+('x'*1024)))) {
        Refuses {ConvertFrom-T7CatalogueExitContext $bad}
    }
    Refuses {ConvertFrom-T7CatalogueTrace $full} 'Trace|trace|stderr'
    Assert-T7CatalogueTraceSize 't7-catalog-exit-context' 4096;$checks++
    Refuses {Assert-T7CatalogueTraceSize 't7-catalog-exit-context' 4097} 'cap exceeded'
    Refuses {Assert-T7CatalogueTraceSize 't7-catalog-trace' 1536} 'cap exceeded'
    $plan=[pscustomobject]@{CandidateProfile='t7-catalog-exit-context';StageRoot=$root};$state=[ordered]@{}
    Read-T7CatalogueTrace $plan $state $context
    Check ($state.TraceOutcome -ceq 'NoTrace' -and $state.ExitContextOutcome -ceq 'Absent') 'Missing file state lost.'
    $log=Join-Path $root 'stderr.log';[IO.File]::WriteAllText($log,$full,[Text.UTF8Encoding]::new($false))
    Read-T7CatalogueTrace $plan $state $context
    Check ($state.TraceOutcome -ceq 'TraceObserved' -and $state.ExitContextOutcome -ceq 'Observed' -and $context.Guards.Count -eq 1) 'Guarded context lost.'
    Refuses {[IO.File]::AppendAllText($log,'x')}
    Close-Guards
    [IO.File]::WriteAllBytes($log,[byte[]]::new(4097))
    Refuses {Read-T7CatalogueTrace $plan $state $context} 'cap exceeded'
    Check ($context.Guards.Count -eq 0 -and $state.TraceOutcome -ceq 'TracePresentUnqualified' -and $state.ExitContextOutcome -ceq 'PresentUnqualified') 'Oversized context inspected or reported absent.'
    [ordered]@{Status='Passed';Checks=$checks;NativeTypesLoaded=$false;RealLeaseAcquired=$false;NativeProcessStarted=$false;OwnerStockRead=$false;MemoryBytes='InventedABOnly'}|ConvertTo-Json
}finally{
    Close-Guards
    $resolved=[IO.Path]::GetFullPath($root);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notmatch '^t7-context-tests-[0-9a-f]{32}$'){throw 'Refuse cleanup outside exact synthetic context root.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
