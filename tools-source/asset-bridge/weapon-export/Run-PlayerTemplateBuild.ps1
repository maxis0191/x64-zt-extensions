# Canonical legacy CLI cohorts and the explicit authored eight-stage H1/T7 profile.
# Default reads only bounded source/metadata. No tool/game/export entry exists.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
function Read-PlayerSource([string]$Path,[string]$SHA256,[long]$Bytes=-1,[Collections.Generic.List[object]]$KeepGuards=$null,[switch]$AllowMarkdown) {
    $extensions=@('.json','.py','.ps1','.cs','.hpp','.cpp','.inc','.rsp','.h','.hh','.inl','.vcxproj','.txt')
    if($AllowMarkdown){$extensions+=@('.md')}
    if([IO.Path]::GetExtension($Path).ToLowerInvariant() -cnotin $extensions){throw 'Source/metadata suffix required before filesystem IO.'}
    if($SHA256 -cnotmatch '^[0-9a-f]{64}$' -or ![IO.Path]::IsPathFullyQualified($Path)){throw 'Exact source binding required.'}
    for($part=$Path;$part;$part=[IO.Path]::GetDirectoryName($part)){
        if((Get-Item -LiteralPath $part).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Linked source ancestry refused.'}
    }
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read')
    try{
        if($stream.Length -gt 2MB -or ($Bytes -ge 0 -and $stream.Length -ne $Bytes)){throw 'Source size differs.'}
        $buffer=[byte[]]::new(2MB+1);$used=0
        do{$count=$stream.Read($buffer,$used,$buffer.Length-$used);$used+=$count}while($count -gt 0 -and $used -lt $buffer.Length)
        if($used -gt 2MB){throw 'Source grew above cap before hash/decode.'}
        $raw=[byte[]]::new($used);[Array]::Copy($buffer,$raw,$used)
        if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant() -cne $SHA256){throw 'Source hash differs.'}
        $decoded=[Text.Encoding]::UTF8.GetString($raw)
        if($null -ne $KeepGuards){$stream.Position=0;$KeepGuards.Add($stream);$stream=$null}
        $decoded
    }finally{if($null -ne $stream){$stream.Dispose()}}
}
function Get-PlayerDefinitionResponse([string]$Prepared,[string]$Run){
    $stage=Join-Path $Run 'definition-compile'
    '/nologo /std:c++17 /EHsc /MT /DNDEBUG /W4 /WX /Zi /Od /Y- /I"'+$Prepared+'" /FI"'+(Join-Path $Prepared 'native_definition_fixture_binding.hpp')+
        '" /Fo"'+(Join-Path $stage 'definition.obj')+'" /Fe"'+(Join-Path $stage 'definition.exe')+'" /Fd"'+(Join-Path $stage 'compile.pdb')+
        '" /sourceDependencies "'+(Join-Path $stage 'dependencies.json')+'" "'+(Join-Path $Prepared 'test_definition_readset.cpp')+
        '" /link /INCREMENTAL:NO /DEBUG /PDB:"'+(Join-Path $stage 'definition.pdb')+'"'+"`n"
}
function Assert-PlayerDefinitionFixture($Plan){
    if(!$Plan.PSObject.Properties['DefinitionFixture'] -or $Plan.DefinitionFixture.Schema -cne 'iw7.player-definition-fixture-source/1' -or
        $Plan.NativeSourcePin -cne 'fab935826c898806855376662a8a03317b3ad8f1'){throw 'Exact real definition fixture Source contract required.'}
    $contract=$Plan.DefinitionFixture
    if(!$Plan.PSObject.Properties['CandidateBytes'] -or !$Plan.PSObject.Properties['CandidateSHA256'] -or
        $null -ne $Plan.CandidateBytes -or $null -ne $Plan.CandidateSHA256){throw 'Future neutral candidate bytes/hash must remain null.'}
    $expected=@{
        'test_definition_readset.cpp'='ca53ca9baf8a5924692d303fba580d5632b4a07aee7533fdecf9fe5c3f3422c3'
        'native_definition_access.hpp'='92eb62fd94a18397ea09de034330009aaa17d16abaf037d98e041412f4ce1890'
        'native_definition_readset.hpp'='eb6957a20506e87f75f056a040c8213d979fbd64a79765700593e9f78ff6bcb6'
        'native_definition_fields.inc'='302e324b98175981ba8ae3e071a23e125ed83353d8319ca60a9c0390f47db7e3'
        'native_definition_gate.hpp'='314667bfc966bd38ba8040a9a3b12f7cef513819659ce170f05547bd0b0e409f'
    }
    if($contract.Files -isnot [array] -or $contract.Files.Count -ne $expected.Count){throw 'All five real readset fixture Source files required.'}
    foreach($name in $expected.Keys){
        $path=Join-Path $Plan.PreparedRoot $name
        $pins=@($contract.Files|Where-Object {$_.Path -is [string] -and $_.Path -ceq $path})
        $prepared=@($Plan.PreparedBindings|Where-Object Path -CEQ $path)
        if($pins.Count -ne 1 -or $prepared.Count -ne 1 -or $pins[0].SHA256 -cne $prepared[0].SHA256 -or $pins[0].Bytes -ne $prepared[0].Bytes){throw 'Unique prepared fixture Source binding required.'}
        $text=Read-PlayerSource $pins[0].Path $pins[0].SHA256 $pins[0].Bytes
        $raw=[Text.Encoding]::UTF8.GetBytes($text.Replace("`r`n","`n"))
        if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant() -cne $expected[$name]){throw 'Real pinned 100-check fixture/readset required; metadata stubs refused.'}
    }
    # The native declaration is an EXPECTED retained input here. Do not open,
    # stat or hash it in DEFAULT. Its actual read remains behind admission.
    $native=$contract.NativeHeader
    if($native.Path -isnot [string] -or ![IO.Path]::IsPathFullyQualified($native.Path) -or $native.Path -match '["\x00-\x1f]' -or
        ($native.Bytes -isnot [int] -and $native.Bytes -isnot [long]) -or $native.Bytes -ne 354227 -or
        $native.SHA256 -isnot [string] -or $native.SHA256 -cne 'adb62e481a533d27f97829e64d9038b13c5e9cd88e6b4aee8cac339b9492921a' -or
        $native.Path.Replace('\','/') -cnotmatch '/src/zonetool/zonetool/iw7/structs\.hpp$'){throw 'Exact declared native structs input required.'}
    $retained=@($Plan.RetainedInputPins|Where-Object {[IO.Path]::GetFullPath($_.Path) -ieq [IO.Path]::GetFullPath($native.Path)})
    if($retained.Count -ne 1 -or $retained[0].Bytes -ne $native.Bytes -or $retained[0].SHA256 -cne $native.SHA256){throw 'Native fixture header must be the original retained input declaration.'}
    $bindingPath=Join-Path $Plan.PreparedRoot 'native_definition_fixture_binding.hpp'
    $binding=@($Plan.PreparedBindings|Where-Object Path -CEQ $bindingPath)
    $response=@($Plan.PreparedBindings|Where-Object Path -CEQ (Join-Path $Plan.PreparedRoot 'definition.rsp'))
    if($binding.Count -ne 1 -or $response.Count -ne 1){throw 'Pinned forced-include binding and definition response required.'}
    $expectedBinding="#pragma once`n#define IW7_NATIVE_STRUCTS_HEADER `""+$native.Path.Replace('\','/')+"`"`n"
    if((Read-PlayerSource $binding[0].Path $binding[0].SHA256 $binding[0].Bytes).Replace("`r`n","`n") -cne $expectedBinding -or
        (Read-PlayerSource $response[0].Path $response[0].SHA256 $response[0].Bytes).Replace("`r`n","`n") -cne (Get-PlayerDefinitionResponse $Plan.PreparedRoot $Plan.RunRoot)){
        throw 'Exact real fixture100 source/forced include/compiler response required.'
    }
    foreach($name in @($expected.Keys)+@('native_definition_fixture_binding.hpp')){
        $path=Join-Path $Plan.PreparedRoot $name
        if(@($Plan.OwnDirectIncludeCoverage|Where-Object {$_.Path -ceq $path -and $_.Pinned -is [bool] -and $_.Pinned}).Count -ne 1){throw 'Exact guarded fixture Source include coverage required.'}
    }
}

function Read-PlayerAuthoredSource([string]$Path,[string]$SHA256,[long]$Bytes=-1,[Collections.Generic.List[object]]$KeepGuards=$null) {
    Read-PlayerSource $Path $SHA256 $Bytes $KeepGuards -AllowMarkdown
}
function Get-PlayerAuthoredSafetyClock {
    if(Get-Command Get-H1Clock -CommandType Function -ErrorAction SilentlyContinue){return Get-H1Clock}
    # A Source guard may fail before Core import; teardown still needs a clock.
    [Diagnostics.Stopwatch]::GetTimestamp()/([double][Diagnostics.Stopwatch]::Frequency)*1000
}
function Invoke-NeutralFactoryBridge($Factory,$Context,[double]$Started,[int]$Seconds,[double]$GroupStarted,[int]$GroupSeconds) {
    Assert-H1Deadline $GroupStarted $GroupSeconds
    Assert-H1Deadline $Started $Seconds
    $owner=& $Factory
    if(!$owner){throw 'Original factory returned no owner.'}
    $Context.Owner=$owner
    Assert-H1Deadline $GroupStarted $GroupSeconds
    Assert-H1Deadline $Started $Seconds
    $owner
}
function Open-NeutralPublication($Entry,$Context,$Guards) {
    # Retain a partial entry before CreateNew; retain its stream before enrollment.
    $Context.PublicationEntries.Add($Entry)
    $Entry.Stream=[IO.FileStream]::new($Entry.Path,'CreateNew','ReadWrite','Read')
    $Entry.SafeHandle=$Entry.Stream.SafeFileHandle
    $Guards.Add($Entry.Stream)
}
function Write-NeutralPublication($Entry) {
    if(!$Entry.Stream -or !$Entry.SafeHandle -or $Entry.SafeHandle.IsClosed){throw 'Original publication handle required.'}
    $Entry.Stream.Position=0;$Entry.Stream.Write($Entry.Bytes,0,$Entry.Bytes.Length);$Entry.Stream.Flush($true)
}
function Read-NeutralPublication($Entry) {
    $stream=$Entry.Stream
    if(!$stream -or $Entry.SafeHandle.IsClosed -or $stream.Length -ne $Entry.Bytes.Length -or $stream.Length -gt 1MB){throw 'Same bounded publication stream required.'}
    $stream.Position=0;$read=[byte[]]::new($Entry.Bytes.Length);$used=0
    while($used -lt $read.Length){$count=$stream.Read($read,$used,$read.Length-$used);if($count -le 0){throw 'Publication shortened.'};$used+=$count}
    if($stream.ReadByte() -ne -1){throw 'Publication grew.'}
    for($index=0;$index -lt $read.Length;$index++){if($read[$index] -ne $Entry.Bytes[$index]){throw 'Same-stream publication bytes differ.'}}
    $hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($read)).ToLowerInvariant()
    if($hash -cne $Entry.SHA256){throw 'Same-stream publication hash differs.'}
    $decoded=[Text.UTF8Encoding]::new($false,$true).GetString($read)|ConvertFrom-Json -Depth 30
    if(!$decoded){throw 'Publication JSON required.'}
    $Entry.ReadBack=$true
}
function New-NeutralPublication([string]$Path,$Value,[int]$Depth=20) {
    $text=($Value|ConvertTo-Json -Depth $Depth)+[string][char]10
    if($text.Length -gt 1MB){throw 'Publication text exceeds metadata reserve.'}
    $bytes=[Text.UTF8Encoding]::new($false,$true).GetBytes($text)
    [pscustomobject]@{Path=$Path;Bytes=$bytes;SHA256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant();
        Stream=$null;SafeHandle=$null;ReadBack=$false}
}
function Save-PlayerAuthoredGuardReferences($Context,$Guards) {
    if($Context.PSObject.Properties['FinalGuardReferences']){
        return [pscustomobject]@{Streams=$Context.FinalGuardReferences;Handles=$Context.FinalGuardSafeHandles}
    }
    $refs=[Collections.Generic.List[object]]::new()
    foreach($guard in $Guards){$refs.Add($guard)}
    if($Context.PSObject.Properties['PublicationEntries']){
        foreach($entry in $Context.PublicationEntries){
            if($null -eq $entry.Stream){continue}
            $present=$false;foreach($ref in $refs){if([object]::ReferenceEquals($ref,$entry.Stream)){$present=$true;break}}
            if(!$present){$refs.Add($entry.Stream)}
        }
    }
    $streams=$refs.ToArray();$handles=[object[]]::new($streams.Count)
    for($i=0;$i -lt $streams.Count;$i++){$handles[$i]=$streams[$i].SafeFileHandle}
    Add-Member -InputObject $Context NoteProperty FinalGuardReferences $streams
    Add-Member -InputObject $Context NoteProperty FinalGuardSafeHandles $handles
    [pscustomobject]@{Streams=$streams;Handles=$handles}
}
function Complete-NeutralPublication($Plan,$State,$Context,$Guards,[double]$Started,$Failure) {
    if(!$Context.Closed -or !$Context.Lease){throw 'Original closed owner and held lease required.'}
    Assert-H1Deadline $Started $Plan.GroupDeadlineSeconds
    $nativeBytes=Measure-H1Output $Plan.RunRoot $Plan.AuthoredOutputBudget
    if($nativeBytes -gt $Plan.OutputLimitBytes-$Plan.MetadataReserveBytes){throw 'Native output exceeds reserved budget.'}
    $State.MaxObservedOutputBytes=[math]::Max($State.MaxObservedOutputBytes,$nativeBytes)
    $measured=New-NeutralPublication (Join-Path $Plan.RunRoot 'measured-before-release.json') $State
    $beforeValue=[ordered]@{Schema='iw7.neutral-cpp-before-release/1';PlanSHA256=$State.PlanSHA256;MeasuredSHA256=$measured.SHA256;
        Host=$State.Host;Status=$State.Status;OriginalRootAndJobClosed=$true;LeaseToken=$Context.Lease.Token;GuardsHeld=($Guards.Count+3);Ready=$false}
    $before=New-NeutralPublication (Join-Path $Plan.RunRoot 'closure-before-release.json') $beforeValue
    $finalValue=[ordered]@{Schema='iw7.neutral-cpp-closure/1';PlanSHA256=$State.PlanSHA256;MeasuredSHA256=$measured.SHA256;
        BeforeReleaseSHA256=$before.SHA256;Host=$State.Host;Status='ClosedReleasedGuardsHeldPendingPostflight';
        OriginalRootAndJobClosed=$true;LeaseReleased=$true;GuardsDisposed=$false;GuardsHeld=($Guards.Count+3);
        PostReadbackDeadlineRequired=$true;CandidateExecuted=$false;Ready=$false}
    $final=New-NeutralPublication (Join-Path $Plan.RunRoot 'final-closure.json') $finalValue
    [long]$metadata=$measured.Bytes.Length+$before.Bytes.Length+$final.Bytes.Length
    if($metadata -gt $Plan.MetadataReserveBytes -or $nativeBytes+$metadata -gt $Plan.OutputLimitBytes){throw 'Three preconstructed JSONs exceed reserved output.'}
    if($Context.PSObject.Properties['PublicationEntries']){throw 'Publication already attempted; original entries must remain retained.'}
    Add-Member -InputObject $Context NoteProperty PublicationEntries ([Collections.Generic.List[object]]::new())
    foreach($entry in @($measured,$before,$final)){Open-NeutralPublication $entry $Context $Guards}
    $original=Save-PlayerAuthoredGuardReferences $Context $Guards
    Assert-H1Deadline $Started $Plan.GroupDeadlineSeconds
    foreach($entry in @($measured,$before)){
        Write-NeutralPublication $entry;Read-NeutralPublication $entry
        Assert-H1Deadline $Started $Plan.GroupDeadlineSeconds
    }
    $State.MeasuredReadback=$true
    Add-Member -InputObject $Context NoteProperty LeaseReleaseAttempted $true -Force
    try{Exit-IW7ResourceLease -Token $Context.Lease.Token}
    catch{Add-Member -InputObject $Context NoteProperty LeaseReleaseError $_.Exception.Message -Force;throw}
    $Context.Lease=$null;$State.LeaseReleased=$true
    Write-NeutralPublication $final;Read-NeutralPublication $final
    $State.FinalReadback=$true
    Assert-H1Deadline $Started $Plan.GroupDeadlineSeconds
    $State.LastReadbackDeadlinePassed=$true
    foreach($guard in $original.Streams){$guard.Dispose()}
    for($i=0;$i -lt $original.Streams.Count;$i++){
        if(!$original.Handles[$i].IsClosed -or $original.Streams[$i].CanRead -or $original.Streams[$i].CanWrite -or $original.Streams[$i].CanSeek){throw 'Original guard closure unconfirmed.'}
    }
    $Guards.Clear();$State.GuardsDisposed=$true
    if(!$Context.Closed -or $null -ne $Context.Lease -or !$State.LeaseReleased -or !$State.FinalReadback -or
       !$State.LastReadbackDeadlinePassed -or !$State.GuardsDisposed -or $Guards.Count){throw 'Actual final closure facts required.'}
    $State.Status=if($Failure){'FailedClosed'}else{'Passed'};$State.CanExit=$true
}
function Complete-PlayerAuthoredFinalization($Plan,$State,$Context,$Guards,[Nullable[double]]$Started,$Failure,[bool]$Created) {
    # This function is also exercised directly by the light Source causals.
    $originalOwner=$Context.Owner;$originalLease=$Context.Lease
    Add-Member -InputObject $Context NoteProperty FinalizationOwnerReference $originalOwner
    Add-Member -InputObject $Context NoteProperty FinalizationLeaseReference $originalLease
    if(!$Context.Closed -and $Context.Owner){
        try{$Context.Owner.StopAndConfirm(5000);$Context.Closed=$Context.Owner.Closed}
        catch{$State.ClosureError=$_.Exception.Message}
    }
    if($Created -and $Context.Closed -and $Context.Lease){
        try{Complete-NeutralPublication $Plan $State $Context $Guards $Started $Failure}
        catch{
            $State.FinalizationError=$_.Exception.Message
            if(!$State.Contains('Error')){$State.Error=$_.Exception.Message}
        }
    }
    if($State.CanExit){return}
    # A failed publication never owns cleanup of a known-closed original job.
    # Retain a separate state: no normal flags are upgraded by safety teardown.
    $safety=[ordered]@{Status='SafetyPending';LeaseToken=$(if($Context.Lease){$Context.Lease.Token}else{$null});
        TreeClosureConfirmed=$false;LeaseReleased=$false;OriginalClock=$Started;Started=(Get-PlayerAuthoredSafetyClock);
        TeardownSeconds=120;ResourcesClosed=$false;CanExit=$false;NoExitRequired=$true;QualifiesCPP=$false}
    Add-Member -InputObject $Context NoteProperty SafetyClosure $safety
    try{
        if(!$Context.Closed -or ($Context.Owner -and !$Context.Owner.Closed)){throw 'Original owner closure unknown; retain actual job, guards and lease.'}
        $original=Save-PlayerAuthoredGuardReferences $Context $Guards
        $lease=$Context.Lease
        if(![object]::ReferenceEquals($originalOwner,$Context.Owner)){throw 'Original owner reference changed.'}
        if($lease -and (![object]::ReferenceEquals($lease,$originalLease) -or $lease.Token -cne $safety.LeaseToken)){throw 'Original admitted lease reference/token changed.'}
        if($lease){
            if($Context.PSObject.Properties['LeaseReleaseAttempted'] -and $Context.LeaseReleaseAttempted){throw 'Original release already refused; retain its actual lease without retry.'}
            if((Get-PlayerAuthoredSafetyClock)-$safety.Started -ge 120000){throw 'Safety teardown window expired.'}
            Add-Member -InputObject $Context NoteProperty LeaseReleaseAttempted $true -Force
            Complete-H1Stage $Context $safety
            if(!$safety.LeaseReleased -or $null -ne $Context.Lease){throw 'Original lease release refused; retain actual references.'}
        }
        if((Get-PlayerAuthoredSafetyClock)-$safety.Started -ge 120000){throw 'Safety teardown window expired.'}
        foreach($guard in $original.Streams){$guard.Dispose()}
        for($i=0;$i -lt $original.Streams.Count;$i++){
            if(!$original.Handles[$i].IsClosed -or $original.Streams[$i].CanRead -or $original.Streams[$i].CanWrite -or $original.Streams[$i].CanSeek){throw 'Original safety FS/SFH closure unconfirmed.'}
        }
        $Guards.Clear();$safety.ResourcesClosed=$true;$safety.Status='SafetyResourcesClosedNoExitRetained'
    }catch{$safety.TeardownError=$_.Exception.Message;$safety.Status='SafetyUnknownRetained'}
    $State.Status=if($Context.Closed -and $null -eq $Context.Lease){'ClosedFinalizationIncomplete'}else{'UnknownRetained'}
    $State.CanExit=$false
    # Optional fallback is bounded in-memory Source metadata, never another disk
    # dependency on the publication which just refused. No native scan/hash.
    try{
        $attestation=[ordered]@{Schema='iw7.authored-safety-attestation/1';Status=$safety.Status;
            OriginalStatus=$State.Status;PrimaryError=$(if($State.Contains('Error')){([string]$State.Error).Substring(0,[math]::Min(4096,([string]$State.Error).Length))}else{$null});
            OriginalClock=$Started;OriginalExpired=$(if($null -eq $Started){$null}else{(Get-PlayerAuthoredSafetyClock)-$Started -ge 600000});
            OriginalOwnerClosed=$Context.Closed;LeaseNull=($null -eq $Context.Lease);GuardsRemaining=$Guards.Count;
            ResourcesClosed=$safety.ResourcesClosed;NormalMeasuredReadback=$State.MeasuredReadback;NormalFinalReadback=$State.FinalReadback;
            NativeInputsReverified=$State.NativeInputsReverified;CanExit=$false;NoExitRequired=$true;QualifiesCPP=$false}
        $text=$attestation|ConvertTo-Json -Depth 6 -Compress
        if($text.Length -ge 256KB -or [Text.Encoding]::UTF8.GetByteCount($text) -ge 256KB){throw 'Safety attestation exceeds Source bound.'}
        Add-Member -InputObject $Context NoteProperty SafetyAttestation $attestation
    }catch{$safety.AttestationError=$_.Exception.Message}
}
function Assert-PlayerOwnedInputPassed($Plan,$State) {
    $names=@('helper-compile','helper-link','helper-test','weapon-core','attachment-core','fixture-compile','fixture-link','fixture-test')
    if($Plan.Schema -cne 'iw7.authored-owned-input-core-cpp-source/1' -or !$State.HelperLinked -or !$State.CoresLinked -or
       (@($State.Stages.Name)-join '|') -cne ($names-join '|') -or
       $State.Stages[2].Checks -ne 6 -or $State.Stages[7].Checks -ne 8){throw 'J8 requires both fresh links and both complete probes.'}
    foreach($stage in $State.Stages){
        if($stage.TreeClosureConfirmed -isnot [bool] -or !$stage.TreeClosureConfirmed -or $stage.ExitCode -ne 0){throw 'Every original J8 stage must exit zero with known closure.'}
    }
}
function Assert-PlayerOwnedInputLinkResponses($Plan) {
    # Exact J8 linker Source grammar from the retained J7 fixture-link response.
    # Paths here are declaration strings only: NEVER open/stat/hash a library.
    if($Plan.RunRoot -isnot [string] -or ![IO.Path]::IsPathFullyQualified($Plan.RunRoot) -or
       [IO.Path]::GetFullPath($Plan.RunRoot) -cne $Plan.RunRoot -or $Plan.RunRoot -match '["\x00-\x1f]'){throw 'Canonical J8 linker output root required.'}
    $libraries=@()
    foreach($name in 'LIBCMT.LIB','LIBCPMT.LIB','LIBVCRUNTIME.LIB','OLDNAMES.LIB','LIBUCRT.LIB','KERNEL32.LIB','USER32.LIB'){
        $pins=@($Plan.RetainedInputPins|Where-Object {$_.InputRole -ceq 'FixtureLinkInput' -and [IO.Path]::GetFileName($_.Path) -ieq $name})
        if($pins.Count -ne 1){throw 'One exact declared J8 linker library per fixed Source role required.'}
        $pin=$pins[0]
        if($pin.Path -isnot [string] -or ![IO.Path]::IsPathFullyQualified($pin.Path) -or
           [IO.Path]::GetFullPath($pin.Path) -cne $pin.Path -or $pin.Path -match '["\x00-\x1f]' -or
           ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -le 0 -or
           $pin.SHA256 -cnotmatch '\A[0-9a-f]{64}\z') {throw 'Canonical J8 linker library declaration required.'}
        $libraries+=@($pin.Path)
    }
    foreach($program in 'helper','fixture'){
        $name=$program+'-link';$root=Join-Path $Plan.RunRoot $name
        $objects=if($program -ceq 'helper'){@((Join-Path $Plan.RunRoot 'helper-compile/helper.obj'))}
            else{@((Join-Path $Plan.RunRoot 'weapon-core/weapon-core.obj'),(Join-Path $Plan.RunRoot 'attachment-core/attachment-core.obj'),(Join-Path $Plan.RunRoot 'fixture-compile/fixture.obj'))}
        $response='/NOLOGO /INCREMENTAL:NO /DEBUG /MACHINE:X64 /SUBSYSTEM:CONSOLE /WX /NODEFAULTLIB /OUT:"'+
            (Join-Path $root ($program+'.exe'))+'" /PDB:"'+(Join-Path $root ($program+'.pdb'))+'" '+
            (@(@($objects)+$libraries|ForEach-Object {'"'+$_+'"'}) -join ' ')+"`n"
        $pins=@($Plan.PreparedBindings|Where-Object Path -CEQ (Join-Path $Plan.PreparedRoot ($name+'.rsp')))
        if($pins.Count -ne 1){throw 'One complete J8 linker response Source pin required.'}
        $text=Read-PlayerAuthoredSource $pins[0].Path $pins[0].SHA256 $pins[0].Bytes
        if($text.Replace("`r`n","`n") -cne $response){throw 'Exact J8 linker response requires only its fresh objects, fixed flags/libraries and own outputs.'}
    }
}
function Assert-PlayerOwnedInputProviderGraph($Plan,$Texts) {
    # AST/Source only: NEVER dot these Sources, compile them or resolve an opaque provider.
    $pin=$Plan.CurrentProviderSourceSnapshot
    $snapshot=Read-PlayerAuthoredSource $pin.Path $pin.SHA256 $pin.Bytes|ConvertFrom-Json -Depth 30
    if($snapshot.CanonicalOwnerRevisions.'x64-zt-extensions' -cne $Plan.SourceHead -or
       $snapshot.CanonicalOwnerRevisions.'iw7-mod-components' -cne 'efe6761bc6a96581140767bde9f82816af579375' -or
       @($snapshot.Entries).Count -ne 11 -or $Texts.Count -ne 11){throw 'Exactly eleven explicit current J8 provider Sources required.'}
    $asset='tools-source/asset-bridge/'
    $expected=@(($asset+'t7-iw7/Run-T7Build.ps1'),($asset+'t7-iw7/T7Build.Profile.ps1'),
        ($asset+'h1-fixture/H1Native.Core.ps1'),($asset+'h1-fixture/H1Native.Compiler.ps1'),
        ($asset+'h1-fixture/H1Native.JobMembers.cs'),($asset+'surfaces/MaterialV2.Compiler.ps1'),
        'ops/Resource-Scheduler.Core.ps1','ops/Resource-Memory.ps1','ops/native/ResourceMemory.cs',
        'ops/Resource-RecorderOwnedProcess.Core.ps1','ops/Resource-OwnedProcess.Core.ps1')
    $native=@{
        'ops/Resource-Scheduler.Core.ps1'='6ed6d1ec0bbadffd36e1c98bfd412e9575f8f46180d4decb06007e13ddc82d41'
        'ops/Resource-Memory.ps1'='4b38b3a4c5ee5176b98acc392e0855bd26c4df0b1f9d91460ffbdfc429a3a9fd'
        'ops/native/ResourceMemory.cs'='b159804d12ca504cd592f4cdee191a9b68353e9e0117f9045a28a522b25692e9'
        'ops/Resource-RecorderOwnedProcess.Core.ps1'='9bb5edee470ab2c5d5077ce2ce79a3b73ee133f9ace8df45f8cbd4226db36d2b'
        'ops/Resource-OwnedProcess.Core.ps1'='4a897af3916f7937f673ae1597997084729cf9ddfddb611d8480e32ee0cbc6c7'
    }
    $sources=@{}
    foreach($entry in $snapshot.Entries){
        $name=$entry.SourcePath
        if($name -cnotin $expected -or $sources.ContainsKey($name) -or !$Texts.ContainsKey($entry.Path) -or
           @($Plan.ParentBindings|Where-Object {$_.IsText -and $_.Path -ceq $entry.Path -and $_.SHA256 -ceq $entry.SHA256 -and $_.Bytes -eq $entry.Bytes}).Count -ne 1){throw 'Exact unique retained provider Source mapping required.'}
        $text=$Texts[$entry.Path];$sources[$name]=$text
        if($native.ContainsKey($name)){
            $hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($text.Replace("`r`n","`n")))).ToLowerInvariant()
            if($entry.Revision -cne 'efe6761bc6a96581140767bde9f82816af579375' -or $hash -cne $native[$name]){throw 'J8 Native provider Source must retain the explicit efe contract.'}
        }elseif($entry.Revision -cne $Plan.SourceHead){throw 'J8 asset providers must bind the final exact Source head.'}
    }
    foreach($role in @{'Core'='h1-fixture/H1Native.Core.ps1';'CompilerCore'='h1-fixture/H1Native.Compiler.ps1';
        'ObserverSource'='h1-fixture/H1Native.JobMembers.cs';'CompilerPolicySource'='surfaces/MaterialV2.Compiler.ps1';'Profile'='t7-iw7/T7Build.Profile.ps1'}.GetEnumerator()){
        $entry=@($snapshot.Entries|Where-Object SourcePath -CEQ ($asset+$role.Value))
        if($Plan.Providers.($role.Key) -cne $entry[0].Path){throw 'Activated provider role/Source correspondence differs.'}
    }
    $scheduler='ops/Resource-Scheduler.Core.ps1';$owned='ops/Resource-OwnedProcess.Core.ps1';$recorder='ops/Resource-RecorderOwnedProcess.Core.ps1'
    $entry=@($snapshot.Entries|Where-Object SourcePath -CEQ $scheduler)
    if($Plan.Providers.Scheduler -cne $entry[0].Path){throw 'Activated Scheduler Source correspondence differs.'}
    Assert-PlayerOwnedInputProviderAst $sources
}
function Assert-PlayerOwnedInputProviderAst($Sources) {
    # Pure analysis only, never a success token/native permission. Production
    # calls this only after complete original Source binding/pin verification.
    $asset='tools-source/asset-bridge/';$trees=@{}
    foreach($name in $Sources.Keys){
        if($name.EndsWith('.ps1') -and $name -cne ($asset+'t7-iw7/Run-T7Build.ps1')){
            $tokens=$null;$errors=$null
            $trees[$name]=[Management.Automation.Language.Parser]::ParseInput($Sources[$name],[ref]$tokens,[ref]$errors)
            if($errors.Count){throw 'Provider Source AST parse refused.'}
        }
    }
    $scheduler='ops/Resource-Scheduler.Core.ps1';$owned='ops/Resource-OwnedProcess.Core.ps1';$recorder='ops/Resource-RecorderOwnedProcess.Core.ps1'
    $top=@($trees[$scheduler].EndBlock.Statements)
    $dots=@('. "$PSScriptRoot/Resource-Memory.ps1"','. "$PSScriptRoot/Resource-OwnedProcess.Core.ps1"','. "$PSScriptRoot/Resource-RecorderOwnedProcess.Core.ps1"')
    for($i=0;$i -lt 3;$i++){if($top[$i].Extent.Text -cne $dots[$i]){throw 'Exact three transitive scheduler dot Sources required.'}}
    foreach($node in $top|Select-Object -Skip 3){if($node -isnot [Management.Automation.Language.FunctionDefinitionAst]){throw 'No additional scheduler top-level activation allowed.'}}
    foreach($name in $owned,$recorder,'ops/Resource-Memory.ps1'){
        foreach($node in $trees[$name].EndBlock.Statements){if($node -isnot [Management.Automation.Language.FunctionDefinitionAst]){throw 'Transitive provider must remain definitions-only.'}}
    }
    $ownedNames=@('Get-IW7ResourceOwnedProviders','Get-IW7ResourceOwnedDigest','Assert-IW7ResourceOwnedHost','Initialize-IW7ResourceOwnedProvider',
        'Assert-IW7ResourceOwnedProvider','Assert-IW7ResourceAdmissionWitness','Add-IW7ResourceOwnedSuspendedProcess')
    if((@($trees[$owned].EndBlock.Statements.Name)-join '|') -cne ($ownedNames-join '|')){throw 'Exact seven definitions are evaluated, not a whitelist import.'}
    # Both modules are defined transitively; invocation allowlists are EMPTY.
    $forbidden=@($ownedNames)+@($trees[$recorder].EndBlock.Statements.Name)
    $functions=@{};foreach($node in $top|Select-Object -Skip 3){$functions[$node.Name]=$node}
    $allowed=@('Get-IW7ResourceRoot','Get-IW7ResourceSnapshot','Test-IW7ResourceBudget','Get-IW7ResourceProcesses','Test-IW7ResourceIdentity',
        'Get-IW7CanonicalScope','Test-IW7ProcessInScope','Test-IW7ReservedProcess','Invoke-IW7ResourceLock','Read-IW7ResourceState',
        'Save-IW7ResourceState','Get-IW7LeaseLiveProcesses','Remove-IW7FinishedRuntimeLeases','Enter-IW7ResourceLease','Add-IW7ResourceProcess','Exit-IW7ResourceLease')
    $pending=[Collections.Generic.Stack[string]]::new();$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach($name in 'Enter-IW7ResourceLease','Add-IW7ResourceProcess','Exit-IW7ResourceLease'){$pending.Push($name)}
    while($pending.Count){
        $name=$pending.Pop();if(!$seen.Add($name)){continue}
        if($name -cnotin $allowed -or !$functions.ContainsKey($name)){throw 'Build scheduler graph left its closed call allowlist.'}
        foreach($command in $functions[$name].Body.FindAll({param($n)$n -is [Management.Automation.Language.CommandAst]},$true)){
            $target=$command.GetCommandName()
            if(!$target){
                if($name -cne 'Invoke-IW7ResourceLock' -or $command.Extent.Text -cne '& $Body'){throw 'Unknown scheduler dynamic call refused.'}
            }elseif($target -iin $forbidden){throw 'Owned/Recorder invocation allowlist is empty.'}
            elseif($target -ceq 'Invoke-IW7ResourceLock' -and ($command.CommandElements.Count -ne 2 -or
                $command.CommandElements[1] -isnot [Management.Automation.Language.ScriptBlockExpressionAst])){throw 'Build lock requires its original literal scheduler body.'}
            elseif($functions.ContainsKey($target)){$pending.Push($target)}
            elseif($target -cne 'Get-IW7NativeMemorySnapshot' -and $target -cnotin @('Join-Path','Get-CimInstance','ForEach-Object','Where-Object','Add-Member','Get-Content','ConvertFrom-Json','ConvertTo-Json','Test-Path','Start-Sleep','Out-Null')){throw 'Unknown Build scheduler leaf refused.'}
        }
    }
    if($seen.Count -ne $allowed.Count){throw 'Exact recursive Build scheduler allowlist required.'}
    # These four Sources are actually dot-sourced. Close all executable root
    # forms before scanning their function bodies; definitions are not imports.
    foreach($name in @(($asset+'h1-fixture/H1Native.Core.ps1'),($asset+'h1-fixture/H1Native.Compiler.ps1'),($asset+'surfaces/MaterialV2.Compiler.ps1'),($asset+'t7-iw7/T7Build.Profile.ps1'))){
        $tree=$trees[$name];$statements=@($tree.EndBlock.Statements)
        if($tree.ParamBlock -or $tree.BeginBlock -or $tree.ProcessBlock -or $tree.CleanBlock -or
           $tree.DynamicParamBlock -or $tree.UsingStatements.Count -or $tree.Attributes.Count -or !$tree.EndBlock -or ($tree.EndBlock.Traps -and $tree.EndBlock.Traps.Count)){
            throw 'Asset provider gained an unreviewed executable root form.'
        }
        $special=@{}
        if($name -ceq ($asset+'h1-fixture/H1Native.Core.ps1')){$special[0]='Set-StrictMode -Version Latest'}
        if($name -ceq ($asset+'t7-iw7/T7Build.Profile.ps1')){
            $special[0]='$script:T7H1Deadline=${function:Assert-H1Deadline}'
            $special[3]='$script:T7H1Budget=${function:Test-H1Budget}'
        }
        foreach($index in $special.Keys){if($index -ge $statements.Count){throw 'Exact asset provider root definitions required.'}}
        for($index=0;$index -lt $statements.Count;$index++){
            $node=$statements[$index]
            if($special.ContainsKey($index)){
                if($node.Extent.Text -cne $special[$index]){throw 'Asset provider gained an unreviewed top-level activation.'}
            }elseif($node -isnot [Management.Automation.Language.FunctionDefinitionAst]){throw 'Asset provider gained an unreviewed top-level activation.'}
        }
    }
    $dynamic=@('& $BeforeReleaseCheck','& $script:T7H1Deadline $script:T7GroupStarted 600',
        '& $script:T7H1Deadline $Started $Seconds','& $script:T7H1Budget $Plan $State')
    foreach($name in @(($asset+'h1-fixture/H1Native.Core.ps1'),($asset+'h1-fixture/H1Native.Compiler.ps1'),($asset+'surfaces/MaterialV2.Compiler.ps1'),($asset+'t7-iw7/T7Build.Profile.ps1'))){
        foreach($type in $trees[$name].FindAll({param($n)$n -is [Management.Automation.Language.TypeExpressionAst]},$true)){
            if($type.TypeName.FullName -match '(?i)DoomSkinBuild|SkinWriterProcess'){throw 'Forbidden fallback type in activated Source.'}
        }
        foreach($invoke in $trees[$name].FindAll({param($n)$n -is [Management.Automation.Language.InvokeMemberExpressionAst]},$true)){
            if($invoke.Member -is [Management.Automation.Language.StringConstantExpressionAst] -and $invoke.Member.Value -iin @('LoadFrom','LoadFile','Load')){throw 'No replacement assembly Load in activated provider Source.'}
        }
        foreach($command in $trees[$name].FindAll({param($n)$n -is [Management.Automation.Language.CommandAst]},$true)){
            $target=$command.GetCommandName()
            if(($target -and $target -iin $forbidden) -or (!$target -and $command.Extent.Text -cnotin $dynamic) -or
               $command.InvocationOperator -eq [Management.Automation.Language.TokenKind]::Dot -or
               $target -iin @('Add-Type','Import-Module','Invoke-Expression')){throw 'Activated H1 Source gained an unreviewed import/dynamic/Owned/Recorder call.'}
        }
    }
    $factory=@($trees[$asset+'h1-fixture/H1Native.Core.ps1'].EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.FunctionDefinitionAst] -and $_.Name -ceq 'New-H1Owner'})
    if($factory.Count -ne 1 -or ($factory[0].Body.Extent.Text -replace '\s','') -cne '{[IW7.AnimationProbe.NativeJob]::new()}'){throw 'Original H1 NativeJob factory only; no fallback constructor.'}
}
function Assert-PlayerAuthoredHost([string]$Capsule,[bool]$Dot) {
    $argsNow=[Environment]::GetCommandLineArgs()
    if(!$Dot -or !(Get-Variable cohortHostWitness -ErrorAction SilentlyContinue)){throw 'Exact physical NoExit/dot capsule witness required.'}
    $witness=$cohortHostWitness;$command=". '"+$Capsule+"' -Run"
    if($argsNow.Count -ne 6 -or $argsNow[0] -cne $witness.ManagedEntry -or $argsNow[1] -cne '-NoLogo' -or
       $argsNow[2] -cne '-NoProfile' -or $argsNow[3] -cne '-NoExit' -or $argsNow[4] -cne '-Command' -or
       $argsNow[5] -cne $command -or $witness.Command -cne $command -or $witness.Capsule -cne $Capsule -or
       !$witness.NoExit -or !$witness.Dot -or $witness.PID -ne $PID -or
       [Reflection.Assembly]::GetEntryAssembly().Location -cne $witness.ManagedEntry){throw 'Exact physical NoExit/dot capsule arguments required.'}
    $physical=Get-CimInstance Win32_Process -Filter "ProcessId=$PID"
    $process=[Diagnostics.Process]::GetCurrentProcess()
    try{$image=$process.MainModule.FileName;$kernel=$process.StartTime.ToUniversalTime()}finally{$process.Dispose()}
    if(!$physical -or $physical.ExecutablePath -cne $witness.PhysicalImage -or $image -cne $witness.PhysicalImage -or
       $kernel.ToString('o',[cultureinfo]::InvariantCulture) -cne $witness.KernelCreatedUtc -or
       ($physical.CreationDate.ToUniversalTime().Ticks-($physical.CreationDate.ToUniversalTime().Ticks%10)) -ne ($kernel.Ticks-($kernel.Ticks%10))){
        throw 'Same original physical/kernel/CIM capsule identity required.'
    }
    $physical
}

