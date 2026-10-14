param([string]$Entry=(Join-Path $PSScriptRoot 'Run-T7Build.ps1'))
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($Entry,[ref]$tokens,[ref]$errors)
if($errors){throw 'Runner syntax failed'}
$function=$ast.Find({param($node)$node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Assert-T7OSResourceContext'},$true)
if(!$function){throw 'Actual OS context guard missing'}
. ([scriptblock]::Create($function.Extent.Text))
$old='f3f5ef83a67c503991d728f62cf039cbb52a18d6eb82197dec23ede8f0996108'
$new='1398cf1d866e49a8ba351e2a30a7803b50c8b595d17f776abe8d2ec4a9c6fb10'
$sha='5a282c19995af210fd9d7c55a8692d87d4456526352fe21034a8f07d83a9fd9d'
$tz='C:\WINDOWS\SYSTEM32\TZRES.DLL';$proofPath='C:\authored\os-proof.json'
$proof=[ordered]@{Schema='iw7.t7-os-resource-qualification/1';Status='ObservationComplete';GuardsDisposed=$true;LeaseReleased=$true;Ready=$false;Postflight=@{Leases=@()};OSResource=@{
    Path=$tz;HistoricalBytes=12288;HistoricalSHA256=$old;ObservedBytes=12288;ObservedSHA256=$new;
    ProductVersion='10.0.26100.9711';SignatureStatus='Valid';SignatureType='Catalog';
    SignerSubject='CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US';
    SignerThumbprint='667BBA1E1F478221AA65DE4F75187A751B03A453';ContractAccepted=$false;PinAdopted=$false}}
$script:proofText=$proof|ConvertTo-Json -Depth 8
$script:opened=0
# Inert source fixture: executes the actual semantic guard, not a DLL/IO guard.
function Open-T7Bootstrap($Path,$Bytes,$SHA256){
    if($Path -cne $proofPath -or $Bytes -ne 8907 -or $SHA256 -cne $sha){throw 'Expected fixed proof pin missing'}
    $script:opened++;[IO.MemoryStream]::new([Text.Encoding]::UTF8.GetBytes($script:proofText))
}
$plan=[ordered]@{BuildProfile=@{Name='t7-material-parts-v1'};Inputs=@(@{Path=$tz;Bytes=12288;SHA256=$new});
    Bindings=@(@{Path=$proofPath;Bytes=8907;SHA256=$sha;IsText=$true});OSResourceContext=[ordered]@{
        Schema='iw7.t7-os-resource-context/1';Name='windows-tzres-20261014';SourceOSDate='2026-10-14';
        Before=@{Path=$tz;Bytes=12288;SHA256=$old};After=@{Path=$tz;Bytes=12288;SHA256=$new};
        Evidence=@{Path=$proofPath;Bytes=8907;SHA256=$sha};ProductVersion='10.0.26100.9711';
        SignatureStatus='Valid';SignatureType='Catalog';SignerThumbprint='667BBA1E1F478221AA65DE4F75187A751B03A453';KBFileAttributionVerified=$false}}
$raw=$plan|ConvertTo-Json -Depth 8;$checks=0
foreach($family in 't7-material-parts-v1','t7-prepatch-link-v3'){
    $p=$raw|ConvertFrom-Json;$p.BuildProfile.Name=$family
    if((Assert-T7OSResourceContext $p) -cne $proofPath){throw 'Positive fixed context refused'};$checks++
}
foreach($case in 'null','extra','wrongprofile','datearray','bytesbool','wrongbefore','wrongafter','freeproofsha','missingbinding','doublebinding','mismatchedduplicate','casealiasbinding','bindingbytesstring','untypedbinding','changedinput','doubleinput','casealiasinput','inputhasharray','kbattribution'){
    $p=$raw|ConvertFrom-Json
    switch($case){
        null {$p.OSResourceContext=$null}
        extra {$p.OSResourceContext|Add-Member NoteProperty Extra 'unexpected'}
        wrongprofile {$p.BuildProfile.Name='t7-catalog-message-publication'}
        datearray {$p.OSResourceContext.SourceOSDate=@('2026-10-14')}
        bytesbool {$p.OSResourceContext.After.Bytes=$true}
        wrongbefore {$p.OSResourceContext.Before.SHA256=$new}
        wrongafter {$p.OSResourceContext.After.SHA256='c'*64}
        freeproofsha {$p.OSResourceContext.Evidence.SHA256='d'*64}
        missingbinding {$p.Bindings=@()}
        doublebinding {$p.Bindings+=@($p.Bindings[0])}
        mismatchedduplicate {$copy=$p.Bindings[0]|ConvertTo-Json|ConvertFrom-Json;$copy.SHA256='e'*64;$p.Bindings+=@($copy)}
        casealiasbinding {$copy=$p.Bindings[0]|ConvertTo-Json|ConvertFrom-Json;$copy.Path=$proofPath.ToLowerInvariant();$p.Bindings+=@($copy)}
        bindingbytesstring {$p.Bindings[0].Bytes='8907'}
        untypedbinding {$p.Bindings[0].IsText='true'}
        changedinput {$p.Inputs[0].SHA256=$old}
        doubleinput {$p.Inputs+=@($p.Inputs[0])}
        casealiasinput {$p.Inputs[0].Path=$tz.ToLowerInvariant()}
        inputhasharray {$p.Inputs[0].SHA256=@($new)}
        kbattribution {$p.OSResourceContext.KBFileAttributionVerified=$true}
    }
    $refused=$false;try{$null=Assert-T7OSResourceContext $p}catch{$refused=$true}
    if(!$refused){throw "Invalid OS context accepted: $case"};$checks++
}
$p=$raw|ConvertFrom-Json;$p.PSObject.Properties.Remove('OSResourceContext');$p.Bindings=@();$p.Inputs[0].SHA256=$old
$null=Assert-T7OSResourceContext $p;$checks++
$p.Inputs[0].SHA256=$new;$refused=$false;try{$null=Assert-T7OSResourceContext $p}catch{$refused=$true}
if(!$refused){throw 'Context-free refreshed pin accepted'};$checks++
"PASS actual OS resource guard: $checks checks; authored metadata only, no DLL/registry/lease."
