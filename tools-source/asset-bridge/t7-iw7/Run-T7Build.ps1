# Default checks source/metadata only. Native execution needs a reviewed exact
# plan and separate coordinator GO; no ZoneTool/game launch exists in this runner.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell 7 required.'}
if($PlanSHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Exact reviewed plan SHA256 required.'}
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards}
$state=$null;$failure=$null;$created=$false;$launcher=$null;$priority=$null
function Open-T7Bootstrap($Path,[long]$Bytes,[string]$SHA256) {
    if(![IO.Path]::IsPathFullyQualified($Path) -or [IO.Path]::GetFullPath($Path) -cne $Path){throw 'Canonical bootstrap path required.'}
    for($part=$Path;$part;$part=[IO.Path]::GetDirectoryName($part)) {
        if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Bootstrap reparse path refused.'}
    }
    if($Bytes -le 0 -or $Bytes -gt 32MB -or $SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Invalid source binding.'}
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read');$guards.Add($stream)
    if($stream.Length -ne $Bytes){throw 'Bootstrap length differs.'}
    $hash=[Security.Cryptography.SHA256]::Create()
    try{$actual=[Convert]::ToHexString($hash.ComputeHash($stream)).ToLowerInvariant()}finally{$hash.Dispose()}
    if($actual -cne $SHA256){throw 'Bootstrap source differs.'}
    $stream.Position=0;return $stream
}
function Assert-T7BuildProfile($Plan,[string]$SourceRoot) {
    $profile=if($Plan.PSObject.Properties.Name -contains 'BuildProfile'){$Plan.BuildProfile}else{$null}
    $recompiled=$Plan.PSObject.Properties.Name -contains 'ReuseCompile' -and $null -ne $Plan.ReuseCompile -and
        $Plan.ReuseCompile.PSObject.Properties.Name -contains 'RecompiledMain' -and
        $Plan.ReuseCompile.RecompiledMain -is [bool] -and $Plan.ReuseCompile.RecompiledMain
    $cliMarker=$Plan.PSObject.Properties.Name -contains 'ReuseCompile' -and $null -ne $Plan.ReuseCompile -and
        $Plan.ReuseCompile.PSObject.Properties.Name -contains 'RecompiledZonetool'
    $publication=$null -ne $profile -and $profile.Name -ceq 't7-catalog-message-publication'
    if($cliMarker -and !$publication){throw 'CLI rebuild marker requires the publication profile.'}
    if($publication -and (!$cliMarker -or $Plan.ReuseCompile.RecompiledZonetool -isnot [bool] -or
        !$Plan.ReuseCompile.RecompiledZonetool)){throw 'Publication requires both fresh translation units.'}
    if($null -eq $profile) {
        if($recompiled){throw 'Recompiled main requires the explicit diagnostic profile.'}
        return $false
    }
    if(!$recompiled){throw 'Explicit profile requires a main rebuild.'}
    if($profile.Name -ceq 't7-prepatch-probe') {
        if($profile.Option -cne '-t7-prepatch-probe' -or $profile.ArgumentCount -ne 2 -or
           $profile.Report -cne 't7-prepatch-probe.local.json'){throw 'Exact pre-patch profile required.'}
        $paths=@{
            Helper=(Join-Path $Plan.PreparedRoot 'native_prepatch_probe.inc')
            Wiring=(Join-Path $SourceRoot 'prepare_prepatch.py')
            PreparedMain=(Join-Path $Plan.PreparedRoot 'main.cpp')
        }
    } elseif($profile.Name -cin @('t7-catalog-trace','t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication')) {
        $fields='ArgumentCount,BaseBuildPlan,BaseBuildReceipt,Name,Option,PreparedMain,TraceSchema,Wiring'
        if($profile.Name -cin @('t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication')) {
            if($profile.ContextSchema -cne 'iw7.t7-catalog-exit-context/1'){throw 'Exact exit-context schema required.'}
            $fields='ArgumentCount,BaseBuildPlan,BaseBuildReceipt,ContextSchema,Name,Option,PreparedMain,TraceSchema,Wiring'
        }
        if($profile.Name -cin @('t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication')) {
            if($profile.CallerSchema -cne 'iw7.t7-catalog-callers/1'){throw 'Exact caller schema required.'}
            $fields='ArgumentCount,BaseBuildPlan,BaseBuildReceipt,CallerSchema,ContextSchema,Name,Option,PreparedMain,TraceSchema,Wiring'
        }
        if($profile.Name -cin @('t7-catalog-message','t7-catalog-message-publication')) {
            if($profile.MessageSchema -cne 'iw7.t7-catalog-message/1'){throw 'Exact message schema required.'}
            $fields='ArgumentCount,BaseBuildPlan,BaseBuildReceipt,CallerSchema,ContextSchema,MessageSchema,Name,Option,PreparedMain,TraceSchema,Wiring'
        }
        if($publication) {
            if($profile.PublicationSchema -cne 'iw7.t7-message-publication-build/1') {throw 'Exact publication build schema required.'}
            $fields=(@($fields.Split(','))+@('PublicationSchema','PublicationWiring','PublicationSource','PreparedCLI',
                'MainResponse','CLIResponse','LinkResponse')|Sort-Object)-join ','
            if((@($Plan.Stages.Name)-join ',') -cne 'main,zonetool11,link') {throw 'Publication requires main,zonetool11,link in order.'}
        }
        if($profile.Option -cne '-t7-iw7-catalog' -or $profile.ArgumentCount -ne 3 -or
           $profile.TraceSchema -cne 'iw7.t7-catalog-trace/1' -or
           (@($profile.PSObject.Properties.Name|Sort-Object)-join ',') -cne $fields -or
           $profile.BaseBuildPlan.SHA256 -cne 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa' -or
           $profile.BaseBuildReceipt.SHA256 -cne 'c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2'){
            throw 'Exact catalogue trace profile and ordinary D2 proof required.'
        }
        $paths=@{
            Wiring=(Join-Path $SourceRoot 'prepare_catalog_trace.py')
            PreparedMain=(Join-Path $Plan.PreparedRoot 'main.cpp')
            BaseBuildPlan=$profile.BaseBuildPlan.Path
            BaseBuildReceipt=$profile.BaseBuildReceipt.Path
        }
        if($publication) {
            $responseRoot=Split-Path $Plan.PreparedRoot -Parent
            $paths.PublicationWiring=Join-Path $SourceRoot 'prepare_message_publication.py'
            $paths.PublicationSource=Join-Path $SourceRoot 'native_message_publication.inc'
            $paths.PreparedCLI=Join-Path $Plan.PreparedRoot 'zonetool.cpp'
            $paths.MainResponse=Join-Path $responseRoot 'main.obj.rsp'
            $paths.CLIResponse=Join-Path $responseRoot 'zonetool11.obj.rsp'
            $paths.LinkResponse=Join-Path $responseRoot 'link.rsp'
            foreach($row in @(@('main','MainResponse'),@('zonetool11','CLIResponse'),@('link','LinkResponse'))) {
                $stage=@($Plan.Stages|Where-Object Name -CEQ $row[0])[0]
                if(@($stage.Arguments).Count -ne 1 -or $stage.Arguments[0] -cne ('@'+$paths[$row[1]])) {
                    throw 'Publication stage must use its pinned response file.'
                }
                $image=if($row[0] -ceq 'link'){Join-Path (Split-Path $Plan.Compiler -Parent) 'link.exe'}else{$Plan.Compiler}
                if($stage.Image -cne $image){throw 'Publication stage image differs.'}
                $artifacts=@(if($row[0] -ceq 'link'){'zonetool-t7.exe','zonetool-t7.pdb','zonetool-t7.lib','zonetool-t7.exp'}
                    else{($row[0]+'.obj'),'compile.pdb','dependencies.json'})
                if((@($stage.Artifacts)-join ',') -cne ($artifacts-join ',')) {throw 'Publication stage artifact guards differ.'}
            }
        }
    } else {
        throw 'Unknown T7 build profile.'
    }
    foreach($name in $paths.Keys) {
        $pin=$profile.$name
        $limit=if($name -ceq 'BaseBuildPlan'){2MB}elseif($name -ceq 'BaseBuildReceipt'){128KB}
               elseif($name -ceq 'LinkResponse'){256KB}elseif($name -ceq 'PublicationSource'){16KB}else{64KB}
        if($pin.Path -cne $paths[$name] -or $pin.Bytes -le 0 -or $pin.Bytes -gt $limit -or
           $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Diagnostic source pin differs.'}
        $match=@($Plan.Bindings|Where-Object {$_.Path -ceq $pin.Path -and $_.IsText -is [bool] -and $_.IsText -and
            $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256})
        if($match.Count -ne 1){throw 'Diagnostic source pin is not guarded by the build.'}
    }
    return $true
}
function Assert-T7InputBindings($Plan) {
    # This runs before any binding is opened, binary metadata is queried or
    # provider is loaded. The legacy bound stays 128; the exact v2 closure is 141.
    $bindings=@($Plan.Bindings);$inputs=@($Plan.Inputs)
    if($bindings.Count -gt 141 -or $inputs.Count -gt 2048 -or
        @($bindings.Path|Sort-Object -Unique).Count -ne $bindings.Count -or
        @($inputs.Path|Sort-Object -Unique).Count -ne $inputs.Count){throw 'Input set bound/uniqueness differs.'}
    if(@($bindings|Where-Object {$_.IsText -isnot [bool]}).Count){throw 'Binding text/binary classification required.'}
    $reuse=if($Plan.PSObject.Properties.Name -contains 'ReuseCompile'){$Plan.ReuseCompile}else{$null}
    $v2=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'ResidentMultiSurfaceV2'
    if(!$v2) {
        if($bindings.Count -gt 128){throw 'Legacy input binding limit is 128.'}
        return
    }
    if($Plan.SourceCommit -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
        $Plan.BuildProfile.Name -cne 't7-catalog-message-publication' -or
        $Plan.BuildProfile.PublicationSchema -cne 'iw7.t7-message-publication-build/1' -or
        $reuse.RecompiledMain -isnot [bool] -or !$reuse.RecompiledMain -or
        $reuse.RecompiledZonetool -isnot [bool] -or !$reuse.RecompiledZonetool -or
        $reuse.PSObject.Properties.Name -contains 'ResidentSurfaceCountDiagnostic' -or
        $bindings.Count -ne 141 -or $inputs.Count -ne 1146 -or
        @($bindings|Where-Object IsText).Count -ne 135){throw 'Exact multisurface publication input profile required.'}
    # Check classification by the retained six-tool metadata inventory too.
    # Counts alone must not permit an EXE to become a pre-admission text read.
    $binaryRows=[Collections.Generic.List[string]]::new()
    foreach($pin in $bindings) {
        if($pin.IsText) {
            if([IO.Path]::GetExtension($pin.Path) -in @('.exe','.dll','.obj','.pdb','.lib','.res','.pch')){
                throw 'Opaque build input cannot be a text binding.'
            }
        } else {$binaryRows.Add([IO.Path]::GetFileName($pin.Path).ToLowerInvariant()+'|'+$pin.Bytes+'|'+$pin.SHA256+"`n")}
    }
    $binaryRows.Sort([StringComparer]::Ordinal);$binaryBytes=[Text.Encoding]::UTF8.GetBytes(($binaryRows -join ''))
    if($binaryBytes.Length -ne 494 -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($binaryBytes)).ToLowerInvariant() -cne
        '3d5bcf2d88a865efba3e9fea62c90949a7b44330631689946f733de3497cb89d'){throw 'Exact six binary metadata bindings required.'}
    $proof=$reuse.ResidentMultiSurfaceV2;$headers=$proof.AdditionalHeaderInputs
    $readSHA='d9cdd533796a9fe14e0d5140d8adcbf5cbc932fafd4c06e18a615d15199a2185'
    $compileSHA='a7083ce5b9ba2fe1421c4f8733cf1d1e0b286549dbc55a44f3ef30ceb3c05333'
    $linkSHA='70455d2f32a9b034dda20fbaf48443ee68a02e552381edbf88b19d219f1f66b2'
    if($proof.Schema -cne 'iw7.t7-resident-multi-surface-build/2' -or
        $proof.Header -cne 'prepared/t7_iw7_resident_model.hpp' -or
        $proof.PreviousSHA256 -cne '6d2da3d4f7c3d0686909dc488f3d176ee2dd250e8d43d9a3cd9bcfa701482777' -or
        $proof.SHA256 -cne '857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4' -or
        $proof.E7ReadSHA256 -cne $readSHA -or $proof.E7CompileSHA256 -cne $compileSHA -or
        $proof.E7LinkSHA256 -cne $linkSHA -or $proof.E7TranslationUnits -ne 413 -or $proof.E7Objects -ne 413 -or
        $headers.Count -ne 66 -or $headers.Bytes -ne 87204 -or @($headers.Inputs).Count -ne 66 -or
        $headers.E7ReadSHA256 -cne $readSHA -or $headers.E7CompileSHA256 -cne $compileSHA -or
        $headers.CompilerContextMatchesCLI -isnot [bool] -or !$headers.CompilerContextMatchesCLI){
        throw 'Complete pinned multisurface dependency proof required.'
    }
    $suffix='\src\zonetool\zonetool\iw7\assets\xsurface.cpp'
    $tu=$headers.E7TranslationUnit
    if(![IO.Path]::IsPathFullyQualified($tu) -or [IO.Path]::GetFullPath($tu) -cne $tu -or
        !$tu.EndsWith($suffix,[StringComparison]::Ordinal)){throw 'Exact IW7 writer source context required.'}
    $native=$tu.Substring(0,$tu.Length-$suffix.Length)
    $rows=[Collections.Generic.List[string]]::new();$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($pin in $headers.Inputs) {
        if(![IO.Path]::IsPathFullyQualified($pin.Path) -or [IO.Path]::GetFullPath($pin.Path) -cne $pin.Path -or
            !$seen.Add($pin.Path) -or $pin.Bytes -le 0 -or $pin.Bytes -gt 16KB -or
            $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Canonical unique bounded header pin required.'}
        $relative=[IO.Path]::GetRelativePath($native,$pin.Path).Replace('\','/').ToLowerInvariant()
        $rows.Add($relative+'|'+$pin.Bytes+'|'+$pin.SHA256+"`n")
        $input=@($inputs|Where-Object {$_.Path -ceq $pin.Path -and $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256})
        $binding=@($bindings|Where-Object {$_.Path -ceq $pin.Path -and $_.Bytes -eq $pin.Bytes -and
            $_.SHA256 -ceq $pin.SHA256 -and $_.IsText})
        if($input.Count -ne 1 -or $binding.Count -ne 1){throw 'Header proof/Inputs/text Bindings bijection differs.'}
    }
    # Canonical sorted relative-path|raw-bytes|SHA256 LF rows from the reviewed
    # MULTISURFACE_HEADER_PINS table. Do not duplicate or discover native files.
    $rows.Sort([StringComparer]::Ordinal);$bytes=[Text.Encoding]::UTF8.GetBytes(($rows -join ''))
    if($bytes.Length -ne 7676 -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() -cne
        '5ee7ea0b46848bca9f4d365d0035cf070b2f57c6723019ab1288a54a93a7297b'){throw 'Reviewed 66-header pin inventory differs.'}
    $pch=$headers.PCHExcludedForPreparedYMinus
    if(![IO.Path]::IsPathFullyQualified($pch) -or [IO.Path]::GetFullPath($pch) -cne $pch -or
        !$pch.EndsWith('\obj\community.pch',[StringComparison]::Ordinal)){throw 'Exact excluded E7 PCH required.'}
    $obj=Split-Path $pch -Parent
    foreach($row in @(@('CL.read.1.tlog',$readSHA,15206288,15206288),
        @('CL.command.1.tlog',$compileSHA,1,4MB),@('link.command.1.tlog',$linkSHA,1,256KB))) {
        $path=Join-Path $obj ('tlog/'+$row[0])
        if(@($bindings|Where-Object {$_.Path -ieq $path -and $_.IsText -and $_.SHA256 -ceq $row[1] -and
            $_.Bytes -ge $row[2] -and $_.Bytes -le $row[3]}).Count -ne 1){throw 'Sealed E7 journal text binding absent.'}
    }
    if(@($proof.DependencyJSON).Count -ne 3 -or @($reuse.StageRoots).Count -ne 1){throw 'Exact retained dependency proof required.'}
    $oldRun=Split-Path $reuse.StageRoots[0] -Parent
    $depPins=@(@('helper',16296,'6897d27e8fe0754509e52258082d6178c8cb74fe21a8ef4b006006e97ab9dd12'),
        @('zonetool11',76744,'cfe62be9ce9bf87abd8e6713f1e1f334d76f69472500d2cb260696de26ee8273'),
        @('xpak',64444,'3d742923def4fb049d82853ac0e776ffd071228deaf1da1a624603d10dfd3908'))
    foreach($row in $depPins) {
        $path=Join-Path $oldRun ($row[0]+'/dependencies.json')
        foreach($set in @(@($proof.DependencyJSON),$bindings)) {
            if(@($set|Where-Object {$_.Path -ceq $path -and $_.Bytes -eq $row[1] -and $_.SHA256 -ceq $row[2]}).Count -ne 1){
                throw 'Pinned C dependency JSON or binding differs.'
            }
        }
        if(@($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText}).Count -ne 1){throw 'C dependency JSON must be text.'}
    }
    if(@($proof.SourceTransitions).Count -ne 3){throw 'Exact three source transitions required.'}
    $rows.Clear()
    foreach($row in $proof.SourceTransitions) {
        $rows.Add((@($row.Path,$row.PreviousBytes,$row.PreviousSHA256,$row.Bytes,$row.SHA256,$row.WiredBytes,$row.WiredSHA256)-join '|')+"`n")
        $path=Join-Path (Split-Path $Plan.PreparedRoot -Parent) $row.Path
        if(@($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -and $_.Bytes -eq $row.WiredBytes -and
            $_.SHA256 -ceq $row.WiredSHA256}).Count -ne 1){throw 'Wired v2 transition binding differs.'}
    }
    $rows.Sort([StringComparer]::Ordinal);$bytes=[Text.Encoding]::UTF8.GetBytes(($rows -join ''))
    if($bytes.Length -ne 714 -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() -cne
        'e1b572bfacbce89260ffce52d21c26e15f2ae2aa5172256cd063797b9a0f1b1c'){throw 'Reviewed v2 source transitions differ.'}
}
function Split-T7ResponseArguments([string]$Text) {
    # Deliberately bounded MSVC response syntax: space/tab separators and quoted
    # segments within arguments. Escaped/doubled or unclosed quotes are refused,
    # not guessed; the generator never needs them for these file destinations.
    if($Text -match '[\x00-\x08\x0a-\x1f\x7f]|\\+"|""' -or $Text.Contains('@')) {
        throw 'Unsupported or indirect publication response syntax.'
    }
    $arguments=[Collections.Generic.List[string]]::new()
    $token=[Text.StringBuilder]::new();$quoted=$false
    foreach($character in $Text.ToCharArray()) {
        if($character -eq '"') {$quoted=!$quoted;continue}
        if(!$quoted -and ($character -eq ' ' -or $character -eq "`t")) {
            if($token.Length){$arguments.Add($token.ToString());$null=$token.Clear()}
        } else {$null=$token.Append($character)}
    }
    if($quoted){throw 'Unclosed publication response quote.'}
    if($token.Length){$arguments.Add($token.ToString())}
    return ,$arguments.ToArray()
}
function Assert-T7ResponseOutputs([string[]]$Arguments,[System.Collections.IDictionary]$Outputs) {
    $seen=@{}
    for($index=0;$index -lt $Arguments.Count;$index++) {
        $argument=$Arguments[$index]
        if($argument -notmatch '^[-/]'){continue}
        $option=$argument.Substring(1)
        # This existing linker flag shares PDB's prefix but takes no filename.
        if($option -ieq 'PDBCompress'){continue}
        foreach($name in $Outputs.Keys) {
            if(!$option.StartsWith($name,[StringComparison]::OrdinalIgnoreCase)){continue}
            if($seen.ContainsKey($name)){throw 'Duplicate publication output option.'}
            $seen[$name]=$true
            $value=$option.Substring($name.Length)
            if($value.StartsWith(':')){$value=$value.Substring(1)}
            if(!$value) {
                $index++
                if($index -ge $Arguments.Count){throw 'Missing publication output value.'}
                $value=$Arguments[$index]
            }
            if($value -cne $Outputs[$name]){throw 'Publication output must belong to its exact fresh stage.'}
            break
        }
    }
    if($seen.Count -ne $Outputs.Count){throw 'Missing publication output option.'}
}
function Assert-T7PublicationResponses($Plan,[string]$MainResponse,[string]$CLIResponse,[string]$LinkResponse) {
    # Pure text validation, only for the new profile. The caller already guards
    # these exact response files by length/hash; no binary input is read here.
    foreach($row in @(@('main','main.cpp',$MainResponse),@('zonetool11','zonetool.cpp',$CLIResponse))) {
        $name=$row[0];$text=$row[2];$stageRoot=Join-Path $Plan.RunRoot $name
        $arguments=Split-T7ResponseArguments $text.TrimEnd("`r","`n")
        Assert-T7ResponseOutputs $arguments ([ordered]@{
            Fo=(Join-Path $stageRoot ($name+'.obj'));Fd=(Join-Path $stageRoot 'compile.pdb')
            sourceDependencies=(Join-Path $stageRoot 'dependencies.json')
        })
        if(!$arguments.Count -or $arguments[-1] -cne (Join-Path $Plan.PreparedRoot $row[1])) {throw 'Exact prepared compile source required.'}
    }
    $lines=@($LinkResponse.TrimEnd("`r","`n") -split "`r?`n")
    if($lines.Count -ne 414 -or $lines[0] -match '(?i)\.obj\b|@') {throw 'Exact direct 413-object link required.'}
    $linkRoot=Join-Path $Plan.RunRoot 'link'
    Assert-T7ResponseOutputs (Split-T7ResponseArguments $lines[0]) ([ordered]@{
        OUT=(Join-Path $linkRoot 'zonetool-t7.exe');PDB=(Join-Path $linkRoot 'zonetool-t7.pdb')
        IMPLIB=(Join-Path $linkRoot 'zonetool-t7.lib')
    })
    $objects=@();$unique=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($line in $lines[1..413]) {
        if($line -notmatch '^"([^"\r\n]+\.obj)"$') {throw 'Direct quoted link object required.'}
        $path=$Matches[1]
        if(!$unique.Add($path)){throw 'Duplicate publication link object.'}
        $objects+=$path
    }
    foreach($name in 'main','zonetool11') {
        $objectMatches=@($objects|Where-Object {[IO.Path]::GetFileName($_) -ieq ($name+'.obj')})
        $expected=Join-Path (Join-Path $Plan.RunRoot $name) ($name+'.obj')
        if($objectMatches.Count -ne 1 -or $objectMatches[0] -cne $expected) {throw 'Publication link refuses a retained main or CLI object.'}
    }
    if(@($Plan.ReuseCompile.StageRoots).Count -ne 1){throw 'Publication retains only xpak dependencies.'}
    $objectMatches=@($objects|Where-Object {[IO.Path]::GetFileName($_) -ieq 'xpak.obj'})
    if($objectMatches.Count -ne 1 -or $objectMatches[0] -cne (Join-Path $Plan.ReuseCompile.StageRoots[0] 'xpak.obj')) {
        throw 'Exact retained xpak object required.'
    }
}
try {
    $planSize=(Get-Item -LiteralPath $PlanPath).Length
    if($planSize -gt 2MB){throw 'Plan exceeds 2 MiB.'}
    $planStream=Open-T7Bootstrap $PlanPath $planSize $PlanSHA256
    $reader=[IO.StreamReader]::new($planStream,[Text.Encoding]::UTF8,$true,4096,$true)
    try{$plan=$reader.ReadToEnd()|ConvertFrom-Json -Depth 25}finally{$reader.Dispose()}
    if($plan.Schema -cne 'iw7.t7-minimal-build-plan/1' -or $plan.Runner -cne $PSCommandPath -or
       $plan.Profile -cne (Join-Path $PSScriptRoot 'T7Build.Profile.ps1')){throw 'Exact T7 runner/profile required.'}
    if($plan.PhysicalBytes -ne 4GB -or $plan.CommitBytes -ne 6GB -or $plan.GroupDeadlineSeconds -ne 600 -or
       $plan.OutputLimitBytes -ne 256MB -or $plan.MetadataReserveBytes -ne 1MB -or $plan.CleanupSeconds -ne 5 -or
       $plan.ReusedObjects -ne 410 -or $plan.ReusedProjectLibraries -ne 18 -or $plan.ReusedResources -ne 1){throw 'Fixed minimal build limits differ.'}
    $reuse=$plan.PSObject.Properties.Name -contains 'ReuseCompile' -and $null -ne $plan.ReuseCompile
    $recompiled=Assert-T7BuildProfile $plan $PSScriptRoot
    $buildProfile=if($recompiled){$plan.BuildProfile}else{$null}
    $publication=$null -ne $buildProfile -and $buildProfile.Name -ceq 't7-catalog-message-publication'
    $names=@(if($publication){'main','zonetool11','link'}elseif($recompiled){'main','link'}elseif($reuse){'link'}else{'helper','probe','main','zonetool11','xpak','link'})
    if(@($plan.Stages).Count -ne $names.Count -or (@($plan.Stages.Name)-join ',') -cne ($names-join ',')){throw 'Exact full, retained-link or diagnostic main/link stages required.'}
    Assert-T7InputBindings $plan
    foreach($pin in $plan.Bindings) {
        if($pin.IsText -isnot [bool]){throw 'Binding text/binary classification required.'}
        if($pin.IsText){$null=Open-T7Bootstrap $pin.Path $pin.Bytes $pin.SHA256}
        elseif((Get-Item -LiteralPath $pin.Path).Length -ne $pin.Bytes){throw 'Binary metadata changed.'}
    }
    foreach($required in @($plan.Runner,$plan.Profile,$plan.Core,$plan.CompilerCore,$plan.ObserverSource,$plan.CompilerPolicySource,$plan.Scheduler)) {
        if(@($plan.Bindings|Where-Object {$_.Path -ceq $required -and $_.IsText}).Count -ne 1){throw 'Exact source provider pin missing.'}
    }
    if($publication) {
        Assert-T7PublicationResponses $plan ([IO.File]::ReadAllText($plan.BuildProfile.MainResponse.Path)) `
            ([IO.File]::ReadAllText($plan.BuildProfile.CLIResponse.Path)) ([IO.File]::ReadAllText($plan.BuildProfile.LinkResponse.Path))
    }
    . $plan.Core
    $runtime=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../runtime'))
    Assert-H1Path $plan.RunRoot
    if([IO.Path]::GetDirectoryName($plan.RunRoot) -cne $runtime -or (Test-Path -LiteralPath $plan.RunRoot)){throw 'Fresh output directly under owned runtime required.'}
    foreach($stage in $plan.Stages) {
        $expectedType=if($stage.Name -ceq 'probe'){'Probe'}elseif($stage.Name -ceq 'link'){'Link'}else{'Compile'}
        $expectedSeconds=if($expectedType -ceq 'Probe'){15}else{120}
        if($stage.Stage -cne $expectedType -or $stage.DeadlineSeconds -ne $expectedSeconds){throw 'Fixed stage profile differs.'}
        Assert-H1Path $stage.Image
    }
    foreach($pin in $plan.Inputs) {
        Assert-H1Path $pin.Path
        if((Get-Item -LiteralPath $pin.Path).Length -ne $pin.Bytes){throw 'Recorded input metadata differs.'}
    }
    if($reuse) {
        $prior=Read-H1SmallJson $plan.ReuseCompile.Receipt
        if($prior.Schema -cne 'iw7.t7-minimal-build/1' -or $prior.Status -cne 'Failed' -or
           $prior.TreeClosureConfirmed -isnot [bool] -or !$prior.TreeClosureConfirmed -or
           $prior.LeaseReleased -isnot [bool] -or !$prior.LeaseReleased -or
           $prior.Quarantined -isnot [bool] -or $prior.Quarantined -or
           $prior.PlanSHA256 -cne $plan.ReuseCompile.SourcePlanSHA256 -or $plan.ReuseCompile.Checks -ne 51){throw 'Retained compile proof differs.'}
        foreach($name in 'helper','probe','main','zonetool11','xpak') {
            $row=@($prior.Stages|Where-Object Name -CEQ $name)
            if($row.Count -ne 1 -or $row[0].ExitCode -ne 0 -or !$row[0].TreeClosureConfirmed){throw 'Retained sub-stage was not successful and closed.'}
        }
        if(@($prior.Stages|Where-Object Name -CEQ 'probe')[0].Checks -ne 51){throw 'Retained name probe differs.'}
        foreach($required in @($plan.ReuseCompile.Receipt,$plan.ReuseCompile.SourcePlan)) {
            if(@($plan.Bindings|Where-Object {$_.Path -ceq $required -and $_.IsText}).Count -ne 1){throw 'Retained receipt/plan binding absent.'}
        }
        $priorPlan=Read-H1SmallJson $plan.ReuseCompile.SourcePlan 2MB
        $retainedNames=@(if($publication){'xpak'}elseif($recompiled){'zonetool11','xpak'}else{'main','zonetool11','xpak'})
        $retainedRoots=@($retainedNames|ForEach-Object {Join-Path $priorPlan.RunRoot $_})
        if((@($plan.ReuseCompile.StageRoots)-join '|') -cne ($retainedRoots-join '|')){throw 'Exact retained dependency roots required.'}
    }
    if(!$Run) {
        [ordered]@{Schema='iw7.t7-minimal-build-check/1';PlanSHA256=$PlanSHA256;Stages=@($plan.Stages).Count;ReusedCompilation=$reuse;BuildProfile=$buildProfile;
            ExpectedInputs=@($plan.Inputs).Count;MissingExpectedPins=@($plan.MissingExpectedPins).Count;
            NativeTypesLoaded=$false;BinaryInputsHashed=$false;LeaseAcquired=$false;RunRootCreated=$false;Ready=$false}|ConvertTo-Json
        return
    }
    if($plan.InputPinsComplete -isnot [bool] -or !$plan.InputPinsComplete -or @($plan.MissingExpectedPins).Count){throw 'Complete reviewed expected input pins required before native GO.'}
    if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7.H1Diagnostics.JobMembers' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Fresh PowerShell host required.'}
    . $plan.Scheduler
    $state=[ordered]@{Schema='iw7.t7-minimal-build/1';PlanSHA256=$PlanSHA256;Status='Pending';Ready=$false;BuildProfile=$buildProfile;
        EstimatesAreMeasured=$false;TreeClosureConfirmed=$true;LeaseReleased=$false;Quarantined=$false;
        MaxObservedOutputBytes=0L;CompilerTelemetry=[ordered]@{Completed=$false};Stages=[Collections.Generic.List[object]]::new()}
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Build -PhysicalBytes $plan.PhysicalBytes -CommitBytes $plan.CommitBytes -Owner 'T7 three TU build and name helper'
    $state.LeaseToken=$context.Lease.Token;$script:T7GroupStarted=Get-H1Clock
    if(Test-Path -LiteralPath $plan.RunRoot){throw 'Output appeared during admission.'}
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$created=$true
    . $plan.CompilerPolicySource
    . $plan.CompilerCore
    . $plan.Profile
    $launcher=Get-Process -Id $PID;$priority=$launcher.PriorityClass;$launcher.PriorityClass='BelowNormal'
    # No binary contents are read until the one account-wide reservation exists.
    foreach($pin in @($plan.Inputs)+@($plan.Bindings|Where-Object {!$_.IsText})){Open-T7Pin $pin $context}
    if($reuse){foreach($root in $plan.ReuseCompile.StageRoots){Assert-T7Dependencies $plan $root}}
    $null=[Reflection.Assembly]::LoadFrom($plan.JobAssembly)
    Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    Add-Type -LiteralPath $plan.ObserverSource
    Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    foreach($stage in $plan.Stages) {
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
        if(!$context.Closed){throw 'Previous original job not closed.'}
        $script:T7CurrentStage=$stage
        $stageRoot=Join-Path $plan.RunRoot $stage.Name
        [IO.Directory]::CreateDirectory($stageRoot)|Out-Null
        $stageState=[ordered]@{Stage=$stage.Stage;Name=$stage.Name;PlanSHA256=$PlanSHA256;DeadlineSeconds=$stage.DeadlineSeconds;
            MaxObservedOutputBytes=$state.MaxObservedOutputBytes;TreeClosureConfirmed=$false;
            CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
        $state.Stages.Add($stageState)
        $stageStarted=Get-H1Clock
        $image=if($stage.Stage -ceq 'Probe'){@($state.Stages[0].Artifacts|Where-Object Path -CEQ $stage.Image)[0]}
               else{@($plan.Bindings|Where-Object Path -CEQ $stage.Image)[0]}
        $start=New-T7Start $plan $stage $stageRoot
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
        Invoke-T7OwnedStage $plan $stageState $context $start $image.SHA256 $stageRoot $stageStarted
        $stageState.Artifacts=@(Get-H1CompilerArtifacts $plan $context)
        if($stageState.CompilerTelemetry.Completed) {
            foreach($prior in $stageState.CompilerTelemetry.Artifacts) {
                $now=@($stageState.Artifacts|Where-Object Path -CEQ $prior.Path)
                if($now.Count -ne 1 -or $now[0].SHA256 -cne $prior.SHA256 -or $now[0].Bytes -ne $prior.Bytes){throw 'Artifact changed across compiler cleanup.'}
            }
        }
        if($stage.Stage -ceq 'Compile'){Assert-T7Dependencies $plan $stageRoot}
        if($stage.Stage -ceq 'Probe') {
            $stdout=Join-Path $stageRoot 'stdout.log';$stderr=Join-Path $stageRoot 'stderr.log'
            if((Get-Item -LiteralPath $stdout).Length -gt 128 -or (Get-Item -LiteralPath $stderr).Length -ne 0){throw 'Name helper output differs.'}
            $observed=[IO.File]::ReadAllText($stdout)
            if($observed -cne "T7_ASSET_NAME_CHECKS=51`n" -and $observed -cne "T7_ASSET_NAME_CHECKS=51`r`n"){throw 'Exactly 51 native name checks required.'}
            $stageState.Checks=51
        }
        Test-H1Budget $plan $stageState
        Assert-H1Deadline $stageStarted $stage.DeadlineSeconds
        $state.MaxObservedOutputBytes=[math]::Max($state.MaxObservedOutputBytes,$stageState.MaxObservedOutputBytes)
    }
    foreach($pin in $plan.Inputs){Open-T7Pin $pin $context}
    foreach($pin in $plan.Bindings){$guard=Open-H1Pin $pin;try{}finally{$guard.Dispose()};Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds}
    Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    $state.ElapsedMs=(Get-H1Clock)-$script:T7GroupStarted
    $state.InputsReverified=$true;$state.CandidateExecuted=$false
}catch{
    $failure=$_
    if($state){$state.Status='Failed';$state.Error=$_.Exception.Message}
}finally{
    if($state){Complete-H1Stage $context $state}
    if($launcher -and $null -ne $priority){try{$launcher.PriorityClass=$priority}catch{if(!$failure){$failure=$_};$state.Status='Failed'}}
    if($context.Closed -and !$context.Lease){foreach($guard in $guards){$guard.Dispose()};$guards.Clear()}
    if($state -and $created) {
        try {
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            if(!$failure -and $context.Closed -and !$context.Lease){$state.Status='Passed'}
        }catch{
            if(!$failure){$failure=$_}
            if($state.Status -cne 'Quarantined'){$state.Status='Failed'}
            $state.GroupDeadlineError=$_.Exception.Message
        }
        $state.ElapsedMs=(Get-H1Clock)-$script:T7GroupStarted
        $state.FinishedUtc=[datetime]::UtcNow.ToString('o')
        try{Write-H1Receipt $plan $state $plan.RunRoot}catch{if(!$failure){$failure=$_};Write-Warning $_.Exception.Message}
        if(!$failure) {
            try{Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds}
            catch {
                $failure=$_;$state.Status='Failed';$state.GroupDeadlineError=$_.Exception.Message
                $state.ElapsedMs=(Get-H1Clock)-$script:T7GroupStarted
                # A slow publication must not leave a canonical Passed receipt.
                # Preserve the late attempt, then publish failure diagnostics.
                try {
                    $receipt=Join-Path $plan.RunRoot 'receipt.json'
                    $late=Join-Path $plan.RunRoot 'receipt.deadline-exceeded.json'
                    Assert-H1Path $receipt;Assert-H1Path $late
                    [IO.File]::Move($receipt,$late)
                    Write-H1Receipt $plan $state $plan.RunRoot
                }catch{Write-Warning ('Late receipt failure: '+$_.Exception.Message)}
            }
        }
    }
}
if($failure){throw $failure}
if(!$state.LeaseReleased -or $state.Status -cne 'Passed'){throw 'Build did not close and release successfully.'}
[ordered]@{Status=$state.Status;Receipt=(Join-Path $plan.RunRoot 'receipt.json');CandidateExecuted=$false;Ready=$false}|ConvertTo-Json
