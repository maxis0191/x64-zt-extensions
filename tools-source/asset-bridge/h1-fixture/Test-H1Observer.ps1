[CmdletBinding()]
param([Parameter(Mandatory)][string]$MaterialObserverSource)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$checks=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
Check ((Get-FileHash -LiteralPath $MaterialObserverSource).Hash -ieq 'c8fce6094104eae70442a081654f403739f5315d531c35385021759b74c2abda') 'Reviewed MaterialV2 observer source required.'
$baseline=(Get-Content -LiteralPath $MaterialObserverSource -Raw).Replace("`r`n","`n")
$cs=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'H1Native.JobMembers.cs') -Raw).Replace("`r`n","`n")
function MemberBody([string]$Value) {
    $start=$Value.IndexOf('    static QueryBasic OptionalParentQuery()')
    $end=$Value.IndexOf('    public static Observation Capture(', $start)
    if($start -lt 0 -or $end -le $start){throw 'Observer markers changed.'}
    $Value.Substring($start,$end-$start)
}
Check ((MemberBody $cs) -ceq (MemberBody $baseline)) 'Production observer parent/member query must remain byte-identical.'
# Bundled managed Roslyn diagnoses source only. No Emit, Add-Type, helper load,
# native call, process launch or resource admission occurs here.
$null=[Reflection.Assembly]::LoadFrom((Join-Path $PSHOME 'Microsoft.CodeAnalysis.dll'))
$null=[Reflection.Assembly]::LoadFrom((Join-Path $PSHOME 'Microsoft.CodeAnalysis.CSharp.dll'))
$tree=[Microsoft.CodeAnalysis.CSharp.CSharpSyntaxTree]::ParseText($cs)
$references=@([AppContext]::GetData('TRUSTED_PLATFORM_ASSEMBLIES') -split [IO.Path]::PathSeparator|ForEach-Object {[Microsoft.CodeAnalysis.MetadataReference]::CreateFromFile($_)})
$options=[Microsoft.CodeAnalysis.CSharp.CSharpCompilationOptions]::new([Microsoft.CodeAnalysis.OutputKind]::DynamicallyLinkedLibrary)
$analysis=[Microsoft.CodeAnalysis.CSharp.CSharpCompilation]::Create('H1JobMembersSourceAnalysis',
    [Microsoft.CodeAnalysis.SyntaxTree[]]@($tree),[Microsoft.CodeAnalysis.MetadataReference[]]$references,$options)
$errors=@($analysis.GetDiagnostics()|Where-Object Severity -EQ Error)
Check (!$errors.Count) ('C# semantic diagnostics: '+($errors -join '; '))
Check ($cs -notmatch '\b(TerminateProcess|TerminateJobObject|CreateProcess|CreateJobObject|AssignProcessToJobObject|SetInformationJobObject|WriteProcessMemory|ReadProcessMemory|CloseHandle)\b') 'Observer must not own, kill, assign or inspect process memory.'
Check ($cs.Contains('OpenProcess(0x1000, false, pid)') -and $cs.Contains('IsProcessInJob(process, job, out member)')) 'Limited query and exact job membership required.'
Check ($cs.Contains('Capacity = 64') -and $cs.Contains('listed != assigned') -and $cs.Contains('returned > bytes')) 'Bounded complete PID list required.'
Check ($cs.Contains('field.FieldType != typeof(SafeFileHandle)') -and $cs.Contains('IW7.AnimationProbe.NativeJob')) 'Pinned NativeJob/SafeFileHandle adapter required.'
Check ($cs.Contains('borrowed.DangerousAddRef(ref retained)') -and $cs.Contains('if(retained) borrowed.DangerousRelease()')) 'Synchronous borrowed handle lifetime must be protected.'
$compiler=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'H1Native.Compiler.ps1') -Raw
Check ($compiler -notmatch 'DllImport|Stop-Process|taskkill|TerminateProcess|GetProcessById') 'Closure must reuse original provider, never introduce PID termination.'
Check ($compiler.Contains('Get-H1PrivateMethod $Owner TerminateJobObject -Static') -and $compiler.Contains('Assert-H1Deadline $Started $State.DeadlineSeconds')) 'Existing original-job stop and original deadline required.'
$runner=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Run-H1Native.ps1') -Raw
Check ($runner.IndexOf('Enter-IW7ResourceLease') -lt $runner.IndexOf('Add-Type -LiteralPath $plan.ObserverSource')) 'Observer native type can only load after full admission.'
Check (!(('IW7.H1Diagnostics.JobMembers' -as [type]) -or ('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]))) 'Observer source checks must not load native helper types.'
[ordered]@{Schema='iw7.h1-native-observer-source-tests/1';Assertions=$checks;SemanticErrors=$errors.Count;
    AssemblyEmitted=$false;NativeHelperLoaded=$false;NativeCalls=$false;LeaseAcquired=$false}|ConvertTo-Json
