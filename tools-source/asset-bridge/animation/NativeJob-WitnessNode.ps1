# Fixture child only. Launched by Run-NativeJobWitness.ps1 after admission.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Parent','Child','Grandchild','Foreign','Launcher')][string]$Role,
    [Parameter(Mandatory)][string]$CaseRoot,
    [Parameter(Mandatory)][string]$PowerShellExe,
    [Parameter(Mandatory)][string]$Nonce,
    [string]$HelperAssembly,[string]$HelperSHA256
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell7 required.'}
$CaseRoot=[IO.Path]::GetFullPath($CaseRoot)
$ticket=Get-Content -LiteralPath (Join-Path $CaseRoot 'fixture-ticket.json') -Raw | ConvertFrom-Json
if($ticket.Nonce -cne $Nonce -or ([datetime]$ticket.ExpiresUtc).ToUniversalTime() -le [datetime]::UtcNow -or $ticket.Kind -cne 'iw7.native-job-fixture/1'){throw 'Missing, expired or mismatched fixture ticket.'}
function New-NodeStart([string]$NextRole) {
    $start=[Diagnostics.ProcessStartInfo]::new($PowerShellExe)
    $start.WorkingDirectory=$CaseRoot;$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle='Hidden'
    foreach($arg in @('-NoProfile','-File',$PSCommandPath,'-Role',$NextRole,'-CaseRoot',$CaseRoot,'-PowerShellExe',$PowerShellExe,'-Nonce',$Nonce)){$start.ArgumentList.Add($arg)}
    $start
}
function Write-NodeIdentity {
    $self=Get-Process -Id $PID
    $identity=[ordered]@{Role=$Role;PID=$PID;CreationFileTime=$self.StartTime.ToUniversalTime().ToFileTimeUtc();Image=$self.Path;Nonce=$Nonce}
    $pending=Join-Path $CaseRoot "$Role.ready.pending.json"
    $final=Join-Path $CaseRoot "$Role.ready.json"
    $bytes=[Text.Encoding]::UTF8.GetBytes(($identity | ConvertTo-Json))
    $stream=[IO.File]::Open($pending,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try {$stream.Write($bytes,0,$bytes.Length)} finally {$stream.Dispose()}
    [IO.File]::Move($pending,$final)
}
$inner=$null
try {
    if($Role -eq 'Launcher'){
        if((Get-FileHash -LiteralPath $HelperAssembly).Hash -ine $HelperSHA256){throw 'Fixture helper assembly hash differs.'}
        $null=[Reflection.Assembly]::LoadFrom($HelperAssembly)
        $inner=[IW7.AnimationProbe.NativeJob]::new()
        $inner.Start((New-NodeStart 'Parent'),(Get-FileHash -LiteralPath $PowerShellExe).Hash,(Join-Path $CaseRoot 'inner.stdout.log'),(Join-Path $CaseRoot 'inner.stderr.log'))
    } elseif($Role -in @('Parent','Child')){
        $next=if($Role -eq 'Parent'){'Child'}else{'Grandchild'}
        $spawn=[Diagnostics.Process]::new();$spawn.StartInfo=New-NodeStart $next
        try {if(!$spawn.Start()){throw "Fixture could not start $next"}} finally {$spawn.Dispose()}
        # Normal CreateProcess descendants inherit the root's native Job Object.
    }
    Write-NodeIdentity
    $deadline=[datetime]::UtcNow.AddSeconds(60)
    while(!(Test-Path -LiteralPath (Join-Path $CaseRoot 'finish'))){
        if($Role -eq 'Parent' -and (Test-Path -LiteralPath (Join-Path $CaseRoot 'parent-exit'))){break}
        if([datetime]::UtcNow -ge $deadline){throw 'Fixture self-expiry without completion signal.'}
        Start-Sleep -Milliseconds 50
    }
} finally {
    # The forced-launcher-exit case deliberately prevents this finally from
    # running. Its inner job's last OS handle then closes in that process.
    if($inner -and !$inner.Closed){$inner.StopAndConfirm(5000)}
}
