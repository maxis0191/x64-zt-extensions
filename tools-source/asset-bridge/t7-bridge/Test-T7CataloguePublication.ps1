# Original source/receipt fixtures only. No binary file, provider, admission or Run.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Test-T7CatalogueTrace.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Historical fixture syntax differs.'}
foreach($name in 'Check','Refuses','Copy-Value','New-Pin','New-Binding','New-Fixture','Read-H1SmallJson') {
    $function=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true))
    if($function.Count -ne 1){throw 'Expected fixture helper missing.'}
    . ([scriptblock]::Create($function[0].Extent.Text))
}
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-publication-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
$script:checks=0
$context=[pscustomobject]@{Guards=[Collections.Generic.List[object]]::new()}
function New-PublicationFixture {
    $f=New-Fixture;$p=$f.Build.BuildProfile
    $p.Name='t7-catalog-message-publication';$f.Plan.CandidateProfile=$p.Name
    foreach($pair in @(@('ContextSchema','iw7.t7-catalog-exit-context/1'),@('CallerSchema','iw7.t7-catalog-callers/1'),
        @('MessageSchema','iw7.t7-catalog-message/1'),@('PublicationSchema','iw7.t7-message-publication-build/1'))) {$p|Add-Member NoteProperty $pair[0] $pair[1]}
    $f.Build|Add-Member NoteProperty Compiler (Join-Path $root 'compiler/cl.exe')
    $paths=[ordered]@{PublicationWiring=(Join-Path $root 'prepare_message_publication.py');PublicationSource=(Join-Path $root 'native_message_publication.inc');
        PreparedCLI=(Join-Path $f.Build.PreparedRoot 'zonetool.cpp');MainResponse=(Join-Path $root 'main.obj.rsp');
        CLIResponse=(Join-Path $root 'zonetool11.obj.rsp');LinkResponse=$f.Rsp}
    foreach($name in $paths.Keys) {
        $pin=New-Pin $paths[$name];$p|Add-Member NoteProperty $name $pin
        if($name -cne 'LinkResponse'){$f.Build.Bindings+=@(New-Binding $pin);$f.Plan.Bindings+=@(New-Binding $pin)}
    }
    $f.Receipt.BuildProfile=Copy-Value $p
    $f.Build.ReuseCompile|Add-Member NoteProperty RecompiledZonetool $true
    $f.Build.ReuseCompile.StageRoots=@($f.Base.ReuseCompile.StageRoots[-1])
    $f.Plan|Add-Member NoteProperty BuildReceipt (Join-Path $f.Build.RunRoot 'receipt.json')
    $f.Plan|Add-Member NoteProperty ExpectedBuildReceiptSHA256 ('f'*64)
    $f.Plan.Bindings+=@(New-Binding (New-Pin $f.Plan.BuildReceipt ('f'*64)))
    $stages=@();$proofs=@()
    foreach($index in 0..2) {
        $name=@('main','zonetool11','link')[$index];$stageRoot=Join-Path $f.Build.RunRoot $name
        $kind=if($index -eq 2){'Link'}else{'Compile'}
        $names=@(if($index -eq 2){'zonetool-t7.exe','zonetool-t7.pdb','zonetool-t7.lib','zonetool-t7.exp'}else{($name+'.obj'),'compile.pdb','dependencies.json'})
        $image=if($index -eq 2){Join-Path (Split-Path $f.Build.Compiler -Parent) 'link.exe'}else{$f.Build.Compiler}
        $response=$p.(@('MainResponse','CLIResponse','LinkResponse')[$index]).Path
        $stages+=@([pscustomobject]@{Name=$name;Stage=$kind;Image=$image;Arguments=@('@'+$response);Artifacts=$names})
        $artifacts=@(foreach($leaf in $names){New-Pin (Join-Path $stageRoot $leaf)})
        $proofs+=@([pscustomobject]@{Name=$name;Stage=$kind;PlanSHA256=$f.Plan.ExpectedBuildPlanSHA256;ExitCode=0;TreeClosureConfirmed=$true;Artifacts=$artifacts})
        if($index -lt 2) {
            $source=$p.(@('PreparedMain','PreparedCLI')[$index]).Path
            $dep=$artifacts[-1];$script:json[$dep.Path]=[pscustomobject]@{Data=[pscustomobject]@{Source=$source}}
            if($index -eq 1){$f.Plan.Bindings+=@(New-Binding $dep)}
            $text='/c /Fo"'+$artifacts[0].Path+'" /Fd"'+$artifacts[1].Path+'" /sourceDependencies "'+$dep.Path+'" "'+$source+'"'
            [IO.File]::WriteAllText($response,$text+"`n")
        }
    }
    $f.Build.Stages=$stages;$f.Receipt.Stages=$proofs
    $objects=@(0..409|ForEach-Object {Join-Path $root ('retained/e7-'+$_+'.obj')})
    $objects+=@($proofs[0].Artifacts[0].Path,$proofs[1].Artifacts[0].Path,(Join-Path $f.Build.ReuseCompile.StageRoots[0] 'xpak.obj'))
    $flags='/OUT:"'+$f.Plan.CandidateSource+'" /PDB:"'+(Join-Path $f.Build.RunRoot 'link/zonetool-t7.pdb')+'" /IMPLIB:"'+(Join-Path $f.Build.RunRoot 'link/zonetool-t7.lib')+'" /PDBCompress'
    [IO.File]::WriteAllLines($f.Rsp,@($flags)+@($objects|ForEach-Object {'"'+$_+'"'}))
    return $f
}
try {
    $f=New-PublicationFixture
    Assert-T7CatalogueBuild $f.Plan $f.Receipt;$checks++
    Check ((Get-T7CatalogueCandidateProfile $f.Plan) -ceq 't7-catalog-message-publication') 'New profile was relabeled.'
    foreach($side in 'Build','Receipt') {
        foreach($field in 'Name','Option','TraceSchema','ContextSchema','CallerSchema','MessageSchema','PublicationSchema') {
            $f=New-PublicationFixture;$f.$side.BuildProfile.$field='unknown'
            Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Exact .* (profile|schema)'
        }
        foreach($field in 'PublicationSchema','PublicationWiring','PublicationSource','PreparedCLI','MainResponse','CLIResponse','LinkResponse') {
            $f=New-PublicationFixture;$f.$side.BuildProfile.PSObject.Properties.Remove($field)
            Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Exact catalogue fields'
        }
    }
    foreach($field in 'PublicationWiring','PublicationSource','PreparedCLI','MainResponse','CLIResponse','LinkResponse') {
        foreach($side in 'Build','Receipt') {
            $f=New-PublicationFixture;$f.$side.BuildProfile.$field.SHA256='0'*64
            Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'pin is not guarded|profile differs'
        }
        foreach($collection in 'Plan','Build') {
            $f=New-PublicationFixture;$path=$f.Build.BuildProfile.$field.Path
            $f.$collection.Bindings=@($f.$collection.Bindings|Where-Object Path -CNE $path)
            Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'pin is not guarded'
        }
        foreach($change in 'path','size') {
            $f=New-PublicationFixture;$pin=$f.Build.BuildProfile.$field;$old=$pin.Path
            if($change -ceq 'path'){$pin.Path=Join-Path $root 'redirected.txt'}
            else{$pin.Bytes=1+$(if($field -ceq 'PublicationSource'){16KB}elseif($field -ceq 'LinkResponse'){256KB}else{64KB})}
            $f.Receipt.BuildProfile.$field=Copy-Value $pin
            foreach($collection in 'Plan','Build') {
                $row=@($f.$collection.Bindings|Where-Object Path -CEQ $old)[0];$row.Path=$pin.Path;$row.Bytes=$pin.Bytes
            }
            Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'source/response path or bound'
        }
    }
    foreach($value in @($false,'true',1)) {
        $f=New-PublicationFixture;$f.Build.ReuseCompile.RecompiledZonetool=$value
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'fresh CLI'
    }
    $f=New-PublicationFixture;$f.Build.ReuseCompile.PSObject.Properties.Remove('RecompiledZonetool')
    Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'fresh CLI'
    $f=New-PublicationFixture;$f.Build.ReuseCompile.StageRoots=@($f.Base.ReuseCompile.StageRoots[1..2])
    Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'only the qualified xpak'
    $f=New-PublicationFixture;$f.Plan.BuildReceipt=$f.Build.BuildProfile.BaseBuildReceipt.Path
    Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'own build receipt'
    $f=New-PublicationFixture;$f.Plan.ExpectedBuildReceiptSHA256='e'*64
    Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'receipt pin differs'
    foreach($side in 'Build','Receipt') {
        $f=New-PublicationFixture;$f.$side.Stages=@($f.$side.Stages[0],$f.$side.Stages[2])
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'two actual Compile'
        $f=New-PublicationFixture;$f.$side.Stages=@($f.$side.Stages[1],$f.$side.Stages[0],$f.$side.Stages[2])
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'two actual Compile'
    }
    foreach($index in 0..2) {
        foreach($field in 'PlanSHA256','ExitCode','TreeClosureConfirmed') {
            $f=New-PublicationFixture;$f.Receipt.Stages[$index].$field=if($field -ceq 'ExitCode'){1}elseif($field -ceq 'TreeClosureConfirmed'){$false}else{'e'*64}
            Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'not successful and closed'
        }
        $f=New-PublicationFixture;$f.Build.Stages[$index].Image=Join-Path $root 'other.exe'
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'compiler/response command'
        $f=New-PublicationFixture;$f.Build.Stages[$index].Arguments+=@('/extra')
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'compiler/response command'
        $f=New-PublicationFixture;$f.Receipt.Stages[$index].Artifacts=@($f.Receipt.Stages[$index].Artifacts[0])
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'artifact guards'
        $f=New-PublicationFixture;$f.Receipt.Stages[$index].Artifacts[0].Path=Join-Path $root 'retained/old.obj'
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'artifact metadata'
    }
    foreach($index in 0..1) {
        $f=New-PublicationFixture;$dep=$f.Receipt.Stages[$index].Artifacts[-1].Path
        $script:json[$dep].Data.Source=Join-Path $root 'retained/old.cpp'
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'different TU'
        $f=New-PublicationFixture;$dep=$f.Receipt.Stages[$index].Artifacts[-1].Path
        $f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $dep)
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'pin is not guarded'
        $f=New-PublicationFixture;$rsp=$f.Build.BuildProfile.(@('MainResponse','CLIResponse')[$index]).Path
        [IO.File]::WriteAllText($rsp,'@nested.rsp')
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'direct compile response'
        $f=New-PublicationFixture;$rsp=$f.Build.BuildProfile.(@('MainResponse','CLIResponse')[$index]).Path
        [IO.File]::WriteAllText($rsp,[IO.File]::ReadAllText($rsp).Replace('/Fo"','/Fo"old-'))
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'fresh stage'
    }
    foreach($name in 'main','zonetool11','xpak') {
        $f=New-PublicationFixture;$lines=[IO.File]::ReadAllLines($f.Rsp)
        $index=if($name -ceq 'main'){411}elseif($name -ceq 'zonetool11'){412}else{413}
        $lines[$index]='"'+(Join-Path $root ('stale/'+$name+'.obj'))+'"';[IO.File]::WriteAllLines($f.Rsp,$lines)
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'both fresh objects'
    }
    foreach($change in 'missing','duplicate','nested','flags') {
        $f=New-PublicationFixture;$lines=[IO.File]::ReadAllLines($f.Rsp)
        switch($change){missing{$lines=$lines[0..412]} duplicate{$lines[410]=$lines[411]} nested{$lines[1]='@nested.rsp'} flags{$lines[0]+=' "old.obj"'}}
        [IO.File]::WriteAllLines($f.Rsp,$lines)
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'direct link|indirect or duplicated'
    }
    foreach($index in 0..1) {
        foreach($option in '/FoC:\old.obj','-fo:C:\old.obj','/Fo C:\old.obj','/FdC:\old.pdb','/sourceDependencies:C:\old.json') {
            $f=New-PublicationFixture;$rsp=$f.Build.BuildProfile.(@('MainResponse','CLIResponse')[$index]).Path
            [IO.File]::WriteAllText($rsp,([IO.File]::ReadAllText($rsp).TrimEnd()+" $option`n"))
            Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Duplicate publication output'
        }
    }
    foreach($option in '/OUT:C:\old.exe','-out C:\old.exe','/PDB:C:\old.pdb','/IMPLIB:C:\old.lib') {
        $f=New-PublicationFixture;$lines=[IO.File]::ReadAllLines($f.Rsp);$lines[0]+=' '+$option;[IO.File]::WriteAllLines($f.Rsp,$lines)
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Duplicate publication output'
    }
    foreach($option in 'OUT','PDB','IMPLIB') {
        $f=New-PublicationFixture;$lines=[IO.File]::ReadAllLines($f.Rsp)
        $lines[0]=$lines[0] -replace ('/'+$option+':"[^"]+"'),('/'+$option+':C:\stale.bin');[IO.File]::WriteAllLines($f.Rsp,$lines)
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'exact fresh stage'
    }
    foreach($text in @('/Fo"unclosed','/Fo""','/Fo"escaped\"quote"',"/Foabc`n/Fddef",'@nested.rsp')) {
        Refuses {Split-T7CatalogueResponseArguments $text} 'response syntax|response quote'
    }
    # Historical profile must still accept its exact original fixture and refuse new fields/markers.
    $f=New-Fixture;Assert-T7CatalogueBuild $f.Plan $f.Receipt;$checks++
    $f.Build.ReuseCompile|Add-Member NoteProperty RecompiledZonetool $false
    Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'CLI rebuild marker'
    $f=New-PublicationFixture;$f.Plan.CandidateProfile='t7-catalog-message'
    Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'Exact catalogue fields'
    Assert-T7CatalogueTraceSize 't7-catalog-message-publication' 8192;$checks++
    Refuses {Assert-T7CatalogueTraceSize 't7-catalog-message-publication' 8193} 'cap exceeded'
    $tracePlan=[pscustomobject]@{CandidateProfile='t7-catalog-message-publication';StageRoot=$root}
    $state=[ordered]@{};Read-T7CatalogueTrace $tracePlan $state $context
    Check ($state.MessageOutcome -ceq 'Absent') 'Missing publication message became evidence.'
    $prefix='[T7_CATALOG_MSG] schema=iw7.t7-catalog-message/1 kind='
    $text="[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase=enabled stdout_unbuffered=1 stderr_unbuffered=1 tid=42`n"+
        "[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase=before_post_unpack code=0 tid=42 return_address=0000000000000000`n"+
        $prefix+"install tid=42 status=installed error=0`n"+$prefix+'buffer tid=43 status=ok requested=384 read='
    [IO.File]::WriteAllText((Join-Path $root 'stderr.log'),$text)
    $state=[ordered]@{};Read-T7CatalogueTrace $tracePlan $state $context
    Check ($state.MessageOutcome -ceq 'Partial' -and $state.Message.IncompleteTrailingLine) 'Partial message was repaired or accepted.'
    & {
        # Existing synthetic metadata provider; no retail input or operational plan.
        foreach($row in @(@('Test-T7CatalogueBootstrap.ps1',@('Get-Item','New-Fixture')),
            @('Test-T7CatalogueBootstraps.ps1',@('New-Qualified')))) {
            $fixtureAst=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $row[0]),[ref]$tokens,[ref]$errors)
            foreach($name in $row[1]) {
                $fn=$fixtureAst.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
                . ([scriptblock]::Create($fn.Extent.Text))
            }
        }
        foreach($policy in 'QualifiedCollectionV1','QualifiedCollectionV2','QualifiedCollectionV3','SharedV3') {
            $shared=$policy -ceq 'SharedV3';$count=if($policy -like '*V3'){20}else{3}
            $f=New-Qualified $count $(if($shared){'QualifiedCollectionV3'}else{$policy})
            if($shared) {
                $group=[pscustomobject]@{Script=(New-Pin (Join-Path $root 'Qualify-T7BootstrapGroup.ps1'));
                    Plan=(New-Pin (Join-Path $root 'group-plan.json'));Receipt=(New-Pin (Join-Path $root 'group-receipt.json'))}
                foreach($index in 8..19) {
                    $old=$f.Plan.Bootstraps[$index].QualificationScript.Path
                    $f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $old)
                    $f.Plan.Bootstraps[$index].QualificationScript=Copy-Value $group.Script
                }
                $f.Plan|Add-Member NoteProperty SharedQualification $group
                foreach($name in 'Script','Plan','Receipt'){
                    $f.Plan.Bindings+=@(New-Binding $group.$name)
                    $script:provider[$group.$name.Path]=[pscustomobject]@{PSIsContainer=$false;Length=100;Attributes='Archive'}
                }
            }
            Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$script:checks++
            $oldCount=$f.Plan.Bindings.Count;$oldLimit=$f.Plan.OutputLimitBytes
            $f.Plan.CandidateProfile='t7-catalog-message-publication'
            Refuses {Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner'} 'binding count'
            foreach($index in 0..5) {
                $pin=New-Pin (Join-Path $root ('publication-pin-'+$index+'.json'))
                $f.Plan.Bindings+=@(New-Binding $pin)
                $script:provider[$pin.Path]=[pscustomobject]@{PSIsContainer=$false;Length=100;Attributes='Archive'}
            }
            Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$script:checks++
            Check ($f.Plan.Bindings.Count -eq $oldCount+6 -and $f.Plan.OutputLimitBytes -eq $oldLimit) 'Publication changed a payload budget.'
            if($shared){Check ($oldCount -eq 73 -and $f.Plan.Bindings.Count -eq 79) 'Shared20 publication count differs.'}
            $f.Plan.CandidateProfile='t7-catalog-message'
            Refuses {Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner'} 'binding count'
        }
    }
    [ordered]@{Status='Passed';Checks=$checks;NativeLoaded=$false;BinaryFilesReadOrHashed=$false;OperationalPlanCreated=$false;LeaseAcquired=$false}|ConvertTo-Json
} finally {
    foreach($guard in $context.Guards){$guard.Dispose()}
    $resolved=[IO.Path]::GetFullPath($root);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-publication-tests-[0-9a-f]{32}$'){throw 'Refuse cleanup outside exact synthetic root.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
