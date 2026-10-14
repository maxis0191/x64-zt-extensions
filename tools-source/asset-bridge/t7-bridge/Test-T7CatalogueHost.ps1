# Synthetic lifecycle tests plus a real lightweight pwsh argument probe.
# No engine, payload, native runtime type or lease is opened.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern){
    $caught=$false;try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected refusal: '+$_.Exception.Message)}
    Check $caught ('Expected refusal: '+$Pattern)
}
function Pin([string]$Path){[pscustomobject]@{Path=$Path;Bytes=(Get-Item -LiteralPath $Path).Length;SHA256=(Get-FileHash -LiteralPath $Path).Hash.ToLowerInvariant()}}
# Match the real runner's local import followed by closure in the original host.
Check (!(Get-Command Get-T7SelectedStreamedExport -ErrorAction SilentlyContinue)) 'Clean host unexpectedly has the runner-local selector.'
& {
    . (Join-Path $PSScriptRoot 'T7ResidentExport.Profile.ps1')
    Check ([bool](Get-Command Get-T7SelectedStreamedExport -ErrorAction SilentlyContinue)) 'Runner-local selector was not loaded.'
}
Check (!(Get-Command Get-T7SelectedStreamedExport -ErrorAction SilentlyContinue)) 'Runner-local selector leaked into host closure scope.'
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('t7-host-tests-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($temporary)
try {
    foreach($name in @('Invoke-T7CatalogueHost.ps1','T7CatalogueHost.Core.ps1')){
        $tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name),[ref]$tokens,[ref]$errors)
        Check (!$errors.Count) ('Parse error in '+$name)
    }
    # Exercise the installed host's actual .NET argv interface, not invented argv[0].
    $probePath=Join-Path $temporary 'argv-probe.ps1';$probeSpecPath=Join-Path $temporary 'argv-spec.json'
    $probeSource=@'
