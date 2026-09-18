# Quest + quest-text extraction across base pak + patch chain, merged newest-wins.
param([string]$Research = "$env:TEMP\mhwilds-research",
      [string]$Game = "D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds")

$ErrorActionPreference = 'Stop'
$T = "$Research\tools"
$Out = "$Research\extract_quest"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

$listFile = "$T\quest.list"
if (-not (Test-Path $listFile)) {
    $L = Get-Content "$T\MHWs.list"
    $sel = $L | Where-Object {
        ($_ -like 'natives/STM/GameDesign/Mission/*/_Quest/*') -or
        ($_ -like 'natives/STM/GameDesign/Text/Excel_Data/Quest*.msg.*') -or
        ($_ -like 'natives/STM/GameDesign/Text/Reference/RefQuest.msg.*')
    }
    $sel | Set-Content $listFile
}
Write-Host ("list entries={0}" -f (Get-Content $listFile | Measure-Object -Line).Lines)

$paks = @(Join-Path $Game 're_chunk_000.pak')
foreach ($n in 1..15) { $paks += (Join-Path $Game ("re_chunk_000.pak.patch_{0:000}.pak" -f $n)) }
foreach ($pak in $paks) {
    if (-not (Test-Path $pak)) { continue }
    if ((Get-Item $pak).Length -le 1024) { Write-Host ("skip tiny {0}" -f (Split-Path $pak -Leaf)); continue }
    $name = [IO.Path]::GetFileName($pak)
    $wd = Join-Path $Out $name
    New-Item -ItemType Directory -Force -Path $wd | Out-Null
    Write-Host ("=== {0} ===" -f $name)
    Push-Location $wd
    & "$T\REToolCustom\REtool.exe" -h $listFile -x -skipUnknowns -dontOverwrite $pak 2>&1 |
        Select-String 'Extracted|error|Error' | Select-Object -Last 4
    Pop-Location
}

$merged = Join-Path $Out 'merged'
New-Item -ItemType Directory -Force -Path $merged | Out-Null
$order = @('re_chunk_000.pak') + (1..15 | ForEach-Object { "re_chunk_000.pak.patch_{0:000}.pak" -f $_ })
foreach ($name in $order) {
    $wd = Join-Path $Out $name
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
Write-Host '=== merged total ==='
(Get-ChildItem $merged -Recurse -File | Measure-Object).Count
