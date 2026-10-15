$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1')
. (Join-Path $PSScriptRoot 'T7IncomingImage.Profile.ps1')
$checks=0
function Check($Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Message){$caught=$false;try{& $Action}catch{$caught=$_.Exception.Message.Contains($Message)};Check $caught ('Expected refusal: '+$Message)}
function New-IncomingSourcePlan {
    [pscustomobject]@{Schema='iw7.t7-incoming-image-source-plan/1';Operation='IncomingImageObservationV1';CandidateProfile='t7-incoming-image-header-observation-v1';
        Arguments=@('-t7-iw7-incoming-image-header-v1','mp_freerun_04','p7_fre_platform_cap_02','0');
        CandidateSource=$null;CandidateBytes=$null;CandidateSHA256=$null;BuildPlan=$null;BuildReceipt=$null;ExpectedBuildPlanSHA256=$null;ExpectedBuildReceiptSHA256=$null;
        SelectedIncomingImageObservationV1=[pscustomobject]@{Schema='iw7.t7-incoming-image-proposal/1';SourceRevision='4873ef4a4ce8478020d8533651f123f8feadfa95';NativeSchema='iw7.t7-incoming-image-header-observation/1';
            Contract=[pscustomobject]@{Path='C:\authored\incoming-image-source-contract.json';Bytes=4613;SHA256='1f672f51533f90ea10d396bd28a8298f6070d39df938b0bf4033c4754dc4659f'};
            SlotOrder=@('bootstrap/reference','bootstrap/ordinary','map_load/reference','map_load/ordinary');SourceOnlyPending=$true;CPPQualified=$false;NativeObserved=$false;QualifiedObjectMipCount=$null;Ready=$false}}
}
$plan=New-IncomingSourcePlan;Assert-T7IncomingImageSourcePlan $plan;Check $true 'Exact pending Source plan refused.'
Check (Test-T7IncomingImageIntent $plan) 'Incoming Source intent not detected.'
Check ((Get-T7CatalogueOperation $plan) -ceq 'IncomingImageObservationV1') 'Incoming operation unknown.'
Check ((Get-T7CatalogueCandidateProfile $plan) -ceq 't7-incoming-image-header-observation-v1') 'Incoming profile unknown.'
Check ((Get-T7CatalogueHostSchema $plan 'host-closure') -ceq 'iw7.t7-incoming-image-host-closure/1') 'Incoming host schema fell through.'
Check ((Get-T7CatalogueHostOutcomeName $plan) -ceq 'IncomingObservationOutcome') 'Incoming outcome fell through.'
function New-T7PrepatchStart {throw 'Reached process setup'}
Refuses {Assert-T7CataloguePlan $plan 'unused' 'unused'} 'new actual closed CPP cohort'
Refuses {Assert-T7CatalogueBuild $plan $null} 'new actual closed CPP cohort'
Refuses {New-T7CatalogueStart $plan} 'new actual closed CPP cohort'
foreach($name in 'CandidateSource','CandidateBytes','CandidateSHA256','BuildPlan','BuildReceipt','ExpectedBuildPlanSHA256','ExpectedBuildReceiptSHA256'){
    foreach($bad in @('eeeca36f',0,$false,[object[]]@($null))){$plan=New-IncomingSourcePlan;$plan.$name=$bad;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'must remain NULL'}
    $plan=New-IncomingSourcePlan;$plan.PSObject.Properties.Remove($name);Refuses {Assert-T7IncomingImageSourcePlan $plan} 'must remain NULL'
}
foreach($name in 'Schema','Operation','CandidateProfile'){
    $plan=New-IncomingSourcePlan;$plan.$name=@($plan.$name);Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Typed incoming Source selectors'
    $plan=New-IncomingSourcePlan;$plan.$name='RegistrationImageMetadataV1';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Exact incoming Source schema'
}
foreach($name in 'Schema','SourceRevision','NativeSchema'){
    $plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.$name=@($plan.SelectedIncomingImageObservationV1.$name)
    Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Typed incoming Source descriptor texts'
}
foreach($name in 'CPPQualified','NativeObserved','Ready'){
    $plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.$name=$true;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'cannot promote'
    $plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.$name='false';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'cannot promote'
}
$plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.SourceOnlyPending=$false;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'must remain Source pending'
$plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.QualifiedObjectMipCount=1;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'mip fact must remain NULL'
foreach($name in 'SelectedImageProvenanceV1','SelectedRegistrationImageHeaderV1','SelectedMaterialPartsV1','SelectedXpakProvider','ExportRequest'){
    $plan=New-IncomingSourcePlan;$plan|Add-Member $name $false;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'another operation/provider'
}
for($i=0;$i -lt 4;$i++){
    $plan=New-IncomingSourcePlan;$plan.Arguments[$i]='wrong';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Source arguments required'
    $plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.SlotOrder[$i]='wrong';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Source slot order required'
}
$plan=New-IncomingSourcePlan;$plan.Arguments[3]=0;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Source arguments required'
$plan=New-IncomingSourcePlan;$plan.Arguments+='extra';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Source arguments required'
foreach($path in @('C:\authored\candidate.exe:incoming-image-source-contract.json','\\?\C:\authored\incoming-image-source-contract.json','C:\authored\other.json')){
    $plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.Contract.Path=$path;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'contract text pin required'
}
$plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.Contract.Bytes='4613';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'contract text pin required'
$plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.Contract.SHA256='old';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'contract text pin required'
foreach($operation in 'Catalogue','ResidentExportV1','MaterialPartsV1','ImageProvenanceV1','RegistrationImageMetadataV1'){
    $legacy=[pscustomobject]@{Operation=$operation;CandidateProfile='ordinary-d2'}
    Check (!(Test-T7IncomingImageIntent $legacy)) 'Existing mode selected incoming.'
    Check ((Get-T7CatalogueOperation $legacy) -ceq $operation) 'Existing operation changed.'
}
[ordered]@{Status='Passed';Checks=$checks;SourceOnly=$true;CPPExecuted=$false;NativeExecuted=$false;LeaseAcquired=$false;OpaqueRead=$false;OperationalDEFAULTExecuted=$false}|ConvertTo-Json
