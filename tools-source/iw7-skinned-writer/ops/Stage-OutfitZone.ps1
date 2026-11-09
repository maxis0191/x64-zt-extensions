# Stage hero outfit models (+ new materials) into a PRIVATE copy of an assembled Station Zero zone source, then
# build it under the resource lease. Never touches the source work dir (read-only copy).
#   .\Stage-OutfitZone.ps1 -SourceWork <assembled ztwork of a good level build> -Work <own ztwork (new-work.ps1)>
#       -Models body_zmb_hero_jock_sztest,body_zmb_hero_jock_szred -KitDump <writer kitdump> [-MaterialRoots <dirs>] [-Build]
param(
  [Parameter(Mandatory)][string]$SourceWork,
  [Parameter(Mandatory)][string]$Work,
  [Parameter(Mandatory)][string[]]$Models,
  [Parameter(Mandatory)][string]$KitDump,                 # build_model.py --out (xmodel\, xsurface\)
  [string[]]$MaterialRoots=@(),                          # hero_material_zone.py --out dirs (images\, materials\, techsets\)
  [string]$OutfitsGsc="$PSScriptRoot\..\gsc\cp_iwz_outfits.gsc",
  [string]$Map='cp_iwz',
  [switch]$Refresh,                                      # re-copy the source zone (else reuse the private copy)
  [switch]$Build)
$ErrorActionPreference='Stop'
$Z="$Work\zonetool\$Map"
if($Refresh -or !(Test-Path $Z)){
  robocopy "$SourceWork\zonetool\$Map" $Z /E /MT:16 /NFL /NDL /NJH /NP /R:1 /W:1 | Out-Null
  Copy-Item "$SourceWork\zone_source\$Map.csv" "$Work\zone_source\$Map.csv" -Force
  Copy-Item "$SourceWork\zonetool.exe" "$Work\zonetool.exe" -Force
}
foreach($m in $Models){
  Copy-Item "$KitDump\xmodel\$m.xmb" "$Z\xmodel\" -Force
  Copy-Item "$KitDump\xsurface\${m}_lod0.xsb" "$Z\xsurface\" -Force
}
foreach($r in $MaterialRoots){ robocopy $r $Z /E /NFL /NDL /NJH /NP | Out-Null }
# level script: stock Spaceland character table -> data-driven outfit table
$g="$Z\scripts\cp\maps\$Map\$Map.gsc"; $text=[IO.File]::ReadAllText($g)
$old='scripts\cp\maps\cp_zmb\cp_zmb_player_character_setup::init_player_characters();'
if($text.Contains($old)){ [IO.File]::WriteAllText($g,$text.Replace($old,"scripts\cp\maps\$Map\cp_iwz_outfits::init_player_characters();")) }
Copy-Item $OutfitsGsc "$Z\scripts\cp\maps\$Map\cp_iwz_outfits.gsc" -Force
# zone rows: outfit script after the level script, models after the stock body row
$csv="$Work\zone_source\$Map.csv"; $rows=[IO.File]::ReadAllText($csv) -split "`n"; $out=[Collections.Generic.List[string]]::new()
$have=@{}; foreach($r in $rows){ $have[$r.TrimEnd("`r")]=1 }
$added=$false
foreach($r in $rows){
  $out.Add($r); $t=$r.TrimEnd("`r")
  if($t -eq "rawfile,scripts/cp/maps/$Map/$Map.gsc" -and !$have["rawfile,scripts/cp/maps/$Map/cp_iwz_outfits.gsc"]){ $out.Add("rawfile,scripts/cp/maps/$Map/cp_iwz_outfits.gsc") }
  if(!$added -and $t.StartsWith('xmodel,')){ foreach($m in $Models){ if(!$have["xmodel,$m"]){ $out.Add("xmodel,$m") } }; $added=$true }
}
[IO.File]::WriteAllText($csv,($out -join "`n"))
"staged $($Models -join ',') into $Z"
if($Build){
  $zt='C:\Users\ezvalo\Documents\IW7-Products\worktrees\sdk-hero-train\tools-source\iwzmap\zt.ps1'
  for($k=0;$k -lt 180;$k++){
    try{ & $zt -Work $Work -ZtArgs @('-buildzone',$Map) -TimeoutSec 2400 -Owner 'heroes-writer outfit zone build'; break }
    catch{ if($_.Exception.Message -match 'busy|Heavy job|wait'){ Start-Sleep 60; continue }; throw }
  }
}
