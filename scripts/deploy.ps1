param(
  [string[]]$Mods = @("fieldguide-sos", "gunlance-shells")
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$game = "D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds"
$dest = Join-Path $game "reframework\autorun"

if (-not (Test-Path (Join-Path $game "MonsterHunterWilds.exe"))) {
  throw "Game not found: $game"
}

if ($Mods -contains "all") {
  $Mods = Get-ChildItem (Join-Path $root "mods") -Directory | Select-Object -ExpandProperty Name
}

New-Item -ItemType Directory -Force -Path $dest | Out-Null
foreach ($mod in $Mods) {
  # Convention: mods/<name-with-dashes>/<name_with_underscores>.lua is the entry file.
  $file = ($mod -replace "-", "_") + ".lua"
  $src = Join-Path $root ("mods\" + $mod + "\" + $file)
  if (-not (Test-Path $src)) { throw "Mod entry not found: $src" }
  Copy-Item $src $dest -Force
  Write-Host ("Deployed {0} -> {1}" -f $file, $dest)
}

Get-ChildItem $dest -Filter "*.lua" | Format-Table Name, Length, LastWriteTime
