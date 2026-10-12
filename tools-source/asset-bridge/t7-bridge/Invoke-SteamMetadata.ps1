# Fixed AppInfo, manifest or one-file acquisition; existing NativeJob/scheduler.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Plan,
      [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$PlanSHA256,
      [switch]$Run)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Read-SteamSnapshot([string]$Path,[ValidateRange(1,67108864)][int]$Limit,$Guards,[switch]$Allow64MiB) {
    if($Limit -gt 32MB -and !$Allow64MiB){throw 'Snapshot above 32 MiB requires explicit 64 MiB opt-in.'}
    Assert-H1Path $Path
    $stream=[IO.FileStream]::new($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $retained=$false
    try {
        $initial=$stream.Length
        if($initial -gt $Limit){throw 'Snapshot input exceeds byte bound.'}
        $buffer=[byte[]]::new($Limit+1);$used=0
        do {
            $read=$stream.Read($buffer,$used,$buffer.Length-$used);$used+=$read
        }while($read -gt 0 -and $used -lt $buffer.Length)
        if($used -gt $Limit -or $used -ne $initial -or $stream.Length -ne $initial){throw 'Snapshot grew or changed length during bounded read.'}
        $bytes=[byte[]]::new($used);[Array]::Copy($buffer,$bytes,$used)
        $digest=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
        Assert-H1Path $Path
        $Guards.Add($stream);$retained=$true
        # Caller parses and hashes this same immutable byte array. The original
        # FileShare.Read guard stays in Context.Guards through measure/receipt.
        [pscustomobject]@{Bytes=$bytes;Length=$used;SHA256=$digest}
    }finally{if(!$retained){$stream.Dispose()}}
}
function Assert-SteamExecutableFileList([string]$Path,$Guards) {
    $snapshot=Read-SteamSnapshot $Path 4096 $Guards
    $text=[Text.UTF8Encoding]::new($false,$true).GetString($snapshot.Bytes)
    if($text -cne "UnrankedServer/BlackOps3_UnrankedDedicatedServer.exe`n"){
        throw 'Only the exact one-file literal list is permitted; no regex or fallback.'
    }
    $snapshot
}

function Measure-SteamAttempt($Settings,[double]$Started,[int]$Seconds=200) {
    $manifestMode=$Settings.PSObject.Properties['operation'] -and $Settings.operation -ceq 'depot-file-manifest'
    $executableMode=$Settings.PSObject.Properties['operation'] -and $Settings.operation -ceq 'bo3-dedicated-executable'
    $totals=@(0L,0L);$roots=@($Settings.tool_root,$Settings.outer_evidence_root)
    for($index=0;$index -lt 2;$index++) {
        Assert-H1Path $roots[$index]
        $pending=[Collections.Generic.Stack[string]]::new();$pending.Push($roots[$index]);$count=0
        while($pending.Count) {
            $directory=$pending.Pop();Assert-H1Deadline $Started $Seconds
            try {
                $attrs=[IO.File]::GetAttributes($directory)
                if($attrs -band [IO.FileAttributes]::ReparsePoint){throw 'Output reparse directory refused.'}
                foreach($entry in [IO.Directory]::EnumerateFileSystemEntries($directory)) {
                    Assert-H1Deadline $Started $Seconds
                    if(++$count -gt $(if($index -eq 0){20000}elseif($manifestMode -or $executableMode){1024}else{64})){throw 'Output entry cap exceeded.'}
                    try {
                        $attrs=[IO.File]::GetAttributes($entry)
                        if($attrs -band [IO.FileAttributes]::ReparsePoint){throw 'Output reparse entry refused.'}
                        if($attrs -band [IO.FileAttributes]::Directory){$pending.Push($entry)}
                        else {$totals[$index]+=([IO.FileInfo]$entry).Length}
                    }catch [IO.FileNotFoundException] {continue} # Steam updater rename race.
                    if($totals[$index] -gt $(if($index -eq 0){512MB-128KB}elseif($executableMode){64MB-64KB}elseif($manifestMode){32MB-64KB}else{512KB-64KB})){
                        throw 'Private output byte cap exceeded.'
                    }
                }
            }catch [IO.DirectoryNotFoundException] {
                if($directory -eq $roots[$index]){throw} # Root must never disappear.
            }
        }
    }
    foreach($name in 'stdout.log','stderr.log') {
        $file=Join-Path $Settings.outer_evidence_root $name
        if((Test-Path -LiteralPath $file) -and ([IO.FileInfo]$file).Length -gt 64KB){throw 'Outer log cap exceeded.'}
        $file=Join-Path $Settings.tool_root ('metadata-attempt-a/'+$name)
        if((Test-Path -LiteralPath $file) -and ([IO.FileInfo]$file).Length -gt 2MB){throw 'Phase log cap exceeded.'}
    }
    if($totals[0]+$totals[1] -gt 512MB-64KB){throw 'Aggregate output cap exceeded.'}
    [pscustomobject]@{ToolBytes=$totals[0];OuterBytes=$totals[1];TotalBytes=$totals[0]+$totals[1]}
}
function Assert-SteamOriginal($Snapshot,$Identity) {
    if($Identity -and ($Snapshot.PID -ne $Identity.PID -or $Snapshot.Image -ine $Identity.Image -or
        $Snapshot.CreatedUtc -cne $Identity.CreatedUtc)){throw 'Original root identity changed.'}
    if($Snapshot.RootExited -isnot [bool] -or $Snapshot.ActiveProcesses -lt 0){throw 'Invalid original job observation.'}
}
function Wait-SteamOriginal($Settings,$State,$Context,[double]$Started) {
    while($true) {
        $State.Output=Measure-SteamAttempt $Settings $Started
        $memory=Get-IW7ResourceSnapshot
        if($memory.CommitLimit -le 0 -or $memory.Committed -lt 0 -or $memory.Committed -gt $memory.CommitLimit*0.85){throw 'Commit high water or invalid telemetry.'}
        Assert-H1Deadline $Started 200
        $sample=Get-H1OriginalState $Context.Owner
        Assert-SteamOriginal $sample $State.Identity
        $State.LastOriginalSnapshot=$sample
        Assert-H1Deadline $Started 200
        if(Test-Path -LiteralPath (Join-Path $Settings.outer_evidence_root 'stop.request')){throw 'Coordinator stop requested.'}
        if($sample.RootExited -and $sample.ActiveProcesses -eq 0) {
            if($sample.RootExitCode -ne 0){throw 'Original Python root failed.'}
            $Context.Owner.CloseConfirmed();$Context.Closed=$Context.Owner.Closed
            $State.TreeClosureConfirmed=$Context.Closed
            Assert-H1Deadline $Started 200
            if(!$Context.Closed){throw 'Original job closure not confirmed.'}
            return
        }
        # A failed root or phase does not retain updater children until timeout.
        if($sample.RootExited -and $sample.RootExitCode -ne 0){throw 'Failed root left original children.'}
        Start-Sleep -Milliseconds 250
        Assert-H1Deadline $Started 200
    }
}
function Close-SteamAttempt($State,$Context) {
    if(!$Context.Closed) {
        try {
            if(!$Context.Owner){throw 'Missing original owner after creation attempt.'}
            # A pre-CreateProcess failure has no process handle. The provider's
            # createPending/TreeExited check is authoritative for this one case.
            if($Context.Owner.PID -eq 0 -and $Context.Owner.TreeExited()) {
                $State.NoProcessCreated=$true
            }else{
                $State.ForcedStop=$true;$cleanup=Get-H1Clock
                Stop-H1OriginalJob $Context.Owner
                do {
                    $sample=Get-H1OriginalState $Context.Owner
                    Assert-SteamOriginal $sample $State.Identity
                    Assert-H1Deadline $cleanup 5
                    $State.AfterStopOriginalSnapshot=$sample
                    if($sample.RootExited -and $sample.ActiveProcesses -eq 0){break}
                    Start-Sleep -Milliseconds 20
                }while($true)
            }
            $Context.Owner.CloseConfirmed();$Context.Closed=$Context.Owner.Closed
            if(!$Context.Closed){throw 'Original tree still open.'}
            if($State.ForcedStop){Assert-H1Deadline $cleanup 5}
        }catch{$State.CleanupError=$_.Exception.Message}
    }
    $State.TreeClosureConfirmed=$Context.Closed
    if($Context.Closed -and $Context.Lease) {
        try {Exit-IW7ResourceLease -Token $Context.Lease.Token;$Context.Lease=$null;$State.LeaseReleased=$true}
        catch {$State.CleanupError=$_.Exception.Message}
    }
    if(!$Context.Closed -or $Context.Lease) {$State.Status='Quarantined';$State.Quarantined=$true}
}

$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$core=Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1'
$compilerCore=Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1'
$scheduler=Join-Path $repo 'ops/Resource-Scheduler.Core.ps1'
$phase=Join-Path $PSScriptRoot 'steamcmd_metadata_phase.py'
$guards=[Collections.Generic.List[IO.FileStream]]::new()
$context=[pscustomobject]@{Owner=$null;Lease=$null;Closed=$true;Guards=$guards}
$state=$null;$failure=$null;$outputCreated=$false;$settings=$null
try {
    if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell 7 required.'}
    # Bootstrap trust before importing helpers: retain the exact reviewed plan,
    # then every source/provider/interpreter binding, with no write/delete share.
    $planGuard=[IO.FileStream]::new($Plan,'Open','Read','Read');$guards.Add($planGuard)
    if($planGuard.Length -gt 128KB -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($planGuard)).ToLowerInvariant() -cne $PlanSHA256){throw 'Plan hash/size differs.'}
    $planGuard.Position=0
    $reader=[IO.StreamReader]::new($planGuard,[Text.Encoding]::UTF8,$true,4096,$true)
    try {$settings=$reader.ReadToEnd()|ConvertFrom-Json -Depth 20}finally{$reader.Dispose()}
    $manifestMode=$settings.PSObject.Properties['operation'] -and $settings.operation -ceq 'depot-file-manifest'
    $executableMode=$settings.PSObject.Properties['operation'] -and $settings.operation -ceq 'bo3-dedicated-executable'
    $depotMode=$manifestMode -or $executableMode
    $attempt=if($executableMode){'executable-a'}elseif($manifestMode){'manifest-a'}else{'metadata-a'}
    if($settings.PSObject.Properties['operation'] -and $settings.operation -cnotin @('steamcmd-appinfo','depot-file-manifest','bo3-dedicated-executable')){throw 'Unknown fixed operation.'}
    if($settings.schema -cne 'iw7.steamcmd-metadata-outer-plan/1' -or $settings.attempt -cne $attempt -or
       $settings.retry_authorized -ne $false){throw 'Only the reviewed fixed attempt is supported.'}
    $pins=@{}
    foreach($pin in $settings.bindings_retained_read_only) {
        $largeDepotPin=$depotMode -and $pin.path -ceq $settings.root_executable -and $pin.bytes -eq 78840739 -and
            $pin.sha256 -ceq '6281279efce8f1e20db9532a58e42382f81afb9e3827a8b965ffcb43fbe4531f'
        if($pins.ContainsKey($pin.path) -or $pin.bytes -lt 0 -or ($pin.bytes -gt 64MB -and !$largeDepotPin) -or $pin.sha256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Invalid or duplicate binding.'}
        $guard=[IO.FileStream]::new($pin.path,'Open','Read','Read');$guards.Add($guard)
        if($guard.Length -ne $pin.bytes -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($guard)).ToLowerInvariant() -cne $pin.sha256){throw 'Source/provider binding differs.'}
        $pins[$pin.path]=$pin
    }
    $required=@($PSCommandPath,$core,$compilerCore,$scheduler,$settings.root_executable,(Join-Path $repo 'ops/Resource-Memory.ps1'),
        (Join-Path $repo 'ops/Resource-RecorderOwnedProcess.Core.ps1'),(Join-Path $repo 'ops/native/ResourceMemory.cs'))
    if(!$depotMode){$required+=@($phase,(Join-Path $repo 'sdk/modding/beacon_tool_phase.py'))}
    else {$required+=(Join-Path $settings.tool_root 'prepare-receipt.json')}
    $fileList=Join-Path $repo 'runtime/bo3-executable-filelist-a.local.txt'
    $sourceManifest=Join-Path $repo 'runtime/depot-manifest-a/manifest/manifest_545991_2350066205567669287.txt'
    if($executableMode){$required+=@($fileList,$sourceManifest)}
    foreach($path in $required){if(!$pins.ContainsKey($path)){throw ('Missing required binding: '+$path)}}
    . $core
    Assert-H1Path $Plan
    foreach($pin in $pins.Values){Assert-H1Path $pin.path}
    $jobPin=@($pins.Values|Where-Object { [IO.Path]::GetFileName($_.path) -ceq 'Probe-NativeJob.dll' })
    if($jobPin.Count -ne 1 -or $jobPin[0].sha256 -cne '5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8'){throw 'Existing witnessed NativeJob DLL required.'}
    $shell=[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    if(!$pins.ContainsKey($shell)){throw 'Current PowerShell host is not pinned.'}
    foreach($name in $(if($depotMode){@()}else{@('python312.dll','python3.dll')})) {
        if(!$pins.ContainsKey((Join-Path (Split-Path $settings.root_executable -Parent) $name))){throw 'Python runtime DLL binding missing.'}
    }
    Assert-H1Path $settings.tool_root;Assert-H1Path $settings.outer_evidence_root
    foreach($pin in $pins.Values) {
        if(!$depotMode -and $pin.path.StartsWith($settings.tool_root.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)){
            throw 'An updater file must not remain guarded as a source binding.'
        }
    }
    $outerName=if($executableMode){'depot-executable-a'}elseif($manifestMode){'depot-manifest-a'}else{'steamcmd-metadata-outer-a'}
    if($settings.outer_evidence_root -ine (Join-Path $repo ('runtime/'+$outerName)) -or
       (Test-Path -LiteralPath $settings.outer_evidence_root)){throw 'Fresh fixed outer evidence root required.'}
    $expectedCwd=if($depotMode){$settings.outer_evidence_root}else{$settings.tool_root}
    if($depotMode) {
        $expectedArgs=@('-app','545990','-depot','545991','-manifest','2350066205567669287')
        $expectedArgs+=if($executableMode){@('-filelist',$fileList)}else{@('-manifest-only')}
        $expectedArgs+=@('-loginid','20261012','-max-downloads','1','-dir',
            (Join-Path $settings.outer_evidence_root $(if($executableMode){'payload'}else{'manifest'})))
    }else{$expectedArgs=@('-B','-I',$phase,'--tool-root',$settings.tool_root)}
    if($settings.working_directory -ine $expectedCwd -or ($settings.root_arguments -join "`0") -cne ($expectedArgs -join "`0")){throw 'Fixed metadata command differs.'}
    if($settings.admission.kind -cne 'Analysis' -or $settings.admission.scope -ine $settings.tool_root -or
       $settings.admission.physical_bytes -ne 2GB -or $settings.admission.commit_bytes -ne 3GB -or
       $settings.limits.outer_acceptance_seconds -ne 200 -or $settings.limits.cleanup_seconds -ne 5){throw 'Reviewed fixed budget/deadlines required.'}
    if($depotMode) {
        if($settings.root_executable -ine (Join-Path $settings.tool_root 'bin/DepotDownloader.exe') -or
           $pins[$settings.root_executable].sha256 -cne '6281279efce8f1e20db9532a58e42382f81afb9e3827a8b965ffcb43fbe4531f'){throw 'Exact prepared portable executable required.'}
        $prepared=Read-H1SmallJson (Join-Path $settings.tool_root 'prepare-receipt.json')
        if($prepared.archive_sha256 -cne '41c9e9f0df54b3ad02e67a11726756e5c73283bd7c2e1b04acfa5ae4c2ed3767' -or
           $prepared.source_commit -cne 'c553ef4d60c00a4f5fd16c9fe017f569001589ff' -or $prepared.archive_bytes -ne 33474005){throw 'Prepared release provenance differs.'}
        if($executableMode) {
            $listSnapshot=Assert-SteamExecutableFileList $fileList $context.Guards
            $sourceSnapshot=Read-SteamSnapshot $sourceManifest 16MB $context.Guards
            if($sourceSnapshot.SHA256 -cne '4423aa96951c341b32e34e65787b6ef7fda29733c8a11f4f254a6d1531b35eb8'){
                throw 'Selection must be bound to the actual retrieved manifest.'
            }
        }
    }else{
        if((@(Get-ChildItem -LiteralPath $settings.tool_root -Force|Sort-Object Name|ForEach-Object Name) -join '|') -cne 'steamcmd.exe|steamcmd.zip'){throw 'Fresh two-file bootstrap root required.'}
        $bootstrap=@($settings.bootstrap_check_before_start_only)
        if($bootstrap.Count -ne 2){throw 'Both bootstrap pins required.'}
        foreach($name in 'steamcmd.exe','steamcmd.zip') {
            $pin=@($bootstrap|Where-Object path -CEQ (Join-Path $settings.tool_root $name))
            if($pin.Count -ne 1){throw 'Exact bootstrap path missing.'}
            $guard=Open-H1Pin $pin[0];$guard.Dispose() # Allow self-update replacement.
        }
    }
    if(!$Run) {
        [ordered]@{Status='PlanVerified';Attempt=$attempt;PlanSHA256=$PlanSHA256;Bindings=$pins.Count;NativeLoaded=$false;LeaseAcquired=$false;ToolStarted=$false}|ConvertTo-Json
        return
    }
    if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Fresh native host required.'}
    $null=[Reflection.Assembly]::LoadFrom($jobPin[0].path)
    . $compilerCore
    . $scheduler
    $state=[ordered]@{Schema='iw7.steam-tool-metadata-outer/1';Attempt=$attempt;Status='Running';PlanSHA256=$PlanSHA256;
        Identity=$null;StartedUtc=[datetime]::UtcNow.ToString('o');PhysicalBytes=2GB;CommitBytes=3GB;
        DeadlineSeconds=200;ForcedStop=$false;TreeClosureConfirmed=$true;LeaseReleased=$false;Quarantined=$false;
        ApplicationIdentityConfirmed=$false;NativeT7Started=$false;EstimatesAreMeasured=$false;LimitsAreOSQuotas=$false}
    $context.Lease=Enter-IW7ResourceLease -Scope $settings.tool_root -Kind Analysis -PhysicalBytes 2GB -CommitBytes 3GB -Owner ('Steam metadata '+$attempt+' only')
    $state.LeaseToken=$context.Lease.Token;$started=Get-H1Clock
    if(Test-Path -LiteralPath $settings.outer_evidence_root){throw 'Outer output appeared during admission.'}
    $null=[IO.Directory]::CreateDirectory($settings.outer_evidence_root);$outputCreated=$true
    $temp=Join-Path $settings.outer_evidence_root 'temp';$null=[IO.Directory]::CreateDirectory($temp)
    $start=[Diagnostics.ProcessStartInfo]::new($settings.root_executable)
    $start.WorkingDirectory=$settings.working_directory;$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle='Hidden'
    $start.Environment['TEMP']=$temp;$start.Environment['TMP']=$temp
    if($depotMode){$start.Environment['DOTNET_BUNDLE_EXTRACT_BASE_DIR']=Join-Path $temp 'dotnet-bundle'}
    foreach($arg in $settings.root_arguments){$start.ArgumentList.Add([string]$arg)}
    Assert-H1Deadline $started 200
    $context.Owner=New-H1Owner;$context.Closed=$false;$state.TreeClosureConfirmed=$false
    $context.Owner.Start($start,$pins[$settings.root_executable].sha256,
        (Join-Path $settings.outer_evidence_root 'stdout.log'),(Join-Path $settings.outer_evidence_root 'stderr.log'))
    $state.Identity=[ordered]@{PID=$context.Owner.PID;Image=$context.Owner.Image;CreatedUtc=[datetime]::FromFileTimeUtc($context.Owner.CreationFileTime).ToString('o')}
    Assert-H1Deadline $started 200
    try {Register-H1Original $context.Lease $state.Identity;$state.Registration='Registered'}
    catch {
        $state.RegistrationError=$_.Exception.Message;$sample=Get-H1OriginalState $context.Owner
        Assert-SteamOriginal $sample $state.Identity
        if(!$sample.RootExited -or $sample.ActiveProcesses -ne 0){throw}
        $state.Registration='Original tree already empty before registry observation'
    }
    Wait-SteamOriginal $settings $state $context $started
    if($executableMode) {
        $state.Output=Measure-SteamAttempt $settings $started
        $payload=Join-Path $settings.outer_evidence_root 'payload'
        $executable=Join-Path $payload 'UnrankedServer/BlackOps3_UnrankedDedicatedServer.exe'
        $files=@(Get-ChildItem -LiteralPath $payload -Recurse -File|Where-Object {
            !$_.FullName.StartsWith((Join-Path $payload '.DepotDownloader')+'\',[StringComparison]::OrdinalIgnoreCase)})
        if($files.Count -ne 1 -or $files[0].FullName -ine $executable){throw 'Unexpected payload outside the one-file allowlist.'}
        $exeSnapshot=Read-SteamSnapshot $executable 21737352 $context.Guards
        $sha1=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData($exeSnapshot.Bytes)).ToLowerInvariant()
        if($exeSnapshot.Length -ne 21737352 -or $sha1 -cne '9d5fdd6f44defb8d65f8f5256e4eb83d4547f408'){
            throw 'Executable differs from exact manifest length/SHA1.'
        }
        $consoleSnapshot=Read-SteamSnapshot (Join-Path $settings.outer_evidence_root 'stdout.log') 64KB $context.Guards
        $console=[Text.UTF8Encoding]::new($false,$true).GetString($consoleSnapshot.Bytes)
        $transfer=[regex]::Match($console,'Total downloaded: (\d+) bytes \(21737352 bytes uncompressed\) from 1 depots')
        if(!$console.Contains("Using filelist: '$fileList'.") -or $console.Contains('Warning: Unable to load filelist:') -or
           !$transfer.Success){
            throw 'Successful exact filelist acquisition not confirmed.'
        }
        $compressed=[long]$transfer.Groups[1].Value
        if($compressed -le 0 -or $compressed -gt 32MB){throw 'Selected transfer counter exceeds 32 MiB.'}
        $state.Executable=[ordered]@{RelativePath='UnrankedServer/BlackOps3_UnrankedDedicatedServer.exe';Bytes=$exeSnapshot.Length;
            SHA1=$sha1;SHA256=$exeSnapshot.SHA256;ManifestChunks=21;CompressedBytes=$compressed;
            FileListSHA256=$listSnapshot.SHA256;ManifestSHA256=$sourceSnapshot.SHA256;
            StdoutSHA256=$consoleSnapshot.SHA256;SnapshotsRetainedThroughReceipt=$true;PEInspected=$false;Executed=$false}
    }elseif($manifestMode) {
        $manifest=Join-Path $settings.outer_evidence_root 'manifest/manifest_545991_2350066205567669287.txt'
        $manifestSnapshot=Read-SteamSnapshot $manifest 16MB $context.Guards
        $text=[Text.UTF8Encoding]::new($false,$true).GetString($manifestSnapshot.Bytes)
        if($text -cnotmatch '(?m)^Content Manifest for Depot 545991\s*$' -or
           $text -cnotmatch '(?m)^Manifest ID / date\s*: 2350066205567669287 / '){throw 'Manifest depot/ID differs.'}
        $consoleSnapshot=Read-SteamSnapshot (Join-Path $settings.outer_evidence_root 'stdout.log') 64KB $context.Guards
        $console=[Text.UTF8Encoding]::new($false,$true).GetString($consoleSnapshot.Bytes)
        if(!$console.Contains('Total downloaded: 0 bytes (0 bytes uncompressed) from 1 depots')){throw 'Zero content-chunk counter not confirmed.'}
        $state.Manifest=[ordered]@{Depot=545991;ManifestID='2350066205567669287';Bytes=$manifestSnapshot.Length;
            SHA256=$manifestSnapshot.SHA256;ContentChunkBytes=0;FileSelectionReviewed=$false;
            StdoutBytes=$consoleSnapshot.Length;StdoutSHA256=$consoleSnapshot.SHA256;SnapshotsRetainedThroughReceipt=$true}
        $state.Output=Measure-SteamAttempt $settings $started
    }else{
    $result=Read-H1SmallJson (Join-Path $settings.tool_root 'metadata-attempt-a/phase.json') 64KB
    if($result.schema -cne 'iw7.steamcmd-metadata-phase/1' -or $null -ne $result.failure -or
       $result.steamcmd_exit_code -ne 0 -or $result.elapsed_seconds -lt 0 -or $result.elapsed_seconds -ge 180 -or
       ($result.command -join "`0") -cne ($settings.fixed_child_arguments -join "`0") -or
       $result.app_or_depot_download_requested -ne $false -or $result.personal_login_requested -ne $false){throw 'Metadata phase did not complete within its contract.'}
    $state.Phase=$result;$state.Output=Measure-SteamAttempt $settings $started
    $updated=Join-Path $settings.tool_root 'steamcmd.exe';Assert-H1Path $updated
    $item=Get-Item -LiteralPath $updated
    if($item.Length -le 0 -or $item.Length -gt 64MB){throw 'Updated executable size outside metadata binding limit.'}
    $signature=Get-AuthenticodeSignature -LiteralPath $updated
    $state.UpdatedSteamCmd=[ordered]@{Bytes=$item.Length;SHA256=(Get-FileHash -LiteralPath $updated).Hash.ToLowerInvariant();
        Version=$item.VersionInfo.FileVersion;SignatureStatus=[string]$signature.Status}
    }
    Assert-H1Deadline $started 200
    $state.ElapsedMilliseconds=(Get-H1Clock)-$started
    $state.Status=if($executableMode){'ExecutableRetrievedPendingPEInspection'}elseif($manifestMode){'ManifestRetrievedPendingFileSelection'}else{'MetadataProcessPassedPendingAppInfoReview'}
}catch{
    $failure=$_
    if($state){$state.Status='Failed';$state.Error=$_.Exception.Message}
}finally{
    if($state){Close-SteamAttempt $state $context}
    if($state -and $outputCreated) {
        $state.FinishedUtc=[datetime]::UtcNow.ToString('o')
        try {
            $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($state|ConvertTo-Json -Depth 16)+"`n")
            if($bytes.Length -gt 64KB){throw 'Receipt exceeds its reserved 64 KiB.'}
            $pending=Join-Path $settings.outer_evidence_root 'receipt.pending.json'
            $stream=[IO.FileStream]::new($pending,'CreateNew','Write','Read')
            try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
            [IO.File]::Move($pending,(Join-Path $settings.outer_evidence_root 'receipt.json'))
        }catch{if(!$failure){$failure=$_};Write-Warning ('Receipt publication failed: '+$_.Exception.Message)}
    }
    if($context.Closed -and !$context.Lease){foreach($guard in $guards){$guard.Dispose()};$guards.Clear()}
}
if($state -and $state.Quarantined) {
    [AppDomain]::CurrentDomain.SetData('IW7.SteamMetadata.Quarantine',$context)
    Write-Warning 'Original owner/lease retained. This host stays alive for coordinator recovery; no retry.'
    while($true){Start-Sleep -Seconds 1}
}
if($failure){throw $failure}
[ordered]@{Status=$state.Status;Receipt=(Join-Path $settings.outer_evidence_root 'receipt.json');
    TreeClosureConfirmed=$state.TreeClosureConfirmed;LeaseReleased=$state.LeaseReleased;ApplicationIdentityConfirmed=$false}|ConvertTo-Json
