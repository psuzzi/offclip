# offclip bootstrap for Windows.
# 1. find a Python >= 3.9 with Tkinter, or fetch a private one into %LOCALAPPDATA%\offclip (and say why);
# 2. hand over to offclip\bootstrap.py, which prepares the environment and starts the window.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
$ErrorActionPreference = "Stop"
$App = Split-Path -Parent $PSScriptRoot
$Data = if ($env:OFFCLIP_DATA) { $env:OFFCLIP_DATA } else { Join-Path $env:LOCALAPPDATA "offclip" }
$Launcher = if ($env:OFFCLIP_LAUNCHER) { $env:OFFCLIP_LAUNCHER } else { Join-Path $App "run.bat" }
New-Item -ItemType Directory -Force -Path $Data | Out-Null

# Private Python: python-build-standalone (relocatable CPython with Tkinter), pinned.
$PbsTag = "20261009"
$PbsVer = "3.12.15"
$Arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "aarch64" } else { "x86_64" }
$PbsName = "cpython-$PbsVer+$PbsTag-$Arch-pc-windows-msvc-install_only_stripped.tar.gz"
$PbsBase = "https://github.com/astral-sh/python-build-standalone/releases/download/$PbsTag"

function Say($tag, $msg) { Write-Host "  [$tag] $msg" }
function Run-Py($exe, $code) {
  $ErrorActionPreference = "SilentlyContinue"
  try { $out = & $exe -c $code 2>$null; return @{ ok = ($LASTEXITCODE -eq 0); out = "$out" } } catch { return @{ ok = $false; out = "" } }
}
function Usable($exe)    { (Run-Py $exe "import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 9) else 1)").ok }
function NewEnough($exe) { (Run-Py $exe "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)").ok }
function PyVer($exe)     { $r = Run-Py $exe "import sys; print('%d.%d.%d' % sys.version_info[:3])"; if ($r.ok) { $r.out.Trim() } else { "?" } }

Write-Host "offclip setup"
$Py = $null
$Reason = $null
if ($env:OFFCLIP_FORCE_PRIVATE_PYTHON -ne "1") {
  $cands = @((Join-Path $Data "python\python.exe"))
  $r = Run-Py "py" "import sys; print(sys.executable)"          # the py launcher knows the real installs
  if ($r.ok -and $r.out.Trim()) { $cands += $r.out.Trim() }
  foreach ($n in "python", "python3") {
    $c = Get-Command $n -ErrorAction SilentlyContinue
    if ($c -and $c.Source -and $c.Source -notlike "*WindowsApps*") { $cands += $c.Source }   # skip the Store stub
  }
  foreach ($c in $cands) {
    if (-not (Test-Path $c)) { continue }
    if (Usable $c) { $Py = $c; break }
    if (-not $Reason) {
      if (NewEnough $c) { $Reason = "Python $(PyVer $c) at $c has no Tkinter" } else { $Reason = "Python $(PyVer $c) at $c is older than 3.9" }
    }
  }
} else {
  $Reason = if ($env:OFFCLIP_FORCE_REASON) { $env:OFFCLIP_FORCE_REASON } else { "a private Python was requested" }
}

if ($Py) {
  Say "ok" "Python $(PyVer $Py) with Tkinter: $Py"
} else {
  if (-not $Reason) { $Reason = "no Python was found on this computer" }
  Say "++" "Installing a private Python $PbsVer into $Data\python (about 22 MB, one time)"
  Write-Host "       because: $Reason"
  $Tmp = Join-Path $Data "tmp"; New-Item -ItemType Directory -Force -Path $Tmp | Out-Null
  $Tar = Join-Path $Tmp $PbsName
  $Sums = Join-Path $Tmp "SHA256SUMS"
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $ProgressPreference = "SilentlyContinue"      # Invoke-WebRequest is very slow with its progress bar on
  Invoke-WebRequest -Uri "$PbsBase/$PbsName" -OutFile $Tar -UseBasicParsing
  Invoke-WebRequest -Uri "$PbsBase/SHA256SUMS" -OutFile $Sums -UseBasicParsing
  $line = Select-String -Path $Sums -SimpleMatch " $PbsName" | Select-Object -First 1
  if (-not $line) { throw "no checksum published for $PbsName" }
  $expected = ($line.Line -split "\s+")[0].ToLower()
  $actual = (Get-FileHash -Algorithm SHA256 -Path $Tar).Hash.ToLower()
  if ($expected -ne $actual) { throw "checksum mismatch for $PbsName: refusing to use it" }
  $Dest = Join-Path $Data "python"
  if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
  & tar -xzf $Tar -C $Data
  if ($LASTEXITCODE -ne 0) { throw "could not extract $PbsName" }
  Remove-Item -Force $Tar, $Sums
  $Py = Join-Path $Dest "python.exe"
  if (-not (Usable $Py)) { throw "the private Python does not start" }
  Say "ok" "Python $(PyVer $Py) with Tkinter: $Py"
}

$env:OFFCLIP_LAUNCHER = $Launcher
$env:PYTHONPATH = $App
Set-Location $App
$ErrorActionPreference = "Continue"
& $Py -m offclip.bootstrap --app $App --data $Data -- @Rest
$rc = $LASTEXITCODE
if ($rc -eq 3 -and $env:OFFCLIP_FORCE_PRIVATE_PYTHON -ne "1") {
  $env:OFFCLIP_FORCE_PRIVATE_PYTHON = "1"
  $env:OFFCLIP_FORCE_REASON = "the Python at $Py cannot create virtual environments"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath @Rest
  $rc = $LASTEXITCODE
}
exit $rc
