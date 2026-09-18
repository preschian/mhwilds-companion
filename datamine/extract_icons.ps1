# Extract EmIcon textures from the streaming pak + patch chain.
# Output lands in per-pak subdirs under extract_icons/; build_icons.ps1 merges.
param([string]$Research = "$env:TEMP\mhwilds-research",
      [string]$Game = "D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds")

$ErrorActionPreference = 'Stop'
$T = Join-Path $Research 'tools'
$X = Join-Path $Research 'extract_icons'
New-Item -ItemType Directory -Force -Path $X | Out-Null

$listFile = Join-Path $T 'icons.list'
if (-not (Test-Path $listFile)) {
    Select-String -Path (Join-Path $T 'MHWs.list') -Pattern 'EmIcon' |
        ForEach-Object { $_.Line } | Set-Content $listFile
}
Write-Host ("list entries={0}" -f (Get-Content $listFile | Measure-Object -Line).Lines)

$paks = @(Join-Path $Game 're_chunk_000.pak.sub_000.pak')
foreach ($n in 1..15) { $paks += (Join-Path $Game ("re_chunk_000.pak.sub_000.pak.patch_{0:000}.pak" -f $n)) }
Set-Location $X
foreach ($pak in $paks) {
    if (-not (Test-Path $pak)) { continue }
    if ((Get-Item $pak).Length -le 1024) { continue }
    Write-Host ("=== {0} ===" -f (Split-Path $pak -Leaf))
    & (Join-Path $T 'REToolCustom\REtool.exe') -h $listFile -x -skipUnknowns -dontOverwrite $pak 2>&1 |
        Select-String 'Extracted' | Select-Object -Last 2
}
Write-Host '=== total ==='
(Get-ChildItem $X -Recurse -File | Measure-Object).Count
