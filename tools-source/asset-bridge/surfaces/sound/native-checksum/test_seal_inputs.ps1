$ErrorActionPreference='Stop'
. "$PSScriptRoot/SealInputs.Core.ps1"
function Add-Type {throw 'Native type load forbidden by source test.'}
$root=Join-Path ([IO.Path]::GetTempPath()) ('sound-seal-source-test-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
$script:checks=0;$script:enters=0;$script:exits=0;$script:releaseFailure=$false;$script:clock=0L
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Enter-IW7ResourceLease {param($Scope,$Kind,$PhysicalBytes,$CommitBytes,$Owner)
    Check ($Kind -ceq 'Analysis' -and $PhysicalBytes -eq 1GB -and $CommitBytes -eq 2GB) 'Exact sealing admission'
    $script:enters++;[pscustomobject]@{Token='mock-seal-lease'}
}
function Exit-IW7ResourceLease {param($Token)
    Check ($Token -ceq 'mock-seal-lease') 'Only original mock lease released'
    $script:exits++;if($script:releaseFailure){throw 'mock release refused'}
}
function Get-IW7ResourceSnapshot {[pscustomobject]@{CommitLimit=50GB;Committed=10GB}}
function Get-ChecksumSealClock {$script:clock}
function Fixture([string]$Name){
    $dir=Join-Path $root $Name;[IO.Directory]::CreateDirectory($dir)|Out-Null
    $files=@()
    foreach($pair in @(@('one.txt','abcd'),@('empty.txt',''))){
        $p=Join-Path $dir $pair[0];[IO.File]::WriteAllText($p,$pair[1]);$f=Get-Item -LiteralPath $p
        $files+=,[pscustomobject]@{Path=$p;Bytes=[long]$f.Length;Attributes=[int]$f.Attributes;ModifiedUtcTicks=$f.LastWriteTimeUtc.Ticks;
            Category='fixture';ExpectedSHA256=(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant()}
    }
    [pscustomobject]@{Recipe=[pscustomobject]@{OutputRoot=(Join-Path $dir 'seal');InventorySHA256=('a'*64)};
        Inventory=[pscustomobject]@{Schema='iw7.sound-checksum-input-inventory/1';FileCount=2;TotalBytes=4L;Inputs=$files}}
}
function Failure($Fixture){
    $failed=$false
    try{$null=Invoke-ChecksumInputSeal $Fixture.Recipe $Fixture.Inventory ('b'*64)}catch{$failed=$true}
    Check $failed 'Failure must propagate'
    $path=Join-Path $Fixture.Recipe.OutputRoot 'state.local.json'
    if(Test-Path -LiteralPath $path){Get-Content -LiteralPath $path -Raw|ConvertFrom-Json}
}
try {
    $f=Fixture 'success';$f.Inventory=($f.Inventory|ConvertTo-Json -Depth 8|ConvertFrom-Json);$script:guardDenied=$false
    function Read-ChecksumSealChunk($Stream,[byte[]]$Buffer){
        try{[IO.File]::WriteAllText($Stream.Name,'unsafe')}catch [IO.IOException]{$script:guardDenied=$true}
        $Stream.Read($Buffer,0,$Buffer.Length)
    }
    $s=Invoke-ChecksumInputSeal $f.Recipe $f.Inventory ('b'*64)
    Check ($s.Status -ceq 'Sealed' -and $s.LeaseReleased -and !$s.RetainedLeaseToken) 'Complete read-only seal'
    Check ($s.BytesRead -eq 8 -and $s.GuardsOpened -eq 4 -and $s.GuardsDisposed -eq 4) 'Two guarded passes including empty source'
    Check $script:guardDenied 'Concurrent source writes denied by real FileStream guards'
    Check ($s.OutputBytes -eq (Measure-ChecksumSealOutput $f.Recipe.OutputRoot)) 'Serialized receipt included in accounting'
    Check ($s.NativeCommandsStarted -eq 0 -and !$s.ProbeTypesLoaded -and !$s.Ready) 'No native or readiness claim'
    function Read-ChecksumSealChunk($Stream,[byte[]]$Buffer){$Stream.Read($Buffer,0,$Buffer.Length)}
    $f=Fixture 'metadata';$f.Inventory.Inputs[0].ModifiedUtcTicks++
    $s=Failure $f
    Check ($s.Status -ceq 'Failed' -and $s.BytesRead -eq 0 -and $s.LeaseReleased) 'Metadata drift refuses before content read'
    $f=Fixture 'digest';$f.Inventory.Inputs[0].ExpectedSHA256='0'*64
    $s=Failure $f
    Check (!$s.InputHashesVerifiedTwice -and $s.LeaseReleased -and $s.GuardsOpened -eq $s.GuardsDisposed) 'Prior known digest drift refuses'
    $f=Fixture 'late-read';$script:clock=0L
    function Read-ChecksumSealChunk($Stream,[byte[]]$Buffer){$read=$Stream.Read($Buffer,0,$Buffer.Length);$script:clock+=120000;return $read}
    $s=Failure $f
    Check ($s.BytesRead -eq 4 -and $s.ReadCalls -eq 1 -and !$s.InputHashesVerifiedTwice) 'Late blocking read counted and rejected'
    Check (!$s.BlockingIOPreempted -and $s.LeaseReleased) 'No false I/O preemption or job claim'
    function Read-ChecksumSealChunk($Stream,[byte[]]$Buffer){$Stream.Read($Buffer,0,$Buffer.Length)}
    $script:clock=0L;$script:releaseFailure=$true;$f=Fixture 'release'
    $s=Failure $f
    Check ($s.Status -ceq 'Failed' -and !$s.LeaseReleased -and $s.RetainedLeaseToken -ceq 'mock-seal-lease') 'Refused release remains explicit'
    $script:releaseFailure=$false;$f=Fixture 'duplicate';$before=$script:enters
    $f.Inventory.Inputs[1]=$f.Inventory.Inputs[0]
    $s=Failure $f
    Check ($script:enters -eq $before) 'Duplicate inventory rejected before admission'
    $f=Fixture 'read-error'
    function Read-ChecksumSealChunk($Stream,[byte[]]$Buffer){throw [IO.IOException]::new('mock failed read')}
    $s=Failure $f
    Check ($s.GuardsOpened -eq $s.GuardsDisposed -and $s.LeaseReleased -and !$s.InputHashesVerifiedTwice) 'Read errors close guards and release read-only lease'
    function Read-ChecksumSealChunk($Stream,[byte[]]$Buffer){$Stream.Read($Buffer,0,$Buffer.Length)}
    $script:realWriter=(Get-Command Write-ChecksumSealJson).ScriptBlock
    function Write-ChecksumSealJson([string]$Path,$Value){
        & $script:realWriter $Path $Value
        if($Value.Schema -ceq 'iw7.sound-checksum-input-seal-result/1'){$script:clock=120000}
    }
    $script:clock=0L;$f=Fixture 'late-state';$s=Failure $f
    Check ($s.Status -ceq 'Failed' -and $s.ElapsedMs -eq 120000 -and $s.LeaseReleased) 'Slow final state write cannot preserve a successful receipt'
    Check (!(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7.AnimationRig.JobMembers' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]))) 'No native types loaded'
    [ordered]@{Checks=$script:checks;Cases=8;NativeCommands=0;LiveReservations=0}|ConvertTo-Json
} finally {
    # Explicit file cleanup within this test's verified unique temporary root.
    foreach($p in Get-ChildItem -LiteralPath $root -Recurse -File){Remove-Item -LiteralPath $p.FullName -Force}
    foreach($p in Get-ChildItem -LiteralPath $root -Recurse -Directory|Sort-Object FullName -Descending){[IO.Directory]::Delete($p.FullName)}
    [IO.Directory]::Delete($root)
}
