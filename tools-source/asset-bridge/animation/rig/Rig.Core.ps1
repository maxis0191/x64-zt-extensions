# Local orchestration predicates. Import starts no process, lease or native type.
function New-RigOwnedJob([string]$Python,[string]$Arguments,[string]$Work) {
    [IW7.CommunityBuild.BuildJob]::Prepare($Python,$Arguments,$Work)
}
function Get-RigOriginalJobMembers($Owner) {[IW7.AnimationRig.JobMembers]::Capture($Owner)}
function Get-RigMonotonicMs {[Environment]::TickCount64}
function Get-RigJobSnapshot($Owner,[long]$StartedMs) {
    $exited=$Owner.Exited;$active=$Owner.Active
    [pscustomobject]@{Utc=[datetime]::UtcNow.ToString('o');ElapsedMs=((Get-RigMonotonicMs)-$StartedMs);
        RootExited=$exited;ActiveProcesses=$active;RootExitCode=$(if($exited){$Owner.ExitCode}else{$null})}
}
function Wait-RigOwnedPhase($Owner,$Identity,[long]$StartedMs,[int]$TimeoutSeconds,[scriptblock]$OnPoll) {
    if($TimeoutSeconds -notin 30,120,240){throw 'Known rig phase timeout required.'}
    $evidence=[ordered]@{PollCount=0;RootExitObservedMs=$null;DrainLimitMs=2000;LastSnapshot=$null;Outcome='Waiting'}
    $Identity.Supervision=$evidence
    try {
        while($true){
            $sample=Get-RigJobSnapshot $Owner $StartedMs;$evidence.PollCount++;$evidence.LastSnapshot=$sample
            if($sample.RootExited -and $null -eq $evidence.RootExitObservedMs){$evidence.RootExitObservedMs=$sample.ElapsedMs}
            & $OnPoll $sample | Out-Null
            $now=(Get-RigMonotonicMs)-$StartedMs
            if($now -ge ($TimeoutSeconds+5)*1000){throw 'Rig phase deadline expired.'}
            $drain=if($null -ne $evidence.RootExitObservedMs){$now-$evidence.RootExitObservedMs}else{0}
            if($sample.RootExited -and $drain -gt 2000){throw 'Rig owned job drain deadline expired.'}
            # After an accepted telemetry stop, use a NEW snapshot on the next
            # iteration. A callback's successful Stop is never an exit0/Active0.
            if($sample.RootExited -and $sample.ActiveProcesses -eq 0){
                $Identity.ExitCode=$sample.RootExitCode;$Identity.JobActiveAtClose=$sample.ActiveProcesses
                $Identity.JobRootExitedAtClose=$sample.RootExited;$evidence.Outcome='Closed';return
            }
            if($sample.RootExited -and $drain -ge 2000){throw 'Rig owned job drain deadline expired.'}
            Start-Sleep -Milliseconds 100
        }
    }catch{$evidence.Outcome='Failed';$evidence.Failure=$_.Exception.Message;throw}
}
function Stop-RigOwnedPhase($Owner,$Evidence) {
    $Evidence.Closed=$false;$Evidence.StopRequested=$true;$Evidence.Error=$null
    try {
        $started=Get-RigMonotonicMs;$Owner.Stop()
        while($true){
            $sample=Get-RigJobSnapshot $Owner $started;$Evidence.LastSnapshot=$sample
            if($sample.ElapsedMs -gt 15000){throw 'Rig original job stop deadline expired.'}
            if($sample.RootExited -and $sample.ActiveProcesses -eq 0){$Evidence.Closed=$true;return $true}
            if($sample.ElapsedMs -ge 15000){throw 'Rig original job stop deadline expired.'}
            Start-Sleep -Milliseconds 100
        }
    }catch{$Evidence.Error=$_.Exception.Message;return $false}
}
function Assert-RigPhaseResult($Result,[string]$Phase,[string]$Hash,[string]$SpecHash,$Identity) {
    if($Result.schema -cne 'iw7.rig-chain-phase-result/1' -or $Result.phase -cne $Phase -or $Result.failure -or
       $Result.executable_sha256 -ine $Hash -or $Result.spec_sha256 -ine $SpecHash -or
       $Result.log_limit_each -ne 2MB -or $Result.ownership -cne 'outer original Windows job' -or
       ($Result.exit_code -isnot [int] -and $Result.exit_code -isnot [long]) -or $Result.exit_code -ne 0 -or
       ($Identity.ExitCode -isnot [uint32] -and $Identity.ExitCode -isnot [int] -and $Identity.ExitCode -isnot [long]) -or
       ($Identity.JobActiveAtClose -isnot [uint32] -and $Identity.JobActiveAtClose -isnot [int] -and $Identity.JobActiveAtClose -isnot [long]) -or
       $Identity.JobRootExitedAtClose -isnot [bool] -or !$Identity.JobRootExitedAtClose -or
       $Identity.ExitCode -ne 0 -or $Identity.JobActiveAtClose -ne 0){throw 'Exact rig phase receipt and original exit0/Active0 required.'}
}
function Read-RigPhaseResult([string]$Logs,[string]$SpecPath,[string]$SpecHash,$Identity,[string]$Phase,$RootExitCode=$null) {
    $receipt=Join-Path $Logs 'phase.json'
    if(Test-Path -LiteralPath $receipt){return Read-BeaconJson $receipt}
    $exitCode=if($null -eq $RootExitCode){$Identity.ExitCode}else{$RootExitCode}
    $prefix="Rig phase $Phase exited $exitCode without phase.json."
    $errorPath=[IO.Path]::ChangeExtension($SpecPath,'launch-error.json')
    if(Test-Path -LiteralPath $errorPath){
        $failure=Read-BeaconJson $errorPath 65536
        if($failure.schema -cne 'iw7.rig-chain-launch-error/1' -or $failure.phase -cne $Phase -or
           $failure.spec_sha256 -ine $SpecHash -or
           ($failure.root_pid -isnot [int] -and $failure.root_pid -isnot [long]) -or $failure.root_pid -ne $Identity.PID -or
           $failure.error_type -isnot [string] -or !$failure.error_type -or $failure.error_type.Length -gt 128 -or
           $failure.error -isnot [string] -or !$failure.error -or $failure.error.Length -gt 8192){
            throw "$prefix Unbound launch-error receipt preserved at $errorPath"
        }
        throw "$prefix Bootstrap $($failure.error_type): $($failure.error)"
    }
    throw "$prefix No launch-error receipt is available; preserve original root and phase evidence."
}
function Set-RigSourceIdentity($Entry,[string]$Identity) {
    if(!$Identity){throw 'Fresh source identity required.'}
    if($Entry.PSObject.Properties['SourceId']){
        if($Entry.SourceId -cne $Identity){throw 'Bound source identity changed.'}
    }else{$Entry|Add-Member NoteProperty SourceId $Identity}
}
function Assert-RigCopyIdentity($Entry,[string]$Identity) {
    if($Entry.Relative -cne 'main/fileSysCheck.cfg' -or $Entry.Mode -cne 'Copy' -or $Entry.Bytes -ne 77 -or
       !$Entry.SourceId -or !$Identity -or $Identity -ceq $Entry.SourceId){throw 'Only independent 77-byte sentinel copy can change attributes.'}
}
function Get-RigInventory([string]$Log) {
    if($Log.Length -gt 2MB -or !$Log.Contains('Loading zone "sdk_original_rig_probe"') -or
       $Log -match 'could not be found|Could not find referenced|\[ ERROR \]|\[ FATAL \]'){throw 'Rig inventory absent or unresolved.'}
    $expected=@('material,,mopw/character_park_clown_zombie_shoes','xmodelsurfs,paris_doom_skin_two_bone_first_a_lod0',
        'xmodelsurfs,paris_doom_skin_two_bone_second_a_lod0','xmodel,paris_doom_skin_two_bone_first_a',
        'xmodel,paris_doom_skin_two_bone_second_a','xanim,paris_original_probe_bend','rawfile,sdk_original_rig_probe')
    $rows=@(foreach($line in $Log -split '\r?\n'|Where-Object {$_ -match 'Loading asset '}){
        if($line -cnotmatch 'Loading asset "([^"\r\n]+)" of type ([a-z0-9]+)\.$'){throw 'Malformed rig inventory row.'}
        $Matches[2]+','+$Matches[1]
    })
    if($rows.Count -ne 7 -or @($rows|Sort-Object -Unique).Count -ne 7 -or @($expected|Where-Object {$_ -cnotin $rows}).Count){throw 'Exact seven-asset rig inventory required.'}
    $rows
}
function Assert-RigReader($Result,[switch]$FF) {
    $status=if($FF){'rig-chain-data-pass'}else{'rig-native-data-pass'}
    if($Result.schema -cne 'iw7.original-rig-chain-data/1' -or $Result.status -cne $status){throw 'Complete independent rig reader pass required.'}
    foreach($key in 'native_execution_verified','ff_execution_verified','material_resolution_verified','engine_weight_direction_verified','runtime_verified','ready'){
        if($Result.$key -isnot [bool] -or $Result.$key){throw 'Data reader cannot assert execution/runtime acceptance.'}
    }
    $stages=@($Result.native);if($FF){$stages+=,$Result.redump}elseif($null -ne $Result.redump){throw 'Unexpected native-phase FF proof.'}
    foreach($stage in $stages){
        if(!$stage -or $stage.complete_model_surface_read -isnot [bool] -or !$stage.complete_model_surface_read -or
           $stage.clip_rig_cpu.status -cne 'four-key-rig-cpu-pass' -or @($stage.models.PSObject.Properties).Count -ne 2){throw 'Both complete rig profiles and clip oracle required.'}
        foreach($profile in 'first','second'){
            $model=$stage.models.$profile
            if($model.name -cne "paris_doom_skin_two_bone_${profile}_a" -or $model.model.bones -ne 2 -or
               $model.model.roots -ne 1 -or $model.model.client_bones -ne 0 -or !$model.model.complete_model_bytes_read -or
               $model.surface.vertices -ne 8 -or $model.surface.triangles -ne 6 -or $model.surface.blend_bytes -ne 48){throw 'Exact two-bone geometry required.'}
        }
    }
}
function Write-RigJson($Value,[string]$Path) {
    $text=$Value|ConvertTo-Json -Depth 35
    [IO.File]::WriteAllText($Path,$text+"`n",[Text.UTF8Encoding]::new($false))
}
function Write-RigNewText([string]$Text,[string]$Path) {
    $stream=[IO.File]::Open($Path,'CreateNew','Write','None')
    try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes($Text);$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
function Write-RigNewJson($Value,[string]$Path) {Write-RigNewText (($Value|ConvertTo-Json -Depth 35)+"`n") $Path}
function Assert-RigArtifact([string]$Path,[long]$Limit) {
    $null=Resolve-IW7BasePath (Split-Path $Path) (Split-Path $Path -Leaf)
    $file=Get-Item -LiteralPath $Path
    if($file.PSIsContainer -or $file.Length -lt 1 -or $file.Length -gt $Limit){throw 'Bounded nonempty rig artifact required.'}
}
function Assert-RigEmission($Result,[string]$Profile) {
    if($Profile -cnotin @('first','second') -or $Result.schema -cne 'iw7.doom-two-bone-writer-emission/1' -or
       $Result.hypothesis -cne $Profile -or $Result.vertices -ne 8 -or $Result.triangles -ne 6 -or $Result.bones -ne 2 -or
       $Result.rigid_lists -ne 0 -or $Result.blend_bytes -ne 48 -or $Result.native_files_emitted -isnot [bool] -or !$Result.native_files_emitted){throw 'Exact native emission receipt required.'}
    foreach($key in 'independent_read_verified','part_bits_engine_verified','iw7_shader_encoding_verified','weight_direction_engine_verified','draw_verified','pixels_verified','ready'){
        if($Result.$key -isnot [bool] -or $Result.$key){throw 'Writer cannot assert independent/engine validation.'}
    }
}
function Assert-RigNativeInventory($Plan) {
    $root=Join-Path $Plan.run_root 'native'
    $expected=@($Plan.staged_profile_inputs|Where-Object {$_.relative -cmatch '^(xmodel|xsurface)/'}|ForEach-Object {[IO.Path]::GetFullPath($_.source)})
    $actual=@(Get-ChildItem -LiteralPath $root -File -Recurse -Force)
    if($expected.Count -ne 4 -or $actual.Count -ne 4 -or @($actual|Where-Object {$_.FullName -cnotin $expected}).Count){throw 'Exact four native rig outputs required.'}
    foreach($item in $actual){Assert-RigArtifact $item.FullName 64KB}
}
function Assert-RigReaderBindings($Result,$Plan,[switch]$FF) {
    foreach($profile in 'first','second'){
        $name='paris_doom_skin_two_bone_'+$profile+'_a'
        foreach($pair in @(@('xmodel',($name+'.xmb'),'xmb'),@('xsurface',($name+'_lod0.xsb'),'xsb'))){
            $relative=$pair[0]+'/'+$pair[1]
            $input=@($Plan.staged_profile_inputs|Where-Object relative -CEQ $relative)
            if($input.Count -ne 1){throw 'Unique actual native binding required.'}
            $model=$Result.native.models.$profile
            Assert-BeaconHash $input[0].source $model.($pair[2]+'_sha256')
            if((Get-Item -LiteralPath $input[0].source).Length -ne $model.($pair[2]+'_bytes')){throw 'Native reader byte binding differs.'}
            if($FF){
                $path=Join-Path (Join-Path $Plan.run_root 'roundtrip') $relative
                $model=$Result.redump.models.$profile
                Assert-BeaconHash $path $model.($pair[2]+'_sha256')
                if((Get-Item -LiteralPath $path).Length -ne $model.($pair[2]+'_bytes')){throw 'FF reader byte binding differs.'}
            }
        }
    }
    $clip=@($Plan.staged_profile_inputs|Where-Object relative -CEQ 'xanim/paris_original_probe_bend.xab')
    if($clip.Count -ne 1){throw 'Unique actual clip required.'}
    Assert-BeaconHash $clip[0].source $Result.native.clip_rig_cpu.clip_sha256
    if($FF){Assert-BeaconHash (Join-Path $Plan.run_root 'roundtrip/xanim/paris_original_probe_bend.xab') $Result.redump.clip_rig_cpu.clip_sha256}
}
function Save-RigFinalCounters($State,[scriptblock]$Save,[scriptblock]$Measure) {
    for($i=0;$i -lt 4;$i++){
        & $Save;$previous=$State.FinalObservedBytes;$max=$State.MaxObservedBytes
        $bytes=& $Measure;$State.FinalObservedBytes=$bytes;$State.MaxObservedBytes=[math]::Max($State.MaxObservedBytes,$bytes)
        if($State.FinalObservedBytes -eq $previous -and $State.MaxObservedBytes -eq $max){return}
    }
    throw 'Final rig byte counters did not converge.'
}
function Get-RigToolchainInventory($Roots) {
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $items=[Collections.Generic.List[object]]::new();$total=0L
    foreach($root in $Roots){
        $null=Resolve-IW7BasePath (Split-Path $root) (Split-Path $root -Leaf)
        if(!(Test-Path -LiteralPath $root -PathType Container)){throw 'Existing toolchain root required.'}
        $queue=[Collections.Generic.Queue[string]]::new();$queue.Enqueue($root)
        while($queue.Count){
            foreach($entry in Get-ChildItem -LiteralPath $queue.Dequeue() -Force){
                if($entry.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){throw 'Toolchain reparse entry refused.'}
                if($entry.PSIsContainer){$queue.Enqueue($entry.FullName);continue}
                if($seen.Add($entry.FullName)){
                    $total+=$entry.Length
                    if($seen.Count -gt 30000 -or $total -gt 6GB){throw 'Toolchain inventory exceeds reviewed bound.'}
                    $items.Add([pscustomobject]@{Path=$entry.FullName;Bytes=$entry.Length;ModifiedUtc=$entry.LastWriteTimeUtc.ToString('o');Attributes=[int]$entry.Attributes})
                }
            }
        }
    }
    @($items|Sort-Object Path)
}
function Assert-RigToolchainInventory($Expected,$Roots) {
    $current=@(Get-RigToolchainInventory $Roots)
    if(($current|ConvertTo-Json -Depth 5 -Compress) -cne ($Expected|ConvertTo-Json -Depth 5 -Compress)){throw 'Toolchain inventory changed; source proof refused.'}
}
function Add-RigGuard([string]$Path,[string]$Expected,$Guards,$Baselines) {
    $null=Resolve-IW7BasePath (Split-Path $Path) (Split-Path $Path -Leaf)
    $stream=[IO.File]::Open($Path,'Open','Read','Read');$Guards.Add($stream)
    $file=Get-Item -LiteralPath $Path;$hash=(Get-FileHash -LiteralPath $Path).Hash
    if($Expected -and $hash -ine $Expected){throw 'Guarded source hash changed.'}
    $Baselines.Add([pscustomobject]@{Path=$file.FullName;SHA256=$hash;Bytes=$file.Length;ModifiedUtc=$file.LastWriteTimeUtc.ToString('o');
        Attributes=[int]$file.Attributes;SourceId=[IW7HudFileIdentity]::Read($file.FullName)})
}
function Assert-RigBaselines($Baselines,[switch]$Hashes) {
    foreach($item in $Baselines){
        $null=Resolve-IW7BasePath (Split-Path $item.Path) (Split-Path $item.Path -Leaf)
        $file=Get-Item -LiteralPath $item.Path
        if($file.Length -ne $item.Bytes -or $file.LastWriteTimeUtc.ToString('o') -cne $item.ModifiedUtc -or
           [int]$file.Attributes -ne $item.Attributes -or [IW7HudFileIdentity]::Read($item.Path) -cne $item.SourceId){throw 'Source metadata/identity changed.'}
        if($Hashes){Assert-BeaconHash $item.Path $item.SHA256}
    }
}
function Complete-RigGroup($State,[bool]$Closed,[bool]$SourceIntact,[bool]$Saved,$Guards,[scriptblock]$Restore,[scriptblock]$Release) {
    if(!$Closed -or !$SourceIntact){$State.CleanupError='Owned closure/source proof incomplete; guards and reservation retained.';return $false}
    foreach($guard in $Guards){$guard.Dispose()}
    if($Saved){& $Restore}else{& $Release}
    return $true
}
