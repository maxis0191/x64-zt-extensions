# Synthetic C2 records and existing F grammar only. No stock, native types or lease.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern='.'){$caught=$false;try{$null=& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected refusal: '+$_.Exception.Message)};Check $caught ('Expected refusal: '+$Pattern)}
function Copy-Value($Value){$Value|ConvertTo-Json -Depth 20|ConvertFrom-Json}
$prefix='[T7_ZM_ADD] schema=iw7.t7-zm-add-observation/1 '
$target=[Convert]::ToHexString([Text.Encoding]::ASCII.GetBytes('ui/uieditor/widgets/attachmentnamesdisplay.lua')).ToLowerInvariant()
function Row([string]$Body,[int]$Seq=0,[ulong]$Tid=17){$prefix+"seq=$Seq tid=$Tid $Body`n"}
function Context([string]$State='read',[string]$Name='zm_common',[int]$Nul=1){'ff_state='+$State+' ff_nul='+$Nul+' ff_name_hex='+[Convert]::ToHexString([Text.Encoding]::ASCII.GetBytes($Name)).ToLowerInvariant()+' ff_atomic=0'}
function Entry([int]$Seq=1,[int]$Call=0,[int]$Reference=0,[ulong]$Tid=17){$name=$(if($Reference){'2c'}else{''})+$target;Row ("kind=add_enter call=$Call type=47 reference_prefix=$Reference name_hex=$name caller=00000001401D1234 asset=0000000140123456 "+(Context)) $Seq $Tid}
function Returned([int]$Seq=2,[int]$Call=0,[int]$Reference=0,[ulong]$Tid=17){Row ("kind=add_return call=$Call reference_prefix=$Reference result=0000000140123456 "+(Context)) $Seq $Tid}
$enabled=Row 'kind=enabled'
$trace='[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase='
$message='[T7_CATALOG_MSG] schema=iw7.t7-catalog-message/1 kind='
$fatal='Could not load ui/uieditor/widgets/attachmentnamesdisplay.lua'
$fatalHex=[Convert]::ToHexString([Text.Encoding]::ASCII.GetBytes($fatal))
$legacyEnabled=$trace+'enabled stdout_unbuffered=1 stderr_unbuffered=1 tid=42'
$legacyBefore=$trace+'before_post_unpack code=0 tid=42 return_address=0000000000000000'
$legacyInstall=$message+'install tid=42 status=installed error=0'
$legacyAfter=$trace+'after_post_unpack code=0 tid=42 return_address=0000000000000000'
$legacyBuffer=$message+"buffer tid=73 status=ok requested=384 read=384 length=$($fatal.Length) nul=1 error=0 data=$fatalHex"
$legacyExit=$trace+'exit_hook code=0 tid=73 return_address=0000000140AC00C4'
$legacy=(@($legacyEnabled,$legacyBefore,$legacyInstall,$legacyAfter,$legacyBuffer,$legacyExit) -join "`n")+"`n"
$full=$legacy+$enabled+(Entry)+(Returned)+(Entry 3 1 1)+(Returned 4 1 1)
$split=Split-T7CatalogueZombiesAddObservation $full
Check ($split.LegacyText -ceq $legacy -and $split.Records.Count -eq 5) 'C2 changed F bytes or plain/comma calls.'
Check (($split.Records.kind -join '|') -ceq 'enabled|add_enter|add_return|add_enter|add_return') 'C2 record order changed.'
$combined=ConvertFrom-T7CatalogueZombiesAddObservation $full
Check ($combined.Outcome -ceq 'TraceObserved' -and $combined.MessageOutcome -ceq 'Observed' -and $combined.Message.ExitCorrelated) 'C2 changed the legacy fatal/correlation result.'
Check ($combined.Message.Captures[1].DataHex -ceq $fatalHex -and $combined.ZombiesAddObservations.Count -eq 5) 'Opaque fatal bytes or C2 records changed.'
Check ((Split-T7CatalogueZombiesAddObservation ($full.Replace("`n","`r`n"))).LegacyText -ceq $legacy.Replace("`n","`r`n")) 'CRLF legacy bytes changed.'
Check ((Split-T7CatalogueZombiesAddObservation ($enabled+(Entry))).Records.Count -eq 2) 'Unreturned entry was upgraded or rejected.'
Check ((Split-T7CatalogueZombiesAddObservation $legacy).Records.Count -eq 0) 'Absent observations became calls.'
foreach($state in @('getter_exception','prefix_unreadable','name_unreadable')){
    $rows=(Split-T7CatalogueZombiesAddObservation ($enabled+(Row ("kind=selection_refused type=47 read_state=$state target=unknown") 1))).Records
    Check ($rows[1].kind -ceq 'selection_refused' -and !$rows[1].PSObject.Properties['call']) 'Unknown selection became a target call or no-lookup claim.'
}
foreach($state in @('pointer_unreadable','null','name_unreadable','prefix','read')){
    $ctx=if($state -ceq 'prefix'){Context $state ('a'*64) 0}elseif($state -ceq 'read'){Context}else{Context $state '' 0}
    $rows=(Split-T7CatalogueZombiesAddObservation (($enabled+(Entry)).Replace((Context),$ctx))).Records
    Check ($rows[1].ff_state -ceq $state) 'Fastfile read state was inferred or changed.'
}
foreach($bad in @((Returned),((Entry)+(Returned 2 0 0 18)),((Entry)+(Returned 2 0 1)),((Entry)+(Entry 2)),((Entry)+(Returned)+(Returned 3)))){
    Refuses {Split-T7CatalogueZombiesAddObservation ($enabled+$bad)} 'entry|matching'
}
foreach($pair in @(@('type=47','type=46'),@('reference_prefix=0','reference_prefix=1'),@(('name_hex='+$target),('name_hex='+('61'*46))),
    @('iw7.t7-zm-add-observation/1','iw7.t7-zm-observation/1'),@('ff_atomic=0','ff_atomic=1'),@('ff_nul=1','ff_nul=0'),@('tid=17','tid=0'),@('seq=1','seq=64'))){
    $bad=($enabled+(Entry)).Replace($pair[0],$pair[1]);Refuses {Split-T7CatalogueZombiesAddObservation $bad}
}
Refuses {Split-T7CatalogueZombiesAddObservation ($enabled+(Entry 1 0 0 4294967296))} 'sequence/thread'
Refuses {Split-T7CatalogueZombiesAddObservation ($enabled+$enabled)} 'duplicated|initial'
Refuses {Split-T7CatalogueZombiesAddObservation (Entry)} 'before enabled'
Refuses {Split-T7CatalogueZombiesAddObservation (($enabled+(Entry)).TrimEnd("`n"))} 'Complete bounded'
Refuses {Split-T7CatalogueZombiesAddObservation ('é'+$enabled)} 'ASCII'
Refuses {Split-T7CatalogueZombiesAddObservation ('a'*16385)} 'ASCII'
$edge=$enabled.Replace('seq=0','seq='+('0'*(513-$enabled.Length)))
Check ($edge.Length -eq 512 -and (Split-T7CatalogueZombiesAddObservation $edge).Records.Count -eq 1) '512-byte physical line changed.'
Refuses {Split-T7CatalogueZombiesAddObservation ($edge.Replace('seq=','seq=0'))} 'Complete bounded'
$ten=$enabled+(Row 'kind=selection_refused type=47 read_state=name_unreadable target=unknown' 1)
for($i=0;$i -lt 4;$i++){$ten+=(Entry (2+2*$i) $i)+(Returned (3+2*$i) $i)}
Check ((Split-T7CatalogueZombiesAddObservation $ten).Records.Count -eq 10) 'Four pairs plus enabled/refused lost the ten-row boundary.'
$plan=[pscustomobject]@{Operation='Catalogue';CandidateProfile='t7-zombies-catalogue-observation-c2';Zone=[pscustomobject]@{Path='C:\synthetic\zm_common.ff'};
    TraceStderrLimitBytes=16384;ZombiesAddObservationC2=[pscustomobject]@{Schema='iw7.t7-zm-add-observation-plan/1'}}
