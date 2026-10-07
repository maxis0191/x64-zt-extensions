param([Parameter(Mandatory)][string]$OutputRoot,[switch]$Download)
$ErrorActionPreference='Stop'
$url='https://download.blender.org/release/Blender4.2/blender-4.2.23-windows-x64.zip'
$checksumUrl='https://download.blender.org/release/Blender4.2/blender-4.2.23.sha256'
$sha='82E791475779A7342424A480BDDE9A20B43710DA9264C60346125AA16CD910CB'
$root=[IO.Path]::GetFullPath($OutputRoot)
$plan=[ordered]@{Schema='iw7.blender-acquisition/1';Version='4.2.23 LTS';Source=$url;ChecksumSource=$checksumUrl;SHA256=$sha;
    OutputRoot=$root;Downloaded=$false;Extracted=$false;Executed=$false;GlobalInstalled=$false;
    FutureArguments=@('--factory-startup','--disable-autoexec','--background','--threads','4');HeavyExecutionRequiresAdmission=$true}
if(!$Download){$plan | ConvertTo-Json;return}
if(Test-Path -LiteralPath $root){throw 'Fresh acquisition directory required; preserve an existing tool/download.'}
[IO.Directory]::CreateDirectory($root) | Out-Null
$checksum=Join-Path $root 'blender-4.2.23.sha256'
Invoke-WebRequest -Uri $checksumUrl -OutFile $checksum -TimeoutSec 30
$expectedLine=$sha.ToLowerInvariant()+'  blender-4.2.23-windows-x64.zip'
if(@([IO.File]::ReadAllLines($checksum) | Where-Object { $_.Trim() -ceq $expectedLine }).Count -ne 1){throw 'Official checksum does not match reviewed archive tuple.'}
$archive=Join-Path $root 'blender-4.2.23-windows-x64.zip'
Invoke-WebRequest -Uri $url -OutFile $archive -TimeoutSec 600
if((Get-FileHash -LiteralPath $archive).Hash -cne $sha){throw 'Blender download hash mismatch; preserve failed download.'}
$plan.Downloaded=$true;$plan.Bytes=(Get-Item -LiteralPath $archive).Length;$plan.ObservedUtc=[datetime]::UtcNow.ToString('o')
$plan | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'acquisition.local.json')
$plan | ConvertTo-Json
