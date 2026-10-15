param([string]$Entry=(Join-Path $PSScriptRoot '../../ops/model-lab/ModelFF.PathPreflight.ps1'))
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. $Entry
$testNames=[Collections.Generic.List[string]]::new()
function Confirm-SourceCase([string]$Name,[scriptblock]$Body){& $Body;$testNames.Add($Name)}
function Confirm-SourceRefusal([string]$Name,[scriptblock]$Body){
    $refused=$false;try{$null=& $Body}catch{$refused=$true}
    if(!$refused){throw ('Source refusal expected: '+$Name)};$testNames.Add($Name)
}
$fixtureBase=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
$fixtureRoot=Join-Path $fixtureBase ('ModelFFPathSource-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($fixtureRoot)
$run=Join-Path $fixtureRoot 'run';$source=Join-Path $run 'source';$caseNumber=0
function Write-SourceJson([string]$Text){
    $script:caseNumber++;$path=Join-Path $fixtureRoot ('case'+$script:caseNumber+'.json')
    [IO.File]::WriteAllText($path,$Text,[Text.UTF8Encoding]::new($false))
    [pscustomobject]@{Path=$path;SHA256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Read-SourceDeclaration($Value){
    $pin=Write-SourceJson ($Value|ConvertTo-Json -Depth 8 -Compress)
    Read-ModelFFOutputNamespacePlan $pin.Path $pin.SHA256 $run
}
function New-SourceValue {
    [ordered]@{Schema='iw7.model-ff-output-files/1';Files=@('work/fixture.pak','source/model-ff-plan.json');StockInputs=@('fixture.pak')}
}
try{
    Confirm-SourceCase 'manifest source hash and immutable lists' {
        $declaration=Read-SourceDeclaration (New-SourceValue)
        if($declaration.Files.Count -ne 2 -or $declaration.StockInputs.Count -ne 1){throw 'Source manifest arrays differ.'}
        $mutable=$true;try{$declaration.Files[0]='changed'}catch{$mutable=$false}
        if($mutable -or (Test-Path -LiteralPath $run)){throw 'Source declaration modified data or created RunRoot.'}
    }
    Confirm-SourceRefusal 'manifest hash mismatch' {$pin=Write-SourceJson ((New-SourceValue)|ConvertTo-Json);Read-ModelFFOutputNamespacePlan $pin.Path ('0'*64) $run}
    Confirm-SourceRefusal 'duplicate JSON property' {$pin=Write-SourceJson '{"Schema":"iw7.model-ff-output-files/1","Files":["work/a"],"Files":["work/b"],"StockInputs":["b"]}';Read-ModelFFOutputNamespacePlan $pin.Path $pin.SHA256 $run}
    foreach($field in 'Schema','Files','StockInputs'){
        Confirm-SourceRefusal ('missing '+$field) {$value=New-SourceValue;$value.Remove($field);Read-SourceDeclaration $value}
        Confirm-SourceRefusal ('wrong type '+$field) {$value=New-SourceValue;$value[$field]=42;Read-SourceDeclaration $value}
    }
    Confirm-SourceRefusal 'unknown manifest field' {$value=New-SourceValue;$value.Extra=$false;Read-SourceDeclaration $value}
    Confirm-SourceRefusal 'case duplicate paths' {$value=New-SourceValue;$value.Files+=@('work/FIXTURE.PAK');Read-SourceDeclaration $value}
    Confirm-SourceRefusal 'stock not in global namespace' {$value=New-SourceValue;$value.StockInputs=@('missing.pak');Read-SourceDeclaration $value}
    Confirm-SourceRefusal 'nonstring manifest item' {$value=New-SourceValue;$value.Files+=42;Read-SourceDeclaration $value}
    Confirm-SourceRefusal 'empty stock array' {$value=New-SourceValue;$value.StockInputs=@();Read-SourceDeclaration $value}
    foreach($path in @('../escape','/absolute','C:drive','a\b','a//b','a/./b','a/../b','a/b.','a/b ','a/AUX.bin','a/*')){
        Confirm-SourceRefusal ('ordinary relative '+$path) {ConvertTo-ModelFFRelativeOutputPath $path}
    }
    Confirm-SourceRefusal 'invalid UTF8 metadata' {
        $path=Join-Path $fixtureRoot 'invalid-utf8.json';[IO.File]::WriteAllBytes($path,[byte[]]@(123,255,125))
        Read-ModelFFOutputNamespacePlan $path (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() $run
    }
    Confirm-SourceRefusal 'one MiB source metadata bound' {
        $pin=Write-SourceJson (' '*1MB+'{}');Read-ModelFFOutputNamespacePlan $pin.Path $pin.SHA256 $run
    }
    Confirm-SourceCase 'path 259 characters accepted without IO' {Assert-ModelFFNativePathBudget 'C:\p' @('a'*254)}
    Confirm-SourceRefusal 'path 260 characters refused without IO' {Assert-ModelFFNativePathBudget 'C:\p' @('a'*255)}
    Confirm-SourceRefusal 'long effective sidecar path refused before RunRoot exists' {
        $longRoot='C:\'+('a'*180)
        Assert-ModelFFNativePathBudget $longRoot @('work/dump/fixture/techsets/constantbuffer/fixture_techset/fixture_material.cbi')
    }
    $declaration=Read-SourceDeclaration (New-SourceValue)
    $project=[pscustomobject]@{'authoring.json'=[pscustomobject]@{Bytes=1;SHA256=('a'*64)}}
    $descriptor=[pscustomobject]@{material_template=[pscustomobject]@{material='templates/material.json'}}
    $projectValue=New-SourceValue;$projectValue.Files+=@('author-project/authoring.json','author-project/templates/material.json')
    $projectDeclaration=Read-SourceDeclaration $projectValue
    Confirm-SourceCase 'author project and template coverage before admission' {Assert-ModelFFNamespaceAuthorProject $projectDeclaration $project $descriptor}
    Confirm-SourceRefusal 'missing author project declaration' {Assert-ModelFFNamespaceAuthorProject $declaration $project $descriptor}
    Confirm-SourceRefusal 'extra author project declaration' {$value=New-SourceValue;$value.Files=@($projectValue.Files)+@('author-project/extra.json');Assert-ModelFFNamespaceAuthorProject (Read-SourceDeclaration $value) $project $descriptor}
    $requiredPaths=@('work/zonetool.exe','work/xmodel/fixture.xmb','work/dump/fixture/techsets/constantbuffer/techset/material.cbi','roundtrip/techsets/constantbuffer/techset/material.cbi')
    $requiredMap=[Collections.Generic.Dictionary[string,bool]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($name in $requiredPaths){$requiredMap.Add($name,$true)}
    $requiredNamespace=[pscustomobject]@{Files=$requiredMap}
    $requiredPlan=[pscustomobject]@{zone='fixture';source_files=[pscustomobject]@{'xmodel/fixture.xmb'=('a'*64)};dump_files=@('techsets/constantbuffer/techset/material.cbi')}
    Confirm-SourceCase 'required native Work dump and roundtrip paths covered before FF' {Assert-ModelFFNamespaceRequiredFFPaths $requiredNamespace $requiredPlan}
    Confirm-SourceRefusal 'required native CBI path undeclared before FF' {$name=$requiredPaths[2];$null=$requiredMap.Remove($name);try{Assert-ModelFFNamespaceRequiredFFPaths $requiredNamespace $requiredPlan}finally{$requiredMap.Add($name,$true)}}
    Confirm-SourceCase 'actual stock exact match' {Assert-ModelFFNamespaceStockInputs $declaration @([pscustomobject]@{Relative='fixture.pak'})}
    Confirm-SourceRefusal 'actual stock missing' {Assert-ModelFFNamespaceStockInputs $declaration @()}
    Confirm-SourceRefusal 'actual stock extra' {Assert-ModelFFNamespaceStockInputs $declaration @([pscustomobject]@{Relative='fixture.pak'},[pscustomobject]@{Relative='extra.pak'})}
    Confirm-SourceRefusal 'actual stock duplicate' {Assert-ModelFFNamespaceStockInputs $declaration @([pscustomobject]@{Relative='fixture.pak'},[pscustomobject]@{Relative='FIXTURE.PAK'})}
    $stageFiles=@('model-ff-plan.json','xmodel/fixture.xmb','evidence/material-inputs.json','evidence/writer/writer-source.json','evidence/writer/writer-provenance.json','evidence/writer/writer.cpp','evidence/writer/writer-closure.json','evidence/writer/writer-native-run.json')
    $stageValue=New-SourceValue;$stageValue.Files=@('work/fixture.pak')+@($stageFiles|ForEach-Object {'source/'+$_})
    $stageDeclaration=Read-SourceDeclaration $stageValue
    $plan=[pscustomobject]@{source_files=[pscustomobject]@{'xmodel/fixture.xmb'=('a'*64)}}
    $writer=[pscustomobject]@{source_files=[pscustomobject]@{'writer.cpp'=('b'*64)}}
    foreach($name in $stageFiles){$path=Join-Path $source $name;$null=[IO.Directory]::CreateDirectory((Split-Path $path));[IO.File]::WriteAllText($path,'Source fixture only')}
    Confirm-SourceCase 'actual stage files and recipe exactly match sealed declaration' {Assert-ModelFFNamespaceStage $stageDeclaration $run $source $plan $writer $true}
    Confirm-SourceRefusal 'actual stage extra file' {$path=Join-Path $source 'extra.txt';[IO.File]::WriteAllText($path,'x');try{Assert-ModelFFNamespaceStage $stageDeclaration $run $source $plan $writer $true}finally{[IO.File]::Delete($path)}}
    Confirm-SourceRefusal 'actual stage missing file' {$path=Join-Path $source 'xmodel/fixture.xmb';[IO.File]::Delete($path);try{Assert-ModelFFNamespaceStage $stageDeclaration $run $source $plan $writer $true}finally{[IO.File]::WriteAllText($path,'Source fixture only')}}
    Confirm-SourceRefusal 'stage declared extra recipe file' {$value=New-SourceValue;$value.Files=@($stageValue.Files)+@('source/undeclared-recipe.txt');$different=Read-SourceDeclaration $value;Assert-ModelFFNamespaceStage $different $run $source $plan $writer $true}
    Confirm-SourceRefusal 'unexpected empty stage directory' {$path=Join-Path $source 'unexpected';$null=[IO.Directory]::CreateDirectory($path);try{Assert-ModelFFNamespaceStage $stageDeclaration $run $source $plan $writer $true}finally{[IO.Directory]::Delete($path,$false)}}
    $material='{"techniqueSet->name":"fixture_techset","constantTable":[{"name":"a","literal":[1,1,1,1]}],"textureTable":[{"image":"fixture_color","semantic":14}],"stateFlags":57}'
    function Invoke-SourceMaterial([string]$Before,[string]$After){
        $first=Write-SourceJson $Before;$second=Write-SourceJson $After
        $sourceGuard=[IO.FileStream]::new($first.Path,'Open','Read','Read');$dumpGuard=[IO.FileStream]::new($second.Path,'Open','Read','Read')
        try{
            $sourceGuard.Position=$sourceGuard.Length;$dumpGuard.Position=$dumpGuard.Length
            $result=Assert-ModelFFDumpMaterialJson $sourceGuard $dumpGuard
            if($sourceGuard.Position -ne 0 -or $dumpGuard.Position -ne 0 -or !$sourceGuard.CanRead -or !$dumpGuard.CanRead){throw 'Original material guards were closed or positions not reset.'}
            if(!$result.MetadataMatch -or $result.MaterialReadbackVerified -or $result.Ready){throw 'Material metadata promoted qualification.'}
        }finally{$sourceGuard.Dispose();$dumpGuard.Dispose()}
    }
    Confirm-SourceCase 'literal techniqueSet and all source fields match' {Invoke-SourceMaterial $material $material}
    Confirm-SourceCase 'JSON formatting and object order do not affect semantic match' {Invoke-SourceMaterial $material '{"stateFlags":57,"textureTable":[{"semantic":14,"image":"fixture_color"}],"constantTable":[{"literal":[1.0,1,1,1],"name":"a"}],"techniqueSet->name":"fixture_techset","extraNativeField":0}'}
    Confirm-SourceCase 'existing Python numeric scalar equality preserved' {Invoke-SourceMaterial ($material.Replace('"stateFlags":57','"stateFlags":true')) ($material.Replace('"stateFlags":57','"stateFlags":1.0'))}
    Confirm-SourceRefusal 'material wrong literal techset value' {Invoke-SourceMaterial $material ($material.Replace('fixture_techset','different'))}
    Confirm-SourceRefusal 'material wrong literal key' {Invoke-SourceMaterial $material ($material.Replace('techniqueSet->name','techniqueSet'))}
    Confirm-SourceRefusal 'material changed constant' {Invoke-SourceMaterial $material ($material.Replace('[1,1,1,1]','[2,1,1,1]'))}
    Confirm-SourceRefusal 'material changed texture semantics' {Invoke-SourceMaterial $material ($material.Replace('"semantic":14','"semantic":15'))}
    Confirm-SourceRefusal 'material duplicate key' {Invoke-SourceMaterial $material ($material.Replace('"stateFlags":57','"stateFlags":57,"stateFlags":57'))}
    Confirm-SourceRefusal 'material JSON exceeds bounded input' {Invoke-SourceMaterial $material (' '*256KB+$material)}
    $buildPath=Join-Path (Split-Path $Entry) 'Build-ModelFF.ps1';$tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile([IO.Path]::GetFullPath($buildPath),[ref]$tokens,[ref]$errors)
    if($errors.Count){throw 'Actual ModelFF entry failed to parse.'}
    $commands=@($ast.FindAll({param($node)$node -is [Management.Automation.Language.CommandAst]},$true))
    $admission=@($commands|Where-Object {$_.GetCommandName() -ceq 'Enter-IW7ResourceLease'})[0]
    Confirm-SourceCase 'namespace Source and effective paths are checked before admission' {
        foreach($name in 'Read-ModelFFOutputNamespacePlan','New-ModelFFOutputNamespace','New-ModelFFOutputNamespaceCounter','Assert-ModelFFNativePathBudget'){
            $calls=@($commands|Where-Object {$_.GetCommandName() -ceq $name})
            if($calls.Count -ne 1 -or $calls[0].Extent.EndOffset -gt $admission.Extent.StartOffset){throw ('Source ordering differs: '+$name)}
        }
    }
    Confirm-SourceCase 'actual stage and stock declarations are enforced before FF construction' {
        $build=@($commands|Where-Object {$_.GetCommandName() -ceq 'Invoke-ModelFFTool' -and $_.Extent.Text -match '^Invoke-ModelFFTool hud-build'})[0]
        foreach($name in 'Assert-ModelFFNamespaceStage','Assert-ModelFFNamespaceStockInputs'){
            $call=@($commands|Where-Object {$_.GetCommandName() -ceq $name})[0]
            if($call.Extent.StartOffset -le $admission.Extent.EndOffset -or $call.Extent.EndOffset -ge $build.Extent.StartOffset){throw ('Actual Source conformance ordering differs: '+$name)}
        }
    }
    Confirm-SourceCase 'literal JSON comparison precedes required sidecar copies' {
        $json=@($commands|Where-Object {$_.GetCommandName() -ceq 'Assert-ModelFFDumpMaterialJson'})[0]
        $copy=@($ast.FindAll({param($node)$node -is [Management.Automation.Language.ForEachStatementAst] -and $node.Variable.Extent.Text -ceq '$name' -and $node.Condition.Extent.Text -ceq '$dumpNames'},$true))[0]
        if($json.Extent.EndOffset -ge $copy.Extent.StartOffset -or !$copy.Extent.Text.Contains('Copy-Item -LiteralPath $p -Destination $target')){throw 'Required material sidecar copying was omitted or reordered.'}
    }
    [ordered]@{Schema='iw7.model-ff-path-source-tests/1';SourceOnly=$true;CaseCount=$testNames.Count;Cases=$testNames.ToArray();NativeJobStarted=$false;LeaseAcquired=$false;GameRun=$false;Passed=$true}|ConvertTo-Json -Depth 4
}finally{
    $resolved=[IO.Path]::GetFullPath($fixtureRoot)
    if(!$resolved.StartsWith($fixtureBase+'\',[StringComparison]::OrdinalIgnoreCase) -or !(Split-Path $resolved -Leaf).StartsWith('ModelFFPathSource-',[StringComparison]::Ordinal)){
        throw 'Source fixture cleanup path escaped its intended temporary directory.'
    }
    [IO.Directory]::Delete($resolved,$true)
}
