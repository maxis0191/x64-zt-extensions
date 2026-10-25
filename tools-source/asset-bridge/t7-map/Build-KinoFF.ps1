param(
    [Parameter(Mandatory)][string]$BuildRoot,      # kino_compose output (+ assets/ from kino-writer)
    [Parameter(Mandatory)][string]$Work,           # fresh work directory
    [Parameter(Mandatory)][string]$PreparedSource, # iw7-paris-server prepared inputs (resource scheduler)
    [Parameter(Mandatory)][string]$StockRoot,      # IW7 game root (read-only stock)
    [Parameter(Mandatory)][string]$ZoneTool,       # measured community ZoneTool (IW7 mode)
    [Parameter(Mandatory)][string]$TlsDll,
    [Parameter(Mandatory)][string]$Sentinel,       # main/fileSysCheck.cfg source
    [string]$Zone='kino'
)
# Builds the Kino overlay fastfile in an owned work directory: stock FFs/paks are
# hard links (read-only use), the executable/DLLs are copies (ff-work-profile.json).
$ErrorActionPreference='Stop'
$Work=[IO.Path]::GetFullPath($Work)
if(Test-Path -LiteralPath $Work){throw 'Fresh work directory required.'}
. "$PreparedSource/ops/Resource-Scheduler.Core.ps1"
$profile=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'ff-work-profile.json') -Raw|ConvertFrom-Json
$lease=Enter-IW7ResourceLease -Scope $Work -Kind Build -PhysicalBytes 6GB -CommitBytes 8GB -Owner 'Kino overlay fastfile build'
try{
    [IO.Directory]::CreateDirectory($Work)|Out-Null
    foreach($i in $profile.inputs){
        $dst=Join-Path $Work $i.relative
        [IO.Directory]::CreateDirectory((Split-Path $dst -Parent))|Out-Null
        $src=switch($i.role){'tlsdll'{$TlsDll}'sentinel'{$Sentinel}default{Join-Path $StockRoot $i.stock_name}}
        if($i.mode -eq 'HardLink'){New-Item -ItemType HardLink -Path $dst -Target $src|Out-Null}else{Copy-Item -LiteralPath $src -Destination $dst}
    }
    Copy-Item -LiteralPath $ZoneTool -Destination (Join-Path $Work 'zonetool.exe')
    foreach($d in @('zone_source','materials','techsets','netconststrings','vision')|Where-Object {Test-Path (Join-Path $BuildRoot $_)}){Copy-Item -LiteralPath (Join-Path $BuildRoot $d) -Destination (Join-Path $Work $d) -Recurse}
    foreach($d in 'xmodel','xsurface','images'){Copy-Item -LiteralPath (Join-Path $BuildRoot "assets/$d") -Destination (Join-Path $Work $d) -Recurse}
    $p=Start-Process -FilePath (Join-Path $Work 'zonetool.exe') -ArgumentList '-headless','-unbuffered-io','-strict-content-sources','-buildzone',$Zone -WorkingDirectory $Work -RedirectStandardOutput (Join-Path $Work 'build.stdout.log') -RedirectStandardError (Join-Path $Work 'build.stderr.log') -PassThru -NoNewWindow
    Add-IW7ResourceProcess -Token $lease.Token -ProcessId $p.Id
    if(!$p.WaitForExit(1800000)){Stop-Process -Id $p.Id;throw 'ZoneTool build deadline exceeded.'}
    $ff=Join-Path $Work "zone/$Zone.ff"
    [pscustomobject]@{FF=$ff;Exists=(Test-Path $ff);Bytes=$(if(Test-Path $ff){(Get-Item $ff).Length}else{0})}|ConvertTo-Json
}finally{
    Exit-IW7ResourceLease -Token $lease.Token
}
