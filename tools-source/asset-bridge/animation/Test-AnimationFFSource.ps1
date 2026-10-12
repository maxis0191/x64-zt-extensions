# Pure binding/refusal/restoration tests. No launcher, Add-Type, lease or native call.
param([Parameter(Mandatory)][string]$ProviderRoot)
$ErrorActionPreference='Stop'
$checks=0
function Assert-Check([bool]$Condition,[string]$Message){if(!$Condition){throw $Message};$script:checks++}
function Assert-Throws([scriptblock]$Body,[string]$Pattern){
    $caught=$false
    try{& $Body}catch{if($_.Exception.Message -notmatch $Pattern){throw};$caught=$true}
    Assert-Check $caught "Expected refusal: $Pattern"
}
. "$PSScriptRoot/AnimationFF.Core.ps1"
$bindings=Get-AnimationProviderBindings $ProviderRoot
Assert-Check ($bindings.Count -eq 9) 'Nine explicit provider/transitive bindings'
$pins=@{};foreach($key in $bindings.Keys){$pins[$key]=$bindings[$key].SHA256}
Assert-Check ((Get-AnimationProviderBindings $ProviderRoot $pins -RequirePins).Count -eq 9) 'Exact complete pins accepted'
$broken=$pins.Clone();$broken['sdk/modding/beacon_tool_phase.py']='0'*64
Assert-Throws {Get-AnimationProviderBindings $ProviderRoot $broken -RequirePins} 'Provider hash changed'
$broken=$pins.Clone();$broken.Remove('ops/Resource-Memory.ps1')
Assert-Throws {Get-AnimationProviderBindings $ProviderRoot $broken -RequirePins} 'exact nine'
$broken=$pins.Clone();$broken.Remove('ops/Resource-Memory.ps1');$broken['unexpected']='0'*64
Assert-Throws {Get-AnimationProviderBindings $ProviderRoot $broken -RequirePins} 'Missing provider pin'
foreach($name in @('ops/Base-Client.Core.ps1','sdk/modding/BeaconFF.Core.ps1','ops/model-lab/ModelFF.Core.ps1')){
    Assert-AnimationPureImport $bindings[$name].Path
    . $bindings[$name].Path
}
foreach($name in @('Build-AnimationFF.ps1','AnimationFF.Core.ps1')){
    $errors=$null;$tokens=$null
    $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name),[ref]$tokens,[ref]$errors)
    Assert-Check (!$errors.Count) "PowerShell syntax: $name $errors"
}
$source=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'Build-AnimationFF.ps1'))
Assert-Check ($source.IndexOf('if(!$Run)') -lt $source.IndexOf('. $bindings[''ops/Resource-Scheduler.Core.ps1''].Path')) 'Plan exits before scheduler import'
Assert-Check ($source.IndexOf('$lease=Enter-IW7ResourceLease') -lt $source.IndexOf('Add-Type -LiteralPath')) 'BuildJob compilation follows admission'
Assert-Check ($source.IndexOf('Get-BeaconJobIdentity $owner') -lt $source.IndexOf('$owner.Resume()')) 'Original handle identity before resume'
Assert-Check ($source.IndexOf('Add-IW7ResourceProcess -Token') -lt $source.IndexOf('$owner.Resume()')) 'Suspended registration before resume'
Assert-Check ($source -notmatch 'Stop-Process|taskkill|\.Kill\(|WaitForExit|Start-Process') 'No PID-only process/closure fallback'
Assert-Check ($source -match 'if\(\$closed\)\{\$owner.Dispose\(\)' -and $source -match 'AnimationFF.Quarantine') 'Unknown closure retains exact owner'
Assert-Check ($source.IndexOf('$script:closed=$false') -lt $source.IndexOf('[IW7.CommunityBuild.BuildJob]::Prepare')) 'Failed factory cannot imply tree closure'

$native=[pscustomobject]@{Schema='iw7.original-probe-native-run/1';Status='NativeSerializerAndReadbackPassed';XabBytes=281;
    XabSHA256='1284b72cf501ae42f77958579610dbcaf692b9153cd06ff66dcf2d1d11eeda7d';
    Readback=[pscustomobject]@{status='original-probe-data-pass';sha256='1284b72cf501ae42f77958579610dbcaf692b9153cd06ff66dcf2d1d11eeda7d'};
    Processes=@([pscustomobject]@{ExitCode=0},[pscustomobject]@{ExitCode=0},[pscustomobject]@{ExitCode=0})}
