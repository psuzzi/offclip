# Build offclip-setup.exe from a git ref:  scripts\build-windows-installer.ps1 -Ref v1.1.3 [-OutDir dist]
# Needs git and Inno Setup 6 (ISCC.exe), both present on GitHub's Windows runners.
param([Parameter(Mandatory = $true)][string]$Ref, [string]$OutDir = "dist")
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Work = Join-Path ([IO.Path]::GetTempPath()) ("offclip-build-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $Work | Out-Null
$Zip = Join-Path $Work "src.zip"
git archive --format=zip --prefix=src/ -o $Zip $Ref
if ($LASTEXITCODE -ne 0) { throw "git archive failed for $Ref" }
Expand-Archive -Path $Zip -DestinationPath $Work
$Src = Join-Path $Work "src"
$Version = (Select-String -Path (Join-Path $Src "offclip\__init__.py") -Pattern '__version__ = "([^"]+)"').Matches[0].Groups[1].Value
$Out = (New-Item -ItemType Directory -Force -Path $OutDir).FullName
$Iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe", "ISCC.exe") | Where-Object { Get-Command $_ -ErrorAction SilentlyContinue } | Select-Object -First 1
if (-not $Iscc) { throw "Inno Setup 6 (ISCC.exe) not found" }
Write-Host "Building offclip-setup.exe for $Ref (version $Version)"
& $Iscc /Q "/DAppVersion=$Version" "/DSourceDir=$Src" "/DOutputDir=$Out" (Join-Path $Src "installer\windows\offclip.iss")
if ($LASTEXITCODE -ne 0) { throw "ISCC failed" }
Remove-Item -Recurse -Force $Work
Get-Item (Join-Path $Out "offclip-setup.exe") | ForEach-Object { Write-Host ("  built {0} ({1:N0} bytes)" -f $_.FullName, $_.Length) }
