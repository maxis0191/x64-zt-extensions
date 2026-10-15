# Source-only integration causal against the existing reviewed Stock35 provider.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$StockCore,[Parameter(Mandatory)][string]$StockSHA256,
 [Parameter(Mandatory)][string]$LabSHA256,[string]$Runner=(Join-Path $PSScriptRoot 'Run-PlayerTemplateExport.ps1'))
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$sourceGuards=[Collections.Generic.List[object]]::new();$directory=$null
try{
    foreach($pin in @(@{Path=$StockCore;SHA256=$StockSHA256;Name='Stock-Links.Core.ps1'},
        @{Path=(Join-Path (Split-Path $StockCore -Parent) 'Lab-Paths.ps1');SHA256=$LabSHA256;Name='Lab-Paths.ps1'})){
        if($pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or [IO.Path]::GetFileName($pin.Path) -cne $pin.Name -or
           $pin.Path -cnotmatch '^[A-Za-z]:\\' -or [IO.Path]::GetFullPath($pin.Path) -cne $pin.Path -or $pin.Path.Substring(2).Contains(':')){throw 'Exact Source provider required before open.'}
        for($part=$pin.Path;$part;$part=[IO.Path]::GetDirectoryName($part)){if((Get-Item -LiteralPath $part).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Source redirect refused.'}}
        $stream=[IO.FileStream]::new($pin.Path,'Open','Read','Read');$sourceGuards.Add($stream)
        if($stream.Length -gt 128KB){throw 'Bounded Source provider required.'}
        $hash=[Security.Cryptography.SHA256]::Create();try{$sha=[Convert]::ToHexString($hash.ComputeHash($stream)).ToLowerInvariant()}finally{$hash.Dispose()}
        if($sha -cne $pin.SHA256){throw 'Source provider hash differs.'};$stream.Position=0
    }
    . $StockCore # Functions-only import, same guarded provider bytes.
    function Initialize-IW7StockLinkNtfs {throw 'SourceOnlyPreflightRefusedBeforeNative'}
    function Enter-IW7ResourceLease {throw 'No real admission in Source causal'}
    $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($Runner,[ref]$tokens,[ref]$errors)
    if($errors.Count){throw 'Runner parse failed.'}
    foreach($name in @('Assert-PlayerExportClock','Assert-PlayerExportCaller','New-PlayerStockTransaction','Pin-PlayerOpaque','Confirm-PlayerStock')){
        $definition=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true)
        if(!$definition){throw 'Actual caller function missing.'};. ([scriptblock]::Create($definition.Extent.Text))
    }
    $script:T7GroupStarted='source-clock';$script:clockCalls=0;$script:opaqueCalls=0
    function Assert-H1Deadline($Started,$Seconds){if($Started -cne 'source-clock' -or $Seconds -ne 600){throw 'Wrong original clock'};$script:clockCalls++}
    function Open-T7Pin($Pin,$Context){
        if(![object]::ReferenceEquals($Context,$script:PlayerTemplateExportOriginalRoot.Context) -or $Pin.Role -cne 'SourceOnlyFixture'){throw 'Source-only opaque substitute required'}
        $script:opaqueCalls++ # No file is opened and no opaque input is read.
    }
    $directory=Join-Path ([IO.Path]::GetTempPath()) ('iw7-player-stock-source-'+[guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($directory)|Out-Null
    $fixture=[pscustomobject]@{Role='SourceOnlyFixture'}
    $script:PlayerTemplateExportOriginalRoot=@{Key='IW7.PlayerExport.SourceCausal';Context=[pscustomobject]@{Lease=[pscustomobject]@{Token='source-only'}};
        Plan=[pscustomobject]@{RunRoot=$directory;GroupSeconds=600;Candidate=$fixture;TLS=$fixture;Sentinel=$fixture};State=@{Host=@{PID=$PID};ContentPins=@();CreatedCopies=@()};StockContexts=[Collections.Generic.List[object]]::new()}
    [AppDomain]::CurrentDomain.SetData($script:PlayerTemplateExportOriginalRoot.Key,$script:PlayerTemplateExportOriginalRoot)
    $linkPlan=[pscustomobject]@{Schema='iw7.stock-link-plan/1';SourceRoot=(Join-Path $directory 'base');TargetRoot=(Join-Path $directory 'target');Rows=@()}
    $tx=New-PlayerStockTransaction ([pscustomobject]@{Name='root'}) $linkPlan
    if(![object]::ReferenceEquals($tx,$script:PlayerTemplateExportOriginalRoot.Stock_root) -or
       ![object]::ReferenceEquals($tx,$script:PlayerTemplateExportOriginalRoot.StockContexts[0])){throw 'Actual published transaction was not retained'}
    function Invoke-StockPlanShadow($Context){$plan=$Context.Plan;$state=@{};$root=@{};Assert-IW7StockLinkContext $Context}
    Invoke-StockPlanShadow $tx # Real helper Context plus caller stock Plan shadow.
    $refused=$false;try{Invoke-IW7StockLinkPreflight $tx}catch{if($_.Exception.Message -cne 'SourceOnlyPreflightRefusedBeforeNative'){throw};$refused=$true}
    if(!$refused -or $tx.Phase -cne 'PublishedBeforePreflight' -or $tx.Guards.Count -or $tx.Sources.Count -or
       $tx.CreatedLinks.Count -or $tx.CreatedDirectories.Count -or $null -ne $tx.JournalStream -or ('IW7StockLinksV1.Ntfs' -as [type])){throw 'Preflight reached native/effects'}
    Confirm-PlayerStock # Actual known uneffected publication is safe to close.
    $tx.UnknownCreation=$true;$refused=$false;try{Confirm-PlayerStock}catch{$refused=$true};$tx.UnknownCreation=$false
    if(!$refused){throw 'Unknown stock effects accepted'}
    $tx.CreatedLinks.Add(@{Path='source-only'});$refused=$false;try{Confirm-PlayerStock}catch{$refused=$true};$tx.CreatedLinks.Clear()
    if(!$refused){throw 'Unprepared stock effects accepted'}
    $script:PlayerTemplateExportOriginalRoot.State.Host.PID=-1
    $refused=$false;try{$null=New-PlayerStockTransaction ([pscustomobject]@{Name='main'}) $linkPlan}catch{$refused=$true}
    $script:PlayerTemplateExportOriginalRoot.State.Host.PID=$PID
    if(!$refused -or $script:PlayerTemplateExportOriginalRoot.StockContexts.Count -ne 2 -or
       ![object]::ReferenceEquals($script:PlayerTemplateExportOriginalRoot.Stock_main,$script:PlayerTemplateExportOriginalRoot.StockContexts[1])){throw 'Factory callback failure lost actual published context'}
    Close-IW7StockLinkGuards $tx;Close-IW7StockLinkGuards $script:PlayerTemplateExportOriginalRoot.Stock_main
    if(@(Get-ChildItem -LiteralPath $directory -Force).Count -or $script:clockCalls -lt 3 -or $script:opaqueCalls -ne 3){throw 'Unexpected Source causal effects'}
    [ordered]@{Schema='iw7.player-export-stock-source-causal/1';Passed=$true;ActualStock35Imported=$true;DynamicContextAndPlanShadowPassed=$true;
        PreflightRefusedBeforeNative=$true;UnreturnedPublishedContextRetained=$true;UnknownAndUnpreparedEffectsRefused=$true;
        NativeTypesLoaded=$false;OpaqueInputsRead=$false;LeaseAcquired=$false;AliasesCreated=$false;CandidateExecuted=$false;Ready=$false}|ConvertTo-Json -Compress
}finally{
    foreach($guard in $sourceGuards){$guard.Dispose()}
    if($directory -and [IO.Directory]::Exists($directory)){[IO.Directory]::Delete($directory,$false)} # Only our proven empty temporary directory.
}
