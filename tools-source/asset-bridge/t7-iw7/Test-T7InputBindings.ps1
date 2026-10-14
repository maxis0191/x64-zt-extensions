# Exercise the actual early validator. Optional frozen-B DEFAULT rejection
# tests use temporary JSON text only, never -Run or a changed prepared source.
[CmdletBinding()]
param([string]$MultisurfaceFixturePlanPath)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$runner=Join-Path $PSScriptRoot 'Run-T7Build.ps1';$errors=$null;$tokens=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($runner,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner syntax errors.'}
$definition=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Assert-T7InputBindings'},$true)
if(!$definition){throw 'Actual binding validator missing.'}
. ([scriptblock]::Create($definition.Extent.Text))
$os=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Assert-T7OSResourceContext'},$true)
if(!$os){throw 'Actual OS context guard missing.'}
. ([scriptblock]::Create($os.Extent.Text))
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
        @('zonetool.cpp',35974,'106ccdb4aec584184132c309c117f778d504ca9e64e8a821d23bfecc83bc8635',62674,'c080e69319ccff31fd8a25747210baeddc95269d6b416d18321ea272935ffff8',62728,'d9e25c2cdd8a422fdf5312ad3dc4596fb60482ee165e77f59bff1a30d436fe7f'),
        @('t7_iw7_resident_model.hpp',13444,'6d2da3d4f7c3d0686909dc488f3d176ee2dd250e8d43d9a3cd9bcfa701482777',21290,'857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4',21290,'857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4'))) {
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
        @('resident_image_copy.hpp',6366,'96291c23f132e09285d4ea3171c9107ac525d8628403014eae85a895f99c324e'),
        @('selected_material_observation.hpp',12765,'a935803571f04b3a2cad7346824bf3194f5d44aeada15b224a3faa75ea292d7f'),
        @('selected_material_observation_fixture.cpp',8146,'f011131feeb5495b3bfb0a1e86ad34aad20fc7869ec775c861290df6e3e1a05b'))) {
        $bindings+=@([pscustomobject]@{Path=('C:\fixture\'+$row[0]);Bytes=$row[1];SHA256=$row[2];IsText=$true})
    }
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
    return ([pscustomobject]@{SourceCommit='fab935826c898806855376662a8a03317b3ad8f1';PreparedRoot='C:\plan\prepared';Runner='C:\fixture\Run-T7Build.ps1';
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
function New-StreamedBindingFixture {
    $fixture=New-BindingFixture
    foreach($row in @(
        @('selected_material_observation.hpp',16489,'0ea84735fca2502033cc48a4eede6a19e1bd1283ba1975829f763c16e5ef343a'),
        @('selected_material_observation_fixture.cpp',13721,'cb27d4df66f3a186de3e0f5faedf7bf713610a2da0fc599861e5a4838ea2dfed'))) {
        $pin=@($fixture.Bindings|Where-Object Path -CEQ ('C:\fixture\'+$row[0]))[0]
        $pin.Bytes=$row[1];$pin.SHA256=$row[2]
    }
    $fixture.ReuseCompile|Add-Member NoteProperty SelectedStreamedStaticV1 ([pscustomobject]@{
        Schema='iw7.t7-selected-streamed-static-build/1';GeometryProfile='t7-iw7-selected-streamed-static-v1'})
    foreach($row in @(
        @('prepared/main.cpp',13052,'ca8875cf36bdf9a8c8e6142969eab95194d214d09c90064e202d68ff9302fcb3',43146,'e599c3e6945e2192443b8a3a3e274d5d36b133b41beb38d6d9234c669defca01'),
        @('prepared/zonetool.cpp',107731,'dc8211db172c1d6f470b518aa0884ff1be9e1a15faf6a739155a1cc60ca43ac5',107785,'c480fbd39525df09bd5677026678743c73fa66eb3ca0752e78729eee2f4dcc50'))) {
        $transition=@($fixture.ReuseCompile.ResidentMultiSurfaceV2.SourceTransitions|Where-Object Path -CEQ $row[0])[0]
        $transition.Bytes=$row[1];$transition.SHA256=$row[2];$transition.WiredBytes=$row[3];$transition.WiredSHA256=$row[4]
        $path='C:\plan\'+$row[0].Replace('/','\')
        $binding=@($fixture.Bindings|Where-Object Path -CEQ $path)[0]
        $binding.Bytes=$row[3];$binding.SHA256=$row[4]
    }
    foreach($row in @(
        @('streamed_mesh_payload.hpp',18512,'53265601cec86ba6e0b731e54d9c706f41d390756f4e4566ace70bd5fbd25adf'),
        @('t7_iw7_streamed_model.hpp',11289,'5eeaa89565bcfb2c5a1d899f78a47787584a1472caae9e84f04af1b8c886e5a0'),
        @('native_streamed_export.inc',9823,'60916d49cb4490f0cc508b699d9adaa02a780229fa5e69e3c66297f50c3b0123'),
        @('streamed_contract.py',7996,'b7d68593b93975832cfa6362c2f782187772c2255cd59c78ab5aae66d759518f'),
        @('test_streamed_contract.py',8796,'fe25379d80cc1ec328836a0e75652046c01b9ddadba3dba73c8e7a550bed1d16'))) {
        $fixture.Bindings+=@([pscustomobject]@{Path=('C:\fixture\'+$row[0]);Bytes=$row[1];SHA256=$row[2];IsText=$true})
    }
    $fixture
}
Assert-T7InputBindings (New-StreamedBindingFixture);$checks++
foreach($mode in 'missing-marker','null-marker','schema','profile','extra-marker','missing-common-proof','old-transition') {
    $f=New-StreamedBindingFixture
    switch($mode) {
        missing-marker {$f.ReuseCompile.PSObject.Properties.Remove('SelectedStreamedStaticV1')}
        null-marker {$f.ReuseCompile.SelectedStreamedStaticV1=$null}
        schema {$f.ReuseCompile.SelectedStreamedStaticV1.Schema='iw7.t7-selected-streamed-static-build/2'}
        profile {$f.ReuseCompile.SelectedStreamedStaticV1.GeometryProfile='t7-iw7-resident-static-v2'}
        extra-marker {$f.ReuseCompile.SelectedStreamedStaticV1|Add-Member NoteProperty Guess $true}
        missing-common-proof {$f.ReuseCompile.PSObject.Properties.Remove('ResidentMultiSurfaceV2')}
        old-transition {$f.ReuseCompile.ResidentMultiSurfaceV2.SourceTransitions[0].WiredSHA256=('0'*64)}
    }
    Must-RefuseBinding $f
}
foreach($name in 'streamed_mesh_payload.hpp','t7_iw7_streamed_model.hpp','native_streamed_export.inc','streamed_contract.py','test_streamed_contract.py') {
    foreach($mode in 'missing','sha','size','path','classification') {
        $f=New-StreamedBindingFixture;$path='C:\fixture\'+$name
        $pin=@($f.Bindings|Where-Object Path -CEQ $path)[0]
        switch($mode) {
            missing {$f.Bindings=@($f.Bindings|Where-Object Path -CNE $path)}
            sha {$pin.SHA256=('0'*64)}
            size {$pin.Bytes++}
            path {$pin.Path='C:\unowned\'+$name}
            classification {$pin.IsText=$false}
        }
        Must-RefuseBinding $f
    }
}
Assert-T7InputBindings (New-BindingFixture);$checks++
foreach($mode in 'missing-marker','null-marker','old-profile','mixed','false-main','string-cli','schema','source',
    'proof-missing','proof-count','proof-bytes','context','journal','pch','input-count','binding-count','classification',
    'header-input','header-binding','header-missing','header-extra','header-duplicate','header-mutant-all','header-path-all',
    'duplicate-input','duplicate-binding','journal-binding','dep-json','transition','wired-binding','string-classification',
    'binary-mutant','binary-as-text','header-length','old-surface80-all','old-surface80-transition',
    'observer-missing','observer-hash','observer-bytes','observer-path','observer-classification') {
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
        {$_ -in 'old-surface80-all','old-surface80-transition'} {
            $oldSHA='97a417b82ab7edf002f73039d1280b5e2a34370594e151ff07698db3a81f65ed'
            $row=@($p.SourceTransitions|Where-Object Path -CEQ 'prepared/t7_iw7_resident_model.hpp')[0]
            $row.SHA256=$oldSHA;$row.WiredSHA256=$oldSHA
            @($f.Bindings|Where-Object Path -CEQ 'C:\plan\prepared\t7_iw7_resident_model.hpp')[0].SHA256=$oldSHA
            if($mode -ceq 'old-surface80-all'){$p.SHA256=$oldSHA}
        }
        wired-binding {$f.Bindings[72].SHA256=('0'*64)}
        observer-missing {$f.Bindings[135].Path='C:\fixture\other.hpp'}
        observer-hash {$f.Bindings[135].SHA256=('0'*64)}
        observer-bytes {$f.Bindings[136].Bytes++}
        observer-path {$f.Bindings[136].Path='C:\other\selected_material_observation.hpp'}
        observer-classification {$f.Bindings[137].IsText=$false}
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
    # B still contains the historical surface80 adapter. It is never promoted
    # to a positive fixture by rewriting its sealed source/proof in place.
    Must-RefuseBinding $base
    if(Test-Path -LiteralPath $base.RunRoot){throw 'Fixture run root must remain absent.'}
    $runnerRaw=[IO.File]::ReadAllBytes($runner);$runnerSHA=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($runnerRaw)).ToLowerInvariant()
    $fixtureRoot=[IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetTempPath()) ('iw7-t7-binding-fixture-'+[guid]::NewGuid().ToString('N'))))
    [IO.Directory]::CreateDirectory($fixtureRoot)|Out-Null
    $fixturePath=Join-Path $fixtureRoot 'fixture.json'
    try {
        foreach($mode in 'old-surface80','missing-proof','header-classification','legacy129') {
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
            $expected=switch($mode) {
                old-surface80 {'Complete pinned multisurface dependency proof required.'}
                missing-proof {'AdditionalHeaderInputs'}
                header-classification {'Opaque build input cannot be a text binding.'}
                legacy129 {'Legacy input binding limit is 128.'}
            }
            if($code -eq 0 -or !($output -join "`n").Contains($expected)){
                throw ('Actual DEFAULT did not fail at the expected early gate for '+$mode+': '+($output -join "`n"))
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
function New-ZombiesBindingFixture {
    $fixture=New-StreamedBindingFixture
    $fixture.BuildProfile.Name='t7-zombies-catalogue-observation-c'
    $fixture.BuildProfile|Add-Member NoteProperty ObservationSchema 'iw7.t7-zm-observation/1'
    $fixture.ReuseCompile|Add-Member NoteProperty ZombiesObservationC ([pscustomobject]@{
        Schema='iw7.t7-zm-observation-build/1';SourceProfile='t7-zombies-catalogue-observation-c';
        BaseCLIBytes=107785;BaseCLISHA256='c480fbd39525df09bd5677026678743c73fa66eb3ca0752e78729eee2f4dcc50';
        CLIBytes=118485;CLISHA256='917c2f9025185d23a8b2b683157144c2da62fe747f17f11e0f8c1abcf66be987'})
    foreach($row in @(
        @('ObserverSource','native_catalog_zombies_observation.inc',9668,'50361fbd5deb38b7410e31b995b1dcd7cdf6e43f04dc81835ed213f74155d181'),
        @('ObserverAdapter','prepare_catalog_zombies_observation.py',7613,'1bf133356025893ff59c4d3de7e3614ac60f00a098f16b4b707e0eaa012da445'))) {
        $pin=[pscustomobject]@{Path=('C:\fixture\'+$row[1]);Bytes=$row[2];SHA256=$row[3]}
        $fixture.BuildProfile|Add-Member NoteProperty $row[0] $pin
        $fixture.Bindings+=@([pscustomobject]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true})
    }
    $cli=@($fixture.Bindings|Where-Object Path -CEQ 'C:\plan\prepared\zonetool.cpp')[0]
    $cli.Bytes=118485;$cli.SHA256='917c2f9025185d23a8b2b683157144c2da62fe747f17f11e0f8c1abcf66be987'
    return $fixture
}
Assert-T7InputBindings (New-ZombiesBindingFixture);$checks++
foreach($change in @(
    {$fixture.BuildProfile.Name='t7-catalog-message-publication'},
    {$fixture.BuildProfile.ObservationSchema='wrong'},
    {$fixture.ReuseCompile.PSObject.Properties.Remove('ZombiesObservationC')},
    {$fixture.ReuseCompile.PSObject.Properties.Remove('SelectedStreamedStaticV1')},
    {$fixture.ReuseCompile.ZombiesObservationC.Schema='wrong'},
    {$fixture.ReuseCompile.ZombiesObservationC.SourceProfile='t7-catalog-message-publication'},
    {$fixture.ReuseCompile.ZombiesObservationC.BaseCLIBytes=107784},
    {$fixture.ReuseCompile.ZombiesObservationC.BaseCLISHA256=('a'*64)},
    {$fixture.ReuseCompile.ZombiesObservationC.CLIBytes=118484},
    {$fixture.ReuseCompile.ZombiesObservationC.CLISHA256=('a'*64)},
    {$fixture.ReuseCompile.ZombiesObservationC|Add-Member NoteProperty Unbounded $true},
    {$fixture.BuildProfile.ObserverSource.Bytes=9667},
    {$fixture.BuildProfile.ObserverSource.SHA256=('a'*64)},
    {$fixture.BuildProfile.ObserverAdapter.Path='C:\other.py'},
    {$fixture.BuildProfile.ObserverAdapter|Add-Member NoteProperty Optional $true},
    {@($fixture.Bindings|Where-Object Path -CEQ 'C:\fixture\native_catalog_zombies_observation.inc')[0].IsText=$false},
    {@($fixture.Bindings|Where-Object Path -CEQ 'C:\plan\prepared\zonetool.cpp')[0].Bytes=107785},
    {$fixture.ReuseCompile.ResidentMultiSurfaceV2.SourceTransitions[1].WiredSHA256=('a'*64)},
    {$fixture.Bindings+=$fixture.Bindings[-1]},
    {$fixture.Bindings=$fixture.Bindings[0..149]},
    {$fixture.ReuseCompile.RecompiledZonetool=$false}
)) {
    $fixture=New-ZombiesBindingFixture;. $change;Must-RefuseBinding $fixture
}

function New-RenderOnlyBindingFixture {
    $fixture=New-StreamedBindingFixture
    $fixture.ReuseCompile.PSObject.Properties.Remove('SelectedStreamedStaticV1')
    $fixture.ReuseCompile|Add-Member NoteProperty SelectedStreamedRenderOnlyV2 ([pscustomobject]@{
        Schema='iw7.t7-selected-streamed-render-only-build/2';GeometryProfile='t7-iw7-selected-streamed-render-only-v2';
        CollisionPolicy='omit-source-rigid-collision-trees'})
    foreach($row in @(
        @('prepared/main.cpp',13160,'55081db20863f291f4f1fea8c1c995995e5e548b56acf043201fbb2e361f3934',43254,'5aef1fad310071f5e680a9f5b4dbd6a303af6ea8605fccb5dc5705cb386b761d'),
        @('prepared/zonetool.cpp',112323,'774c5e0a2716c27c381a1f353d02ba504488affe3350faf84ce1d802a2d98be8',112377,'c63d9552464da674d3b03c35f7edc16385fb9370b113a3925fd7bc4835fb005a'))) {
        $transition=@($fixture.ReuseCompile.ResidentMultiSurfaceV2.SourceTransitions|Where-Object Path -CEQ $row[0])[0]
        $transition.Bytes=$row[1];$transition.SHA256=$row[2];$transition.WiredBytes=$row[3];$transition.WiredSHA256=$row[4]
        $pin=@($fixture.Bindings|Where-Object Path -CEQ ('C:\plan\'+$row[0].Replace('/','\')))[0]
        $pin.Bytes=$row[3];$pin.SHA256=$row[4]
    }
    foreach($row in @(
        @('streamed_mesh_payload.hpp',18512,'53265601cec86ba6e0b731e54d9c706f41d390756f4e4566ace70bd5fbd25adf'),
        @('t7_iw7_streamed_model.hpp',11951,'04007fa53fc6a3cc0307a589e7f28cebfa1c2a37c6071e0a2cb9ded412782453'),
        @('native_streamed_export.inc',10919,'f4fdc95d6a29bbe36c9140beff11567ab3ecc4d87f3c28e1e4e7fa4a25ec92c7'),
        @('streamed_contract.py',10366,'cc584cf6d2ff82be77b9ef0e926cda75ac7768f85e906d6eef22c2f8c2572df4'),
        @('test_streamed_contract.py',13768,'86392ae7934213692ae4c9453579d4b006d2665d6a80aaf52e39a41edc18bb3c'))) {
        $pin=@($fixture.Bindings|Where-Object Path -CEQ ('C:\fixture\'+$row[0]))[0]
        $pin.Bytes=$row[1];$pin.SHA256=$row[2]
    }
    foreach($row in @(
        @('selected_material_observation.hpp',18583,'a8848a92b8d7918fbe91ec4b68df123b1eaab89edde9d8a7c24d5a0cfb576ffc'),
        @('selected_material_observation_fixture.cpp',20260,'b3de68880b6f8c717c2e70ed44497ae2f95f37db7e73bbf34ef014d8e5b6fc6f'))) {
        $pin=@($fixture.Bindings|Where-Object Path -CEQ ('C:\fixture\'+$row[0]))[0]
        $pin.Bytes=$row[1];$pin.SHA256=$row[2]
    }
    return $fixture
}
Assert-T7InputBindings (New-RenderOnlyBindingFixture);$checks++
foreach($change in @(
    {$fixture.ReuseCompile.SelectedStreamedRenderOnlyV2.PSObject.Properties.Remove('CollisionPolicy')},
    {$fixture.ReuseCompile.SelectedStreamedRenderOnlyV2.CollisionPolicy='convert'},
    {$fixture.ReuseCompile.SelectedStreamedRenderOnlyV2.Schema='iw7.t7-selected-streamed-static-build/1'},
    {$fixture.ReuseCompile.SelectedStreamedRenderOnlyV2.GeometryProfile='t7-iw7-selected-streamed-static-v1'},
    {$fixture.ReuseCompile|Add-Member NoteProperty SelectedStreamedStaticV1 ([pscustomobject]@{})},
    {$fixture.ReuseCompile|Add-Member NoteProperty ZombiesObservationC ([pscustomobject]@{})},
    {$fixture.ReuseCompile.ResidentMultiSurfaceV2.SourceTransitions[0].WiredBytes=43146},
    {@($fixture.Bindings|Where-Object Path -CEQ 'C:\fixture\t7_iw7_streamed_model.hpp')[0].SHA256=('0'*64)},
    {$fixture.ReuseCompile.PSObject.Properties.Remove('ResidentMultiSurfaceV2')}
)) {
    $fixture=New-RenderOnlyBindingFixture;. $change;Must-RefuseBinding $fixture
}

function New-AddBindingFixture {
    $fixture=New-RenderOnlyBindingFixture
    $fixture.BuildProfile.Name='t7-zombies-catalogue-observation-c2'
    $fixture.BuildProfile|Add-Member NoteProperty ObservationSchema 'iw7.t7-zm-add-observation/1'
    $fixture.ReuseCompile|Add-Member NoteProperty ZombiesAddObservationC2 ([pscustomobject]@{
        Schema='iw7.t7-zm-add-observation-build/1';SourceProfile='t7-zombies-catalogue-observation-c2';
        BaseCLIBytes=112377;BaseCLISHA256='c63d9552464da674d3b03c35f7edc16385fb9370b113a3925fd7bc4835fb005a';
        CLIBytes=119139;CLISHA256='19af683d0c609d43cefc7c93dd3d7fa6f7ae1a6f5b90d2945d37b1830bda1111'})
    $pin=@($fixture.Bindings|Where-Object Path -CEQ 'C:\plan\prepared\zonetool.cpp')[0]
    $pin.Bytes=119139;$pin.SHA256='19af683d0c609d43cefc7c93dd3d7fa6f7ae1a6f5b90d2945d37b1830bda1111'
    $test=@($fixture.Bindings|Where-Object Path -CEQ 'C:\fixture\test_streamed_contract.py')[0]
    $test.Bytes=17443;$test.SHA256='9146f69c84c4178341010f7b6d7c10c4226ce4c7ec524b5fcdf4da742a95ac30'
    foreach($row in @(
        @('ObserverSource','native_catalog_add_observation.inc',6397,'fe37357ad1f3162f24ae79af51f325763b81e05851eb263f8681b5558835f11d'),
        @('ObserverAdapter','prepare_catalog_add_observation.py',6156,'cf6551b918e21d0046136ea3e328494960b70a62334bc3f2727e0a52fee5ec6f'))) {
        $pin=[pscustomobject]@{Path=('C:\fixture\'+$row[1]);Bytes=$row[2];SHA256=$row[3]}
        $fixture.BuildProfile|Add-Member NoteProperty $row[0] $pin
        $fixture.Bindings+=@([pscustomobject]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true})
    }
    return $fixture
}
Assert-T7InputBindings (New-AddBindingFixture);$checks++
foreach($change in @(
    {$fixture.BuildProfile.Name='t7-zombies-catalogue-observation-c'},
    {$fixture.ReuseCompile|Add-Member NoteProperty ZombiesObservationC ([pscustomobject]@{})},
    {$fixture.ReuseCompile.PSObject.Properties.Remove('ZombiesAddObservationC2')},
    {$fixture.ReuseCompile.PSObject.Properties.Remove('SelectedStreamedRenderOnlyV2')},
    {$fixture.ReuseCompile|Add-Member NoteProperty SelectedStreamedStaticV1 ([pscustomobject]@{})},
    {$fixture.ReuseCompile.ZombiesAddObservationC2.BaseCLIBytes=107785},
    {$fixture.ReuseCompile.ZombiesAddObservationC2.BaseCLISHA256='c480fbd39525df09bd5677026678743c73fa66eb3ca0752e78729eee2f4dcc50'},
    {$fixture.ReuseCompile.ZombiesAddObservationC2.CLIBytes=119138},
    {$fixture.ReuseCompile.ZombiesAddObservationC2.CLISHA256=('0'*64)},
    {$fixture.ReuseCompile.ZombiesAddObservationC2|Add-Member NoteProperty Permissive $true},
    {$fixture.BuildProfile.ObservationSchema='iw7.t7-zm-observation/1'},
    {$fixture.BuildProfile.ObserverSource.SHA256=('0'*64)},
    {@($fixture.Bindings|Where-Object Path -CEQ 'C:\fixture\prepare_catalog_add_observation.py')[0].IsText=$false},
    {@($fixture.Bindings|Where-Object Path -CEQ 'C:\plan\prepared\zonetool.cpp')[0].Bytes=112377},
    {$fixture.Bindings=$fixture.Bindings[0..149]},
    {@($fixture.Bindings|Where-Object Path -CEQ 'C:\fixture\test_streamed_contract.py')[0].SHA256='86392ae7934213692ae4c9453579d4b006d2665d6a80aaf52e39a41edc18bb3c'}
)) {
    $fixture=New-AddBindingFixture;. $change;Must-RefuseBinding $fixture
}

[ordered]@{Checks=$checks;ActualDefaultChecks=$entryChecks;Passed=$true;NativeInvoked=$false;OpaqueContentRead=$false}|ConvertTo-Json -Compress
