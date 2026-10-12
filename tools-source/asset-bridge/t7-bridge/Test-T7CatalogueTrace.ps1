# Synthetic provenance and bounded stderr only; no native process, lease or stock.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern){
    $caught=$false
    try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected error: '+$_.Exception.Message)}
    Check $caught ('Expected refusal: '+$Pattern)
}
function Copy-Value($Value){$Value|ConvertTo-Json -Depth 16|ConvertFrom-Json}
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-trace-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
$context=[pscustomobject]@{Guards=[Collections.Generic.List[object]]::new()}
function Close-Guards {foreach($guard in $context.Guards){$guard.Dispose()};$context.Guards.Clear()}
function New-Pin([string]$Path,[string]$Hash=('a'*64)) {[pscustomobject]@{Path=$Path;Bytes=100;SHA256=$Hash}}
function New-Binding($Pin) {[pscustomobject]@{Path=$Pin.Path;Bytes=$Pin.Bytes;SHA256=$Pin.SHA256;IsText=$true}}
function New-Fixture {
    $buildPath=Join-Path $root 'build.json';$basePath=Join-Path $root 'base.json'
    $prepared=Join-Path $root 'prepared';$run=Join-Path $root 'run';$rsp=Join-Path $root 'link.rsp'
    $obj=Join-Path $run 'main/main.obj';$deps=Join-Path $run 'main/dependencies.json';$candidate=Join-Path $run 'link/zonetool-t7.exe'
    $prior=Join-Path $root 'prior'
    $reuse=[pscustomobject]@{OriginalStatus='Failed';Checks=51;RecompiledMain=$true;
        SourcePlan=(Join-Path $root 'compile.json');SourcePlanSHA256=('c'*64);Receipt=(Join-Path $root 'compile-receipt.json');ReceiptSHA256=('d'*64);
        StageRoots=@((Join-Path $prior 'zonetool11'),(Join-Path $prior 'xpak'))}
    $profile=[pscustomobject]@{Name='t7-catalog-trace';Option='-t7-iw7-catalog';ArgumentCount=3;TraceSchema='iw7.t7-catalog-trace/1';
        Wiring=(New-Pin (Join-Path $root 'prepare_catalog_trace.py'));PreparedMain=(New-Pin (Join-Path $prepared 'main.cpp'));
        BaseBuildPlan=(New-Pin $basePath 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa');
        BaseBuildReceipt=(New-Pin (Join-Path $root 'base-receipt.json') 'c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2')}
    $pins=@(foreach($name in 'Wiring','PreparedMain','BaseBuildPlan','BaseBuildReceipt'){New-Binding $profile.$name})
    $priorPins=@((New-Binding (New-Pin $reuse.SourcePlan $reuse.SourcePlanSHA256)),(New-Binding (New-Pin $reuse.Receipt $reuse.ReceiptSHA256)))
    $build=[pscustomobject]@{Schema='iw7.t7-minimal-build-plan/1';SourceCommit='fab935826c898806855376662a8a03317b3ad8f1';
        PreparedRoot=$prepared;RunRoot=$run;Runner=(Join-Path $root 'Run-T7Build.ps1');BuildProfile=$profile;ReuseCompile=$reuse;
        Bindings=@($pins)+@($priorPins)+@((New-Binding (New-Pin $rsp)));
        Stages=@([pscustomobject]@{Name='main';Stage='Compile'},[pscustomobject]@{Name='link';Stage='Link';Arguments=@('@'+$rsp)})}
    $base=[pscustomobject]@{Schema='iw7.t7-minimal-build-plan/1';ReuseCompile=(Copy-Value $reuse);Bindings=(Copy-Value $priorPins)}
    $base.ReuseCompile.StageRoots=@((Join-Path $prior 'main'))+@($reuse.StageRoots);$base.ReuseCompile.RecompiledMain=$false
    $receipt=[pscustomobject]@{Schema='iw7.t7-minimal-build/1';PlanSHA256=('b'*64);Status='Passed';InputsReverified=$true;TreeClosureConfirmed=$true;
        LeaseReleased=$true;Quarantined=$false;CandidateExecuted=$false;BuildProfile=(Copy-Value $profile);
        Stages=@([pscustomobject]@{Name='main';Stage='Compile';PlanSHA256=('b'*64);ExitCode=0;TreeClosureConfirmed=$true;Artifacts=@((New-Pin $obj),(New-Pin $deps))},
                 [pscustomobject]@{Name='link';Stage='Link';PlanSHA256=('b'*64);ExitCode=0;TreeClosureConfirmed=$true;Artifacts=@((New-Pin $candidate))})}
    $plan=[pscustomobject]@{CandidateProfile='t7-catalog-trace';BuildPlan=$buildPath;ExpectedBuildPlanSHA256=('b'*64);
        CandidateSource=$candidate;CandidateBytes=100;CandidateSHA256=('a'*64);
        Bindings=@($pins)+@((New-Binding (New-Pin $buildPath ('b'*64))),(New-Binding (New-Pin $deps)),(New-Binding (New-Pin $rsp)))}
    $script:json=@{};$script:json[$buildPath]=$build;$script:json[$basePath]=$base
    $script:json[$deps]=[pscustomobject]@{Data=[pscustomobject]@{Source=$profile.PreparedMain.Path}}
    [IO.File]::WriteAllText($rsp,('"'+$obj+'"'+"`n"))
    [pscustomobject]@{Plan=$plan;Build=$build;Receipt=$receipt;Base=$base;Deps=$script:json[$deps];Rsp=$rsp;Object=$obj}
}
# The runner holds/hash-checks all text pins before this qualifier. Here only the
# provenance JSON reader is stubbed; link.rsp and stderr are real synthetic files.
function Read-H1SmallJson([string]$Path,[int]$Limit=128KB){$script:json[$Path]}
try {
    Check ((Get-T7CatalogueCandidateProfile ([pscustomobject]@{})) -ceq 'ordinary-d2') 'Implicit D2 lost.'
    foreach($name in 't7-prepatch-probe','unknown','T7-CATALOG-TRACE','') {
        Refuses {Get-T7CatalogueCandidateProfile ([pscustomobject]@{CandidateProfile=$name})} 'Unknown catalogue'
    }
    $f=New-Fixture;Assert-T7CatalogueBuild $f.Plan $f.Receipt;$checks++
    $f=New-Fixture;$f.Plan.CandidateProfile='t7-catalog-exit-context'
    foreach($profile in @($f.Build.BuildProfile,$f.Receipt.BuildProfile)){
        $profile.Name='t7-catalog-exit-context';$profile|Add-Member NoteProperty ContextSchema 'iw7.t7-catalog-exit-context/1'
    }
    Assert-T7CatalogueBuild $f.Plan $f.Receipt;$checks++
    $f.Receipt.BuildProfile.ContextSchema='unknown'
    Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Exact exit context schema'
    $f.Receipt.BuildProfile.PSObject.Properties.Remove('ContextSchema')
    Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Exact catalogue fields'
    $f=New-Fixture;$f.Plan.CandidateProfile='t7-catalog-exit-context'
    Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Exact catalogue fields'
    foreach($side in 'Build','Receipt') {
        foreach($field in 'Name','ContextSchema','CallerSchema') {
            $f=New-Fixture;$f.Plan.CandidateProfile='t7-catalog-callers'
            foreach($profile in @($f.Build.BuildProfile,$f.Receipt.BuildProfile)) {
                $profile.Name='t7-catalog-callers'
                $profile|Add-Member NoteProperty ContextSchema 'iw7.t7-catalog-exit-context/1'
                $profile|Add-Member NoteProperty CallerSchema 'iw7.t7-catalog-callers/1'
            }
            Assert-T7CatalogueBuild $f.Plan $f.Receipt;$checks++
            $f.$side.BuildProfile.$field='unknown'
            Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Exact .*(profile|schema)'
            $f.$side.BuildProfile.PSObject.Properties.Remove($field)
            Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Exact catalogue fields'
        }
    }
    $f=New-Fixture;$f.Plan.CandidateProfile='t7-catalog-callers'
    Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Exact catalogue fields'
    $f=New-Fixture;$f.Receipt.BuildProfile|Add-Member NoteProperty CallerSchema 'iw7.t7-catalog-callers/1'
    Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Exact catalogue fields'
    $cases=@(
        @{Change={$f.Build.BuildProfile.Name='unknown'};Error='Exact catalogue trace'},
        @{Change={$f.Build.BuildProfile.Option='-new-mode'};Error='Exact catalogue trace'},
        @{Change={$f.Build.BuildProfile.ArgumentCount='3'};Error='Exact catalogue trace'},
        @{Change={$f.Build.BuildProfile.TraceSchema='other'};Error='Exact catalogue trace'},
        @{Change={$f.Receipt.BuildProfile|Add-Member NoteProperty Extra $true};Error='Exact catalogue fields'},
        @{Change={$f.Build.SourceCommit='0'*40};Error='source/schema'},
        @{Change={$f.Build.ReuseCompile.RecompiledMain=$false};Error='recompile main'},
        @{Change={$f.Build.ReuseCompile.RecompiledMain='true'};Error='recompile main'},
        @{Change={$f.Build.ReuseCompile.SourcePlanSHA256='0'*64};Error='reuse chain'},
        @{Change={$f.Build.ReuseCompile.StageRoots+=@(Join-Path $root 'prior/main')};Error='retained'},
        @{Change={$f.Build.ReuseCompile.StageRoots=@($f.Build.ReuseCompile.StageRoots[1],$f.Build.ReuseCompile.StageRoots[0])};Error='retained'},
        @{Change={$f.Build.PreparedRoot=Join-Path $root 'wrong'};Error='source/base'},
        @{Change={$f.Build.Runner=Join-Path $root 'wrong/runner.ps1'};Error='source/base'},
        @{Change={$f.Plan.Bindings[0].IsText=$false};Error='not guarded'},
        @{Change={$f.Build.Bindings[4].SHA256='0'*64};Error='not guarded'},
        @{Change={$f.Receipt.BuildProfile.PreparedMain.SHA256='0'*64};Error='Receipt trace'},
        @{Change={$f.Build.Stages=@($f.Build.Stages[1])};Error='actual main'},
        @{Change={$f.Receipt.Stages[0].Stage='Link'};Error='actual main'},
        @{Change={$f.Receipt.Stages[0].ExitCode=1};Error='not successful'},
        @{Change={$f.Receipt.Stages[1].TreeClosureConfirmed=$false};Error='not successful'},
        @{Change={$f.Receipt.Stages[0].PlanSHA256='0'*64};Error='not successful'},
        @{Change={$f.Receipt.Stages[0].Artifacts=@($f.Receipt.Stages[0].Artifacts[0])};Error='main artifact'},
        @{Change={$f.Deps.Data.Source=Join-Path $root 'old-main.cpp'};Error='dependencies'},
        @{Change={$f.Build.Stages[1].Arguments=@('@wrong.rsp')};Error='link command'},
        @{Change={[IO.File]::AppendAllText($f.Rsp,('"'+$f.Object+'"'+"`n"))};Error='exactly once'},
        @{Change={$f.Receipt.Stages[1].Artifacts[0].SHA256='0'*64};Error='build artifact'},
        @{Change={$f.Receipt.Status='Failed'};Error='successful unexecuted'},
        @{Change={$f.Receipt.CandidateExecuted=$true};Error='successful unexecuted'},
        @{Change={$f.Receipt.LeaseReleased='true'};Error='booleans'},
        @{Change={$f.Plan.ExpectedBuildPlanSHA256='daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa';$f.Receipt.PlanSHA256=$f.Plan.ExpectedBuildPlanSHA256;$f.Plan.Bindings[4].SHA256=$f.Plan.ExpectedBuildPlanSHA256};Error='own guarded'}
    )
    foreach($case in $cases){$f=New-Fixture;. $case.Change;Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} $case.Error}
    $prefix='[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase='
    $enabled=$prefix+"enabled stdout_unbuffered=1 stderr_unbuffered=1 tid=42`n"
    $boundary=$prefix+"before_post_unpack code=0 tid=42 return_address=0000000000000000`n"
    $exitLine=$prefix+"exit_hook code=-2147483648 tid=4294967295 return_address=000000014012ABCD`n"
    Check ((ConvertFrom-T7CatalogueTrace '').Outcome -ceq 'NoTrace') 'Empty trace changed.'
    Check ((ConvertFrom-T7CatalogueTrace $boundary).Outcome -ceq 'TracePartial') 'Partial trace overclaimed.'
    $complete=$enabled+$boundary
    foreach($phase in 'after_post_unpack','before_entry_point','entry_point_return'){$complete+=$prefix+$phase+" code=0 tid=42 return_address=0000000000000000`n"}
    $complete+=$exitLine
    $parsed=ConvertFrom-T7CatalogueTrace $complete
    Check ($parsed.Outcome -ceq 'TraceObserved' -and $parsed.Events.Count -eq 6 -and $parsed.Events[5].Code -eq [int]::MinValue) 'Six valid events lost.'
    Check ((ConvertFrom-T7CatalogueTrace ($complete.Replace("`n","`r`n"))).Events.Count -eq 6) 'CRLF trace lost.'
    Check ((ConvertFrom-T7CatalogueTrace ($exitLine+$enabled)).Outcome -ceq 'TraceObserved') 'Event order wrongly assumed.'
    $partial=ConvertFrom-T7CatalogueTrace ($enabled.Replace('unbuffered=1','unbuffered=0'))
    Check (!$partial.Events[0].StdoutUnbuffered -and !$partial.Events[0].StderrUnbuffered) 'setvbuf failure flags lost.'
    # The five-event shape actually observed in D remains valid under /1.
    $observedD=@(
        $prefix+'enabled stdout_unbuffered=1 stderr_unbuffered=1 tid=31804'
        $prefix+'before_entry_point code=0 tid=31804 return_address=0000000000000000'
        $prefix+'before_post_unpack code=0 tid=31804 return_address=0000000000000000'
        $prefix+'after_post_unpack code=0 tid=31804 return_address=0000000000000000'
        $prefix+'exit_hook code=0 tid=18184 return_address=0000000140AC00C4'
    ) -join "`r`n"
    $observed=ConvertFrom-T7CatalogueTrace ($observedD+"`r`n")
    Check ($observed.Outcome -ceq 'TraceObserved' -and $observed.Events.Count -eq 5 -and
        $observed.Events[4].ThreadId -eq 18184 -and $observed.Events[4].ReturnAddress -ceq '0000000140AC00C4' -and
        @($observed.Events|Where-Object Phase -CEQ 'entry_point_return').Count -eq 0) 'Observed D trace changed or invented a return.'
    foreach($bad in @($enabled.TrimEnd("`n"),($enabled+$enabled),($complete+$boundary),($prefix+"unknown code=0 tid=42 return_address=0000000000000000`n"),
        $enabled.Replace('tid=42','tid=4294967296'),$enabled.Replace('tid=42','tid=042'),$enabled.Replace('unbuffered=1','unbuffered=2'),
        $boundary.Replace('code=0','code=1'),$boundary.Replace('code=0','code=-0'),$boundary.Replace('0000000000000000','0000000000000001'),
        $exitLine.Replace('-2147483648','2147483648'),$exitLine.Replace('-2147483648','-2147483649'),$exitLine.Replace('return_address=','return_address=0x'),
        ($enabled+"ordinary stderr`n"),($enabled+"`n"),([char]0xfeff+$enabled),(('x'*255)+"`n"),(('x'*1535)+"`n"))) {
        Refuses {ConvertFrom-T7CatalogueTrace $bad} 'Trace|trace|stderr|boundary'
    }
    $plan=[pscustomobject]@{CandidateProfile='t7-catalog-trace';StageRoot=$root};$state=[ordered]@{}
    Read-T7CatalogueTrace $plan $state $context
    Check ($state.TraceOutcome -ceq 'NoTrace' -and $context.Guards.Count -eq 0) 'Absent log read.'
    $log=Join-Path $root 'stderr.log'
    [IO.File]::WriteAllText($log,$enabled,[Text.UTF8Encoding]::new($false))
    Read-T7CatalogueTrace $plan $state $context
    Check ($state.TraceOutcome -ceq 'TraceObserved' -and $context.Guards.Count -eq 1) 'Guarded trace lost.'
    Refuses {[IO.File]::AppendAllText($log,'x')} '.'
    Close-Guards
    [IO.File]::WriteAllText($log,$enabled,[Text.UnicodeEncoding]::new($false,$true))
    Refuses {Read-T7CatalogueTrace $plan $state $context} 'format|decode|translate'
    Check ($state.TraceOutcome -ceq 'TracePresentUnqualified') 'Invalid bytes overclaimed.'
    Close-Guards
    [IO.File]::WriteAllBytes($log,[byte[]]::new(1536))
    Refuses {Read-T7CatalogueTrace $plan $state $context} 'cap exceeded'
    Check ($context.Guards.Count -eq 0) 'Oversized trace was read.'
    [IO.File]::WriteAllBytes($log,[byte[]]::new(0))
    Read-T7CatalogueTrace $plan $state $context
    Check ($state.TraceOutcome -ceq 'NoTrace') 'Empty file overclaimed.'
    Close-Guards
    [ordered]@{Status='Passed';Checks=$checks;NativeTypesLoaded=$false;RealLeaseAcquired=$false;NativeProcessStarted=$false;OwnerStockRead=$false}|ConvertTo-Json
}finally{
    Close-Guards
    $resolved=[IO.Path]::GetFullPath($root);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notmatch '^t7-trace-tests-[0-9a-f]{32}$'){throw 'Refuse cleanup outside exact synthetic trace root.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
