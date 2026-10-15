# Source declarations and bounded JSON diagnostics for the authored ModelFF route.
# These checks do not qualify FF geometry, image bytes, native ABI or rendering.
function Assert-ModelFFJsonKeys([System.Text.Json.JsonElement]$Element,[int]$Depth=0){
    if($Depth -gt 32){throw 'ModelFF JSON nesting exceeds 32.'}
    if($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Object){
        $keys=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach($property in $Element.EnumerateObject()){
            if(!$keys.Add($property.Name)){throw 'Duplicate ModelFF JSON property.'}
            Assert-ModelFFJsonKeys $property.Value ($Depth+1)
        }
    }elseif($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Array){
        foreach($item in $Element.EnumerateArray()){Assert-ModelFFJsonKeys $item ($Depth+1)}
    }
}
function ConvertTo-ModelFFRelativeOutputPath([string]$Path){
    if([string]::IsNullOrWhiteSpace($Path) -or $Path.Contains('\') -or $Path.Contains(':') -or
        $Path.StartsWith('/') -or $Path -match '[\x00-\x1f\x7f<>"|?*]'){
        throw 'Ordinary forward-slash relative ModelFF file path required.'
    }
    foreach($part in $Path.Split('/')){
        if(!$part -or $part -in '.','..' -or $part.EndsWith('.') -or $part.EndsWith(' ') -or
            $part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)'){
            throw 'Ordinary ModelFF path components required.'
        }
    }
    $Path
}
function Assert-ModelFFNativePathBudget([string]$RunRoot,[object[]]$Files){
    $root=[IO.Path]::GetFullPath($RunRoot)
    if(![IO.Path]::IsPathFullyQualified($RunRoot) -or $root -cne $RunRoot){throw 'Canonical ModelFF RunRoot required.'}
    foreach($item in $Files){
        if($item -isnot [string]){throw 'ModelFF output file paths must be strings.'}
        $relative=ConvertTo-ModelFFRelativeOutputPath $item
        $effective=[IO.Path]::GetFullPath((Join-Path $root $relative))
        if(!$effective.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
            throw 'ModelFF output path escaped RunRoot.'
        }
        # The native narrow stdio writer has no proven extended-path contract.
        # Include the terminator: a 260-character path is refused before a job.
        if($effective.Length -ge 260){throw ('ModelFF native path exceeds MAX_PATH budget ('+$effective.Length+' characters): '+$relative)}
    }
}
function Read-ModelFFOutputNamespacePlan([string]$Path,[string]$SHA256,[string]$RunRoot){
    if($SHA256 -cnotmatch '^[a-f0-9]{64}$' -or ![IO.Path]::IsPathFullyQualified($Path) -or [IO.Path]::GetFullPath($Path) -cne $Path){
        throw 'Canonical hash-bound ModelFF output namespace Source sidecar required.'
    }
    for($part=$Path;$part;$part=[IO.Path]::GetDirectoryName($part)){
        if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'ModelFF namespace Source reparse refused.'}
    }
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read');$handle=$stream.SafeFileHandle;$document=$null
    try{
        if($stream.Length -lt 1 -or $stream.Length -gt 1MB){throw 'ModelFF namespace Source sidecar exceeds one MiB.'}
        $raw=[byte[]]::new([int]$stream.Length);$stream.ReadExactly($raw)
        if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant() -cne $SHA256){throw 'ModelFF namespace Source hash differs.'}
        $text=[Text.UTF8Encoding]::new($false,$true).GetString($raw)
        $options=[System.Text.Json.JsonDocumentOptions]::new();$options.MaxDepth=32
        $document=[System.Text.Json.JsonDocument]::Parse($text,$options)
        $value=$document.RootElement;Assert-ModelFFJsonKeys $value
        if($value.ValueKind -ne [System.Text.Json.JsonValueKind]::Object){throw 'ModelFF namespace Source object required.'}
        $keys=@($value.EnumerateObject()|ForEach-Object Name)
        if(($keys|Sort-Object)-join ',' -cne 'Files,Schema,StockInputs'){throw 'Exact ModelFF namespace Source fields required.'}
        if($value.GetProperty('Schema').ValueKind -ne [System.Text.Json.JsonValueKind]::String -or
            $value.GetProperty('Schema').GetString() -cne 'iw7.model-ff-output-files/1'){
            throw 'ModelFF namespace Source schema differs.'
        }
        $lists=@{}
        foreach($field in 'Files','StockInputs'){
            $array=$value.GetProperty($field)
            if($array.ValueKind -ne [System.Text.Json.JsonValueKind]::Array -or !$array.GetArrayLength()){
                throw 'Nonempty ModelFF namespace Source file arrays required.'
            }
            $names=[Collections.Generic.List[string]]::new()
            $unique=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
            foreach($item in $array.EnumerateArray()){
                if($item.ValueKind -ne [System.Text.Json.JsonValueKind]::String){throw 'ModelFF namespace Source file entries must be strings.'}
                $name=ConvertTo-ModelFFRelativeOutputPath $item.GetString()
                if(!$unique.Add($name)){throw 'Duplicate ModelFF namespace Source file path.'}
                $names.Add($name)
            }
            $lists[$field]=[array]::AsReadOnly($names.ToArray())
        }
        $all=[Collections.Generic.HashSet[string]]::new([string[]]$lists.Files,[StringComparer]::OrdinalIgnoreCase)
        foreach($name in $lists.StockInputs){if(!$all.Contains('work/'+$name)){throw 'Every declared stock input must be declared in the full output namespace.'}}
        Assert-ModelFFNativePathBudget $RunRoot ([object[]]$lists.Files)
        [pscustomobject]@{Schema='iw7.model-ff-output-files/1';Files=$lists.Files;StockInputs=$lists.StockInputs;Path=$Path;Bytes=$raw.Length;SHA256=$SHA256}
    }finally{
        if($document){$document.Dispose()};$stream.Dispose()
        if(!$handle.IsClosed){throw 'Actual ModelFF namespace Source metadata handle remains open.'}
    }
}
function Assert-ModelFFNamespaceAuthorProject($Declaration,$ProjectFiles,$Descriptor){
    $expected=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($name in $ProjectFiles.PSObject.Properties.Name){
        if(!$expected.Add('author-project/'+(ConvertTo-ModelFFRelativeOutputPath $name))){throw 'Duplicate authored project recipe path.'}
    }
    foreach($property in $Descriptor.material_template.PSObject.Properties){
        if($property.Value -isnot [string] -or !$expected.Add('author-project/'+(ConvertTo-ModelFFRelativeOutputPath $property.Value))){throw 'Distinct authored template recipe paths required.'}
    }
    $declared=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($name in $Declaration.Files){if($name.StartsWith('author-project/',[StringComparison]::OrdinalIgnoreCase)){$null=$declared.Add($name)}}
    if(!$declared.SetEquals($expected)){throw 'Authored project/template paths differ from the sealed Source declaration.'}
}
function Assert-ModelFFNamespaceRequiredFFPaths($Namespace,$Plan){
    $required=[Collections.Generic.List[string]]::new();$required.Add('work/zonetool.exe')
    foreach($name in $Plan.source_files.PSObject.Properties.Name){$required.Add('work/'+(ConvertTo-ModelFFRelativeOutputPath $name))}
    foreach($item in $Plan.dump_files){
        if($item -isnot [string]){throw 'Actual ModelFF dump file path required.'}
        $name=ConvertTo-ModelFFRelativeOutputPath $item
        $required.Add('work/dump/'+$Plan.zone+'/'+$name);$required.Add('roundtrip/'+$name)
    }
    foreach($name in $required){if(!$Namespace.Files.ContainsKey($name)){throw ('Required ModelFF path absent from sealed Source namespace: '+$name)}}
}
function Assert-ModelFFNamespaceStockInputs($Declaration,$Inputs){
    $expected=[Collections.Generic.HashSet[string]]::new([string[]]$Declaration.StockInputs,[StringComparer]::OrdinalIgnoreCase)
    $actual=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($entry in $Inputs){
        if($entry.Relative -isnot [string]){throw 'Actual ModelFF stock input relative path required.'}
        $name=ConvertTo-ModelFFRelativeOutputPath $entry.Relative.Replace('\','/')
        if(!$actual.Add($name)){throw 'Duplicate actual ModelFF stock input.'}
    }
    if(!$expected.SetEquals($actual)){throw 'Actual ModelFF stock inputs differ from the sealed Source declaration.'}
}
function Assert-ModelFFNamespaceStage($Declaration,[string]$RunRoot,[string]$SourceRoot,$Plan,$WriterRecipe,[bool]$NativeClosure){
    $root=[IO.Path]::GetFullPath($RunRoot);$source=[IO.Path]::GetFullPath($SourceRoot)
    if(!$source.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
        throw 'Deferred ModelFF namespace stage must be inside RunRoot.'
    }
    for($part=$source;$part;$part=[IO.Path]::GetDirectoryName($part)){
        if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'ModelFF stage root or ancestor reparse refused before descent.'}
    }
    $prefix=[IO.Path]::GetRelativePath($root,$source).Replace('\','/')+'/'
    $expected=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($name in $Declaration.Files){if($name.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){$null=$expected.Add($name.Substring($prefix.Length))}}
    $recipe=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($name in @('model-ff-plan.json','evidence/material-inputs.json','evidence/writer/writer-source.json','evidence/writer/writer-provenance.json')){$null=$recipe.Add($name)}
    foreach($name in $Plan.source_files.PSObject.Properties.Name){$null=$recipe.Add((ConvertTo-ModelFFRelativeOutputPath $name))}
    foreach($name in $WriterRecipe.source_files.PSObject.Properties.Name){$null=$recipe.Add('evidence/writer/'+(ConvertTo-ModelFFRelativeOutputPath $name))}
    if($NativeClosure){$null=$recipe.Add('evidence/writer/writer-closure.json');$null=$recipe.Add('evidence/writer/writer-native-run.json')}
    if(!$expected.SetEquals($recipe)){throw 'Actual ModelFF stage recipe differs from the sealed Source declaration.'}
    $allowedDirectories=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($name in $recipe){
        for($parent=$name.LastIndexOf('/');$parent -ge 0;$parent=$name.LastIndexOf('/',$parent-1)){
            $null=$allowedDirectories.Add($name.Substring(0,$parent))
            if($parent -eq 0){break}
        }
    }
    $actual=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $pending=[Collections.Generic.Stack[string]]::new();$pending.Push($source)
    while($pending.Count){foreach($path in [IO.Directory]::EnumerateFileSystemEntries($pending.Pop())){
        $attributes=[IO.File]::GetAttributes($path)
        if($attributes -band [IO.FileAttributes]::ReparsePoint){throw 'ModelFF stage output reparse refused.'}
        if($attributes -band [IO.FileAttributes]::Directory){
            $relative=[IO.Path]::GetRelativePath($source,$path).Replace('\','/')
            if(!$allowedDirectories.Contains($relative)){throw 'Unexpected actual ModelFF stage directory outside sealed Source declaration.'}
            $pending.Push($path)
        }
        else{
            $relative=[IO.Path]::GetRelativePath($source,$path).Replace('\','/')
            if(!$actual.Add($relative) -or !$expected.Contains($relative)){throw 'Unexpected actual ModelFF stage file outside sealed Source declaration.'}
        }
    }}
    if(!$expected.SetEquals($actual)){throw 'Actual ModelFF stage files differ from the sealed Source declaration.'}
}
function Test-ModelFFJsonValueEqual([System.Text.Json.JsonElement]$Before,[System.Text.Json.JsonElement]$After){
    if($Before.ValueKind -ne $After.ValueKind){
        # Preserve the existing Python verifier's scalar numeric equality.
        if($Before.ValueKind -in [System.Text.Json.JsonValueKind]::True,[System.Text.Json.JsonValueKind]::False -and $After.ValueKind -eq [System.Text.Json.JsonValueKind]::Number){
            $truth=if($Before.ValueKind -eq [System.Text.Json.JsonValueKind]::True){1}else{0}
            if($After.GetRawText() -notmatch '[.eE]'){return [Numerics.BigInteger]::Parse($After.GetRawText(),[Globalization.CultureInfo]::InvariantCulture) -eq $truth}
            $number=$After.GetDouble();return [double]::IsFinite($number) -and $number -eq $truth
        }
        if($After.ValueKind -in [System.Text.Json.JsonValueKind]::True,[System.Text.Json.JsonValueKind]::False -and $Before.ValueKind -eq [System.Text.Json.JsonValueKind]::Number){return Test-ModelFFJsonValueEqual $After $Before}
        return $false
    }
    switch($Before.ValueKind.ToString()){
        Object {
            $beforeProperties=@($Before.EnumerateObject());$afterProperties=@($After.EnumerateObject())
            if($beforeProperties.Count -ne $afterProperties.Count){return $false}
            foreach($property in $beforeProperties){
                $found=[System.Text.Json.JsonElement]::new()
                if(!$After.TryGetProperty($property.Name,[ref]$found) -or !(Test-ModelFFJsonValueEqual $property.Value $found)){return $false}
            }
            return $true
        }
        Array {
            if($Before.GetArrayLength() -ne $After.GetArrayLength()){return $false}
            for($i=0;$i -lt $Before.GetArrayLength();$i++){if(!(Test-ModelFFJsonValueEqual $Before[$i] $After[$i])){return $false}}
            return $true
        }
        String {return [string]::Equals($Before.GetString(),$After.GetString(),[StringComparison]::Ordinal)}
        Number {
            $beforeText=$Before.GetRawText();$afterText=$After.GetRawText()
            $beforeInteger=$beforeText -notmatch '[.eE]';$afterInteger=$afterText -notmatch '[.eE]'
            if($beforeInteger -and $afterInteger){
                return [Numerics.BigInteger]::Parse($beforeText,[Globalization.CultureInfo]::InvariantCulture) -eq [Numerics.BigInteger]::Parse($afterText,[Globalization.CultureInfo]::InvariantCulture)
            }
            if($beforeInteger -or $afterInteger){
                $integerText=if($beforeInteger){$beforeText}else{$afterText}
                $float=if($beforeInteger){$After.GetDouble()}else{$Before.GetDouble()}
                return [double]::IsFinite($float) -and [math]::Truncate($float) -eq $float -and [Numerics.BigInteger]::Parse($integerText,[Globalization.CultureInfo]::InvariantCulture) -eq [Numerics.BigInteger]::new($float)
            }
            $first=$Before.GetDouble();$second=$After.GetDouble()
            return [double]::IsFinite($first) -and [double]::IsFinite($second) -and $first -eq $second
        }
        True {return $true}
        False {return $true}
        Null {return $true}
        default {return $false}
    }
}
function Assert-ModelFFDumpMaterialJson([IO.FileStream]$SourceGuard,[IO.FileStream]$DumpGuard){
    $documents=[Collections.Generic.List[IDisposable]]::new();$elements=[Collections.Generic.List[System.Text.Json.JsonElement]]::new()
    $hashes=[Collections.Generic.List[string]]::new();$lengths=[Collections.Generic.List[long]]::new()
    try{
        foreach($guard in @($SourceGuard,$DumpGuard)){
            if(!$guard -or !$guard.CanRead -or $guard.SafeFileHandle.IsClosed -or $guard.Length -lt 1 -or $guard.Length -gt 256KB){throw 'Held material JSON must be readable and bounded to 256 KiB each.'}
            $guard.Position=0;$raw=[byte[]]::new([int]$guard.Length);$guard.ReadExactly($raw);$guard.Position=0
            $text=[Text.UTF8Encoding]::new($false,$true).GetString($raw)
            $options=[System.Text.Json.JsonDocumentOptions]::new();$options.MaxDepth=32
            $document=[System.Text.Json.JsonDocument]::Parse($text,$options);$documents.Add($document)
            Assert-ModelFFJsonKeys $document.RootElement
            if($document.RootElement.ValueKind -ne [System.Text.Json.JsonValueKind]::Object){throw 'Authored material JSON object required.'}
            $elements.Add($document.RootElement);$hashes.Add([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant());$lengths.Add($raw.Length)
        }
        $before=$elements[0];$after=$elements[1]
        foreach($value in @($before,$after)){
            $techset=[System.Text.Json.JsonElement]::new()
            if(!$value.TryGetProperty('techniqueSet->name',[ref]$techset) -or $techset.ValueKind -ne [System.Text.Json.JsonValueKind]::String -or [string]::IsNullOrWhiteSpace($techset.GetString())){
                throw 'Authored material JSON requires literal techniqueSet->name.'
            }
        }
        foreach($property in $before.EnumerateObject()){
            $found=[System.Text.Json.JsonElement]::new()
            if(!$after.TryGetProperty($property.Name,[ref]$found) -or !(Test-ModelFFJsonValueEqual $property.Value $found)){
                throw ('Dumped authored material fields differ: '+$property.Name)
            }
        }
        [pscustomobject]@{Schema='iw7.model-ff-material-json-preflight/1';MetadataMatch=$true;
            TechniqueSetName=$before.GetProperty('techniqueSet->name').GetString();SourceBytes=$lengths[0];DumpBytes=$lengths[1];
            SourceSHA256=$hashes[0];DumpSHA256=$hashes[1];MaterialReadbackVerified=$false;Ready=$false}
    }finally{
        foreach($document in $documents){$document.Dispose()}
        foreach($guard in @($SourceGuard,$DumpGuard)){if($guard -and $guard.CanSeek){$guard.Position=0}}
    }
}