function Assert-AuthoredSourceBindings($Value,[string[]]$Roots) {
    # Pure lexical/tuple checks before a Source pathname can be queried. SDK and
    # third-party declarations cannot be reclassified as DEFAULT-readable Source.
    $all=@($Value.SourceBindings)+@($Value.PreparedBindings)+@($Value.ParentBindings|Where-Object IsText)+@($Value.RunnerBinding)
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($pin in $all){
        if($pin.IsText -isnot [bool] -or !$pin.IsText -or $pin.SHA256 -cnotmatch '\A[0-9a-f]{64}\z' -or $pin.Bytes -lt 1 -or $pin.Bytes -gt 2MB -or
           ![IO.Path]::IsPathFullyQualified($pin.Path) -or [IO.Path]::GetFullPath($pin.Path) -cne $pin.Path -or
           [IO.Path]::GetExtension($pin.Path).ToLowerInvariant() -cnotin @('.json','.py','.ps1','.cs','.hpp','.cpp','.inc','.rsp','.h','.hh','.inl','.vcxproj','.txt','.md')){
            throw 'Canonical bounded explicit Source tuple required before pathname IO.'
        }
        if(!@($roots|Where-Object {$pin.Path.StartsWith($_,[StringComparison]::OrdinalIgnoreCase)}).Count -or !$seen.Add($pin.Path)){
            throw 'Unique owned Source scope required before pathname IO.'
        }
    }
    foreach($name in 'CompilerInputRoleManifest','DirectIncludeClosure','NativeSourceProvenance','CurrentProviderSourceSnapshot','FixtureSourceClosure'){
        $pin=$Value.$name
        $matches=@($Value.PreparedBindings|Where-Object {$_.Path -ceq $pin.Path -and $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256 -and $_.IsText})
        if($pin.IsText -isnot [bool] -or !$pin.IsText -or $matches.Count -ne 1){throw 'Every metadata Source must have one exact retained Prepared binding.'}
    }
}

