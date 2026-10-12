# Ordinary source-only host-root tests. No GC experiment or native execution.
$ErrorActionPreference='Stop'
. "$PSScriptRoot/BuildCandidate.Core.ps1"
function Add-Type {throw 'Quarantine test must not load native types'}
function Enter-IW7ResourceLease {throw 'Quarantine test must not acquire a real lease'}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('sound-quarantine-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
$keys=[Collections.Generic.List[string]]::new();$checks=0
function Check($Value,[string]$Message){$script:checks++;if(!$Value){throw $Message}}
try {
    # The fixture invokes the actual policy in its own .ps1 scope and returns only
    # its key. All owner/context/guard strong references live in the host root.
    $child=Join-Path $temp 'fixture-scope.ps1'
    [IO.File]::WriteAllText($child,@'
param($Core,$InputPath,$BootstrapPath,$Token)
. $Core
$owner=[pscustomobject]@{FixtureOnly=$true;Identity=$Token;Disposed=$false}
$owner|Add-Member ScriptMethod Dispose {$this.Disposed=$true}
$inputs=[Collections.Generic.List[IDisposable]]::new()
$inputs.Add([IO.File]::Open($InputPath,'Open','Read','Read'))
$bootstrap=@{Retain=$false;Guards=[Collections.Generic.List[IDisposable]]::new()}
$bootstrap.Guards.Add([IO.File]::Open($BootstrapPath,'Open','Read','Read'))
$context=@{Record=[ordered]@{FixtureOnly=$true};InputGuards=$inputs}
Preserve-ChecksumBuildQuarantine $owner @{Token=$Token;FixtureOnly=$true} $context $bootstrap
'@)
    foreach($number in 1,2){
        $inputPath=Join-Path $temp ("input-$number.txt");$bootstrapPath=Join-Path $temp ("bootstrap-$number.txt")
        [IO.File]::WriteAllText($inputPath,'input');[IO.File]::WriteAllText($bootstrapPath,'bootstrap')
        $token='fixture-quarantine-'+[guid]::NewGuid().ToString('N')
        $key=& $child (Join-Path $PSScriptRoot 'BuildCandidate.Core.ps1') $inputPath $bootstrapPath $token
        $keys.Add($key)
        $held=[AppDomain]::CurrentDomain.GetData($key)
        Check ($held.Owner.FixtureOnly -and $held.Owner.Identity -ceq $token -and !$held.Owner.Disposed) 'returned script scope lost original owner'
        Check ([object]::ReferenceEquals($held.Owner,$held.Context.Owner) -and [object]::ReferenceEquals($held.InputGuards,$held.Context.InputGuards)) 'host root did not group original identities'
        Check ($held.Lease.Token -ceq $token -and $held.Bootstrap.Retain -and $held.Record.QuarantineKey -ceq $key) 'host root omitted reservation/bootstrap/record'
        foreach($path in $inputPath,$bootstrapPath){
            $denied=$false;$stream=$null
            try{$stream=[IO.File]::Open($path,'Open','ReadWrite','ReadWrite')}catch [IO.IOException]{$denied=$true}
            finally{if($stream){$stream.Dispose()}}
            Check $denied 'a guard was released on return from fixture .ps1'
        }
        $refused=$false
        try{$null=Preserve-ChecksumBuildQuarantine ([pscustomobject]@{FixtureOnly=$true}) @{Token=$token} @{Record=@{};InputGuards=@()} @{Retain=$false}}
        catch{$refused=$_.Exception.Message -ceq 'Existing sound quarantine must not be overwritten.'}
        Check ($refused -and [object]::ReferenceEquals([AppDomain]::CurrentDomain.GetData($key),$held)) 'duplicate quarantine silently replaced the original'
    }
    Check (![object]::ReferenceEquals([AppDomain]::CurrentDomain.GetData($keys[0]),[AppDomain]::CurrentDomain.GetData($keys[1]))) 'distinct reservations replaced each other'
    Check (!('IW7.CommunityBuild.BuildJob' -as [type]) -and !('IW7.AnimationRig.JobMembers' -as [type])) 'quarantine test loaded native types'
    [ordered]@{Assertions=$script:checks;ScopeReturns=2;GCExperiment=$false;NativeTypesLoaded=$false;RealReservations=0}|ConvertTo-Json
}finally{
    foreach($key in $keys){
        $held=[AppDomain]::CurrentDomain.GetData($key)
        if(!$held.Owner.FixtureOnly -or !$held.Record.FixtureOnly -or !$held.Lease.FixtureOnly -or $key -cnotlike 'IW7.SoundChecksum.Quarantine.fixture-quarantine-*'){throw 'Refusing nonfixture quarantine cleanup'}
        foreach($guard in $held.InputGuards){$guard.Dispose()}
        foreach($guard in $held.Bootstrap.Guards){$guard.Dispose()}
        $held.Owner.Dispose();[AppDomain]::CurrentDomain.SetData($key,$null)
    }
    $resolved=[IO.Path]::GetFullPath($temp);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notlike 'sound-quarantine-*'){throw 'Unsafe fixture cleanup path'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
