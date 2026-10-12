param([Parameter(Mandatory)][string]$FixtureRoot)
# Generated tiny fixtures only. No retail read, plan generation, lease or native job.
$ErrorActionPreference='Stop'
. "$PSScriptRoot/Recipient.Core.ps1"
$checks=0
function Check([bool]$Value,[string]$Name){if(!$Value){throw $Name};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Name){$failed=$false;try{& $Action|Out-Null}catch{$failed=$true};Check $failed $Name}
function Hash([byte[]]$Bytes){[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($Bytes))}
function Put([string]$Name,[byte[]]$Bytes){$path=Join-Path $FixtureRoot $Name;[IO.File]::WriteAllBytes($path,$Bytes);$path}
if(![IO.Path]::IsPathFullyQualified($FixtureRoot) -or (Test-Path -LiteralPath $FixtureRoot)){throw 'Fresh absolute generated-fixture directory required.'}
$null=New-Item -ItemType Directory -Path $FixtureRoot
$small=[Text.Encoding]::UTF8.GetBytes('{"value":"original","count":7}')
$path=Put 'small.json' $small;$hash=Hash $small
$doc=Read-RecipientInventorySnapshot $path $hash
Check ($doc.value -ceq 'original' -and $doc.count -eq 7) 'Valid same-snapshot hash and JSON'
$prefix='{"value":"';$suffix='"}'
$exact=[Text.Encoding]::UTF8.GetBytes($prefix+('p'*(128KB-$prefix.Length-$suffix.Length))+$suffix)
$exactPath=Put 'exact-limit.json' $exact
$doc=Read-RecipientInventorySnapshot $exactPath (Hash $exact)
Check ($exact.Length -eq 128KB -and $doc.value.Length -eq (128KB-$prefix.Length-$suffix.Length)) 'Exact 128 KiB JSON accepted'
$over=[byte[]]::new(128KB+1);$overPath=Put 'over-limit.json' $over
Refuses {Read-RecipientInventorySnapshot $overPath (Hash $over)} 'One byte over initial limit refused'
$bom=[byte[]](@(0xEF,0xBB,0xBF)+@($small));$bomPath=Put 'bom.json' $bom
Check ((Read-RecipientInventorySnapshot $bomPath (Hash $bom)).value -ceq 'original') 'BOM is hashed before UTF8 JSON decoding'
$invalid=[byte[]]@(0xC3,0x28);$invalidPath=Put 'invalid-utf8.json' $invalid
Refuses {Read-RecipientInventorySnapshot $invalidPath (Hash $invalid)} 'Invalid UTF8 refuses even with matching bytes hash'
$badJson=[Text.Encoding]::UTF8.GetBytes('{"incomplete":');$badJsonPath=Put 'invalid-json.json' $badJson
Refuses {Read-RecipientInventorySnapshot $badJsonPath (Hash $badJson)} 'Invalid JSON refuses even with matching bytes hash'
Refuses {Read-RecipientInventorySnapshot 'relative.json' $hash} 'Relative path refused'
Refuses {Read-RecipientInventorySnapshot $path 'not-a-hash'} 'Invalid hash refused'
$script:parseCalls=0
function ConvertFrom-Json {param($InputObject,[int]$Depth);$script:parseCalls++;Microsoft.PowerShell.Utility\ConvertFrom-Json -InputObject $InputObject -Depth $Depth}
try{
    Refuses {Read-RecipientInventorySnapshot $path ('0'*64)} 'Wrong hash refuses'
    Check ($script:parseCalls -eq 0) 'JSON parser never sees bytes that failed the digest'
}finally{Remove-Item Function:\ConvertFrom-Json}
# Managed synthetic stream permits short reads and an intentionally stale Length.
Add-Type -TypeDefinition @'
using System;
using System.IO;
public sealed class RecipientSnapshotFixtureStream : Stream {
    readonly byte[] data; readonly int chunk; readonly long reportedLength;
    long position; public int Calls; public long BytesRead;
    public RecipientSnapshotFixtureStream(byte[] data, int chunk, long reportedLength) {
        this.data=data; this.chunk=chunk; this.reportedLength=reportedLength;
    }
    public override int Read(byte[] buffer,int offset,int count) {
        Calls++; int n=Math.Min(Math.Min(count,chunk),data.Length-(int)position);
        Array.Copy(data,position,buffer,offset,n); position+=n; BytesRead+=n; return n;
    }
    public override bool CanRead=>true; public override bool CanWrite=>false; public override bool CanSeek=>false;
    public override long Length=>reportedLength;
    public override long Position {get=>position;set=>throw new NotSupportedException();}
    public override void Flush(){} public override long Seek(long a,SeekOrigin b)=>throw new NotSupportedException();
    public override void SetLength(long a)=>throw new NotSupportedException();
    public override void Write(byte[] a,int b,int c)=>throw new NotSupportedException();
}
'@
$short=[RecipientSnapshotFixtureStream]::new($small,3,$small.Length)
try{
    $bytes=Read-RecipientInventoryBytes $short
    Check ($bytes.Count -eq $small.Length -and $short.Calls -gt 2 -and (Hash $bytes.Buffer[0..($bytes.Count-1)]) -ceq $hash) 'Short reads accumulate exact bytes'
}finally{$short.Dispose()}
$growing=[RecipientSnapshotFixtureStream]::new([byte[]]::new(2MB),4096,1)
try{
    Refuses {Read-RecipientInventoryBytes $growing} 'Growth beyond stale length refuses by bytes actually read'
    Check ($growing.BytesRead -eq (128KB+1) -and $growing.Position -eq (128KB+1)) 'Oversized or growing input consumes at most 128 KiB plus one byte'
}finally{$growing.Dispose()}
$state=[pscustomobject]@{Handle=123;Length=7;CreatedTicks=100;ModifiedTicks=200;Attributes=32}
Assert-RecipientInventoryStable $state $state 7;$checks++
foreach($field in @('Handle','Length','CreatedTicks','ModifiedTicks','Attributes')){
    $changed=$state|ConvertTo-Json|ConvertFrom-Json;$changed.$field++
    Refuses {Assert-RecipientInventoryStable $state $changed 7} ('Changed handle metadata refuses: '+$field)
}
Refuses {Assert-RecipientInventoryStable $state $state 6} 'Short/truncated snapshot refuses stable reported length'
# Observe real Windows sharing semantics while the producer retains its handle.
$script:realState=(Get-Command Get-RecipientInventoryHandleState).ScriptBlock
$script:fixturePath=$path;$script:replacement=Put 'replacement.json' $small
$script:blocked=0;$script:attempted=0;$script:stateCalls=0
function Get-RecipientInventoryHandleState([IO.FileStream]$Stream){
    $script:stateCalls++
    foreach($action in @(
        {[IO.File]::Open($script:fixturePath,'Open','Write','ReadWrite').Dispose()},
        {[IO.File]::Move($script:fixturePath,($script:fixturePath+'.renamed'))},
        {[IO.File]::Delete($script:fixturePath)},
        {[IO.File]::Move($script:replacement,$script:fixturePath,$true)}
    )){
        $script:attempted++;try{& $action}catch [IO.IOException]{$script:blocked++}catch [UnauthorizedAccessException]{$script:blocked++}
    }
    & $script:realState $Stream
}
try{
    $doc=Read-RecipientInventorySnapshot $path $hash
    Check ($doc.value -ceq 'original' -and $script:stateCalls -eq 3) 'Original handle retained before read, after read and after parsing'
    Check ($script:blocked -eq 12 -and $script:attempted -eq 12) 'Writer, rename, delete and replacement refused throughout snapshot'
}finally{Set-Item Function:\Get-RecipientInventoryHandleState -Value $script:realState}
$write=[IO.File]::Open($path,'Open','Write','ReadWrite')
try{Refuses {Read-RecipientInventorySnapshot $path $hash} 'Conflicting pre-existing writer prevents guarded open'}finally{$write.Dispose()}
Refuses {Read-RecipientInventorySnapshot $path ('0'*64)} 'Digest failure releases guarded handle'
$write=[IO.File]::Open($path,'Open','Write','None');$write.Dispose();$checks++
Check ((Read-RecipientInventorySnapshot $path $hash).value -ceq 'original') 'Success and failure leave fixture content intact and handle reusable'
$core=Get-Content -Raw "$PSScriptRoot/Recipient.Core.ps1"
Check ($core.Contains('$completeInventory=Read-RecipientInventorySnapshot $Spec.RecipientCompleteInventoryReceipt') -and
    !$core.Contains('Read-BeaconJson $Spec.RecipientCompleteInventoryReceipt') -and
    !$core.Contains('Assert-BeaconHash $Spec.RecipientCompleteInventoryReceipt')) 'Complete inventory uses only the snapshot path before baseline validation'
"$checks inventory snapshot checks passed; generated fixtures only, no retail or Plan execution."
