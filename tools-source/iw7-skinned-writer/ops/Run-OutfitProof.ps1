# Private local outfit proof run (retries while the base game / leases are busy). Never deploys; sv_cheats stays 0.
#   .\Run-OutfitProof.ps1 -UsermapDir <dir with cp_iwz.ff + .arena> -OutRoot <runs dir> [-View "x,y,z,yaw"] [-Models a,b,c] [-Anims x,y]
param([Parameter(Mandatory)][string]$UsermapDir,[Parameter(Mandatory)][string]$OutRoot,[string]$View='',[string]$Models='',[string]$Anims='',
  [string]$Fixture="$PSScriptRoot\..\gsc\iwzmap_outfit_fixture.gsc",
  [string]$Runner='C:\Users\ezvalo\Documents\IW7-Paris-Server\.claude\worktrees\custom-zombies-map-iwz-26cd2d\ops\iwzmap\Test-IWZMapLocal.ps1',
  [string]$InjectDll='C:\Users\ezvalo\Documents\IW7-Runtime\iwz-stage2\audio\errjournal\v4\iw7_error_journal.dll')
$extra=@(); if($View){$extra+="+set paris_iwz_outfit_view $View"}; if($Models){$extra+="+set paris_iwz_outfit_models $Models"}; if($Anims){$extra+="+set paris_iwz_outfit_anims $Anims"}
for($k=0;$k -lt 180;$k++){
  $o=Join-Path $OutRoot ("run_{0:000}" -f $k)
  $out = & $Runner -SourcePackage C:\Users\ezvalo\Documents\IW7-Runtime\iwz-stage2\srcpkg-shared -GameRoot C:\Users\ezvalo\Desktop\iw_game_files -OutputRoot $o -UsermapDir $UsermapDir -Map cp_iwz -Fixture $Fixture -Seconds 170 -ExtraArgs ($extra -join ' ') -InjectDll $InjectDll 2>&1 | Out-String
  if($out -match 'error=Resource busy|Base game occupied|error=Resource lease not found|Child identity unavailable'){ Remove-Item $o -Recurse -Force -ErrorAction SilentlyContinue; Start-Sleep 60; continue }
  $out; "RUN_OUT $o"; break
}
