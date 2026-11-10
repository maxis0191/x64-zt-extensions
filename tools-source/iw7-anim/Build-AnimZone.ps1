param(
    [Parameter(Mandatory)][string]$Source,         # tree written by `iw7_anim_gltf.py zone-source` (zonetool/<zone>, zone_source/<zone>.csv)
    [Parameter(Mandatory)][string]$Work,           # fresh private work folder, on the volume of the stock
    [Parameter(Mandatory)][string]$PreparedSource, # iw7-paris-server prepared inputs (resource scheduler)
    [Parameter(Mandatory)][string]$StockRoot,      # stock game files (hard-linked, read-only use)
    [Parameter(Mandatory)][string]$ZoneTool,       # zonetool.exe (IW7 mode)
    [Parameter(Mandatory)][string]$TlsDll,
    [Parameter(Mandatory)][string]$Sentinel,       # main/fileSysCheck.cfg source
    [string]$Zone='mod',
    [int]$TimeoutSec=900,
    [ValidateRange(0,14400)][int]$WaitForSlotSeconds=0   # how long to wait for the build reservation instead of failing at once
)
# Builds a small fastfile of animations in a private work folder: stock fastfiles are hard links (read-only use),
# executables are copies (the profile of ../asset-bridge/t7-map/ff-work-profile.json), one Build lease covers the
# run. The result is <Work>/zone/<Zone>.ff. Delete the work folder file by file, never with a forced recursive
# delete: forcing would change attributes on files shared with the stock.
$ErrorActionPreference='Stop'
$Work=[IO.Path]::GetFullPath($Work)
if(Test-Path -LiteralPath $Work){throw 'Fresh work directory required.'}
foreach($need in @("zone_source/$Zone.csv","zonetool/$Zone")){ if(!(Test-Path -LiteralPath (Join-Path $Source $need))){ throw "Missing in the source tree: $need" } }
. "$PreparedSource/ops/Resource-Scheduler.Core.ps1"
$profile=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../asset-bridge/t7-map/ff-work-profile.json') -Raw|ConvertFrom-Json
$deadline=(Get-Date).AddSeconds($WaitForSlotSeconds); $pause=30; $lease=$null
while(!$lease){
    try{ $lease=Enter-IW7ResourceLease -Scope $Work -Kind Build -PhysicalBytes 6GB -CommitBytes 8GB -Owner 'animation fastfile build' }
    catch{
        if($_.Exception.Message -notmatch 'Resource busy|already reserved|laboratory is running|wait before heavy admission|identity unavailable' -or (Get-Date) -ge $deadline){ throw }
        Start-Sleep -Seconds $pause; $pause=[Math]::Min(300,$pause*2)
    }
}
try{
    [IO.Directory]::CreateDirectory($Work)|Out-Null
    foreach($i in $profile.inputs){
        $dst=Join-Path $Work $i.relative
        [IO.Directory]::CreateDirectory((Split-Path $dst -Parent))|Out-Null
        $src=switch($i.role){'tlsdll'{$TlsDll}'sentinel'{$Sentinel}default{Join-Path $StockRoot $i.stock_name}}
        if($i.mode -eq 'HardLink'){New-Item -ItemType HardLink -Path $dst -Target $src|Out-Null}else{Copy-Item -LiteralPath $src -Destination $dst}
    }
    Copy-Item -LiteralPath $ZoneTool -Destination (Join-Path $Work 'zonetool.exe')
    Copy-Item -LiteralPath (Join-Path $Source 'zone_source') -Destination (Join-Path $Work 'zone_source') -Recurse
    Copy-Item -LiteralPath (Join-Path $Source 'zonetool') -Destination (Join-Path $Work 'zonetool') -Recurse
    $p=Start-Process -FilePath (Join-Path $Work 'zonetool.exe') -ArgumentList '-headless','-unbuffered-io','-strict-content-sources','-buildzone',$Zone -WorkingDirectory $Work -RedirectStandardOutput (Join-Path $Work 'build.stdout.log') -RedirectStandardError (Join-Path $Work 'build.stderr.log') -PassThru -NoNewWindow
    Add-IW7ResourceProcess -Token $lease.Token -ProcessId $p.Id
    if(!$p.WaitForExit($TimeoutSec*1000)){Stop-Process -Id $p.Id;throw 'ZoneTool build deadline exceeded.'}
    $ff=Join-Path $Work "zone/$Zone.ff"
    [pscustomobject]@{FF=$ff;Exists=(Test-Path $ff);Bytes=$(if(Test-Path $ff){(Get-Item $ff).Length}else{0});ExitCode=$p.ExitCode}|ConvertTo-Json
    if(!(Test-Path $ff)){exit 1}
}finally{
    Exit-IW7ResourceLease -Token $lease.Token
}
