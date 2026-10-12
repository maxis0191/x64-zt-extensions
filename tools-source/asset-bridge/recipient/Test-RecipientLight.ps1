# Pure identity fixtures; no real process observation or native launch.
$ErrorActionPreference='Stop'
$checks=0
function Check([bool]$Value,[string]$Name){if(!$Value){throw $Name};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Name){$failed=$false;try{& $Action|Out-Null}catch{$failed=$true};Check $failed $Name}
$path=Join-Path $PSScriptRoot 'Recipient.Light.ps1';$errors=$null;$tokens=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
Check ($errors.Count -eq 0) 'Light helpers parse'
Check (@($ast.EndBlock.Statements|Where-Object {$_ -isnot [Management.Automation.Language.FunctionDefinitionAst]}).Count -eq 0) 'Import is pure'
$mutators=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -in @('Add-Type','Start-Process','Stop-Process','Enter-IW7ResourceLease','Write-Output')},$true))
Check ($mutators.Count -eq 0) 'Observer does not compile, launch, kill or reserve'
. $path
$plan=@{Work='C:\fixture\work';PythonExe='C:\fixture\python.exe';Phases=@('references');Candidate=@{SHA256='e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04'}}
$phase=@{Phase='references';PID=100;Image=$plan.PythonExe;CreatedUtc='2026-10-12T05:00:00.0000001Z'}
$locator=@{phase='references';pid=101;parent_pid=100;image='C:\fixture\work\zonetool.exe';executable_sha256=$plan.Candidate.SHA256;spawn_observed_utc='2026-10-12T05:00:01.0100000Z'}
$parent=@{PID=100;Image=$plan.PythonExe;CreatedUtc='2026-10-12T05:00:00.0000000Z'}
$child=@{PID=101;ParentPID=100;Image=$locator.image;CreatedUtc='2026-10-12T05:00:01.0000000Z'}
Assert-RecipientLightIdentity $plan $phase $locator $parent $child $null;$checks++
$expected=$child.Clone()
Assert-RecipientLightIdentity $plan $phase $locator $parent $child $expected;$checks++
foreach($change in @(@{PID=102},@{ParentPID=99},@{Image='C:\other\zonetool.exe'},@{CreatedUtc='2026-10-12T05:00:00.5000000Z'},@{CreatedUtc=$null})){
    $altered=$child.Clone();foreach($key in $change.Keys){$altered[$key]=$change[$key]}
    Refuses {Assert-RecipientLightIdentity $plan $phase $locator $parent $altered $expected} 'Changed native identity refuses'
}
$altered=$parent.Clone();$altered.CreatedUtc='2026-10-12T05:00:00.0010000Z'
Refuses {Assert-RecipientLightIdentity $plan $phase $locator $altered $child $null} 'Reused parent PID refuses'
$altered=$child.Clone();$altered.CreatedUtc='2026-10-12T05:00:02.0000000Z'
Refuses {Assert-RecipientLightIdentity $plan $phase $locator $parent $altered $null} 'Child later than locator refuses'
$plan.Phases=@('references','script')
Refuses {Assert-RecipientLightIdentity $plan $phase $locator $parent $child $null} 'Light probe requires explicit references-only plan'
"$checks pure light-observation checks passed; no process queried."
