$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1')
. (Join-Path $PSScriptRoot 'T7ImageProvenance.Profile.ps1')
$checks=0
function Check($Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Message){
    $caught=$false;try{& $Action}catch{$caught=$_.Exception.Message.Contains($Message)}
    Check $caught ('Expected refusal: '+$Message)
}
function New-SourcePlan {
    [pscustomobject]@{
        Schema='iw7.t7-image-provenance-source-plan/1';Operation='ImageProvenanceV1';CandidateProfile='t7-image-provenance-v1'
        Arguments=@('-t7-iw7-image-provenance-v1','mp_freerun_04','p7_fre_platform_cap_02','0')
        CandidateSource=$null;CandidateBytes=$null;CandidateSHA256=$null;BuildPlan=$null;BuildReceipt=$null
        ExpectedBuildPlanSHA256=$null;ExpectedBuildReceiptSHA256=$null
        SelectedImageProvenanceV1=[pscustomobject]@{
            Schema='iw7.t7-image-provenance-proposal/1';SourceRevision='678bf7dde6a99207654256c1e53ebaaec286ffe1'
            NativeSchema='iw7.t7-selected-image-provenance/1'
            Contract=('{"schema":"iw7.t7-image-provenance-source/1","source_profile":"t7-image-provenance-v1",'+
                '"files":{"selected_image_provenance.hpp":{"lf_bytes":15069,"lf_sha256":"d8b3f07f787f03dbda7c0305e2aad685c131130fbe43a839145e869858925c16"},'+
                '"native_image_provenance.inc":{"lf_bytes":1254,"lf_sha256":"360bcf806e2d69f3ecba2d2422b99c8c86a775397438117607115ed0d8b5573e"},'+
                '"selected_image_provenance_fixture.cpp":{"lf_bytes":14892,"lf_sha256":"f123c92c219c6d133882cadda2c8f62967de9bb86f2de0f55d0b468384d5f574"}},'+
                '"main":{"bytes":43370,"sha256":"13052a66ba89d5e66253c6931b81cb120aaa5acac37d6a4b15ab57cac4c10900"},'+
                '"cli":{"bytes":130246,"sha256":"15d03375dcd65f428ed10522ed238fe24c8ab407716780188ce341b87e1cbcf1"}}'|ConvertFrom-Json)
        }
    }
}
$plan=New-SourcePlan
Assert-T7ImageProvenanceSourcePlan $plan;Check $true 'Exact pending source plan refused.'
Check (Test-T7ImageProvenancePlan $plan) 'Source intent not detected.'
Check ((Get-T7CatalogueOperation $plan) -ceq 'ImageProvenanceV1') 'Operation not registered.'
Check ((Get-T7CatalogueCandidateProfile $plan) -ceq 't7-image-provenance-v1') 'Profile not registered.'
Check ((Get-T7CatalogueHostOutcomeName $plan) -ceq 'ProvenanceOutcome') 'Host fell back to catalogue/parts outcome.'
Check ((Get-T7CatalogueHostSchema $plan 'host-closure') -ceq 'iw7.t7-image-provenance-host-closure/1') 'Wrong host schema.'
function New-T7PrepatchStart {throw 'Reached process setup'}
Refuses {Assert-T7CataloguePlan $plan 'unused' 'unused'} 'qualified full-CLI CPP cohort'
Refuses {New-T7CatalogueStart $plan} 'qualified full-CLI CPP cohort'
Refuses {Assert-T7CatalogueBuild $plan $null} 'qualified full-CLI CPP cohort'
$badValues=[Collections.Generic.List[object]]::new()
$badValues.Add('cce8bbb8f068b4897a391880db316bd1d7586f26f7ec0c1cee2316d76c8644b3')
$badValues.Add(0);$badValues.Add($false);$badValues.Add([object[]]@($null))
foreach($name in 'CandidateSource','CandidateBytes','CandidateSHA256','BuildPlan','BuildReceipt','ExpectedBuildPlanSHA256','ExpectedBuildReceiptSHA256'){
    foreach($bad in $badValues){
        $plan=New-SourcePlan;$plan.$name=$bad
        Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'must remain NULL'
    }
    $plan=New-SourcePlan;$plan.PSObject.Properties.Remove($name)
    Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'must remain NULL'
}
foreach($name in 'SelectedMaterialPartsV1','SelectedXpakProvider','ExportRequest','SelectedStreamedRenderOnlyV2','ZombiesObservationC'){
    $plan=New-SourcePlan;$plan|Add-Member $name $false
    Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'another operation or provider'
}
foreach($name in 'Operation','CandidateProfile','Schema'){
    $plan=New-SourcePlan;$plan.$name='MaterialPartsV1'
    Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'must be paired'
}
for($i=0;$i -lt 4;$i++){
    $plan=New-SourcePlan;$plan.Arguments[$i]='wrong'
    Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'arguments required'
}
$plan=New-SourcePlan;$plan.Arguments+='extra';Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'arguments required'
$plan=New-SourcePlan;$plan.Arguments='flattened';Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'arguments required'
$plan=New-SourcePlan;$plan.SelectedImageProvenanceV1.SourceRevision='old';Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'source basis'
$plan=New-SourcePlan;$plan.SelectedImageProvenanceV1.Contract.files.'selected_image_provenance.hpp'.lf_bytes=$true
Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'source pin required'
$plan=New-SourcePlan;$plan.SelectedImageProvenanceV1.Contract.cli.sha256='old'
Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'source pair required'
$plan=New-SourcePlan;$plan.SelectedImageProvenanceV1.Contract.files.'selected_image_provenance_fixture.cpp'.lf_bytes=14626
Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'source pin required'
$plan=New-SourcePlan;$plan.SelectedImageProvenanceV1.Contract|Add-Member extra $false
Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'Exact catalogue fields'
$plan=New-SourcePlan;$plan.Arguments[3]=0
Refuses {Assert-T7ImageProvenanceSourcePlan $plan} 'arguments required'
foreach($operation in 'Catalogue','ResidentExportV1','MaterialPartsV1'){
    $legacy=[pscustomobject]@{Operation=$operation;CandidateProfile='ordinary-d2'}
    Check (!(Test-T7ImageProvenancePlan $legacy)) 'Legacy operation selected provenance.'
    Check ((Get-T7CatalogueOperation $legacy) -ceq $operation) 'Legacy operation changed.'
}
[ordered]@{Status='Passed';Checks=$checks;SourceOnly=$true;CPPExecuted=$false;NativeExecuted=$false;
    RealLeaseAcquired=$false;OpaqueInputsRead=$false;OperationalDEFAULTExecuted=$false}|ConvertTo-Json