$plan=Read-PlayerSource $PlanPath $PlanSHA256 | ConvertFrom-Json -Depth 30
if(!$plan.PSObject.Properties['RunnerBinding'] -or $plan.RunnerBinding.Path -cne $PSCommandPath){throw 'Exact specialized runner binding required.'}
$null=Read-PlayerSource $plan.RunnerBinding.Path $plan.RunnerBinding.SHA256 $plan.RunnerBinding.Bytes
if($plan.Schema -cin @('iw7.authored-pair-core-cpp-source/1','iw7.authored-owned-input-core-cpp-source/1')){
$ownedInputProfile=$plan.Schema -ceq 'iw7.authored-owned-input-core-cpp-source/1'
if([IO.Path]::GetFileName($PlanPath) -cne 'cohort-source-plan.json'){throw 'Exact authored Source plan filename required.'}
Assert-AuthoredSourceBindings $plan @((([IO.Path]::GetDirectoryName([IO.Path]::GetDirectoryName($PlanPath)))+[IO.Path]::DirectorySeparatorChar),(([IO.Path]::GetDirectoryName($PSCommandPath))+[IO.Path]::DirectorySeparatorChar))
if($plan.Schema -cnotin @('iw7.authored-pair-core-cpp-source/1','iw7.authored-owned-input-core-cpp-source/1') -or
   $plan.SourceHead -cnotmatch '\A[0-9a-f]{40}\z' -or
   $plan.NativeSourcePin -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
   $plan.RunnerBinding.Path -cne $PSCommandPath -or $plan.Ready -or $plan.CandidateExecuted -or
   $plan.ChecksExecuted -or $plan.TUsCompiled -or $plan.CoresLinked -or $plan.ParentCPPQualificationInherited -or
   $plan.FatalAllocatorClosure -or $plan.ActualPairParseActivated -or
   !$plan.NoHistoricalObjects -or !$plan.NoFullCLILink -or !$plan.RealOSAllocatorRequested -or
   $plan.ChecksAuthored -ne 8 -or $plan.GroupDeadlineSeconds -ne 600 -or
   $plan.OutputLimitBytes -ne 256MB -or $plan.MetadataReserveBytes -ne 1MB -or
   $plan.PhysicalReservationBytes -ne 4GB -or $plan.CommitReservationBytes -ne 6GB -or
   $plan.LogicalFixtureArenaBytes -ne 6208 -or $plan.MaximumSimultaneousFixtureArenas -ne 1 -or
   !$plan.RequireActualDependenciesWithinGuardedSet -or $plan.FixtureCompileProfile -cne 'RealCoreJSONDiagnostics1RealArena'){
    throw 'Exact unqualified authored pair core Source contract required.'
}
$null=Read-PlayerAuthoredSource $plan.RunnerBinding.Path $plan.RunnerBinding.SHA256 $plan.RunnerBinding.Bytes
$names=@('weapon-core','attachment-core','fixture-compile','fixture-link','fixture-test','weapondef','weaponattachment','filesystem')
if($ownedInputProfile){
    $names=@('helper-compile','helper-link','helper-test','weapon-core','attachment-core','fixture-compile','fixture-link','fixture-test')
    if(($plan.HelperChecksAuthored -isnot [int] -and $plan.HelperChecksAuthored -isnot [long]) -or $plan.HelperChecksAuthored -ne 6 -or
       ($plan.WrapperTUsRequested -isnot [int] -and $plan.WrapperTUsRequested -isnot [long]) -or $plan.WrapperTUsRequested -ne 0){throw 'Exact J8 helper6/no-wrapper contract required.'}
}
if((@($plan.Stages.Name)-join '|') -cne ($names-join '|') -or @($plan.FixtureCases).Count -ne 8 -or
   @($plan.FixtureCases|Sort-Object -Unique).Count -ne 8){throw 'Exactly eight phases and eight distinct fixture groups required.'}
$expectedObjects=@(
    (Join-Path $plan.RunRoot 'weapon-core/weapon-core.obj'),
    (Join-Path $plan.RunRoot 'attachment-core/attachment-core.obj'),
    (Join-Path $plan.RunRoot 'fixture-compile/fixture.obj'))
if((@($plan.GeneratedLinkInputs)-join '|') -cne ($expectedObjects-join '|')){throw 'Three exact fresh cohort link objects required.'}
$expectedMarker=(@($plan.FixtureCases|ForEach-Object {'PASS '+$_}) -join "`n")+"`nIW7_AUTHORED_PAIR_REAL_CORE_FIXTURE=8`n"
if($ownedInputProfile){
    $fixtureCases=@('sha256_known_vectors','real_pair_and_approved_mutants','same_length_mutant_old_source_pin_refuses','malformed_raw_old_pins_refuse_before_decode',
        'real_maps_outlive_roots_first_pointer_wins','checked_capacity_failure_unwinds_once','real_second_parser_failure_keeps_primary','bypassed_core_cannot_publish_inventory')
    $helperCases=@('sha256_known_vectors','every_role_before_copy','actual_bounded_addition','pins_and_roles','private_storage_lifetime','standard_memory_unwind')
    if(@($plan.HelperCases).Count -ne 6 -or @($plan.HelperCases|Sort-Object -Unique).Count -ne 6 -or
       (@($plan.FixtureCases)-join '|') -cne ($fixtureCases-join '|') -or
       (@($plan.HelperCases)-join '|') -cne ($helperCases-join '|') -or
       (@($plan.HelperLinkInputs)-join '|') -cne (Join-Path $plan.RunRoot 'helper-compile/helper.obj')){throw 'Exact J8 fixture/helper groups and fresh helper link object required.'}
    $helperMarker=(@($helperCases|ForEach-Object {'PASS '+$_}) -join "`n")+"`nIW7_PAIR_OWNED_INPUT=6`n"
}

for($index=0;$index -lt 8;$index++){
    $stage=$plan.Stages[$index]
    $probe=if($ownedInputProfile){$index -in @(2,7)}else{$index -eq 4}
    $link=if($ownedInputProfile){$index -in @(1,6)}else{$index -eq 3}
    $kind=if($probe){'Probe'}elseif($link){'Link'}else{'Compile'}
    $program=if($ownedInputProfile -and $index -in @(1,2)){'helper'}else{'fixture'}
    $object=if($ownedInputProfile -and $index -eq 0){'helper.obj'}elseif((!$ownedInputProfile -and $index -eq 2) -or ($ownedInputProfile -and $index -eq 5)){'fixture.obj'}else{$stage.Name+'.obj'}
    $artifacts=if($probe){@()}elseif($link){@(($program+'.exe'),($program+'.pdb'))}
        else{@($object,'compile.pdb','dependencies.json')}
    if($stage.Stage -cne $kind -or $stage.DeadlineSeconds -ne $(if($probe){15}else{120}) -or
       (@($stage.Artifacts)-join '|') -cne ($artifacts-join '|')){throw 'Exact phase kind/deadline/artifacts required.'}
    if($probe){
        $checks=if($program -ceq 'helper'){6}else{8};$marker=if($program -ceq 'helper'){$helperMarker}else{$expectedMarker}
        if($stage.Image -cne (Join-Path $plan.RunRoot ($program+'-link/'+$program+'.exe')) -or @($stage.Arguments).Count -ne 0 -or
           $stage.ExpectedChecks -ne $checks -or $stage.ExpectedStdout -cne $marker){throw 'Exact complete requested fixture stdout required.'}
    }else{
        $image=if($link){Join-Path (Split-Path $plan.Compiler -Parent) 'link.exe'}else{$plan.Compiler}
        if($stage.Image -cne $image -or @($stage.Arguments).Count -ne 1 -or
           $stage.Arguments[0] -cne ('@'+(Join-Path $plan.PreparedRoot ($stage.Name+'.rsp')))){throw 'Exact fixed response required.'}
    }
}
foreach($pin in @($plan.SourceBindings)+@($plan.PreparedBindings)){
    $null=Read-PlayerAuthoredSource $pin.Path $pin.SHA256 $pin.Bytes
}
$providers=$plan.Providers
$providerTexts=@{}
$providerPins=@(foreach($pin in @($plan.ParentBindings|Where-Object IsText)){
    $providerTexts[$pin.Path]=Read-PlayerAuthoredSource $pin.Path $pin.SHA256 $pin.Bytes;$pin
})
if($providerPins.Count -ne 11){throw 'All eleven current direct/transitive provider Sources required before imports.'}
foreach($name in 'Core','CompilerCore','ObserverSource','CompilerPolicySource','Scheduler','Profile'){
    if(@($providerPins|Where-Object Path -CEQ $providers.$name).Count -ne 1){throw 'Exact Source provider binding required.'}
}
$rolePin=$plan.CompilerInputRoleManifest
$roles=Read-PlayerAuthoredSource $rolePin.Path $rolePin.SHA256 $rolePin.Bytes|ConvertFrom-Json -Depth 40
if($roles.Schema -cne 'iw7.authored-core-compiler-input-roles/1' -or $roles.OpaqueFilesQueried -or
   $roles.InheritedQualification -or !$roles.AdmissionBeforeOpaqueIO -or
   @($roles.Selected).Count -ne @($plan.RetainedInputPins).Count){throw 'Finite opaque declaration-only roles required.'}
for($index=0;$index -lt @($roles.Selected).Count;$index++){
    $expected=$roles.Selected[$index];$actual=$plan.RetainedInputPins[$index]
    foreach($field in 'Path','Bytes','SHA256','InputRole','DeclaredRoleRoot','ParentPlanSHA256','AdmissionRequired'){
        if($actual.$field -cne $expected.$field){throw 'Retained role/pin tuple differs.'}
    }
    if($actual.PSObject.Properties['IsText'] -or !$actual.AdmissionRequired -or
       $actual.InputRole -cnotin @('CompilerInclude','CompilerRuntime','FixtureLinkInput')){throw 'Opaque input cannot become pre-admission Source.'}
}
$memory=$plan.CheckedMemoryOverlay
if($memory.StagedBytes -ne 11393 -or $memory.StagedSHA256 -cne '8835b6da207f4fb872e199a5f6b86f0d98a8714a1d6a11421ac7e8d19ca766d4' -or
   $memory.ActualActivation){throw 'Unchanged checked-memory overlay required.'}
$fixtureClosurePin=$plan.FixtureSourceClosure
$fixtureClosure=Read-PlayerAuthoredSource $fixtureClosurePin.Path $fixtureClosurePin.SHA256 $fixtureClosurePin.Bytes|ConvertFrom-Json -Depth 40
if($fixtureClosure.Schema -cne 'iw7.authored-fixture-prepared-source-closure/1' -or $fixtureClosure.SourceHead -cne $plan.SourceHead -or
   !$fixtureClosure.SourceOnly -or $fixtureClosure.OpaqueFilesQueried -or !$fixtureClosure.OldFourFileDeclarationSetRefuses -or
   !$fixtureClosure.ActualCompilerDependencySubsetStillRequired -or $fixtureClosure.Ready -or
   @($fixtureClosure.CanonicalSupportFiles).Count -ne $(if($ownedInputProfile){7}else{6}) -or @($fixtureClosure.GeneratedHeaders).Count -ne 2){throw 'Exact six-source and two-generated-header preparation proof required.'}
if($ownedInputProfile){
    $support=@('test_authored_pair_json.cpp','native_pair_session.hpp','native_pair_owned_input.hpp','native_neutral_dependencies.hpp','native_definition_access.hpp','native_weapon_dependencies.inc','native_attachment_dependencies.inc')
    if((@($fixtureClosure.CanonicalSupportFiles)-join '|') -cne ($support-join '|')){throw 'Exact seven J8 canonical support Sources required.'}
    foreach($name in 'test_pair_owned_input.cpp','native_pair_owned_input.hpp'){
        if(@($plan.PreparedBindings|Where-Object Path -CEQ (Join-Path $plan.PreparedRoot $name)).Count -ne 1){throw 'One retained helper TU/header Source required.'}
    }
}
foreach($pin in @($fixtureClosure.VisitedSourceBindings)){
    if(@($plan.PreparedBindings|Where-Object {$_.Path -ceq $pin.Path -and $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256 -and $_.IsText}).Count -ne 1){throw 'Every prepared include Source must be retained before CPP.'}
}
$closurePin=$plan.DirectIncludeClosure
$closure=Read-PlayerAuthoredSource $closurePin.Path $closurePin.SHA256 $closurePin.Bytes|ConvertFrom-Json -Depth 40
if($closure.OpaqueFilesQueried -or !$closure.ActualCompilerDependencySubsetStillRequired -or
   !$closure.NoPostcompileGuardAdds -or $closure.JSONDiagnostics -ne 1){throw 'Declaration-only include closure required.'}
foreach($entry in $closure.DirectIncludeDeclarations){
    $match=@($plan.RetainedInputPins|Where-Object Path -CEQ $entry.Declaration.Path)
    if($match.Count -ne 1 -or $match[0].SHA256 -cne $entry.Declaration.SHA256 -or
       $match[0].Bytes -ne $entry.Declaration.Bytes -or $match[0].InputRole -cne 'CompilerInclude'){throw 'Direct include lacks exact opaque declaration.'}
}
$jsonPin=$plan.JSONBinding.RawDeclaration
$jsonMatch=@($plan.RetainedInputPins|Where-Object {$_.Path -ceq $jsonPin.Path -and $_.Bytes -eq $jsonPin.Bytes -and $_.SHA256 -ceq $jsonPin.SHA256 -and $_.InputRole -ceq 'CompilerInclude'})
if($jsonMatch.Count -ne 1 -or $plan.JSONBinding.Diagnostics -ne 1 -or $plan.JSONBinding.IdentityVerified -or
   $plan.JSONBinding.JSONRevision -cne '484483acad6d562306efc9b3c6d413404f1b1f8a' -or
   $plan.JSONBinding.SourceExpectedLFHash -cne '53855e4a20d7bc92d9624bf0d83fba8e22d0d9de83f9480bd4895651602fa8cc' -or
   $closure.JSONSourceExpectedLFHash -cne $plan.JSONBinding.SourceExpectedLFHash){throw 'Exact still-unverified JSON Source/opaque binding required.'}
foreach($stage in $plan.Stages|Where-Object Stage -CEQ 'Compile'){
    $pin=@($plan.PreparedBindings|Where-Object Path -CEQ (Join-Path $plan.PreparedRoot ($stage.Name+'.rsp')))
    if($pin.Count -ne 1){throw 'One complete response Source pin required.'}
    $text=Read-PlayerAuthoredSource $pin[0].Path $pin[0].SHA256 $pin[0].Bytes
    if($text -cnotmatch '(?:^| )/W4(?: |$)' -or $text -cnotmatch '(?:^| )/WX(?: |$)' -or $text -cnotmatch '(?:^| )/c(?: |$)' -or
       $text.Contains('/MP') -or $text.Contains('/wd4100')){throw 'Single compiler /W4 /WX /c with no warning bypass required.'}
}
if((@($plan.PostflightSources.PSObject.Properties.Name)-join '|') -cne 'Writer|Caller|Bootstrap'){throw 'Three exact postflight Source roles required.'}
foreach($role in 'Writer','Caller','Bootstrap'){
    $pin=$plan.PostflightSources.$role
    if(@($plan.SourceBindings|Where-Object {$_.Path -ceq $pin.Path -and $_.SHA256 -ceq $pin.SHA256 -and $_.Bytes -eq $pin.Bytes}).Count -ne 1){throw 'Postflight Source pin absent.'}
}
if($ownedInputProfile){
    Assert-PlayerOwnedInputLinkResponses $plan
    Assert-PlayerOwnedInputProviderGraph $plan $providerTexts
}
if(Test-Path -LiteralPath $plan.RunRoot){throw 'Fresh exact owned runtime root required.'}
if(!$Run){
    $defaultResult=[ordered]@{Schema='iw7.authored-pair-core-cpp-default/1';PlanSHA256=$PlanSHA256;SourceHead=$plan.SourceHead;
        Stages=8;FixtureGroupsAuthored=8;ProviderSources=$providerPins.Count;OpaqueDeclarations=@($plan.RetainedInputPins).Count;
        ExpectedNoEffects=$true;NativeTypesLoaded=$false;NativeInputsHashed=$false;RunRootCreated=$false;
        LeaseAcquired=$false;CPPExecuted=$false;CoresLinked=$false;ActualPairParseActivated=$false;Ready=$false}
    if($ownedInputProfile){$defaultResult['HelperGroupsAuthored']=6;$defaultResult['WrapperTUsRequested']=0}
    $defaultResult|ConvertTo-Json
    return
}

$capsule=Join-Path ([IO.Path]::GetDirectoryName($PlanPath)) 'invoke-cohort.local.ps1'
if(@($plan.SourceBindings|Where-Object Path -CEQ $capsule).Count -ne 1){throw 'Exact reviewed capsule Source binding required.'}
$physical=Assert-PlayerAuthoredHost $capsule ($MyInvocation.InvocationName -ceq '.')
if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7.H1Diagnostics.JobMembers' -as [type])){throw 'Fresh host required.'}
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards}
$state=[ordered]@{Schema='iw7.player-template-build/1';PlanSHA256=$PlanSHA256;Status='Pending';Stages=[Collections.Generic.List[object]]::new();
    MaxObservedOutputBytes=0L;NativeInputsReverified=$false;MeasuredReadback=$false;FinalReadback=$false;LeaseReleased=$false;GuardsDisposed=$false;CanExit=$false;CoresLinked=$false;Ready=$false;
    Host=[ordered]@{PID=$PID;Image=$physical.ExecutablePath;CreatedUtc=$physical.CreationDate.ToUniversalTime().ToString('o');NoExit=$true;Dot=$true}}