Assert-AnimationNativeReceipt $native;$checks++
$native.Processes[2].ExitCode=1
Assert-Throws {Assert-AnimationNativeReceipt $native} 'Exact successful'
$native.Processes[2].ExitCode=0;$native.XabBytes=282
Assert-Throws {Assert-AnimationNativeReceipt $native} 'Exact successful'
$log="Loading zone `"sdk_animation_probe`"`nLoading asset `"paris_original_probe_bend`" of type xanim.`nLoading asset `"sdk_animation_probe`" of type rawfile."
Assert-Check (@(Get-AnimationInventory $log).Count -eq 2) 'Exact two-asset inventory'
Assert-Throws {Get-AnimationInventory ($log+"`nLoading asset `"extra`" of type xanim.")} 'Exactly two'
Assert-Throws {Get-AnimationInventory ($log.Replace('type rawfile','type xanim'))} 'Exactly two'
Assert-Throws {Get-AnimationInventory ($log+"`n[ ERROR ] unresolved")} 'unavailable'
Assert-Throws {Get-AnimationInventory ($log+"`nLoading asset invalid")} 'Malformed'
$readback=[pscustomobject]@{status='original-probe-data-pass';readback_scope='ff-redump-profile';bytes=281;runtime_verified=$false;general_xanim_decoder=$false;notetrack=@{name='probe_contact';normalized_time=0.5}}
Assert-AnimationReadback $readback;$checks++
$readback.runtime_verified=$true
Assert-Throws {Assert-AnimationReadback $readback} 'Exact original'
$readback.runtime_verified=$false;$readback.readback_scope='original-native-writer-profile'
Assert-Throws {Assert-AnimationReadback $readback} 'Exact original'
Assert-Check ((ConvertTo-AnimationArguments @('-B','C:\space name\input.py')) -ceq '"-B" "C:\space name\input.py"') 'Windows argument quoting'
foreach($bad in @('bad"quote',"bad`nline",'C:\tail\','')){Assert-Throws {ConvertTo-AnimationArguments @($bad)} 'Unsupported'}

$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$testRoot=Join-Path $repo ('runtime/animation-ff-source-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($testRoot)|Out-Null
try{
    $impure=Join-Path $testRoot 'impure.ps1';[IO.File]::WriteAllText($impure,'function Safe {} ; Write-Output unsafe')
    Assert-Throws {Assert-AnimationPureImport $impure} 'function definitions only'
    $stock=Join-Path $testRoot 'stock';[IO.Directory]::CreateDirectory($stock)|Out-Null
    $names=@('main/code_pre_gfx.ff','zone/assetfile1.pak','iw7_ship.exe','main/fileSysCheck.cfg')+@(0..67|ForEach-Object {"main/pure-$_.ff"})
    $entries=@(foreach($name in $names){
        $path=Join-Path $stock $name;[IO.Directory]::CreateDirectory((Split-Path $path))|Out-Null
        $size=if($name -ceq 'main/fileSysCheck.cfg'){77}else{1}
        [IO.File]::WriteAllBytes($path,[byte[]]::new($size))
        [pscustomobject]@{Relative=$name;Source=[IO.Path]::GetFullPath($path);Bytes=$size}
    })
    $receipt=[pscustomobject]@{Schema='iw7.model-ff-build/1';Restored=$true;StockPreserved=$true;RetainedLeaseToken=$null;Inputs=$entries}
    $inputs=@(Get-AnimationStockInputs $receipt $stock)
    Assert-Check ($inputs.Count -eq 72 -and @($inputs|Where-Object Mode -eq Copy).Count -eq 1) '72 entries; sentinel only copy'
    $receipt.Restored=$false;Assert-Throws {Get-AnimationStockInputs $receipt $stock} 'Completed/restored';$receipt.Restored=$true
    $receipt.RetainedLeaseToken='still-owned';Assert-Throws {Get-AnimationStockInputs $receipt $stock} 'Completed/restored';$receipt.RetainedLeaseToken=$null
    $entries[0].Bytes=2;Assert-Throws {Get-AnimationStockInputs $receipt $stock} 'Stock size';$entries[0].Bytes=1
    $old=$entries[1];$entries[1]=$entries[0];Assert-Throws {Get-AnimationStockInputs $receipt $stock} 'duplicate';$entries[1]=$old
    $entries[0].Relative='../outside';Assert-Throws {Get-AnimationStockInputs $receipt $stock} 'relative|escape|Invalid|Unsafe|outside';$entries[0].Relative='main/code_pre_gfx.ff'
    Assert-Throws {Resolve-IW7BasePath $stock '../outside'} 'relative|escape|Invalid|Unsafe|outside'

    # Run the real common restore coordinator; replace only native/CIM and lease I/O.
    $script:events=[Collections.Generic.List[string]]::new();$script:failRestore=$false;$script:failFinal=$false
    function Assert-ModelFFVacant {$script:events.Add('vacant')}
    function Assert-ModelFFInputs($Inputs,$Work,[switch]$SourceOnly){
        $script:events.Add($(if($SourceOnly){'source-final'}else{'inputs'}))
        if($SourceOnly -and $script:failFinal){throw 'injected source-final failure'}
    }
    function Restore-IW7BaseTransaction {if($script:failRestore){throw 'injected restoration failure'};$script:events.Add('restore')}
    function Exit-IW7ResourceLease {param($Token);$script:events.Add('release')}
    function Write-ModelFFState {$script:events.Add('receipt')}
    $guard=[pscustomobject]@{};$guard|Add-Member ScriptMethod Dispose {$script:events.Add('dispose')}
    function New-TestState {@{Work='pure';Inputs=@();Transaction=@{};Restored=$false;StockPreserved=$false;RestorationStatus='Pending';CleanupError=$null;RetainedLeaseToken='kept'}}
    $state=New-TestState
    Complete-AnimationFF $state 'unused' @{Token='kept'} $false $true @($guard)
    Assert-Check (($events -join ',') -ceq 'receipt' -and $state.RetainedLeaseToken -ceq 'kept') 'Unknown tree keeps guards, staging and lease'
    $events.Clear();$state=New-TestState
    Complete-AnimationFF $state 'unused' @{Token='kept'} $true $true @($guard)
    Assert-Check (($events -join ',') -ceq 'dispose,vacant,inputs,restore,source-final,receipt,release,receipt') 'Common restore/source proof precede release'
    Assert-Check ($state.Restored -and $state.StockPreserved -and !$state.RetainedLeaseToken) 'Confirmed restore clears retained lease'
    $events.Clear();$state=New-TestState;$script:failRestore=$true
    Assert-Throws {Complete-AnimationFF $state 'unused' @{Token='kept'} $true $true @($guard)} 'injected restoration'
    Assert-Check ($events -notcontains 'release' -and $state.RetainedLeaseToken -ceq 'kept' -and $state.RestorationStatus -ceq 'Refused') 'Restoration refusal retains lease'
    $events.Clear();$state=New-TestState;$script:failRestore=$false;$script:failFinal=$true
    Assert-Throws {Complete-AnimationFF $state 'unused' @{Token='kept'} $true $true @($guard)} 'injected source-final'
    Assert-Check ($events -contains 'restore' -and $events -notcontains 'release') 'Source final refusal after restoration retains lease'
    $events.Clear();$state=New-TestState;$script:failFinal=$false
    Complete-AnimationFF $state 'unused' @{Token='kept'} $true $false @($guard)
    Assert-Check (($events -join ',') -ceq 'dispose,release') 'No staging releases without guessed restoration'
}finally{
    # Only tiny files created above; no recursive tree removal.
    $canonical=[IO.Path]::GetFullPath($testRoot)
    if(!$canonical.StartsWith(([IO.Path]::GetFullPath((Join-Path $repo 'runtime'))+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)){throw 'Test cleanup root escaped runtime.'}
    Get-ChildItem -LiteralPath $canonical -File -Recurse|ForEach-Object {Remove-Item -LiteralPath $_.FullName}
    Get-ChildItem -LiteralPath $canonical -Directory -Recurse|Sort-Object {$_.FullName.Length} -Descending|ForEach-Object {Remove-Item -LiteralPath $_.FullName}
    Remove-Item -LiteralPath $canonical
}
[pscustomobject]@{Checks=$checks;NativeLoaded=$false;FFBuilt=$false;LeaseAcquired=$false}|ConvertTo-Json
