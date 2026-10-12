# Pure world adapter gates. Importing this file starts nothing.
function Get-WorldObserverBudgets {
    [ordered]@{PhysicalBytes=4GB;CommitBytes=6GB;OutputBytes=64MB;LiveOutputBytes=63MB;
        StreamBytes=2MB;CompileMs=90000L;FixtureMs=10000L;GroupMs=120000L;SupervisorSeconds=240}
}
function Assert-WorldObserverTime([long]$ElapsedMs,[string]$Phase,[long]$PhaseElapsedMs) {
    $b=Get-WorldObserverBudgets
    if($ElapsedMs -lt 0 -or $PhaseElapsedMs -lt 0 -or $ElapsedMs -ge $b.GroupMs){throw 'World group deadline reached (120 seconds).'}
    $limit=switch -CaseSensitive ($Phase){'compile'{$b.CompileMs};'fixture'{$b.FixtureMs};default{throw 'Unknown world phase.'}}
    if($PhaseElapsedMs -ge $limit){throw "World $Phase deadline reached."}
}
function Assert-WorldObserverPollTime($State,[long]$StartedMs,[long]$NowMs,[long]$GroupStartedMs=$StartedMs) {
    $phase=if($null -eq $State.FixtureStartedMs){'compile'}else{'fixture'}
    $phaseStart=if($null -eq $State.FixtureStartedMs){$StartedMs}else{$State.FixtureStartedMs}
    Assert-WorldObserverTime ($NowMs-$GroupStartedMs) $phase ($NowMs-$phaseStart)
}
function Resolve-WorldObserverPath([string]$Path) {
    if($Path -notmatch '^[A-Za-z]:[\\/]' -or $Path.Substring(2) -match '[:"<>|?*\x00-\x1f]' -or
       $Path -match '(^|[\\/])(?:\.\.?|[^\\/]*[. ])([\\/]|$)'){throw 'Unambiguous absolute local path required.'}
    foreach($part in $Path.Substring(3) -split '[\\/]'){
        if($part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)'){throw 'Reserved Windows device path refused.'}
    }
    $full=[IO.Path]::GetFullPath($Path).TrimEnd('\','/')
    Resolve-IW7BasePath (Split-Path $full -Parent) (Split-Path $full -Leaf)
}
function Assert-WorldObserverPins($Entries) {
    foreach($entry in $Entries){
        $null=Resolve-WorldObserverPath $entry.Path
        Assert-BeaconHash $entry.Path $entry.SHA256
    }
}
function Measure-WorldObserverOutput([string]$Root,[switch]$Final) {
    $count=0;$bytes=0L
    foreach($file in Get-ChildItem -LiteralPath $Root -Recurse -Force){
        if(++$count -gt 4096 -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'World output inventory bound or redirect.'}
        if(!$file.PSIsContainer){$bytes+=$file.Length}
    }
    Assert-WorldObserverOutput $bytes -Final:$Final
    $bytes
}
function Assert-WorldObserverOutput([long]$Bytes,[switch]$Final) {
    $b=Get-WorldObserverBudgets;$limit=if($Final){$b.OutputBytes}else{$b.LiveOutputBytes}
    if($Bytes -lt 0 -or $Bytes -gt $limit){throw 'World output budget exceeded.'}
}
function Write-WorldObserverJson([string]$Path,$Value) {
    # Publish complete small protocol files only. Never overwrite a prior receipt.
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 20))
    if($bytes.Length -gt 512KB){throw 'World JSON receipt bound.'}
    $temporary=$Path+'.pending'
    $stream=[IO.File]::Open($temporary,'CreateNew','Write','None')
    try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
    [IO.File]::Move($temporary,$Path)
}
function Write-WorldObserverFinalReceipt([string]$Root,$State) {
    $before=Measure-WorldObserverOutput $Root
    $State.FinalBytes=$before
    $stable=$false
    for($pass=0;$pass -lt 4;$pass++){
        $serialized=[Text.UTF8Encoding]::new($false).GetBytes(($State|ConvertTo-Json -Depth 20))
        $next=$before+$serialized.Length
        if($next -eq $State.FinalBytes){$stable=$true;break}
        $State.FinalBytes=$next
    }
    if(!$stable){throw 'Final world byte accounting did not converge.'}
    Assert-WorldObserverOutput $State.FinalBytes -Final
    Write-WorldObserverJson (Join-Path $Root 'run.json') $State
    if((Measure-WorldObserverOutput $Root -Final) -ne $State.FinalBytes){throw 'Final world receipt byte accounting differs.'}
}
function Assert-WorldObserverCompileReceipt($Receipt,$Witness,$Policy) {
    if($Receipt.schema -cne 'iw7.material-v2-phase-result/1' -or $Receipt.phase -cne 'compile' -or
       $Receipt.failure -or ($Receipt.exit_code -isnot [long] -and $Receipt.exit_code -isnot [int]) -or
       $Receipt.exit_code -ne 0 -or $Receipt.executable_sha256 -ine $Policy.CompilerSHA256 -or
       !$Witness.CompilerIdentity -or ($Receipt.pid -isnot [long] -and $Receipt.pid -isnot [int]) -or
       $Receipt.pid -ne $Witness.CompilerIdentity.PID){throw 'Successful independently witnessed world compiler receipt required.'}
}
function Assert-WorldObserverAdvance($Observation,$Root,$Witness,$Receipt,$Policy) {
    Assert-WorldObserverCompileReceipt $Receipt $Witness $Policy
    $members=@($Observation.Members)
    if($members.Count -notin 1,2 -or $Observation.AssignedCount -ne $members.Count -or
       $Observation.ListedCount -ne $members.Count){throw 'Complete root/optional-telemetry membership required.'}
    $roots=@($members|Where-Object PID -EQ $Root.PID)
    if($roots.Count -ne 1){throw 'Original root missing from world gate.'}
    $rootMember=$roots[0];Assert-MaterialV2MemberIdentity $rootMember
    if($rootMember.Image -ine $Root.Image -or $rootMember.CreatedUtc -cne $Root.CreatedUtc){throw 'Original root generation changed.'}
    foreach($member in $members|Where-Object PID -NE $Root.PID){
        Assert-MaterialV2MemberIdentity $member
        if($member.Image -ine $Policy.Telemetry -or $member.ParentPID -ne $Witness.CompilerIdentity.PID -or
           (Get-MaterialV2MemberTime $member.CreatedUtc) -lt (Get-MaterialV2MemberTime $Witness.CompilerIdentity.CreatedUtc) -or
           (Get-MaterialV2MemberTime $member.CreatedUtc) -gt (Get-MaterialV2MemberTime $Observation.CapturedUtc)){
            throw 'Unrecognized world pre-fixture survivor.'
        }
    }
}
function Assert-WorldObserverClosed($Identity) {
    if($Identity.JobRootExitedAtClose -isnot [bool] -or !$Identity.JobRootExitedAtClose -or
       ($Identity.JobActiveAtClose -isnot [uint32] -and $Identity.JobActiveAtClose -isnot [int] -and $Identity.JobActiveAtClose -isnot [long]) -or
       $Identity.JobActiveAtClose -ne 0 -or
       ($Identity.ExitCode -isnot [uint32] -and $Identity.ExitCode -isnot [int] -and $Identity.ExitCode -isnot [long]) -or
       $Identity.ExitCode -ne 0){throw 'Fresh original root0/Active0 required.'}
}
function Get-WorldObserverCompilerArguments([string]$VC,[string]$SDK,[string]$Version,[string]$World,[string]$RunRoot) {
    if($Version -cnotmatch '^10\.0\.\d+\.0$'){throw 'Exact Windows SDK version required.'}
    $includes=@((Join-Path $VC 'include'))+@('ucrt','shared','um'|ForEach-Object{Join-Path $SDK "Include/$Version/$_"})
    foreach($path in $includes){$null=Resolve-WorldObserverPath $path;if(!(Test-Path -LiteralPath $path -PathType Container)){throw 'Installed compiler include directory missing.'}}
    @('/nologo','/std:c++20','/EHsc','/MD','/O1','/W4','/D_CRT_SECURE_NO_WARNINGS')+
        @($includes|ForEach-Object{'/I'+$_})+
        @((Join-Path $World 'test_world_clipmap_observer.cpp'),('/Fo'+(Join-Path $RunRoot 'observer.obj')),
          ('/Fe'+(Join-Path $RunRoot 'observer.exe')),('/Fd'+(Join-Path $RunRoot 'observer.pdb')),'/link','/INCREMENTAL:NO',
          ('/LIBPATH:'+(Join-Path $VC 'lib/x64')),('/LIBPATH:'+(Join-Path $SDK "Lib/$Version/ucrt/x64")),
          ('/LIBPATH:'+(Join-Path $SDK "Lib/$Version/um/x64")),'bcrypt.lib')
}
