# Extract item-icon atlas textures (streaming pak chain) + icon metadata
# (AddIconData, colorPreset.gcp: base pak chain).
# Output lands in per-pak subdirs under extract_atlas/ + extract_gui/;
# build_itemicons.ps1 merges newest-wins.
param([string]$Research = "$env:TEMP\mhwilds-research",
      [string]$Game = "")

$ErrorActionPreference = 'Stop'
if (-not $Game) {
    $Game = if ($env:MHWILDS_GAME) { $env:MHWILDS_GAME } `
        else { 'D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds' }
}
$T = Join-Path $Research 'tools'

$atlasList = Join-Path $T 'atlas.list'
if (-not (Test-Path $atlasList)) {
    Select-String -Path (Join-Path $T 'MHWs.list') -Pattern 'ui_texture/tex000000/tex000\d+[^/]*\.tex\.' |
        ForEach-Object { $_.Line } | Set-Content $atlasList
}
$guiList = Join-Path $T 'gui_icon.list'
if (-not (Test-Path $guiList)) {
    @('natives/STM/GameDesign/GUI/Common/_UserData/AddIconData.user.3',
      'natives/STM/GUI/colorPreset.gcp.2') | Set-Content $guiList
}
Write-Host ("atlas entries={0}" -f (Get-Content $atlasList | Measure-Object -Line).Lines)

function Unpack($Sub, $List, $PakName) {
    $X = Join-Path $Research $Sub
    New-Item -ItemType Directory -Force -Path $X | Out-Null
    $paks = @(Join-Path $Game $PakName)
    foreach ($n in 1..15) { $paks += (Join-Path $Game ("{0}.patch_{1:000}.pak" -f $PakName, $n)) }
    Set-Location $X
    foreach ($pak in $paks) {
        if (-not (Test-Path $pak)) { continue }
        if ((Get-Item $pak).Length -le 1024) { continue }
        Write-Host ("=== {0} ===" -f (Split-Path $pak -Leaf))
        & (Join-Path $T 'REToolCustom\REtool.exe') -h $List -x -skipUnknowns -dontOverwrite $pak 2>&1 |
            Select-String 'Extracted' | Select-Object -Last 2
    }
}

Unpack 'extract_atlas' $atlasList 're_chunk_000.pak.sub_000.pak'
Unpack 'extract_gui' $guiList 're_chunk_000.pak'
Write-Host '=== total ==='
(Get-ChildItem (Join-Path $Research 'extract_atlas') -Recurse -File | Measure-Object).Count
(Get-ChildItem (Join-Path $Research 'extract_gui') -Recurse -File | Measure-Object).Count
