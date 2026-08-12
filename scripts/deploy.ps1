$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$src = Join-Path $root "mods\fieldguide-sos"
$game = "D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds"
$dest = Join-Path $game "reframework\autorun"

if (-not (Test-Path (Join-Path $game "MonsterHunterWilds.exe"))) {
  throw "Game not found: $game"
}

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item (Join-Path $src "fieldguide_sos.lua") $dest -Force

Write-Host "Deployed to $dest"
Get-ChildItem $dest -Filter "fieldguide_sos*.lua*" | Format-Table Name, Length, LastWriteTime
