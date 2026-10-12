# Pure PowerShell fault injection: no native type, lease or process is started.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Invoke-SteamMetadata.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
foreach($name in 'Read-SteamSnapshot','Assert-SteamExecutableFileList','Measure-SteamAttempt','Assert-SteamOriginal','Wait-SteamOriginal','Close-SteamAttempt') {
    $fn=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
    if(!$fn){throw ('Missing host function '+$name)}
    . ([scriptblock]::Create($fn.Extent.Text))
}
$script:checks=0;$script:clock=0
function Get-H1Clock {$script:clock}
function Check([bool]$Condition,[string]$Message){if(!$Condition){throw $Message};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern){
    $caught=$false
    try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected error: '+$_.Exception.Message)}
    Check $caught ('Expected rejection: '+$Pattern)
}
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('steam-metadata-host-tests-'+[guid]::NewGuid().ToString('N'))
$tool=Join-Path $temporary 'tool';$outer=Join-Path $temporary 'outer'
$null=[IO.Directory]::CreateDirectory((Join-Path $tool 'cache'));$null=[IO.Directory]::CreateDirectory($outer)
$settings=[pscustomobject]@{tool_root=$tool;outer_evidence_root=$outer}
try {
    $snapshotPath=Join-Path $outer 'snapshot.txt'
    $replacement=Join-Path $outer 'replacement.txt'
    $original=[Text.Encoding]::UTF8.GetBytes('observed header and bytes')
    [IO.File]::WriteAllBytes($snapshotPath,$original)
    [IO.File]::WriteAllText($replacement,'replacement content')
    $held=[Collections.Generic.List[IO.FileStream]]::new()
    try {
        $snapshot=Read-SteamSnapshot $snapshotPath 64 $held
        Check ($snapshot.Length -eq $original.Length -and $held.Count -eq 1 -and !$held[0].SafeFileHandle.IsClosed) 'Snapshot guard was not retained.'
        Check ($snapshot.SHA256 -ceq [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($snapshot.Bytes)).ToLowerInvariant() -and
            [Text.Encoding]::UTF8.GetString($snapshot.Bytes) -ceq 'observed header and bytes') 'Header and digest did not use the same snapshot.'
        Refuses {[IO.File]::AppendAllText($snapshotPath,'growth')} '.'
        Refuses {[IO.File]::Move($replacement,$snapshotPath,$true)} '.'
        Check ([IO.File]::ReadAllText($snapshotPath) -ceq 'observed header and bytes' -and (Test-Path -LiteralPath $replacement)) 'Guarded file was replaced or grew.'
    }finally{foreach($guard in $held){$guard.Dispose()};$held.Clear()}
    [IO.File]::WriteAllBytes($snapshotPath,[byte[]]::new(65))
    Refuses {Read-SteamSnapshot $snapshotPath 64 $held} 'exceeds byte bound'
    Check ($held.Count -eq 0 -and $snapshot.Length -eq $original.Length -and
        [Text.Encoding]::UTF8.GetString($snapshot.Bytes) -ceq 'observed header and bytes') 'Oversize read retained a handle or mutated earlier snapshot.'
    Remove-Item -LiteralPath $snapshotPath,$replacement
    $listPath=Join-Path $outer 'filelist.txt'
    try {
        [IO.File]::WriteAllText($listPath,"UnrankedServer/BlackOps3_UnrankedDedicatedServer.exe`n",[Text.UTF8Encoding]::new($false))
        $list=Assert-SteamExecutableFileList $listPath $held
        Check ($held.Count -eq 1 -and $list.Length -gt 0) 'Literal allowlist was not retained.'
    }finally{foreach($guard in $held){$guard.Dispose()};$held.Clear()}
    foreach($bad in @("regex:.*`n","UnrankedServer/BlackOps3_UnrankedDedicatedServer.exe`nUnrankedServer/zone/example.ff`n",'')) {
        try {
            [IO.File]::WriteAllText($listPath,$bad,[Text.UTF8Encoding]::new($false))
            Refuses {Assert-SteamExecutableFileList $listPath $held} 'exact one-file literal'
        }finally{foreach($guard in $held){$guard.Dispose()};$held.Clear()}
    }
    Remove-Item -LiteralPath $listPath
    [IO.File]::WriteAllBytes((Join-Path $tool 'cache/data'),[byte[]](1,2,3))
    [IO.File]::WriteAllBytes((Join-Path $outer 'stdout.log'),[byte[]](4,5))
    $sample=Measure-SteamAttempt $settings 0
    Check ($sample.ToolBytes -eq 3 -and $sample.OuterBytes -eq 2 -and $sample.TotalBytes -eq 5) 'Aggregate metadata accounting differs.'
    [IO.File]::WriteAllBytes((Join-Path $outer 'stdout.log'),[byte[]]::new(65537))
    Refuses {Measure-SteamAttempt $settings 0} 'Outer log cap'
    [IO.File]::WriteAllBytes((Join-Path $outer 'stdout.log'),[byte[]](4,5))
    $script:clock=200000;Refuses {Measure-SteamAttempt $settings 0} 'deadline'
    $script:clock=0
    [IO.File]::WriteAllBytes((Join-Path $outer 'manifest-test.txt'),[byte[]]::new(1MB))
    Refuses {Measure-SteamAttempt $settings 0} 'Private output byte cap'
    $settings|Add-Member NoteProperty operation 'depot-file-manifest'
    $manifestSample=Measure-SteamAttempt $settings 0
    Check ($manifestSample.OuterBytes -eq 1MB+2) 'Manifest metadata needs its explicit larger output cap.'
    Remove-Item -LiteralPath (Join-Path $outer 'manifest-test.txt')

    function Measure-SteamAttempt($Settings,$Started){$script:clock+=$script:budgetDelay;[pscustomobject]@{TotalBytes=5}}
    function Get-IW7ResourceSnapshot {[pscustomobject]@{CommitLimit=100;Committed=$script:commit}}
    function Start-Sleep {param([int]$Milliseconds,[int]$Seconds);$script:clock+=$Milliseconds+1000*$Seconds}
    function Get-H1OriginalState($Owner){$script:clock+=$script:sampleDelay;$script:samples.Dequeue()}
    function Stop-H1OriginalJob($Owner){$script:events.Add('stop');if($script:stopFails){throw 'injected stop failure'}}
    function Exit-IW7ResourceLease($Token){$script:events.Add('release');if($script:releaseFails){throw 'injected release failure'}}
    function Reset-Case {
        $script:clock=0;$script:budgetDelay=0;$script:sampleDelay=0;$script:commit=20
        $script:stopFails=$false;$script:releaseFails=$false
        $script:events=[Collections.Generic.List[string]]::new()
        $script:samples=[Collections.Generic.Queue[object]]::new()
        $owner=[pscustomobject]@{PID=123;Closed=$false;Empty=$false}
        $owner|Add-Member ScriptMethod CloseConfirmed {$script:events.Add('close');$this.Closed=$true}
        $owner|Add-Member ScriptMethod TreeExited {return $this.Empty}
        $script:context=[pscustomobject]@{Owner=$owner;Lease=[pscustomobject]@{Token='test'};Closed=$false}
        $script:state=[ordered]@{Status='Failed';Identity=[ordered]@{PID=123;Image='pinned-python';CreatedUtc='time'};
            ForcedStop=$false;TreeClosureConfirmed=$false;LeaseReleased=$false;Quarantined=$false}
    }
    function Enqueue-Sample([bool]$Exited,[int]$Active,[int]$Code=0,[string]$Image='pinned-python') {
        $script:samples.Enqueue([pscustomobject]@{RootExited=$Exited;ActiveProcesses=$Active;RootExitCode=$Code;PID=123;Image=$Image;CreatedUtc='time'})
    }
    Reset-Case;Enqueue-Sample $true 0
    Wait-SteamOriginal $settings $state $context 0
    Check ($context.Closed -and $state.TreeClosureConfirmed -and ($events -join ',') -ceq 'close') 'Timely original tree did not close.'
    Close-SteamAttempt $state $context
    Check ($state.LeaseReleased -and !$context.Lease -and ($events -join ',') -ceq 'close,release') 'Lease release ordering differs.'

    Reset-Case;Enqueue-Sample $true 1;Enqueue-Sample $true 0
    Wait-SteamOriginal $settings $state $context 0
    Check ($clock -eq 250 -and $context.Closed) 'Root exit alone closed live children.'

    Reset-Case;Enqueue-Sample $true 0;$script:sampleDelay=200000
    Refuses {Wait-SteamOriginal $settings $state $context 0} 'deadline'
    Check (!$context.Closed -and $events.Count -eq 0) 'Late success closed before deadline refusal.'

    Reset-Case;Enqueue-Sample $true 0 2
    Refuses {Wait-SteamOriginal $settings $state $context 0} 'root failed'
    Check (!$context.Closed) 'Nonzero root accepted.'

    Reset-Case;Enqueue-Sample $true 1 2
    Refuses {Wait-SteamOriginal $settings $state $context 0} 'Failed root left'
    Check (!$context.Closed) 'Failed root with children accepted.'

    Reset-Case;Enqueue-Sample $true 0 0 'different-python'
    Refuses {Wait-SteamOriginal $settings $state $context 0} 'identity changed'

    Reset-Case;$script:commit=86
    Refuses {Wait-SteamOriginal $settings $state $context 0} 'Commit high water'

    Reset-Case;Enqueue-Sample $false 2;Enqueue-Sample $true 0 375
    Close-SteamAttempt $state $context
    Check ($state.ForcedStop -and $state.AfterStopOriginalSnapshot.ActiveProcesses -eq 0 -and
        $context.Closed -and $state.LeaseReleased -and ($events -join ',') -ceq 'stop,close,release') 'Fresh post-stop closure not required.'
    Check ($state.Status -ceq 'Failed') 'Forced stop became success.'

    Reset-Case;$script:stopFails=$true
    Close-SteamAttempt $state $context
    Check ($state.Quarantined -and $context.Lease -and !$context.Closed -and ($events -join ',') -ceq 'stop') 'Failed stop lost owner/lease.'

    Reset-Case;Enqueue-Sample $true 0;$script:sampleDelay=5000
    Close-SteamAttempt $state $context
    Check ($state.Quarantined -and !$context.Closed -and !$state.LeaseReleased) 'Late cleanup released ownership.'

    Reset-Case;Enqueue-Sample $true 0;$script:releaseFails=$true
    Close-SteamAttempt $state $context
    Check ($state.Quarantined -and $context.Closed -and $context.Lease -and !$state.LeaseReleased) 'Failed release lost retained lease.'

    Reset-Case;$context.Owner.PID=0;$context.Owner.Empty=$true
    Close-SteamAttempt $state $context
    Check ($state.NoProcessCreated -and $context.Closed -and $state.LeaseReleased -and !$state.ForcedStop) 'Pre-create failure could not close safely.'
    [ordered]@{Status='Passed';Checks=$checks;NativeTypesLoaded=$false;SteamCmdStarted=$false;LeaseAcquired=$false}|ConvertTo-Json
}finally{
    # Exact fresh test root only; all files above are synthetic and under it.
    $resolved=[IO.Path]::GetFullPath($temporary)
    $parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notmatch '^steam-metadata-host-tests-[0-9a-f]{32}$'){throw 'Refuse test cleanup outside exact temp root.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
