# Merge item-icon atlas newest-wins, convert TEX->DDS->PNG.
param([string]$Research = "$env:TEMP\mhwilds-research")

$ErrorActionPreference = 'Stop'
$T = Join-Path $Research 'tools'
$Out = Join-Path $Research 'atlas_png'
New-Item -ItemType Directory -Force -Path $Out | Out-Null

function Merge($Sub, $MergedName, $Base) {
    $X = Join-Path $Research $Sub
    $merged = Join-Path $Research $MergedName
    New-Item -ItemType Directory -Force -Path $merged | Out-Null
    $order = @($Base) + (1..15 | ForEach-Object { "$Base.patch_{0:000}.pak" -f $_ })
    foreach ($name in $order) {
        $wd = Join-Path $X $name
        if (-not (Test-Path $wd)) { continue }
        Get-ChildItem $wd -Recurse -File | ForEach-Object {
            $rel = $_.FullName.Substring($wd.Length + 1)
            $parts = $rel -split '\\'
            $rel2 = ($parts[1..($parts.Length - 1)] -join '\')
            $dest = Join-Path $merged $rel2
            New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
            Copy-Item $_.FullName $dest -Force
        }
    }
    (Get-ChildItem $merged -Recurse -File | Measure-Object).Count
}

Write-Host ("atlas merged={0}" -f (Merge 'extract_atlas' 'atlas_merged' 're_chunk_000.pak.sub_000.pak'))
Write-Host ("gui merged={0}" -f (Merge 'extract_gui' 'gui_merged' 're_chunk_000.pak'))

$merged = Join-Path $Research 'atlas_merged'
$texs = Get-ChildItem $merged -Recurse -Filter "*.tex.*"
Write-Host ("tex files={0}" -f $texs.Count)
Push-Location $merged
foreach ($f in $texs) {
    & (Join-Path $T 'REToolCustom\REtool.exe') $f.FullName 2>&1 | Out-Null
}
$dds = Get-ChildItem $merged -Recurse -Filter "*.dds"
Write-Host ("dds files={0}" -f $dds.Count)
foreach ($d in $dds) {
    # NOTE: no -f flag (texconv rejects it); output name follows the input.
    & (Join-Path $T 'texconv.exe') -nologo -y -ft png -o $Out $d.FullName 2>&1 | Out-Null
}
Pop-Location
Write-Host ("png files={0}" -f (Get-ChildItem $Out -Filter '*.png').Count)
