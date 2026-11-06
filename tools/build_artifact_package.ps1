# Build the public (frontend-only) site as a package for a Claude Artifact.
# Output: <OutDir>\page.html (the Artifact page) plus assets\ and favicon.svg (supporting files).
# Usage (repo root):  powershell -ExecutionPolicy Bypass -File tools\build_artifact_package.ps1 [-OutDir <folder>]
# Requires: Node.js and `frontend\node_modules` already installed (corepack pnpm install --frozen-lockfile).
param([string]$OutDir = (Join-Path $env:TEMP 'youth-life-artifact'))
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'frontend'
$vite = Join-Path $frontend 'node_modules\vite\bin\vite.js'
if (-not (Test-Path $vite)) { throw "vite not found. Run 'corepack pnpm install --frozen-lockfile' in $frontend first." }
if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
$env:VITE_PUBLIC_BACKEND_PENDING = 'true'
Push-Location $frontend
try { & node $vite build --base=./ --outDir $OutDir --emptyOutDir; if ($LASTEXITCODE -ne 0) { throw 'vite build failed' } } finally { Pop-Location }
$js = Get-ChildItem (Join-Path $OutDir 'assets') -Filter 'index-*.js' | Select-Object -First 1
$css = Get-ChildItem (Join-Path $OutDir 'assets') -Filter 'index-*.css' | Select-Object -First 1
if (-not $js -or -not $css) { throw 'entry js/css not found in build output' }
# The Artifact tool wraps the page in its own document skeleton, so write a fragment, not a full document.
# Title is written with Unicode escapes on purpose: Windows PowerShell 5.1 reads BOM-less scripts as ANSI and would garble literal Korean.
$title = -join ([char[]](0xCCAD, 0xB144, 0x20, 0xACBD, 0xC81C, 0xC0DD, 0xD65C))
$page = "<title>$title</title>`n<link rel=`"stylesheet`" href=`"./assets/$($css.Name)`">`n<div id=`"root`"></div>`n<script type=`"module`" src=`"./assets/$($js.Name)`"></script>`n"
[IO.File]::WriteAllText((Join-Path $OutDir 'page.html'), $page, (New-Object Text.UTF8Encoding($false)))
Write-Host "Artifact package: $OutDir"
Write-Host 'Supporting files to publish (relative to OutDir):'
Get-ChildItem (Join-Path $OutDir 'assets') -File | ForEach-Object { "  assets/$($_.Name)" }
Write-Host '  favicon.svg'
$mb = [math]::Round(((Get-ChildItem $OutDir -Recurse -File | Measure-Object Length -Sum).Sum) / 1MB, 2)
Write-Host "Total size: $mb MB (Artifact limit: 16 MB per page and per file)"
