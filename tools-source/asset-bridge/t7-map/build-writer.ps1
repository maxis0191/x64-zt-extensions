param([Parameter(Mandatory)][string]$ZoneToolSource)  # pinned x64-zt checkout (fab9358), read-only
# Compiles kino-writer.exe (one translation unit, pinned ZoneTool headers only).
$ErrorActionPreference='Stop'
$vs=& "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -products * -version "[17.0,18.0)" -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1
$vc=Get-ChildItem "$vs\VC\Tools\MSVC" -Directory | Sort-Object Name -Descending | Select-Object -First 1 -ExpandProperty FullName
$sdk="${env:ProgramFiles(x86)}\Windows Kits\10"
$sv=Get-ChildItem "$sdk\Include" -Directory | Where-Object Name -match '^10\.0\.\d+\.0$' | Sort-Object {[version]$_.Name} -Descending | Select-Object -First 1 -ExpandProperty Name
$inc=@("$vc\include","$sdk\Include\$sv\ucrt","$sdk\Include\$sv\shared","$sdk\Include\$sv\um","$ZoneToolSource\src\zonetool") | ForEach-Object {"/I$_"}
Set-Location $PSScriptRoot
& "$vc\bin\Hostx64\x64\cl.exe" /nologo /std:c++20 /EHsc /O2 /D_CRT_SECURE_NO_WARNINGS /MD /W3 /bigobj @inc kino_writer.cpp /Fe:kino-writer.exe /link "/LIBPATH:$vc\lib\x64" "/LIBPATH:$sdk\Lib\$sv\ucrt\x64" "/LIBPATH:$sdk\Lib\$sv\um\x64" user32.lib kernel32.lib
exit $LASTEXITCODE