if($ownedInputProfile){$state['HelperLinked']=$false}
$global:IW7PlayerTemplateBuild=[pscustomobject]@{Context=$context;State=$state;Plan=$plan;Guards=$guards}
$failure=$null;$created=$false;$authoredGroupStarted=$null
try{
    # Reverify and retain the SAME read/shareRead streams before source imports,
    # scheduler effects or admission. The bounded source reader is unchanged
    # except for transferring its verified stream to the original guard list.
    foreach($pin in @($plan.SourceBindings)+@($plan.PreparedBindings)+$providerPins+@($plan.RunnerBinding)){
        $null=Read-PlayerAuthoredSource $pin.Path $pin.SHA256 $pin.Bytes $guards
    }
    . $providers.Core
    $plan|Add-Member NoteProperty AuthoredOutputBudget (New-H1AuthoredOutputBudget $plan.RunRoot $plan.Stages)
    $neutralOriginalFactory=${function:New-H1Owner}
    function New-H1Owner {
        Invoke-NeutralFactoryBridge $neutralOriginalFactory $context $neutralStageStarted $stage.DeadlineSeconds $script:T7GroupStarted $plan.GroupDeadlineSeconds
    }
    . $providers.Scheduler
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Build -PhysicalBytes 4GB -CommitBytes 6GB -Owner 'IW7 authored real pair core link and eight groups plus three TUs'
    $state.LeaseToken=$context.Lease.Token;$script:T7GroupStarted=Get-H1Clock;$authoredGroupStarted=$script:T7GroupStarted
    # The source guards acquired before imports remain held through release.
    . $providers.CompilerCore
    . $providers.CompilerPolicySource
    . $providers.Profile
    foreach($pin in $plan.RetainedInputPins){Open-T7Pin $pin $context}
    foreach($pin in @($plan.ParentBindings|Where-Object {-not $_.IsText})){Open-T7Pin $pin $context}
    $assembly=@($plan.ParentBindings|Where-Object Path -IEQ $plan.JobAssembly)
    if($assembly.Count -ne 1){throw 'Exact original-job assembly binding required.'}
    Open-T7Pin $assembly[0] $context
    $jsonExpected=$plan.JSONBinding.RawDeclaration
    $jsonGuards=@($guards|Where-Object {$_.Name -ieq $jsonExpected.Path})
    if($jsonGuards.Count -ne 1){throw 'One original admitted JSON guard required.'}
    $jsonStream=$jsonGuards[0];$jsonStream.Position=0
    $jsonRaw=[byte[]]::new($jsonExpected.Bytes);$jsonUsed=0
    while($jsonUsed -lt $jsonRaw.Length){$jsonRead=$jsonStream.Read($jsonRaw,$jsonUsed,$jsonRaw.Length-$jsonUsed);if($jsonRead -le 0){throw 'Admitted JSON shortened.'};$jsonUsed+=$jsonRead}
    if($jsonStream.ReadByte() -ne -1 -or $jsonStream.Length -ne $jsonExpected.Bytes -or
       [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($jsonRaw)).ToLowerInvariant() -cne $jsonExpected.SHA256){throw 'Same-held admitted JSON raw identity differs.'}
    $jsonText=[Text.UTF8Encoding]::new($false,$true).GetString($jsonRaw).Replace("`r`n","`n")
    if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($jsonText))).ToLowerInvariant() -cne $plan.JSONBinding.SourceExpectedLFHash){throw 'Admitted JSON LF identity differs from reviewed Source pin; no compiler may start.'}
    $jsonStream.Position=0
    [Reflection.Assembly]::LoadFrom($plan.JobAssembly)|Out-Null
    Add-Type -LiteralPath $providers.ObserverSource
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$created=$true
    # H1 compiler consumers use the existing provider fields; no API is changed.
    $plan|Add-Member NoteProperty ObserverSource $providers.ObserverSource -Force
    $plan|Add-Member NoteProperty CompilerPolicySource $providers.CompilerPolicySource -Force
    $plan|Add-Member NoteProperty Bindings (@($plan.ParentBindings)+@($plan.SourceBindings)+@($plan.PreparedBindings)) -Force
    $plan|Add-Member NoteProperty Inputs @($plan.RetainedInputPins) -Force
    foreach($stage in $plan.Stages){
        $neutralStageStarted=Get-H1Clock
        Assert-H1Deadline $neutralStageStarted $stage.DeadlineSeconds
        if(!$context.Closed){throw 'Previous original job must be closed.'}
        # A failed new factory cannot inherit a prior closed owner's evidence.
        $context.Owner=$null
        $script:T7CurrentStage=$stage;$stageRoot=Join-Path $plan.RunRoot $stage.Name
        [IO.Directory]::CreateDirectory($stageRoot)|Out-Null
        $current=[ordered]@{Name=$stage.Name;Stage=$stage.Stage;PlanSHA256=$PlanSHA256;DeadlineSeconds=$stage.DeadlineSeconds;TreeClosureConfirmed=$false;
            MaxObservedOutputBytes=$state.MaxObservedOutputBytes;CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
        $state.Stages.Add($current)
        if($stage.Stage -ceq 'Link'){
            $freshInputs=if($ownedInputProfile -and $stage.Name -ceq 'helper-link'){@($plan.HelperLinkInputs)}else{@($plan.GeneratedLinkInputs)}
            foreach($expectedObject in $freshInputs){
                $produced=@($state.Stages|ForEach-Object {if($_.Contains('Artifacts')){$_.Artifacts}}|Where-Object Path -CEQ $expectedObject)
                if($produced.Count -ne 1){throw 'Each linked object must be freshly produced by this exact cohort.'}
                Open-T7Pin $produced[0] $context
                $plan.Bindings+=@($produced[0])
            }
        }
        $images=if($stage.Stage -ceq 'Probe'){@($state.Stages|ForEach-Object {if($_.Contains('Artifacts')){$_.Artifacts}}|Where-Object Path -IEQ $stage.Image)}
            else{@($plan.Bindings|Where-Object Path -IEQ $stage.Image)}
        if(@($images).Count -ne 1){throw 'One original stage image pin required.'}
        $image=@($images)[0]
        if(!$image){throw 'One original stage image pin required.'}
        $start=New-T7Start $plan $stage $stageRoot
        Invoke-T7OwnedStage $plan $current $context $start $image.SHA256 $stageRoot $neutralStageStarted
        $current.Artifacts=@(Get-H1CompilerArtifacts $plan $context)
        if($stage.Stage -ceq 'Compile'){Assert-T7Dependencies $plan $stageRoot}
        if($stage.Stage -ceq 'Link'){
            if($ownedInputProfile -and $stage.Name -ceq 'helper-link'){$state.HelperLinked=$true}else{$state.CoresLinked=$true}
        }
        if($stage.Stage -ceq 'Probe'){
            $stdout=Join-Path $stageRoot 'stdout.log';$stderr=Join-Path $stageRoot 'stderr.log'
            if((Get-Item -LiteralPath $stdout).Length -gt 2048 -or (Get-Item -LiteralPath $stderr).Length -ne 0 -or
               [IO.File]::ReadAllText($stdout).Replace("`r`n","`n") -cne $stage.ExpectedStdout){throw 'Exact requested native fixture evidence required.'}
            $current.Checks=$stage.ExpectedChecks
        }
        $state.MaxObservedOutputBytes=[math]::Max($state.MaxObservedOutputBytes,$current.MaxObservedOutputBytes)
    }
    foreach($pin in $plan.RetainedInputPins){Open-T7Pin $pin $context}
    foreach($pin in @($plan.SourceBindings)+@($plan.PreparedBindings)+$providerPins){
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
        $null=Read-PlayerAuthoredSource $pin.Path $pin.SHA256 $pin.Bytes
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    }
    if($ownedInputProfile){Assert-PlayerOwnedInputPassed $plan $state}
    $state.NativeInputsReverified=$true;$state.Status='MeasuredPassed'
}catch{$failure=$_;$state.Status='Failed';$state.Error=$_.Exception.Message}
finally{
    Complete-PlayerAuthoredFinalization $plan $state $context $guards $authoredGroupStarted $failure $created
    $state|ConvertTo-Json -Depth 20
}
if($failure){throw $failure}
if(!$state.CanExit){throw 'Original authored result is incomplete; retain physical NoExit and actual references.'}
return
}
if($plan.Schema -cne 'iw7.player-template-cohort-source/1' -or $plan.Ready -or $plan.CandidateExecuted -or
   $plan.WeaponReady -or $plan.PhysicsQualified -or $plan.PAPTransactionQualified -or
   $plan.RetainedObjects -ne 412 -or $plan.LinkedObjectCount -ne 413){throw 'Exact unqualified source cohort required.'}
