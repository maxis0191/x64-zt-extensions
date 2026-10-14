# Fixed V2 consumer. The unchanged H1 core owns admission, processes and teardown.
function Read-T7RefV2Json([string]$Path,[int]$Limit=128KB) {
    Assert-H1Path $Path;$stream=[IO.FileStream]::new($Path,'Open','Read','Read')
    try {
        if($stream.Length -gt $Limit){throw 'V2 bounded JSON input required.'}
        $bytes=[byte[]]::new($Limit+1);$used=0
        do {$read=$stream.Read($bytes,$used,$bytes.Length-$used);$used+=$read}while($read -gt 0 -and $used -lt $bytes.Length)
        if($used -gt $Limit){throw 'V2 JSON input grew above bound.'}
        $text=[Text.Encoding]::UTF8.GetString($bytes,0,$used)
        # PS 7.5 added automatic date conversion; keep the literal UTC strings.
        if((Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')){return ($text|ConvertFrom-Json -Depth 20 -DateKind String)}
        $text|ConvertFrom-Json -Depth 20
    }finally{$stream.Dispose()}
}
function Assert-T7RefV2String($Value,[string]$Label) {
    if($Value -isnot [string] -or !$Value){throw ('V2 scalar string required: '+$Label)}
}
function Assert-T7RefV2Integer($Value,[string]$Label,[long]$Maximum=[long]::MaxValue) {
    if(($Value -isnot [int] -and $Value -isnot [long]) -or $Value -lt 0 -or $Value -gt $Maximum){throw ('V2 scalar integer required: '+$Label)}
}
function Assert-T7RefV2Fields($Value,[string[]]$Fields,[string]$Label) {
    if($Value -isnot [pscustomobject] -or ((@($Value.PSObject.Properties.Name|Sort-Object)-join ',') -cne (@($Fields|Sort-Object)-join ','))){throw ('V2 exact fields required: '+$Label)}
}
function Assert-T7RefV2Pin($Pin) {
    Assert-T7RefV2Fields $Pin @('Path','Bytes','SHA256','IsText') 'binding'
    Assert-T7RefV2String $Pin.Path 'pin.Path';Assert-T7RefV2String $Pin.SHA256 'pin.SHA256'
    Assert-T7RefV2Integer $Pin.Bytes 'pin.Bytes' 256MB
    if($Pin.Bytes -le 0 -or $Pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or $Pin.IsText -isnot [bool] -or ($Pin.IsText -and $Pin.Bytes -gt 1MB)){throw 'V2 binding type/bound differs.'}
    Assert-H1Path $Pin.Path
}
function Assert-T7RefV2TextPin($Pin,$Bindings,[long]$Bytes,[string]$SHA256) {
    Assert-T7RefV2Fields $Pin @('Path','Bytes','SHA256') 'source pin'
    Assert-T7RefV2String $Pin.Path 'source.Path';Assert-T7RefV2String $Pin.SHA256 'source.SHA256'
    Assert-T7RefV2Integer $Pin.Bytes 'source.Bytes' 1MB
    if($Pin.Bytes -ne $Bytes -or $Pin.SHA256 -cne $SHA256){throw 'V2 exact source pin differs.'}
    $rows=@($Bindings|Where-Object {$_.Path -is [string] -and $_.Path -ceq $Pin.Path -and $_.IsText -is [bool] -and $_.IsText -and
        ($_.Bytes -is [int] -or $_.Bytes -is [long]) -and $_.Bytes -eq $Bytes -and $_.SHA256 -is [string] -and $_.SHA256 -ceq $SHA256})
    if($rows.Count -ne 1){throw 'V2 guarded text binding missing.'}
}
function Assert-T7RefV2Marker($Marker) {
    Assert-T7RefV2Fields $Marker @('Schema','SourceProfile','RetainedMainBytes','RetainedMainSHA256','BaseMainBytes','BaseMainSHA256','MainBytes','MainSHA256','HelperBytes','HelperSHA256') 'build marker'
    foreach($name in 'Schema','SourceProfile','RetainedMainSHA256','BaseMainSHA256','MainSHA256','HelperSHA256'){Assert-T7RefV2String $Marker.$name ('marker.'+$name)}
    foreach($name in 'RetainedMainBytes','BaseMainBytes','MainBytes','HelperBytes'){Assert-T7RefV2Integer $Marker.$name ('marker.'+$name) 64KB}
    if($Marker.Schema -cne 'iw7.t7-prepatch-reference-build/2' -or $Marker.SourceProfile -cne 't7-prepatch-reference-v2' -or
       $Marker.RetainedMainBytes -ne 12854 -or $Marker.RetainedMainSHA256 -cne '40de5fda829cec32a5d75359f58e69c84db7d8ee54f198cf6befa2a6ebe6f86e' -or
       $Marker.BaseMainBytes -ne 13160 -or $Marker.BaseMainSHA256 -cne '55081db20863f291f4f1fea8c1c995995e5e548b56acf043201fbb2e361f3934' -or
       $Marker.MainBytes -ne 14524 -or $Marker.MainSHA256 -cne 'e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28' -or
       $Marker.HelperBytes -ne 15785 -or $Marker.HelperSHA256 -cne '0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a'){throw 'V2 fixed build marker differs.'}
}
function Assert-T7RefV2BuildProfile($Profile,$Bindings) {
    Assert-T7RefV2Fields $Profile @('Name','Option','ArgumentCount','Report','ObservationSchema','Helper','Wiring','BaseHelper','BaseWiring','BaseBuildPlan','BaseBuildReceipt','PreparedMain') 'build profile'
    foreach($name in 'Name','Option','Report','ObservationSchema'){Assert-T7RefV2String $Profile.$name ('profile.'+$name)}
    Assert-T7RefV2Integer $Profile.ArgumentCount 'profile.ArgumentCount' 2
    if($Profile.Name -cne 't7-prepatch-reference-v2' -or $Profile.Option -cne '-t7-prepatch-reference-v2' -or $Profile.ArgumentCount -ne 2 -or
       $Profile.Report -cne 't7-prepatch-reference-v2.local.json' -or $Profile.ObservationSchema -cne 'iw7.t7-prepatch-reference-observation/2'){throw 'V2 exclusive build profile required.'}
    foreach($row in @(
        @('Helper',15785,'0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a'),
        @('Wiring',3665,'89f3f26699f1240400c4bd96f2987963374658e55a8501cab7dc2543a84ceace'),
        @('BaseHelper',16281,'a9f458d2783c845af6958c896bda07fa4b92a5ea23a14c9e5d1201fe234a2018'),
        @('BaseWiring',3078,'162763ab503a7971bc56753e3aba9fc1c76bf181881f9bddf45718456467e129'),
        @('BaseBuildPlan',292575,'422e79898fa2b16defc8193182fe146e2db5d73aeb4516c2bd2aaf87c409c4de'),
        @('BaseBuildReceipt',26199,'af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897'),
        @('PreparedMain',14524,'e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28'))){Assert-T7RefV2TextPin $Profile.($row[0]) $Bindings $row[1] $row[2]}
}
function Assert-T7RefV2Build($Plan,$BuildPlan,$Receipt=$null) {
    foreach($name in 'Schema','SourceCommit'){Assert-T7RefV2String $BuildPlan.$name ('build.'+$name)}
    if($BuildPlan.Schema -cne 'iw7.t7-minimal-build-plan/1' -or $BuildPlan.SourceCommit -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
       (@($BuildPlan.Stages.Name)-join ',') -cne 'main,link' -or @($BuildPlan.Stages).Count -ne 2){throw 'V2 fixed two-stage build plan required.'}
    Assert-T7RefV2BuildProfile $BuildPlan.BuildProfile $Plan.Bindings
    Assert-T7RefV2Marker $BuildPlan.ReuseCompile.PrepatchReferenceV2
    if($BuildPlan.ReuseCompile.RecompiledMain -isnot [bool] -or !$BuildPlan.ReuseCompile.RecompiledMain){throw 'V2 fresh main required.'}
    foreach($name in 'RecompiledZonetool','ResidentMultiSurfaceV2','SelectedStreamedStaticV1','SelectedStreamedRenderOnlyV2','ZombiesObservationC','ZombiesAddObservationC2','ResidentSurfaceCountDiagnostic'){
        if($BuildPlan.ReuseCompile.PSObject.Properties[$name]){throw 'V2 cannot mix catalogue/export markers.'}
    }
    if($null -eq $Receipt){return}
    foreach($name in 'Schema','Status','PlanSHA256'){Assert-T7RefV2String $Receipt.$name ('receipt.'+$name)}
    foreach($name in 'InputsReverified','TreeClosureConfirmed','LeaseReleased','Quarantined','CandidateExecuted','Ready'){
        if($Receipt.$name -isnot [bool]){throw ('V2 closed-build boolean required: '+$name)}
    }
    if($Receipt.Schema -cne 'iw7.t7-minimal-build/1' -or $Receipt.Status -cne 'Passed' -or $Receipt.PlanSHA256 -cne $Plan.ExpectedBuildPlanSHA256 -or
       !$Receipt.InputsReverified -or !$Receipt.TreeClosureConfirmed -or !$Receipt.LeaseReleased -or $Receipt.Quarantined -or $Receipt.CandidateExecuted -or $Receipt.Ready){throw 'V2 successful closed unexecuted build required.'}
    Assert-T7RefV2BuildProfile $Receipt.BuildProfile $Plan.Bindings
    if(($Receipt.BuildProfile|ConvertTo-Json -Depth 6 -Compress) -cne ($BuildPlan.BuildProfile|ConvertTo-Json -Depth 6 -Compress)){throw 'V2 receipt profile differs from original recipe.'}
    if(@($Receipt.Stages).Count -ne 2 -or (@($Receipt.Stages.Name)-join ',') -cne 'main,link'){throw 'V2 original main/link stages required.'}
    foreach($stage in $Receipt.Stages){
        Assert-T7RefV2String $stage.Name 'stage.Name';Assert-T7RefV2Integer $stage.ExitCode 'stage.ExitCode' 0
        if($stage.TreeClosureConfirmed -isnot [bool] -or !$stage.TreeClosureConfirmed){throw 'V2 original stage closure required.'}
        $telemetry=$stage.CompilerTelemetry
        if($telemetry.Completed -isnot [bool] -or !$telemetry.Completed -or $telemetry.AfterStop.RootExited -isnot [bool] -or !$telemetry.AfterStop.RootExited){throw 'V2 compiler original closure required.'}
        Assert-T7RefV2Integer $telemetry.AfterStop.RootExitCode 'compiler exit' 0;Assert-T7RefV2Integer $telemetry.AfterStop.ActiveProcesses 'compiler active' 0
        Assert-T7RefV2Integer $telemetry.AfterStopMembers.AssignedCount 'compiler members' 0;Assert-T7RefV2Integer $telemetry.AfterStopMembers.ListedCount 'compiler listed' 0
        if($telemetry.AfterStopMembers.Members -isnot [array] -or $telemetry.AfterStopMembers.Members.Count){throw 'V2 original compiler job still populated.'}
    }
    $artifacts=@($Receipt.Stages[1].Artifacts|Where-Object {$_.Path -ceq $Plan.CandidateSource})
    if($artifacts.Count -ne 1){throw 'V2 unique actual executable artifact required.'}
    Assert-T7RefV2String $artifacts[0].Path 'artifact.Path';Assert-T7RefV2String $artifacts[0].SHA256 'artifact.SHA256';Assert-T7RefV2Integer $artifacts[0].Bytes 'artifact.Bytes' 64MB
    if($artifacts[0].Bytes -ne $Plan.CandidateBytes -or $artifacts[0].SHA256 -cne $Plan.CandidateSHA256){throw 'V2 executable differs from actual link artifact.'}
}
function Assert-T7RefV2ClosedBuildPins($Plan,$Index) {
    Assert-T7RefV2String $Index.Schema 'closed index.Schema'
    if($Index.Schema -cne 'iw7.t7-prepatch-reference-build-six-closed-pins/2' -or $Index.Pins -isnot [array] -or $Index.Pins.Count -ne 6){throw 'V2 original six-closure index required.'}
    $rows=@(
        @('entry.json',1198,'3df5aaa0afa6abd389d5c702e00f605f8d6fa3d9363c60a8c227e4a95392b4a4'),
        @('completion.json',669,'b74ce370e6e762356fb89848044a2f5f32d18d9a0627593949283a311295ef07'),
        @('tool-return.local.json',320,'ed0502ded5282e0e64f99f99c45915d9538cfdd52fa6acf3141c6527d7c743e1'),
        @('inventory.local.json',1429,'d669090440784bf8da2d8aec1f51930e29a78474ed2e73266e588ab513f01c5b'),
        @('build-completion.local.json',8528,'7966dd067d6b490babe1dc076f2d1c55850338302661d74c5a9eba1bb6338183'),
        @('closed-bundle.local.json',2359,'d2a3b8c8a14ed2471d45f7bb08e59c359209e0f9594c517909c8272ce4b16105'))
    for($i=0;$i -lt 6;$i++){
        $pin=$Index.Pins[$i];Assert-T7RefV2TextPin $pin $Plan.Bindings $rows[$i][1] $rows[$i][2]
        if([IO.Path]::GetFileName($pin.Path) -cne $rows[$i][0]){throw 'V2 closure role differs.'}
    }
}
function Get-T7RefV2Metadata([string]$Path) {
    Assert-H1Path $Path
    if(!(Test-Path -LiteralPath $Path)){return [pscustomobject]@{Path=$Path;Exists=$false;Directory=$false;Bytes=0L;Attributes='';LastWriteUtc='';CreationUtc=''}}
    $item=Get-Item -LiteralPath $Path
    [pscustomobject]@{Path=$Path;Exists=$true;Directory=[bool]$item.PSIsContainer;Bytes=$(if($item.PSIsContainer){0L}else{$item.Length});Attributes=[string]$item.Attributes;LastWriteUtc=$item.LastWriteTimeUtc.ToString('o');CreationUtc=$item.CreationTimeUtc.ToString('o')}
}
function Get-T7RefV2BankSnapshot([string]$Root) {
    Assert-H1Path $Root
    $rows=[Collections.Generic.List[object]]::new();$pending=[Collections.Generic.Stack[string]]::new();$pending.Push($Root)
    while($pending.Count){
        $path=$pending.Pop();$row=Get-T7RefV2Metadata $path;$rows.Add($row)
        if($rows.Count -gt 512){throw 'V2 bounded bank metadata inventory exceeded.'}
        if($row.Exists -and $row.Directory){foreach($entry in [IO.Directory]::EnumerateFileSystemEntries($path)){$pending.Push($entry)}}
    }
    [pscustomobject]@{Root=$Root;Entries=@($rows|Sort-Object Path)}
}
function Assert-T7RefV2MetadataShape($Row) {
    Assert-T7RefV2Fields $Row @('Path','Exists','Directory','Bytes','Attributes','LastWriteUtc','CreationUtc') 'Main metadata'
    Assert-T7RefV2String $Row.Path 'Main metadata.Path';Assert-H1Path $Row.Path
    Assert-T7RefV2Integer $Row.Bytes 'Main metadata.Bytes'
    if($Row.Exists -isnot [bool] -or $Row.Directory -isnot [bool]){throw 'V2 metadata booleans required.'}
    foreach($name in 'Attributes','LastWriteUtc','CreationUtc'){
        if($Row.$name -isnot [string]){throw ('V2 metadata scalar string required: '+$name)}
    }
    if(!$Row.Exists){if($Row.Directory -or $Row.Bytes -or $Row.Attributes -or $Row.LastWriteUtc -or $Row.CreationUtc){throw 'V2 absent metadata differs.'}}
    else {$null=[datetimeoffset]::Parse($Row.LastWriteUtc);$null=[datetimeoffset]::Parse($Row.CreationUtc);if($Row.Directory -and $Row.Bytes){throw 'V2 directory metadata bytes differ.'}}
}
function Assert-T7RefV2MainShape($Plan) {
    Assert-T7RefV2String $Plan.MainBaseline 'MainBaseline'
    if($Plan.MainBaseline -cne 'Stopped'){throw 'V2 preserves the assigned stopped Main baseline only.'}
    Assert-T7RefV2Fields $Plan.PreservedMain @('PID','CreatedUtc','Image') 'Main identity'
    Assert-T7RefV2Integer $Plan.PreservedMain.PID 'Main.PID' ([int]::MaxValue)
    Assert-T7RefV2String $Plan.PreservedMain.CreatedUtc 'Main.CreatedUtc';Assert-T7RefV2String $Plan.PreservedMain.Image 'Main.Image'
    if($Plan.PreservedMain.PID -le 0){throw 'V2 original Main identity required.'}
    $null=[datetimeoffset]::Parse($Plan.PreservedMain.CreatedUtc);Assert-H1Path $Plan.PreservedMain.Image
    if($Plan.MainFiles -isnot [array] -or !@($Plan.MainFiles).Count -or @($Plan.MainFiles).Count -gt 16 -or
       @($Plan.MainFiles.Path|Sort-Object -Unique).Count -ne $Plan.MainFiles.Count -or @($Plan.MainFiles|Where-Object Path -CEQ $Plan.PreservedMain.Image).Count -ne 1){throw 'V2 bounded original Main file metadata required.'}
    foreach($row in $Plan.MainFiles){
        Assert-T7RefV2MetadataShape $row
        if(!$row.Path.StartsWith(([IO.Path]::GetDirectoryName($Plan.PreservedMain.Image))+'\',[StringComparison]::Ordinal)){throw 'V2 Main metadata escapes the preserved installation.'}
    }
    Assert-T7RefV2Fields $Plan.BankSnapshot @('Root','Entries') 'bank snapshot'
    Assert-T7RefV2String $Plan.BankSnapshot.Root 'bank.Root';Assert-H1Path $Plan.BankSnapshot.Root
    if($Plan.BankSnapshot.Root -cne (Join-Path ([IO.Path]::GetDirectoryName($Plan.PreservedMain.Image)) 'mods/paris_beta/bank')){throw 'V2 original Main bank root required.'}
    if($Plan.BankSnapshot.Entries -isnot [array] -or !$Plan.BankSnapshot.Entries.Count -or $Plan.BankSnapshot.Entries.Count -gt 512){throw 'V2 bank metadata required.'}
    foreach($row in $Plan.BankSnapshot.Entries){
        Assert-T7RefV2MetadataShape $row
        if($row.Path -cne $Plan.BankSnapshot.Root -and !$row.Path.StartsWith($Plan.BankSnapshot.Root+'\',[StringComparison]::Ordinal)){throw 'V2 bank metadata escapes the selected root.'}
    }
    if(@($Plan.BankSnapshot.Entries.Path|Sort-Object -Unique).Count -ne $Plan.BankSnapshot.Entries.Count -or
       @($Plan.BankSnapshot.Entries|Where-Object Path -CEQ $Plan.BankSnapshot.Root).Count -ne 1){throw 'V2 exact bank metadata inventory required.'}
}
function Assert-T7RefV2Main($Plan) {
    Assert-T7RefV2MainShape $Plan
    $expected=$Plan.PreservedMain;$name=[IO.Path]::GetFileName($expected.Image)
    $rows=@(Get-IW7ResourceProcesses|Where-Object {$_.PID -eq $expected.PID -or ($_.Image -and $_.Image -ieq $expected.Image) -or (!$_.Image -and $_.Name -ieq $name)})
    $udp=@(Get-NetUDPEndpoint -ErrorAction Stop|Where-Object LocalPort -EQ 27016)
    if($rows.Count -or $udp.Count){throw 'V2 stopped Main identity/UDP ownership conflict.'}
    foreach($row in $Plan.MainFiles){
        if(((Get-T7RefV2Metadata $row.Path)|ConvertTo-Json -Compress) -cne ($row|ConvertTo-Json -Compress)){throw 'V2 preserved Main file metadata changed.'}
    }
    $bank=Get-T7RefV2BankSnapshot $Plan.BankSnapshot.Root
    if(($bank|ConvertTo-Json -Depth 6 -Compress) -cne ($Plan.BankSnapshot|ConvertTo-Json -Depth 6 -Compress)){throw 'V2 preserved bank metadata changed.'}
    [ordered]@{CapturedUtc=[datetime]::UtcNow.ToString('o');Baseline='Stopped';OriginalPID=$expected.PID;OriginalCreatedUtc=$expected.CreatedUtc;ExpectedImage=$expected.Image;OriginalPIDAbsent=$true;ExpectedImageAbsent=$true;UDP27016Absent=$true;MainFileCount=$Plan.MainFiles.Count;BankEntryCount=$bank.Entries.Count;BankMetadataUnchanged=$true;BankContentsRead=$false;Cause='Unknown'}
}
function Assert-T7RefV2Plan($Plan,[string]$Repo,[string]$Runner) {
    foreach($name in 'Schema','CandidateProfile','ObservationSchema','ReportName','Runner','RunRoot','WorkingDirectory','StageRoot','Image','EngineSource','SteamSource','JobAssembly','HostImage','BuildPlan','ExpectedBuildPlanSHA256','BuildClosedPins'){
        Assert-T7RefV2String $Plan.$name ('plan.'+$name)
    }
    foreach($name in 'PhysicalBytes','CommitBytes','GroupDeadlineSeconds','DeadlineSeconds','MutableOutputLimitBytes','MetadataReserveBytes','CleanupSeconds','ReportLimitBytes','LogLimitBytes','CandidateBytes','OutputLimitBytes'){Assert-T7RefV2Integer $Plan.$name ('plan.'+$name)}
    if($Plan.Schema -cne 'iw7.t7-prepatch-reference-plan/2' -or $Plan.CandidateProfile -cne 't7-prepatch-reference-v2' -or
       $Plan.ObservationSchema -cne 'iw7.t7-prepatch-reference-observation/2' -or $Plan.ReportName -cne 't7-prepatch-reference-v2.local.json' -or
       $Plan.Runner -cne $Runner -or $Plan.PhysicalBytes -ne 6GB -or $Plan.CommitBytes -ne 8GB -or
       $Plan.GroupDeadlineSeconds -ne 200 -or $Plan.DeadlineSeconds -ne 120 -or $Plan.MutableOutputLimitBytes -ne 64MB -or
       $Plan.MetadataReserveBytes -ne 64KB -or $Plan.CleanupSeconds -ne 5 -or $Plan.ReportLimitBytes -ne 256KB -or $Plan.LogLimitBytes -ne 1MB -or
       $Plan.RetryAuthorized -isnot [bool] -or $Plan.RetryAuthorized -or $Plan.ExpectedBuildPlanSHA256 -cne '0aca63cb09e8ecfc96dee34e1fdf94f8cb66e400f8a190ffdefd38bec3a2c549'){throw 'V2 fixed source/diagnostic plan differs.'}
    foreach($name in 'Zone','Zones','ZombiesObservationC','ZombiesAddObservationC2','ResidentExportV1','Addresses'){if($Plan.PSObject.Properties[$name]){throw 'V2 has no zone/export/address selector.'}}
    if($Plan.Arguments -isnot [array] -or $Plan.Arguments.Count -ne 1){throw 'V2 sole native argument required.'}
    Assert-T7RefV2String $Plan.Arguments[0] 'argv[0]'
    if($Plan.Arguments[0] -cne '-t7-prepatch-reference-v2'){throw 'V2 sole native argument differs.'}
    Assert-T7RefV2MainShape $Plan
    if($Plan.Bindings -isnot [array] -or !$Plan.Bindings.Count -or $Plan.Bindings.Count -gt 48){throw 'V2 bounded bindings required.'}
    foreach($pin in $Plan.Bindings){Assert-T7RefV2Pin $pin}
    if(@($Plan.Bindings.Path|Sort-Object -Unique).Count -ne $Plan.Bindings.Count){throw 'V2 duplicate binding refused.'}
    foreach($path in @($Plan.RunRoot,$Plan.WorkingDirectory,$Plan.StageRoot,$Plan.Image,$Plan.EngineSource,$Plan.SteamSource,$Plan.JobAssembly,$Plan.HostImage,$Plan.BuildPlan,$Plan.BuildClosedPins)){Assert-H1Path $path}
    if([IO.Path]::GetDirectoryName($Plan.RunRoot) -cne (Join-Path $Repo 'runtime') -or [IO.Path]::GetFileName($Plan.RunRoot) -cnotmatch '^t7-prepatch-reference-[a-z][a-z0-9-]*$' -or
       $Plan.WorkingDirectory -cne (Join-Path $Plan.RunRoot 'work') -or $Plan.StageRoot -cne (Join-Path $Plan.RunRoot 'evidence') -or
       $Plan.Image -cne (Join-Path $Plan.WorkingDirectory 't7-zonetool-prepatch-reference-v2.exe')){throw 'V2 exact private paths required.'}
    foreach($dir in @($Plan.WorkingDirectory,$Plan.StageRoot,(Join-Path $Plan.RunRoot 'temp'))){if(![IO.Directory]::Exists($dir)){throw 'V2 prepared private directories required.'}}
    foreach($path in @($Plan.Image,(Join-Path $Plan.RunRoot 'attempt.json'),(Join-Path $Plan.RunRoot 'stop.request'),(Join-Path $Plan.WorkingDirectory $Plan.ReportName),($Plan.RunRoot+'.host-start.json'),($Plan.RunRoot+'.host-postflight.json'),(Join-Path $Plan.RunRoot 'zone'))){if(Test-Path -LiteralPath $path){throw 'V2 create-only attempt/output/host required.'}}
    $names=@([IO.Directory]::EnumerateFileSystemEntries($Plan.WorkingDirectory)|ForEach-Object {[IO.Path]::GetFileName($_)}|Sort-Object)
    if(($names -join '|') -cne 'BlackOps3_UnrankedDedicatedServer.exe|steam_api64.dll' -or @([IO.Directory]::EnumerateFileSystemEntries($Plan.StageRoot)).Count -or @([IO.Directory]::EnumerateFileSystemEntries((Join-Path $Plan.RunRoot 'temp'))).Count){throw 'V2 only two prepared aliases and empty evidence/temp allowed.'}
    foreach($pin in $Plan.Bindings){if((Get-Item -LiteralPath $pin.Path).Length -ne $pin.Bytes){throw 'V2 binding metadata length differs.'}}
    foreach($pair in @(@('BlackOps3_UnrankedDedicatedServer.exe',21737352,'3df511d71e3690b14517379783bbfb713f6fe2ed2f2e73b445b4878216686156',$Plan.EngineSource),@('steam_api64.dll',235600,'71af8666392acad2080a816b9f1196fe9ccb950e1db8a549f8312c4d231f55a8',$Plan.SteamSource))){
        foreach($path in @($pair[3],(Join-Path $Plan.WorkingDirectory $pair[0]))){$pin=@($Plan.Bindings|Where-Object Path -CEQ $path);if($pin.Count -ne 1 -or $pin[0].Bytes -ne $pair[1] -or $pin[0].SHA256 -cne $pair[2] -or $pin[0].IsText){throw 'V2 exact engine/Steam metadata pins required.'}}
    }
    if($Plan.OutputLimitBytes -ne (64MB+21737352+235600+$Plan.CandidateBytes)){throw 'V2 output budget includes aliases.'}
    foreach($row in @(@($Plan.BuildPlan,303783,$Plan.ExpectedBuildPlanSHA256,$true),@($Plan.BuildClosedPins,1867,'cfb6f523336ad0fd163c2ffcdeaf4ff5b31b83fc5fa17321662bce89c61353d0',$true),@($Plan.JobAssembly,$null,'5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8',$false))){
        $pins=@($Plan.Bindings|Where-Object {$_.Path -ceq $row[0] -and $_.SHA256 -ceq $row[2]});if($pins.Count -ne 1 -or $pins[0].IsText -ne $row[3] -or ($null -ne $row[1] -and $pins[0].Bytes -ne $row[1])){throw 'V2 recipe/closure/provider binding differs.'}
    }
}
function Assert-T7RefV2HostArguments($Plan,[string]$PlanPath,[string]$PlanSHA256,$Actual) {
    $expected=@($Plan.HostImage,'-NoLogo','-NoProfile','-NoExit','-File',$Plan.Runner,'-PlanPath',$PlanPath,'-PlanSHA256',$PlanSHA256,'-Run')
    if($Actual -isnot [array] -or $Actual.Count -ne $expected.Count){throw 'V2 exact fresh NoProfile/NoExit host required.'}
    for($i=0;$i -lt $expected.Count;$i++){Assert-T7RefV2String $Actual[$i] 'host argv';if($Actual[$i] -cne $expected[$i]){throw 'V2 exact fresh NoProfile/NoExit host required.'}}
}
function Complete-T7RefV2Host {
    $taskHostState=[AppDomain]::CurrentDomain.GetData('IW7.T7PrepatchReferenceV2')
    if(!$taskHostState -or $taskHostState.Host.PID -ne $PID -or $taskHostState.Phase -cne 'Returned' -or !$taskHostState.Context.Closed -or $taskHostState.Context.Lease -or
       $taskHostState.Context.Guards.Count -or $taskHostState.State.Quarantined -or !$taskHostState.State.TreeClosureConfirmed -or !$taskHostState.State.LeaseReleased){throw 'V2 same original closed host with no guards/lease required.'}
    $taskPlan=$taskHostState.Plan;$taskNative=$taskHostState.State.Identity
    $taskProcesses=@(Get-IW7ResourceProcesses)
    if(@($taskProcesses|Where-Object {($taskNative -and $_.PID -eq $taskNative.PID) -or ($_.Image -and $_.Image.StartsWith($taskPlan.RunRoot+'\',[StringComparison]::OrdinalIgnoreCase))}).Count){throw 'V2 original native PID/run process remains.'}
    $taskRegistry=Read-IW7ResourceState
    if(@($taskRegistry.Leases|Where-Object Token -CEQ $taskHostState.State.LeaseToken).Count){throw 'V2 original lease remains.'}
    $taskMain=Assert-T7RefV2Main $taskPlan
    $taskProof=[ordered]@{Schema='iw7.t7-prepatch-reference-host-closure/2';CapturedUtc=[datetime]::UtcNow.ToString('o');Host=$taskHostState.Host;Native=$taskNative;PlanSHA256=$taskHostState.PlanSHA256;
        Status=$taskHostState.State.Status;CaptureOutcome=$taskHostState.State.CaptureOutcome;NativeExitCode=$taskHostState.State.ExitCode;TreeClosureConfirmed=$true;LeaseReleased=$true;WrapperGuardCount=0;Main=$taskMain;
        CanExit=$true;ActualPTYExitObserved=$false;IndependentAbsencePending=$true;OpaqueInputsReadAfterRelease=$false;Ready=$false}
    $path=$taskPlan.RunRoot+'.host-postflight.json';$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($taskProof|ConvertTo-Json -Depth 8)+"`n")
    $stream=[IO.FileStream]::new($path,'CreateNew','Write','Read');try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
    $taskHostState.Phase='Closed';$taskHostState.CanExit=$true
    [ordered]@{Postflight='Passed';HostPID=$PID;CanExit=$true;WrapperGuardCount=0;ActualPTYExitObserved=$false;IndependentAbsencePending=$true}|ConvertTo-Json
}
function New-T7RefV2Start($Plan) {
    $start=[Diagnostics.ProcessStartInfo]::new($Plan.Image);$start.WorkingDirectory=$Plan.WorkingDirectory;$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle='Hidden'
    $start.Environment.Clear();$windows=[Environment]::GetEnvironmentVariable('SystemRoot')
    $start.Environment['SystemRoot']=$windows;$start.Environment['WINDIR']=$windows;$start.Environment['PATH']=Join-Path $windows 'System32';$start.Environment['COMSPEC']=Join-Path $windows 'System32/cmd.exe'
    $temp=Join-Path $Plan.RunRoot 'temp';$start.Environment['TEMP']=$temp;$start.Environment['TMP']=$temp;$start.Environment['USERPROFILE']=Join-Path $temp 'profile';$start.Environment['APPDATA']=Join-Path $temp 'profile/roaming';$start.Environment['LOCALAPPDATA']=Join-Path $temp 'profile/local'
    $start.ArgumentList.Add('-t7-prepatch-reference-v2');$start
}
function ConvertFrom-T7RefV2Pointer($Value,[string]$Label) {
    Assert-T7RefV2String $Value $Label
    if($Value -cnotmatch '^0x(?:0|[1-9a-f][0-9a-f]{0,15})$'){throw ('V2 pointer format differs: '+$Label)}
    [UInt64]::Parse($Value.Substring(2),[Globalization.NumberStyles]::AllowHexSpecifier,[Globalization.CultureInfo]::InvariantCulture)
}
function Get-T7RefV2Outcome($Report,$Identity,$ExitCode,[string]$ExpectedModule) {
    if($null -eq $Report){return 'NoCapture'}
    foreach($name in 'schema','phase','source_base','status'){Assert-T7RefV2String $Report.$name ('report.'+$name)}
    foreach($name in 'pid','thread_id','read_limit','report_limit','window_count','window_observations','requested_bytes','returned_bytes'){Assert-T7RefV2Integer $Report.$name ('report.'+$name)}
    Assert-T7RefV2Integer $Identity.PID 'identity.PID' ([int]::MaxValue);Assert-T7RefV2String $Identity.CreatedUtc 'identity.CreatedUtc';Assert-T7RefV2Integer $ExitCode 'exit' 2
    if($Report.schema -cne 'iw7.t7-prepatch-reference-observation/2' -or $Report.phase -cne 'first_dpi_before_component_post_unpack' -or $Report.pid -ne $Identity.PID -or
       $Report.pid -le 0 -or $Report.thread_id -le 0 -or $Report.thread_id -gt [UInt32]::MaxValue -or
       $Report.read_limit -ne 4MB -or $Report.report_limit -ne 256KB -or $Report.window_count -ne 2 -or $Report.source_base -cne '0x140000000' -or
       $Report.windows -isnot [array] -or $Report.window_observations -ne $Report.windows.Count -or $Report.windows.Count -gt 2 -or
       $Report.requested_bytes -gt 4MB -or $Report.returned_bytes -gt $Report.requested_bytes -or $Report.capture_complete -isnot [bool]){throw 'V2 report identity/schema/bounds differ.'}
    foreach($name in 'boot_authorized','abi_proven','runtime_compatibility_proven'){if($Report.$name -isnot [bool] -or $Report.$name){throw 'V2 report overclaims compatibility.'}}
    if($Report.PSObject.Properties['creation_filetime']){
        Assert-T7RefV2String $Report.creation_filetime 'creation_filetime'
        if($Report.creation_filetime -cnotmatch '^[1-9][0-9]{0,18}$' -or [DateTime]::FromFileTimeUtc([long]::Parse($Report.creation_filetime)).ToString('o') -cne $Identity.CreatedUtc){throw 'V2 original report generation differs.'}
    }
    $names=@('DB_AddXAsset','Load_SimpleAsset');$rvas=@(0x1D4600,0x1DB2B0);$lengths=@(2048,256)
    for($i=0;$i -lt $Report.windows.Count;$i++){
        $row=$Report.windows[$i];Assert-T7RefV2String $row.site 'window.site'
        foreach($name in 'rva','window_rva','window_bytes'){Assert-T7RefV2Integer $row.$name ('window.'+$name) ([UInt32]::MaxValue)}
        if($row.site -cne $names[$i] -or $row.rva -ne $rvas[$i] -or $row.window_rva -ne $rvas[$i] -or $row.window_bytes -ne $lengths[$i]){throw 'V2 fixed window differs.'}
    }
    if(!$Report.capture_complete){if($ExitCode -ne 2 -or $Report.status -cne 'incomplete_stop'){throw 'V2 partial report/exit disagree.'};return 'CapturePartial'}
    if($ExitCode -ne 0 -or $Report.status -cne 'captured_for_offline_review' -or !$Report.PSObject.Properties['creation_filetime'] -or $Report.windows.Count -ne 2 -or
       $Report.requested_bytes -lt 2304 -or $Report.returned_bytes -ne $Report.requested_bytes -or $Report.PSObject.Properties['capture_error'] -or $Report.PSObject.Properties['metadata_error']){throw 'V2 complete capture contract differs.'}
    Assert-T7RefV2String $Report.module_path 'module_path';Assert-H1Path $ExpectedModule
    if(![IO.Path]::IsPathFullyQualified($Report.module_path) -or [IO.Path]::GetFullPath($Report.module_path) -ine $ExpectedModule -or $Report.base_matches_source -isnot [bool]){throw 'V2 mapped module identity differs.'}
    $base=ConvertFrom-T7RefV2Pointer $Report.module_base 'module_base'
    if($Report.base_matches_source -ne ($base -eq 0x140000000)){throw 'V2 mapped module base claim differs.'}
    Assert-T7RefV2Integer $Report.pe.size_of_image 'PE size' 1GB
    Assert-T7RefV2Integer $Report.pdata_records 'pdata_records' ([long][math]::Floor(2MB/12))
    if($Report.pe.size_of_image -lt 4096 -or $base -gt [UInt64]::MaxValue-$Report.pe.size_of_image){throw 'V2 mapped image range differs.'}
    for($i=0;$i -lt 2;$i++){
        $row=$Report.windows[$i];Assert-T7RefV2String $row.bytes_hex 'window.bytes_hex'
        if($row.bytes_hex -cnotmatch ('^[0-9a-f]{'+(2*$lengths[$i])+'}$') -or $row.PSObject.Properties['error'] -or $rvas[$i]+$lengths[$i] -gt $Report.pe.size_of_image){throw 'V2 complete window bytes/range differ.'}
        if($row.regions -isnot [array] -or !$row.regions.Count -or $row.regions.Count -gt 128){throw 'V2 memory regions required.'}
        $cursor=$base+$rvas[$i];$end=$cursor+$lengths[$i]
        foreach($span in $row.regions){
            $begin=ConvertFrom-T7RefV2Pointer $span.base 'region.base';$allocation=ConvertFrom-T7RefV2Pointer $span.allocation_base 'region.allocation_base'
            foreach($name in 'size','state','protect','allocation_protect','type'){Assert-T7RefV2Integer $span.$name ('region.'+$name)}
            if(!$span.size -or $begin -gt [UInt64]::MaxValue-$span.size -or $begin -gt $cursor -or $begin+$span.size -le $cursor -or $cursor -ge $end -or
               $allocation -ne $base -or $span.state -ne 4096 -or $span.type -ne 16777216 -or ($span.protect -band 0x101)){throw 'V2 memory region identity/readability/range differs.'}
            $cursor=[math]::Min([decimal]$end,[decimal]($begin+$span.size))
        }
        if($cursor -ne $end){throw 'V2 incomplete region coverage.'}
        if($null -ne $row.runtime_function){
            $fn=$row.runtime_function
            foreach($name in 'begin_rva','end_rva','unwind_rva'){Assert-T7RefV2Integer $fn.$name ('pdata.'+$name) $Report.pe.size_of_image}
            Assert-T7RefV2String $fn.unwind_header_hex 'pdata.unwind_header_hex'
            if($fn.begin_rva -gt $rvas[$i] -or $fn.end_rva -le $rvas[$i] -or $fn.begin_rva -ge $fn.end_rva -or !$fn.unwind_rva -or $fn.unwind_rva+4 -gt $Report.pe.size_of_image -or
               $fn.unwind_header_hex -cnotmatch '^[0-9a-f]{8}$' -or $fn.unwind_format_validated -isnot [bool] -or $fn.unwind_format_validated){throw 'V2 pdata observation differs.'}
        }
    }
    'CaptureComplete'
}
function Read-T7RefV2Report($Plan,$State,$Context) {
    $path=Join-Path $Plan.WorkingDirectory 't7-prepatch-reference-v2.local.json'
    if(!(Test-Path -LiteralPath $path)){return 'NoCapture'}
    $State.CaptureOutcome='CapturePresentUnqualified';Assert-H1Path $path;$size=(Get-Item -LiteralPath $path).Length
    if($size -le 0 -or $size -gt 256KB){throw 'V2 diagnostic JSON size refused.'}
    $pin=[pscustomobject]@{Path=$path;Bytes=$size;SHA256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
    $Context.Guards.Add((Open-H1Pin $pin));$State.Report=$pin
    Get-T7RefV2Outcome (Read-T7RefV2Json $path 256KB) $State.Identity $State.ExitCode (Join-Path $Plan.WorkingDirectory 'BlackOps3_UnrankedDedicatedServer.exe')
}
function Enable-T7RefV2RuntimeProfile($Plan,$Context) {
    $script:T7RefV2Started=Get-H1Clock;$script:T7RefV2BaseDeadline=${function:Assert-H1Deadline};$script:T7RefV2BaseBudget=${function:Test-H1Budget}
    function script:Assert-H1Deadline($Started,[int]$Seconds){& $script:T7RefV2BaseDeadline $script:T7RefV2Started 200;& $script:T7RefV2BaseDeadline $Started $Seconds}
    function script:Test-H1Budget($Plan,$State){
        Assert-H1Deadline $script:T7RefV2Started 200;& $script:T7RefV2BaseBudget $Plan $State
        foreach($name in 'stdout.log','stderr.log'){$path=Join-Path $Plan.StageRoot $name;if((Test-Path -LiteralPath $path) -and (Get-Item -LiteralPath $path).Length -gt 1MB){throw 'V2 diagnostic log cap exceeded.'}}
        $path=Join-Path $Plan.WorkingDirectory 't7-prepatch-reference-v2.local.json';if((Test-Path -LiteralPath $path) -and (Get-Item -LiteralPath $path).Length -gt 256KB){throw 'V2 report cap exceeded.'}
        $allowed=@('BlackOps3_UnrankedDedicatedServer.exe','steam_api64.dll','t7-zonetool-prepatch-reference-v2.exe','t7-prepatch-reference-v2.local.json')
        foreach($entry in [IO.Directory]::EnumerateFileSystemEntries($Plan.WorkingDirectory)){if([IO.Path]::GetFileName($entry) -cnotin $allowed -or [IO.Directory]::Exists($entry)){throw 'V2 unexpected engine output; preserve and stop.'}}
        Assert-H1Deadline $script:T7RefV2Started 200
    }
}
