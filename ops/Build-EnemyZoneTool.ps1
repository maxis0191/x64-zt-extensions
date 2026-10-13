param([switch]$Rebuild)
# Source reproducibility and explicit binary review, not a byte-reproducibility claim.
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$source = Join-Path $repo 'tools/x64-zt-enemy'
$pinPath = Join-Path $PSScriptRoot 'enemy-ports/lab-enemy-toolchain.json'
$pin = Get-Content -LiteralPath $pinPath -Raw | ConvertFrom-Json
if ($pin.Repository -ne 'https://github.com/bigmangeekf/x64-zt.git' -or $pin.SourceCommit -notmatch '^[a-f0-9]{40}$' -or
    @($pin.AcceptedBinarySHA256 | Where-Object { $_ -notmatch '^[A-Fa-f0-9]{64}$' }).Count) { throw 'Invalid reviewed enemy-tool pin.' }
. "$PSScriptRoot/Lab-Paths.ps1"
. "$PSScriptRoot/Resource-Scheduler.Core.ps1"
$null = Assert-IW7LabPath $source $repo
$runtime = Join-Path $repo 'runtime/enemy-zonetool-builds'
$null = Assert-IW7LabPath $runtime $repo
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
if (!(Test-Path -LiteralPath $vswhere)) { throw 'VS2022 C++/ATL tools are required; run ops/Install-Tools.ps1 -IncludeEnemyTools.' }
$installation = & $vswhere -products '*' -version '[17.0,18.0)' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 Microsoft.VisualStudio.Component.VC.ATL -property installationPath | Select-Object -First 1
if ($LASTEXITCODE -or !$installation) { throw 'VS2022 C++/ATL tools were not found.' }
$msbuild = Join-Path $installation 'MSBuild/Current/Bin/MSBuild.exe'
$vcVersion = (Get-Content -LiteralPath (Join-Path $installation 'VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt') -Raw).Trim()
if ($vcVersion -notmatch '^14\.\d+\.\d+$') { throw 'Unexpected installed MSVC toolset version.' }
$compiler = Join-Path $installation "VC/Tools/MSVC/$vcVersion/bin/Hostx64/x64/cl.exe"
foreach ($path in @($msbuild,$compiler)) { if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required native tool missing: $path" } }
Get-Command git -ErrorAction Stop | Out-Null

function Invoke-EnemyToolGit([string[]]$Arguments) {
    $result = @(& git @Arguments)
    if ($LASTEXITCODE) { throw "Enemy-tool Git operation failed: $($Arguments -join ' ')" }
    $result
}
function Assert-EnemyToolSource([switch]$AllowUninitialized) {
    $null = Assert-IW7LabPath $source $repo
    if (!(Test-Path -LiteralPath "$source/.git" -PathType Container)) { throw 'Existing tool path is not the expected independent clone; preserve it.' }
    $null = Assert-IW7LabPath "$source/.git" $source
    $top = @(Invoke-EnemyToolGit @('-C',$source,'rev-parse','--show-toplevel'))
    $origin = @(Invoke-EnemyToolGit @('-C',$source,'remote','get-url','origin'))
    $head = @(Invoke-EnemyToolGit @('-C',$source,'rev-parse','HEAD'))
    if ($top.Count -ne 1 -or [IO.Path]::GetFullPath($top[0]) -ne [IO.Path]::GetFullPath($source) -or
        $origin.Count -ne 1 -or $origin[0] -ne $pin.Repository -or $head.Count -ne 1 -or $head[0] -ne $pin.SourceCommit) {
        throw 'Existing tool checkout does not match the reviewed repository/commit. No checkout, reset or overwrite was performed.'
    }
    if (@(Invoke-EnemyToolGit @('-C',$source,'status','--porcelain','--untracked-files=all','--ignore-submodules=none')).Count) {
        throw 'Enemy-tool source/submodules contain local changes; preserve them before building.'
    }
    $submodules = @(Invoke-EnemyToolGit @('-C',$source,'submodule','status','--recursive'))
    foreach ($line in $submodules) {
        if ($line -notmatch '^[ -][a-f0-9]{40} .+') { throw 'A submodule is conflicted or differs from its recorded revision; no reset was performed.' }
        if ($line[0] -eq '-') {
            if (!$AllowUninitialized) { throw 'A pinned submodule is still uninitialized.' }
            $relative = $line.Substring(42)
            $subPath = Join-Path $source $relative
            $null = Assert-IW7LabPath $subPath $source
            if ((Test-Path -LiteralPath $subPath) -and @(Get-ChildItem -LiteralPath $subPath -Force).Count) {
                throw "Uninitialized submodule path is occupied; preserving $relative."
            }
        }
    }
    $submodules
}
function Invoke-EnemyToolBuild([string]$Project, [string]$Log, [string]$Target = 'Build') {
    $arguments = @($Project,"/t:$Target",'/m:1','/nr:false','/v:minimal','/p:Configuration=Release','/p:Platform=x64',
        '/p:MultiProcessorCompilation=false','/p:CL_MPCount=1','/p:PreferredToolArchitecture=x64',
        "/p:VCToolsVersion=$vcVersion",'/p:PostBuildEventUseInBuild=false')
    & $msbuild @arguments *> $Log
    if ($LASTEXITCODE) { throw "Enemy-tool compilation failed; inspect $Log" }
}

Invoke-IW7ResourceJob -Scope $source -Kind Build -Owner 'Pinned enemy ZoneTool and asset-free tests' -PhysicalBytes 4GB -CommitBytes 6GB -Body {
    if (!(Test-Path -LiteralPath $source)) {
        # Only a newly created clone may be checked out. Existing branches stay put.
        New-Item -ItemType Directory -Path (Split-Path $source -Parent) -Force | Out-Null
        Invoke-EnemyToolGit @('clone','--no-checkout','--', $pin.Repository,$source) | Out-Null
        Invoke-EnemyToolGit @('-C',$source,'checkout','--detach',$pin.SourceCommit) | Out-Null
    }
    $null = Assert-EnemyToolSource -AllowUninitialized
    Invoke-EnemyToolGit @('-C',$source,'submodule','update','--init','--recursive','--jobs','1') | Out-Null
    $submodulePins = @(Assert-EnemyToolSource)
    $run = Join-Path $runtime ([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $run -Force | Out-Null
    $binary = Join-Path $source 'build/bin/x64/Release/zonetool.exe'
    $null = Assert-IW7LabPath $binary $source
    $previousHash = if (Test-Path -LiteralPath $binary) { (Get-FileHash -LiteralPath $binary).Hash } else { $null }
    $reuse = !$Rebuild -and $previousHash -and $previousHash -in $pin.AcceptedBinarySHA256
    $provenance = [ordered]@{
        StartedUtc=[DateTime]::UtcNow.ToString('o'); Repository=$pin.Repository; SourceCommit=$pin.SourceCommit;
        PinSHA256=(Get-FileHash -LiteralPath $pinPath).Hash; Submodules=$submodulePins;
        Mode=$(if ($reuse) {'ReuseReviewedBinary'} else {'ReleaseRebuild'}); Status='Running';
        Compiler=[ordered]@{Path=$compiler;Toolset=$vcVersion;FileVersion=(Get-Item -LiteralPath $compiler).VersionInfo.FileVersion;SHA256=(Get-FileHash -LiteralPath $compiler).Hash};
        MSBuild=[ordered]@{Path=$msbuild;FileVersion=(Get-Item -LiteralPath $msbuild).VersionInfo.FileVersion;SHA256=(Get-FileHash -LiteralPath $msbuild).Hash};
        Jobs=1;MultiProcessorCompilation=$false;Priority='BelowNormal';Tests=@();PreviousBinarySHA256=$previousHash;
        BinaryCompiler=$(if ($reuse) {'Not inferred for reused binary; Compiler records the test compiler.'} else {'Compiler field records the explicitly selected build/test compiler.'});
        Validation='Source build and asset-free tests only; package/gameplay validation remains separate.'
    }
    $manifest = Join-Path $run 'provenance.json'
    $oldCL = $env:CL; $oldTrailingCL = $env:_CL_
    Push-Location $source
    try {
        # Prevent inherited compiler options from re-enabling /MP. Process local.
        $env:CL=$null; $env:_CL_=$null
        if (!$reuse) {
            if ($previousHash) { Copy-Item -LiteralPath $binary -Destination "$run/previous-zonetool.exe" }
            & ./tools/premake5.exe vs2022 *> "$run/premake.log"
            if ($LASTEXITCODE) { throw "ZoneTool project generation failed; inspect $run/premake.log" }
            # Premake emits literal item metadata, which /p alone cannot override.
            # Change only ignored generated projects, never reviewed source.
            $projects = @(Get-ChildItem -LiteralPath "$source/build" -Filter '*.vcxproj' -File -Recurse)
            if (!$projects.Count) { throw 'Premake produced no native projects.' }
            foreach ($project in $projects) {
                $null = Assert-IW7LabPath $project.FullName $source
                $xml = New-Object Xml.XmlDocument
                $xml.PreserveWhitespace=$true; $xml.Load($project.FullName)
                foreach ($node in $xml.SelectNodes('//*[local-name()="MultiProcessorCompilation"]')) { $node.InnerText='false' }
                foreach ($node in $xml.SelectNodes('//*[local-name()="AdditionalOptions"]')) {
                    if ($node.InnerText -match '(?i)(?:^|\s)/MP(?:\d|\s|$)') { throw 'Explicit /MP compiler option needs review.' }
                }
                $xml.Save($project.FullName)
            }
            Invoke-EnemyToolBuild 'build/x64-zt.sln' "$run/release-build.log" 'Rebuild'
        }
        foreach ($name in @('filesystem_ownership_tests','sound_bank_subset_tests')) {
            Invoke-EnemyToolBuild "tests/$name.vcxproj" "$run/$name-build.log" 'Rebuild'
            & "./build/tests/$name.exe" *> "$run/$name-run.log"
            if ($LASTEXITCODE) { throw "Asset-free test failed; inspect $run/$name-run.log" }
            $provenance.Tests += [ordered]@{Name=$name;Passed=$true;LogSHA256=(Get-FileHash -LiteralPath "$run/$name-run.log").Hash}
        }
        $null = Assert-EnemyToolSource
        if ((Get-FileHash -LiteralPath $pinPath).Hash -ne $provenance.PinSHA256) { throw 'Reviewed tool pin changed during the run; candidate requires review.' }
        $hash = (Get-FileHash -LiteralPath $binary).Hash
        Copy-Item -LiteralPath $binary -Destination "$run/zonetool.exe"
        if (Test-Path -LiteralPath "$source/build/bin/x64/Release/zonetool.pdb") {
            Copy-Item -LiteralPath "$source/build/bin/x64/Release/zonetool.pdb" -Destination "$run/zonetool.pdb"
        }
        $provenance.BinarySHA256=$hash
        $provenance.AcceptedBinary=($hash -in $pin.AcceptedBinarySHA256)
        $provenance.Status=$(if ($provenance.AcceptedBinary) {'TestsPassedReviewedBinary'} else {'TestsPassedReviewRequired'})
        Write-Output "Enemy ZoneTool tests passed. Binary: $run/zonetool.exe; SHA256: $hash"
        if (!$provenance.AcceptedBinary) { Write-Warning 'Candidate retained. Its hash is not accepted; review and offline/runtime validation are required before updating pins or installing a package.' }
    } catch {
        $provenance.Status='Failed'; $provenance.Error=$_.Exception.Message
        throw
    } finally {
        $env:CL=$oldCL; $env:_CL_=$oldTrailingCL
        Pop-Location
        $provenance.FinishedUtc=[DateTime]::UtcNow.ToString('o')
        $provenance | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifest -Encoding UTF8
        Write-Output "Enemy ZoneTool provenance: $manifest"
    }
}
