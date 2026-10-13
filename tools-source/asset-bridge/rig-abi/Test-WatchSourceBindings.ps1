$ErrorActionPreference='Stop'
# Extract only three pure definitions from the real runner AST. Do not invoke its
# entry point, import providers, generate a revised Plan, or load native types.
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Run-WatchFixture.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner AST invalid.'}
foreach($name in @('Assert-WatchPath','Get-ReviewedWatchSourceBindings','Assert-WatchFixtureSpec')){
    $definition=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true)
    if(!$definition){throw 'Pure binding definition missing.'}
    Invoke-Expression $definition.Extent.Text
}
$bindingCall=$ast.Find({param($node) $node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -ceq 'Get-ReviewedWatchSourceBindings'},$true)
$imports=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.CommandAst] -and
    ($node.InvocationOperator -eq 'Dot' -or $node.GetCommandName() -eq 'Add-Type')},$true))
if(!$bindingCall -or @($imports|Where-Object {$_.Extent.StartOffset -lt $bindingCall.Extent.StartOffset}).Count){throw 'Source binding must precede every import/Add-Type.'}
$taskTemp=[IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetTempPath()) ('iw7-rig-source-bindings-'+[guid]::NewGuid().ToString('N'))))
$taskParent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
if(!$taskTemp.StartsWith($taskParent,[StringComparison]::OrdinalIgnoreCase)){throw 'Synthetic directory escaped Temp.'}
New-Item -ItemType Directory -Path $taskTemp|Out-Null
$guards=[Collections.Generic.List[IDisposable]]::new()
$names=@('Run-WatchFixture.ps1','Watchpoint.Core.ps1','WatchpointDeadline.cs','capture.py','cdb_transport.py','debug_fixture.py','owned_fixture.py','fixture-providers.json')
$hashes=[ordered]@{};$payloads=@{}
try{
    foreach($name in $names){
        $path=Join-Path $taskTemp $name;$payloads[$name]='synthetic source only: '+$name
        [IO.File]::WriteAllText($path,$payloads[$name]);$hashes[$name]=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()
    }
    $expected=[pscustomobject]$hashes
    $spec=[ordered]@{Schema='iw7.rig-watch-fixture-plan/4';Mode='fixture';ResourceProfile='iw7.rig-watch-python-cdb-fixture/1';
        Nonce=('b'*32);RunRoot='C:\synthetic\runtime\fresh';ProviderRoot='C:\synthetic';PythonExe='C:\synthetic\python.exe';
        PythonSHA256=('a'*64);CdbExe='C:\synthetic\cdb.exe';SourceBindings=$expected}
    $profile=Assert-WatchFixtureSpec ([pscustomobject]$spec)
    if($profile.PhysicalBytes -ne 4GB -or $profile.CommitBytes -ne 6GB -or !$profile.EstimateOnly -or $profile.MeasuredPeaks -or $profile.RetailCompatible){throw 'Plan fixed fixture envelope differs.'}
    foreach($change in @(@{Schema='iw7.rig-watch-fixture-plan/1'},@{Schema='iw7.rig-watch-fixture-plan/2'},@{Schema='iw7.rig-watch-fixture-plan/3'},
        @{Mode='retail'},@{ResourceProfile='retail-10-14'},@{ResourceProfile='custom'},@{PhysicalBytes=1GB},@{CommitBytes=1GB},@{TargetExe='zonetool.exe'})){
        $bad=$spec|ConvertTo-Json -Depth 5|ConvertFrom-Json
        foreach($key in $change.Keys){$bad|Add-Member -NotePropertyName $key -NotePropertyValue $change[$key] -Force}
        $refused=$false;try{Assert-WatchFixtureSpec $bad|Out-Null}catch{$refused=$true}
        if(!$refused){throw 'Old schema, retail profile or arbitrary budget/target accepted.'}
    }
    $specText=$spec|ConvertTo-Json -Depth 4 -Compress
    $specHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($specText)))
    $bindings=Get-ReviewedWatchSourceBindings $expected $taskTemp $guards
    if($bindings.Count -ne 8 -or $guards.Count){throw 'Valid source-only binding failed.'}
    foreach($name in $names){
        $path=Join-Path $taskTemp $name;[IO.File]::AppendAllText($path,' MUTATED')
        $refused=$false
        try{Get-ReviewedWatchSourceBindings $expected $taskTemp $guards -Hold|Out-Null}catch{
            $refused=$_.Exception.Message -eq "Reviewed source changed before import: $name"
        }
        if(!$refused -or $guards.Count){throw "Mutation did not fail closed before import: $name"}
        $unchanged=$spec|ConvertTo-Json -Depth 4 -Compress
        if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($unchanged))) -cne $specHash){throw 'Test changed spec instead of source.'}
        [IO.File]::WriteAllText($path,$payloads[$name])
    }
    foreach($bad in @($null,[pscustomobject]@{},[pscustomobject]@{'capture.py'=('a'*64)})){
        $refused=$false;try{Get-ReviewedWatchSourceBindings $bad $taskTemp $guards|Out-Null}catch{$refused=$true}
        if(!$refused){throw 'Incomplete reviewed source map accepted.'}
    }
    $null=Get-ReviewedWatchSourceBindings $expected $taskTemp $guards -Hold
    if($guards.Count -ne 8){throw 'Run did not hold all eight source files before import.'}
    $blocked=$false
    try{[IO.File]::AppendAllText((Join-Path $taskTemp 'capture.py'),'late mutation')}catch{$blocked=$true}
    if(!$blocked){throw 'Late edit was allowed while reviewed source guards were held.'}
    'PASS fixed fixture4/6 and 9 profile/schema/override refusals; 8 independent source mutations with unchanged SpecSHA; 3 incomplete maps; early-import ordering; 8 held guards and late-edit refusal. No Plan or native execution.'
}finally{
    foreach($guard in $guards){$guard.Dispose()}
    # Delete only the known files and then the now-empty synthetic directory.
    foreach($name in $names){$path=Join-Path $taskTemp $name;if(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $path}}
    Remove-Item -LiteralPath $taskTemp
}
