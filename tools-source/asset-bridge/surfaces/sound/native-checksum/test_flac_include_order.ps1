param([Parameter(Mandatory)][string]$ProviderRoot,[string]$RetainedReceipt)
$ErrorActionPreference='Stop'
$provider=Join-Path $ProviderRoot 'completion.ps1'
if((Get-FileHash -LiteralPath $provider).Hash -ine '9710dd10beaa1db17d0bca51916679145f5d76460bc3c43463f888bc9aff3ad0'){throw 'Exact completion provider required'}
. $provider
. "$PSScriptRoot/FlacBuild.Profile.ps1"
function Add-Type {throw 'Include source test must not load native types'}
function Enter-IW7ResourceLease {throw 'Include source test must not acquire admission'}
$path=Join-Path ([IO.Path]::GetTempPath()) ('sound-flac-includes-'+[guid]::NewGuid().ToString('N')+'.log')
$culture=[Threading.Thread]::CurrentThread.CurrentCulture
$uiCulture=[Threading.Thread]::CurrentThread.CurrentUICulture
$expected=@('c:\fixture\a.h','c:\fixture\a_b.h','c:\fixture\i.h','c:\fixture\vcruntime-special.h','c:\fixture\vcruntime.h','c:\fixture\vcruntime_exception.h')
$checks=0;$replayed=0
try {
    # Explicit Python-compatible character ordering, including punctuation that
    # culture-sensitive Sort-Object places differently. No SDK source is read.
    $text=(@($expected[($expected.Count-1)..0])+'C:\FIXTURE\I.H'|ForEach-Object {'Note: including file:   '+$_}) -join "`n"
    foreach($name in 'en-US','fr-FR','tr-TR',''){
        [Threading.Thread]::CurrentThread.CurrentCulture=[Globalization.CultureInfo]::GetCultureInfo($name)
        [Threading.Thread]::CurrentThread.CurrentUICulture=[Globalization.CultureInfo]::GetCultureInfo($name)
        foreach($case in 'valid','wrong-order','missing','extra','different','relative'){
            $declared=@($expected);$actual=$text
            switch($case){
                'wrong-order' {$declared=@($expected[($expected.Count-1)..0])}
                'missing' {$declared=@($expected|Select-Object -Skip 1)}
                'extra' {$declared+='c:\fixture\unreviewed.h'}
                'different' {$actual=$actual.Replace('vcruntime.h','other.h')}
                'relative' {$actual+="`nNote: including file: relative.h"}
            }
            [IO.File]::WriteAllText($path,$actual,[Text.UTF8Encoding]::new($false))
            $guard=[IO.File]::Open($path,'Open','Read','Read');$failure=$null
            try{Assert-FlacIncludeBytes @{Image=$path;Bytes=$guard.Length} $declared {}}
            catch{$failure=$_.Exception.Message}
            finally{$guard.Dispose()}
            $checks++
            if($case -ceq 'valid' -and $failure){throw "Valid ordinal includes failed under '$name': $failure"}
            if($case -cne 'valid' -and !$failure){throw "Invalid includes accepted: $case"}
        }
    }
    if($RetainedReceipt){
        if((Get-Item -LiteralPath $RetainedReceipt).Length -gt 2MB){throw 'Bounded text receipt required'}
        $receipt=Get-Content -Raw -LiteralPath $RetainedReceipt|ConvertFrom-Json -AsHashtable
        if($receipt.schema -cne 'iw7.sound-flac-dump-build-receipt/1' -or $receipt.includes.Count -ne 9){throw 'Exact retained FLAC include inventory required'}
        foreach($name in $receipt.includes.Keys){
            $log=Join-Path (Split-Path $RetainedReceipt -Parent) ('logs/'+$name+'/stdout.log')
            $guard=[IO.File]::Open($log,'Open','Read','Read')
            try{Assert-FlacIncludeBytes @{Image=$log;Bytes=$guard.Length} $receipt.includes[$name].paths {}}
            finally{$guard.Dispose()}
            $replayed++
        }
    }
    [ordered]@{Cultures=4;Assertions=$checks;RetainedTextReports=$replayed;NativeTypesLoaded=$false;RealReservations=0;ArtifactsOpened=0;NativeBuildQualified=$false}|ConvertTo-Json
} finally {
    [Threading.Thread]::CurrentThread.CurrentCulture=$culture
    [Threading.Thread]::CurrentThread.CurrentUICulture=$uiCulture
    $full=[IO.Path]::GetFullPath($path);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$full.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($full) -notlike 'sound-flac-includes-*.log'){throw 'Unsafe synthetic log cleanup'}
    if(Test-Path -LiteralPath $full){Remove-Item -LiteralPath $full -Force}
}
