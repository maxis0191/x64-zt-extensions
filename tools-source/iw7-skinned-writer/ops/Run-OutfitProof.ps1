# Private local outfit proof: one run of the server repository's local map runner with the outfit fixture.
# Never deploys; sv_cheats stays 0. It runs once and does not retry: when the machine's slot is busy it says so and
# stops. To queue a session use the game lab of the server repository (ops/gamelab, -WaitForSlotSeconds).
#   .\Run-OutfitProof.ps1 -Runner <server checkout>\ops\iwzmap\Test-IWZMapLocal.ps1 -SourcePackage <prepared source package>
#       -GameRoot <bench root> -InjectDll <error journal dll> -UsermapDir <dir with cp_iwz.ff + .arena> -OutputRoot <new run dir>
#       [-View "x,y,z,yaw"] [-Models a,b,c] [-Anims x,y]
# -GameRoot must be a bench root made by ops/bench/New-BenchRoot.ps1 (server repository). The owner's game folder is refused.
param(
  [Parameter(Mandatory)][string]$Runner,
  [Parameter(Mandatory)][string]$SourcePackage,
  [Parameter(Mandatory)][string]$GameRoot,
  [Parameter(Mandatory)][string]$InjectDll,
  [Parameter(Mandatory)][string]$UsermapDir,
  [Parameter(Mandatory)][string]$OutputRoot,
  [switch]$SecondClient,[int]$Seconds=170,[string]$Extra='',[string]$View='',[string]$Models='',[string]$Anims='',
  [string]$Fixture="$PSScriptRoot\..\gsc\iwzmap_outfit_fixture.gsc")
$ErrorActionPreference='Stop'
foreach($path in @($Runner,$InjectDll,$Fixture)){if(!(Test-Path -LiteralPath $path -PathType Leaf)){throw "File not found: $path"}}
foreach($path in @($SourcePackage,$UsermapDir)){if(!(Test-Path -LiteralPath $path -PathType Container)){throw "Folder not found: $path"}}
# A bench root carries this manifest at its top (written by ops/bench/New-BenchRoot.ps1). Anything else is refused.
if(!(Test-Path -LiteralPath (Join-Path $GameRoot 'paris-bench-root.json') -PathType Leaf)){
  throw "GameRoot is not a bench root (paris-bench-root.json is absent): $GameRoot. Make one with ops/bench/New-BenchRoot.ps1 of the server repository; never test in the owner's game folder."
}
if(Test-Path -LiteralPath $OutputRoot){throw "OutputRoot already exists; give a new folder: $OutputRoot"}
$xargs=@(); if($Extra){$xargs+=$Extra}; if($View){$xargs+="+set paris_iwz_outfit_view $View"}; if($Models){$xargs+="+set paris_iwz_outfit_models $Models"}; if($Anims){$xargs+="+set paris_iwz_outfit_anims $Anims"}
$out = & $Runner -SourcePackage $SourcePackage -GameRoot $GameRoot -OutputRoot $OutputRoot -UsermapDir $UsermapDir -Map cp_iwz -Fixture $Fixture -Seconds $Seconds -SecondClient:$SecondClient -ExtraArgs ($xargs -join ' ') -InjectDll $InjectDll 2>&1 | Out-String
$out; "RUN_OUT $OutputRoot"
if($out -match 'error=Resource busy|Base game occupied|error=Resource lease not found|Child identity unavailable'){
  Write-Output 'The session did not start: the slot is busy or its lease was not available. Nothing was retried and the output folder is kept.'
  exit 2
}
