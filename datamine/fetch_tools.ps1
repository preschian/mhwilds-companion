# Fetch third-party datamining tools (REToolCustom, file list, texconv).
param([string]$Research = "$env:TEMP\mhwilds-research")

$ErrorActionPreference = 'Stop'
$T = Join-Path $Research 'tools'
New-Item -ItemType Directory -Force -Path $T | Out-Null

function Get-IfMissing($url, $dest) {
    if (Test-Path $dest) { Write-Host ("exists: {0}" -f $dest); return }
    Write-Host ("GET {0}" -f $url)
    Invoke-WebRequest $url -OutFile $dest
}

$zip = Join-Path $T 'REToolCustom_1.0.zip'
Get-IfMissing 'https://github.com/SlickAmogus/REToolCustom/releases/download/release/REToolCustom_1.0.zip' $zip
$retool = Join-Path $T 'REToolCustom\REtool.exe'
if (-not (Test-Path $retool)) {
    Expand-Archive $zip -DestinationPath (Join-Path $T 'REToolCustom') -Force
}
Get-IfMissing 'https://raw.githubusercontent.com/dtlnor/MonsterHunterWildsModding/main/files/MHWs.list' (Join-Path $T 'MHWs.list')
Get-IfMissing 'https://github.com/microsoft/DirectXTex/releases/download/may2026/texconv.exe' (Join-Path $T 'texconv.exe')

Write-Host '--- tools ---'
Get-ChildItem $T | Format-Table Name, Length
& $retool 2>&1 | Select-Object -First 2