$names=@('name-compile','name-test','argv-compile','argv-test','iw7','link')
$primaryFixture=($null -ne $plan.PSObject.Properties['PrimaryGuardFixture'])
$pairCLI=($null -ne $plan.PSObject.Properties['PairProfileCLI'])
$definitionCLI=($null -ne $plan.PSObject.Properties['PairDefinitionsCLI'])
if($pairCLI -and ($plan.PairProfileCLI -isnot [bool] -or !$plan.PairProfileCLI -or !$primaryFixture)){throw 'Explicit pair-profile CLI requires the primary fixture profile.'}
if($definitionCLI -and ($plan.PairDefinitionsCLI -isnot [bool] -or !$plan.PairDefinitionsCLI -or !$pairCLI -or !$primaryFixture)){throw 'Explicit neutral definition CLI requires both existing fixture profiles.'}
$argvChecks=if($definitionCLI){28}elseif($pairCLI){18}else{10}
if($pairCLI -and ($plan.Stages[3].ExpectedChecks -isnot [int] -and $plan.Stages[3].ExpectedChecks -isnot [long])){throw 'Scalar integer pair argv fixture count required.'}
if($primaryFixture){
    if($plan.PrimaryGuardFixture -isnot [bool] -or !$plan.PrimaryGuardFixture){throw 'Explicit true primary-guard fixture opt-in required.'}
    $names=@('name-compile','name-test','argv-compile','argv-test','primary-compile','primary-test','iw7','link')
}
if($definitionCLI){$names=@($names[0..5])+@('definition-compile','definition-test')+@($names[6..7])}
if((@($plan.Stages.Name)-join '|') -cne ($names-join '|') -or $plan.Stages[1].ExpectedChecks -ne 8 -or $plan.Stages[3].ExpectedChecks -ne $argvChecks -or
   ($primaryFixture -and (($plan.Stages[5].ExpectedChecks -isnot [int] -and $plan.Stages[5].ExpectedChecks -isnot [long]) -or $plan.Stages[5].ExpectedChecks -ne 36)) -or
   ($definitionCLI -and (($plan.Stages[7].ExpectedChecks -isnot [int] -and $plan.Stages[7].ExpectedChecks -isnot [long]) -or $plan.Stages[7].ExpectedChecks -ne 100))){throw 'Fixed source-selected 8+10-or-18-or-28/36/100 stage sequence required.'}
