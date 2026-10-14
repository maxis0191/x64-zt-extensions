# Fixed catalogue adapter. Ownership, pin readers and closure stay in H1Native.Core.
function Get-T7CatalogueZoneSpec($Name='mp_freerun_04') {
    if($Name -isnot [string] -or $Name -cnotin @('mp_freerun_04','zm_common')){throw 'Only exact allowlisted catalogue zones are allowed.'}
    $bytes=if($Name -ceq 'mp_freerun_04'){16977344L}else{36332480L}
    $fileName=$Name+'.ff'
    $sha=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::ASCII.GetBytes($Name))).ToLowerInvariant()
    [pscustomobject]@{Name=$Name;FileName=$fileName;Bytes=$bytes;RelativePath=('zone/'+$fileName);
        OutputKey=('t7_iw7_catalog_'+$sha);FixedBytes=($bytes+21737352L+235600L+64MB)}
}
function Get-T7CataloguePlanZoneSpec($Plan) {
    # Small historical synthetic callers omit Zone; operational plans require it.
    $spec=if($Plan.PSObject.Properties['Zone']){
        $name=[IO.Path]::GetFileName($Plan.Zone.Path)
        $selected=Get-T7CatalogueZoneSpec ([IO.Path]::GetFileNameWithoutExtension($name))
        if($name -cne $selected.FileName){throw 'Exact catalogue zone filename required.'}
        $selected
    }else{Get-T7CatalogueZoneSpec}
    if((Get-T7CatalogueOperation $Plan) -ceq 'ResidentExportV1' -and $spec.Name -cne 'mp_freerun_04'){
        throw 'Resident export retains only the observed platform donor zone.'
    }
    $spec
}
function Get-T7CatalogueCandidateProfile($Plan) {
    if(!$Plan.PSObject.Properties['CandidateProfile']){return 'ordinary-d2'}
    if($Plan.CandidateProfile -cnotin @('ordinary-d2','t7-catalog-trace','t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c')){throw 'Unknown catalogue candidate profile.'}
    $Plan.CandidateProfile
}
function Assert-T7CatalogueZombiesObservationPlan($Plan) {
    $selected=(Get-T7CatalogueCandidateProfile $Plan) -ceq 't7-zombies-catalogue-observation-c'
    $present=[bool]$Plan.PSObject.Properties['ZombiesObservationC']
    if(!$selected -and !$present){return}
    if(!$selected -or !$present){throw 'Catalogue C profile and observation plan must be selected together.'}
    Assert-T7CatalogueFields $Plan.ZombiesObservationC @('Schema')
    if($Plan.ZombiesObservationC.Schema -cne 'iw7.t7-zm-observation-plan/1' -or
       (Get-T7CatalogueOperation $Plan) -cne 'Catalogue' -or !$Plan.PSObject.Properties['Zone'] -or
       (Get-T7CataloguePlanZoneSpec $Plan).Name -cne 'zm_common' -or
       !(Test-T7CatalogueInteger $Plan.TraceStderrLimitBytes 16384) -or $Plan.TraceStderrLimitBytes -ne 16384){
        throw 'Catalogue C requires its exact schema, Zombies zone and 16 KiB trace bound.'
    }
    foreach($name in 'ResidentSurfaceCountDiagnostic','ResidentMultiSurfaceV2','SelectedMeshMaterialObservation','SelectedStreamedStaticV1','SelectedStreamedRenderOnlyV2'){
        if($Plan.PSObject.Properties[$name]){throw 'Catalogue C cannot select an export experiment.'}
    }
}
function Get-T7CatalogueMainBaseline($Plan) {
    if(!$Plan.PSObject.Properties['MainBaseline']){return 'Running'}
    if($Plan.MainBaseline -cnotin @('Running','Stopped')){throw 'Unknown Main baseline.'}
    $Plan.MainBaseline
}
function Assert-T7CatalogueMain($Plan) {
    $baseline=Get-T7CatalogueMainBaseline $Plan
    if($baseline -ceq 'Running') {
        # Preserve the existing generation/UDP-owner check without changing its helper.
        return (Assert-T7PrepatchMain $Plan.PreservedMain)
    }
    $expected=$Plan.PreservedMain
    if(!(Test-T7CatalogueInteger $expected.PID ([int]::MaxValue)) -or $expected.PID -le 0 -or
       !$expected.CreatedUtc -or !$expected.Image){throw 'Original Main identity required for stopped baseline.'}
    $null=[datetimeoffset]::Parse($expected.CreatedUtc)
    Assert-H1Path $expected.Image
    $name=[IO.Path]::GetFileName($expected.Image)
    $processes=@(Get-IW7ResourceProcesses)
    # PID reuse, inaccessible same-name images and the expected image at any PID
    # are conservative refusals. Absence does not explain why Main stopped.
    $matches=@($processes|Where-Object {
        $_.PID -eq $expected.PID -or
        ($_.Image -and $_.Image -ieq $expected.Image) -or
        (!$_.Image -and $_.Name -ieq $name)
    })
    $udp=@(Get-NetUDPEndpoint -ErrorAction Stop|Where-Object LocalPort -EQ 27016)
    if($matches.Count -or $udp.Count){throw 'Stopped Main baseline differs or is ambiguous.'}
    [ordered]@{CapturedUtc=[DateTime]::UtcNow.ToString('o');Baseline='Stopped';
        OriginalPID=$expected.PID;OriginalCreatedUtc=$expected.CreatedUtc;ExpectedImage=$expected.Image;
        OriginalPIDAbsent=$true;ExpectedImageAbsent=$true;UDP27016Absent=$true;Cause='Unknown'}
}
function Assert-T7CatalogueMetadata($Expected) {
    Assert-H1Path $Expected.Path
    $item=Get-Item -LiteralPath $Expected.Path
    if($item.PSIsContainer -or $item.Length -ne $Expected.Bytes -or
       [string]$item.Attributes -cne $Expected.Attributes -or
       $item.LastWriteTimeUtc.Ticks -ne ([datetimeoffset]$Expected.LastWriteUtc).UtcDateTime.Ticks){throw 'Reviewed input metadata changed.'}
    if($Expected.PSObject.Properties['CreationUtc'] -and
       $item.CreationTimeUtc.Ticks -ne ([datetimeoffset]$Expected.CreationUtc).UtcDateTime.Ticks){throw 'Reviewed input creation metadata changed.'}
}
function Get-T7CatalogueBootstrap($Plan) {
    # Legacy single-item accessor retained for existing callers/tests.
    $items=@(Get-T7CatalogueBootstraps $Plan)
    if($items.Count -gt 1){throw 'Single bootstrap accessor cannot select a collection item.'}
    if($items.Count){$items[0]}
}
function Get-T7CatalogueBootstrapPolicy($Plan) {
    if(!$Plan.PSObject.Properties['BootstrapPolicy']){return 'Legacy'}
    if($Plan.BootstrapPolicy -isnot [string] -or $Plan.BootstrapPolicy -cnotin @('QualifiedCollectionV1','QualifiedCollectionV2','QualifiedCollectionV3')){
        throw 'Unknown bootstrap collection policy.'
    }
    $Plan.BootstrapPolicy
}
function Get-T7CatalogueBootstrapLimits($Plan) {
    switch -CaseSensitive (Get-T7CatalogueBootstrapPolicy $Plan) {
        'QualifiedCollectionV1' {[pscustomobject]@{ItemCount=8;ItemBytes=32MB;TotalBytes=32MB}}
        'QualifiedCollectionV2' {[pscustomobject]@{ItemCount=8;ItemBytes=64MB;TotalBytes=128MB}}
        'QualifiedCollectionV3' {[pscustomobject]@{ItemCount=32;ItemBytes=512MB;TotalBytes=768MB}}
        default {throw 'Explicit qualified collection policy required for byte limits.'}
    }
}
function Get-T7CatalogueSharedQualification($Plan) {
    if(!$Plan.PSObject.Properties['SharedQualification']){return}
    if((Get-T7CatalogueBootstrapPolicy $Plan) -cne 'QualifiedCollectionV3'){throw 'Shared qualification requires explicit V3.'}
    $shared=$Plan.SharedQualification
    Assert-T7CatalogueFields $shared @('Script','Plan','Receipt')
    foreach($name in 'Script','Plan','Receipt'){
        $pin=$shared.$name;Assert-T7CatalogueFields $pin @('Path','Bytes','SHA256')
        if($pin.Path -isnot [string] -or !(Test-T7CatalogueInteger $pin.Bytes 32KB) -or $pin.Bytes -le 0 -or
           $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '\A[0-9a-f]{64}\z'){throw 'Bounded shared qualification text pins required.'}
        Assert-H1Path $pin.Path
    }
    if([IO.Path]::GetFileName($shared.Script.Path) -cne 'Qualify-T7BootstrapGroup.ps1' -or
       @(@($shared.Script.Path,$shared.Plan.Path,$shared.Receipt.Path)|Sort-Object -Unique).Count -ne 3){throw 'Distinct shared qualifier script/plan/receipt required.'}
    $shared
}
function Get-T7CatalogueBootstraps($Plan) {
    $single=[bool]$Plan.PSObject.Properties['Bootstrap']
    $plural=[bool]$Plan.PSObject.Properties['Bootstraps']
    $qualified=(Get-T7CatalogueBootstrapPolicy $Plan) -cne 'Legacy'
    $shared=Get-T7CatalogueSharedQualification $Plan
    if($single -and $plural){throw 'Mixed bootstrap schemas are forbidden.'}
    if($qualified -and ($single -or !$plural)){throw 'Qualified collection requires only Bootstraps.'}
    if(!$single -and !$plural){return}
    if($qualified){
        $zoneSpec=Get-T7CataloguePlanZoneSpec $Plan
        $limits=Get-T7CatalogueBootstrapLimits $Plan
        if($Plan.Bootstraps -isnot [array] -or $Plan.Bootstraps.Count -lt 1 -or $Plan.Bootstraps.Count -gt $limits.ItemCount){
            throw ('Qualified collection requires one through '+$limits.ItemCount+' explicit items.')
        }
        if((Get-T7CatalogueCandidateProfile $Plan) -cnotin @('t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c')){throw 'Qualified collection requires MSG profile.'}
        $items=@($Plan.Bootstraps);$total=0L
        $names=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        $paths=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        $aliases=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        $ids=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach($path in @($Plan.Zone.Path,$Plan.CandidateSource,$Plan.EngineSource,$Plan.SteamSource,$Plan.JobAssembly,
            $Plan.Image,$Plan.RunRoot,$Plan.WorkingDirectory,$Plan.StageRoot,[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName)){
            $null=$paths.Add($path)
        }
        $sharedCount=0
        if($shared){
            foreach($path in @($shared.Script.Path,$shared.Plan.Path,$shared.Receipt.Path)){
                if(!$paths.Add($path) -or $path.StartsWith($Plan.RunRoot.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Distinct shared paths outside catalogue run root required.'}
            }
        }
        foreach($bootstrap in $items){
            Assert-T7CatalogueFields $bootstrap @('Path','Bytes','SHA256','FileId','RelativePath','HashProvenance','QualificationReceipt','QualificationScript')
            foreach($field in 'Path','SHA256','FileId','RelativePath','HashProvenance'){
                if($bootstrap.$field -isnot [string]){throw 'Qualified bootstrap strings required.'}
            }
            $name=[IO.Path]::GetFileName($bootstrap.Path)
            $stem=[IO.Path]::GetFileNameWithoutExtension($name)
            if($name -cnotmatch '\A[a-z][a-z0-9_]{0,62}\.ff\z' -or
               $stem -match '\A(con|prn|aux|nul|com[1-9]|lpt[1-9])\z' -or $name -ieq $zoneSpec.FileName -or
               $bootstrap.Path -cne (Join-Path ([IO.Path]::GetDirectoryName($Plan.Zone.Path)) $name) -or
               $bootstrap.RelativePath -cne ('zone/'+$name)) {throw 'Unsafe or noncanonical qualified bootstrap name/path.'}
            if(!(Test-T7CatalogueInteger $bootstrap.Bytes $limits.ItemBytes) -or $bootstrap.Bytes -le 0 -or
               $bootstrap.Bytes -gt $limits.TotalBytes-$total){throw 'Qualified bootstrap bytes exceed the item or aggregate policy bound.'}
            $total+=[long]$bootstrap.Bytes
            if($bootstrap.SHA256 -cnotmatch '\A[0-9a-f]{64}\z' -or $bootstrap.FileId -cnotmatch '\A[0-9A-F]{8}:[0-9A-F]{16}\z' -or
               $bootstrap.HashProvenance -cne 'ObservedUnderLeaseNotDepotVerified'){throw 'Qualified bootstrap provenance differs.'}
            if(!$names.Add($name) -or !$aliases.Add($bootstrap.RelativePath) -or !$ids.Add($bootstrap.FileId)){
                throw 'Distinct qualified names, aliases and file identities required.'
            }
            foreach($field in 'QualificationReceipt','QualificationScript'){
                $pin=$bootstrap.$field
                Assert-T7CatalogueFields $pin @('Path','Bytes','SHA256')
                if($pin.Path -isnot [string] -or $pin.SHA256 -isnot [string] -or
                   !(Test-T7CatalogueInteger $pin.Bytes 32KB) -or $pin.Bytes -le 0 -or $pin.SHA256 -cnotmatch '\A[0-9a-f]{64}\z'){
                    throw 'Bounded qualified receipt/script text pins required.'
                }
            }
            $itemPaths=@($bootstrap.Path,$bootstrap.QualificationReceipt.Path)
            if($shared -and $bootstrap.QualificationScript.Path -ceq $shared.Script.Path){
                if($bootstrap.QualificationScript.Bytes -ne $shared.Script.Bytes -or $bootstrap.QualificationScript.SHA256 -cne $shared.Script.SHA256){throw 'Exact shared qualifier script pin required.'}
                $sharedCount++
            }else{$itemPaths+=@($bootstrap.QualificationScript.Path)}
            foreach($path in $itemPaths){
                Assert-H1Path $path
                if(!$paths.Add($path) -or $path.StartsWith($Plan.RunRoot.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)){
                    throw 'Distinct qualified source/text paths outside the run root required.'
                }
            }
        }
        if($shared -and !$sharedCount){throw 'Shared qualification must select explicit members.'}
        return $items # No partial collection may escape before every item validates.
    }
    $specs=@(@{Name='en_core_pre_gfx.ff';Bytes=832L},@{Name='core_pre_gfx.ff';Bytes=22351168L})
    if($single){
        if($null -eq $Plan.Bootstrap -or $Plan.Bootstrap -is [array]){throw 'One legacy bootstrap object required.'}
        $items=@($Plan.Bootstrap);$specs=@($specs[0])
    }
    else {
        if($Plan.Bootstraps -isnot [array] -or $Plan.Bootstraps.Count -ne 2){throw 'Exactly two declared bootstrap items required.'}
        $items=@($Plan.Bootstraps)
    }
    for($index=0;$index -lt $items.Count;$index++){
        $bootstrap=$items[$index];$spec=$specs[$index]
        Assert-T7CatalogueFields $bootstrap @('Path','Bytes','SHA256','FileId','RelativePath','HashProvenance','QualificationReceipt','QualificationScript')
        if((Get-T7CatalogueCandidateProfile $Plan) -cnotin @('t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c') -or
           !(Test-T7CatalogueInteger $bootstrap.Bytes $spec.Bytes) -or $bootstrap.Bytes -ne $spec.Bytes -or
           $bootstrap.Path -cne (Join-Path ([IO.Path]::GetDirectoryName($Plan.Zone.Path)) $spec.Name) -or
           $bootstrap.RelativePath -cne ('zone/'+$spec.Name) -or
           $bootstrap.SHA256 -cnotmatch '\A[0-9a-f]{64}\z' -or $bootstrap.FileId -cnotmatch '\A[0-9A-F]{8}:[0-9A-F]{16}\z' -or
           $bootstrap.HashProvenance -cne 'ObservedUnderLeaseNotDepotVerified'){throw 'Only the exact declared message bootstraps are allowed.'}
        Assert-H1Path $bootstrap.Path
    }
    $items # Publish no item until the complete declared collection has validated.
}
function Assert-T7CatalogueBootstrapBindings($Plan) {
    $bootstraps=@(Get-T7CatalogueBootstraps $Plan)
    if(!$bootstraps.Count){return}
    $binaryPaths=@($Plan.CandidateSource,$Plan.EngineSource,$Plan.SteamSource,$Plan.JobAssembly,
        [Diagnostics.Process]::GetCurrentProcess().MainModule.FileName)+@($bootstraps.Path)
    $binaryPins=@($Plan.Bindings|Where-Object {!$_.IsText})
    if($binaryPins.Count -ne 5+$bootstraps.Count -or @($binaryPins|Where-Object {$_.Path -cnotin $binaryPaths}).Count){throw 'Only the explicit runtime binary bindings are allowed.'}
    $qualificationPaths=@()
    foreach($bootstrap in $bootstraps){
        $pin=@($Plan.Bindings|Where-Object Path -CEQ $bootstrap.Path)
        if($pin.Count -ne 1 -or $pin[0].IsText -isnot [bool] -or $pin[0].IsText -or
           $pin[0].Bytes -ne $bootstrap.Bytes -or $pin[0].SHA256 -cne $bootstrap.SHA256){throw 'Exact bootstrap binary pin missing.'}
        foreach($name in 'QualificationReceipt','QualificationScript'){
            Assert-T7CatalogueTextPin $bootstrap.$name $Plan.Bindings
            if($bootstrap.$name.Bytes -gt 32KB){throw 'Bootstrap qualification text exceeds 32 KiB.'}
            $qualificationPaths+=@($bootstrap.$name.Path)
        }
        $metadata=@($Plan.InputMetadata|Where-Object Path -CEQ $bootstrap.Path)
        if($metadata.Count -ne 1 -or $metadata[0].Bytes -ne $bootstrap.Bytes){throw 'One matching bootstrap metadata record required.'}
        Assert-T7CatalogueFields $metadata[0] @('Path','Bytes','Attributes','CreationUtc','LastWriteUtc')
        Assert-T7CatalogueMetadata $metadata[0]
    }
    $shared=Get-T7CatalogueSharedQualification $Plan
    $scriptCount=@($bootstraps.QualificationScript.Path|Sort-Object -Unique).Count
    $textCount=if($shared){$bootstraps.Count+$scriptCount}else{2*$bootstraps.Count}
    if(@($qualificationPaths|Sort-Object -Unique).Count -ne $textCount){throw 'Distinct per-item bootstrap receipts and scripts required.'}
    if($shared){foreach($name in 'Plan','Receipt'){Assert-T7CatalogueTextPin $shared.$name $Plan.Bindings}}
}
function Assert-T7QualificationLifecycle($Receipt) {
    foreach($name in 'DataFileOpened','PayloadHashed','LeaseAcquired','LeaseReleased','GuardsClosed','TreeClosureConfirmed',
        'MetadataAndIdentityReverifiedUnderGuard','HashReverifiedUnderGuard','PreservedPythonIdentityUnchanged'){
        if(!$Receipt.PSObject.Properties[$name] -or $Receipt.$name -isnot [bool] -or !$Receipt.$name){throw 'Bootstrap qualification lifecycle proof missing.'}
    }
    foreach($name in 'Quarantined','HeaderSemanticsKnown','HeaderPrefixCaptured','ContentCompatibilityProven','DepotVerified',
        'EngineLookupPathProven','NativeEngineExecuted','NativeJobCreated','PayloadCopiedToDisk','PayloadHashesReadAfterRelease','Ready'){
        if(!$Receipt.PSObject.Properties[$name] -or $Receipt.$name -isnot [bool] -or $Receipt.$name){throw 'Bootstrap qualification overclaims its scope.'}
    }
    foreach($name in 'NoProfile','NoExit','DirectFileLaunch','ExactArgumentsVerified'){
        if(!$Receipt.Host.Contract.PSObject.Properties[$name] -or $Receipt.Host.Contract.$name -isnot [bool] -or !$Receipt.Host.Contract.$name){throw 'Qualified persistent bootstrap host required.'}
    }
}
function Assert-T7CatalogueSharedReceipt($Plan,$Receipt,$Bootstrap) {
    $shared=Get-T7CatalogueSharedQualification $Plan
    if(!$shared -or $Bootstrap.QualificationScript.Path -cne $shared.Script.Path){
        if($Receipt.PSObject.Properties['QualificationGroup']){throw 'Unexpected shared qualification membership.'}
        return
    }
    $members=@(Get-T7CatalogueBootstraps $Plan|Where-Object {$_.QualificationScript.Path -ceq $shared.Script.Path})
    $groupPlan=Read-H1SmallJson $shared.Plan.Path 32KB
    $group=Read-H1SmallJson $shared.Receipt.Path 32KB
    Assert-T7CatalogueFields $groupPlan @('Schema','Runner','Script','SourceDirectory','RunRoot','Inputs','Bindings','HostImage','Main','PreservedPython','PhysicalBytes','CommitBytes','DeadlineSeconds','RetryAuthorized')
    if($groupPlan.Schema -cne 'iw7.t7-bootstrap-group-plan/1' -or $groupPlan.Script.Path -cne $shared.Script.Path -or
       $groupPlan.Script.Bytes -ne $shared.Script.Bytes -or $groupPlan.Script.SHA256 -cne $shared.Script.SHA256 -or
       $groupPlan.Runner -cne $shared.Script.Path -or $groupPlan.PhysicalBytes -ne 6GB -or $groupPlan.CommitBytes -ne 8GB -or
       $groupPlan.DeadlineSeconds -ne 200 -or $groupPlan.RetryAuthorized -isnot [bool] -or $groupPlan.RetryAuthorized -or
       $groupPlan.SourceDirectory -cne [IO.Path]::GetDirectoryName($members[0].Path) -or
       $shared.Receipt.Path -cne (Join-Path $groupPlan.RunRoot 'group-receipt.json') -or
       $groupPlan.Inputs -isnot [array] -or $groupPlan.Inputs.Count -ne $members.Count -or
       $group.Schema -cne 'iw7.t7-bootstrap-group-qualification/1' -or $group.Status -cne 'IdentityAndHashObservedCompatibilityUnknown' -or
       $group.PlanSHA256 -cne $shared.Plan.SHA256 -or $group.ScriptSHA256 -cne $shared.Script.SHA256 -or
       $group.GroupComplete -isnot [bool] -or !$group.GroupComplete -or $group.Items -isnot [array] -or $group.Items.Count -ne $members.Count -or
       $group.PSObject.Properties['Error'] -or $group.PSObject.Properties['CleanupError'] -or $group.PSObject.Properties['FinalizationError']){throw 'Complete closed shared qualification required.'}
    Assert-T7QualificationLifecycle $group
    if(!$Receipt.PSObject.Properties['QualificationGroup']){throw 'Shared qualification membership missing.'}
    $membership=$Receipt.QualificationGroup
    Assert-T7CatalogueFields $membership @('PlanSHA256','InputCount','InputIndex')
    if($membership.PlanSHA256 -cne $shared.Plan.SHA256 -or !(Test-T7CatalogueInteger $membership.InputCount 32) -or
       $membership.InputCount -ne $members.Count -or !(Test-T7CatalogueInteger $membership.InputIndex ($members.Count-1))){throw 'Shared qualification membership differs.'}
    for($i=0;$i -lt $members.Count;$i++){
        $member=$members[$i];$declared=$groupPlan.Inputs[$i];$row=$group.Items[$i]
        Assert-T7CatalogueFields $declared @('Name','Path','Bytes','FileId','Attributes','CreationUtc','LastWriteUtc')
        Assert-T7CatalogueFields $row @('Path','Bytes','SHA256','FileId','QualificationReceipt')
        Assert-T7CatalogueFields $row.QualificationReceipt @('Path','Bytes','SHA256')
        $metadata=@($Plan.InputMetadata|Where-Object Path -CEQ $member.Path)[0]
        if($declared.Name -cne [IO.Path]::GetFileName($member.Path) -or $declared.Path -cne $member.Path -or $declared.Bytes -ne $member.Bytes -or
           $declared.FileId -cne $member.FileId -or $declared.Attributes -cne $metadata.Attributes -or
           ([datetimeoffset]$declared.CreationUtc).UtcDateTime.Ticks -ne ([datetimeoffset]$metadata.CreationUtc).UtcDateTime.Ticks -or
           ([datetimeoffset]$declared.LastWriteUtc).UtcDateTime.Ticks -ne ([datetimeoffset]$metadata.LastWriteUtc).UtcDateTime.Ticks -or
           $row.Path -cne $member.Path -or $row.Bytes -ne $member.Bytes -or $row.SHA256 -cne $member.SHA256 -or $row.FileId -cne $member.FileId -or
           $member.QualificationReceipt.Path -cne (Join-Path $groupPlan.RunRoot ($declared.Name+'.receipt.json')) -or
           $row.QualificationReceipt.Path -cne $member.QualificationReceipt.Path -or $row.QualificationReceipt.Bytes -ne $member.QualificationReceipt.Bytes -or
           $row.QualificationReceipt.SHA256 -cne $member.QualificationReceipt.SHA256){throw 'Shared qualification input/receipt identity differs.'}
    }
    if($members[$membership.InputIndex].Path -cne $Bootstrap.Path){throw 'Shared qualification index points to another input.'}
}
function Assert-T7CatalogueBootstrapReceipt($Plan,$Receipt,[string]$BootstrapPath) {
    $items=@(Get-T7CatalogueBootstraps $Plan)
    if($BootstrapPath){$items=@($items|Where-Object Path -CEQ $BootstrapPath)}
    if($items.Count -ne 1){throw 'Select one explicitly declared bootstrap receipt.'}
    $bootstrap=$items[0]
    Assert-T7CatalogueBootstrapBindings $Plan
    if($Receipt.Schema -cne 'iw7.t7-bootstrap-qualification/1' -or
       $Receipt.Status -cne 'IdentityAndHashObservedCompatibilityUnknown' -or
       $Receipt.ScriptSHA256 -cne $bootstrap.QualificationScript.SHA256 -or
       $Receipt.SHA256 -cne $bootstrap.SHA256 -or $Receipt.FileId -cne $bootstrap.FileId -or
       $Receipt.HashProvenance -cne $bootstrap.HashProvenance -or
       $Receipt.GuardedReadBytesPerPass -ne $bootstrap.Bytes -or $Receipt.GuardedReadPasses -ne 2 -or
       $Receipt.PSObject.Properties['Error'] -or $Receipt.PSObject.Properties['CleanupError'] -or
       $Receipt.PSObject.Properties['FinalizationError']){throw 'Closed successful bootstrap qualification required.'}
    Assert-T7QualificationLifecycle $Receipt
    Assert-T7CatalogueSharedReceipt $Plan $Receipt $bootstrap
    $metadata=@($Plan.InputMetadata|Where-Object Path -CEQ $bootstrap.Path)[0]
    Assert-T7CatalogueFields $Receipt.Input @('Path','Bytes','Attributes','CreationUtc','LastWriteUtc')
    if($Receipt.Input.Path -cne $bootstrap.Path){throw 'Qualification input path differs.'}
    foreach($row in @($Receipt.Input,$Receipt.MetadataBefore,$Receipt.MetadataAfter)){
        if($row.Bytes -ne $bootstrap.Bytes -or $row.Attributes -cne $metadata.Attributes -or
           ([datetimeoffset]$row.CreationUtc).UtcDateTime.Ticks -ne ([datetimeoffset]$metadata.CreationUtc).UtcDateTime.Ticks -or
           ([datetimeoffset]$row.LastWriteUtc).UtcDateTime.Ticks -ne ([datetimeoffset]$metadata.LastWriteUtc).UtcDateTime.Ticks){throw 'Qualified bootstrap metadata differs.'}
    }
    foreach($row in @($Receipt.MetadataBefore,$Receipt.MetadataAfter)){
        Assert-T7CatalogueFields $row @('Bytes','Attributes','CreationUtc','LastWriteUtc','FileId')
        if($row.FileId -cne $bootstrap.FileId){throw 'Qualified bootstrap file identity differs.'}
    }
}
function Assert-T7CatalogueBootstrapIdentity($Plan) {
    foreach($bootstrap in @(Get-T7CatalogueBootstraps $Plan)){
        $metadata=@($Plan.InputMetadata|Where-Object Path -CEQ $bootstrap.Path)
        if($metadata.Count -ne 1){throw 'One bootstrap metadata record required.'}
        Assert-T7CatalogueMetadata $metadata[0]
        if((Get-T7CatalogueFileId $bootstrap.Path) -cne $bootstrap.FileId){throw 'Bootstrap differs from its qualified file identity.'}
    }
}
function Assert-T7CatalogueDistinctInputIds($Plan,$InputFileIds) {
    if((Get-T7CatalogueBootstrapPolicy $Plan) -ceq 'Legacy'){return}
    $bootstraps=@(Get-T7CatalogueBootstraps $Plan)
    $expected=@($Plan.CandidateSource,$Plan.EngineSource,$Plan.SteamSource,$Plan.Zone.Path)+@($bootstraps.Path)
    if((Get-T7CatalogueOperation $Plan) -ceq 'ResidentExportV1' -and (Get-T7SelectedStreamedExport $Plan)){$expected+=@($Plan.SelectedXpakProvider.Metadata.Path,$Plan.ExportRequestFile.Path)}
    if(@($InputFileIds).Count -ne $expected.Count){throw 'Complete original input IDs required before aliases.'}
    $paths=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $ids=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($row in $InputFileIds){
        Assert-T7CatalogueFields $row @('Path','FileId')
        if($row.Path -isnot [string] -or $row.Path -cnotin $expected -or $row.FileId -isnot [string] -or
           $row.FileId -cnotmatch '\A[0-9A-F]{8}:[0-9A-F]{16}\z' -or !$paths.Add($row.Path) -or !$ids.Add($row.FileId)){
            throw 'Distinct original input paths and file identities required before aliases.'
        }
        $bootstrap=@($bootstraps|Where-Object Path -CEQ $row.Path)
        if($bootstrap.Count -and $bootstrap[0].FileId -cne $row.FileId){throw 'Original bootstrap identity differs from qualification.'}
    }
}
function Get-T7CatalogueOperation($Plan) {
    if(!$Plan.PSObject.Properties['Operation']){return 'Catalogue'}
    if($Plan.Operation -isnot [string] -or $Plan.Operation -cnotin @('Catalogue','ResidentExportV1')){throw 'Unknown T7 operation.'}
    $Plan.Operation
}
function Assert-T7CataloguePlan($Plan,[string]$Repo,[string]$Runner) {
    $export=(Get-T7CatalogueOperation $Plan) -ceq 'ResidentExportV1'
    $zoneSpec=Get-T7CataloguePlanZoneSpec $Plan
    $diagnostic=[bool]$Plan.PSObject.Properties['ResidentSurfaceCountDiagnostic']
    if($diagnostic -and !$export){throw 'Surface-count diagnostic is restricted to ResidentExportV1.'}
    if($Plan.PSObject.Properties['ResidentMultiSurfaceV2'] -and !$export){throw 'Resident multi-surface v2 is restricted to the export operation.'}
    if($Plan.PSObject.Properties['SelectedMeshMaterialObservation'] -and !$export){throw 'Selected observation probe is restricted to the export operation.'}
    if($Plan.PSObject.Properties['SelectedStreamedStaticV1'] -and !$export){throw 'Selected-streamed E3 is restricted to the export operation.'}
    if($Plan.PSObject.Properties['SelectedStreamedRenderOnlyV2'] -and !$export){throw 'Render-only E5 is restricted to the export operation.'}
    $streamed=$export -and [bool](Get-T7SelectedStreamedExport $Plan)
    $schema=if($export){'iw7.t7-resident-export-plan/1'}else{'iw7.t7-catalogue-plan/1'}
    $reportLimit=if($export){Get-T7ResidentExportReportLimit $Plan}else{512KB}
    if($export){Assert-T7ResidentExportPlan $Plan $Repo}
    $candidateProfile=Get-T7CatalogueCandidateProfile $Plan
    Assert-T7CatalogueZombiesObservationPlan $Plan
    $null=Get-T7CatalogueMainBaseline $Plan
    $bootstraps=@(Get-T7CatalogueBootstraps $Plan)
    $qualified=(Get-T7CatalogueBootstrapPolicy $Plan) -cne 'Legacy'
    if(!(Test-T7CatalogueInteger $Plan.CandidateBytes 64MB) -or $Plan.CandidateBytes -le 0){throw 'Exact bounded candidate identity required.'}
    $bootstrapBytes=0L
    foreach($bootstrap in $bootstraps){
        if(!(Test-T7CatalogueInteger $bootstrap.Bytes ([long]::MaxValue-$bootstrapBytes))){throw 'Bootstrap sum exceeds integer range.'}
        $bootstrapBytes+=[long]$bootstrap.Bytes
    }
    $fixedBytes=$zoneSpec.FixedBytes+[long]$Plan.CandidateBytes
    if($bootstrapBytes -gt [long]::MaxValue-$fixedBytes){throw 'Output budget exceeds integer range.'}
    $expectedOutputBytes=$fixedBytes+$bootstrapBytes
    $selectedExtraBytes=0L
    if($streamed){$selectedExtraBytes=[long]$Plan.SelectedXpakProvider.Metadata.Bytes+[long]$Plan.ExportRequestFile.Bytes;$expectedOutputBytes+=$selectedExtraBytes}
    if($qualified){
        $limits=Get-T7CatalogueBootstrapLimits $Plan
        $shared=Get-T7CatalogueSharedQualification $Plan
        $bindingCount=22+3*$bootstraps.Count
        if($shared){$bindingCount=24+2*$bootstraps.Count+@($bootstraps.QualificationScript.Path|Sort-Object -Unique).Count}
        # Five new profile text pins (link.rsp already exists), plus CLI dependencies.
        if($candidateProfile -cin @('t7-catalog-message-publication','t7-zombies-catalogue-observation-c')){$bindingCount+=6}
        if($candidateProfile -ceq 't7-zombies-catalogue-observation-c'){$bindingCount+=11} # Observer pair, shared qualifier and eight C closure/source pins.
        if($export){$bindingCount+=9}
        if($diagnostic){$bindingCount++} # Exactly one additional guarded prepared header.
        if($export -and (Get-T7ResidentExportVersion $Plan) -eq 2){$bindingCount+=6} # D header and five closed-build evidence texts.
        if($export -and (Get-T7SelectedObservationProbe $Plan)){$bindingCount+=3} # E2 source/probe pins and distinct closure bundle.
        if($streamed){$bindingCount+=9} # Eight E3 build text pins beyond D plus the operational streamed reader contract.
        if($streamed -and ((Test-T7SelectedStreamedE4Build $Plan) -or (Get-T7SelectedStreamedRenderOnly $Plan))){$bindingCount+=2} # E4/E5 actual tool return and completion texts.
        if(!(Test-T7CatalogueInteger $Plan.CandidateBytes 64MB) -or $Plan.CandidateBytes -le 0 -or
           !(Test-T7CatalogueInteger $Plan.OutputLimitBytes ($zoneSpec.FixedBytes+64MB+$limits.TotalBytes+$selectedExtraBytes)) -or
           @($Plan.Bindings).Count -ne $bindingCount){throw 'Exact qualified collection budget/binding count required.'}
    }
    if($Plan.Schema -cne $schema -or $Plan.Runner -cne $Runner -or
       $Plan.EngineOutputProfile -cnotin @('ObservedStartupA','ObservedStartupManifestA') -or
       $Plan.PhysicalBytes -ne 6GB -or $Plan.CommitBytes -ne 8GB -or
       $Plan.GroupDeadlineSeconds -ne 200 -or $Plan.DeadlineSeconds -ne 120 -or
       $Plan.MutableOutputLimitBytes -ne 64MB -or $Plan.MetadataReserveBytes -ne 64KB -or
       $Plan.CleanupSeconds -ne 5 -or $Plan.ReportLimitBytes -ne $reportLimit -or
       $Plan.LogLimitBytes -ne 1MB -or $Plan.OutputLimitBytes -ne $expectedOutputBytes -or
       $Plan.RetryAuthorized -isnot [bool] -or $Plan.RetryAuthorized){throw 'Fixed catalogue plan differs.'}
    if(!(Test-T7CatalogueInteger $Plan.CandidateBytes 64MB) -or $Plan.CandidateBytes -le 0 -or
       $Plan.CandidateSHA256 -cnotmatch '\A[0-9a-f]{64}\z'){throw 'Exact bounded candidate identity required.'}
    if($candidateProfile -ceq 'ordinary-d2' -and ($Plan.CandidateBytes -ne 21740032 -or
       $Plan.CandidateSHA256 -cne '94dd29a9cb538504ddeb3545483e43a5dfea195aaca155db5bf147f1c6334c15')){throw 'Ordinary D2 candidate differs.'}
    if($candidateProfile -cne 'ordinary-d2') {
        $limit=switch($candidateProfile){'t7-catalog-trace'{1536};'t7-catalog-exit-context'{4096};'t7-catalog-callers'{8192};'t7-catalog-message'{8192};'t7-catalog-message-publication'{8192};'t7-zombies-catalogue-observation-c'{16384}}
        if(!(Test-T7CatalogueInteger $Plan.TraceStderrLimitBytes $limit) -or $Plan.TraceStderrLimitBytes -ne $limit){throw 'Exact trace stderr bound required.'}
    }
    Assert-H1Path $Plan.RunRoot
    $rootPattern=if($export){'^t7-export-[a-z][a-z0-9-]*$'}else{'^t7-catalog-[a-z][a-z0-9-]*$'}
    if([IO.Path]::GetDirectoryName($Plan.RunRoot) -cne (Join-Path $Repo 'runtime') -or
       [IO.Path]::GetFileName($Plan.RunRoot) -cnotmatch $rootPattern -or
       $Plan.WorkingDirectory -cne (Join-Path $Plan.RunRoot 'work') -or
       $Plan.StageRoot -cne (Join-Path $Plan.RunRoot 'evidence') -or
       $Plan.Image -cne (Join-Path $Plan.WorkingDirectory 't7-zonetool-candidate.exe')){throw 'Exact catalogue command/root required.'}
    if(!$export -and (@($Plan.Arguments).Count -ne 2 -or $Plan.Arguments[0] -isnot [string] -or
       $Plan.Arguments[0] -cne '-t7-iw7-catalog' -or $Plan.Arguments[1] -isnot [string] -or
       $Plan.Arguments[1] -cne $zoneSpec.Name -or $Plan.OutputKey -isnot [string] -or
       $Plan.OutputKey -cne $zoneSpec.OutputKey)){throw 'Exact catalogue command/root required.'}
    foreach($dir in @($Plan.RunRoot,$Plan.WorkingDirectory,$Plan.StageRoot,(Join-Path $Plan.RunRoot 'temp'))) {
        Assert-H1Path $dir
        if(![IO.Directory]::Exists($dir)){throw 'Prepared empty ordinary directories required.'}
    }
    $rootNames=@([IO.Directory]::EnumerateFileSystemEntries($Plan.RunRoot)|ForEach-Object {[IO.Path]::GetFileName($_)}|Sort-Object)
    if(($rootNames -join '|') -cne 'evidence|temp|work'){throw 'Fresh attempt root required; no retry or parent zone.'}
    foreach($dir in @($Plan.WorkingDirectory,$Plan.StageRoot,(Join-Path $Plan.RunRoot 'temp'))) {
        if(@([IO.Directory]::EnumerateFileSystemEntries($dir)).Count){throw 'Prepared work/evidence/temp must be empty.'}
    }
    $bindingLimit=if($qualified){22+3*$limits.ItemCount+$(if($shared){2}else{0})}else{32}
    if($candidateProfile -cin @('t7-catalog-message-publication','t7-zombies-catalogue-observation-c')){$bindingLimit+=6}
    if($candidateProfile -ceq 't7-zombies-catalogue-observation-c'){$bindingLimit+=11}
    if($export){$bindingLimit+=9}
    if($diagnostic){$bindingLimit++}
    if($streamed){$bindingLimit+=9}
    if($streamed -and ((Test-T7SelectedStreamedE4Build $Plan) -or (Get-T7SelectedStreamedRenderOnly $Plan))){$bindingLimit+=2}
    if(@($Plan.Bindings).Count -gt $bindingLimit -or @($Plan.Bindings.Path|Sort-Object -Unique).Count -ne @($Plan.Bindings).Count){throw 'Bounded unique bindings required.'}
    $bindingPaths=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($pin in $Plan.Bindings) {
        if($qualified -and !$bindingPaths.Add($pin.Path)){throw 'Distinct qualified binding paths required.'}
        Assert-H1Path $pin.Path
        # Only explicit bootstrap bindings inherit the selected collection cap.
        # Candidate/provider/text bounds do not grow with the donor-file policy.
        $pinLimit=if($qualified -and $pin.Path -cin @($bootstraps.Path)){$limits.ItemBytes}else{64MB}
        $item=Get-Item -LiteralPath $pin.Path
        if($item.PSIsContainer -or $pin.IsText -isnot [bool] -or $pin.Bytes -le 0 -or $pin.Bytes -gt $pinLimit -or
           ($pin.IsText -and $pin.Bytes -gt 1MB) -or $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or $item.Length -ne $pin.Bytes){throw 'Bound pin metadata differs.'}
    }
    if($candidateProfile -ceq 't7-zombies-catalogue-observation-c'){
        $sharedPath=Join-Path (Split-Path $Runner -Parent) 'T7ResidentExport.Profile.ps1'
        if(@($Plan.Bindings|Where-Object {$_.Path -ceq $sharedPath -and $_.IsText -is [bool] -and $_.IsText}).Count -ne 1){throw 'C shared build qualifier must be guarded text.'}
    }
    $expected=@(
        @($Plan.CandidateSource,$Plan.CandidateBytes,$Plan.CandidateSHA256),
        @($Plan.EngineSource,21737352,'3df511d71e3690b14517379783bbfb713f6fe2ed2f2e73b445b4878216686156'),
        @($Plan.SteamSource,235600,'71af8666392acad2080a816b9f1196fe9ccb950e1db8a549f8312c4d231f55a8'))
    foreach($row in $expected) {
        $pin=@($Plan.Bindings|Where-Object Path -CEQ $row[0])
        if($pin.Count -ne 1 -or $pin[0].IsText -or $pin[0].Bytes -ne $row[1] -or $pin[0].SHA256 -cne $row[2]){throw 'Exact qualified D2/engine/Steam binding required.'}
    }
    $inputCount=4+$bootstraps.Count
    if($streamed){$inputCount+=2}
    if(@($Plan.InputMetadata).Count -ne $inputCount -or @($Plan.InputMetadata.Path|Sort-Object -Unique).Count -ne $inputCount){throw 'Exact input metadata count differs.'}
    $paths=@($Plan.CandidateSource,$Plan.EngineSource,$Plan.SteamSource,$Plan.Zone.Path)
    if($bootstraps.Count){$paths+=@($bootstraps.Path)}
    if($streamed){$paths+=@($Plan.SelectedXpakProvider.Metadata.Path,$Plan.ExportRequestFile.Path)}
    foreach($item in $Plan.InputMetadata){if($item.Path -cnotin $paths){throw 'Unexpected input metadata.'};Assert-T7CatalogueMetadata $item}
    if(!(Test-T7CatalogueInteger $Plan.Zone.Bytes $zoneSpec.Bytes) -or $Plan.Zone.Bytes -ne $zoneSpec.Bytes -or $Plan.Zone.SHA256 -ne $null -or
       $Plan.Zone.RelativePath -isnot [string] -or $Plan.Zone.RelativePath -cne $zoneSpec.RelativePath -or
       $Plan.Zone.HashProvenance -cne 'ObserveUnderLease' -or
       [IO.Path]::GetFileName($Plan.Zone.Path) -cne $zoneSpec.FileName -or
       @($Plan.Bindings|Where-Object Path -CEQ $Plan.Zone.Path).Count){throw 'Only the explicit unsealed owner FF is allowed.'}
    Assert-T7CatalogueMetadata $Plan.Zone
    Assert-T7CatalogueBootstrapBindings $Plan
}
function Assert-T7CatalogueBuild($Plan,$Receipt) {
    $candidateProfile=Get-T7CatalogueCandidateProfile $Plan
    if($candidateProfile -ceq 't7-zombies-catalogue-observation-c' -or $Plan.PSObject.Properties['ZombiesObservationC']){
        Assert-T7CatalogueZombiesObservationPlan $Plan
    }
    foreach($field in 'InputsReverified','TreeClosureConfirmed','LeaseReleased','Quarantined','CandidateExecuted') {
        if($Receipt.$field -isnot [bool]){throw 'Build lifecycle booleans required.'}
    }
    if($Receipt.Schema -cne 'iw7.t7-minimal-build/1' -or $Receipt.PlanSHA256 -cne $Plan.ExpectedBuildPlanSHA256 -or
       $Receipt.Status -cne 'Passed' -or !$Receipt.InputsReverified -or !$Receipt.TreeClosureConfirmed -or
       !$Receipt.LeaseReleased -or $Receipt.Quarantined -or $Receipt.CandidateExecuted){throw 'Closed successful unexecuted catalogue build required.'}
    if($candidateProfile -ceq 'ordinary-d2') {
        if($Receipt.PlanSHA256 -cne 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa' -or
           $Receipt.PSObject.Properties['BuildProfile']){throw 'Exact closed ordinary D2 build required.'}
    }else{Assert-T7CatalogueTraceBuild $Plan $Receipt}
    $artifacts=@($Receipt.Stages|ForEach-Object {$_.Artifacts}|Where-Object Path -CEQ $Plan.CandidateSource)
    if($artifacts.Count -ne 1 -or $artifacts[0].Bytes -ne $Plan.CandidateBytes -or $artifacts[0].SHA256 -cne $Plan.CandidateSHA256){throw 'Candidate differs from build artifact.'}
}
function Assert-T7CatalogueTextPin($Pin,$Bindings) {
    Assert-T7CatalogueFields $Pin @('Path','Bytes','SHA256')
    Assert-H1Path $Pin.Path
    if(!(Test-T7CatalogueInteger $Pin.Bytes 1MB) -or $Pin.Bytes -eq 0 -or $Pin.SHA256 -cnotmatch '\A[0-9a-f]{64}\z'){throw 'Bounded exact trace text pin required.'}
    $match=@($Bindings|Where-Object {$_.Path -ceq $Pin.Path -and $_.IsText -is [bool] -and $_.IsText -and $_.Bytes -eq $Pin.Bytes -and $_.SHA256 -ceq $Pin.SHA256})
    if($match.Count -ne 1){throw 'Trace text pin is not guarded.'}
}
function Assert-T7CatalogueTraceBuild($Plan,$Receipt) {
    $candidateProfile=Get-T7CatalogueCandidateProfile $Plan
    $publication=$candidateProfile -cin @('t7-catalog-message-publication','t7-zombies-catalogue-observation-c')
    $buildPin=@($Plan.Bindings|Where-Object {$_.Path -ceq $Plan.BuildPlan -and $_.IsText})
    if($buildPin.Count -ne 1 -or $buildPin[0].SHA256 -cne $Plan.ExpectedBuildPlanSHA256 -or
       $buildPin[0].Bytes -gt 1MB -or $Plan.ExpectedBuildPlanSHA256 -ceq 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa'){throw 'Trace requires its own guarded build plan.'}
    $build=Read-H1SmallJson $Plan.BuildPlan 1MB
    if($build.Schema -cne 'iw7.t7-minimal-build-plan/1' -or
       $build.SourceCommit -cne 'fab935826c898806855376662a8a03317b3ad8f1'){throw 'Trace build source/schema differs.'}
    $profile=$build.BuildProfile
    $fields=@('Name','Option','ArgumentCount','TraceSchema','Wiring','PreparedMain','BaseBuildPlan','BaseBuildReceipt')
    if($candidateProfile -cin @('t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c')){$fields+=@('ContextSchema')}
    if($candidateProfile -cin @('t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c')){$fields+=@('CallerSchema')}
    if($candidateProfile -cin @('t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c')){$fields+=@('MessageSchema')}
    $pinNames=@('Wiring','PreparedMain','BaseBuildPlan','BaseBuildReceipt')
    if($publication){
        $extraPins=@('PublicationWiring','PublicationSource','PreparedCLI','MainResponse','CLIResponse','LinkResponse')
        $fields+=@('PublicationSchema')+$extraPins;$pinNames+=$extraPins
    }
    if($candidateProfile -ceq 't7-zombies-catalogue-observation-c'){
        $fields+=@('ObservationSchema','ObserverSource','ObserverAdapter');$pinNames+=@('ObserverSource','ObserverAdapter')
    }
    foreach($p in @($profile,$Receipt.BuildProfile)) {
        Assert-T7CatalogueFields $p $fields
        if($p.Name -cne $candidateProfile -or $p.Option -cne '-t7-iw7-catalog' -or
           ($p.ArgumentCount -isnot [long] -and $p.ArgumentCount -isnot [int]) -or $p.ArgumentCount -ne 3 -or
           $p.TraceSchema -cne 'iw7.t7-catalog-trace/1'){throw 'Exact catalogue trace profile required.'}
        if($candidateProfile -cin @('t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c') -and $p.ContextSchema -cne 'iw7.t7-catalog-exit-context/1'){throw 'Exact exit context schema required.'}
        if($candidateProfile -cin @('t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c') -and $p.CallerSchema -cne 'iw7.t7-catalog-callers/1'){throw 'Exact caller schema required.'}
        if($candidateProfile -cin @('t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c') -and $p.MessageSchema -cne 'iw7.t7-catalog-message/1'){throw 'Exact message schema required.'}
        if($publication -and $p.PublicationSchema -cne 'iw7.t7-message-publication-build/1'){throw 'Exact publication build schema required.'}
        if($candidateProfile -ceq 't7-zombies-catalogue-observation-c' -and $p.ObservationSchema -cne 'iw7.t7-zm-observation/1'){throw 'Exact C observation build schema required.'}
    }
    foreach($name in $pinNames) {
        $pin=$profile.$name;$other=$Receipt.BuildProfile.$name
        Assert-T7CatalogueTextPin $pin $Plan.Bindings
        Assert-T7CatalogueTextPin $pin $build.Bindings
        Assert-T7CatalogueFields $other @('Path','Bytes','SHA256')
        if($other.Path -cne $pin.Path -or $other.Bytes -ne $pin.Bytes -or $other.SHA256 -cne $pin.SHA256){throw 'Receipt trace profile differs from build plan.'}
    }
    if($profile.PreparedMain.Path -cne (Join-Path $build.PreparedRoot 'main.cpp') -or
       $profile.Wiring.Path -cne (Join-Path ([IO.Path]::GetDirectoryName($build.Runner)) 'prepare_catalog_trace.py') -or
       $profile.BaseBuildPlan.SHA256 -cne 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa' -or
       $profile.BaseBuildReceipt.SHA256 -cne 'c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2'){throw 'Trace source/base provenance differs.'}
    $base=Read-H1SmallJson $profile.BaseBuildPlan.Path 1MB
    $reuse=$build.ReuseCompile;$old=$base.ReuseCompile
    if($base.Schema -cne 'iw7.t7-minimal-build-plan/1' -or $reuse.RecompiledMain -isnot [bool] -or !$reuse.RecompiledMain -or
       $reuse.OriginalStatus -cne 'Failed' -or $reuse.Checks -ne 51){throw 'Trace must recompile main and retain qualified failed-group objects.'}
    foreach($name in 'SourcePlan','SourcePlanSHA256','Receipt','ReceiptSHA256') {
        if($reuse.$name -cne $old.$name){throw 'Trace reuse chain differs from ordinary D2.'}
        if($name -cin @('SourcePlan','Receipt')) {
            $pin=@($base.Bindings|Where-Object {$_.Path -ceq $old.$name -and $_.IsText})
            if($pin.Count -ne 1){throw 'D2 reuse source pin missing.'}
            Assert-T7CatalogueTextPin ([pscustomobject]@{Path=$pin[0].Path;Bytes=$pin[0].Bytes;SHA256=$pin[0].SHA256}) $build.Bindings
        }
    }
    if($publication){Assert-T7CataloguePublicationBuild $Plan $Receipt $build $base;return}
    if($reuse.PSObject.Properties['RecompiledZonetool']){throw 'CLI rebuild marker requires the publication profile.'}
    $retained=@($old.StageRoots|Where-Object {[IO.Path]::GetFileName($_) -cne 'main'})
    if(@($reuse.StageRoots).Count -ne 2 -or (@($retained|ForEach-Object {[IO.Path]::GetFileName($_)}) -join '|') -cne 'zonetool11|xpak' -or
       (@($reuse.StageRoots) -join '|') -cne ($retained -join '|')){throw 'Exact retained zonetool11/xpak roots required.'}
    foreach($stages in @(@{Rows=@($build.Stages)},@{Rows=@($Receipt.Stages)})) {
        if($stages.Rows.Count -ne 2 -or ($stages.Rows.Name -join '|') -cne 'main|link' -or
           ($stages.Rows.Stage -join '|') -cne 'Compile|Link'){throw 'Trace requires actual main Compile then link Link.'}
    }
    for($i=0;$i -lt 2;$i++) {
        $stage=$Receipt.Stages[$i]
        if($stage.PlanSHA256 -cne $Plan.ExpectedBuildPlanSHA256 -or $stage.ExitCode -ne 0 -or
           $stage.TreeClosureConfirmed -isnot [bool] -or !$stage.TreeClosureConfirmed){throw 'Trace compile/link stage not successful and closed.'}
    }
    $mainRoot=Join-Path $build.RunRoot 'main';$linkRoot=Join-Path $build.RunRoot 'link'
    $mainObject=Join-Path $mainRoot 'main.obj';$dependencyPath=Join-Path $mainRoot 'dependencies.json'
    foreach($path in @($mainObject,$dependencyPath)) {
        $pin=@($Receipt.Stages[0].Artifacts|Where-Object Path -CEQ $path)
        if($pin.Count -ne 1 -or $pin[0].Bytes -le 0 -or $pin[0].SHA256 -cnotmatch '\A[0-9a-f]{64}\z'){throw 'Trace main artifact missing.'}
        if($path -ceq $dependencyPath){Assert-T7CatalogueTextPin $pin[0] $Plan.Bindings}
    }
    $deps=Read-H1SmallJson $dependencyPath 1MB
    if([IO.Path]::GetFullPath($deps.Data.Source) -ine $profile.PreparedMain.Path){throw 'Compiler dependencies do not identify prepared trace main.'}
    $link=$build.Stages[1]
    $rsp=Join-Path ([IO.Path]::GetDirectoryName($build.PreparedRoot)) 'link.rsp'
    if(@($link.Arguments).Count -ne 1 -or $link.Arguments[0] -cne ('@'+$rsp) -or
       $Plan.CandidateSource -cne (Join-Path $linkRoot 'zonetool-t7.exe')){throw 'Trace link command/artifact differs.'}
    $rspPin=@($build.Bindings|Where-Object {$_.Path -ceq $rsp -and $_.IsText})
    if($rspPin.Count -ne 1){throw 'Trace link response pin missing.'}
    Assert-T7CatalogueTextPin ([pscustomobject]@{Path=$rsp;Bytes=$rspPin[0].Bytes;SHA256=$rspPin[0].SHA256}) $Plan.Bindings
    if(@([IO.File]::ReadAllLines($rsp)|Where-Object {$_ -ceq ('"'+$mainObject+'"')}).Count -ne 1){throw 'Trace Link must consume the newly compiled main object exactly once.'}
    if(@($Receipt.Stages[1].Artifacts|Where-Object Path -CEQ $Plan.CandidateSource).Count -ne 1){throw 'Trace candidate absent from Link artifacts.'}
}
function Split-T7CatalogueResponseArguments([string]$Text) {
    # Same bounded generated-response syntax as the publication build validator.
    if($Text -match '[\x00-\x08\x0a-\x1f\x7f]|\\+"|""' -or $Text.Contains('@')){throw 'Unsupported or indirect publication response syntax.'}
    $arguments=[Collections.Generic.List[string]]::new();$token=[Text.StringBuilder]::new();$quoted=$false
    foreach($character in $Text.ToCharArray()) {
        if($character -eq '"'){$quoted=!$quoted;continue}
        if(!$quoted -and ($character -eq ' ' -or $character -eq "`t")) {
            if($token.Length){$arguments.Add($token.ToString());$null=$token.Clear()}
        }else{$null=$token.Append($character)}
    }
    if($quoted){throw 'Unclosed publication response quote.'}
    if($token.Length){$arguments.Add($token.ToString())}
    return ,$arguments.ToArray()
}
function Assert-T7CatalogueResponseOutputs([string[]]$Arguments,[System.Collections.IDictionary]$Outputs) {
    $seen=@{}
    for($index=0;$index -lt $Arguments.Count;$index++) {
        $argument=$Arguments[$index];if($argument -notmatch '^[-/]'){continue};$option=$argument.Substring(1)
        if($option -ieq 'PDBCompress'){continue}
        foreach($name in $Outputs.Keys) {
            if(!$option.StartsWith($name,[StringComparison]::OrdinalIgnoreCase)){continue}
            if($seen.ContainsKey($name)){throw 'Duplicate publication output option.'};$seen[$name]=$true
            $value=$option.Substring($name.Length);if($value.StartsWith(':')){$value=$value.Substring(1)}
            if(!$value){$index++;if($index -ge $Arguments.Count){throw 'Missing publication output value.'};$value=$Arguments[$index]}
            if($value -cne $Outputs[$name]){throw 'Publication output must belong to its exact fresh stage.'}
            break
        }
    }
    if($seen.Count -ne $Outputs.Count){throw 'Missing publication output option.'}
}
function Assert-T7CatalogueZombiesSourceTransition($Build) {
    if(!$Build.ReuseCompile.PSObject.Properties['ZombiesObservationC']){throw 'Explicit Catalogue C source transition required.'}
    $proof=$Build.ReuseCompile.ZombiesObservationC
    Assert-T7CatalogueFields $proof @('Schema','SourceProfile','BaseCLIBytes','BaseCLISHA256','CLIBytes','CLISHA256')
    if($proof.Schema -cne 'iw7.t7-zm-observation-build/1' -or
       $proof.SourceProfile -cne 't7-zombies-catalogue-observation-c' -or
       !(Test-T7CatalogueInteger $proof.BaseCLIBytes 107785) -or $proof.BaseCLIBytes -ne 107785 -or
       $proof.BaseCLISHA256 -cne 'c480fbd39525df09bd5677026678743c73fa66eb3ca0752e78729eee2f4dcc50' -or
       !(Test-T7CatalogueInteger $proof.CLIBytes 118485) -or $proof.CLIBytes -ne 118485 -or
       $proof.CLISHA256 -cne '917c2f9025185d23a8b2b683157144c2da62fe747f17f11e0f8c1abcf66be987' -or
       $Build.BuildProfile.PreparedCLI.Bytes -ne $proof.CLIBytes -or
       $Build.BuildProfile.PreparedCLI.SHA256 -cne $proof.CLISHA256){throw 'Exact reviewed Catalogue C source transition required.'}
}
function Assert-T7CataloguePublicationBuild($Plan,$Receipt,$Build,$Base) {
    # Only guarded source/response/dependency text is read here. Binary artifacts
    # are receipt metadata; their actual verification remains under admission.
    $profile=$Build.BuildProfile;$reuse=$Build.ReuseCompile
    $zombies=(Get-T7CatalogueCandidateProfile $Plan) -ceq 't7-zombies-catalogue-observation-c'
    if($reuse.PSObject.Properties['ZombiesObservationC'] -and !$zombies){throw 'C reuse marker requires the C catalogue profile.'}
    if(!$reuse.PSObject.Properties['RecompiledZonetool'] -or $reuse.RecompiledZonetool -isnot [bool] -or
       !$reuse.RecompiledZonetool){throw 'Publication requires a fresh CLI compilation.'}
    $retained=@($Base.ReuseCompile.StageRoots|Where-Object {[IO.Path]::GetFileName($_) -ceq 'xpak'})
    if($retained.Count -ne 1 -or @($reuse.StageRoots).Count -ne 1 -or $reuse.StageRoots[0] -cne $retained[0]){throw 'Publication retains only the qualified xpak root.'}
    if($Plan.BuildReceipt -cne (Join-Path $Build.RunRoot 'receipt.json')){throw 'Publication requires its own build receipt.'}
    $receiptPin=@($Plan.Bindings|Where-Object {$_.Path -ceq $Plan.BuildReceipt -and $_.IsText})
    if($receiptPin.Count -ne 1 -or $receiptPin[0].SHA256 -cne $Plan.ExpectedBuildReceiptSHA256){throw 'Publication receipt pin differs.'}
    $sourceRoot=Split-Path $Build.Runner -Parent;$responseRoot=Split-Path $Build.PreparedRoot -Parent
    $paths=[ordered]@{PublicationWiring=(Join-Path $sourceRoot 'prepare_message_publication.py');
        PublicationSource=(Join-Path $sourceRoot 'native_message_publication.inc');PreparedCLI=(Join-Path $Build.PreparedRoot 'zonetool.cpp');
        MainResponse=(Join-Path $responseRoot 'main.obj.rsp');CLIResponse=(Join-Path $responseRoot 'zonetool11.obj.rsp');LinkResponse=(Join-Path $responseRoot 'link.rsp')}
    if($zombies){
        $paths.ObserverSource=Join-Path $sourceRoot 'native_catalog_zombies_observation.inc'
        $paths.ObserverAdapter=Join-Path $sourceRoot 'prepare_catalog_zombies_observation.py'
    }
    foreach($name in $paths.Keys) {
        $limit=if($name -cin @('PublicationSource','ObserverSource','ObserverAdapter')){16KB}elseif($name -ceq 'LinkResponse'){256KB}elseif($name -ceq 'PreparedCLI' -and ($zombies -or ((Get-T7CatalogueOperation $Plan) -ceq 'ResidentExportV1' -and (Get-T7SelectedStreamedExport $Plan)))){128KB}else{64KB}
        if($profile.$name.Path -cne $paths[$name] -or $profile.$name.Bytes -gt $limit){throw 'Publication source/response path or bound differs.'}
    }
    if($zombies -and ($profile.ObserverSource.Bytes -ne 9668 -or
       $profile.ObserverSource.SHA256 -cne '50361fbd5deb38b7410e31b995b1dcd7cdf6e43f04dc81835ed213f74155d181' -or
       $profile.ObserverAdapter.Bytes -ne 7613 -or
       $profile.ObserverAdapter.SHA256 -cne '1bf133356025893ff59c4d3de7e3614ac60f00a098f16b4b707e0eaa012da445')){
        throw 'Reviewed Catalogue C observer source pins differ.'
    }
    if($zombies){Assert-T7CatalogueZombiesSourceTransition $Build}
    foreach($rows in @(@{Value=@($Build.Stages)},@{Value=@($Receipt.Stages)})) {
        if($rows.Value.Count -ne 3 -or ($rows.Value.Name -join '|') -cne 'main|zonetool11|link' -or
           ($rows.Value.Stage -join '|') -cne 'Compile|Compile|Link'){throw 'Publication requires two actual Compile stages then Link.'}
    }
    for($index=0;$index -lt 3;$index++) {
        $stage=$Build.Stages[$index];$proof=$Receipt.Stages[$index];$stageRoot=Join-Path $Build.RunRoot $stage.Name
        $names=@(if($index -eq 2){'zonetool-t7.exe','zonetool-t7.pdb','zonetool-t7.lib','zonetool-t7.exp'}
            else{($stage.Name+'.obj'),'compile.pdb','dependencies.json'})
        if(($stage.Artifacts -join '|') -cne ($names -join '|') -or @($proof.Artifacts).Count -ne $names.Count){throw 'Publication artifact guards differ.'}
        if($proof.PlanSHA256 -cne $Plan.ExpectedBuildPlanSHA256 -or !(Test-T7CatalogueInteger $proof.ExitCode 0) -or
           $proof.TreeClosureConfirmed -isnot [bool] -or !$proof.TreeClosureConfirmed){throw 'Publication compile/link proof is not successful and closed.'}
        $response=$profile.(@('MainResponse','CLIResponse','LinkResponse')[$index])
        $image=if($index -eq 2){Join-Path (Split-Path $Build.Compiler -Parent) 'link.exe'}else{$Build.Compiler}
        if($stage.Image -cne $image -or @($stage.Arguments).Count -ne 1 -or $stage.Arguments[0] -cne ('@'+$response.Path)){throw 'Publication compiler/response command differs.'}
        foreach($name in $names) {
            $path=Join-Path $stageRoot $name;Assert-H1Path $path
            $pins=@($proof.Artifacts|Where-Object Path -CEQ $path)
            if($pins.Count -ne 1 -or !(Test-T7CatalogueInteger $pins[0].Bytes 256MB) -or $pins[0].Bytes -le 0 -or
               $pins[0].SHA256 -cnotmatch '\A[0-9a-f]{64}\z'){throw 'Publication artifact metadata differs.'}
            if($name -ceq 'dependencies.json') {
                Assert-T7CatalogueTextPin $pins[0] $Plan.Bindings
                $deps=Read-H1SmallJson $path 1MB
                $source=$profile.(@('PreparedMain','PreparedCLI')[$index]).Path
                if([IO.Path]::GetFullPath($deps.Data.Source) -ine $source){throw 'Publication compiler dependencies identify a different TU.'}
            }
        }
        if($index -lt 2) {
            $text=[IO.File]::ReadAllText($response.Path)
            if(($text.TrimEnd("`r","`n") -split "`n").Count -ne 1 -or $text.Contains('@')){throw 'Publication requires one direct compile response.'}
            $arguments=Split-T7CatalogueResponseArguments $text.TrimEnd("`r","`n")
            Assert-T7CatalogueResponseOutputs $arguments ([ordered]@{Fo=(Join-Path $stageRoot ($stage.Name+'.obj'));
                Fd=(Join-Path $stageRoot 'compile.pdb');sourceDependencies=(Join-Path $stageRoot 'dependencies.json')})
            $source=$profile.(@('PreparedMain','PreparedCLI')[$index]).Path
            if(!$arguments.Count -or $arguments[-1] -cne $source){throw 'Publication response compiles a different TU.'}
        }
    }
    $lines=@([IO.File]::ReadAllText($profile.LinkResponse.Path).TrimEnd("`r","`n") -split "`r?`n")
    if($lines.Count -ne 414 -or $lines[0] -match '(?i)\.obj\b|@'){throw 'Publication requires exactly 413 direct link objects.'}
    Assert-T7CatalogueResponseOutputs (Split-T7CatalogueResponseArguments $lines[0]) ([ordered]@{
        OUT=(Join-Path $Build.RunRoot 'link/zonetool-t7.exe');PDB=(Join-Path $Build.RunRoot 'link/zonetool-t7.pdb');
        IMPLIB=(Join-Path $Build.RunRoot 'link/zonetool-t7.lib')})
    $objects=[Collections.Generic.List[string]]::new();$unique=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($line in $lines[1..413]) {
        if($line -notmatch '^"([^"\r\n]+\.obj)"$' -or !$unique.Add($Matches[1])){throw 'Publication link object is indirect or duplicated.'}
        $objects.Add($Matches[1])
    }
    foreach($name in 'main','zonetool11','xpak') {
        $matches=@($objects|Where-Object {[IO.Path]::GetFileName($_) -ieq ($name+'.obj')})
        $expected=if($name -ceq 'xpak'){Join-Path $retained[0] 'xpak.obj'}else{Join-Path (Join-Path $Build.RunRoot $name) ($name+'.obj')}
        if($matches.Count -ne 1 -or $matches[0] -cne $expected){throw 'Publication link must consume both fresh objects and exact retained xpak.'}
    }
    if($Plan.CandidateSource -cne (Join-Path $Build.RunRoot 'link/zonetool-t7.exe')){throw 'Publication candidate is not the new link output.'}
    if($zombies){
        Assert-T7CatalogueZombiesObservationPlan $Plan
        Assert-T7ResidentMultiSurfaceBuild $Plan $Receipt $Build
        return
    }
    if($Plan.PSObject.Properties['ResidentSurfaceCountDiagnostic'] -or $reuse.PSObject.Properties['ResidentSurfaceCountDiagnostic']){
        Assert-T7ResidentExportDiagnosticBuild $Plan $Receipt $Build
    }
    if($Plan.PSObject.Properties['ResidentMultiSurfaceV2'] -or $reuse.PSObject.Properties['ResidentMultiSurfaceV2']){
        Assert-T7ResidentMultiSurfaceBuild $Plan $Receipt $Build
    }
}
function Get-T7CatalogueZombiesBuildPins($Plan) {
    Assert-T7CatalogueZombiesObservationPlan $Plan
    if($Plan.ExpectedBuildPlanSHA256 -cne '627f3aacf6ef892af2a7bc94c00ad0f40e811649bbdf2aa49aecad6569930a15' -or
       $Plan.ExpectedBuildReceiptSHA256 -cne '5f817f2f3f24c04868d022b41a3b68da492b75818816c37bb99eb1f6c8805051' -or
       $Plan.CandidateBytes -ne 21925376 -or
       $Plan.CandidateSHA256 -cne '88f2147de79e696d3342f4e838cf5b7b8b25da29cddea41def9395b6933342c8'){
        throw 'Exact actual Catalogue C build and candidate required.'
    }
    $prepared=Join-Path (Split-Path $Plan.BuildPlan -Parent) 'prepared'
    $source=Split-Path (Split-Path (Split-Path $Plan.BuildPlan -Parent) -Parent) -Parent
    $hostRoot=Join-Path $source 'runtime/catalogue-c-original-host-a';$pins=[ordered]@{}
    foreach($row in @(
        @('BuildPlan',$Plan.BuildPlan,370846,'627f3aacf6ef892af2a7bc94c00ad0f40e811649bbdf2aa49aecad6569930a15'),
        @('BuildReceipt',$Plan.BuildReceipt,25317,'5f817f2f3f24c04868d022b41a3b68da492b75818816c37bb99eb1f6c8805051'),
        @('Header',(Join-Path $prepared 't7_iw7_resident_model.hpp'),21290,'857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4'),
        @('SourceReceipt',(Join-Path $source 'source-workspace.json'),311606,'63b4d81d83bd5121272ca477290c43d7d6f0f24c7c25401bde030c8f7ec86f3d'),
        @('OriginalEntry',(Join-Path $hostRoot 'entry.json'),1161,'c6a66476f87c799e2d1d7e420e5fd72db2d41a80da8e109b23b093a2c189b741'),
        @('OriginalHostCompletion',(Join-Path $hostRoot 'completion.json'),449,'58d0b704033d7f5c6b958c588587f7e80d6ffd3d75f1d78a00a153ed24e759a0'),
        @('ActualToolReturn',(Join-Path $hostRoot 'tool-return.local.json'),546,'7271b7f5de9193069ca660dc7910a1d2caee68367836a945e51fc9a361512849'),
        @('Inventory',(Join-Path $hostRoot 'inventory.local.json'),2800,'9a39f98a8be8ea2c6b66f1afc97e095b22b9562e52197f89337eff43b55a703f'),
        @('BuildCompletion',(Join-Path $hostRoot 'build-completion.local.json'),2433,'5fbaec983b62f206c8b568384e0770f79db4d8ef0f54e1027c556f09740f7c9e'),
        @('Bundle',(Join-Path $hostRoot 'closed-bundle.local.json'),2613,'d51071803aa7f95948439ffde769c0918c0509734935aedc653b47759613c496'))){
        $pin=[pscustomobject]@{Path=$row[1];Bytes=$row[2];SHA256=$row[3]}
        Assert-T7CatalogueTextPin $pin $Plan.Bindings;$pins[$row[0]]=$pin
    }
    $pins
}
function Assert-T7CatalogueZombiesBuildClosure($Plan,$Receipt,$Build,$Pins) {
    $source=Read-H1SmallJson $Pins.SourceReceipt.Path 512KB
    if($source.schema -cne 'iw7.source-workspace/1' -or
       $source.revisions.'x64-zt-extensions' -cne 'fa45c395597697843053ffc23195320dca6ae73d' -or
       $source.revisions.'iw7-mod-components' -cne '2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1'){throw 'Exact C compilation source provenance required.'}
    $entry=Read-H1SmallJson $Pins.OriginalEntry.Path 2KB;$hostProof=Read-H1SmallJson $Pins.OriginalHostCompletion.Path 2KB
    $tool=Read-H1SmallJson $Pins.ActualToolReturn.Path 2KB;$inventory=Read-H1SmallJson $Pins.Inventory.Path 4KB
    $completion=Read-H1SmallJson $Pins.BuildCompletion.Path 4KB;$bundle=Read-H1SmallJson $Pins.Bundle.Path 4KB
    if($entry.Schema -cne 'iw7.t7-c-build-own-host/1' -or $hostProof.Schema -cne 'iw7.t7-c-build-own-host-completion/1' -or
       $tool.Schema -cne 'iw7.t7-c-build-tool-return/1' -or $inventory.Schema -cne 'iw7.t7-c-build-inventory/1' -or
       $completion.Schema -cne 'iw7.t7-c-native-build-completion/1' -or $bundle.Schema -cne 'iw7.t7-c-build-closed-bundle/1'){
        throw 'Exact original C closure schemas required.'
    }
    foreach($proof in @($entry,$hostProof,$tool,$inventory,$completion,$bundle)){
        if($proof.PlanSHA256 -cne $Plan.ExpectedBuildPlanSHA256){throw 'C original evidence plan differs.'}
    }
    foreach($proof in @($entry,$inventory,$completion,$bundle)){
        if($proof.SourceRevision -cne $source.revisions.'x64-zt-extensions'){throw 'C closure source revision differs.'}
    }
    foreach($proof in @($entry,$hostProof,$tool)){
        if($proof.HostPID -ne 24984 -or ([datetimeoffset]$proof.HostCreatedUtc).UtcTicks -ne
           ([datetimeoffset]'2026-10-14T00:02:39.0260276Z').UtcTicks){throw 'Exact original C host identity required.'}
    }
    if($entry.PlanPath -cne $Pins.BuildPlan.Path -or $entry.Runner -cne $Build.Runner -or $entry.HostImage -cne $tool.HostImage -or
       (@($entry.Arguments) -join '|') -cne (@('-PlanPath',$Pins.BuildPlan.Path,'-PlanSHA256',$Pins.BuildPlan.SHA256,'-Run') -join '|') -or
       $hostProof.Status -cne 'Passed' -or $null -ne $hostProof.Failure -or $hostProof.GuardCount -ne 0 -or
       $tool.Source -cne 'observed_tool_result' -or $tool.SessionId -ne 73114 -or $tool.ChunkId -cne '2216da' -or $tool.ExitCode -ne 0 -or
       $completion.Status -cne 'Passed' -or $completion.FinishedUtc -cne $Receipt.FinishedUtc -or
       $inventory.ObservedRegistryLeaseCount -ne 0 -or @($inventory.ObservedRegistryScopePaths).Count -ne 0 -or
       $bundle.MemberCount -ne 6 -or @($bundle.Members).Count -ne 6){throw 'Exact C actual host/tool/build completion required.'}
    foreach($proof in @(@{Object=$hostProof;Fields=@('OriginalContextClosed','LeaseAbsent','CanExit')},
        @{Object=$tool;Fields=@('Completed')},@{Object=$completion;Fields=@('InputsReverified','TreeClosureConfirmed','LeaseReleased')},
        @{Object=$inventory;Fields=@('OriginalIdentitiesAbsent','OwnBuildLeaseAbsent')})){
        foreach($name in $proof.Fields){if($proof.Object.$name -isnot [bool] -or !$proof.Object.$name){throw 'C original closure incomplete.'}}
    }
    foreach($proof in @(@{Object=$entry;Fields=@('ActualNativeStarted','CandidateExecutionRequested')},
        @{Object=$hostProof;Fields=@('CandidateExecutionRequested')},@{Object=$tool;Fields=@('CandidateExecuted')},
        @{Object=$inventory;Fields=@('OpaqueContentRead')},@{Object=$completion;Fields=@('CandidateExecuted','Quarantined','OpaqueContentReadAfterRelease')},
        @{Object=$bundle;Fields=@('CandidateExecuted','OpaqueContentReadAfterRelease')})){
        foreach($name in $proof.Fields){if($proof.Object.$name -isnot [bool] -or $proof.Object.$name){throw 'C build evidence overclaims its scope.'}}
    }
    $members=[ordered]@{ActualBuildReceipt=$Pins.BuildReceipt;OriginalEntry=$Pins.OriginalEntry;
        OriginalHostCompletion=$Pins.OriginalHostCompletion;ActualToolReturn=$Pins.ActualToolReturn;Inventory=$Pins.Inventory;BuildCompletion=$Pins.BuildCompletion}
    foreach($role in $members.Keys){$pin=$members[$role]
        if(@($bundle.Members|Where-Object {$_.Role -ceq $role -and $_.Path -ceq $pin.Path -and $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256}).Count -ne 1){throw 'C bundle member differs.'}
    }
    if(@($completion.StageClosure).Count -ne 3 -or @($completion.LinkArtifacts).Count -ne 4 -or @($inventory.Identities).Count -ne 7){throw 'Exact C stage/artifact/identity counts required.'}
    for($i=0;$i -lt 3;$i++){
        $stage=$Receipt.Stages[$i];$snapshot=$stage.LastOriginalSnapshot;$closed=$completion.StageClosure[$i]
        if($stage.Identity.PID -ne @(25568,22536,4424)[$i] -or $snapshot.RootExited -isnot [bool] -or !$snapshot.RootExited -or
           $snapshot.RootExitCode -ne 0 -or $snapshot.ActiveProcesses -ne 0 -or $snapshot.PID -ne $stage.Identity.PID -or
           $snapshot.Image -cne $stage.Identity.Image -or ([datetimeoffset]$snapshot.CreatedUtc).UtcTicks -ne ([datetimeoffset]$stage.Identity.CreatedUtc).UtcTicks -or
           $closed.Name -cne $stage.Name -or $closed.ExitCode -ne 0 -or $closed.TreeClosureConfirmed -isnot [bool] -or !$closed.TreeClosureConfirmed -or
           $closed.OriginalJobActiveAfterStop -ne 0 -or $closed.OriginalJobMembersAfterStop -ne 0){throw 'Exact closed original C compiler/link jobs required.'}
    }
    foreach($artifact in $Receipt.Stages[2].Artifacts){
        if(@($completion.LinkArtifacts|Where-Object {$_.Path -ceq $artifact.Path -and $_.Bytes -eq $artifact.Bytes -and $_.SHA256 -ceq $artifact.SHA256}).Count -ne 1){throw 'C admitted artifact tuple differs.'}
    }
    if((@($inventory.Identities.PID) -join '|') -cne '24984|25568|24656|22536|2724|4424|17400' -or
       (@($inventory.Identities.Role) -join '|') -cne 'OriginalHost|main|main_VCTIP|zonetool11|zonetool11_VCTIP|link|link_VCTIP'){throw 'Exact C original PID inventory required.'}
    $expected=@(@{Image=$entry.HostImage;Created=$entry.HostCreatedUtc})
    for($i=0;$i -lt 3;$i++){
        $identity=$Receipt.Stages[$i].Identity;$expected+=@(@{Image=$identity.Image;Created=$identity.CreatedUtc})
        $expected+=@(@{Image=(Join-Path (Split-Path $identity.Image -Parent) 'vctip.exe');
            Created=@('2026-10-14T00:02:52.0758494Z','2026-10-14T00:02:57.7539086Z','2026-10-14T00:03:03.2204821Z')[$i]})
    }
    for($i=0;$i -lt 7;$i++){
        if($inventory.Identities[$i].Image -ine $expected[$i].Image -or
           ([datetimeoffset]$inventory.Identities[$i].CreatedUtc).UtcTicks -ne ([datetimeoffset]$expected[$i].Created).UtcTicks){throw 'C inventory original creation identity differs.'}
    }
    foreach($identity in $inventory.Identities){
        foreach($name in 'PIDCurrentlyPresent','OriginalIdentityPresent'){if($identity.$name -isnot [bool] -or $identity.$name){throw 'C original inventory is not absent.'}}
    }
    if(([datetimeoffset]$entry.CapturedUtc).UtcTicks -ge ([datetimeoffset]$Receipt.Stages[0].Identity.CreatedUtc).UtcTicks -or
       ([datetimeoffset]$hostProof.CapturedUtc).UtcTicks -lt ([datetimeoffset]$Receipt.FinishedUtc).UtcTicks -or
       ([datetimeoffset]$tool.RecordedUtc).UtcTicks -lt ([datetimeoffset]$hostProof.CapturedUtc).UtcTicks -or
       ([datetimeoffset]$inventory.CapturedUtc).UtcTicks -lt ([datetimeoffset]$tool.RecordedUtc).UtcTicks -or
       ([datetimeoffset]$bundle.RecordedUtc).UtcTicks -lt ([datetimeoffset]$inventory.CapturedUtc).UtcTicks){throw 'C original lifecycle ordering differs.'}
}
function Get-T7CatalogueFileId([string]$Path) { [IW7HudFileIdentity]::Read($Path) }
function Open-T7CatalogueV3Pin($Plan,$Pin,[scriptblock]$DefaultReader) {
    if((Get-T7CatalogueBootstrapPolicy $Plan) -cne 'QualifiedCollectionV3'){throw 'Explicit V3 reader policy required.'}
    # Revalidate the complete collection before returning any guarded source or
    # alias. The runner still performs original-file-ID admission before aliases.
    $items=@(Get-T7CatalogueBootstraps $Plan)
    $match=@($items|Where-Object {$Pin.Path -ceq $_.Path -or $Pin.Path -ceq (Join-Path $Plan.WorkingDirectory $_.RelativePath)})
    if(!$match.Count){return (& $DefaultReader $Pin)}
    if($match.Count -ne 1 -or !(Test-T7CatalogueInteger $Pin.Bytes 512MB) -or
       $Pin.Bytes -ne $match[0].Bytes -or $Pin.SHA256 -cne $match[0].SHA256 -or
       ($Pin.PSObject.Properties['IsText'] -and ($Pin.IsText -isnot [bool] -or $Pin.IsText))){throw 'Exact V3 bootstrap source/alias pin required.'}
    Assert-H1Path $Pin.Path
    $metadata=Get-Item -LiteralPath $Pin.Path
    if($metadata.PSIsContainer -or $metadata.Length -ne $Pin.Bytes){throw 'V3 bound input metadata differs before open.'}
    $guard=[IO.FileStream]::new($Pin.Path,'Open','Read','Read')
    try {
        if($guard.Length -ne $Pin.Bytes){throw 'V3 bound input length differs.'}
        # The catalogue needs a retained hash guard, not a byte snapshot. Hash
        # through the stream; do not allocate one 512 MiB array per binding.
        $hash=[Security.Cryptography.SHA256]::Create()
        try{$actual=[Convert]::ToHexString($hash.ComputeHash($guard)).ToLowerInvariant()}finally{$hash.Dispose()}
        if($actual -cne $Pin.SHA256 -or $guard.Length -ne $Pin.Bytes){throw 'V3 bound input hash/length differs.'}
        Assert-H1Path $Pin.Path
        $guard.Position=0
        return $guard
    }catch{$guard.Dispose();throw}
}
function Open-T7CatalogueZone($Zone,$Context) {
    $spec=Get-T7CatalogueZoneSpec ([IO.Path]::GetFileNameWithoutExtension($Zone.Path))
    if([IO.Path]::GetFileName($Zone.Path) -cne $spec.FileName -or
       !(Test-T7CatalogueInteger $Zone.Bytes $spec.Bytes) -or $Zone.Bytes -ne $spec.Bytes){throw 'Observed FF length/name differs.'}
    Assert-T7CatalogueMetadata $Zone
    # The only unsealed payload. Hold this exact source open before observing its hash.
    $guard=[IO.FileStream]::new($Zone.Path,'Open','Read','Read')
    try {
        Assert-T7CatalogueMetadata $Zone
        if($guard.Length -ne $spec.Bytes){throw 'Observed FF length differs.'}
        $fileId=Get-T7CatalogueFileId $Zone.Path
        $hash=[Security.Cryptography.SHA256]::Create()
        try{$sha=[Convert]::ToHexString($hash.ComputeHash($guard)).ToLowerInvariant()}finally{$hash.Dispose()}
        Assert-T7CatalogueMetadata $Zone
        if($guard.Length -ne $Zone.Bytes -or (Get-T7CatalogueFileId $Zone.Path) -cne $fileId){throw 'Observed FF identity changed.'}
        $guard.Position=0;$Context.Guards.Add($guard)
        [pscustomobject]@{Path=$Zone.Path;Bytes=$Zone.Bytes;SHA256=$sha;IsText=$false;FileId=$fileId;HashProvenance='ObservedUnderLeaseNotDepotVerified'}
    }catch{$guard.Dispose();throw}
}
function New-T7CatalogueAlias($Pin,[string]$Destination,$Context) {
    Assert-H1Path $Destination
    if(Test-Path -LiteralPath $Destination){throw 'Alias destination already exists.'}
    $sourceId=Get-T7CatalogueFileId $Pin.Path
    New-Item -ItemType HardLink -Path $Destination -Target $Pin.Path -ErrorAction Stop|Out-Null
    $guard=Open-H1Pin ([pscustomobject]@{Path=$Destination;Bytes=$Pin.Bytes;SHA256=$Pin.SHA256})
    $Context.Guards.Add($guard)
    $aliasId=Get-T7CatalogueFileId $Destination
    if($sourceId -cne $aliasId){throw 'Source/alias file IDs differ.'}
    [pscustomobject]@{Path=$Destination;Source=$Pin.Path;Bytes=$Pin.Bytes;SHA256=$Pin.SHA256;FileId=$aliasId}
}
function New-T7CatalogueStart($Plan) {
    $start=New-T7PrepatchStart $Plan # Environment setup only; diagnostic is not invoked.
    $zoneSpec=Get-T7CataloguePlanZoneSpec $Plan
    $start.ArgumentList.Clear();$start.ArgumentList.Add('-t7-iw7-catalog');$start.ArgumentList.Add($zoneSpec.Name)
    if((Get-T7CatalogueOperation $Plan) -ceq 'ResidentExportV1'){
        Assert-T7ResidentExportRequest $Plan.ExportRequest
        $streamed=[bool](Get-T7SelectedStreamedExport $Plan)
        $command=if($streamed){'-t7-iw7-model-streamed-v1'}elseif((Get-T7ResidentExportVersion $Plan) -eq 2){'-t7-iw7-model-v2'}else{'-t7-iw7-model'}
        $start.ArgumentList.Clear()
        foreach($argument in @($command,$Plan.ExportRequest.zone,$Plan.ExportRequest.model,'0')){$start.ArgumentList.Add($argument)}
        if($streamed){$start.ArgumentList.Add('streamed-request.json')}
    }
    $start
}
function Assert-T7CatalogueFields($Value,[string[]]$Fields) {
    if($null -eq $Value -or $Value -isnot [pscustomobject] -or
       (@($Value.PSObject.Properties.Name|Sort-Object) -join '|') -cne (@($Fields|Sort-Object) -join '|')){throw 'Exact catalogue fields required.'}
}
function Test-T7CatalogueInteger($Value,[long]$Maximum) {
    ($Value -is [int] -or $Value -is [long]) -and $Value -ge 0 -and $Value -le $Maximum
}
function Get-T7CatalogueOutcome($Report,[Nullable[int]]$ExitCode,$ZoneName='mp_freerun_04') {
    $zoneSpec=Get-T7CatalogueZoneSpec $ZoneName
    if($null -eq $Report){return 'NoCatalogue'}
    $falseFields=@('truncated','asset_zone_ownership_verified','zonetool_xpak_helper_reads_allowed','engine_io_verified','geometry_verified','runtime_verified','ready')
    Assert-T7CatalogueFields $Report (@('schema','requested_zone','provenance','model_count','name_bytes','models')+$falseFields)
    if($Report.schema -cne 'iw7.t7-iw7-model-catalog/1' -or $Report.requested_zone -isnot [string] -or
       $Report.requested_zone -cne $zoneSpec.Name -or
       $Report.provenance -cne 'observed_during_requested_zone_load'){throw 'Catalogue request/provenance differs.'}
    foreach($field in $falseFields){if($Report.$field -isnot [bool] -or $Report.$field){throw 'Catalogue overclaims its scope.'}}
    if($Report.models -isnot [array] -or !(Test-T7CatalogueInteger $Report.model_count 1024) -or
       $Report.model_count -ne $Report.models.Count -or !(Test-T7CatalogueInteger $Report.name_bytes 256KB)){throw 'Catalogue count exceeds bound or differs.'}
    $previous=$null;$nameBytes=0
    foreach($row in $Report.models) {
        Assert-T7CatalogueFields $row @('name','reference','resolved_nondefault','counts')
        if($row.name -isnot [string] -or $row.name -cnotmatch '\A[\x20-\x7e]{1,255}\z' -or
           ($null -ne $previous -and [string]::CompareOrdinal($previous,$row.name) -ge 0)){throw 'Names must be bounded ASCII, sorted and unique.'}
        if($row.reference -isnot [bool] -or $row.reference -ne $row.name.StartsWith(',') -or
           $row.resolved_nondefault -isnot [bool]){throw 'Reference/resolution flags differ.'}
        if($row.resolved_nondefault) {
            if($row.reference){throw 'Reference alias cannot claim resolved counts.'}
            Assert-T7CatalogueFields $row.counts @('bones','roots','cosmetic_bones','lods')
            foreach($name in 'bones','roots','cosmetic_bones','lods') {
                $max=if($name -ceq 'cosmetic_bones'){65535}else{255}
                if(!(Test-T7CatalogueInteger $row.counts.$name $max)){throw 'Header count width differs.'}
            }
        }elseif($null -ne $row.counts){throw 'Unresolved row cannot claim counts.'}
        $nameBytes+=$row.name.Length+1;$previous=$row.name
    }
    if($nameBytes -ne $Report.name_bytes){throw 'Name byte count differs.'}
    if($ExitCode -ne 0){return 'ValidCatalogueFromFailedProcess'}
    if($Report.model_count -eq 0){return 'EmptyCatalogue'}
    'CatalogueWithNames'
}
function Read-T7CatalogueReport($Plan,$State,$Context) {
    $path=Join-Path (Join-Path $Plan.WorkingDirectory $Plan.OutputKey) 'catalog.json'
    if(!(Test-Path -LiteralPath $path)){return 'NoCatalogue'}
    $State.CatalogueOutcome='CataloguePresentUnqualified'
    Assert-H1Path $path
    $size=(Get-Item -LiteralPath $path).Length
    if($size -le 0 -or $size -gt 512KB){throw 'Catalogue JSON size refused.'}
    $pin=[pscustomobject]@{Path=$path;Bytes=$size;SHA256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
    $Context.Guards.Add((Open-H1Pin $pin));$State.Report=$pin
    $report=Read-H1SmallJson $path 512KB
    $outcome=Get-T7CatalogueOutcome $report $State.ExitCode (Get-T7CataloguePlanZoneSpec $Plan).Name
    $State.ModelCount=$report.model_count
    $outcome
}
function ConvertFrom-T7CatalogueTrace([string]$Text) {
    if($Text.Length -eq 0){return [pscustomobject]@{Outcome='NoTrace';Events=@()}}
    if([Text.Encoding]::UTF8.GetByteCount($Text) -ge 1536 -or !$Text.EndsWith("`n")){throw 'Trace stderr oversized or incomplete.'}
    $lines=$Text.Substring(0,$Text.Length-1).Split("`n")
    if($lines.Count -gt 6){throw 'Trace exceeds six one-shot events.'}
    $events=[Collections.Generic.List[object]]::new();$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $prefix='\A\[T7_CATALOG_TRACE\] schema=iw7\.t7-catalog-trace/1 phase='
    $tid='(0|[1-9][0-9]{0,9})'
    foreach($raw in $lines) {
        if($raw.Length+1 -ge 256){throw 'Trace line reaches 256 bytes.'}
        $line=$raw -creplace '\r$',''
        $enabled=[regex]::Match($line,($prefix+'enabled stdout_unbuffered=([01]) stderr_unbuffered=([01]) tid='+$tid+'\z'))
        if($enabled.Success) {
            $row=[pscustomobject]@{Phase='enabled';StdoutUnbuffered=($enabled.Groups[1].Value -ceq '1');StderrUnbuffered=($enabled.Groups[2].Value -ceq '1');ThreadId=[ulong]$enabled.Groups[3].Value}
        }else {
            $match=[regex]::Match($line,($prefix+'(before_post_unpack|after_post_unpack|before_entry_point|entry_point_return|exit_hook) code=(0|-?[1-9][0-9]{0,9}) tid='+$tid+' return_address=([0-9A-Fa-f]{16})\z'))
            if(!$match.Success){throw 'Unknown trace event or stderr format.'}
            $code=[long]$match.Groups[2].Value
            if($code -lt [int]::MinValue -or $code -gt [int]::MaxValue){throw 'Trace code exceeds signed int32.'}
            $row=[pscustomobject]@{Phase=$match.Groups[1].Value;Code=$code;ThreadId=[ulong]$match.Groups[3].Value;ReturnAddress=$match.Groups[4].Value}
            if($row.Phase -cin @('before_post_unpack','after_post_unpack','before_entry_point') -and $code -ne 0){throw 'Nonzero boundary trace code.'}
            if($row.Phase -cne 'exit_hook' -and $row.ReturnAddress -cne '0000000000000000'){throw 'Unexpected non-exit trace return address.'}
        }
        if($row.ThreadId -gt [uint]::MaxValue -or !$seen.Add($row.Phase)){throw 'Trace thread ID or duplicate event differs.'}
        $events.Add($row)
    }
    [pscustomobject]@{Outcome=$(if($seen.Contains('enabled')){'TraceObserved'}else{'TracePartial'});Events=@($events.ToArray())}
}
function Read-T7CatalogueTrace($Plan,$State,$Context) {
    $profile=Get-T7CatalogueCandidateProfile $Plan
    if($profile -ceq 'ordinary-d2'){return}
    $State.TraceOutcome='NoTrace'
    $hasContext=$profile -cin @('t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c')
    $hasCallers=$profile -cin @('t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c')
    $hasMessage=$profile -cin @('t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c')
    if($hasContext){$State.ExitContextOutcome='Absent';$State.ExitContext=[ordered]@{Captures=@();IncompleteTrailingLine=$false}}
    if($hasCallers){$State.CallersOutcome='Absent';$State.Callers=[ordered]@{Captures=@();IncompleteTrailingLine=$false}}
    if($hasMessage){$State.MessageOutcome='Absent';$State.Message=[ordered]@{Captures=@();IncompleteTrailingLine=$false;ExitCorrelated=$false}}
    if($profile -ceq 't7-zombies-catalogue-observation-c'){$State.ZombiesObservations=@();$State.ZombiesObservationBytes=0}
    $path=Join-Path $Plan.StageRoot 'stderr.log'
    if(!(Test-Path -LiteralPath $path)){return}
    $State.TraceOutcome='TracePresentUnqualified'
    Assert-H1Path $path
    $size=(Get-Item -LiteralPath $path).Length
    if($hasContext -and $size -gt 0){$State.ExitContextOutcome='PresentUnqualified'}
    if($hasCallers -and $size -gt 0){$State.CallersOutcome='PresentUnqualified'}
    if($hasMessage -and $size -gt 0){$State.MessageOutcome='PresentUnqualified'}
    Assert-T7CatalogueTraceSize $profile $size
    $pin=[pscustomobject]@{Path=$path;Bytes=$size;SHA256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
    $Context.Guards.Add((Open-H1Pin $pin));$State.TraceReport=$pin
    $text=[Text.UTF8Encoding]::new($false,$true).GetString([IO.File]::ReadAllBytes($path))
    $result=switch($profile){
        't7-catalog-message'{ConvertFrom-T7CatalogueMessage $text}
        't7-catalog-message-publication'{ConvertFrom-T7CatalogueMessage $text}
        't7-zombies-catalogue-observation-c'{ConvertFrom-T7CatalogueZombiesObservation $text}
        't7-catalog-callers'{ConvertFrom-T7CatalogueCallers $text}
        't7-catalog-exit-context'{ConvertFrom-T7CatalogueExitContext $text}
        default{ConvertFrom-T7CatalogueTrace $text}
    }
    $State.TraceOutcome=$result.Outcome;$State.TraceEvents=$result.Events
    if($profile -ceq 't7-zombies-catalogue-observation-c'){
        $State.ZombiesObservations=$result.ZombiesObservations;$State.ZombiesObservationBytes=$result.ZombiesObservationBytes
    }
    if($hasContext){$State.ExitContextOutcome=$result.ContextOutcome;$State.ExitContext=$result.Context}
    if($hasCallers){$State.CallersOutcome=$result.CallersOutcome;$State.Callers=$result.Callers}
    if($hasMessage){$State.MessageOutcome=$result.MessageOutcome;$State.Message=$result.Message}
}
function Assert-T7CatalogueTraceSize([string]$Profile,[long]$Bytes) {
    if(($Profile -ceq 't7-catalog-trace' -and $Bytes -ge 1536) -or
       ($Profile -ceq 't7-catalog-exit-context' -and $Bytes -gt 4096) -or
       ($Profile -cin @('t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication') -and $Bytes -gt 8192) -or ($Profile -ceq 't7-zombies-catalogue-observation-c' -and $Bytes -gt 16384)){throw 'Trace stderr cap exceeded.'}
}
function Get-T7CatalogueContextNumber($Match,[string]$Name,[ulong]$Maximum=[uint]::MaxValue) {
    $value=[ulong]::Parse($Match.Groups[$Name].Value,[Globalization.CultureInfo]::InvariantCulture)
    if($value -gt $Maximum){throw 'Exit context integer exceeds field width.'}
    $value
}
function ConvertFrom-T7CatalogueExitLine([string]$Line) {
    $dec='(0|[1-9][0-9]{0,19})';$ptr='[0-9A-Fa-f]{16}'
    $prefix='\A\[T7_CATALOG_EXIT\] schema=iw7\.t7-catalog-exit-context/1 kind='
    $head=$prefix+'(?<kind>memory|stack|function) code=(?<code>0|-?[1-9][0-9]{0,9}) tid=(?<tid>'+ $dec +') ra=(?<ra>'+ $ptr +') '
    $prefixMatch=[regex]::Match($Line,$head)
    if(!$prefixMatch.Success){throw 'Unknown exit context prefix or correlation fields.'}
    $kind=$prefixMatch.Groups['kind'].Value
    $tail=switch($kind) {
        memory {'status=(?<status>ok|module_missing|module_mismatch|address_invalid|query_failed|region_invalid|read_failed|partial|exception) start=(?<start>'+$ptr+') requested=256 read=(?<read>'+$dec+') module=(?<module>'+$ptr+') allocation=(?<allocation>'+$ptr+') region=(?<region>'+$ptr+') region_size=(?<region_size>'+$dec+') state=(?<state>'+$dec+') protect=(?<protect>'+$dec+') type=(?<type>'+$dec+') error=(?<error>'+$dec+') data=(?<data>-|[0-9A-F]+)\z'}
        stack {'status=(?<status>ok|empty|invalid_count|exception) count=(?<count>'+$dec+') error=(?<error>'+$dec+') addresses=(?<addresses>-|[0-9A-F]{16}(,[0-9A-F]{16}){0,7})\z'}
        function {'status=(?<status>ok|not_found|module_mismatch|query_failed|region_invalid|read_failed|partial|record_invalid|exception) image=(?<image>'+$ptr+') record=(?<record>'+$ptr+') read=(?<read>'+$dec+') begin=(?<begin>[0-9A-F]{8}) end=(?<end>[0-9A-F]{8}) unwind=(?<unwind>[0-9A-F]{8}) error=(?<error>'+$dec+')\z'}
    }
    $m=[regex]::Match($Line,$head+$tail)
    if(!$m.Success){throw 'Unknown exit context status or field format.'}
    $code=[long]$m.Groups['code'].Value
    if($code -lt [int]::MinValue -or $code -gt [int]::MaxValue){throw 'Exit context code exceeds int32.'}
    $ra=$m.Groups['ra'].Value;$raValue=[Convert]::ToUInt64($ra,16)
    $row=[ordered]@{Kind=$kind;Code=$code;ThreadId=(Get-T7CatalogueContextNumber $m 'tid');ReturnAddress=$ra;
        Status=$m.Groups['status'].Value;Error=(Get-T7CatalogueContextNumber $m 'error')}
    switch($kind) {
        memory {
            foreach($field in 'start','module','allocation','region'){$row[$field]=$m.Groups[$field].Value}
            $row.Requested=256;$row.ReadBytes=Get-T7CatalogueContextNumber $m 'read' 256
            $row.RegionSize=Get-T7CatalogueContextNumber $m 'region_size' ([ulong]::MaxValue)
            foreach($field in 'state','protect','type'){$row[$field]=Get-T7CatalogueContextNumber $m $field}
            $row.DataHex=$m.Groups['data'].Value
            if(($row.ReadBytes -eq 0 -and $row.DataHex -cne '-') -or
               ($row.ReadBytes -gt 0 -and ($row.DataHex -ceq '-' -or $row.DataHex.Length -ne 2*$row.ReadBytes))){throw 'Exit memory data/read mismatch.'}
            if(($row.Status -ceq 'partial' -and ($row.ReadBytes -eq 0 -or $row.ReadBytes -eq 256)) -or
               ($row.Status -ceq 'read_failed' -and $row.ReadBytes -notin @(0,256)) -or
               ($row.Status -cnotin @('ok','partial','read_failed','exception') -and $row.ReadBytes -ne 0)){throw 'Exit memory status/read mismatch.'}
            if($row.Status -ceq 'ok') {
                $start=[Convert]::ToUInt64($row.start,16);$region=[Convert]::ToUInt64($row.region,16)
                if($row.ReadBytes -ne 256 -or $row.Error -ne 0 -or $raValue -lt 64 -or $start -ne $raValue-64 -or
                   [Convert]::ToUInt64($row.module,16) -ne 0x140000000L -or [Convert]::ToUInt64($row.allocation,16) -ne 0x140000000L -or
                   $row.state -ne 0x1000 -or ($row.protect -band 0x100) -ne 0 -or
                   ($row.protect -band 0xFF) -eq 1 -or ($row.protect -band 0xFF) -eq 0 -or $start -lt $region -or
                   $row.RegionSize -lt 256 -or ([decimal]$start-[decimal]$region) -gt ([decimal]$row.RegionSize-256)){throw 'Successful exit memory capture has inconsistent bounds.'}
            }
        }
        stack {
            $row.Count=Get-T7CatalogueContextNumber $m 'count' 8
            $value=$m.Groups['addresses'].Value
            $row.Addresses=@(if($value -cne '-'){$value.Split(',')})
            if($row.Addresses.Count -ne $row.Count -or ($row.Count -eq 0 -and $value -cne '-')){throw 'Exit stack address/count mismatch.'}
            if($row.Status -ceq 'ok' -and ($row.Count -eq 0 -or $row.Error -ne 0)){throw 'Successful exit stack capture is empty or failed.'}
            if($row.Status -cne 'ok' -and $row.Count -ne 0){throw 'Failed exit stack capture exposes addresses.'}
        }
        function {
            $row.Image=$m.Groups['image'].Value;$row.Record=$m.Groups['record'].Value
            $row.ReadBytes=Get-T7CatalogueContextNumber $m 'read' 12
            foreach($field in 'begin','end','unwind'){$row[$field]=[Convert]::ToUInt32($m.Groups[$field].Value,16)}
            if($row.ReadBytes -ne 12 -and ($row.begin -ne 0 -or $row.end -ne 0 -or $row.unwind -ne 0)){throw 'Incomplete runtime function copy exposes RVAs.'}
            if(($row.Status -ceq 'partial' -and ($row.ReadBytes -eq 0 -or $row.ReadBytes -eq 12)) -or
               ($row.Status -cin @('read_failed','record_invalid') -and $row.ReadBytes -notin @(0,12)) -or
               ($row.Status -cnotin @('ok','partial','read_failed','record_invalid','exception') -and $row.ReadBytes -ne 0)){throw 'Runtime function status/read mismatch.'}
            if($row.Status -cnotin @('ok','record_invalid') -and ($row.begin -ne 0 -or $row.end -ne 0 -or $row.unwind -ne 0)){throw 'Failed runtime function copy exposes RVAs.'}
            if($row.Status -ceq 'ok') {
                $base=[Convert]::ToUInt64($row.Image,16)
                if($row.ReadBytes -ne 12 -or $row.Error -ne 0 -or $base -ne 0x140000000L -or
                   [Convert]::ToUInt64($row.Record,16) -eq 0 -or $raValue -eq 0 -or $row.begin -ge $row.end -or
                   ([decimal]$raValue-1) -lt ([decimal]$base+$row.begin) -or ([decimal]$raValue-1) -ge ([decimal]$base+$row.end)){throw 'Successful runtime function capture does not contain RA-1.'}
            }
        }
    }
    [pscustomobject]$row
}
function ConvertFrom-T7CatalogueExitContext([string]$Text) {
    Assert-T7CatalogueTraceSize 't7-catalog-exit-context' ([Text.Encoding]::UTF8.GetByteCount($Text))
    if($Text -cmatch '[^\x20-\x7e\r\n]'){throw 'Exit context stderr must be ASCII without BOM.'}
    if(!$Text.Length){return [pscustomobject]@{Outcome='NoTrace';Events=@();ContextOutcome='Absent';Context=[ordered]@{Captures=@();IncompleteTrailingLine=$false}}}
    $complete=$Text.EndsWith("`n")
    $lines=if($complete){@($Text.Substring(0,$Text.Length-1).Split("`n"))}else{@($Text.Split("`n"))}
    if($lines.Count -gt 9){throw 'Exit context stderr exceeds nine lines.'}
    $markers=[Collections.Generic.List[string]]::new();$captures=[Collections.Generic.List[object]]::new()
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $prefix='[T7_CATALOG_EXIT] schema=iw7.t7-catalog-exit-context/1 kind='
    $exitSeen=$false;$incomplete=$false;$lastKind=-1
    for($i=0;$i -lt $lines.Count;$i++) {
        $raw=$lines[$i];$line=$raw -creplace '\r$',''
        if(!$complete -and $i -eq $lines.Count-1) {
            if(!$exitSeen -or $captures.Count -ge 3 -or (!$prefix.StartsWith($line,[StringComparison]::Ordinal) -and !$line.StartsWith($prefix,[StringComparison]::Ordinal))){throw 'Unrecognized incomplete exit context line.'}
            $incomplete=$true
            if($line.StartsWith($prefix,[StringComparison]::Ordinal)) {
                $kind=($line.Substring($prefix.Length) -split ' ',2)[0]
                $possible=@('memory','stack','function'|Where-Object {$_.StartsWith($kind,[StringComparison]::Ordinal)})
                if(!$possible.Count){throw 'Unknown incomplete exit context kind.'}
                if($kind -cin @('memory','stack','function')) {
                    $index=[array]::IndexOf(@('memory','stack','function'),$kind)
                    $cap=if($kind -ceq 'memory'){1024}else{512}
                    if($seen.Contains($kind) -or $index -le $lastKind -or $raw.Length -gt $cap){throw 'Duplicate, reordered or oversized incomplete exit context.'}
                }
            }
            continue
        }
        if($line.StartsWith('[T7_CATALOG_TRACE] ',[StringComparison]::Ordinal)) {
            $markers.Add($raw+"`n")
            if($line -cmatch ' phase=exit_hook '){$exitSeen=$true}
            continue
        }
        $row=ConvertFrom-T7CatalogueExitLine $line
        $cap=if($row.Kind -ceq 'memory'){1024}else{512}
        $index=[array]::IndexOf(@('memory','stack','function'),$row.Kind)
        if(!$exitSeen -or !$seen.Add($row.Kind) -or $index -le $lastKind -or $raw.Length+1 -gt $cap){throw 'Exit context order, duplicate or line bound differs.'}
        $lastKind=$index;$captures.Add($row)
    }
    $trace=ConvertFrom-T7CatalogueTrace ($markers -join '')
    if($captures.Count -or $incomplete) {
        $exit=@($trace.Events|Where-Object Phase -CEQ 'exit_hook')
        if($exit.Count -ne 1){throw 'Exit context has no matching exit_hook.'}
        foreach($row in $captures){if($row.Code -ne $exit[0].Code -or $row.ThreadId -ne $exit[0].ThreadId -or $row.ReturnAddress -ine $exit[0].ReturnAddress){throw 'Exit context correlation differs from exit_hook.'}}
    }
    $outcome=if(!$captures.Count -and !$incomplete){'Absent'}elseif($captures.Count -eq 3 -and !$incomplete -and !@($captures|Where-Object Status -CNE 'ok').Count){'Observed'}else{'Partial'}
    [pscustomobject]@{Outcome=$trace.Outcome;Events=$trace.Events;ContextOutcome=$outcome;
        Context=[ordered]@{Captures=@($captures.ToArray());IncompleteTrailingLine=$incomplete}}
}
function Assert-T7CatalogueCallerWindow($Row) {
    $base=0x140000000L;$ra=[Convert]::ToUInt64($Row.ReturnAddress,16)
    $start=[Convert]::ToUInt64($Row.Start,16);$region=[Convert]::ToUInt64($Row.Region,16)
    $begin=[decimal]$base+$Row.Begin;$end=[decimal]$base+$Row.End
    $regionEnd=[decimal]$region+$Row.RegionSize
    if($Row.RecordReadBytes -ne 12 -or [Convert]::ToUInt64($Row.Record,16) -eq 0 -or
       [Convert]::ToUInt64($Row.Module,16) -ne $base -or [Convert]::ToUInt64($Row.Image,16) -ne $base -or
       [Convert]::ToUInt64($Row.Allocation,16) -ne $base -or $Row.Begin -ge $Row.End -or
       ([decimal]$ra-1) -lt $begin -or ([decimal]$ra-1) -ge $end -or
       $Row.State -ne 0x1000 -or ($Row.Protect -band 0x100) -ne 0 -or
       ($Row.Protect -band 0xFF) -in @(0,1) -or $regionEnd -gt [decimal][ulong]::MaxValue -or
       ([decimal]$ra-1) -lt $region -or ([decimal]$ra-1) -ge $regionEnd){throw 'Caller code window lacks a qualified function or readable region.'}
    if($end-$begin -le 512 -and $begin -ge $region -and $end -le $regionEnd) {
        $expectedStart=$begin;$expectedEnd=$end;$scope='full'
    }else {
        $expectedStart=[Math]::Max([Math]::Max(([decimal]$ra-448),$begin),[decimal]$region)
        $expectedEnd=[Math]::Min([Math]::Min(([decimal]$ra+64),$end),$regionEnd);$scope='window'
    }
    if($expectedStart -gt ([decimal]$ra-1) -or $expectedEnd -le ([decimal]$ra-1) -or
       $expectedEnd-$expectedStart -gt 512 -or $start -ne $expectedStart -or
       $Row.Requested -ne $expectedEnd-$expectedStart -or $Row.Scope -cne $scope){throw 'Caller code window differs from the exact bounded intersection.'}
}
function ConvertFrom-T7CatalogueCallerLine([string]$Line) {
    $dec='(0|[1-9][0-9]{0,19})';$ptr='[0-9A-F]{16}'
    $pattern='\A\[T7_CATALOG_CALLER\] schema=iw7\.t7-catalog-callers/1 code=(?<code>0|-?[1-9][0-9]{0,9}) tid=(?<tid>'+$dec+') exit_ra=(?<exit_ra>'+$ptr+') index=(?<index>[0-2]) ra=(?<ra>'+$ptr+') '+
        'status=(?<status>ok|absent|stack_unavailable|module_missing|module_mismatch|query_failed|region_invalid|not_found|record_partial|record_read_failed|record_invalid|partial|read_failed|exception) frame=(?<frame>-1|[0-7]) '+
        'module=(?<module>'+$ptr+') image=(?<image>'+$ptr+') record=(?<record>'+$ptr+') record_read=(?<record_read>'+$dec+') '+
        'begin=(?<begin>[0-9A-F]{8}) end=(?<end>[0-9A-F]{8}) unwind=(?<unwind>[0-9A-F]{8}) start=(?<start>'+$ptr+') requested=(?<requested>'+$dec+') read=(?<read>'+$dec+') '+
        'scope=(?<scope>none|full|window) allocation=(?<allocation>'+$ptr+') region=(?<region>'+$ptr+') region_size=(?<region_size>'+$dec+') '+
        'state=(?<state>'+$dec+') protect=(?<protect>'+$dec+') type=(?<type>'+$dec+') error=(?<error>'+$dec+') data=(?<data>-|[0-9A-F]+)\z'
    $m=[regex]::Match($Line,$pattern)
    if(!$m.Success){throw 'Unknown caller record or field format.'}
    $code=[long]$m.Groups['code'].Value
    if($code -lt [int]::MinValue -or $code -gt [int]::MaxValue){throw 'Caller code exceeds int32.'}
    $row=[ordered]@{Code=$code;ThreadId=(Get-T7CatalogueContextNumber $m 'tid');ExitReturnAddress=$m.Groups['exit_ra'].Value;
        Index=[int]$m.Groups['index'].Value;ReturnAddress=$m.Groups['ra'].Value;Status=$m.Groups['status'].Value;
        Frame=[int]$m.Groups['frame'].Value;RecordReadBytes=(Get-T7CatalogueContextNumber $m 'record_read' 12);
        Requested=(Get-T7CatalogueContextNumber $m 'requested' 512);ReadBytes=(Get-T7CatalogueContextNumber $m 'read' 512);
        Scope=$m.Groups['scope'].Value;RegionSize=(Get-T7CatalogueContextNumber $m 'region_size' ([ulong]::MaxValue));DataHex=$m.Groups['data'].Value}
    foreach($field in 'module','image','record','start','allocation','region'){$row[$field]=$m.Groups[$field].Value}
    foreach($field in 'begin','end','unwind'){$row[$field]=[Convert]::ToUInt32($m.Groups[$field].Value,16)}
    foreach($field in 'state','protect','type','error'){$row[$field]=Get-T7CatalogueContextNumber $m $field}
    if($row.ReturnAddress -cne @('0000000140584FD8','00000001401DA015','0000000140526D02')[$row.Index]){throw 'Caller index/target differs.'}
    if($row.ReadBytes -gt $row.Requested -or ($row.ReadBytes -eq 0 -and $row.DataHex -cne '-') -or
       ($row.ReadBytes -gt 0 -and ($row.DataHex -ceq '-' -or $row.DataHex.Length -ne 2*$row.ReadBytes))){throw 'Caller data/read bounds differ.'}
    $hasRvas=$row.begin -ne 0 -or $row.end -ne 0 -or $row.unwind -ne 0
    if(($row.RecordReadBytes -ne 12 -and $hasRvas) -or
       ($row.Status -cnotin @('ok','partial','read_failed','record_invalid','region_invalid') -and $hasRvas)){throw 'Failed or incomplete caller function copy exposes RVAs.'}
    if(($row.Status -ceq 'record_partial' -and $row.RecordReadBytes -notin (1..11)) -or
       ($row.Status -cin @('record_read_failed','record_invalid','region_invalid') -and $row.RecordReadBytes -notin @(0,12)) -or
       ($row.Status -cin @('absent','stack_unavailable','module_missing','module_mismatch','query_failed','not_found') -and $row.RecordReadBytes -ne 0)){throw 'Caller function status/read differs.'}
    if($row.Requested -eq 0) {
        if($row.start -cne '0000000000000000' -or $row.Scope -cne 'none' -or $row.ReadBytes -ne 0){throw 'Caller without a code request has a window.'}
    }elseif($row.start -ceq '0000000000000000' -or $row.Scope -ceq 'none' -or
        $row.Status -cnotin @('ok','partial','read_failed','exception')){throw 'Caller pre-read refusal exposes a code request.'}
    if(($row.Status -ceq 'ok' -and ($row.Requested -eq 0 -or $row.ReadBytes -ne $row.Requested -or $row.error -ne 0)) -or
       ($row.Status -ceq 'partial' -and ($row.ReadBytes -eq 0 -or $row.ReadBytes -ge $row.Requested)) -or
       ($row.Status -ceq 'read_failed' -and $row.ReadBytes -notin @(0,$row.Requested)) -or
       ($row.Status -ceq 'read_failed' -and $row.Requested -eq 0 -and $row.error -ne 13)){throw 'Caller code status/read differs.'}
    if($row.Status -cin @('absent','stack_unavailable')) {
        if($row.Frame -ne -1 -or $row.RecordReadBytes -ne 0 -or $row.Requested -ne 0 -or $row.error -ne 0 -or
           $row.RegionSize -ne 0 -or $row.state -ne 0 -or $row.protect -ne 0 -or $row.type -ne 0){throw 'Uncaptured caller exposes lookup/read metadata.'}
        foreach($field in 'module','image','record','allocation','region'){if($row[$field] -cne '0000000000000000'){throw 'Uncaptured caller exposes an address.'}}
    }
    # Exceptions preserve bounded diagnostic metadata but zero the record RVAs.
    # A serializer clamp is explicit read_failed/error 13, never Observed.
    if($row.Requested -gt 0 -and $row.Status -cne 'exception'){Assert-T7CatalogueCallerWindow ([pscustomobject]$row)}
    [pscustomobject]$row
}
function ConvertFrom-T7CatalogueCallers([string]$Text) {
    Assert-T7CatalogueTraceSize 't7-catalog-callers' ([Text.Encoding]::UTF8.GetByteCount($Text))
    if($Text -cmatch '[^\x20-\x7e\r\n]'){throw 'Caller stderr must be ASCII without BOM.'}
    $complete=$Text.EndsWith("`n")
    $lines=@(if($Text.Length){if($complete){$Text.Substring(0,$Text.Length-1).Split("`n")}else{$Text.Split("`n")}})
    if($lines.Count -gt 12){throw 'Caller stderr exceeds twelve lines.'}
    $prefix='[T7_CATALOG_CALLER] schema=iw7.t7-catalog-callers/1 '
    $legacy=[Text.StringBuilder]::new();$captures=[Collections.Generic.List[object]]::new()
    $started=$false;$incomplete=$false
    for($i=0;$i -lt $lines.Count;$i++) {
        $raw=$lines[$i];$line=$raw -creplace '\r$','';$lastIncomplete=!$complete -and $i -eq $lines.Count-1
        $isCaller=$line.StartsWith('[T7_CATALOG_CALLER]',[StringComparison]::Ordinal)
        # Recognizable truncated caller prefix is preserved only after three EXIT records.
        $isPartial=$lastIncomplete -and $line.Length -gt 0 -and
            ($prefix.StartsWith($line,[StringComparison]::Ordinal) -or $line.StartsWith($prefix,[StringComparison]::Ordinal))
        if(!$started -and ($isCaller -or $isPartial)) {
            $context=ConvertFrom-T7CatalogueExitContext $legacy.ToString()
            if($context.Context.Captures.Count -eq 3 -and !$context.Context.IncompleteTrailingLine){$started=$true}
            elseif($isCaller){throw 'Caller records require all three preceding EXIT records.'}
            # A shorter ambiguous prefix may still be a truncated legacy EXIT.
            # Let the unchanged legacy reader qualify it at its current stage.
        }
        if(!$started){[void]$legacy.Append($raw);if(!$lastIncomplete){[void]$legacy.Append("`n")};continue}
        if($captures.Count -ge 3 -or $raw.Length+$(if($lastIncomplete){0}else{1}) -gt 2048){throw 'Caller count or line cap exceeded.'}
        if($lastIncomplete) {
            if(!$isPartial){throw 'Unrecognized incomplete caller line.'}
            # Do not accept a visibly duplicated/reordered target even when cut off.
            $index=[regex]::Match($line,' index=([0-9]+)(?: |$)')
            if($index.Success -and $index.Groups[1].Value -cne [string]$captures.Count){throw 'Incomplete caller index is duplicated or reordered.'}
            $incomplete=$true;continue
        }
        if(!$isCaller){throw 'Non-caller record follows caller diagnostics.'}
        $row=ConvertFrom-T7CatalogueCallerLine $line
        if($row.Index -ne $captures.Count){throw 'Caller records are duplicated or reordered.'}
        $captures.Add($row)
    }
    if(!$started){$context=ConvertFrom-T7CatalogueExitContext $legacy.ToString()}
    if($started) {
        $exit=@($context.Events|Where-Object Phase -CEQ 'exit_hook')[0]
        $stack=@($context.Context.Captures|Where-Object Kind -CEQ 'stack')[0]
        foreach($row in $captures) {
            if($row.Code -ne $exit.Code -or $row.ThreadId -ne $exit.ThreadId -or $row.ExitReturnAddress -ine $exit.ReturnAddress){throw 'Caller correlation differs from exit_hook.'}
            $frame=if($stack.Status -ceq 'ok'){[array]::IndexOf($stack.Addresses,$row.ReturnAddress)}else{-1}
            if($row.Frame -ne $frame){throw 'Caller frame is not the first matching stack occurrence.'}
            if(($stack.Status -cne 'ok' -and $row.Status -cne 'stack_unavailable') -or
               ($stack.Status -ceq 'ok' -and $frame -lt 0 -and $row.Status -cne 'absent') -or
               ($frame -ge 0 -and $row.Status -cin @('absent','stack_unavailable'))){throw 'Caller presence/status differs from the captured stack.'}
        }
    }
    $outcome=if(!$captures.Count -and !$incomplete){'Absent'}elseif($captures.Count -eq 3 -and !$incomplete -and !@($captures|Where-Object Status -CNE 'ok').Count){'Observed'}else{'Partial'}
    [pscustomobject]@{Outcome=$context.Outcome;Events=$context.Events;ContextOutcome=$context.ContextOutcome;Context=$context.Context;
        CallersOutcome=$outcome;Callers=[ordered]@{Captures=@($captures.ToArray());IncompleteTrailingLine=$incomplete}}
}
function ConvertFrom-T7CatalogueMessageLine([string]$Line) {
    $dec='(0|[1-9][0-9]{0,9})';$count='(0|[1-9][0-9]{0,2})'
    $head='\A\[T7_CATALOG_MSG\] schema=iw7\.t7-catalog-message/1 kind=(?<kind>install|buffer) tid=(?<tid>'+$dec+') status='
    $install='(?<status>installed|module_missing|module_mismatch|query_failed|region_invalid|read_failed|signature_mismatch|call_mismatch|wrapper_far|compare_mismatch|rolled_back|rollback_failed|exception) error=(?<error>'+$dec+')\z'
    $buffer='(?<status>ok|prefix|partial|argument_invalid|stack_invalid|query_failed|region_invalid|read_failed|exception) '+
        'requested=(?<requested>'+$count+') read=(?<read>'+$count+') length=(?<length>'+$count+') nul=(?<nul>[01]) error=(?<error>'+$dec+') data=(?<data>-|[0-9A-F]+)\z'
    $m=[regex]::Match($Line,$head+$install)
    if(!$m.Success -or $m.Groups['kind'].Value -cne 'install') {
        $m=[regex]::Match($Line,$head+$buffer)
        if(!$m.Success -or $m.Groups['kind'].Value -cne 'buffer'){throw 'Unknown message record or field format.'}
    }
    $row=[ordered]@{Kind=$m.Groups['kind'].Value;ThreadId=(Get-T7CatalogueContextNumber $m 'tid');
        Status=$m.Groups['status'].Value;Error=(Get-T7CatalogueContextNumber $m 'error')}
    if($row.Kind -ceq 'install') {
        if($row.Status -ceq 'installed' -and $row.Error -ne 0){throw 'Successful message installation has an error.'}
        return [pscustomobject]$row
    }
    $row.Requested=Get-T7CatalogueContextNumber $m 'requested' 384
    $row.ReadBytes=Get-T7CatalogueContextNumber $m 'read' 384
    $row.Length=Get-T7CatalogueContextNumber $m 'length' 384
    $row.NulTerminated=$m.Groups['nul'].Value -ceq '1';$row.DataHex=$m.Groups['data'].Value
    if($row.ReadBytes -gt $row.Requested -or $row.Length -gt $row.ReadBytes -or
       ($row.NulTerminated -and $row.Length -ge $row.ReadBytes) -or
       (!$row.NulTerminated -and $row.Length -ne $row.ReadBytes) -or
       ($row.Length -eq 0 -and $row.DataHex -cne '-') -or
       ($row.Length -gt 0 -and ($row.DataHex -ceq '-' -or $row.DataHex.Length -ne 2*$row.Length))){throw 'Message counts, NUL or payload length differ.'}
    # The terminator is excluded by the producer. Keep bytes private and opaque;
    # checking aligned zero bytes does not assume a text encoding.
    if($row.Length -gt 0){for($i=0;$i -lt $row.DataHex.Length;$i+=2){if($row.DataHex.Substring($i,2) -ceq '00'){throw 'Message payload includes a NUL or bytes after it.'}}}
    switch($row.Status) {
        ok {if($row.Requested -eq 0 -or $row.ReadBytes -ne $row.Requested -or !$row.NulTerminated -or $row.Error -ne 0){throw 'Complete message capture has inconsistent status.'}}
        prefix {if($row.Requested -eq 0 -or $row.ReadBytes -ne $row.Requested -or $row.NulTerminated -or $row.Error -ne 0){throw 'Message prefix has inconsistent status.'}}
        partial {if($row.ReadBytes -eq 0 -or $row.ReadBytes -ge $row.Requested){throw 'Partial message capture has inconsistent counts.'}}
        read_failed {
            if($row.ReadBytes -notin @(0,$row.Requested) -or ($row.Requested -eq 0 -and $row.Error -ne 13)){throw 'Failed message copy differs from the bounded RPM/clamp contract.'}
        }
        exception {} # Bounded counts already checked; a NUL never upgrades SEH.
        default {if($row.Requested -ne 0 -or $row.ReadBytes -ne 0 -or $row.Length -ne 0 -or $row.NulTerminated){throw 'Message pre-read refusal exposes a copy.'}}
    }
    [pscustomobject]$row
}
function ConvertFrom-T7CatalogueMessage([string]$Text) {
    Assert-T7CatalogueTraceSize 't7-catalog-message' ([Text.Encoding]::UTF8.GetByteCount($Text))
    if($Text -cmatch '[^\x20-\x7e\r\n]'){throw 'Message stderr must be ASCII without BOM.'}
    $complete=$Text.EndsWith("`n")
    $lines=@(if($Text.Length){if($complete){$Text.Substring(0,$Text.Length-1).Split("`n")}else{$Text.Split("`n")}})
    if($lines.Count -gt 14){throw 'Message stderr exceeds fourteen lines.'}
    $prefix='[T7_CATALOG_MSG] schema=iw7.t7-catalog-message/1 kind='
    $legacy=[Text.StringBuilder]::new();$captures=[Collections.Generic.List[object]]::new()
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $positions=@{};$tracePositions=@{};$incomplete=$false
    for($i=0;$i -lt $lines.Count;$i++) {
        $raw=$lines[$i];$line=$raw -creplace '\r$','';$lastIncomplete=!$complete -and $i -eq $lines.Count-1
        $isMessage=$line.StartsWith('[T7_CATALOG_MSG]',[StringComparison]::Ordinal)
        $couldBeMessage=$lastIncomplete -and $line.Length -gt 0 -and
            ($prefix.StartsWith($line,[StringComparison]::Ordinal) -or $line.StartsWith($prefix,[StringComparison]::Ordinal))
        if($couldBeMessage -and !$isMessage) {
            # An ambiguous short prefix can still belong to EXIT/CALLER /1.
            $legacyAccepts=$false
            try{$null=ConvertFrom-T7CatalogueCallers ($legacy.ToString()+$raw);$legacyAccepts=$true}catch{}
            if($legacyAccepts){$couldBeMessage=$false}
        }
        if($lastIncomplete -and ($isMessage -or $couldBeMessage)) {
            if(!$couldBeMessage -or $captures.Count -ge 2 -or $raw.Length -gt 1024){throw 'Unrecognized or excess incomplete message record.'}
            if($line.StartsWith($prefix,[StringComparison]::Ordinal)) {
                $kind=($line.Substring($prefix.Length) -split ' ',2)[0]
                $possible=@('install','buffer'|Where-Object {$_.StartsWith($kind,[StringComparison]::Ordinal)})
                if(!$possible.Count){throw 'Unknown incomplete message kind.'}
                if($kind -cin @('install','buffer')) {
                    $cap=if($kind -ceq 'install'){256}else{1024}
                    if($seen.Contains($kind) -or $raw.Length -gt $cap){throw 'Duplicate or oversized incomplete message record.'}
                    if($kind -ceq 'buffer' -and (!$seen.Contains('install') -or $captures[0].Status -cne 'installed')){throw 'Incomplete message buffer requires a preceding successful installation.'}
                }
            }
            $incomplete=$true;continue
        }
        if($isMessage) {
            $row=ConvertFrom-T7CatalogueMessageLine $line
            $cap=if($row.Kind -ceq 'install'){256}else{1024}
            if(!$seen.Add($row.Kind) -or $raw.Length+1 -gt $cap){throw 'Message one-shot or line cap differs.'}
            $positions[$row.Kind]=$i;$captures.Add($row);continue
        }
        [void]$legacy.Append($raw);if(!$lastIncomplete){[void]$legacy.Append("`n")}
        $phase=[regex]::Match($line,'\A\[T7_CATALOG_TRACE\] .* phase=(before_post_unpack|after_post_unpack|exit_hook) ')
        if($phase.Success){$tracePositions[$phase.Groups[1].Value]=$i}
    }
    $previous=ConvertFrom-T7CatalogueCallers $legacy.ToString()
    $installation=@($captures|Where-Object Kind -CEQ 'install');$buffer=@($captures|Where-Object Kind -CEQ 'buffer')
    $installBoundaryObserved=$false;$correlated=$false;$correlation='NoBuffer'
    if($installation.Count) {
        if(!$tracePositions.ContainsKey('before_post_unpack')){throw 'Message installation lacks before_post_unpack.'}
        if($positions.install -le $tracePositions.before_post_unpack){throw 'Message installation precedes before_post_unpack.'}
        $installBoundaryObserved=$true
        if($tracePositions.ContainsKey('after_post_unpack') -and $positions.install -ge $tracePositions.after_post_unpack){throw 'Message installation follows after_post_unpack.'}
    }
    if($buffer.Count) {
        if($installation.Count -ne 1 -or $installation[0].Status -cne 'installed' -or $positions.buffer -le $positions.install){throw 'Message buffer requires a preceding successful installation.'}
        $exit=@($previous.Events|Where-Object Phase -CEQ 'exit_hook')
        if(!$exit.Count){$correlation='NoExitHook'}
        elseif($buffer[0].ThreadId -ne $exit[0].ThreadId){$correlation='DifferentThread'}
        elseif($positions.buffer -ge $tracePositions.exit_hook){throw 'Message buffer follows exit_hook on its own thread.'}
        else{$correlated=$true;$correlation='SameThreadBeforeExit'}
    }
    $outcome=if(!$captures.Count -and !$incomplete){'Absent'}elseif($incomplete -or !$buffer.Count -or !$correlated -or !$installBoundaryObserved){'Partial'}
        elseif($buffer[0].Status -ceq 'ok'){'Observed'}elseif($buffer[0].Status -ceq 'prefix'){'Prefix'}else{'Partial'}
    [pscustomobject]@{Outcome=$previous.Outcome;Events=$previous.Events;ContextOutcome=$previous.ContextOutcome;Context=$previous.Context;
        CallersOutcome=$previous.CallersOutcome;Callers=$previous.Callers;MessageOutcome=$outcome;
        Message=[ordered]@{Captures=@($captures.ToArray());IncompleteTrailingLine=$incomplete;InstallBoundaryObserved=$installBoundaryObserved;
            ExitCorrelated=$correlated;Correlation=$correlation}}
}
function Initialize-T7CatalogueOpaqueManifestObservation($Plan) {
    # Per-attempt metadata only. Never infer a producer, format, or file contents.
    $script:T7CatalogueOpaqueManifestObservation=$null
    if($Plan.PSObject.Properties['EngineOutputProfile'] -and $Plan.EngineOutputProfile -ceq 'ObservedStartupManifestA') {
        $script:T7CatalogueOpaqueManifestObservation=[pscustomobject]@{
            Plan=$Plan;RunRoot=$Plan.RunRoot;Seen=$false;FileId=$null;Finalized=$false;PresentAtFinal=$false
        }
    }
}
function Get-T7CatalogueOpaqueManifestObservation($Plan) {
    $variable=Get-Variable T7CatalogueOpaqueManifestObservation -Scope Script -ErrorAction SilentlyContinue
    if(!$variable -or !$variable.Value -or ![object]::ReferenceEquals($variable.Value.Plan,$Plan) -or
       $variable.Value.RunRoot -cne $Plan.RunRoot){throw 'Opaque manifest requires its initialized runtime attempt.'}
    $variable.Value
}
function Assert-T7CatalogueOpaqueManifestContext($Context) {
    if(!$Context -or !$Context.PSObject.Properties['Lease'] -or !$Context.Lease -or
       !$Context.Lease.PSObject.Properties['Token'] -or $Context.Lease.Token -cnotmatch '\A[0-9a-f]{32}\z' -or
       !$Context.PSObject.Properties['Closed'] -or $Context.Closed -ne $true -or
       !$Context.PSObject.Properties['Guards'] -or $null -eq $Context.Guards){
        throw 'Opaque manifest final validation requires closed native ownership and retained admission/guards.'
    }
}
function Assert-T7CatalogueOpaqueManifest($Plan,[string]$Path,$Observation,[switch]$Closed,$Context) {
    $expected=Join-Path $Plan.WorkingDirectory 'identities\dedicatedpc\LPC\.manifest'
    if($Plan.EngineOutputProfile -cne 'ObservedStartupManifestA' -or $Path -cne $expected){
        throw 'Only the explicit opaque manifest output path is permitted.'
    }
    Assert-H1Path $Path
    $item=Get-Item -LiteralPath $Path
    if($item.PSIsContainer -or $item.Length -gt 8){throw 'Opaque manifest must be an ordinary file of at most eight bytes.'}
    $fileId=Get-T7CatalogueFileId $Path
    if($fileId -cnotmatch '\A[0-9A-F]{8}:[0-9A-F]{16}\z' -or
       ($Observation.Seen -and $Observation.FileId -cne $fileId) -or
       ($Observation.Finalized -and !$Observation.PresentAtFinal)){
        throw 'Opaque manifest identity or finalized absence changed.'
    }
    if($Closed) {
        Assert-T7CatalogueOpaqueManifestContext $Context
        # Do not read/hash the opaque bytes. Holding this read/share-read handle
        # freezes the observed file through final validation and lease release.
        $guard=[IO.FileStream]::new($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        try {
            Assert-H1Path $Path
            if($guard.Length -ne 8 -or (Get-T7CatalogueFileId $Path) -cne $fileId){
                throw 'Opaque manifest final size or identity differs.'
            }
            $Context.Guards.Add($guard)
        }catch{$guard.Dispose();throw}
    }elseif((Get-T7CatalogueFileId $Path) -cne $fileId){
        throw 'Opaque manifest identity changed during observation.'
    }
    $Observation.Seen=$true;$Observation.FileId=$fileId
}
function Assert-T7CatalogueEngineOutputs($Plan,[switch]$Closed,$Context) {
    $export=(Get-T7CatalogueOperation $Plan) -ceq 'ResidentExportV1'
    $opaque=[bool]($Plan.PSObject.Properties['EngineOutputProfile'] -and
        $Plan.EngineOutputProfile -ceq 'ObservedStartupManifestA')
    $manifestSeen=$false;$observation=$null
    if($opaque) {
        $observation=Get-T7CatalogueOpaqueManifestObservation $Plan
        if($Closed) {
            Assert-T7CatalogueOpaqueManifestContext $Context
            if($observation.Finalized){throw 'Opaque manifest final validation already consumed.'}
        }
    }
    Assert-H1Path $Plan.WorkingDirectory
    $allowedFiles=@('BlackOps3_UnrankedDedicatedServer.exe','steam_api64.dll','t7-zonetool-candidate.exe')
    if($export -and (Get-T7SelectedStreamedExport $Plan)){$allowedFiles+=@('streamed-request.json')}
    foreach($entry in [IO.Directory]::EnumerateFileSystemEntries($Plan.WorkingDirectory)) {
        Assert-H1Path $entry
        $name=[IO.Path]::GetFileName($entry)
        if($name -cin $allowedFiles){if([IO.Directory]::Exists($entry)){throw 'Binary alias became a directory.'};continue}
        if($name -ceq 'steam_appid.txt') {
            if([IO.Directory]::Exists($entry) -or (Get-Item -LiteralPath $entry).Length -gt 6){throw 'Observed Steam app-id output type/size differs.'}
            if($Closed) {
                # Partial writes are tolerated during observation, never at acceptance.
                $sha=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::ASCII.GetBytes('311210'))).ToLowerInvariant()
                $Context.Guards.Add((Open-H1Pin ([pscustomobject]@{Path=$entry;Bytes=6;SHA256=$sha})))
            }
            continue
        }
        if($name -ceq 'identities') {
            if(![IO.Directory]::Exists($entry)){throw 'Observed identities path must be a directory.'}
            # The historical A profile still accepts only the empty directories.
            $allowed=@('dedicatedpc','dedicatedpc\dumps','dedicatedpc\LPC')
            $pending=[Collections.Generic.Stack[string]]::new();$pending.Push($entry)
            while($pending.Count) {
                foreach($child in [IO.Directory]::EnumerateFileSystemEntries($pending.Pop())) {
                    Assert-H1Path $child
                    $relative=$child.Substring($entry.Length+1)
                    if($opaque -and $relative -ceq 'dedicatedpc\LPC\.manifest') {
                        Assert-T7CatalogueOpaqueManifest $Plan $child $observation -Closed:$Closed -Context $Context
                        $manifestSeen=$true
                        continue
                    }
                    if($relative -cnotin $allowed -or ![IO.Directory]::Exists($child)){throw 'Unexpected identity entry; retain privately without reading payload.'}
                    $pending.Push($child)
                }
            }
            continue
        }
        if($export -and $name -ceq 'dump'){$null=@(Get-T7ResidentExportFiles $Plan);continue}
        $allowedDirectories=if($export){@('zone')}else{@('zone',$Plan.OutputKey)}
        if($name -cnotin $allowedDirectories -or ![IO.Directory]::Exists($entry)){throw 'Unexpected engine output; preserve and stop.'}
        $allowed=@(if($name -ceq 'zone'){(Get-T7CataloguePlanZoneSpec $Plan).FileName}else{'catalog.json'})
        if($name -ceq 'zone'){$allowed+=@(Get-T7CatalogueBootstraps $Plan|ForEach-Object {[IO.Path]::GetFileName($_.RelativePath)})}
        if($export -and (Get-T7SelectedStreamedExport $Plan) -and $name -ceq 'zone'){$allowed+=@([IO.Path]::GetFileName($Plan.SelectedXpakProvider.RelativePath))}
        foreach($child in [IO.Directory]::EnumerateFileSystemEntries($entry)) {
            Assert-H1Path $child
            if([IO.Path]::GetFileName($child) -cnotin $allowed -or [IO.Directory]::Exists($child)){throw 'Unexpected zone/catalogue output; preserve and stop.'}
            if($name -ceq $Plan.OutputKey -and (Get-Item -LiteralPath $child).Length -gt 512KB){throw 'Catalogue report cap exceeded.'}
        }
    }
    if(Test-Path -LiteralPath (Join-Path $Plan.RunRoot 'zone')){throw 'Unexpected parent zone.'}
    if($opaque) {
        if($observation.Seen -and !$manifestSeen){throw 'Previously observed opaque manifest disappeared.'}
        if($Closed){$observation.Finalized=$true;$observation.PresentAtFinal=$manifestSeen}
    }
}
function Enable-T7CatalogueRuntimeProfile($Plan) {
    $script:T7CatalogueGroupStarted=Get-H1Clock
    Initialize-T7CatalogueOpaqueManifestObservation $Plan
    if((Get-T7CatalogueBootstrapPolicy $Plan) -ceq 'QualifiedCollectionV3'){
        $null=Get-T7CatalogueBootstraps $Plan
        $script:T7CatalogueV3Plan=$Plan;$script:T7CatalogueBaseOpenPin=${function:Open-H1Pin}
        function script:Open-H1Pin($Pin) {
            Open-T7CatalogueV3Pin $script:T7CatalogueV3Plan $Pin $script:T7CatalogueBaseOpenPin
        }
    }
    $script:T7CatalogueBaseDeadline=${function:Assert-H1Deadline};$script:T7CatalogueBaseBudget=${function:Test-H1Budget}
    function script:Assert-H1Deadline($Started,[int]$Seconds) {
        & $script:T7CatalogueBaseDeadline $script:T7CatalogueGroupStarted 200
        & $script:T7CatalogueBaseDeadline $Started $Seconds
    }
    function script:Test-H1Budget($Plan,$State) {
        Assert-H1Deadline $script:T7CatalogueGroupStarted 200
        & $script:T7CatalogueBaseBudget $Plan $State
        foreach($name in 'stdout.log','stderr.log') {
            $path=Join-Path $Plan.StageRoot $name
            if((Test-Path -LiteralPath $path) -and (Get-Item -LiteralPath $path).Length -gt 1MB){throw 'Catalogue log cap exceeded.'}
            if($name -ceq 'stderr.log' -and (Test-Path -LiteralPath $path)){
                Assert-T7CatalogueTraceSize (Get-T7CatalogueCandidateProfile $Plan) (Get-Item -LiteralPath $path).Length
            }
        }
        Assert-T7CatalogueEngineOutputs $Plan
        Assert-H1Deadline $script:T7CatalogueGroupStarted 200
    }
}
# C observation splitter: only finite opt-in markers are removed. Legacy text is untouched.
function Split-T7CatalogueZombiesObservation([string]$Text) {
    if($Text -cmatch '[^\x00-\x7f]' -or [Text.Encoding]::ASCII.GetByteCount($Text) -gt 16KB){throw 'Bounded ASCII combined Zombies trace required.'}
    $legacy=[Text.StringBuilder]::new();$records=[Collections.Generic.List[object]]::new()
    $sequences=[Collections.Generic.HashSet[uint]]::new();$phases=[Collections.Generic.HashSet[uint]]::new();$counts=@{};$observedBytes=0
    $patterns=@(
        'kind=phase phase=(?<phase>[0-9]+)',
        'kind=raw_enter phase=(?<phase>[0-9]+) caller=(?<caller>[0-9A-Fa-f]{16}) type=47 error=(?<error>[01]) wait=(?<wait>-?[0-9]+)',
        'kind=raw_return phase=(?<phase>[0-9]+) result=(?<result>[0-9A-Fa-f]{16})',
        'kind=load_enter phase=(?<phase>[0-9]+) caller=(?<caller>[0-9A-Fa-f]{16}) count=(?<count>[0-9]+) sync=(?<sync>-?[0-9]+) suppress=(?<suppress>-?[0-9]+)',
        'kind=load_return phase=(?<phase>[0-9]+)',
        'kind=zone index=(?<index>[01]) status=unreadable',
        'kind=zone index=(?<index>[01]) status=(?<status>read|unreadable) nul=(?<nul>[01]) name_hex=(?<name_hex>[0-9a-f]{0,128}) alloc=(?<alloc>[0-9]+) free=(?<free>[0-9]+) alloc_slot=(?<alloc_slot>[0-9]+) free_slot=(?<free_slot>[0-9]+)')
    # Regex retains each terminator, including CRLF, and never invents the final newline.
    $lines=[regex]::Matches($Text,'[^\n]*\n|[^\n]+\z')
    foreach($item in $lines){
        $line=$item.Value
        if(!$line.StartsWith('[T7_ZM_OBS]',[StringComparison]::Ordinal)){[void]$legacy.Append($line);continue}
        if(!$line.EndsWith("`n") -or $line.Length -gt 512){throw 'Complete bounded Zombies observation line required.'}
        $row=$line.Substring(0,$line.Length-1) -creplace '\r$',''
        $head=[regex]::Match($row,'\A\[T7_ZM_OBS\] schema=iw7\.t7-zm-observation/1 seq=([0-9]+) tid=([0-9]+) (.+)\z')
        if(!$head.Success){throw 'Exact Zombies observation schema required.'}
        try{$sequence=[uint]::Parse($head.Groups[1].Value);$thread=[uint]::Parse($head.Groups[2].Value)}catch{throw 'Observation sequence/thread exceeds native width.'}
        if($sequence -gt 63 -or !$thread -or !$sequences.Add($sequence)){throw 'Observation sequence/thread invalid or duplicated.'}
        $body=$head.Groups[3].Value;$match=$null
        foreach($pattern in $patterns){$candidate=[regex]::Match($body,('\A'+$pattern+'\z'));if($candidate.Success){$match=$candidate;break}}
        if(!$match){throw 'Unknown Zombies observation record.'}
        $kind=($body.Split(' ')[0]).Substring(5)
        $fields=[ordered]@{kind=$kind;sequence=$sequence;thread=$thread}
        foreach($name in @($match.Groups.Keys|Where-Object {$_ -notmatch '^[0-9]+$'})){
            $group=$match.Groups[$name];if(!$group.Success){continue};$value=$group.Value
            if($name -cin @('caller','result','status','name_hex')){$fields[$name]=$value;continue}
            try{$number=if($name -cin @('wait','sync','suppress')){[long]::Parse($value)}else{[ulong]::Parse($value)}}catch{throw 'Observation integer exceeds native width.'}
            if($name -cin @('wait','sync','suppress') -and ($number -lt [int]::MinValue -or $number -gt [int]::MaxValue)){throw 'Observation integer exceeds int32.'}
            $fields[$name]=$number
        }
        if(($fields.Contains('phase') -and $fields.phase -ge 14) -or ($fields.Contains('count') -and $fields.count -gt [uint]::MaxValue)){throw 'Observation phase/count outside bounds.'}
        if($kind -ceq 'phase' -and !$phases.Add([uint]$fields.phase)){throw 'Duplicate one-shot phase.'}
        if($fields.Contains('name_hex')){
            $hex=$fields.name_hex
            if($hex.Length%2 -or ($fields.status -ceq 'unreadable' -and ($hex.Length -or $fields.nul)) -or
               ($fields.status -ceq 'read' -and (($hex.Length -eq 128) -ne ($fields.nul -eq 0)))){throw 'Observed name length/termination differs.'}
        }
        if(!$counts.ContainsKey($kind)){$counts[$kind]=0};$counts[$kind]++
        $cap=if($kind -ceq 'phase'){14}elseif($kind -ceq 'zone'){8}else{4}
        if($counts[$kind] -gt $cap){throw 'Observation event cap exceeded.'}
        $observedBytes+=$line.Length
        if($observedBytes -gt 8KB -or $records.Count -ge 38){throw 'Observation trace cap exceeded.'}
        $records.Add([pscustomobject]$fields)
    }
    [pscustomobject]@{LegacyText=$legacy.ToString();Records=$records.ToArray();ObservationBytes=$observedBytes;CombinedBytes=[Text.Encoding]::ASCII.GetByteCount($Text)}
}
function ConvertFrom-T7CatalogueZombiesObservation([string]$Text) {
    $split=Split-T7CatalogueZombiesObservation $Text
    # F still enforces its original ASCII/8KiB/fourteen-line contract on all other bytes.
    $result=ConvertFrom-T7CatalogueMessage $split.LegacyText
    $result|Add-Member -NotePropertyName ZombiesObservations -NotePropertyValue $split.Records
    $result|Add-Member -NotePropertyName ZombiesObservationBytes -NotePropertyValue $split.ObservationBytes
    $result
}
