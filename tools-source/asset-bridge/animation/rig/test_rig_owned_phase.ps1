# Execute the real orchestration function with mocked native/scheduler adapters.
# No source rewrite, Add-Type, compiler, real process or lease is used.
$ErrorActionPreference='Stop'
. "$PSScriptRoot/Rig.Core.ps1"
. "$PSScriptRoot/Rig.Compiler.ps1"
. "$PSScriptRoot/../AnimationFF.Core.ps1"
$rigRoot=$PSScriptRoot
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Build-RigChain.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner syntax failed'}
$function=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Invoke-RigPhase'},$true))
if($function.Count -ne 1){throw 'One real phase orchestrator required'}
. ([scriptblock]::Create($function[0].Extent.Text))
$checks=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuse([scriptblock]$Body){$caught=$false;try{& $Body|Out-Null}catch{$caught=$true};Check $caught 'Failure fixture accepted'}
function Get-RigMonotonicMs {$script:tick}
function Start-Sleep {param($Milliseconds) $script:tick+=$Milliseconds}
function Assert-RigRunningBudget {if($script:mode -ceq 'budget' -and $script:owner -and $script:owner.Resumed){throw 'Mock stop requested'}}
function Save-RigState {}
function Assert-RigToolchainInventory($Expected,$Roots) {}
function Assert-RigBaselines($Values) {}
function Assert-BeaconHash($Path,$Hash) {if($Hash.Length -ne 64){throw 'Mock hash malformed'}}
function Read-BeaconJson($Path){[IO.File]::ReadAllText($Path)|ConvertFrom-Json}
function Add-RigGuard($Path,$Expected,$Guards,$Baselines){
    if((Get-FileHash -LiteralPath $Path).Hash -ine $Expected){throw 'Real created spec hash differs'}
    $script:spec=Read-BeaconJson $Path;$script:specHash=$Expected
}
function Get-BeaconJobIdentity($Owner,$ExpectedImage,$Phase){
    Check (!$Owner.Resumed -and $Owner.Image -ceq $ExpectedImage) 'Original identity must be read before Resume'
    [ordered]@{Phase=$Phase;PID=$Owner.PID;Image=$Owner.Image;CreatedUtc=$Owner.CreatedUtc;Priority=0x4000;JobActiveAtClose=$null;ExitCode=$null}
}
function Add-IW7ResourceProcess {param($Token,$ProcessId)
    Check ($script:owner.Resumed -and $Token -ceq 'mock-lease' -and $ProcessId -eq 36) 'Registration must follow Resume of original owner'
    if($script:mode -ceq 'registration'){throw 'Mock unrelated registration refusal'}
    $script:owner.Exited=$true;$script:owner.Active=1
}
function Get-RigOriginalJobMembers($Owner){
    Check ([object]::ReferenceEquals($Owner,$script:owner)) 'Observer must borrow the exact original job'
    $member=if(!$Owner.Exited){
        [pscustomobject]@{PID=37;ParentPID=36;Image=$policy.Compiler;CreatedUtc='2026-10-12T04:00:00.1000000Z';InOriginalJob=$true;Error=$null;ParentError=$null}
    }elseif($Owner.Active){
        [pscustomobject]@{PID=38;ParentPID=37;Image=$policy.Telemetry;CreatedUtc='2026-10-12T04:00:00.2000000Z';InOriginalJob=$true;Error=$null;ParentError=$null}
    }else{$null}
    [pscustomobject]@{Members=@($member|Where-Object {$null -ne $_});AssignedCount=$Owner.Active;ListedCount=$Owner.Active;CapturedUtc='2026-10-12T04:00:01.0000000Z'}
}
function New-RigOwnedJob($Python,$Arguments,$Work){
    Check (!$script:closed) 'Factory entry must already be closure-unknown'
    if($script:mode -ceq 'factory'){throw 'Mock partial factory failure'}
    Check ($Arguments.StartsWith('"-I" "-B"') -and $Work -ceq $script:runRoot) 'Isolated exact Python command and working directory'
    $job=[pscustomobject]@{PID=36;Image=$Python;CreatedUtc='2026-10-12T04:00:00.0000000Z';Priority=0x4000;
        Exited=$false;Active=1;ExitCode=0;Resumed=$false;Disposed=$false;Stops=0}
    $job|Add-Member ScriptMethod Resume {
        if($script:mode -ceq 'resume'){throw 'Mock Resume failed'}
        $this.Resumed=$true
        if(Test-Path -LiteralPath $script:spec.logs){throw 'Mock phase refuses existing log directory'}
        [IO.Directory]::CreateDirectory($script:spec.logs)|Out-Null
        Write-RigNewText 'mocked phase stdout' (Join-Path $script:spec.logs 'stdout.log')
        $receipt=[ordered]@{schema='iw7.rig-chain-phase-result/1';phase=$script:spec.phase;spec_sha256=$script:specHash;
            executable_sha256=$script:spec.sha256;pid=37;exit_code=0;failure=$null;log_limit_each=2MB;ownership='outer original Windows job'}
        if($script:mode -ceq 'receipt'){$receipt.spec_sha256='0'*64}
        if($script:mode -cin @('launch-error','unbound-error')){
            $this.ExitCode=2
            Write-RigNewJson ([ordered]@{schema='iw7.rig-chain-launch-error/1';phase=$script:spec.phase;spec_sha256=$script:specHash;
                root_pid=$(if($script:mode -ceq 'unbound-error'){99}else{$this.PID});error_type='ValueError';error='initial distinct bootstrap error'}) (Join-Path $script:runRoot ($script:spec.phase+'.spec.launch-error.json'))
        }elseif($script:mode -ceq 'no-receipt'){$this.ExitCode=1}
        else{Write-RigNewJson $receipt (Join-Path $script:spec.logs 'phase.json')}
        if($script:mode -cin @('telemetry','registration')){$this.Active=2}
        else{$this.Exited=$true;$this.Active=0}
    }
    $job|Add-Member ScriptMethod Stop {$this.Stops++;$this.Exited=$true;$this.Active=0}
    $job|Add-Member ScriptMethod Dispose {if(!$this.Exited -or $this.Active){throw 'Disposed live owner'};$this.Disposed=$true}
    $script:lastOwner=$job
    return $job
}
$tempRoot=Join-Path ([IO.Path]::GetTempPath()) ('iw7-rig-phase-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($tempRoot)|Out-Null
try{
    foreach($case in 'normal','telemetry','ff-build','factory','resume','receipt','registration','budget','launch-error','unbound-error','no-receipt'){
        $script:mode=$case;$script:tick=0;$script:owner=$null;$script:lastOwner=$null;$script:closed=$true
        $script:runRoot=Join-Path $tempRoot $case;[IO.Directory]::CreateDirectory($script:runRoot)|Out-Null
        $name=if($case -cin @('telemetry','registration')){'compile'}elseif($case -ceq 'ff-build'){'build'}else{'read-native'}
        $group=if($case -ceq 'ff-build'){'ff'}else{'native'}
        if($case -ceq 'ff-build'){
            [IO.Directory]::CreateDirectory((Join-Path $script:runRoot 'build/tmp'))|Out-Null
            Write-RigNewText 'retained compiler artifact' (Join-Path $script:runRoot 'build/writer.obj')
        }
        $policy=Get-RigCompilerPolicy 'C:\mock\cl.exe'
        $plan=[pscustomobject]@{python=[pscustomobject]@{path='C:\mock\python.exe'};phases=@([pscustomobject]@{
            id=$name;group=$group;command=@('C:\mock\child.exe','literal value');working_directory=$script:runRoot})}
        $recipe=[pscustomobject]@{freeze_roots=@()};$toolchain=@();$baselines=@();$guards=@();$environment=@{}
        $bindings=@{'sdk/modding/beacon_tool_phase.py'=[pscustomobject]@{Path='C:\mock\bounded.py'}}
        $lease=[pscustomobject]@{Token='mock-lease'};$state=[ordered]@{Phases=@()}
        $hash=if($name -ceq 'compile'){$policy.CompilerSHA256}else{'a'*64}
        if($case -cin @('normal','telemetry','ff-build')){
            $output=Invoke-RigPhase $name $hash
            Check ($output -ceq 'mocked phase stdout' -and $script:closed -and !$script:owner -and $script:lastOwner.Disposed) 'Successful phase requires disposed closed owner'
            Check ($state.Phases.Count -eq 1 -and $state.Phases[0].JobActiveAtClose -eq 0 -and $state.Phases[0].ReceiptSHA256.Length -eq 64) 'Exact phase closure and receipt are retained'
            if($case -ceq 'telemetry'){
                Check ($script:lastOwner.Stops -eq 1 -and $state.Phases[0].CompilerClosure.Completed -and $state.Phases[0].Supervision.PollCount -eq 2) 'Real phase orchestration re-samples after the accepted original-job telemetry stop'
            }
            if($case -ceq 'ff-build'){
                Check ($script:spec.logs -ceq (Join-Path $script:runRoot 'logs/build') -and
                    [IO.File]::ReadAllText((Join-Path $script:runRoot 'build/writer.obj')) -ceq 'retained compiler artifact') 'Populated compiler build directory must remain distinct from fresh FF logs'
            }
        }else{
            if($case -cin @('launch-error','unbound-error','no-receipt')){
                $caught=$null;try{Invoke-RigPhase $name $hash|Out-Null}catch{$caught=$_.Exception.Message}
                if($case -ceq 'launch-error'){
                    Check ($caught -ceq 'Rig phase read-native exited 2 without phase.json. Bootstrap ValueError: initial distinct bootstrap error') 'Missing phase.json must retain original bootstrap error and root exit'
                }elseif($case -ceq 'unbound-error'){
                    Check ($caught.StartsWith('Rig phase read-native exited 2 without phase.json. Unbound launch-error receipt preserved at ') -and !$caught.Contains('initial distinct bootstrap error')) 'Unbound failure text cannot replace original-root evidence'
                }else{
                    Check ($caught -ceq 'Rig phase read-native exited 1 without phase.json. No launch-error receipt is available; preserve original root and phase evidence.') 'Missing both receipts must still retain root exit and phase context'
                }
            }else{Refuse {Invoke-RigPhase $name $hash}}
            if($case -cin @('receipt','launch-error','unbound-error','no-receipt')){Check ($script:closed -and !$script:owner) 'Invalid/missing receipt fails even after confirmed closure'}
            elseif($case -ceq 'factory'){Check (!$script:closed -and !$script:owner) 'Factory without owner stays unknown and quarantinable'}
            else{
                Check (!$script:closed -and $script:owner -and !$script:owner.Disposed) 'Incomplete phase retains exact owner for finalizer'
                $evidence=[ordered]@{};Check (Stop-RigOwnedPhase $script:owner $evidence) 'Mock finalizer can close only original owner'
                $script:owner.Dispose()
            }
        }
    }
}finally{
    $resolved=[IO.Path]::GetFullPath($tempRoot);$base=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if(!$resolved.StartsWith($base,[StringComparison]::OrdinalIgnoreCase) -or (Split-Path $resolved -Leaf) -notlike 'iw7-rig-phase-tests-*'){throw 'Unexpected test cleanup root'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
Check (!('IW7.AnimationRig.JobMembers' -as [type]) -and !('IW7.CommunityBuild.BuildJob' -as [type])) 'Native helpers must remain unloaded'
"PASS: $checks real phase orchestration checks with mocked ownership/admission; no process or lease execution."
