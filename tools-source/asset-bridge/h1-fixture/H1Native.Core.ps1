# Functions only. Importing this file does not load native types or touch leases.
Set-StrictMode -Version Latest
function Assert-H1Path([string]$Path) {
    if(![IO.Path]::IsPathFullyQualified($Path) -or [IO.Path]::GetFullPath($Path) -cne $Path -or $Path -match '["\r\n]') {throw 'Canonical absolute path required.'}
    for($part=$Path;$part;$part=[IO.Path]::GetDirectoryName($part)) {
        if(Test-Path -LiteralPath $part) {
            if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Reparse ancestry refused.'}
        }
    }
}
function Open-H1Pin($Pin) {
    Assert-H1Path $Pin.Path
    if($Pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or $Pin.Bytes -lt 0 -or $Pin.Bytes -gt 64MB){throw 'Invalid bounded binding.'}
    $guard=[IO.FileStream]::new($Pin.Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        if($guard.Length -ne $Pin.Bytes){throw 'Bound input length differs.'}
        $hash=[Security.Cryptography.SHA256]::Create()
        try {$actual=[Convert]::ToHexString($hash.ComputeHash($guard)).ToLowerInvariant()} finally {$hash.Dispose()}
        if($actual -cne $Pin.SHA256 -or $guard.Length -ne $Pin.Bytes){throw 'Bound input hash/length differs.'}
        Assert-H1Path $Pin.Path
        $guard.Position=0
        return $guard
    }catch{$guard.Dispose();throw}
}
function Read-H1SmallJson([string]$Path,[int]$Limit=128KB) {
    Assert-H1Path $Path
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read')
    try {
        if($stream.Length -gt $Limit){throw 'JSON input exceeds bound.'}
        $bytes=[byte[]]::new($Limit+1);$used=0
        do {$read=$stream.Read($bytes,$used,$bytes.Length-$used);$used+=$read} while($read -gt 0 -and $used -lt $bytes.Length)
        if($used -gt $Limit){throw 'JSON input grew above bound.'}
        [Text.Encoding]::UTF8.GetString($bytes,0,$used)|ConvertFrom-Json -Depth 20
    }finally{$stream.Dispose()}
}
function Assert-H1OutputName([string]$Name) {
    # Win32 treats trailing dots/spaces, devices and streams as aliases.
    if([string]::IsNullOrWhiteSpace($Name) -or $Name -in @('.','..') -or
       $Name -match '[<>:"/\\|?*\x00-\x1f]' -or $Name -match '[. ]$' -or
       $Name.Split('.')[0].TrimEnd(' ','.') -match '^(?i:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])$'){
        throw 'Ordinary unaliased Win32 output component required.'
    }
}
function New-H1AuthoredOutputBudget([string]$Root,$Stages) {
    # Pure Source derivation. There is no caller-selected numeric entry limit.
    if($Root -cnotmatch '^[A-Za-z]:\\' -or [IO.Path]::GetFullPath($Root) -cne $Root -or
       $Root.EndsWith('\') -or $Root.Contains('/')){throw 'Canonical owned Win32 output root required.'}
    foreach($component in $Root.Substring(3).Split('\')){Assert-H1OutputName $component}
    $names=@('weapon-core','attachment-core','fixture-compile','fixture-link','fixture-test','weapondef','weaponattachment','filesystem')
    $ownedNames=@('helper-compile','helper-link','helper-test','weapon-core','attachment-core','fixture-compile','fixture-link','fixture-test')
    $owned=(@($Stages.Name)-join '|') -ceq ($ownedNames-join '|')
    if(@($Stages).Count -ne 8 -or (!$owned -and (@($Stages.Name)-join '|') -cne ($names-join '|'))){throw 'Only the exact authored eight-stage output profiles are supported.'}
    $entries=[Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
    $roots=[Collections.Generic.List[string]]::new()
    for($i=0;$i -lt 8;$i++){
        $stage=$Stages[$i];Assert-H1OutputName $stage.Name
        if($owned){
            $kind=if($i -in @(2,7)){'Probe'}elseif($i -in @(1,6)){'Link'}else{'Compile'}
            $expected=if($kind -ceq 'Probe'){@()}elseif($i -eq 1){@('helper.exe','helper.pdb')}
                elseif($i -eq 6){@('fixture.exe','fixture.pdb')}
                else{@($(if($i -eq 0){'helper.obj'}elseif($i -eq 5){'fixture.obj'}else{$stage.Name+'.obj'}),'compile.pdb','dependencies.json')}
        }else{
            $expected=if($i -eq 4){@()}elseif($i -eq 3){@('fixture.exe','fixture.pdb')}
                else{@($(if($i -eq 2){'fixture.obj'}else{$stage.Name+'.obj'}),'compile.pdb','dependencies.json')}
            $kind=if($i -eq 4){'Probe'}elseif($i -eq 3){'Link'}else{'Compile'}
        }
        if($stage.Stage -cne $kind -or (@($stage.Artifacts)-join '|') -cne ($expected-join '|')){throw 'Exact declared authored output types/artifacts required.'}
        $stageRoot=Join-Path $Root $stage.Name
        $entries.Add($stageRoot,'Directory');$roots.Add($stageRoot)
        foreach($name in @($stage.Artifacts)+@('stdout.log','stderr.log')){
            Assert-H1OutputName $name
            $entries.Add((Join-Path $stageRoot $name),'File')
        }
    }
    foreach($name in @('measured-before-release.json','closure-before-release.json','final-closure.json','stop.request')){
        $entries.Add((Join-Path $Root $name),'File')
    }
    $declared=if($owned){44}else{48};$files=if($owned){36}else{40}
    if($entries.Count -ne $declared -or @($entries.Values|Where-Object {$_ -ceq 'File'}).Count -ne $files){throw 'Exact authored output shape required.'}
    [pscustomobject]@{Schema=$(if($owned){'iw7.h1-owned-input-output-budget/1'}else{'iw7.h1-authored-output-budget/1'});Root=$Root;
        Entries=[Collections.ObjectModel.ReadOnlyDictionary[string,string]]::new($entries);
        StageRoots=$roots.AsReadOnly();Stages=$Stages;ResidualEntries=64;MaximumDepth=64}
}
function Assert-H1AuthoredOutputBudget([string]$Root,$Budget) {
    $expected=New-H1AuthoredOutputBudget $Root $Budget.Stages
    if($Budget.Schema -cne $expected.Schema -or $Budget.Root -cne $Root -or
       $Budget.Entries.Count -ne $expected.Entries.Count -or $Budget.StageRoots.Count -ne 8 -or
       $Budget.ResidualEntries -ne 64 -or $Budget.MaximumDepth -ne 64){throw 'Reviewed derived authored output budget required.'}
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($pair in $Budget.Entries.GetEnumerator()){
        if($pair.Key -isnot [string] -or $pair.Value -isnot [string] -or
           [IO.Path]::GetFullPath($pair.Key) -cne $pair.Key -or !$seen.Add($pair.Key) -or $seen.Count -gt $expected.Entries.Count -or
           !$expected.Entries.ContainsKey($pair.Key) -or !@($expected.Entries.Keys|Where-Object {$_ -ceq $pair.Key}).Count -or
           $expected.Entries[$pair.Key] -cne $pair.Value){
            throw 'Authored declared output set/types/aliases differ from the exact Source profile.'
        }
    }
    if($seen.Count -ne $expected.Entries.Count){throw 'Authored declared output set/types/aliases differ from the exact Source profile.'}
    $seen.Clear()
    foreach($stageRoot in $Budget.StageRoots){
        if($stageRoot -isnot [string] -or [IO.Path]::GetFullPath($stageRoot) -cne $stageRoot -or
           !$seen.Add($stageRoot) -or $seen.Count -gt 8 -or !@($expected.StageRoots|Where-Object {[string]::Equals($_,$stageRoot,[StringComparison]::Ordinal)}).Count){
            throw 'Authored stage root set/aliases differ from the exact Source profile.'
        }
    }
    if($seen.Count -ne 8){throw 'Authored stage root set/aliases differ from the exact Source profile.'}
    # Measure with the fresh immutable derivation, not the caller's mutable map.
    $expected
}
function Measure-H1AuthoredOutput([string]$Root,$Budget) {
    $Budget=Assert-H1AuthoredOutputBudget $Root $Budget
    Assert-H1Path $Root
    $pending=[Collections.Generic.Stack[object]]::new();$pending.Push(@($Root,0))
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $total=0L;$residual=0
    while($pending.Count){
        $directory=$pending.Pop()
        foreach($entry in [IO.Directory]::EnumerateFileSystemEntries($directory[0])){
            if(!$seen.Add($entry) -or $seen.Count -gt ($Budget.Entries.Count+64)){throw 'Authored output entry total or case alias refused.'}
            Assert-H1OutputName ([IO.Path]::GetFileName($entry))
            if([IO.Path]::GetFullPath($entry) -cne $entry){throw 'Canonical output entry required.'}
            $declared=$Budget.Entries.ContainsKey($entry)
            if(!$declared){
                if(!@($Budget.StageRoots|Where-Object {$entry.StartsWith($_+'\',[StringComparison]::OrdinalIgnoreCase)}).Count){throw 'Undeclared root output refused.'}
                if(++$residual -gt 64){throw 'Authored group residual output entry count exceeded 64.'}
            }
            $attributes=[IO.File]::GetAttributes($entry)
            if($attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Output reparse entry refused before descent.'}
            $isDirectory=($attributes -band [IO.FileAttributes]::Directory) -ne 0
            if($declared -and (($Budget.Entries[$entry] -ceq 'Directory') -ne $isDirectory)){throw 'Declared output file/directory type differs.'}
            if($isDirectory){
                if($directory[1]+1 -gt 64){throw 'Authored output depth exceeded 64.'}
                $pending.Push(@($entry,($directory[1]+1)))
            }else{$total+=([IO.FileInfo]$entry).Length}
        }
    }
    $total
}
function Measure-H1Output([string]$Root,$EntryBudget=$null) {
    if($null -ne $EntryBudget){return Measure-H1AuthoredOutput $Root $EntryBudget}
    Assert-H1Path $Root
    $pending=[Collections.Generic.Stack[string]]::new();$pending.Push($Root)
    $total=0L;$count=0
    while($pending.Count) {
        foreach($entry in [IO.Directory]::EnumerateFileSystemEntries($pending.Pop())) {
            if(++$count -gt 64){throw 'Output entry count exceeded 64.'}
            $attributes=[IO.File]::GetAttributes($entry)
            if($attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Output reparse entry refused before descent.'}
            if($attributes -band [IO.FileAttributes]::Directory){$pending.Push($entry)}
            else {$total+=([IO.FileInfo]$entry).Length}
        }
    }
    $total
}
function Get-H1Clock { [Diagnostics.Stopwatch]::GetTimestamp()/([double][Diagnostics.Stopwatch]::Frequency)*1000 }
function Assert-H1Deadline($Started,[int]$Seconds) {
    if((Get-H1Clock)-$Started -ge $Seconds*1000){throw 'Stage deadline exceeded.'}
}
function Resolve-H1AuthoredPlanOutputBudget($Plan) {
    # Pure Source contract only: no filesystem measurement, telemetry or owner.
    $schemaProperty=$Plan.PSObject.Properties['Schema']
    $budgetProperty=$Plan.PSObject.Properties['AuthoredOutputBudget']
    if(!$budgetProperty){
        if($schemaProperty -is [Management.Automation.PSNoteProperty] -and
           $schemaProperty.Value -is [string] -and $schemaProperty.Value -ceq 'iw7.authored-preflight-real-core-cpp-source/1'){
            throw 'The authored preflight profile requires its derived output budget.'
        }
        return $null # Existing callers without a budget retain legacy64TOTAL.
    }
    if($schemaProperty -isnot [Management.Automation.PSNoteProperty] -or $schemaProperty.Value -isnot [string] -or
       $budgetProperty -isnot [Management.Automation.PSNoteProperty]){throw 'Literal authored schema and budget NoteProperties required.'}
    $profile=switch -CaseSensitive ($schemaProperty.Value){
        'iw7.authored-pair-core-cpp-source/1' {'iw7.h1-authored-output-budget/1'}
        'iw7.authored-owned-input-core-cpp-source/1' {'iw7.h1-owned-input-output-budget/1'}
        'iw7.authored-preflight-real-core-cpp-source/1' {'iw7.h1-owned-input-output-budget/1'}
        default {throw 'Only the authored eight-stage cohort may select its output budget.'}
    }
    $budget=$budgetProperty.Value
    foreach($name in 'RunRoot','Stages'){
        if($Plan.PSObject.Properties[$name] -isnot [Management.Automation.PSNoteProperty]){throw 'Literal authored plan values required.'}
    }
    foreach($name in 'Schema','Root','Entries','StageRoots','Stages','ResidualEntries','MaximumDepth'){
        if($budget.PSObject.Properties[$name] -isnot [Management.Automation.PSNoteProperty]){throw 'Literal derived budget values required.'}
    }
    $entries=$budget.PSObject.Properties['Entries'].Value
    $roots=$budget.PSObject.Properties['StageRoots'].Value
    if($entries -isnot [Collections.ObjectModel.ReadOnlyDictionary[string,string]] -or
       $roots -isnot [Collections.ObjectModel.ReadOnlyCollection[string]] -or
       $entries.PSObject.Methods['GetType'] -isnot [Management.Automation.PSMethod] -or
       $roots.PSObject.Methods['GetType'] -isnot [Management.Automation.PSMethod] -or
       $entries.GetType() -ne [Collections.ObjectModel.ReadOnlyDictionary[string,string]] -or
       $roots.GetType() -ne [Collections.ObjectModel.ReadOnlyCollection[string]]){
        throw 'Exact factory output collection types required before observation.'
    }
    foreach($collection in @($entries,$roots)){
        if($collection.PSObject.Properties['Count'] -isnot [Management.Automation.PSProperty] -or
           $collection.PSObject.Methods['GetEnumerator'] -isnot [Management.Automation.PSMethod]){
            throw 'Ordinary factory collection members required before observation.'
        }
    }
    if($Plan.RunRoot -isnot [string] -or $budget.Schema -isnot [string] -or $budget.Root -isnot [string] -or
       $budget.ResidualEntries -isnot [int] -or
       $budget.MaximumDepth -isnot [int]){throw 'Strict authored output root and integer bounds required.'}
    foreach($stages in @($Plan.Stages,$budget.Stages)){
        if($stages -isnot [array]){throw 'Exact authored stage arrays required.'}
        foreach($stage in $stages){
            foreach($name in 'Name','Stage','Artifacts'){
                if($stage.PSObject.Properties[$name] -isnot [Management.Automation.PSNoteProperty]){throw 'Literal authored stage values required.'}
            }
            if($stage.Name -isnot [string] -or $stage.Stage -isnot [string] -or $stage.Artifacts -isnot [array] -or
               @($stage.Artifacts|Where-Object {$_ -isnot [string]}).Count){throw 'Strict authored stage names, kinds and artifact arrays required.'}
        }
    }
    $expected=New-H1AuthoredOutputBudget $Plan.RunRoot $Plan.Stages
    if($expected.Schema -cne $profile){throw 'Exact authored plan/output profile correspondence required.'}
    $verified=Assert-H1AuthoredOutputBudget $Plan.RunRoot $budget
    if($verified.Schema -cne $expected.Schema){throw 'Supplied authored budget differs from the plan output profile.'}
    return $expected # Fresh read-only entry derivation, never the supplied map.
}
function Test-H1Budget($Plan,$State) {
    $expected=Resolve-H1AuthoredPlanOutputBudget $Plan
    $bytes=Measure-H1Output $Plan.RunRoot $expected
    $State.MaxObservedOutputBytes=[math]::Max($State.MaxObservedOutputBytes,$bytes)
    if($bytes -gt $Plan.OutputLimitBytes-$Plan.MetadataReserveBytes){throw 'Output budget exceeded; preserve diagnostics.'}
    $snapshot=Get-IW7ResourceSnapshot
    if(!$snapshot -or $snapshot.CommitLimit -le 0 -or $snapshot.Committed -lt 0 -or
       $snapshot.Committed -gt $snapshot.CommitLimit){throw 'Invalid fresh memory telemetry.'}
    # Owner GO 2026-10-13: system memory percentages are telemetry only. Keep
    # one current observation, not an unbounded history or a numeric stop policy.
    $observation=[ordered]@{Policy='TelemetryOnly';ObservedUtc=[datetime]::UtcNow.ToString('o');
        Snapshot=$snapshot;CommitUsedPercent=[math]::Round(100*$snapshot.Committed/$snapshot.CommitLimit,2)}
    if($State -is [Collections.IDictionary]){$State['LastMemoryObservation']=$observation}
    else {Add-Member -InputObject $State -NotePropertyName LastMemoryObservation -NotePropertyValue $observation -Force}
}
function Register-H1Original($Lease,$Identity) {
    # Register only the original handle tuple, never adopt a PID's new occupant.
    Invoke-IW7ResourceLock {
        $registry=Read-IW7ResourceState
        $rows=@($registry.Leases|Where-Object Token -CEQ $Lease.Token)
        if($rows.Count -ne 1 -or $rows[0].Kind -cne $Lease.Kind -or $rows[0].Scope -ine $Lease.Scope){throw 'Exact stage lease missing.'}
        $matches=@(Get-IW7ResourceProcesses|Where-Object PID -EQ $Identity.PID)
        if($matches.Count -ne 1 -or !(Test-IW7ResourceIdentity $Identity $matches[0])){throw 'Original process differs from scheduler observation.'}
        $rows[0].Processes=@($matches[0]);$rows[0].Phase='Running'
        Save-IW7ResourceState $registry
    }
}
function New-H1Owner { [IW7.AnimationProbe.NativeJob]::new() }
function Invoke-H1OwnedStage($Plan,$State,$Context,$Start,[string]$ImageSHA256,[string]$StageRoot,[Nullable[double]]$AdmittedStarted=$null) {
    $started=if($null -eq $AdmittedStarted){Get-H1Clock}else{[double]$AdmittedStarted}
    $State.StartedUtc=[datetime]::UtcNow.ToString('o')
    Assert-H1Deadline $started $State.DeadlineSeconds
    $Context.Closed=$false
    $Context.Owner=New-H1Owner # Keep the owner before Start can partially fail.
    $Context.Owner.Start($Start,$ImageSHA256,(Join-Path $StageRoot 'stdout.log'),(Join-Path $StageRoot 'stderr.log'))
    Assert-H1Deadline $started $State.DeadlineSeconds
    $State.Identity=[ordered]@{PID=$Context.Owner.PID;Image=$Context.Owner.Image;
        CreatedUtc=[datetime]::FromFileTimeUtc($Context.Owner.CreationFileTime).ToString('o')}
    if($State.Identity.Image -ine $Start.FileName){throw 'Original child image differs.'}
    try {Register-H1Original $Context.Lease $State.Identity;$State.Registration='Registered'}
    catch {
        $State.RegistrationError=$_.Exception.Message
        if(!$Context.Owner.TreeExited()){throw}
        $State.Registration='Original job already empty before CIM registration'
    }
    Assert-H1Deadline $started $State.DeadlineSeconds
    while($true) {
        Test-H1Budget $Plan $State
        Assert-H1Deadline $started $State.DeadlineSeconds
        if($State.Stage -ceq 'Compile') {
            $sample=Get-H1OriginalState $Context.Owner
            $State.LastOriginalSnapshot=$sample
            Assert-H1Deadline $started $State.DeadlineSeconds
            if(Complete-H1CompilerTelemetry $Plan $State $Context $sample $started){continue}
        }
        $empty=$Context.Owner.TreeExited()
        Assert-H1Deadline $started $State.DeadlineSeconds
        if($empty) {
            $Context.Owner.CloseConfirmed();$Context.Closed=$Context.Owner.Closed
            $State.TreeClosureConfirmed=$Context.Closed;$State.ExitCode=$Context.Owner.ExitCode
            if($State.Stage -ceq 'Compile' -and (!$sample.RootExited -or $sample.RootExitCode -ne 0 -or $sample.ActiveProcesses -ne 0)){
                throw 'Fresh original compiler root0/Active0 sample required.'
            }
            Assert-H1Deadline $started $State.DeadlineSeconds
            $State.ElapsedMs=(Get-H1Clock)-$started
            if(!$Context.Closed -or $State.ExitCode -ne 0){throw 'Original stage process failed.'}
            return
        }
        if(Test-Path -LiteralPath (Join-Path $Plan.RunRoot 'stop.request')){throw 'Coordinator stop requested.'}
        Start-Sleep -Milliseconds 100
        Assert-H1Deadline $started $State.DeadlineSeconds
    }
}
function Complete-H1Stage($Context,$State,[scriptblock]$BeforeReleaseCheck=$null) {
    if(!$Context.Closed) {
        try {
            if(!$Context.Owner){throw 'Owner unavailable after creation attempt; closure unknown.'}
            $State.TerminationRequested=$true
            $Context.Owner.StopAndConfirm(5000)
            $Context.Closed=$Context.Owner.Closed
            if(!$Context.Closed){throw 'Original job closure unconfirmed.'}
        }catch{$State.CleanupError=$_.Exception.Message}
    }
    $State.TreeClosureConfirmed=$Context.Closed
    if($Context.Owner -and $Context.Closed){$State.ExitCode=$Context.Owner.ExitCode}
    if($Context.Closed -and $Context.Lease) {
        try {
            if($BeforeReleaseCheck){& $BeforeReleaseCheck}
            Exit-IW7ResourceLease -Token $Context.Lease.Token;$Context.Lease=$null;$State.LeaseReleased=$true
        }
        catch {$State.CleanupError=$_.Exception.Message}
    }
    if(!$Context.Closed -or $Context.Lease) {
        $State.Status='Quarantined';$State.Quarantined=$true
        [AppDomain]::CurrentDomain.SetData(('IW7.H1.Quarantine.'+$State.LeaseToken),$Context)
    }
}
function Assert-H1ReceiptBytes([string]$Path,[byte[]]$Expected) {
    Assert-H1Path $Path
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read')
    try {
        if($stream.Length -ne $Expected.Length){throw 'Published receipt length differs.'}
        $actual=[byte[]]::new($Expected.Length+1);$used=0
        do{$read=$stream.Read($actual,$used,$actual.Length-$used);$used+=$read}while($read -gt 0 -and $used -lt $actual.Length)
        if($used -ne $Expected.Length){throw 'Published receipt changed during readback.'}
        for($i=0;$i -lt $used;$i++){if($actual[$i] -ne $Expected[$i]){throw 'Published receipt bytes differ.'}}
    }finally{$stream.Dispose()}
}
function Write-H1Receipt($Plan,$State,[string]$StageRoot,[string]$Name='receipt.json',[switch]$PassThru) {
    if($Name -cnotmatch '^[A-Za-z0-9_-]+\.json$'){throw 'One literal receipt filename required.'}
    $total=Measure-H1Output $Plan.RunRoot
    $State.OutputBytesBeforeReceipt=$total
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($State|ConvertTo-Json -Depth 16)+"`n")
    if($bytes.Length -gt $Plan.MetadataReserveBytes -or $total+$bytes.Length -gt $Plan.OutputLimitBytes){throw 'Final receipt exceeds reserved output budget.'}
    $pending=Join-Path $StageRoot ($Name.Replace('.json','.pending.json'));$final=Join-Path $StageRoot $Name
    $stream=[IO.FileStream]::new($pending,'CreateNew','Write','Read')
    try {$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    Assert-H1ReceiptBytes $pending $bytes
    if((Measure-H1Output $Plan.RunRoot) -gt $Plan.OutputLimitBytes){throw 'Output changed before receipt publication.'}
    [IO.File]::Move($pending,$final) # No replacement; success is never published early.
    Assert-H1ReceiptBytes $final $bytes
    if($PassThru){[pscustomobject]@{Path=$final;Bytes=$bytes.Length;SHA256=([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes))).ToLowerInvariant()}}
}
function Assert-H1Observation($Report,[switch]$Dump) {
    $schema=if($Dump){'iw7.h1-parser-converter-dump-observation/1'}else{'iw7.h1-parser-converter-observation/1'}
    if($Report.schema -cne $schema -or $Report.checks -lt 1 -or
       $Report.vertices_checked -ne 24 -or $Report.bone_name_observed -cne 'tag_origin' -or
       $Report.material_reference -cne 'paris_h1_original_material'){throw 'Native observation identity differs.'}
    foreach($name in 'production_parsers_executed','production_converters_executed','declaration_adapter') {
        if($Report.$name -isnot [bool] -or !$Report.$name){throw 'Native method observation missing.'}
    }
    if($Report.dump_executed -isnot [bool] -or $Report.dump_executed -ne [bool]$Dump){throw 'Dump scope differs from reviewed profile.'}
    if($Dump -and ($Report.fixture_string_adapter -isnot [bool] -or !$Report.fixture_string_adapter -or
                  $Report.string_calls -ne 1 -or $Report.dump_files -ne 2)){throw 'Original fixture dump adapter identity differs.'}
    foreach($name in 'whole_zonetool_application','bone_engine_token_resolved','material_complete','lod_named_reference_linked',
        'ff_built','render_verified','retail_h1_compatibility') {
        if($Report.$name -isnot [bool] -or $Report.$name){throw 'Native observation overclaims its scope.'}
    }
}
function Get-H1DumpArtifacts($Plan,$Context) {
    $root=Join-Path $Plan.RunRoot 'probe/dump/h1_original'
    $expected=@('xmodel/paris_h1_original_cube.xmb','xsurface/paris_h1_original_cube_lod0.xsb')
    # Measure validates all descendants before any recursive file enumeration.
    $null=Measure-H1Output $root
    $files=@([IO.Directory]::EnumerateFiles($root,'*',[IO.SearchOption]::AllDirectories))
    if($files.Count -ne 2){throw 'Exactly two dump artifacts required.'}
    foreach($relative in $expected) {
        $path=Join-Path $root $relative
        Assert-H1Path $path
        $stream=[IO.FileStream]::new($path,'Open','Read','Read');$Context.Guards.Add($stream)
        if($stream.Length -le 0 -or $stream.Length -gt 64KB){throw 'Dump artifact exceeds 64 KiB or is empty.'}
        $sha=[Security.Cryptography.SHA256]::Create()
        try{$hash=[Convert]::ToHexString($sha.ComputeHash($stream)).ToLowerInvariant()}finally{$sha.Dispose()}
        [pscustomobject]@{Path=$path;Bytes=$stream.Length;SHA256=$hash}
    }
}
