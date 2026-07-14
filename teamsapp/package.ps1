<#
.SYNOPSIS
  Packages the Teams app manifest into a sideloadable .zip.

.DESCRIPTION
  1. Reads MicrosoftAppId from ../.env (or $env:MicrosoftAppId)
  2. Substitutes the $MicrosoftAppId placeholder in manifest.json
  3. Adds validDomains from the tunneling URL you provide
  4. Zips manifest.json + color.png + outline.png → foundry-greeting.zip

.PARAMETER TunnelingUrl
  Your dev tunnel / ngrok URL WITHOUT trailing slash.
  Example: https://abc123.ngrok.io

.EXAMPLE
  .\package.ps1 -TunnelingUrl https://abc123.ngrok.io
#>
param(
    [Parameter(Mandatory)][string]$TunnelingUrl
)

$ErrorActionPreference = 'Stop'
$scriptDir  = $PSScriptRoot
$envFile    = Join-Path $scriptDir '../.env'
$manifestIn = Join-Path $scriptDir 'manifest.json'
$outZip     = Join-Path $scriptDir 'foundry-greeting.zip'

# ── 1. Resolve MicrosoftAppId ─────────────────────────────────────────────────
$appId = $env:MicrosoftAppId
if (-not $appId -and (Test-Path $envFile)) {
    Get-Content $envFile | Where-Object { $_ -match '^MicrosoftAppId\s*=\s*(.+)$' } | ForEach-Object {
        $appId = $Matches[1].Trim()
    }
}
if (-not $appId) {
    Write-Error "MicrosoftAppId not found. Set it in ../.env or as an environment variable."
}
Write-Host "Using App ID: $appId"

# ── 2. Substitute placeholder and validDomains ────────────────────────────────
$domain  = ([System.Uri]$TunnelingUrl).Host
$json    = Get-Content $manifestIn -Raw
$json    = $json -replace '\$MicrosoftAppId', $appId
$manifest = $json | ConvertFrom-Json
$manifest.validDomains = @($domain)
$manifest.bots[0].botId = $appId

# Write temp manifest
$tempManifest = Join-Path $scriptDir 'manifest_resolved.json'
$manifest | ConvertTo-Json -Depth 10 | Set-Content $tempManifest -Encoding UTF8

# ── 3. Validate icons exist ───────────────────────────────────────────────────
$colorIcon   = Join-Path $scriptDir 'color.png'
$outlineIcon = Join-Path $scriptDir 'outline.png'
if (-not (Test-Path $colorIcon))   { Write-Error "Missing color.png — see ICONS.md" }
if (-not (Test-Path $outlineIcon)) { Write-Error "Missing outline.png — see ICONS.md" }

# ── 4. Package ────────────────────────────────────────────────────────────────
if (Test-Path $outZip) { Remove-Item $outZip -Force }

$tmpDir = Join-Path $env:TEMP 'teams-package'
New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
Copy-Item $tempManifest (Join-Path $tmpDir 'manifest.json') -Force
Copy-Item $colorIcon    (Join-Path $tmpDir 'color.png')     -Force
Copy-Item $outlineIcon  (Join-Path $tmpDir 'outline.png')   -Force

Compress-Archive -Path "$tmpDir\*" -DestinationPath $outZip -Force
Remove-Item $tmpDir -Recurse -Force
Remove-Item $tempManifest -Force

Write-Host ""
Write-Host "Package created: $outZip"
Write-Host ""
Write-Host "Next: in Teams → Apps → Manage your apps → Upload a custom app → select foundry-greeting.zip"