Assert-T7CatalogueZombiesAddPlan $plan;$checks++
foreach($change in @('missing','c1','schema-array','export','zone','cap','profile-array')){
    $bad=Copy-Value $plan
    switch($change){
        missing{$bad.PSObject.Properties.Remove('ZombiesAddObservationC2')}
        c1{$bad|Add-Member NoteProperty ZombiesObservationC ([pscustomobject]@{Schema='iw7.t7-zm-observation-plan/1'})}
        schema-array{$bad.ZombiesAddObservationC2.Schema=@($bad.ZombiesAddObservationC2.Schema)}
        export{$bad|Add-Member NoteProperty SelectedStreamedRenderOnlyV2 ([pscustomobject]@{Schema='iw7.t7-selected-streamed-render-only-plan/2'})}
        zone{$bad.Zone.Path='C:\synthetic\mp_freerun_04.ff'}
        cap{$bad.TraceStderrLimitBytes=8192}
        profile-array{$bad.CandidateProfile=@($bad.CandidateProfile)}
    }
    Refuses {Assert-T7CatalogueZombiesAddPlan $bad}
}
Check (!(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]))) 'Fixture loaded native types.'
[pscustomobject]@{Status='Passed';Checks=$checks;NativeStarted=$false;StockRead=$false;LeaseAcquired=$false;ObservationAuthority='Finite records only; unknown is not no lookup'}|ConvertTo-Json