if($plan.GroupDeadlineSeconds -ne 600 -or $plan.OutputLimitBytes -ne 268435456 -or $plan.MetadataReserveBytes -ne 1048576){throw 'Fixed cohort deadline/output reserve required.'}
$kinds=@('Compile','Probe','Compile','Probe','Compile','Link')
$artifacts=@('name.obj|name.exe|name.pdb|compile.pdb|dependencies.json','','argv.obj|argv.exe|argv.pdb|compile.pdb|dependencies.json','','iw7-player-cli.obj|compile.pdb|dependencies.json','zonetool-iw7-player.exe|zonetool-iw7-player.pdb|zonetool-iw7-player.lib|zonetool-iw7-player.exp')
if($primaryFixture){
    $kinds=@('Compile','Probe','Compile','Probe','Compile','Probe','Compile','Link')
    $artifacts=@($artifacts[0..3])+@('primary.obj|primary.exe|primary.pdb|compile.pdb|dependencies.json','')+@($artifacts[4..5])
}
if($definitionCLI){
    $kinds=@($kinds[0..5])+@('Compile','Probe')+@($kinds[6..7])
    $artifacts=@($artifacts[0..5])+@('definition.obj|definition.exe|definition.pdb|compile.pdb|dependencies.json','')+@($artifacts[6..7])
}
for($index=0;$index -lt $names.Count;$index++){
    $stage=$plan.Stages[$index];$probe=$kinds[$index] -ceq 'Probe'
    if((($primaryFixture -and $index -in @(4,5)) -or ($definitionCLI -and $index -in @(6,7))) -and ($stage.Name -isnot [string] -or $stage.Stage -isnot [string] -or $stage.Image -isnot [string] -or
       $stage.Arguments -isnot [array] -or $stage.Artifacts -isnot [array] -or ($probe -and $stage.ExpectedStdout -isnot [string]))){throw 'Scalar exact primary fixture stage required.'}
    if($stage.Stage -cne $kinds[$index] -or $stage.DeadlineSeconds -ne $(if($probe){15}else{120}) -or
       (@($stage.Artifacts)-join '|') -cne $artifacts[$index]){throw 'Fixed cohort phase/artifacts required.'}
    if($probe){
        $fixture=if($index -eq 1){'name'}elseif($index -eq 3){'argv'}elseif($index -eq 5){'primary'}else{'definition'}
        $expected=if($index -eq 1){"IW7_PLAYER_TEMPLATE_NAME_CHECKS=8`n"}elseif($index -eq 3){"IW7_PLAYER_TEMPLATE_ARGV_CHECKS=$argvChecks`n"}elseif($index -eq 5){"IW7_PLAYER_TEMPLATE_PRIMARY_CHECKS=36`n"}else{"IW7_PLAYER_DEFINITION_READSET_CHECKS=100`n"}
        if($stage.Image -cne (Join-Path (Join-Path $plan.RunRoot "$fixture-compile") "$fixture.exe") -or @($stage.Arguments).Count -ne 0 -or
           $stage.ExpectedStdout -cne $expected){throw 'Fixed cohort probe image/marker required.'}
    }else{
        $rsp=if($index -eq 0){'name'}elseif($index -eq 2){'argv'}elseif($primaryFixture -and $index -eq 4){'primary'}elseif($definitionCLI -and $index -eq 6){'definition'}else{$stage.Name}
        $image=if($stage.Name -ceq 'link'){Join-Path (Split-Path $plan.Compiler -Parent) 'link.exe'}else{$plan.Compiler}
        if($stage.Image -cne $image -or @($stage.Arguments).Count -ne 1 -or $stage.Arguments[0] -cne ('@'+(Join-Path $plan.PreparedRoot "$rsp.rsp"))){throw 'Fixed cohort compiler/link response required.'}
    }
}
if(!$plan.PSObject.Properties['OwnDirectIncludeCoverage'] -or @($plan.OwnDirectIncludeCoverage).Count -lt 1 -or
   @($plan.OwnDirectIncludeCoverage|Where-Object {-not $_.Pinned}).Count -gt 0 -or !$plan.RequireActualDependenciesWithinGuardedSet){throw 'Own IW7 source coverage and future exact dependency guard required.'}
