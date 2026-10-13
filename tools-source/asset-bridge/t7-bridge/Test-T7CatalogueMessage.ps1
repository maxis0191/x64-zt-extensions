# Invented bytes and synthetic stderr only. No native types/jobs/leases/stock.
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
$prefix='[T7_CATALOG_MSG] schema=iw7.t7-catalog-message/1 kind='
$tracePrefix='[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase='
$enabled=$tracePrefix+'enabled stdout_unbuffered=1 stderr_unbuffered=1 tid=42'
$before=$tracePrefix+'before_post_unpack code=0 tid=42 return_address=0000000000000000'
$after=$tracePrefix+'after_post_unpack code=0 tid=42 return_address=0000000000000000'
$exit=$tracePrefix+'exit_hook code=0 tid=73 return_address=0000000140AC00C4'
function Install-Line([string]$Status='installed',[uint]$ErrorCode=0,[uint]$Thread=42) {$prefix+"install tid=$Thread status=$Status error=$ErrorCode"}
function Buffer-Line([hashtable]$Change=@{}) {
    $fields=[ordered]@{tid=73;status='ok';requested=384;read=384;length=12;nul=1;error=0;data=''}
    foreach($key in $Change.Keys){$fields[$key]=$Change[$key]}
    if(!$Change.ContainsKey('data')){$fields.data=if($fields.length){'AB'*$fields.length}else{'-'}}
    $prefix+'buffer '+(@(foreach($key in $fields.Keys){[string]$key+'='+[string]$fields[$key]}) -join ' ')
}
function Envelope([string[]]$Lines) {($Lines -join "`n")+"`n"}
function Full([string]$Buffer=(Buffer-Line),[string]$Install=(Install-Line)) {Envelope @($enabled,$before,$Install,$after,$Buffer,$exit)}
$install=Install-Line;$buffer=Buffer-Line;$full=Full
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-message-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
$context=[pscustomobject]@{Guards=[Collections.Generic.List[object]]::new()}
function Close-Guards {foreach($guard in $context.Guards){$guard.Dispose()};$context.Guards.Clear()}
try {
    $r=ConvertFrom-T7CatalogueMessage $full
    Check ($r.MessageOutcome -ceq 'Observed' -and $r.Outcome -ceq 'TraceObserved' -and $r.ContextOutcome -ceq 'Absent' -and $r.CallersOutcome -ceq 'Absent') 'Message outcome leaked into older diagnostics.'
    Check ($r.Message.ExitCorrelated -and $r.Message.InstallBoundaryObserved -and $r.Message.Captures.Count -eq 2 -and $r.Message.Captures[1].DataHex -ceq ('AB'*12)) 'Complete opaque message lost.'
    Check ((ConvertFrom-T7CatalogueMessage ($full.Replace("`n","`r`n"))).MessageOutcome -ceq 'Observed') 'CRLF lost.'
    Check ((ConvertFrom-T7CatalogueMessage (Envelope @($enabled,$before,$install,$buffer,$after,$exit))).MessageOutcome -ceq 'Observed') 'Buffer during post_unpack rejected.'
    Check ((ConvertFrom-T7CatalogueMessage (Full $buffer (Install-Line installed 0 19))).MessageOutcome -ceq 'Observed') 'Independent installation TID rejected.'
    foreach($text in @('',(Envelope @($enabled,$before,$after,$exit)))) {Check ((ConvertFrom-T7CatalogueMessage $text).MessageOutcome -ceq 'Absent') 'No MSG line became observation.'}
    Check ((ConvertFrom-T7CatalogueMessage (Envelope @($enabled,$before,$install,$after,$exit))).MessageOutcome -ceq 'Partial') 'Installation alone became a message.'
    $r=ConvertFrom-T7CatalogueMessage (Envelope @($enabled,$before,$install,$after,$buffer))
    Check ($r.MessageOutcome -ceq 'Partial' -and !$r.Message.ExitCorrelated -and $r.Message.Correlation -ceq 'NoExitHook') 'Missing exit correlation invented.'
    $r=ConvertFrom-T7CatalogueMessage (Full (Buffer-Line @{tid=74}))
    Check ($r.MessageOutcome -ceq 'Partial' -and $r.Message.Correlation -ceq 'DifferentThread') 'Different exit winner silently matched.'
    Check ((ConvertFrom-T7CatalogueMessage (Envelope @($enabled,$before,$install,$after,$exit,(Buffer-Line @{tid=74})))).MessageOutcome -ceq 'Partial') 'Different-thread late buffer lost.'
    Refuses {ConvertFrom-T7CatalogueMessage (Envelope @($enabled,$install,$buffer,$exit))} 'lacks before_post_unpack'
    $prefixBuffer=Buffer-Line @{status='prefix';length=384;nul=0}
    Check ((ConvertFrom-T7CatalogueMessage (Full $prefixBuffer)).MessageOutcome -ceq 'Prefix') 'Bounded prefix became complete or lost.'
    Check ((ConvertFrom-T7CatalogueMessage (Full (Buffer-Line @{requested=1;read=1;length=0;nul=1}))).MessageOutcome -ceq 'Observed') 'Empty NUL-terminated message rejected.'
    Check ((ConvertFrom-T7CatalogueMessage (Full (Buffer-Line @{requested=384;read=384;length=383;nul=1}))).MessageOutcome -ceq 'Observed') 'Maximum complete payload lost.'
    # Hex remains opaque. A nibble crossing a byte boundary is not a NUL byte.
    Check ((ConvertFrom-T7CatalogueMessage (Full (Buffer-Line @{length=2;data='A00B'}))).MessageOutcome -ceq 'Observed') 'Unaligned zero nibbles wrongly treated as NUL.'
    foreach($status in 'module_missing','module_mismatch','query_failed','region_invalid','read_failed','signature_mismatch','call_mismatch','wrapper_far','compare_mismatch','rolled_back','rollback_failed','exception') {
        $r=ConvertFrom-T7CatalogueMessage (Envelope @($enabled,$before,(Install-Line $status 5),$after,$exit))
        Check ($r.MessageOutcome -ceq 'Partial' -and $r.Message.Captures[0].Status -ceq $status) 'Installation refusal lost or accepted.'
        Refuses {ConvertFrom-T7CatalogueMessage (Full $buffer (Install-Line $status 5))} 'preceding successful'
    }
    foreach($status in 'argument_invalid','stack_invalid','query_failed','region_invalid') {
        $r=ConvertFrom-T7CatalogueMessage (Full (Buffer-Line @{status=$status;requested=0;read=0;length=0;nul=0;error=5}))
        Check ($r.MessageOutcome -ceq 'Partial' -and $r.Message.Captures[1].Status -ceq $status) 'Pre-read failure lost.'
    }
    foreach($change in @(
        @{status='partial';read=1;length=1;nul=0;error=299},@{status='partial';read=383;length=383;nul=0},
        @{status='partial';read=12;length=0;nul=1;error=299},@{status='partial';read=12;length=11;nul=1;error=299},
        @{status='read_failed';read=0;length=0;nul=0;error=5},@{status='read_failed';read=384;length=384;nul=0;error=5},
        @{status='read_failed';read=384;length=12;nul=1;error=5},@{status='read_failed';requested=0;read=0;length=0;nul=0;error=13},
        @{status='exception';requested=0;read=0;length=0;nul=0;error=3221225477},@{status='exception';read=0;length=0;nul=0;error=3221225477},
        @{status='exception';read=12;length=12;nul=0;error=3221225477},@{status='exception';read=12;length=11;nul=1;error=3221225477},
        @{status='exception';read=384;length=12;nul=1;error=3221225477})) {
        Check ((ConvertFrom-T7CatalogueMessage (Full (Buffer-Line $change))).MessageOutcome -ceq 'Partial') 'Failed capture with usable bytes became Observed.'
    }
    foreach($change in @(
        @{tid=4294967296},@{tid='073'},@{status='unknown'},@{requested=385},@{read=385},@{length=385},@{read=383},
        @{length=384;nul=1},@{length=385;nul=0},@{length=12;nul=0},@{nul=2},@{length=0;data='AB'},@{length=1;data='-'},
        @{data='AB'},@{data='ab'*12},@{data=('AB'*3)+'00'+('AB'*8)},@{data=('AB'*11)+'00'},@{error=1},@{error=4294967296},
        @{status='prefix'},@{status='prefix';read=0;length=0;nul=0},@{status='prefix';length=384;nul=0;error=5},
        @{status='partial';read=0;length=0;nul=0},@{status='partial';read=384;length=383;nul=1},
        @{status='read_failed';read=5;length=5;nul=0},@{status='read_failed';requested=0;read=0;length=0;nul=0;error=0},
        @{status='argument_invalid'},@{status='exception';requested=5;read=6;length=6;nul=0},@{requested=-1},@{length='012'})) {
        Refuses {ConvertFrom-T7CatalogueMessage (Full (Buffer-Line $change))}
    }
    foreach($bad in @($install.Replace('installed','unknown'),$install.Replace('error=0','error=1'),$install.Replace('tid=42','tid=4294967296'),
        $install.Replace('error=0','error=4294967296'),$install.Replace('kind=install','kind=buffer'),($install+' extra=0'))) {
        Refuses {ConvertFrom-T7CatalogueMessage (Envelope @($enabled,$before,$bad,$after,$exit))}
    }
    foreach($bad in @(
        (Envelope @($enabled,$install,$before,$buffer,$exit)),(Envelope @($enabled,$before,$after,$install,$buffer,$exit)),
        (Envelope @($enabled,$before,$buffer,$install,$after,$exit)),(Envelope @($enabled,$before,$buffer,$after,$exit)),
        (Envelope @($enabled,$before,$install,$after,$exit,$buffer)),(Envelope @($enabled,$before,$install,$install,$buffer,$exit)),
        (Envelope @($enabled,$before,$install,$after,$buffer,$buffer,$exit)),($full+"`n"),([char]0xfeff+$full),
        $full.Replace('schema=iw7.t7-catalog-message/1','schema=iw7.t7-catalog-message/2'),($full+"unrelated stderr`n"),
        (Envelope (@($enabled)*15)),(('x'*8192)+"`n"))) {
        Refuses {ConvertFrom-T7CatalogueMessage $bad}
    }
    foreach($cut in @(3,($prefix.Length+3),($install.Length-1),$install.Length)) {
        $r=ConvertFrom-T7CatalogueMessage ((Envelope @($enabled,$before))+$install.Substring(0,$cut))
        Check ($r.MessageOutcome -ceq 'Partial' -and $r.Message.IncompleteTrailingLine -and $r.Message.Captures.Count -eq 0) 'Truncated installation overclaimed.'
    }
    foreach($cut in @(3,($prefix.Length+3),($buffer.Length-1),$buffer.Length)) {
        $r=ConvertFrom-T7CatalogueMessage ((Envelope @($enabled,$before,$install,$after))+$buffer.Substring(0,$cut))
        Check ($r.MessageOutcome -ceq 'Partial' -and $r.Message.Captures.Count -eq 1) 'Truncated buffer overclaimed or lost installation.'
    }
    Refuses {ConvertFrom-T7CatalogueMessage ((Envelope @($enabled,$before,$install))+$install)} 'Duplicate'
    Refuses {ConvertFrom-T7CatalogueMessage ((Envelope @($enabled,$before,$install))+$prefix+'unknown')} 'Unknown incomplete'
    Refuses {ConvertFrom-T7CatalogueMessage ((Envelope @($enabled,$before,(Install-Line 'signature_mismatch')))+$buffer)} 'preceding successful'
    Refuses {ConvertFrom-T7CatalogueMessage ((Envelope @($enabled,$before))+$buffer)} 'preceding successful'
    Refuses {ConvertFrom-T7CatalogueMessage ((Envelope @($enabled,$before))+$prefix+'install '+('x'*256))} 'oversized'
    Refuses {ConvertFrom-T7CatalogueMessage ((Envelope @($enabled,$before,$install))+$prefix+'buffer '+('x'*1024))} 'incomplete'
    # A truncated legacy record remains with the old parser; an incomplete trace marker is refused.
    $legacyPartial=Envelope @($enabled,$before,$install,$after,$buffer,$exit)
    $r=ConvertFrom-T7CatalogueMessage ($legacyPartial+'[T7_C')
    Check ($r.MessageOutcome -ceq 'Observed' -and !$r.Message.IncompleteTrailingLine -and $r.ContextOutcome -ceq 'Partial') 'Legacy truncation misclassified as another MSG.'
    Refuses {ConvertFrom-T7CatalogueMessage ($legacyPartial+'[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase=')}
    # Exercise the whole fourteen-line envelope with maximum caller/code payloads.
    $exitPrefix='[T7_CATALOG_EXIT] schema=iw7.t7-catalog-exit-context/1 kind='
    $memory=$exitPrefix+'memory code=0 tid=73 ra=0000000140AC00C4 status=ok start=0000000140AC0084 requested=256 read=256 module=0000000140000000 allocation=0000000140000000 region=0000000140AC0000 region_size=4096 state=4096 protect=32 type=131072 error=0 data='+('AB'*256)
    $stack=$exitPrefix+'stack code=0 tid=73 ra=0000000140AC00C4 status=ok count=3 error=0 addresses=0000000140584FD8,00000001401DA015,0000000140526D02'
    $fn=$exitPrefix+'function code=0 tid=73 ra=0000000140AC00C4 status=ok image=0000000140000000 record=0000000140FE0000 read=12 begin=00AC0000 end=00AC0100 unwind=00FE1122 error=0'
    $targets=@('0000000140584FD8','00000001401DA015','0000000140526D02')
    $callers=@(for($i=0;$i -lt 3;$i++) {
        $address=[Convert]::ToUInt64($targets[$i],16);$start=($address-256).ToString('X16')
        $begin=($address-0x140000000L-256).ToString('X8');$end=($address-0x140000000L+256).ToString('X8')
        '[T7_CATALOG_CALLER] schema=iw7.t7-catalog-callers/1 '+
            "code=0 tid=73 exit_ra=0000000140AC00C4 index=$i ra=$($targets[$i]) status=ok frame=$i module=0000000140000000 image=0000000140000000 record=0000000140FE1000 record_read=12 begin=$begin end=$end unwind=00FE1122 start=$start requested=512 read=512 scope=full allocation=0000000140000000 region=0000000140000000 region_size=268435456 state=4096 protect=32 type=131072 error=0 data="+('AB'*512)
    })
    $fourteen=@($enabled,($tracePrefix+'before_entry_point code=0 tid=42 return_address=0000000000000000'),$before,$install,$after,$prefixBuffer,
        ($tracePrefix+'entry_point_return code=0 tid=42 return_address=0000000000000000'),$exit,$memory,$stack,$fn)+$callers
    $maximum=Envelope $fourteen
    $r=ConvertFrom-T7CatalogueMessage $maximum
    Check ($fourteen.Count -eq 14 -and [Text.Encoding]::ASCII.GetByteCount($maximum) -le 8192) 'Full envelope exceeds message caps.'
    Check ($r.MessageOutcome -ceq 'Prefix' -and $r.ContextOutcome -ceq 'Observed' -and $r.CallersOutcome -ceq 'Observed' -and $r.Events.Count -eq 6) 'Whole profile lost legacy records or upgraded a prefix.'
    Check ((ConvertFrom-T7CatalogueMessage ($maximum.Replace("`n","`r`n"))).MessageOutcome -ceq 'Prefix') 'Maximum CRLF envelope lost.'
    foreach($reader in 'ConvertFrom-T7CatalogueTrace','ConvertFrom-T7CatalogueExitContext','ConvertFrom-T7CatalogueCallers') {Refuses {& $reader $full}}
    Assert-T7CatalogueTraceSize 't7-catalog-message' 8192;$checks++
    Refuses {Assert-T7CatalogueTraceSize 't7-catalog-message' 8193} 'cap exceeded'
    $plan=[pscustomobject]@{CandidateProfile='t7-catalog-message';StageRoot=$root};$state=[ordered]@{CatalogueOutcome='NoCatalogue'}
    Read-T7CatalogueTrace $plan $state $context
    Check ($state.MessageOutcome -ceq 'Absent' -and !$state.Message.ExitCorrelated) 'Missing message file overclaimed.'
    $log=Join-Path $root 'stderr.log';[IO.File]::WriteAllText($log,$full,[Text.UTF8Encoding]::new($false))
    Read-T7CatalogueTrace $plan $state $context
    Check ($state.MessageOutcome -ceq 'Observed' -and $state.CatalogueOutcome -ceq 'NoCatalogue' -and $context.Guards.Count -eq 1) 'Message changed catalogue qualification.'
    Refuses {[IO.File]::AppendAllText($log,'x')}
    Close-Guards
    [IO.File]::WriteAllBytes($log,[byte[]]::new(8193))
    Refuses {Read-T7CatalogueTrace $plan $state $context} 'cap exceeded'
    Check ($context.Guards.Count -eq 0 -and $state.MessageOutcome -ceq 'PresentUnqualified') 'Oversized stderr inspected or accepted.'
    [ordered]@{Status='Passed';Checks=$checks;NativeTypesLoaded=$false;RealLeaseAcquired=$false;NativeProcessStarted=$false;OwnerStockRead=$false;MessageBytes='InventedOpaqueBytesOnly'}|ConvertTo-Json
}finally {
    Close-Guards
    $resolved=[IO.Path]::GetFullPath($root);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notmatch '^t7-message-tests-[0-9a-f]{32}$'){throw 'Refuse cleanup outside exact synthetic message root.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
