param([Parameter(Mandatory)][string]$Workspace,[string]$Output,[string[]]$Only=@())
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$Workspace=(Resolve-Path -LiteralPath $Workspace).Path
if(!$Output){$Output=Join-Path $root ('runtime/checks-'+[guid]::NewGuid().ToString('N'))}
$recipe=Join-Path $root 'ops/check_product.py'
if(!(Test-Path -LiteralPath $recipe)){
    $lock=Get-Content -LiteralPath (Join-Path $root 'dependency-package.json') -Raw | ConvertFrom-Json
    $recipe=Join-Path $root ('runtime/bootstrap/'+$lock.sha256+'/check_product.py')
}
& python -B (Join-Path (Split-Path $recipe -Parent) 'check_boundaries.py') $root
if($LASTEXITCODE){throw 'Product ownership gate failed.'}
# Some frozen tests read product.json, which only the checkout has: they find the checkout through this variable.
$env:IW7_PRODUCT_ROOT=$root
# A full run judges a head: those checkout tests must see exactly that head, so the tree must be clean throughout.
$judged=$null
if(!$Only -and (Test-Path -LiteralPath (Join-Path $root '.git'))){
    if(@(& git -C $root status --porcelain).Count){throw 'The full run judges a head: commit or set aside every change first (git status --porcelain is not empty).'}
    $judged=(& git -C $root rev-parse HEAD)
    & git -C $root rev-parse --verify --quiet origin/main *> $null
    if(!$LASTEXITCODE){
        & git -C $root diff --check origin/main...HEAD
        if($LASTEXITCODE){throw 'git diff --check origin/main...HEAD found whitespace errors.'}
    }
}
# -Only <id>[,<id>...] runs a subset (docs/CHECKS.md); the full run stays the judge for a merge.
$selection=@();foreach($id in @($Only -split ',' | Where-Object {$_})){$selection+=@('--only',$id.Trim())}
& python -B $recipe --project $root --workspace $Workspace --output $Output @selection
if($LASTEXITCODE){
    $resultsPath=Join-Path $Output 'results.json'
    if(Test-Path -LiteralPath $resultsPath){
        $results=Get-Content -LiteralPath $resultsPath -Raw | ConvertFrom-Json
        foreach($failure in @($results.results | Where-Object exit_code -NE 0)){
            Write-Output ("Failed source check: "+$failure.id)
            Get-Content -LiteralPath (Join-Path $Output $failure.log) -Tail 100
        }
    }
    throw 'Source checks failed. See the retained results.json and logs.'
}
if($judged){
    if(@(& git -C $root status --porcelain).Count -or (& git -C $root rev-parse HEAD) -ne $judged){throw 'The tree or HEAD changed during the full run: the result does not judge one head.'}
}