$primaryModule=$false
$pairModule=$false
$definitionModule=$false
foreach($pin in @($plan.SourceBindings)+@($plan.PreparedBindings)){
    $text=Read-PlayerSource $pin.Path $pin.SHA256 $pin.Bytes
    if($pin.Path -ceq (Join-Path $plan.PreparedRoot 'src/zonetool/zonetool/iw7/zonetool.cpp')){
        $primaryModule=$text.Contains('IW7_PLAYER_TEMPLATE_PRIMARY_REFUSAL schema=1') -and $text.Contains('first_failure(reader)')
        $pairModule=$text.Contains('IW7_PLAYER_PAIR_PROFILE donor=cp_zmb') -and $text.Contains('iw7_player_template_cli::pair_selected(args)')
        $definitionModule=$text.Contains('IW7_PLAYER_PAIR_DEFINITIONS donor=cp_zmb') -and $text.Contains('iw7_player_template_cli::definitions_selected(args)') -and $text.Contains('player_definition_readset::with_pair(')
    }
}
if($primaryFixture -ne $primaryModule){throw 'Exact primary module/fixture profile pairing required.'}
if($pairCLI -ne $pairModule){throw 'Exact pair profile CLI/18-check fixture pairing required.'}
if($definitionCLI -ne $definitionModule){throw 'Exact neutral definition CLI/28-argv/100-readset fixture pairing required.'}
if($definitionCLI){Assert-PlayerDefinitionFixture $plan}
$providers=$plan.Providers
$providerPins=@(foreach($name in 'Core','CompilerCore','ObserverSource','CompilerPolicySource','Scheduler','Profile'){
    $pin=@($plan.ParentBindings|Where-Object {$_.Path -ieq $providers.$name -and $_.IsText})
    if($pin.Count -ne 1){throw 'One pinned existing source provider required.'}
    $null=Read-PlayerSource $pin[0].Path $pin[0].SHA256 $pin[0].Bytes;$pin[0]
})
if(Test-Path -LiteralPath $plan.RunRoot){throw 'Fresh owned runtime output required.'}
if(!$Run){
    [ordered]@{Schema='iw7.player-template-build-default/1';PlanSHA256=$PlanSHA256;Stages=$names.Count;NameChecksAuthored=8;ArgvChecksAuthored=$argvChecks;PrimaryChecksAuthored=$(if($primaryFixture){36}else{0});DefinitionChecksAuthored=$(if($definitionCLI){100}else{0});
        DefinitionFixtureSourceVerified=$definitionCLI;ExpectedNoEffects=$true;CandidateBytes=$null;CandidateSHA256=$null;
        NativeTypesLoaded=$false;NativeInputsHashed=$false;RunRootCreated=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json
    return
}
# The physical NoExit/dot host is checked before imports, admission or native IO.
$hostArgs=[Environment]::GetCommandLineArgs()
$commandIndex=[Array]::IndexOf($hostArgs,'-Command')
if('-NoExit' -cnotin $hostArgs -or $commandIndex -lt 0 -or $commandIndex+1 -ge $hostArgs.Length -or
   $hostArgs[$commandIndex+1] -notmatch '^\s*\.\s+' -or $MyInvocation.InvocationName -cne '.'){
    throw 'Fresh physical NoExit host with dot invocation required.'
}
$physical=Get-CimInstance Win32_Process -Filter "ProcessId=$PID"
if(!$physical -or !$physical.ExecutablePath -or !$physical.CreationDate -or $physical.CommandLine -notmatch '(?i)-NoExit\b'){
    throw 'Actual original host identity/NoExit unavailable.'
}
if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7.H1Diagnostics.JobMembers' -as [type])){throw 'Fresh host required.'}
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards}
$state=[ordered]@{Schema='iw7.player-template-build/1';PlanSHA256=$PlanSHA256;Status='Pending';Stages=[Collections.Generic.List[object]]::new();
    MaxObservedOutputBytes=0L;NativeInputsReverified=$false;MeasuredReadback=$false;FinalReadback=$false;LeaseReleased=$false;GuardsDisposed=$false;CanExit=$false;Ready=$false;
    Host=[ordered]@{PID=$PID;Image=$physical.ExecutablePath;CreatedUtc=$physical.CreationDate.ToUniversalTime().ToString('o');NoExit=$true;Dot=$true}}
