param(
    [Parameter(Mandatory)][string]$ToolBinary,
    [Parameter(Mandatory)][ValidatePattern('^[A-Fa-f0-9]{64}$')][string]$ToolSHA256,
    [Parameter(Mandatory)][string]$StockRoot
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$stock = (Resolve-Path -LiteralPath $StockRoot).Path
$tool = (Resolve-Path -LiteralPath $ToolBinary).Path
if ((Get-Item -LiteralPath $stock).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Retail root must be a real directory.' }
if ((Get-FileHash -LiteralPath $tool).Hash -ne $ToolSHA256) { throw 'Exporter checksum differs from its recorded build.' }
$retail = Join-Path $stock 'iw7_ship.exe'
if ((Get-FileHash -LiteralPath $retail).Hash -ne 'A883EE28EE9F552C63D8ED1E352F60501B2E256D8857CA178C6DD3AAE622723B') { throw 'Unreviewed IW7 retail executable.' }
$work = Join-Path $repo ('runtime/doom-texture-work-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff'))
if (Test-Path -LiteralPath $work) { throw 'Fresh scratch directory required.' }
foreach ($folder in @('zone/english','main','zone_source','zonetool')) { New-Item -ItemType Directory -Path (Join-Path $work $folder) -Force | Out-Null }
$links = @()
function Add-DoomStockLink([string]$Relative, [string]$Source) {
    $file = Get-Item -LiteralPath $Source
    if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked source file refused.' }
    New-Item -ItemType HardLink -Path (Join-Path $work $Relative) -Target $file.FullName | Out-Null
    $script:links += [pscustomobject]@{Relative=$Relative;Source=$file.FullName;Length=$file.Length}
}
foreach ($name in @('iw7_ship.exe','amd_ags_x64.dll','bink2w64.dll','d3dcompiler_46.dll','steam_api.dll','steam_api64.dll','Steam.dll')) {
    $path = Join-Path $stock $name
    if (Test-Path -LiteralPath $path) { Add-DoomStockLink $name $path }
}
foreach ($zone in @('code_pre_gfx','code_post_gfx','global','common','global_mp','global_cp','common_mp','common_cp','cp_zmb')) {
    foreach ($prefix in @('','techsets_','patch_')) {
        $name = $prefix + $zone + '.ff'
        $path = Join-Path $stock $name
        if (Test-Path -LiteralPath $path) { Add-DoomStockLink ('zone/' + $name) $path }
    }
    foreach ($prefix in @('eng_','eng_patch_')) {
        $name = $prefix + $zone + '.ff'
        $path = Join-Path $stock ('english/' + $name)
        if (Test-Path -LiteralPath $path) { Add-DoomStockLink ('zone/english/' + $name) $path }
    }
}
foreach ($name in @('techsets_global_core_mp.ff','techsets_common_core_mp.ff')) {
    Add-DoomStockLink ('zone/' + $name) (Join-Path $stock $name)
}
# Engine initialization opens asset PAKs even before an explicit image capture.
# These are directory entries sharing existing bytes, not physical game copies.
foreach ($file in Get-ChildItem -LiteralPath $stock -File | Where-Object {$_.Name -match '^(assetfile|imagefile)\d+\.pak$'}) {
    Add-DoomStockLink ('zone/' + $file.Name) $file.FullName
}
# Mutable cache files belong to this tool; never link the owner's main state.
Copy-Item -LiteralPath (Join-Path $stock 'main/fileSysCheck.cfg') -Destination (Join-Path $work 'main/fileSysCheck.cfg')
Copy-Item -LiteralPath $tool -Destination (Join-Path $work 'zonetool.exe')
$links | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $work 'retail-links.json') -Encoding utf8
$work
