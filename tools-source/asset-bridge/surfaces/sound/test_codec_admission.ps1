$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Invoke-SoundCodec.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Codec syntax failed.'}
$outer=@($ast.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.TryStatementAst]})
if($outer.Count -ne 1){throw 'Expected one lifecycle try/finally.'}
$prefix=[Collections.Generic.List[string]]::new();$importSkipped=0;$endFound=$false
foreach($statement in $outer[0].Body.Statements){
    $text=$statement.Extent.Text
    if($text.StartsWith('[IO.Directory]::CreateDirectory')){$endFound=$true;break}
    if($text -ceq '. $scheduler'){$importSkipped++;continue}
    $prefix.Add($text)
}
if(!$endFound -or $importSkipped -ne 1){throw 'Admission test extraction differs.'}
$acquire=[scriptblock]::Create($prefix -join "`n")
$text=$outer[0].Finally.Extent.Text
$cleanup=[scriptblock]::Create($text.Substring(1,$text.Length-2))

function Test-Admission([string]$Case){
    # Actual acquisition/finally statements; the one provider import is omitted
    # and admission/guards/hashes are explicit pure mocks. No IO or native type.
    $events=[Collections.Generic.List[string]]::new()
    $guards=[Collections.Generic.List[object]]::new();$heldInputs=[Collections.Generic.List[object]]::new()
    $lease=$null;$owner=$null;$closed=$true;$intact=$true;$created=$false;$allInputsVerified=$false
    $PlanPath='plan';$PlanSHA256='plan-hash';$bootstrap=@('entry.ps1','scheduler.ps1')
    $profile=[pscustomobject]@{Name='NativeDumpF';SuccessStatus='DumpDecodedByFFmpeg'}
    $plan=[pscustomobject]@{RunRoot='mock-root';HashInputs=@('entry.ps1','codec.exe','scheduler.ps1','dump.flac')|ForEach-Object {[pscustomobject]@{Path=$_}}}
    $state=[ordered]@{Status='Preparing';RetainedLeaseToken=$null;Reservation=$null;Failure=$null;Cleanup=$null;
        JobDisposeCompleted=$false;InputHashesMatch=$false;JobClosed=$false;InputsUnchanged=$false;Quarantined=$false;
        ReadGuardsReleased=$false;ExternalDecoderVerified=$false;DumpDecodedByFFmpeg=$false}
    function Open-CodecReadGuard($Path){
        $events.Add('Guard:'+ $Path)
        if($Case -eq 'PayloadGuardFailure' -and $Path -ceq 'dump.flac'){throw 'mock payload guard failed'}
        $g=[pscustomobject]@{Path=$Path;Events=$events}
        $g|Add-Member ScriptMethod Dispose {$this.Events.Add('Dispose:'+ $this.Path)}
        $g
    }
    function Get-FileHash {param($LiteralPath);$events.Add('Hash:'+ $LiteralPath);[pscustomobject]@{Hash='plan-hash'}}
    function Assert-CodecHash($Entry){
        if(!@($guards|Where-Object Path -CEQ $Entry.Path).Count){throw 'test observed hash before guard'}
        if($Entry.Path -notin $bootstrap -and !$lease){throw 'test observed payload hash before admission'}
        $events.Add('Hash:'+ $Entry.Path)
        if($Case -eq 'BootstrapMismatch' -and $Entry.Path -ceq 'scheduler.ps1'){throw 'mock source drift'}
    }
    function Enter-IW7ResourceLease {param($Scope,$Kind,$PhysicalBytes,$CommitBytes,$Owner)
        if($PhysicalBytes -ne 512MB -or $CommitBytes -ne 1GB -or $Kind -cne 'Analysis'){throw 'Reservation bounds differ'}
        $events.Add('Admission')
        if($Case -eq 'AdmissionRefused'){throw 'mock admission refused'}
        [pscustomobject]@{Token='mock-token';Kind=$Kind;CreatedUtc='mock';PhysicalBytes=$PhysicalBytes;CommitBytes=$CommitBytes}
    }
    function Assert-CodecDumpEvidence($Plan){if(!$lease -or !$allInputsVerified){throw 'Evidence read before input proof'};$events.Add('Evidence')}
    function Save-CodecState {}
    function Measure-CodecOutputs {}
    function Exit-IW7ResourceLease {param($Token);$events.Add('Release')}
    $failure=$null
    try{. $acquire}catch{$failure=$_.Exception.Message;$state.Status='Failed';$state.Failure=$failure}
    . $cleanup
    if($Case -eq 'Success'){
        if($failure -or !$events.Contains('Evidence') -or !$events.Contains('Release')){throw 'Successful admitted path differs'}
        foreach($name in 'codec.exe','dump.flac'){
            if($events.IndexOf('Hash:'+ $name) -le $events.IndexOf('Admission')){throw 'Payload hash precedes admission'}
        }
    }else{
        if(!$failure){throw 'Failure fixture unexpectedly accepted'}
        if($Case -in @('AdmissionRefused','BootstrapMismatch')){
            if(@($events|Where-Object {$_ -match '^(Hash|Guard):(codec.exe|dump.flac)$'}).Count){throw 'Refusal touched a payload'}
            if($events.Contains('Release') -or $state.RetainedLeaseToken){throw 'Refusal invented a lease'}
        }else{
            if($events.Contains('Hash:dump.flac') -or $events.Contains('Release') -or !$state.Quarantined -or !$state.RetainedLeaseToken){throw 'Partial guard failure escaped quarantine'}
        }
    }
    if(!$state.ReadGuardsReleased){throw 'Guard release not reported'}
}
foreach($case in 'Success','AdmissionRefused','BootstrapMismatch','PayloadGuardFailure'){Test-Admission $case}
if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Unexpected native type loaded'}
'4 actual acquisition/finally ordering cases passed with mocks; no files, payload, codec or lease used.'
