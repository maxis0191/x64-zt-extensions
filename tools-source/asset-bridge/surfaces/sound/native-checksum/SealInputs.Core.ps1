# Read-only input sealing. Import loads no native type and reserves nothing.
function Get-ChecksumSealClock { [Environment]::TickCount64 }
function Assert-ChecksumSealDeadline($Context) {
    $Context.State.ElapsedMs=(Get-ChecksumSealClock)-$Context.Started
    if($Context.State.ElapsedMs -ge 120000){throw 'Input sealing observed deadline reached; blocking I/O is not preempted.'}
}
function Assert-ChecksumSealPath([string]$Path) {
    if(![IO.Path]::IsPathFullyQualified($Path)){throw 'Absolute seal input required.'}
    for($p=[IO.Path]::GetFullPath($Path);$p;$p=Split-Path $p -Parent){
        if((Test-Path -LiteralPath $p) -and (Get-Item -LiteralPath $p -Force).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){
            throw 'Redirected seal path refused.'
        }
    }
}
function Assert-ChecksumSealMetadata($Entry) {
    Assert-ChecksumSealPath $Entry.Path
    $file=Get-Item -LiteralPath $Entry.Path -Force
    if($file.PSIsContainer -or $file.Length -ne $Entry.Bytes -or [int]$file.Attributes -ne $Entry.Attributes -or
        $file.LastWriteTimeUtc.Ticks -ne $Entry.ModifiedUtcTicks){throw ('Seal input metadata changed: '+$Entry.Path)}
}
function Read-ChecksumSealChunk($Stream,[byte[]]$Buffer) { $Stream.Read($Buffer,0,$Buffer.Length) }
function Test-ChecksumSealPressure($Context) {
    $now=Get-ChecksumSealClock
    if($now-$Context.LastPoll -lt 1000){return}
    if(Test-Path -LiteralPath (Join-Path $Context.OutputRoot 'stop.request')){throw 'Read-only sealing stop requested.'}
    $memory=Get-IW7ResourceSnapshot
    $null=Test-IW7ResourceBudget $memory 0 0
    $Context.LastPoll=Get-ChecksumSealClock
    Assert-ChecksumSealDeadline $Context
}
function Get-ChecksumSealStreamHash($Stream,$Context) {
    $hash=[Security.Cryptography.IncrementalHash]::CreateHash([Security.Cryptography.HashAlgorithmName]::SHA256)
    try {
        $buffer=[byte[]]::new(262144)
        while($true){
            Assert-ChecksumSealDeadline $Context
            $read=Read-ChecksumSealChunk $Stream $buffer
            $Context.State.BytesRead+=$read;$Context.State.ReadCalls++
            Assert-ChecksumSealDeadline $Context # Includes time spent inside blocking Read.
            if(!$read){break}
            if($Context.State.BytesRead -gt $Context.State.ExpectedReadBytes){throw 'Declared input read budget exceeded.'}
            $hash.AppendData($buffer,0,$read)
            Test-ChecksumSealPressure $Context
        }
        [Convert]::ToHexString($hash.GetHashAndReset()).ToLowerInvariant()
    } finally {$hash.Dispose()}
}
function Measure-ChecksumSealOutput([string]$Root) {
    $bytes=0L
    foreach($file in Get-ChildItem -LiteralPath $Root -Recurse -Force){
        if($file.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){throw 'Redirected seal output refused.'}
        if(!$file.PSIsContainer){$bytes+=$file.Length}
    }
    if($bytes -gt 16MB){throw 'Input seal outputs exceeded 16 MiB; preserve evidence.'}
    $bytes
}
function Write-ChecksumSealJson([string]$Path,$Value) {
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 12)+"`n")
    if($bytes.Length -gt 15MB){throw 'Serialized seal file exceeds output budget.'}
    [IO.File]::WriteAllBytes($Path,$bytes)
}
function Assert-ChecksumSealInventory($Inventory) {
    if($Inventory.Schema -cne 'iw7.sound-checksum-input-inventory/1' -or @($Inventory.Inputs).Count -lt 1 -or
        @($Inventory.Inputs).Count -gt 4096 -or $Inventory.FileCount -ne @($Inventory.Inputs).Count){throw 'Bounded exact input inventory required.'}
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase);$bytes=0L
    foreach($entry in $Inventory.Inputs){
        if(![IO.Path]::IsPathFullyQualified($entry.Path) -or !$seen.Add([IO.Path]::GetFullPath($entry.Path)) -or
            ($entry.Bytes -isnot [long] -and $entry.Bytes -isnot [int]) -or $entry.Bytes -lt 0 -or $entry.Bytes -gt 512MB -or
            ($entry.ModifiedUtcTicks -isnot [long]) -or ($entry.Attributes -isnot [int] -and $entry.Attributes -isnot [long]) -or
            $entry.Attributes -lt 0 -or $entry.Attributes -gt [uint32]::MaxValue){throw 'Invalid or duplicate input metadata.'}
        if($entry.ExpectedSHA256 -and $entry.ExpectedSHA256 -cnotmatch '^[a-f0-9]{64}$'){throw 'Malformed existing input hash.'}
        $bytes+=$entry.Bytes
    }
    if($bytes -ne $Inventory.TotalBytes -or $bytes -gt 2GB){throw 'Exact bounded inventory byte sum required.'}
}
function Invoke-ChecksumInputSeal($Recipe,$Inventory,[string]$RecipeSHA256) {
    Assert-ChecksumSealInventory $Inventory
    Assert-ChecksumSealPath $Recipe.OutputRoot
    if(Test-Path -LiteralPath $Recipe.OutputRoot){throw 'Fresh seal output required; prior evidence is immutable.'}
    $state=[ordered]@{Schema='iw7.sound-checksum-input-seal-result/1';Status='Preparing';RecipeSHA256=$RecipeSHA256;
        InventorySHA256=$Recipe.InventorySHA256;FileCount=$Inventory.FileCount;TotalInputBytes=$Inventory.TotalBytes;
        ExpectedReadBytes=2L*$Inventory.TotalBytes;BytesRead=0L;ReadCalls=0L;ElapsedMs=0L;ObservedDeadlineMs=120000;
        BlockingIOPreempted=$false;PhysicalBytes=1GB;CommitBytes=2GB;ManifestSHA256=$null;
        GuardsOpened=0;GuardsDisposed=0;InputHashesVerifiedTwice=$false;ReadOnlyGuardsRetainedThroughProof=$false;
        LeaseReleased=$false;RetainedLeaseToken=$null;Failure=$null;OutputBytes=0L;
        NativeCommandsStarted=0;ProbeTypesLoaded=$false;Ready=$false}
    $c=[pscustomobject]@{State=$state;Started=(Get-ChecksumSealClock);LastPoll=(Get-ChecksumSealClock);OutputRoot=$Recipe.OutputRoot}
    $guards=[Collections.Generic.List[IDisposable]]::new();$sealed=[Collections.Generic.List[object]]::new();$lease=$null
    try {
        $lease=Enter-IW7ResourceLease -Scope $Recipe.OutputRoot -Kind Analysis -PhysicalBytes 1GB -CommitBytes 2GB -Owner 'Sound native input sealing only'
        $state.RetainedLeaseToken=$lease.Token
        Assert-ChecksumSealDeadline $c
        [IO.Directory]::CreateDirectory($Recipe.OutputRoot)|Out-Null
        # Each source denies write/delete sharing from its first read through the
        # second independent path read and completion of the whole input proof.
        foreach($entry in $Inventory.Inputs){
            Assert-ChecksumSealDeadline $c;Assert-ChecksumSealMetadata $entry
            $stream=[IO.File]::Open($entry.Path,'Open','Read','Read');$guards.Add($stream);$state.GuardsOpened++
            Assert-ChecksumSealMetadata $entry
            $digest=Get-ChecksumSealStreamHash $stream $c
            if($entry.ExpectedSHA256 -and $digest -cne $entry.ExpectedSHA256){throw ('Previously pinned input changed: '+$entry.Path)}
            $sealed.Add([ordered]@{Path=$entry.Path;Bytes=$entry.Bytes;Attributes=$entry.Attributes;
                ModifiedUtcTicks=$entry.ModifiedUtcTicks;Category=$entry.Category;SHA256=$digest})
        }
        foreach($entry in $sealed){
            Assert-ChecksumSealDeadline $c;Assert-ChecksumSealMetadata $entry
            $again=[IO.File]::Open($entry.Path,'Open','Read','Read');$guards.Add($again);$state.GuardsOpened++
            if((Get-ChecksumSealStreamHash $again $c) -cne $entry.SHA256){throw 'Second guarded path read differs.'}
            Assert-ChecksumSealMetadata $entry
        }
        Assert-ChecksumSealDeadline $c
        if($state.BytesRead -ne $state.ExpectedReadBytes){throw 'Exact two-pass read accounting differs.'}
        $state.InputHashesVerifiedTwice=$true;$state.ReadOnlyGuardsRetainedThroughProof=$true
        $manifest=[ordered]@{Schema='iw7.sound-checksum-sealed-inputs/1';RecipeSHA256=$RecipeSHA256;
            InventorySHA256=$Recipe.InventorySHA256;FileCount=$Inventory.FileCount;TotalBytes=$Inventory.TotalBytes;
            Inputs=@($sealed.ToArray());Ready=$false}
        $path=Join-Path $Recipe.OutputRoot 'sealed-inputs.local.json'
        Write-ChecksumSealJson $path $manifest
        $state.ManifestSHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()
        $state.OutputBytes=Measure-ChecksumSealOutput $Recipe.OutputRoot
        Assert-ChecksumSealDeadline $c
        $state.Status='Sealed'
    } catch {$state.Status='Failed';$state.Failure=$_.Exception.Message}
    finally {
        foreach($guard in $guards){try{$guard.Dispose();$state.GuardsDisposed++}catch{$state.Status='Failed';$state.Failure=$_.Exception.Message}}
        if($lease -and $state.GuardsOpened -eq $state.GuardsDisposed){
            try{Exit-IW7ResourceLease -Token $lease.Token;$state.LeaseReleased=$true;$state.RetainedLeaseToken=$null}
            catch{$state.Status='Failed';$state.Failure=$_.Exception.Message}
        }
        $state.ElapsedMs=(Get-ChecksumSealClock)-$c.Started
        if($state.ElapsedMs -ge 120000){$state.Status='Failed';$state.Failure='Observed sealing deadline exceeded, including final lifecycle.'}
        if(Test-Path -LiteralPath $Recipe.OutputRoot){
            $statePath=Join-Path $Recipe.OutputRoot 'state.local.json'
            for($pass=0;$pass -lt 4;$pass++){
                Write-ChecksumSealJson $statePath $state
                $bytes=Measure-ChecksumSealOutput $Recipe.OutputRoot
                $decisionMs=(Get-ChecksumSealClock)-$c.Started
                if($decisionMs -ge 120000 -and $state.Failure -cne 'Observed sealing deadline exceeded, including final lifecycle.'){
                    $state.Status='Failed';$state.Failure='Observed sealing deadline exceeded, including final lifecycle.'
                    $state.ElapsedMs=$decisionMs;$state.OutputBytes=$bytes;continue
                }
                if($bytes -eq $state.OutputBytes){break}
                $state.OutputBytes=$bytes
            }
            if($pass -eq 4){throw 'Seal receipt accounting failed to converge.'}
        }
    }
    if($state.Status -cne 'Sealed' -or !$state.LeaseReleased){throw ('Input sealing failed; preserve evidence. '+$state.Failure)}
    $state
}
