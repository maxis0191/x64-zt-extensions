$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$plan=Get-Content -LiteralPath "$repo/tools-source/asset-bridge/world/observer-harness-plan.json" -Raw | ConvertFrom-Json
if((Get-FileHash -LiteralPath "$repo/tools-source/asset-bridge/t7-iw7/T7Build.Profile.ps1").Hash -ine $plan.link_profile_sha256){
    throw 'World requires the exact frozen T7 link provider bytes, including checkout line endings.'
}
& python -m py_compile "$repo/ops/doom-source/inspect_blender.py"
if($LASTEXITCODE){throw 'Controlled Blender inspector syntax failed.'}
Write-Output 'Frozen world link provider and controlled inspector syntax verified.'