param($PlanPath,$PlanSHA256,$RunRoot,$HostContractPath,$HostContractSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
try {
    $spec=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'argv-spec.json') -Raw|ConvertFrom-Json
    . $spec.CorePath
    $hostIdentity=Get-T7CatalogueHostIdentity
    $actual=[Environment]::GetCommandLineArgs()
    Assert-T7CatalogueHostArguments $spec.State $actual $hostIdentity
    $result=[ordered]@{Status='Passed';HostImage=$hostIdentity.Image;Arguments=$actual;
        NativeTypesLoaded=[bool](('IW7HudFileIdentity' -as [type]) -or ('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]));
        HostStatePresent=($null -ne [AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost'))}
    [IO.File]::WriteAllText($spec.ResultPath,($result|ConvertTo-Json -Depth 4))
    exit 0
}catch{Write-Error $_ -ErrorAction Continue;exit 1}
'@
    [IO.File]::WriteAllText($probePath,$probeSource)
    $probeState=[pscustomobject]@{Contract=[pscustomobject]@{HostImage=[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName};EntryPath=$probePath;
        PlanPath=(Join-Path $temporary 'unopened-plan.json');PlanSHA256=('b'*64);RunRoot=(Join-Path $temporary 'uncreated-run');
        ContractPath=(Join-Path $temporary 'unopened-contract.json');ContractSHA256=('c'*64)}
    $probeResultPath=Join-Path $temporary 'argv-result.json'
    [IO.File]::WriteAllText($probeSpecPath,([ordered]@{CorePath=(Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1');State=$probeState;ResultPath=$probeResultPath}|ConvertTo-Json -Depth 5))
    $probeArguments=@('-NoLogo','-NoProfile','-NoExit','-File',$probePath,'-PlanPath',$probeState.PlanPath,'-PlanSHA256',$probeState.PlanSHA256,
        '-RunRoot',$probeState.RunRoot,'-HostContractPath',$probeState.ContractPath,'-HostContractSHA256',$probeState.ContractSHA256,'-Run')
    $start=[Diagnostics.ProcessStartInfo]::new($probeState.Contract.HostImage)
    $start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true;$start.RedirectStandardInput=$true
    foreach($argument in $probeArguments){$start.ArgumentList.Add($argument)}
    $probe=[Diagnostics.Process]::new();$probe.StartInfo=$start;$probeStarted=$false
    try {
        $probeStarted=$probe.Start();if(!$probeStarted){throw 'Argument probe did not start.'}
        $probe.StandardInput.Close() # EOF also closes the NoExit prompt after this source-only probe.
        $probeOutput=$probe.StandardOutput.ReadToEndAsync();$probeError=$probe.StandardError.ReadToEndAsync()
        if(!$probe.WaitForExit(10000)){throw 'Lightweight argument probe timed out.'}
        $stdout=$probeOutput.GetAwaiter().GetResult();$stderr=$probeError.GetAwaiter().GetResult()
        Check ($probe.ExitCode -eq 0) ('Actual pwsh argument probe failed: '+$stderr)
        # -NoExit can append a prompt to stdout; read the separate bounded receipt.
        $probeResult=Read-H1SmallJson $probeResultPath 16KB
        Check ($probeResult.Status -ceq 'Passed' -and $probeResult.HostImage -ceq $probeState.Contract.HostImage) 'Actual executable identity differs.'
        Check ([IO.Path]::GetFileName($probeResult.Arguments[0]) -ceq 'pwsh.dll') 'Expected installed pwsh managed argv[0] was not observed.'
        Check ($probeResult.Arguments[0] -cne $probeResult.HostImage) 'Probe no longer reproduces the original argv[0]/executable mismatch.'
        Check ($probeResult.Arguments.Count -eq $probeArguments.Count+1) 'Actual host argument count differs.'
        for($index=1;$index -lt $probeResult.Arguments.Count;$index++){
            Check ($probeResult.Arguments[$index] -ceq $probeArguments[$index-1]) ('Actual host argument differs at '+$index)
        }
        Check (!$probeResult.NativeTypesLoaded -and !$probeResult.HostStatePresent -and !(Test-Path -LiteralPath $probeState.RunRoot)) 'Argument probe touched runtime state.'
    }finally{
        # This is only the exact Process object created above, never a PID lookup.
        if($probeStarted -and !$probe.HasExited){$probe.Kill();if(!$probe.WaitForExit(5000)){throw 'Argument probe closure unconfirmed.'}}
        $probe.Dispose()
    }
    & {
        function Test-IW7ResourceIdentity($Expected,$Actual){$Expected.PID -eq $Actual.PID -and $Expected.Image -ceq $Actual.Image -and ([datetimeoffset]$Expected.CreatedUtc).UtcTicks -eq ([datetimeoffset]$Actual.CreatedUtc).UtcTicks}
        function Get-T7CatalogueBootstraps($Plan){$Plan.Bootstraps}
        function Read-H1SmallJson([string]$Path,[int]$Limit=128KB){
            if($Path.EndsWith('receipt.json')){return $script:receipt};if($Path.EndsWith('attempt.json')){return $script:attempt}
            if($Path.EndsWith('.host-start.json')){return $script:startProof};if($Path.EndsWith('.host-return.json')){return $script:returnProof}
            throw 'Unexpected read.'
        }
        function Get-IW7ResourceStatus {$script:status}
        function Get-IW7ResourceProcesses {$script:processes}
        function Get-T7CatalogueHostIdentity {$script:currentHost}
        function Assert-T7CatalogueMain($Plan){if($script:mainDrift){throw 'Main drift'};[pscustomobject]@{Baseline='Stopped'}}
        function Assert-T7CatalogueMetadata($Row){if($script:metadataDrift){throw 'Metadata drift'}}
        function Get-T7CatalogueFileId([string]$Path){if($script:idDrift){return 'wrong-id'};$script:fileIds[$Path]}
        function Write-T7CatalogueHostEvidence([string]$Path,$Value){if($script:writeFailure){throw 'Evidence publication failed'};$script:published.Add($Path)}
        $script:guardPath=Join-Path $temporary 'source.txt';[IO.File]::WriteAllText($script:guardPath,'frozen source')
        function Reset-Case {
            $previous=[AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost')
            if($previous){foreach($guard in $previous.Guards){$guard.Dispose()}}
            [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.'+('a'*32),$null)
            $hostIdentity=[pscustomobject]@{PID=100;CreatedUtc='2026-10-12T20:00:00Z';Image='C:\synthetic\pwsh.exe'}
            $runRoot=Join-Path $temporary 't7-catalog-synthetic';$work=Join-Path $runRoot 'work'
            $metadata=@('candidate','engine','steam','donor'|ForEach-Object {[pscustomobject]@{Path=(Join-Path $temporary $_);Bytes=1}})
            $plan=[pscustomobject]@{RunRoot=$runRoot;StageRoot=(Join-Path $runRoot 'evidence');WorkingDirectory=$work;
                Image=(Join-Path $work 't7-zonetool-candidate.exe');CandidateSource=$metadata[0].Path;EngineSource=$metadata[1].Path;
                SteamSource=$metadata[2].Path;Zone=[pscustomobject]@{Path=$metadata[3].Path;RelativePath='zone/donor.ff'};
                Bootstraps=@();InputMetadata=$metadata}
            $guardList=[Collections.Generic.List[object]]::new();$guardList.Add((Open-H1Pin (Pin $script:guardPath)))
            $script:state=[pscustomobject]@{Plan=$plan;PlanPath='C:\synthetic\plan.json';PlanSHA256=('b'*64);RunRoot=$runRoot;
                ContractPath='C:\synthetic\contract.json';ContractSHA256=('c'*64);EntryPath='C:\synthetic\Invoke-T7CatalogueHost.ps1';
                Host=$hostIdentity;Contract=[pscustomobject]@{HostImage=$hostIdentity.Image;PreservedProcesses=@([pscustomobject]@{PID=200;CreatedUtc='2026-10-11T10:00:00Z';Image='C:\synthetic\python.exe'})};
                Guards=$guardList;Phase='Returned';RunnerReturned=$true;RunnerReturnedUtc='2026-10-12T20:00:10Z';CanExit=$false;ClosureError=$null}
            $originals=@();$aliases=@();$script:fileIds=@{};$relative=@('t7-zonetool-candidate.exe','BlackOps3_UnrankedDedicatedServer.exe','steam_api64.dll','zone/donor.ff')
            for($index=0;$index -lt 4;$index++){
                $id='id-'+$index;$aliasPath=Join-Path $work $relative[$index]
                $originals+=,[pscustomobject]@{Path=$metadata[$index].Path;FileId=$id};$aliases+=,[pscustomobject]@{Path=$aliasPath;FileId=$id}
                $script:fileIds[$metadata[$index].Path]=$id;$script:fileIds[$aliasPath]=$id
            }
            $script:receipt=[pscustomobject]@{Schema='iw7.t7-catalogue-run/1';PlanSHA256=$script:state.PlanSHA256;
                TreeClosureConfirmed=$true;LeaseReleased=$true;InputsReverified=$true;OriginalInputMetadataUnchanged=$true;AliasesRetained=$true;Quarantined=$false;
                Identity=[pscustomobject]@{PID=300;Image=$plan.Image;CreatedUtc='2026-10-12T20:00:03Z'};LeaseToken=('a'*32);
                StartedUtc='2026-10-12T20:00:02Z';FinishedUtc='2026-10-12T20:00:09Z';InputFileIds=$originals;Aliases=$aliases;Status='Failed';CatalogueOutcome='NoCatalogue'}
            $script:attempt=[pscustomobject]@{Schema='iw7.t7-catalogue-attempt/1';PlanSHA256=$script:state.PlanSHA256;StartedUtc='2026-10-12T20:00:01Z'}
            $script:startProof=[pscustomobject]@{Host=$hostIdentity;PlanSHA256=$script:state.PlanSHA256;ContractSHA256=$script:state.ContractSHA256}
            $script:returnProof=[pscustomobject]@{Host=$hostIdentity;PlanSHA256=$script:state.PlanSHA256;ContractSHA256=$script:state.ContractSHA256;RunnerReturned=$true;RunnerReturnedUtc=$script:state.RunnerReturnedUtc}
            $script:currentHost=$hostIdentity;$script:status=[pscustomobject]@{Leases=@()}
            $script:processes=@([pscustomobject]@{PID=100;CreatedUtc=$hostIdentity.CreatedUtc;Image=$hostIdentity.Image;Name='pwsh.exe';Lab=$false},
                [pscustomobject]@{PID=200;CreatedUtc='2026-10-11T10:00:00Z';Image='C:\synthetic\python.exe';Name='python.exe';Lab=$false})
            $script:metadataDrift=$false;$script:idDrift=$false;$script:mainDrift=$false;$script:writeFailure=$false
            $script:published=[Collections.Generic.List[string]]::new()
            [AppDomain]::CurrentDomain.SetData('IW7.T7CatalogueHost',$script:state)
        }
        function Retained([string]$Why){Check (!$script:state.CanExit -and $script:state.Guards.Count -eq 1 -and !$script:state.Guards[0].SafeFileHandle.IsClosed) $Why}
        Reset-Case
        $result=Complete-T7CatalogueHost $script:state|ConvertFrom-Json
        Check ($result.CanExit -and $result.CatalogueOutcome -ceq 'NoCatalogue' -and !$result.ActualPTYExitObserved) 'Closed NoCatalogue must be safely closable, not a catalogue success.'
        Check ($script:state.Guards.Count -eq 0 -and $script:state.Phase -ceq 'Closed' -and $script:published.Count -eq 1) 'Wrapper guard disposal/publication differs.'
        Refuses {Complete-T7CatalogueHost $script:state} 'no re-entry'
        Check $script:state.CanExit 'Rejected duplicate Finish must preserve already proven CanExit.'
        Reset-Case
        $script:state.Plan|Add-Member NoteProperty Operation 'ResidentExportV1'
        $script:receipt.Schema='iw7.t7-resident-export-run/1';$script:receipt.PSObject.Properties.Remove('CatalogueOutcome')
        $script:receipt|Add-Member NoteProperty ExportOutcome 'NoExport'
        $script:attempt.Schema='iw7.t7-resident-export-attempt/1'
        $exportResult=Complete-T7CatalogueHost $script:state|ConvertFrom-Json
        Check ($exportResult.CanExit -and $exportResult.ExportOutcome -ceq 'NoExport' -and !$exportResult.PSObject.Properties['CatalogueOutcome']) 'Export host closure mislabeled or upgraded failure.'
        Check ($script:state.Guards.Count -eq 0) 'Export host retained closed guards.'
        foreach($version in @(1,2)){
            Reset-Case
            $script:state.Plan|Add-Member NoteProperty Operation 'ResidentExportV1'
            $script:state.Plan|Add-Member NoteProperty ResidentMultiSurfaceV2 ([pscustomobject]@{Schema='iw7.t7-resident-multi-surface/2'})
            $selector=if($version -eq 2){'SelectedStreamedRenderOnlyV2'}else{'SelectedStreamedStaticV1'}
            $schema=if($version -eq 2){'iw7.t7-selected-streamed-render-only-plan/2'}else{'iw7.t7-selected-streamed-export-plan/1'}
            $script:state.Plan|Add-Member NoteProperty $selector ([pscustomobject]@{Schema=$schema})
            $requestPath=Join-Path $temporary 'selected-request.json';$providerPath=Join-Path $temporary 'selected-provider.xpak'
            $script:state.Plan|Add-Member NoteProperty ExportRequestFile ([pscustomobject]@{Path=$requestPath})
            $script:state.Plan|Add-Member NoteProperty SelectedXpakProvider ([pscustomobject]@{Metadata=[pscustomobject]@{Path=$providerPath};RelativePath='zone/mp_initial.xpak'})
            $extraLinks=@(for($index=0;$index -lt 23;$index++){
                $path=Join-Path $temporary ('stream-bootstrap-'+$index+'.ff');$relative='zone/stream-bootstrap-'+$index+'.ff'
                $script:state.Plan.Bootstraps+=,[pscustomobject]@{Path=$path;RelativePath=$relative}
                ,@($path,$relative)
            })
            $extraLinks+=,@($requestPath,'streamed-request.json');$extraLinks+=,@($providerPath,'zone/mp_initial.xpak')
            for($index=0;$index -lt $extraLinks.Count;$index++){
                $path=$extraLinks[$index][0];$aliasPath=Join-Path $script:state.Plan.WorkingDirectory $extraLinks[$index][1];$id='stream-id-'+$index
                $script:state.Plan.InputMetadata+=,[pscustomobject]@{Path=$path;Bytes=1}
                $script:receipt.InputFileIds+=,[pscustomobject]@{Path=$path;FileId=$id}
                $script:receipt.Aliases+=,[pscustomobject]@{Path=$aliasPath;FileId=$id}
                $script:fileIds[$path]=$id;$script:fileIds[$aliasPath]=$id
            }
            $script:receipt.Schema='iw7.t7-resident-export-run/1';$script:receipt.PSObject.Properties.Remove('CatalogueOutcome')
            $script:receipt|Add-Member NoteProperty ExportOutcome 'NoExport';$script:attempt.Schema='iw7.t7-resident-export-attempt/1'
            Check ($script:state.Plan.InputMetadata.Count -eq 29) 'Streamed fixture must include 23 bootstrap and two selected aliases.'
            Assert-T7CatalogueHostReceiptIdentity $script:state $script:receipt;$checks++
            $savedId=$script:receipt.Aliases[-1].FileId;$script:receipt.Aliases[-1].FileId='wrong-provider-id'
            Refuses {Assert-T7CatalogueHostReceiptIdentity $script:state $script:receipt} 'alias identity'
            Retained 'Wrong selected provider identity released wrapper guards.'
            $script:receipt.Aliases[-1].FileId=$savedId
            $streamResult=Complete-T7CatalogueHost $script:state|ConvertFrom-Json
            Check ($streamResult.CanExit -and $streamResult.ExportOutcome -ceq 'NoExport' -and $script:state.Guards.Count -eq 0) 'Exact streamed aliases must permit closure without upgrading NoExport.'
        }
        foreach($extraCount in @(1,8,20)){
            Reset-Case
            for($index=0;$index -lt $extraCount;$index++){
                $path=Join-Path $temporary ('bootstrap-'+$index+'.ff');$relative='zone/bootstrap-'+$index+'.ff'
                $aliasPath=Join-Path $script:state.Plan.WorkingDirectory $relative;$id='bootstrap-id-'+$index
                $script:state.Plan.Bootstraps+=,[pscustomobject]@{Path=$path;RelativePath=$relative}
                $script:state.Plan.InputMetadata+=,[pscustomobject]@{Path=$path;Bytes=1}
                $script:receipt.InputFileIds+=,[pscustomobject]@{Path=$path;FileId=$id}
                $script:receipt.Aliases+=,[pscustomobject]@{Path=$aliasPath;FileId=$id}
                $script:fileIds[$path]=$id;$script:fileIds[$aliasPath]=$id
            }
            $variableResult=Complete-T7CatalogueHost $script:state|ConvertFrom-Json
            Check ($variableResult.CanExit -and $script:receipt.InputFileIds.Count -eq 4+$extraCount) 'Finalization embeds an attempt-specific item count.'
        }
        Reset-Case
        Refuses {[IO.File]::AppendAllText($script:guardPath,'drift')} 'being used|used by another|process cannot access'
        Retained 'Source write refusal released its guard.'
        foreach($field in @('TreeClosureConfirmed','LeaseReleased','InputsReverified','OriginalInputMetadataUnchanged','AliasesRetained')){
            Reset-Case;$script:receipt.$field=$false
            Refuses {Complete-T7CatalogueHost $script:state} 'closure proof';Retained ('Unproven '+$field+' disposed guards.')
        }
        foreach($case in @('plan','image','native-age','native-after-return','alias-path','alias-id','original-duplicate','quarantine','lease','native-pid-reuse','host-pid-reuse','preserved-pid-reuse','heavy','metadata','file-id','main','attempt','publication','start-proof','return-proof')){
            Reset-Case
            $pattern=switch($case){
                'plan' {$script:receipt.PlanSHA256='wrong';'another plan'}
                'image' {$script:receipt.Identity.Image='C:\wrong.exe';'native identity'}
                'native-age' {$script:receipt.Identity.CreatedUtc='2026-10-11T00:00:00Z';'lifetime'}
                'native-after-return' {$script:receipt.FinishedUtc='2026-10-12T20:00:11Z';'lifetime'}
                'alias-path' {$script:receipt.Aliases[0].Path='C:\wrong';'alias identity'}
                'alias-id' {$script:receipt.Aliases[0].FileId='wrong';'alias identity'}
                'original-duplicate' {$script:receipt.InputFileIds[1].FileId=$script:receipt.InputFileIds[0].FileId;'original identity'}
                'quarantine' {[AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.'+('a'*32),[object]::new());'quarantine remains'}
                'lease' {$script:status.Leases=@('occupied');'lease remains'}
                'native-pid-reuse' {$script:processes+=,[pscustomobject]@{PID=300;CreatedUtc='2026-10-12T21:00:00Z';Image='C:\other.exe';Name='other.exe';Lab=$false};'reused PID'}
                'host-pid-reuse' {$script:currentHost=[pscustomobject]@{PID=100;CreatedUtc='2026-10-12T21:00:00Z';Image='C:\synthetic\pwsh.exe'};'PID reuse'}
                'preserved-pid-reuse' {$script:processes[1].CreatedUtc='2026-10-12T21:00:00Z';'Preserved process'}
                'heavy' {$script:processes+=,[pscustomobject]@{PID=400;Image='C:\cl.exe';Name='cl.exe';Lab=$false};'Heavy process'}
                'metadata' {$script:metadataDrift=$true;'Metadata drift'}
                'file-id' {$script:idDrift=$true;'file identity changed'}
                'main' {$script:mainDrift=$true;'Main drift'}
                'attempt' {$script:attempt.PlanSHA256='wrong';'Attempt marker'}
                'publication' {$script:writeFailure=$true;'publication failed'}
                'start-proof' {$script:startProof.ContractSHA256='wrong';'start/return proof'}
                'return-proof' {$script:returnProof.RunnerReturned=$false;'return proof'}
            }
            Refuses {Complete-T7CatalogueHost $script:state} $pattern;Retained ('Failure disposed guards: '+$case)
            Check (!$script:state.CanExit) ('Failure granted exit: '+$case)
        }
        Reset-Case;$script:state.Guards[0].Dispose();Refuses {Complete-T7CatalogueHost $script:state} 'guard lost'
        Check (!$script:state.CanExit) 'Lost source guard must block exit.'
        Reset-Case;$script:state.Guards[0].Dispose();$script:state.Guards.Clear()
        $brokenGuard=[pscustomobject]@{SafeFileHandle=[pscustomobject]@{IsClosed=$false}}
        $brokenGuard|Add-Member ScriptMethod Dispose {throw 'Disposal failed'}
        $script:state.Guards.Add($brokenGuard)
        Refuses {Complete-T7CatalogueHost $script:state} 'Disposal failed';Retained 'Disposal failure granted exit.'
        Check ($script:published.Count -eq 1) 'Disposal scenario did not reach published postflight.'
        $script:state.Guards.Clear()
        Reset-Case;$script:state.RunnerReturned=$false;Refuses {Complete-T7CatalogueHost $script:state} 'returned host';Retained 'Active runner guard lost.'
        Reset-Case
        $argsExact=@($script:state.Contract.HostImage,'-NoLogo','-NoProfile','-NoExit','-File',$script:state.EntryPath,'-PlanPath',$script:state.PlanPath,
            '-PlanSHA256',$script:state.PlanSHA256,'-RunRoot',$script:state.RunRoot,'-HostContractPath',$script:state.ContractPath,'-HostContractSHA256',$script:state.ContractSHA256,'-Run')
        Assert-T7CatalogueHostArguments $script:state $argsExact $script:currentHost;Check $true 'Exact arguments refused.'
        $argsManaged=$argsExact.Clone();$argsManaged[0]='C:\synthetic\pwsh.dll'
        Assert-T7CatalogueHostArguments $script:state $argsManaged $script:currentHost;Check $true 'Managed argv[0] refused.'
        $wrongImage=[pscustomobject]@{PID=$script:currentHost.PID;CreatedUtc=$script:currentHost.CreatedUtc;Image='C:\other\pwsh.exe'}
        Refuses {Assert-T7CatalogueHostArguments $script:state $argsManaged $wrongImage} 'NoProfile/NoExit'
        Refuses {Assert-T7CatalogueHostArguments $script:state ($argsManaged+@('extra')) $script:currentHost} 'NoProfile/NoExit'
        for($index=1;$index -lt $argsManaged.Count;$index++){
            $changed=$argsManaged.Clone();$changed[$index]='wrong'
            Refuses {Assert-T7CatalogueHostArguments $script:state $changed $script:currentHost} 'NoProfile/NoExit'
        }
        $argsBad=$argsExact.Clone();$argsBad[3]='-NonInteractive';Refuses {Assert-T7CatalogueHostArguments $script:state $argsBad $script:currentHost} 'NoProfile/NoExit'
        $argsBad=$argsExact.Clone();$argsBad[7]='C:\other-plan.json';Refuses {Assert-T7CatalogueHostArguments $script:state $argsBad $script:currentHost} 'NoProfile/NoExit'
        Close-T7CatalogueHostGuards $script:state;[AppDomain]::CurrentDomain.SetData('IW7.T7CatalogueHost',$null)
    }
    # Run the default entry end-to-end against small synthetic source fixtures.
    # Its stub runner rejects -Run, so a default-path regression cannot start anything.
    $fakeRepo=Join-Path $temporary 'repo';$bridge=Join-Path $fakeRepo 'tools-source/asset-bridge/t7-bridge'
    foreach($directory in @($bridge,(Join-Path $fakeRepo 'tools-source/asset-bridge/h1-fixture'),(Join-Path $fakeRepo 'ops'),(Join-Path $fakeRepo 'runtime'))){$null=[IO.Directory]::CreateDirectory($directory)}
    $entry=Join-Path $bridge 'Invoke-T7CatalogueHost.ps1';$core=Join-Path $bridge 'T7CatalogueHost.Core.ps1';$h1=Join-Path $fakeRepo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1'
    [IO.File]::Copy((Join-Path $PSScriptRoot 'Invoke-T7CatalogueHost.ps1'),$entry)
    [IO.File]::Copy((Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1'),$core)
    [IO.File]::Copy((Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1'),$h1)
    $runner=Join-Path $bridge 'Run-T7Catalogue.ps1'
    [IO.File]::WriteAllText($runner,'param($PlanPath,$PlanSHA256,[switch]$Run); if($Run){throw "Synthetic runner forbids runtime"}; ''{"Status":"PlanCheckedPendingGO"}''')
    $dependencyPaths=@($runner,$h1,(Join-Path $fakeRepo 'ops/Resource-Scheduler.Core.ps1'),(Join-Path $fakeRepo 'ops/Resource-Memory.ps1'),
        (Join-Path $fakeRepo 'ops/Resource-RecorderOwnedProcess.Core.ps1'),(Join-Path $bridge 'T7Prepatch.Profile.ps1'),(Join-Path $bridge 'T7Catalogue.Profile.ps1'))
    foreach($path in $dependencyPaths|Where-Object {!(Test-Path -LiteralPath $_)}){[IO.File]::WriteAllText($path,'# synthetic source')}
    $runRoot=Join-Path $fakeRepo 'runtime/t7-catalog-test';$planPath=Join-Path $fakeRepo 'runtime/plan.json';$contractPath=Join-Path $fakeRepo 'runtime/host.json'
    $bindings=@(foreach($path in $dependencyPaths){$pin=Pin $path;$pin|Add-Member NoteProperty IsText $true;$pin})
    $plan=[ordered]@{Runner=$runner;RunRoot=$runRoot;StageRoot=(Join-Path $runRoot 'evidence');Bindings=$bindings}
    [IO.File]::WriteAllText($planPath,($plan|ConvertTo-Json -Depth 8))
    $contract=[ordered]@{Schema='iw7.t7-catalogue-host/1';PlanPath=$planPath;PlanSHA256=(Pin $planPath).SHA256;RunRoot=$runRoot;
        HostImage=[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName;SourcePins=@((Pin $entry),(Pin $core),(Pin $h1));PreservedProcesses=@()}
    [IO.File]::WriteAllText($contractPath,($contract|ConvertTo-Json -Depth 8))
    $parameters=@{PlanPath=$planPath;PlanSHA256=$contract.PlanSHA256;RunRoot=$runRoot;HostContractPath=$contractPath;HostContractSHA256=(Pin $contractPath).SHA256}
    $result=& $entry @parameters|ConvertFrom-Json
    Check ($result.Status -ceq 'PlanCheckedPendingGO') 'Default entry failed synthetic source validation.'
    Check (!(Test-Path -LiteralPath $runRoot) -and !(Test-Path -LiteralPath ($runRoot+'.host-start.json'))) 'Default created runtime evidence.'
    Check ($null -eq [AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost')) 'Default consumed a persistent host.'
    Check (!(('IW7HudFileIdentity' -as [type]) -or ('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]))) 'Default/tests loaded native runtime types.'
    Refuses {& $entry @parameters -Run} 'NoProfile/NoExit'
    Check ($null -eq [AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost')) 'Rejected arguments consumed host.'
    [IO.File]::AppendAllText($core,'# source drift')
    Refuses {& $entry @parameters} 'Bound input length differs'
    [IO.File]::WriteAllText(($runRoot+'.host-start.json'),'{}')
    Refuses {& $entry @parameters -Run} 'RunRoot retry'
    [AppDomain]::CurrentDomain.SetData('IW7.T7CatalogueHost',[pscustomobject]@{Consumed=$true})
    Refuses {& $entry @parameters -Run} 'no Run re-entry'
    [AppDomain]::CurrentDomain.SetData('IW7.T7CatalogueHost',$null)
    [ordered]@{Status='Passed';Checks=$script:checks;SyntheticLifecycle=$true;ActualPwshArgumentProbe=$true;NativeRun=$false;NativeTypesLoaded=$false;LeaseAcquired=$false}|ConvertTo-Json
}finally{
    $left=[AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost')
    if($left -and $left.PSObject.Properties['Guards']){foreach($guard in $left.Guards){$guard.Dispose()}}
    [AppDomain]::CurrentDomain.SetData('IW7.T7CatalogueHost',$null)
    [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.'+('a'*32),$null)
    # Keep only this test's resolved temporary tree eligible for cleanup.
    $resolved=[IO.Path]::GetFullPath($temporary);$tempRoot=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($tempRoot,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-host-tests-[0-9a-f]{32}$'){throw 'Unsafe test cleanup path.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
