# Fixed V3 report fixtures only. No mapped executable, provider or reservation.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7PrepatchReferenceV2.Profile.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body){$caught=$false;try{& $Body}catch{$caught=$true};Check $caught 'Unqualified fixed report accepted'}
$module=Join-Path ([IO.Path]::GetTempPath()) 'synthetic-link-engine.exe'
$identity=[pscustomobject]@{PID=123;CreatedUtc='2026-10-14T00:00:00.0000000Z'}
$schema='iw7.t7-prepatch-link-observation/3'
function New-Report {
    [pscustomobject]@{schema=$schema;phase='first_dpi_before_component_post_unpack';pid=123;thread_id=456;creation_filetime=([datetime]::Parse($identity.CreatedUtc).ToFileTimeUtc().ToString());
        module_path=$module;module_base='0x140000000';base_matches_source=$true;source_base='0x140000000';read_limit=4MB;report_limit=256KB;requested_bytes=20000;returned_bytes=20000;
        window_count=3;window_observations=3;capture_complete=$true;status='captured_for_offline_review';boot_authorized=$false;abi_proven=$false;runtime_compatibility_proven=$false;pe=@{size_of_image=0x200000};pdata_records=2;
        windows=@(foreach($spec in (Get-T7ReferenceWindows $schema)){
            $rva=$spec.RVA-$spec.Before;$begin=0x140000000L+$rva
            [pscustomobject]@{site=$spec.Name;rva=$spec.RVA;window_rva=$rva;window_bytes=$spec.Bytes;bytes_hex=('00'*$spec.Bytes);
                regions=@([pscustomobject]@{base=('0x{0:x}' -f $begin);size=$spec.Bytes;allocation_base='0x140000000';state=4096;protect=64;allocation_protect=64;type=16777216});
                runtime_function=[pscustomobject]@{begin_rva=$spec.RVA;end_rva=$spec.RVA+64;unwind_rva=4096;unwind_header_hex='01000000';unwind_format_validated=$false}}
        })}
}
$spec=@(Get-T7ReferenceWindows $schema)
Check ($spec.Count -eq 3 -and $spec[0].RVA -eq 0x1D7960 -and $spec[0].Before -eq 0x2A60 -and $spec[0].Bytes -eq 0x4000) 'Link band differs'
Check (($spec[0].RVA-$spec[0].Before) -eq 0x1D4F00 -and ($spec[0].RVA-$spec[0].Before+$spec[0].Bytes) -eq 0x1D8F00) 'Fixed band endpoints differ'
Check ($spec[1].RVA -eq 0x1D5FB0 -and $spec[2].RVA -eq 0x1D7260 -and $spec[1].Bytes -eq 256 -and $spec[2].Bytes -eq 256) 'Metadata anchors differ'
Check (($spec|Measure-Object Bytes -Sum).Sum -eq 16896) 'Fixed total differs'
Check ((Get-T7RefV2Outcome (New-Report) $identity 0 $module $schema) -ceq 'CaptureComplete') 'Complete V3 band refused'
Refuses {Get-T7RefV2Outcome (New-Report) $identity 0 $module}
Refuses {Get-T7ReferenceWindows @($schema)}
Refuses {Get-T7ReferenceWindows 'iw7.t7-prepatch-link-observation/2'}
foreach($change in @(
    {param($r)$r.windows[0].window_rva=0x1D7960},{param($r)$r.windows[0].window_bytes=4096},{param($r)$r.windows[1].site='DB_AddXAsset'},
    {param($r)$r.windows[1].rva++},{param($r)$r.window_count=1},{param($r)$r.requested_bytes=16895;$r.returned_bytes=16895},
    {param($r)$r.windows[0].bytes_hex='00'},{param($r)$r.windows[0].regions[0].size=16383},{param($r)$r.windows[0].runtime_function.end_rva=0x1D7960},
    {param($r)$r.windows[0].rva=@($r.windows[0].rva)},{param($r)$r.schema=@($r.schema)},{param($r)$r.windows[2].bytes_hex=@($r.windows[2].bytes_hex)},
    {param($r)$r.boot_authorized=$true},{param($r)$r.pdata_records=174763},{param($r)$r.pe.size_of_image=0x1D8EFF}
)){$report=New-Report;& $change $report;Refuses {Get-T7RefV2Outcome $report $identity 0 $module $schema}}
$report=New-Report;$report.capture_complete=$false;$report.status='incomplete_stop';$report.windows=@();$report.window_observations=0
Check ((Get-T7RefV2Outcome $report $identity 2 $module $schema) -ceq 'CapturePartial') 'Partial V3 report differs'
Refuses {Get-T7RefV2Outcome $report $identity 0 $module $schema}
[ordered]@{Schema='iw7.t7-link-v3-report-source-tests/3';Checks=$script:checks;Status='Passed';NativeExecuted=$false;LeaseAcquired=$false;OpaqueInputsRead=$false}|ConvertTo-Json
