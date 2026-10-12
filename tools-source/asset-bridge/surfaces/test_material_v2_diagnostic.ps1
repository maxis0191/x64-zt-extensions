# Read-only source analysis and mocked byte/observation tests. No Add-Type/Emit,
# P/Invoke, child launch, resource lease or compiler execution.
$ErrorActionPreference='Stop'
$checks=0
function Assert([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuse([scriptblock]$Action){$caught=$false;try{& $Action|Out-Null}catch{$caught=$true};Assert $caught 'Expected refusal'}
$tokens=$null;$errors=$null
$path=Join-Path $PSScriptRoot 'Diagnose-MaterialV2Compile.ps1'
$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
Assert (!$errors.Count) 'Diagnostic runner parse'
foreach($name in 'Write-MaterialDiagnosticLine','Save-MaterialJobObservation'){
    $function=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true)
    Assert ($null -ne $function) "Missing function: $name"
    . ([scriptblock]::Create($function.Extent.Text))
}
$stream=[IO.MemoryStream]::new()
try{
    Write-MaterialDiagnosticLine $stream @{Image='C:\é\tool.exe';PID=37}
    $row=[Text.Encoding]::UTF8.GetString($stream.ToArray())|ConvertFrom-Json
    Assert ($row.PID -eq 37 -and $row.Image -ceq 'C:\é\tool.exe') 'UTF8 evidence preserved'
    $stream.SetLength(2MB-1);$stream.Position=$stream.Length;$before=$stream.Length
    Refuse {Write-MaterialDiagnosticLine $stream @{Image='é'}}
    Assert ($stream.Length -eq $before) 'Diagnostic byte overflow refused before write'
}finally{$stream.Dispose()}
function Read-MaterialJobObservation($Owner){
    if($Owner -cne 'same-owned-job'){throw 'Mock wrong owner'}
    [pscustomobject]@{ListedCount=1;Members=@([pscustomobject]@{PID=37;InOriginalJob=$true;Image='C:\compiler-child.exe';CreatedUtc='2026-10-12T04:00:00.0000000Z';ParentPID=36;Error=$null})}
}
$stream=[IO.MemoryStream]::new();$state=[ordered]@{LastJobObservation=$null;JobObservations=0;DiagnosticError=$null}
try{
    $sample=@{RootExited=$true;ActiveProcesses=1;RootExitCode=0;ElapsedMs=3900}
    Save-MaterialJobObservation 'same-owned-job' $sample 'SupervisionPoll' $stream $state
    Assert ($state.JobObservations -eq 1 -and $state.LastJobObservation.Job.Members[0].ParentPID -eq 36) 'Exact observed parent/image captured'
    Assert ($state.LastJobObservation.Supervision.ActiveProcesses -eq 1) 'Residual count retained independently of native receipt'
    Refuse {Save-MaterialJobObservation 'wrong-owner' $sample 'SupervisionPoll' $stream $state}
    Assert ($state.DiagnosticError -ceq 'Mock wrong owner' -and $state.JobObservations -eq 1) 'Diagnostic failure remains explicit'
}finally{$stream.Dispose()}
# Existing bundled Roslyn parses and performs semantic diagnostics only. No Emit
# and no load or execution of this new C# helper occurs in this test.
$null=[Reflection.Assembly]::LoadFrom((Join-Path $PSHOME 'Microsoft.CodeAnalysis.dll'))
$null=[Reflection.Assembly]::LoadFrom((Join-Path $PSHOME 'Microsoft.CodeAnalysis.CSharp.dll'))
$cs=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'MaterialV2.JobMembers.cs') -Raw
$tree=[Microsoft.CodeAnalysis.CSharp.CSharpSyntaxTree]::ParseText($cs)
$references=@([AppContext]::GetData('TRUSTED_PLATFORM_ASSEMBLIES') -split [IO.Path]::PathSeparator|ForEach-Object {[Microsoft.CodeAnalysis.MetadataReference]::CreateFromFile($_)})
$options=[Microsoft.CodeAnalysis.CSharp.CSharpCompilationOptions]::new([Microsoft.CodeAnalysis.OutputKind]::DynamicallyLinkedLibrary)
$analysis=[Microsoft.CodeAnalysis.CSharp.CSharpCompilation]::Create('MaterialJobMembersSourceAnalysis',
    [Microsoft.CodeAnalysis.SyntaxTree[]]@($tree),[Microsoft.CodeAnalysis.MetadataReference[]]$references,$options)
$diagnostics=@($analysis.GetDiagnostics()|Where-Object Severity -EQ Error)
Assert (!$diagnostics.Count) ('C# semantic diagnostics: '+($diagnostics -join '; '))
Assert ($cs -notmatch '\b(TerminateProcess|TerminateJobObject|CreateProcess|CreateJobObject|AssignProcessToJobObject|SetInformationJobObject|WriteProcessMemory|ReadProcessMemory|CloseHandle)\b') 'Diagnostic cannot own, kill, mutate or inspect process memory'
Assert ($cs.Contains('OpenProcess(0x1000, false, pid)') -and $cs.Contains('IsProcessInJob(process, job, out member)')) 'Limited read access and exact job membership required'
Assert ($cs.Contains('QueryInformationJobObject(job, 3, buffer') -and $cs.Contains('listed != assigned') -and $cs.Contains('Capacity = 64')) 'Exact bounded complete job member list'
Assert ($cs.Contains('BindingFlags.DeclaredOnly') -and $cs.Contains('field.FieldType != typeof(IntPtr)') -and $cs.Contains('Live original job handle required')) 'Pinned borrowed-handle layout and disposed-owner refusal'
Assert ($cs.Contains('GetProcAddress(module, "NtQueryInformationProcess")') -and $cs.Contains('ParentError')) 'Optional dynamically resolved parent query records failure'
$runner=Get-Content -LiteralPath $path -Raw
Assert ($runner.IndexOf('Enter-IW7ResourceLease') -lt $runner.IndexOf('Add-Type -LiteralPath')) 'Native helper load follows admission'
Assert ($runner.Contains("Phases=@('compile')") -and $runner.Contains('WriterExecution=$false;FFExecution=$false;StockStaging=$false')) 'Compile-only plan'
Assert ($runner -notmatch '-buildzone|-dumpzone|-verifyzone|New-Item -ItemType HardLink|Save-IW7BaseTransaction|[.]Kill[(]') 'No FF, stock staging or PID kill path'
Assert ($runner.Contains('Stop-MaterialV2OwnedPhase $owner $state.Cleanup') -and $runner.Contains('$lease -and $closed -and $state.SourceHashesUnchanged')) 'Same original-job cleanup and guarded lease release'
Assert ($runner.Contains('Wait-MaterialV2OwnedPhase $owner $identity $started.StartedMonotonicMs 240') -and
    $runner.Contains('DrainMilliseconds=2000;CleanupMilliseconds=15000')) 'Existing deadlines unchanged'
Assert ($runner.Contains('Assert-MaterialV2PhaseResult $state.NativeReceipt') -and $runner.Contains('$closed=$true;$owner.Dispose()')) 'Phase receipt never replaces exact closed-owner gate'
Assert ($runner.Contains('!$state.JobClosureVerified -or !$state.SourceHashesUnchanged -or !$state.LeaseReleased -or $state.RetainedLeaseToken')) 'Final result refuses incomplete cleanup/source proof'
"PASS: $checks source/mocked checks; C# semantic analysis only, no Emit/Add-Type/native call/lease/child."