$global:IW7PlayerTemplateBuild=[pscustomobject]@{Context=$context;State=$state;Plan=$plan;Guards=$guards}
$failure=$null;$created=$false
try{
    # Reverify and retain the SAME read/shareRead streams before source imports,
    # scheduler effects or admission. The bounded source reader is unchanged
    # except for transferring its verified stream to the original guard list.
    foreach($pin in @($plan.SourceBindings)+@($plan.PreparedBindings)+$providerPins+@($plan.RunnerBinding)){
        $null=Read-PlayerSource $pin.Path $pin.SHA256 $pin.Bytes $guards
    }
    . $providers.Core
    . $providers.Scheduler
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Build -PhysicalBytes 4GB -CommitBytes 6GB -Owner $(if($definitionCLI){'IW7 one-TU neutral pair definitions and 8+28+36+100 fixtures'}elseif($pairCLI){'IW7 one-TU pair profile CLI and 8+18+36 fixtures'}elseif($primaryFixture){'IW7 one-TU player template CLI and 8+10+36 fixtures'}else{'IW7 one-TU player template CLI and 8+10 fixtures'})
    $state.LeaseToken=$context.Lease.Token;$script:T7GroupStarted=Get-H1Clock
    # The source guards acquired before imports remain held through release.
    . $providers.CompilerCore
    . $providers.CompilerPolicySource
    . $providers.Profile
    foreach($pin in $plan.RetainedInputPins){Open-T7Pin $pin $context}
    foreach($pin in @($plan.ParentBindings|Where-Object {-not $_.IsText})){Open-T7Pin $pin $context}
    $assembly=@($plan.ParentBindings|Where-Object Path -IEQ $plan.JobAssembly)
    if($assembly.Count -ne 1){throw 'Exact original-job assembly binding required.'}
    Open-T7Pin $assembly[0] $context
    [Reflection.Assembly]::LoadFrom($plan.JobAssembly)|Out-Null
    Add-Type -LiteralPath $providers.ObserverSource
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$created=$true
    # H1 compiler consumers use the existing provider fields; no API is changed.
    $plan|Add-Member NoteProperty ObserverSource $providers.ObserverSource -Force
    $plan|Add-Member NoteProperty CompilerPolicySource $providers.CompilerPolicySource -Force
    $plan|Add-Member NoteProperty Bindings (@($plan.ParentBindings)+@($plan.SourceBindings)+@($plan.PreparedBindings)) -Force
    $plan|Add-Member NoteProperty Inputs @($plan.RetainedInputPins) -Force
    foreach($stage in $plan.Stages){
        if(!$context.Closed){throw 'Previous original job must be closed.'}
        # A failed new factory cannot inherit a prior closed owner's evidence.
        $context.Owner=$null
        $script:T7CurrentStage=$stage;$stageRoot=Join-Path $plan.RunRoot $stage.Name
        [IO.Directory]::CreateDirectory($stageRoot)|Out-Null
        $current=[ordered]@{Name=$stage.Name;Stage=$stage.Stage;PlanSHA256=$PlanSHA256;DeadlineSeconds=$stage.DeadlineSeconds;TreeClosureConfirmed=$false;
            MaxObservedOutputBytes=$state.MaxObservedOutputBytes;CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
        $state.Stages.Add($current)
        $image=if($stage.Stage -ceq 'Probe'){
            $compile=@($state.Stages|Where-Object Name -CEQ ($stage.Name.Replace('-test','-compile')))[0]
            @($compile.Artifacts|Where-Object Path -IEQ $stage.Image)[0]
        }else{@($plan.Bindings|Where-Object Path -IEQ $stage.Image)[0]}
        if(!$image){throw 'One original stage image pin required.'}
        $start=New-T7Start $plan $stage $stageRoot
        Invoke-T7OwnedStage $plan $current $context $start $image.SHA256 $stageRoot (Get-H1Clock)
        $current.Artifacts=@(Get-H1CompilerArtifacts $plan $context)
        if($stage.Stage -ceq 'Compile'){Assert-T7Dependencies $plan $stageRoot}
        if($stage.Stage -ceq 'Probe'){
            $stdout=Join-Path $stageRoot 'stdout.log';$stderr=Join-Path $stageRoot 'stderr.log'
            if((Get-Item -LiteralPath $stdout).Length -gt 128 -or (Get-Item -LiteralPath $stderr).Length -ne 0 -or
               [IO.File]::ReadAllText($stdout).Replace("`r`n","`n") -cne $stage.ExpectedStdout){throw 'Exact requested native fixture evidence required.'}
            $current.Checks=$stage.ExpectedChecks
        }
        $state.MaxObservedOutputBytes=[math]::Max($state.MaxObservedOutputBytes,$current.MaxObservedOutputBytes)
    }
    foreach($pin in $plan.RetainedInputPins){Open-T7Pin $pin $context}
    foreach($pin in @($plan.SourceBindings)+@($plan.PreparedBindings)+$providerPins){
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
        $null=Read-PlayerSource $pin.Path $pin.SHA256 $pin.Bytes
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    }
    $state.NativeInputsReverified=$true;$state.Status='MeasuredPassed'
}catch{$failure=$_;$state.Status='Failed';$state.Error=$_.Exception.Message}
finally{
    if(!$context.Closed -and $context.Owner){try{$context.Owner.StopAndConfirm(5000);$context.Closed=$context.Owner.Closed}catch{$state.ClosureError=$_.Exception.Message}}
    if($created -and $context.Closed -and $context.Lease){
        try{
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            # Observe native outputs once, with the original guards and lease.
            # The three known Source receipts consume the existing reserve;
            # counting them again against the native 64-entry tree cap can fail
            # after release even though every native job already closed.
            $nativeOutputBytes=Measure-H1Output $plan.RunRoot
            if($nativeOutputBytes -gt $plan.OutputLimitBytes-$plan.MetadataReserveBytes){throw 'Native output exceeds reserved budget before publication.'}
            $state.MaxObservedOutputBytes=[math]::Max($state.MaxObservedOutputBytes,$nativeOutputBytes)
            $measured=Join-Path $plan.RunRoot 'measured-before-release.json'
            $raw=[Text.UTF8Encoding]::new($false).GetBytes(($state|ConvertTo-Json -Depth 20)+"`n")
            $hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()
            $before=[ordered]@{Schema='iw7.player-template-build-before-release/1';PlanSHA256=$PlanSHA256;MeasuredSHA256=$hash;
                Host=$state.Host;Status=$state.Status;OriginalRootAndJobClosed=$true;LeaseToken=$context.Lease.Token;
                GuardsHeld=$guards.Count;CandidateExecuted=$false;Ready=$false}
            $beforeFile=Join-Path $plan.RunRoot 'closure-before-release.json'
            $beforeBytes=[Text.UTF8Encoding]::new($false).GetBytes(($before|ConvertTo-Json -Depth 10)+"`n")
            $beforeHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($beforeBytes)).ToLowerInvariant()
            # Preconstruct the final receipt to bound ALL metadata before release.
            # Its release/disposal claims are verified before publication below.
            $closure=[ordered]@{Schema='iw7.player-template-build-closure/1';PlanSHA256=$PlanSHA256;MeasuredSHA256=$hash;
                BeforeReleaseSHA256=$beforeHash;Host=$state.Host;Status='ClosedReleasedPendingPostflight';PostReadbackDeadlineRequired=$true;
                OriginalRootAndJobClosed=$true;LeaseReleased=$true;GuardsDisposed=$true;CandidateExecuted=$false;Ready=$false}
            $final=Join-Path $plan.RunRoot 'final-closure.json';$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($closure|ConvertTo-Json -Depth 10)+"`n")
            $metadataBytes=[long]$raw.Length+$beforeBytes.Length+$bytes.Length
            if($metadataBytes -gt $plan.MetadataReserveBytes -or $nativeOutputBytes+$metadataBytes -gt $plan.OutputLimitBytes){throw 'Three closure receipts exceed reserved output before release.'}
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            $stream=[IO.File]::Open($measured,'CreateNew','Write','Read')
            try{$stream.Write($raw);$stream.Flush($true)}finally{$stream.Dispose()}
            $null=Read-PlayerSource $measured $hash $raw.Length
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            $state.MeasuredReadback=$true
            $stream=[IO.File]::Open($beforeFile,'CreateNew','Write','Read')
            try{$stream.Write($beforeBytes);$stream.Flush($true)}finally{$stream.Dispose()}
            $null=Read-PlayerSource $beforeFile $beforeHash $beforeBytes.Length
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            Exit-IW7ResourceLease -Token $context.Lease.Token;$context.Lease=$null;$state.LeaseReleased=$true
            foreach($guard in $guards){$guard.Dispose()};$guards.Clear();$state.GuardsDisposed=$true
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            if(!$context.Closed -or $null -ne $context.Lease -or $guards.Count -or !$state.LeaseReleased -or !$state.GuardsDisposed){throw 'Actual release/disposal facts required before final Source publication.'}
            # Only this prebounded Source JSON is opened after release.
            $stream=[IO.File]::Open($final,'CreateNew','Write','Read')
            try{$stream.Write($bytes);$stream.Flush($true)}finally{$stream.Dispose()}
            $finalHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            $null=Read-PlayerSource $final $finalHash $bytes.Length
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            $state.Status=if($failure){'FailedClosed'}else{'Passed'}
            $state.FinalReadback=$true;$state.CanExit=$true
        }catch{$state.FinalizationError=$_.Exception.Message;if(!$failure){$failure=$_}}
    }
    if(!$state.CanExit){
        $state.Status=if($context.Closed -and $state.LeaseReleased){'ClosedFinalizationIncomplete'}else{'UnknownRetained'}
        $state.CanExit=$false
    }
    $state|ConvertTo-Json -Depth 20
}
if($failure){throw $failure}
