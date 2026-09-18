# Guide/mission extraction across base pak + patch chain, merged newest-wins.
param([string]$Research = $env:MHRESEARCH,
      [string]$Game = $env:MHWILDS_GAME)

$ErrorActionPreference = 'Stop'
if (-not $Research) { $Research = Join-Path $env:TEMP 'mhwilds-research' }
if (-not $Game) { $Game = 'D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds' }
$T = Join-Path $Research 'tools'
$Lists = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'lists'
$RETool = Join-Path $T 'REToolCustom\REtool.exe'

$pairs = @(
    @('mission.list', 'mission_merged'),
    @('mission_text.list', 'mtext_merged'),
    @('quest.list', 'extract_quest'),
    @('report.list', 'extract_report'),
    @('reporttext.list', 'extract_reporttext'),
    @('breaktext.list', 'extract_breaktext'),
    @('titles.list', 'titles_merged')
)

$paks = @(Join-Path $Game 're_chunk_000.pak')
foreach ($n in 1..15) { $paks += (Join-Path $Game ("re_chunk_000.pak.patch_{0:000}.pak" -f $n)) }
$order = @('re_chunk_000.pak') + (1..15 | ForEach-Object { "re_chunk_000.pak.patch_{0:000}.pak" -f $_ })

foreach ($pair in $pairs) {
    $listFile = Join-Path $Lists $pair[0]
    $Out = Join-Path $Research $pair[1]
    New-Item -ItemType Directory -Force -Path $Out | Out-Null
    Write-Host ("=== {0} ({1} entries) ===" -f $pair[0],
        (Get-Content $listFile | Measure-Object -Line).Lines)
    foreach ($pak in $paks) {
        if (-not (Test-Path $pak)) { continue }
        if ((Get-Item $pak).Length -le 1024) { continue }
        $wd = Join-Path $Out ([IO.Path]::GetFileName($pak))
        New-Item -ItemType Directory -Force -Path $wd | Out-Null
        Push-Location $wd
        & $RETool -h $listFile -x -skipUnknowns -dontOverwrite $pak 2>&1 |
            Select-String 'Extracted [1-9]|error|Error' | Select-Object -Last 2
        Pop-Location
    }
    $merged = Join-Path $Out 'merged'
    New-Item -ItemType Directory -Force -Path $merged | Out-Null
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
    Write-Host ("merged {0}: {1} files" -f $pair[1],
        (Get-ChildItem $merged -Recurse -File | Measure-Object).Count)
}
