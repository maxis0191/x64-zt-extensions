# Exercise the actual early validator. Optional frozen-plan DEFAULT tests use
# temporary JSON text only and never pass -Run or change the frozen plan.
[CmdletBinding()]
param([string]$MultisurfaceFixturePlanPath)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$runner=Join-Path $PSScriptRoot 'Run-T7Build.ps1';$errors=$null;$tokens=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($runner,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner syntax errors.'}
$definition=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Assert-T7InputBindings'},$true)
if(!$definition){throw 'Actual binding validator missing.'}
. ([scriptblock]::Create($definition.Extent.Text))
$checks=0;$entryChecks=0
function New-BindingFixture {
    $headers=@(foreach($match in [regex]::Matches([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'prepare_build.py')),
        "(?m)^    '(src/[^']+\.hpp)': \(([0-9]+), '([0-9a-f]{64})'\),")) {
        [pscustomobject]@{Path=('C:\native\'+$match.Groups[1].Value.Replace('/','\'));Bytes=[int]$match.Groups[2].Value;SHA256=$match.Groups[3].Value}
    })
    if($headers.Count -ne 66){throw 'Existing reviewed header table not found.'}
    $readSHA='d9cdd533796a9fe14e0d5140d8adcbf5cbc932fafd4c06e18a615d15199a2185'
    $compileSHA='a7083ce5b9ba2fe1421c4f8733cf1d1e0b286549dbc55a44f3ef30ceb3c05333'
    $linkSHA='70455d2f32a9b034dda20fbaf48443ee68a02e552381edbf88b19d219f1f66b2'
    $transitions=@(foreach($row in @(
        @('main.cpp',12854,'40de5fda829cec32a5d75359f58e69c84db7d8ee54f198cf6befa2a6ebe6f86e',12944,'ce4fdd46c2da6e777f1142a8b9cb4a7b9fb78715a14e146fcb73e7577bc68615',43038,'3ff489d38adfa4da640c5acd6a78b1600f312fbaef47d41b118fabd7dcd3fb84'),
        @('zonetool.cpp',35974,'106ccdb4aec584184132c309c117f778d504ca9e64e8a821d23bfecc83bc8635',39356,'27c2c8d79e6af6307315ddcd94e4abd58ab774e08895e032d09334b6ef1b360e',39410,'b470e08edaa26c3527d02cab89a867192371290dda02c16c5569acd7d6819279'),
        @('t7_iw7_resident_model.hpp',13444,'6d2da3d4f7c3d0686909dc488f3d176ee2dd250e8d43d9a3cd9bcfa701482777',21290,'97a417b82ab7edf002f73039d1280b5e2a34370594e151ff07698db3a81f65ed',21290,'97a417b82ab7edf002f73039d1280b5e2a34370594e151ff07698db3a81f65ed'))) {
        [pscustomobject]@{Path=('prepared/'+$row[0]);PreviousBytes=$row[1];PreviousSHA256=$row[2];Bytes=$row[3];SHA256=$row[4];WiredBytes=$row[5];WiredSHA256=$row[6]}
    })
    $dependencies=@(foreach($row in @(
        @('helper',16296,'6897d27e8fe0754509e52258082d6178c8cb74fe21a8ef4b006006e97ab9dd12'),
        @('zonetool11',76744,'cfe62be9ce9bf87abd8e6713f1e1f334d76f69472500d2cb260696de26ee8273'),
        @('xpak',64444,'3d742923def4fb049d82853ac0e776ffd071228deaf1da1a624603d10dfd3908'))) {
        [pscustomobject]@{Path=('C:\old\'+$row[0]+'\dependencies.json');Bytes=$row[1];SHA256=$row[2]}
    })
    $bindings=@(foreach($pin in @($headers)+@($dependencies)) {
        [pscustomobject]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true}
    })
    foreach($row in @(@('CL.read.1.tlog',15206288,$readSHA),@('CL.command.1.tlog',1024,$compileSHA),@('link.command.1.tlog',1024,$linkSHA))) {
        $bindings+=@([pscustomobject]@{Path=('C:\e7\obj\tlog\'+$row[0]);Bytes=$row[1];SHA256=$row[2];IsText=$true})
    }
    foreach($row in $transitions) {
        $bindings+=@([pscustomobject]@{Path=('C:\plan\'+$row.Path.Replace('/','\'));Bytes=$row.WiredBytes;SHA256=$row.WiredSHA256;IsText=$true})
    }
    while($bindings.Count -lt 135){$bindings+=@([pscustomobject]@{Path=('C:\fixture\text'+$bindings.Count+'.txt');Bytes=1;SHA256=('a'*64);IsText=$true})}
    foreach($row in @(
        @('cl.exe',677776,'fe251ef50a1545b1b0835ee17b1e785459712b38d79e45b5c1d3d28970a36619'),
        @('link.exe',3252616,'a364af801a8539e4324d9489313dbf001d959128451fc99a27b24676bbac058f'),
        @('probe-nativejob.dll',13312,'5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8'),
        @('rc.exe',55640,'43da1503c262c30894c851589bf0155f8365d77e63a5f7bc13982320e3a6b42d'),
        @('rcdll.dll',264536,'9a11e4759adc48abe1fa9e3082ad7db4b53f4d6d77701c13729f4ffd47ae934c'),
        @('vctip.exe',335288,'d591358c6aee4b673562ca3b3a15c250e612708394fe3b44a7a7eda2470570a5'))) {
        $bindings+=@([pscustomobject]@{Path=('C:\fixture\'+$row[0]);Bytes=$row[1];SHA256=$row[2];IsText=$false})
    }
    $inputs=@($headers)
    1..1080|ForEach-Object {$inputs+=@([pscustomobject]@{Path=('C:\baseline\input'+$_);Bytes=1;SHA256=('a'*64)})}
    $proof=[pscustomobject]@{Schema='iw7.t7-resident-multi-surface-build/2';Header='prepared/t7_iw7_resident_model.hpp';
        PreviousSHA256=$transitions[2].PreviousSHA256;SHA256=$transitions[2].SHA256;E7ReadSHA256=$readSHA;
        E7CompileSHA256=$compileSHA;E7LinkSHA256=$linkSHA;E7TranslationUnits=413;E7Objects=413;DependencyJSON=$dependencies;
        SourceTransitions=$transitions;AdditionalHeaderInputs=[pscustomobject]@{Count=66;Bytes=87204;
            E7TranslationUnit='c:\native\src\zonetool\zonetool\iw7\assets\xsurface.cpp';E7ReadSHA256=$readSHA;
            E7CompileSHA256=$compileSHA;CompilerContextMatchesCLI=$true;PCHExcludedForPreparedYMinus='c:\e7\obj\community.pch';Inputs=$headers}}
    # JSON roundtrip ensures proof, Inputs and Bindings do not share pin objects.
    return ([pscustomobject]@{SourceCommit='fab935826c898806855376662a8a03317b3ad8f1';PreparedRoot='C:\plan\prepared';
        BuildProfile=[pscustomobject]@{Name='t7-catalog-message-publication';PublicationSchema='iw7.t7-message-publication-build/1'};
        ReuseCompile=[pscustomobject]@{RecompiledMain=$true;RecompiledZonetool=$true;StageRoots=@('C:\old\xpak');ResidentMultiSurfaceV2=$proof};
        Inputs=$inputs;Bindings=$bindings}|ConvertTo-Json -Depth 15|ConvertFrom-Json -Depth 15)
}
function Must-RefuseBinding($Fixture) {
    $refused=$false
    try{Assert-T7InputBindings $Fixture}catch{$refused=$true}
    if(!$refused){throw 'Unqualified extended binding set accepted.'}
    $script:checks++
}
Assert-T7InputBindings (New-BindingFixture);$checks++
foreach($mode in 'missing-marker','null-marker','old-profile','mixed','false-main','string-cli','schema','source',
    'proof-missing','proof-count','proof-bytes','context','journal','pch','input-count','binding-count','classification',
    'header-input','header-binding','header-missing','header-extra','header-duplicate','header-mutant-all','header-path-all',
    'duplicate-input','duplicate-binding','journal-binding','dep-json','transition','wired-binding','string-classification',
    'binary-mutant','binary-as-text','header-length') {
    $f=New-BindingFixture;$p=$f.ReuseCompile.ResidentMultiSurfaceV2;$h=$p.AdditionalHeaderInputs
    switch($mode) {
        missing-marker {$f.ReuseCompile.PSObject.Properties.Remove('ResidentMultiSurfaceV2')}
        null-marker {$f.ReuseCompile.ResidentMultiSurfaceV2=$null}
        old-profile {$f.BuildProfile.Name='t7-catalog-message'}
        mixed {$f.ReuseCompile|Add-Member NoteProperty ResidentSurfaceCountDiagnostic @{} }
        false-main {$f.ReuseCompile.RecompiledMain=$false}
        string-cli {$f.ReuseCompile.RecompiledZonetool='true'}
        schema {$p.Schema='iw7.t7-resident-multi-surface-build/1'}
        source {$f.SourceCommit=('0'*40)}
        proof-missing {$p.PSObject.Properties.Remove('AdditionalHeaderInputs')}
        proof-count {$h.Count=65}
        proof-bytes {$h.Bytes=87205}
        context {$h.CompilerContextMatchesCLI='true'}
        journal {$h.E7ReadSHA256=('0'*64)}
        pch {$h.PCHExcludedForPreparedYMinus='c:\e7\obj\other.pch'}
        input-count {$f.Inputs=@($f.Inputs[0..1144])}
        binding-count {$f.Bindings=@($f.Bindings[0..139])}
        classification {$f.Bindings[0].IsText=$false;$f.Bindings[140].IsText=$true}
        string-classification {$f.Bindings[0].IsText='true'}
        binary-mutant {$f.Bindings[140].SHA256=('0'*64)}
        binary-as-text {$f.Bindings[134].IsText=$false;$f.Bindings[140].IsText=$true}
        header-length {$h.Inputs[0].Bytes++;$f.Inputs[0].Bytes++;$f.Bindings[0].Bytes++}
        header-input {$f.Inputs[0].SHA256=('0'*64)}
        header-binding {$f.Bindings[0].SHA256=('0'*64)}
        header-missing {$h.Inputs=@($h.Inputs[0..64])}
        header-extra {$h.Inputs+=@($h.Inputs[0])}
        header-duplicate {$h.Inputs[1]=$h.Inputs[0]}
        header-mutant-all {$h.Inputs[0].SHA256=('0'*64);$f.Inputs[0].SHA256=('0'*64);$f.Bindings[0].SHA256=('0'*64)}
        header-path-all {$h.Inputs[0].Path='C:\native\other.hpp';$f.Inputs[0].Path=$h.Inputs[0].Path;$f.Bindings[0].Path=$h.Inputs[0].Path}
        duplicate-input {$f.Inputs[1145]=$f.Inputs[1144]}
        duplicate-binding {$f.Bindings[140]=$f.Bindings[139]}
        journal-binding {$f.Bindings[69].SHA256=('0'*64)}
        dep-json {$p.DependencyJSON[0].SHA256=('0'*64)}
        transition {$p.SourceTransitions[0].PreviousBytes++}
        wired-binding {$f.Bindings[72].SHA256=('0'*64)}
    }
    Must-RefuseBinding $f
}
foreach($count in 128,129) {
    $f=New-BindingFixture;$f.ReuseCompile.PSObject.Properties.Remove('ResidentMultiSurfaceV2');$f.Bindings=@($f.Bindings[0..($count-1)])
    if($count -eq 128){Assert-T7InputBindings $f;$checks++}else{Must-RefuseBinding $f}
}
# Verify the actual entry calls this gate before it opens bindings, queries
# binary metadata, loads providers or reaches the admission/native region.
$entry=$ast.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.TryStatementAst]}|Select-Object -First 1
$entryText=$entry.Extent.Text
$gate=$entryText.IndexOf('Assert-T7InputBindings $plan',[StringComparison]::Ordinal)
foreach($next in 'foreach($pin in $plan.Bindings)','Binary metadata changed.','. $plan.Core','if(!$Run)','Enter-IW7ResourceLease','Open-T7Pin $pin $context') {
    if($gate -lt 0 -or $entryText.IndexOf($next,[StringComparison]::Ordinal) -le $gate){throw 'Early binding gate order changed.'}
    $checks++
}
if($MultisurfaceFixturePlanPath) {
    $baseRaw=[IO.File]::ReadAllBytes($MultisurfaceFixturePlanPath)
    if($baseRaw.Length -ne 365638 -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($baseRaw)).ToLowerInvariant() -cne
        '23b93e754c725b81b438e12498fac8c93257aa43368889fecc22e3ff1fefa3dc'){throw 'Frozen B fixture differs.'}
    $base=[Text.Encoding]::UTF8.GetString($baseRaw)|ConvertFrom-Json -Depth 25
    Assert-T7InputBindings $base;$checks++
    if(Test-Path -LiteralPath $base.RunRoot){throw 'Fixture run root must remain absent.'}
    $runnerRaw=[IO.File]::ReadAllBytes($runner);$runnerSHA=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($runnerRaw)).ToLowerInvariant()
    $fixtureRoot=[IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetTempPath()) ('iw7-t7-binding-fixture-'+[guid]::NewGuid().ToString('N'))))
    [IO.Directory]::CreateDirectory($fixtureRoot)|Out-Null
    $fixturePath=Join-Path $fixtureRoot 'fixture.json'
    try {
        foreach($mode in 'nominal','missing-proof','header-classification','legacy129') {
            $f=[Text.Encoding]::UTF8.GetString($baseRaw)|ConvertFrom-Json -Depth 25
            $hostPin=@($f.Bindings|Where-Object Path -CEQ $runner)
            if($hostPin.Count -ne 1){throw 'Runner fixture binding absent.'}
            $hostPin[0].Bytes=$runnerRaw.Length;$hostPin[0].SHA256=$runnerSHA
            switch($mode) {
                missing-proof {$f.ReuseCompile.ResidentMultiSurfaceV2.PSObject.Properties.Remove('AdditionalHeaderInputs')}
                header-classification {
                    $name=$f.ReuseCompile.ResidentMultiSurfaceV2.AdditionalHeaderInputs.Inputs[0].Path
                    @($f.Bindings|Where-Object Path -CEQ $name)[0].IsText=$false
                    @($f.Bindings|Where-Object {!$_.IsText -and $_.Path -cne $name})[0].IsText=$true
                }
                legacy129 {
                    $remove=@($f.ReuseCompile.ResidentMultiSurfaceV2.AdditionalHeaderInputs.Inputs[0..11].Path)
                    $f.ReuseCompile.PSObject.Properties.Remove('ResidentMultiSurfaceV2')
                    $f.Bindings=@($f.Bindings|Where-Object {$remove -cnotcontains $_.Path})
                }
            }
            $raw=[Text.Encoding]::UTF8.GetBytes(($f|ConvertTo-Json -Depth 25))
            if($raw.Length -gt 512KB){throw 'Synthetic DEFAULT fixture exceeds bound.'}
            [IO.File]::WriteAllBytes($fixturePath,$raw)
            $sha=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()
            $saved=$ErrorActionPreference;$ErrorActionPreference='Continue'
            try{$output= & (Join-Path $PSHOME 'pwsh.exe') -NoLogo -NoProfile -File $runner -PlanPath $fixturePath -PlanSHA256 $sha 2>&1;$code=$LASTEXITCODE}
            finally{$ErrorActionPreference=$saved}
            if($mode -eq 'nominal') {
                if($code -ne 0){throw ('Nominal DEFAULT failed: '+($output -join "`n"))}
                $result=($output -join "`n")|ConvertFrom-Json
                if($result.ExpectedInputs -ne 1146 -or $result.NativeTypesLoaded -or $result.BinaryInputsHashed -or
                    $result.LeaseAcquired -or $result.RunRootCreated){throw 'DEFAULT crossed native boundary.'}
            } else {
                $expected=switch($mode) {
                    missing-proof {'AdditionalHeaderInputs'}
                    header-classification {'Opaque build input cannot be a text binding.'}
                    legacy129 {'Legacy input binding limit is 128.'}
                }
                if($code -eq 0 -or !($output -join "`n").Contains($expected)){
                    throw ('Actual DEFAULT did not fail at the expected early gate for '+$mode+': '+($output -join "`n"))
                }
            }
            if(Test-Path -LiteralPath $base.RunRoot){throw 'DEFAULT created a run root.'}
            $entryChecks++
        }
    } finally {
        # Only this freshly created, canonical single-file fixture is removed.
        if([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($fixturePath)) -cne $fixtureRoot){throw 'Fixture cleanup escaped its root.'}
        if([IO.File]::Exists($fixturePath)){[IO.File]::Delete($fixturePath)}
        [IO.Directory]::Delete($fixtureRoot,$false)
    }
    if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($MultisurfaceFixturePlanPath))).ToLowerInvariant() -cne
        '23b93e754c725b81b438e12498fac8c93257aa43368889fecc22e3ff1fefa3dc'){throw 'Frozen B changed during testing.'}
}
[ordered]@{Checks=$checks;ActualDefaultChecks=$entryChecks;Passed=$true;NativeInvoked=$false;OpaqueContentRead=$false}|ConvertTo-Json -Compress
