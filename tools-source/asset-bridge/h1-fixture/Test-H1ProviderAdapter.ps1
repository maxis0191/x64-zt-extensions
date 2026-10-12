# Execute the real PowerShell bridge with mocked handles/method objects only.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'H1Native.Compiler.ps1')
$checks=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Body){$caught=$false;try{& $Body|Out-Null}catch{$caught=$true};Check $caught 'Native provider bridge failure was ignored.'}
function New-Handle {
    $handle=[pscustomobject]@{References=0;Releases=0;FailRetain=$false}
    $handle|Add-Member ScriptMethod DangerousAddRef {param($held) if($this.FailRetain){throw 'retain failed'};$this.References++;$held.Value=$true}
    $handle|Add-Member ScriptMethod DangerousRelease {$this.Releases++}
    $handle
}
function Reset-Bridge {
    $script:job=New-Handle;$script:process=New-Handle;$script:rootExited=$true;$script:active=[uint32]1
    $script:exitOkay=$true;$script:stopOkay=$true;$script:exitCalls=0;$script:stopCalls=0
    $script:owner=[pscustomobject]@{PID=37;Image='C:\toolset\cl.exe';CreationFileTime=([datetime]'2026-10-12T04:00:00Z').ToFileTimeUtc()}
}
function Get-H1OriginalHandle($Owner,$Name){if($Name -ceq 'job'){$script:job}else{$script:process}}
function Get-H1PrivateMethod($Owner,$Name,[switch]$Static) {
    $method=[pscustomobject]@{Name=$Name;Static=[bool]$Static}
    $method|Add-Member ScriptMethod Invoke {
        param($target,$arguments)
        switch($this.Name) {
            'RootExited' {if($this.Static){throw 'wrong mode'};return $script:rootExited}
            'ActiveProcesses' {if($this.Static){throw 'wrong mode'};return $script:active}
            'GetExitCodeProcess' {
                if(!$this.Static -or ![object]::ReferenceEquals($arguments[0],$script:process)){throw 'wrong original process'}
                $script:exitCalls++;$arguments[1]=[uint32]0;return $script:exitOkay
            }
            'TerminateJobObject' {
                if(!$this.Static -or ![object]::ReferenceEquals($arguments[0],$script:job) -or $arguments[1] -ne [uint32]3758096385){throw 'wrong original job or stop code'}
                $script:stopCalls++;return $script:stopOkay
            }
            default {throw 'unexpected method'}
        }
    }
    $method
}
Reset-Bridge
$sample=Get-H1OriginalState $script:owner
Check ($sample.RootExited -is [bool] -and $sample.RootExited -and $sample.RootExitCode -is [uint32] -and $sample.RootExitCode -eq 0 -and $sample.ActiveProcesses -eq 1) 'Bridge lost typed original exit/accounting.'
Check ($sample.PID -eq 37 -and $sample.CreatedUtc -ceq '2026-10-12T04:00:00.0000000Z') 'Bridge changed original process generation.'
Check ($script:job.References -eq 1 -and $script:job.Releases -eq 1 -and $script:process.References -eq 1 -and $script:process.Releases -eq 1) 'Borrowed query handles leaked.'
Reset-Bridge;$script:rootExited=$false
$sample=Get-H1OriginalState $script:owner
Check (!$sample.RootExited -and $null -eq $sample.RootExitCode -and $script:exitCalls -eq 0) 'Live root must not invent exit0.'
Reset-Bridge;$script:exitOkay=$false
Refuses {Get-H1OriginalState $script:owner}
Check ($script:job.Releases -eq 1 -and $script:process.Releases -eq 1) 'Query failure leaked borrowed handles.'
Reset-Bridge;$script:process.FailRetain=$true
Refuses {Get-H1OriginalState $script:owner}
Check ($script:job.Releases -eq 1 -and $script:process.Releases -eq 0) 'Partial retain failure released an unheld handle or leaked job.'
Reset-Bridge
Stop-H1OriginalJob $script:owner
Check ($script:stopCalls -eq 1 -and $script:job.References -eq 1 -and $script:job.Releases -eq 1 -and $script:process.References -eq 0) 'Stop did not target only the protected original job.'
Reset-Bridge;$script:stopOkay=$false
Refuses {Stop-H1OriginalJob $script:owner}
Check ($script:job.Releases -eq 1) 'Stop failure leaked borrowed job handle.'
Check (!(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7.H1Diagnostics.JobMembers' -as [type]))) 'Bridge source tests loaded native types.'
[ordered]@{Schema='iw7.h1-provider-adapter-source-tests/1';Assertions=$checks;RealHandlesTested=$false;NativeTypesLoaded=$false;NativeCalls=$false}|ConvertTo-Json
