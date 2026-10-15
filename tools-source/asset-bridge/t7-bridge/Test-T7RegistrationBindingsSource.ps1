# Source descriptors and actual host refusals. No native types, opaque reads or lease.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1')
$checks=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Message){
    $caught=$false;try{& $Action}catch{$caught=$_.Exception.Message.Contains($Message)}
    Check $caught ('Expected refusal: '+$Message)
}
function New-BindingsSourcePlan {
    [pscustomobject]@{Schema='iw7.t7-registration-bindings-source-plan/1';Operation='RegistrationMaterialBindingsV1';CandidateProfile='t7-registration-material-bindings-v1';
        Arguments=@('-t7-iw7-registration-material-bindings-v1','mp_freerun_04','p7_fre_platform_cap_02','0');
        CandidateSource=$null;CandidateBytes=$null;CandidateSHA256=$null;BuildPlan=$null;BuildReceipt=$null;ExpectedBuildPlanSHA256=$null;ExpectedBuildReceiptSHA256=$null;
        SelectedRegistrationMaterialBindingsV1=[pscustomobject]@{Schema='iw7.t7-registration-bindings-proposal/1';
            SourceRevision='92118595079b86d66c340c22b299de90c49a2b6a';ReaderRevision='9eba3c7189fae12e218eadd8f56a7ddda834b1b4';
            Contract=[pscustomobject]@{Path='C:\authored\registration-material-bindings-source-contract.json';Bytes=5391;SHA256='d60f0e33d9dddb69656744f6481ba32ced1a7a040d75ff913908192297e3c9a6'};
            Reader=[pscustomobject]@{Path='C:\authored\registration_bindings_consumer.py';Bytes=9687;SHA256='8e1d464c6467492b65e102b784aa9f265723560b9b486499e3a49cb4073f5c81'};
            NativeSchema='iw7.t7-registration-material-bindings/1';BindingCount=7;ReportLimitBytes=32768;
            SourceOnlyPending=$true;BuildRecipeWired=$false;CompiledExtensionSource=$null;CPPQualification=$null;CPPQualified=$false;
            NativeObserved=$false;DeepMetadataOutcome=$null;QualifiedObjectMipCount=$null;Ready=$false}}
}
$plan=New-BindingsSourcePlan
Assert-T7RegistrationBindingsSourcePlan $plan;Check $true 'Reviewed Source descriptor refused.'
Check (Test-T7RegistrationBindingsIntent $plan) 'Source intent missed.'
foreach($bad in @($false,'true',1)){
    $p=New-BindingsSourcePlan;$p.SelectedRegistrationMaterialBindingsV1.SourceOnlyPending=$bad
    Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'must remain Source pending'
}
# Process setup must not be reached even with a forged operational schema.
function New-T7PrepatchStart {throw 'Unexpected process setup'}
foreach($schema in 'iw7.t7-registration-bindings-source-plan/1','iw7.t7-registration-bindings-plan/1'){
    $p=New-BindingsSourcePlan;$p.Schema=$schema
    Refuses {Assert-T7CatalogueBuild $p $null} 'DEFAULT and Run remain unavailable'
    Refuses {New-T7CatalogueStart $p} 'DEFAULT and Run remain unavailable'
    Refuses {Get-T7CatalogueHostSchema $p 'host'} 'host DEFAULT and Run remain unavailable'
}
Refuses {Assert-T7CataloguePlan $plan 'unused' 'unused'} 'DEFAULT and Run remain unavailable'
foreach($name in 'Schema','Operation','CandidateProfile','Arguments','SelectedRegistrationMaterialBindingsV1'){
    $single=[pscustomobject]@{};$single|Add-Member $name $plan.$name
    Check (Test-T7RegistrationBindingsIntent $single) ('Partial intent missed: '+$name)
    Refuses {Assert-T7CatalogueBuild $single $null} 'DEFAULT and Run remain unavailable'
    Refuses {New-T7CatalogueStart $single} 'DEFAULT and Run remain unavailable'
    Refuses {Get-T7CatalogueHostSchema $single 'host'} 'host DEFAULT and Run remain unavailable'
}
foreach($name in 'Schema','Operation','CandidateProfile'){
    $p=New-BindingsSourcePlan;$p.$name=@($p.$name);Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'typed registration bindings Source selectors'
    $p=New-BindingsSourcePlan;$p.$name='wrong';Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'typed registration bindings Source selectors'
}
foreach($name in 'Schema','SourceRevision','ReaderRevision','NativeSchema'){
    $p=New-BindingsSourcePlan;$p.SelectedRegistrationMaterialBindingsV1.$name=@($p.SelectedRegistrationMaterialBindingsV1.$name)
    Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'reviewed registration bindings Source basis'
    $p=New-BindingsSourcePlan;$p.SelectedRegistrationMaterialBindingsV1.$name='old'
    Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'reviewed registration bindings Source basis'
}
foreach($name in 'Contract','Reader'){
    foreach($field in 'Path','Bytes','SHA256'){
        $p=New-BindingsSourcePlan;$pin=$p.SelectedRegistrationMaterialBindingsV1.$name;$pin.$field=@($pin.$field)
        Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'Source text pin required'
    }
    foreach($path in @('C:\authored\candidate.exe','\\?\C:\authored\registration_bindings_consumer.py','C:\authored\candidate.exe:registration_bindings_consumer.py')){
        $p=New-BindingsSourcePlan;$p.SelectedRegistrationMaterialBindingsV1.$name.Path=$path
        Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'Source text pin required'
    }
}
$p=New-BindingsSourcePlan;$p.SelectedRegistrationMaterialBindingsV1.Reader.Path='C:\other\registration_bindings_consumer.py'
Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'One registration bindings Source package'
foreach($name in 'BindingCount','ReportLimitBytes'){
    foreach($bad in @($true,'7',8)){
        $p=New-BindingsSourcePlan;$p.SelectedRegistrationMaterialBindingsV1.$name=$bad
        Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'seven-row bounded Source proposal'
    }
}
foreach($name in 'BuildRecipeWired','CPPQualified','NativeObserved','Ready'){
    foreach($bad in @($true,'false',0)){
        $p=New-BindingsSourcePlan;$p.SelectedRegistrationMaterialBindingsV1.$name=$bad
        Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'cannot promote'
    }
}
foreach($name in 'CompiledExtensionSource','CPPQualification','DeepMetadataOutcome','QualifiedObjectMipCount'){
    foreach($bad in @($false,0,'old',[object[]]@($null))){
        $p=New-BindingsSourcePlan;$p.SelectedRegistrationMaterialBindingsV1.$name=$bad
        Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'Source facts must remain NULL'
    }
}
foreach($name in 'CandidateSource','CandidateBytes','CandidateSHA256','BuildPlan','BuildReceipt','ExpectedBuildPlanSHA256','ExpectedBuildReceiptSHA256'){
    foreach($bad in @($false,0,'4fcb0205e30979457784d1b883a153ecf5c20751543b68dfb184671d59e3ee4d',[object[]]@($null))){
        $p=New-BindingsSourcePlan;$p.$name=$bad
        Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'candidate/build fields must remain NULL'
    }
    $p=New-BindingsSourcePlan;$p.PSObject.Properties.Remove($name)
    Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'candidate/build fields must remain NULL'
}
foreach($name in 'SelectedIncomingImageObservationV1','SelectedRegistrationImageHeaderV1','SelectedXpakProvider','ExportRequest'){
    $p=New-BindingsSourcePlan;$p|Add-Member $name $false
    Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'another operation/provider'
}
for($i=0;$i -lt 4;$i++){
    $p=New-BindingsSourcePlan;$p.Arguments[$i]='wrong';Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'Source arguments required'
}
$p=New-BindingsSourcePlan;$p.Arguments[3]=0;Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'Source arguments required'
$p=New-BindingsSourcePlan;$p.Arguments+='extra';Refuses {Assert-T7RegistrationBindingsSourcePlan $p} 'Source arguments required'
foreach($mode in 'Catalogue','ResidentExportV1','MaterialPartsV1','ImageProvenanceV1','RegistrationImageMetadataV1','IncomingImageObservationV1'){
    $legacy=[pscustomobject]@{Operation=$mode;CandidateProfile='ordinary-d2'}
    Check (!(Test-T7RegistrationBindingsIntent $legacy)) 'Legacy intent changed.'
    Check ((Get-T7CatalogueOperation $legacy) -ceq $mode) 'Legacy operation changed.'
}
# Exercise the actual host entry in both modes. Only the two small JSON files
# exist; a decoy opaque/text binding and HostImage must never be inspected/opened.
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('t7-bindings-source-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($temporary)
try{
    $planPath=Join-Path $temporary 'plan.json';$contractPath=Join-Path $temporary 'host.json';$runRoot=Join-Path $temporary 'run'
    $p=New-BindingsSourcePlan;$p|Add-Member Bindings @([pscustomobject]@{Path='C:\never-open\candidate.exe';Bytes=1;SHA256=('0'*64);IsText=$true})
    [IO.File]::WriteAllText($planPath,($p|ConvertTo-Json -Depth 8))
    [IO.File]::WriteAllText($contractPath,'{"HostImage":"C:\\never-open\\host.exe"}')
    $planSHA=(Get-FileHash -LiteralPath $planPath).Hash.ToLowerInvariant();$contractSHA=(Get-FileHash -LiteralPath $contractPath).Hash.ToLowerInvariant()
    $entry=Join-Path $PSScriptRoot 'Invoke-T7CatalogueHost.ps1'
    foreach($run in $false,$true){
        Refuses {& $entry -PlanPath $planPath -PlanSHA256 $planSHA -RunRoot $runRoot -HostContractPath $contractPath -HostContractSHA256 $contractSHA -Run:$run} 'host DEFAULT and Run remain unavailable'
    }
    Check (!(Test-Path -LiteralPath $runRoot)) 'Host Source refusal created runtime.'
    Check ((@(Get-ChildItem -LiteralPath $temporary -Force)).Count -eq 2) 'Host Source refusal wrote evidence.'
    Check ($null -eq [AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost')) 'Host Source refusal retained a consumed host.'
    Check (!('IW7.AnimationProbe.NativeJob' -as [type])) 'Host Source refusal loaded NativeJob.'
}finally{
    $resolved=[IO.Path]::GetFullPath($temporary);$tempPrefix=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($tempPrefix,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-bindings-source-[0-9a-f]{32}$'){throw 'Test cleanup target differs.'}
    [IO.Directory]::Delete($resolved,$true)
}
Write-Output ('T7_REGISTRATION_BINDINGS_SOURCE_CHECKS='+$checks)
