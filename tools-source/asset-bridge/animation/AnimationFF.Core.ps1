# Pure functions for this one original animation profile. No native import.
function Get-AnimationProviderBindings([string]$Root,$Expected,[switch]$RequirePins) {
    $names=@('ops/Base-Client.Core.ps1','ops/model-lab/ModelFF.Core.ps1','ops/hud-lab/HudFileIdentity.cs',
        'ops/Resource-Scheduler.Core.ps1','ops/Resource-Memory.ps1','ops/native/ResourceMemory.cs',
        'ops/Resource-RecorderOwnedProcess.Core.ps1','sdk/modding/BeaconFF.Core.ps1','sdk/modding/beacon_tool_phase.py')
    if($RequirePins -and (!$Expected -or $Expected.Count -ne $names.Count)){throw 'Run requires the exact nine provider source hashes.'}
    $result=[ordered]@{}
    foreach($name in $names){
        $path=[IO.Path]::GetFullPath((Join-Path $Root $name))
        $cursor=$path
        while($cursor){if((Get-Item -LiteralPath $cursor).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){throw 'Provider reparse ancestry refused.'};$cursor=Split-Path $cursor -Parent}
        $hash=(Get-FileHash -LiteralPath $path).Hash
        if($Expected -and $Expected.Contains($name)){
            if($Expected[$name] -notmatch '^[a-fA-F0-9]{64}$' -or $hash -ine $Expected[$name]){throw "Provider hash changed: $name"}
        } elseif($RequirePins){throw "Missing provider pin: $name"}
        $result[$name]=[pscustomobject]@{Path=$path;SHA256=$hash}
    }
    $result
}
function Assert-AnimationPureImport([string]$Path) {
    $errors=$null;$tokens=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile($Path,[ref]$tokens,[ref]$errors)
    if($errors.Count -or $ast.ParamBlock -or $ast.BeginBlock -or $ast.ProcessBlock -or
        @($ast.EndBlock.Statements|Where-Object {$_ -isnot [Management.Automation.Language.FunctionDefinitionAst]}).Count){
        throw 'Planning imports must contain function definitions only.'
    }
}
function Assert-AnimationNativeReceipt($Receipt) {
    $hash='1284b72cf501ae42f77958579610dbcaf692b9153cd06ff66dcf2d1d11eeda7d'
    if($Receipt.Schema -cne 'iw7.original-probe-native-run/1' -or $Receipt.Status -cne 'NativeSerializerAndReadbackPassed' -or
        $Receipt.XabBytes -ne 281 -or $Receipt.XabSHA256 -ine $hash -or
        $Receipt.Readback.status -cne 'original-probe-data-pass' -or $Receipt.Readback.sha256 -ine $hash -or
        @($Receipt.Processes).Count -ne 3 -or @($Receipt.Processes|Where-Object {$_.ExitCode -ne 0}).Count){throw 'Exact successful original native XAB receipt required.'}
}
function Get-AnimationStockInputs($State,[string]$StockRoot,$Binding=$null,$ReviewedManifest=$null,[string]$ReviewedManifestSHA256) {
    if($State.Schema -cne 'iw7.model-ff-build/1' -or !$State.Restored -or !$State.StockPreserved -or $State.RetainedLeaseToken -or @($State.Inputs).Count -ne 72){throw 'Completed/restored 72-entry stock transaction required.'}
    if($Binding){
        $bound=@(Get-FFStockBindingInputs $State $Binding $ReviewedManifest $StockRoot '4cf67ebe1645c6c0761b9a24cb4e4630edee9c5d737742c704d624fe60cb3850' $ReviewedManifestSHA256)
        # Preserve each historical mode separately. This staging profile still
        # links immutable EXE/DLL bytes and copies only the mutable sentinel.
        foreach($entry in $bound){$entry|Add-Member NoteProperty BaselineMode $entry.Mode;$entry.Mode=if($entry.Relative -ceq 'main/fileSysCheck.cfg'){'Copy'}else{'HardLink'}}
        return $bound
    }
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $inputs=@(foreach($entry in $State.Inputs){
        $path=Resolve-IW7BasePath $StockRoot $entry.Relative
        if(!$seen.Add($entry.Relative) -or $path -ine $entry.Source){throw 'Stock path or duplicate differs.'}
        $file=Get-Item -LiteralPath $path
        if($file.PSIsContainer -or $file.Length -ne $entry.Bytes -or $file.Attributes.HasFlag([IO.FileAttributes]::ReadOnly)){throw 'Stock size or attributes differ.'}
        [pscustomobject]@{Relative=$entry.Relative;Source=$path;Mode=$(if($entry.Relative -ceq 'main/fileSysCheck.cfg'){'Copy'}else{'HardLink'});
            Bytes=$file.Length;ModifiedUtc=$file.LastWriteTimeUtc.ToString('o');Attributes=[int]$file.Attributes}
    })
    foreach($required in @('main/code_pre_gfx.ff','zone/assetfile1.pak','iw7_ship.exe','main/fileSysCheck.cfg')){if(!$seen.Contains($required)){throw 'Required bounded bootstrap stock missing.'}}
    if(@($inputs|Where-Object Mode -eq Copy).Count -ne 1 -or @($inputs|Where-Object Mode -eq Copy)[0].Bytes -ne 77){throw 'Only the exact 77-byte sentinel may be copied.'}
    $inputs
}
function New-AnimationFFPlan($Bindings,[string]$RunRoot,[string]$AnimationRoot,[string]$NativeInput,[string]$NativeReceipt,
    [string]$NativeReceiptSHA256,[string]$StockRoot,[string]$StockReceipt,[string]$StockReceiptSHA256,
    [string]$CandidateRoot,[string]$CandidateArtifactSHA256,[string]$JobSource,[string]$JobSourceSHA256,
    [string]$PythonExe,[string]$PythonSHA256,[string]$StockBindingReceipt,[string]$StockBindingReceiptSHA256,
    [string]$ReviewedStockManifest,[string]$ReviewedStockManifestSHA256,[switch]$RequirePins) {
    $repo=Split-Path (Split-Path (Split-Path $AnimationRoot -Parent) -Parent) -Parent
    $run=Resolve-IW7BasePath (Join-Path $repo 'runtime') ([IO.Path]::GetRelativePath((Join-Path $repo 'runtime'),[IO.Path]::GetFullPath($RunRoot)))
    if(Test-Path -LiteralPath $run){throw 'Fresh animation FF run directory required.'}
    foreach($pair in @(@($NativeReceipt,$NativeReceiptSHA256),@($StockReceipt,$StockReceiptSHA256))){Assert-BeaconHash $pair[0] $pair[1]}
    if($NativeReceiptSHA256 -ine '7e123916b8e66433a730390151eee15cd20199a81e1558787fa49460ac06b248' -or
        $StockReceiptSHA256 -ine '4cf67ebe1645c6c0761b9a24cb4e4630edee9c5d737742c704d624fe60cb3850'){throw 'Pinned original and stock receipts required.'}
    Assert-AnimationNativeReceipt (Read-BeaconJson $NativeReceipt)
    Assert-BeaconHash $NativeInput '1284b72cf501ae42f77958579610dbcaf692b9153cd06ff66dcf2d1d11eeda7d'
    if((Get-Item -LiteralPath $NativeInput).Length -ne 281){throw 'Original XAB must remain 281 bytes.'}
    $csv=Join-Path $AnimationRoot 'fixtures/sdk_animation_probe.csv'
    if([IO.File]::ReadAllText($csv).Replace("`r`n","`n") -cne "xanim,paris_original_probe_bend`n"){throw 'Exact one-line animation zone required.'}
    $stockBinding=$null;$reviewed=$null
    $stockPins=@($StockBindingReceipt,$StockBindingReceiptSHA256,$ReviewedStockManifest,$ReviewedStockManifestSHA256)
    if(@($stockPins|Where-Object {$_}).Count -notin @(0,4)){throw 'Alternate binding and reviewed stock manifest each require a path and explicit hash.'}
    if($StockBindingReceipt){
        Assert-BeaconHash $StockBindingReceipt $StockBindingReceiptSHA256;$stockBinding=Read-BeaconJson $StockBindingReceipt
        Assert-BeaconHash $ReviewedStockManifest $ReviewedStockManifestSHA256;$reviewed=Read-BeaconJson $ReviewedStockManifest
    }
    $inputs=@(Get-AnimationStockInputs (Read-BeaconJson $StockReceipt) $StockRoot $stockBinding $reviewed $ReviewedStockManifestSHA256)
    if($RequirePins -and (!$CandidateArtifactSHA256 -or !$JobSourceSHA256 -or !$PythonSHA256)){throw 'Run requires candidate artifact, job source and Python hashes.'}
    $candidate=$null
    if($CandidateArtifactSHA256){
        $candidate=Assert-BeaconCandidate $CandidateRoot $CandidateArtifactSHA256
        if($candidate.SHA256 -ine 'e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04'){throw 'Exact full ZoneTool candidate required.'}
    }
    if($JobSourceSHA256){
        if($JobSourceSHA256 -ine 'f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387'){throw 'Reviewed existing BuildJob source required.'}
        Assert-BeaconHash $JobSource $JobSourceSHA256
    }
    $python=[IO.Path]::GetFullPath($PythonExe)
    if($PythonSHA256){Assert-BeaconHash $python $PythonSHA256}
    $reader=Join-Path $AnimationRoot 'read_probe.py';$adapter=Join-Path $AnimationRoot 'animation_tool_phase.py'
    $sources=[ordered]@{}
    foreach($path in @($reader,$adapter,(Join-Path $AnimationRoot 'Build-AnimationFF.ps1'),(Join-Path $AnimationRoot 'AnimationFF.Core.ps1'),
        (Join-Path (Split-Path $AnimationRoot -Parent) 'common/StockBinding.Core.ps1'),$csv,$NativeInput,$NativeReceipt,$StockReceipt)){
        $sources[$path]=(Get-FileHash -LiteralPath $path).Hash
    }
    if($StockBindingReceipt){$sources[$StockBindingReceipt]=$StockBindingReceiptSHA256;$sources[$ReviewedStockManifest]=$ReviewedStockManifestSHA256}
    [pscustomobject]@{Schema='iw7.animation-ff-plan/2';Zone='sdk_animation_probe';RunRoot=$run;Work=(Join-Path $run 'work');
        StockInputs=$inputs;StockBindingReceipt=$StockBindingReceipt;StockBindingReceiptSHA256=$StockBindingReceiptSHA256;
        StagingCopyBytes=[long](($inputs|Where-Object Mode -CEQ Copy|Measure-Object Bytes -Sum).Sum);
        StockContentAndIdentityRecheckPending=($null -ne $stockBinding);Candidate=$candidate;CandidatePending=($null -eq $candidate);Bindings=$Bindings;SourceHashes=$sources;
        NativeInput=[IO.Path]::GetFullPath($NativeInput);ZoneCSV=$csv;Reader=$reader;Adapter=$adapter;PythonExe=$python;
        PythonSHA256=(Get-FileHash -LiteralPath $python).Hash;JobSource=$JobSource;JobSourceSHA256=$JobSourceSHA256;
        Phases=@('build','verify','dump','read');Inventory=@('xanim,paris_original_probe_bend','rawfile,sdk_animation_probe');
        PhysicalBytes=8GB;CommitBytes=11GB;StreamLimitBytes=2MB;OutputStopBytes=64MB;ArtifactLimitBytes=1MB;DumpLimitBytes=64KB;
        PhaseSeconds=240;ReaderSeconds=30;OverallSeconds=900;Ready=$false;FFBuilt=$false}
}
function Get-AnimationInventory([string]$Log) {
    if(!$Log.Contains('Loading zone "sdk_animation_probe"') -or $Log -match 'could not be found|Could not find referenced|\[ ERROR \]|\[ FATAL \]'){throw 'Animation inventory unavailable or unresolved.'}
    $rows=@(foreach($line in $Log -split '\r?\n'|Where-Object {$_ -match 'Loading asset '}){
        if($line -cnotmatch 'Loading asset "([^"\r\n]+)" of type ([a-z0-9]+)\.$'){throw 'Malformed animation inventory row.'}
        $Matches[2]+','+$Matches[1]
    })
    $expected=@('xanim,paris_original_probe_bend','rawfile,sdk_animation_probe')
    if($rows.Count -ne 2 -or @($expected|Where-Object {$_ -cnotin $rows}).Count){throw 'Exactly two original animation inventory rows required.'}
    $rows
}
function Assert-AnimationReadback($Readback) {
    if($Readback.status -cne 'original-probe-data-pass' -or $Readback.readback_scope -cne 'ff-redump-profile' -or
        $Readback.bytes -ne 281 -or $Readback.runtime_verified -ne $false -or $Readback.general_xanim_decoder -ne $false -or
        $Readback.notetrack.name -cne 'probe_contact' -or $Readback.notetrack.normalized_time -ne 0.5){throw 'Exact original FF-redump reader result required.'}
}
function Complete-AnimationFF($State,[string]$StatePath,$Lease,[bool]$TreeClosed,[bool]$Saved,$Guards) {
    if(!$TreeClosed){$State.CleanupError='Owned tree closure unconfirmed; preserve guards, staging and lease.';Write-ModelFFState $State $StatePath;return}
    foreach($guard in $Guards){$guard.Dispose()}
    if($Saved){Complete-ModelFFRestore $State $StatePath $Lease.Token}
    elseif($Lease){Exit-IW7ResourceLease -Token $Lease.Token;$State.RetainedLeaseToken=$null}
}
function ConvertTo-AnimationArguments($Arguments) {
    (@(foreach($arg in $Arguments){
        if(!$arg -or $arg -match '["\x00-\x1f]' -or $arg.EndsWith('\')){throw 'Unsupported animation phase argument.'}
        '"'+$arg+'"'
    }) -join ' ')
}
function Register-AnimationPhase($Owner,[string]$LeaseToken,[scriptblock]$BudgetCheck,
    [scriptblock]$Now={ [datetime]::UtcNow },[scriptblock]$Delay={ Start-Sleep -Milliseconds 100 }) {
    # Original-handle identity is captured before Resume by the caller. As in
    # the proven Beacon adapter, CIM registration follows Resume. Do not weaken
    # the shared identity API or substitute the pre-resume record for its check.
    $deadline=(& $Now).AddSeconds(5);$attempts=0
    while(!$Owner.Exited){
        if((& $Now) -ge $deadline){throw 'Animation CIM registration deadline exceeded; stop original job.'}
        & $BudgetCheck
        $attempts++
        try{
            Add-IW7ResourceProcess -Token $LeaseToken -ProcessId $Owner.PID
            return [pscustomobject]@{Registered=$true;Outcome='Registered';Attempts=$attempts}
        }catch{
            if($_.Exception.Message -notlike 'Child identity unavailable*'){throw}
            if($Owner.Exited){break}
            if((& $Now) -ge $deadline){throw 'Animation CIM registration deadline exceeded; stop original job.'}
            & $Delay
        }
    }
    # A short phase may finish before CIM can observe it. This is not registered
    # success: the caller must still prove zero owned members, exit and receipt.
    [pscustomobject]@{Registered=$false;Outcome='ClosedBeforeRegistration';Attempts=$attempts}
}
