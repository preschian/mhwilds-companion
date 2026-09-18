# Merge icon textures newest-wins, convert TEX->DDS->PNG, build icon map.
param([string]$Research = "$env:TEMP\mhwilds-research")

$ErrorActionPreference = 'Stop'
$T = "$Research\tools"
$X = "$Research\extract_icons"
$Out = "$Research\icons_png"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

# 1. Merge newest-wins from per-pak dirs (base, then patches ascending).
$merged = "$Research\icons_merged"
New-Item -ItemType Directory -Force -Path $merged | Out-Null
$order = @('re_chunk_000.pak.sub_000') + (1..15 | ForEach-Object {
    "re_chunk_000.pak.sub_000.pak.patch_{0:000}" -f $_ })
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
$texs = Get-ChildItem $merged -Recurse -Filter "*.tex.*"
Write-Host ("merged tex files={0}" -f $texs.Count)

# 2. TEX -> DDS (RETool) -> PNG (texconv).
Push-Location $merged
foreach ($f in $texs) {
    & "$T\REToolCustom\REtool.exe" $f.FullName 2>&1 | Out-Null
}
$dds = Get-ChildItem $merged -Recurse -Filter "*.dds"
Write-Host ("dds files={0}" -f $dds.Count)
foreach ($d in $dds) {
    & "$T\texconv.exe" -nologo -y -ft png -o $Out $d.FullName 2>&1 | Out-Null
}
Pop-Location
$pngs = Get-ChildItem $Out -Filter "*.png"
Write-Host ("png files={0}" -f $pngs.Count)
$pngs | Select-Object -First 8 Name
