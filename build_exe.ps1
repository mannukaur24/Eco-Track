# EcoTrack - Smart Waste Management System
# Windows executable build script.
#
# Usage (PowerShell, run from the project root):
#   .\build_exe.ps1
#
# What it does
# ------------
# 1. Verifies the virtual environment (.venv).
# 2. Installs runtime/build dependencies (requirements.txt + PyInstaller, Waitress).
# 3. Runs Python compilation checks on the application source.
# 4. Runs the complete Pytest suite and stops if any test fails.
# 5. Cleans previous packaging artifacts safely (dist/, build/ only).
# 6. Builds the ONEDIR version:   dist/EcoTrack/EcoTrack.exe
# 7. Builds the ONEFILE version:  dist/EcoTrack.exe
# 8. Copies non-secret configuration templates (.env.example) next to both builds.
# 9. Prints a clear build summary.
#
# Source code and user data are never deleted.

$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -LiteralPath $scriptDir

$VENV_PYTHON = Join-Path $scriptDir ".venv\Scripts\python.exe"
$VENV_PIP    = Join-Path $scriptDir ".venv\Scripts\pip.exe"
$PYINSTALLER = Join-Path $scriptDir ".venv\Scripts\pyinstaller.exe"

function Write-Section([string]$title) {
    Write-Host ""
    Write-Host ("=" * 80)
    Write-Host $title
    Write-Host ("=" * 80)
}

function Write-SummaryLine([string]$label, [string]$value) {
    Write-Host ("{0,-22} : {1}" -f $label, $value)
}

# ---------------------------------------------------------------------------
# 1. Verify the virtual environment
# ---------------------------------------------------------------------------
Write-Section "Step 1 - Verifying virtual environment"

if (-not (Test-Path -LiteralPath $VENV_PYTHON)) {
    Write-Error "Virtual environment not found at $VENV_PYTHON. Create it with: python -m venv .venv"
    exit 1
}

$pythonVersion = & $VENV_PYTHON --version 2>&1
Write-Host "Virtual environment Python: $pythonVersion"

# ---------------------------------------------------------------------------
# 2. Install missing build dependencies
# ---------------------------------------------------------------------------
Write-Section "Step 2 - Installing build dependencies"

& $VENV_PIP install --upgrade pip > $null 2>&1
if ($LASTEXITCODE -ne 0) { Write-Warning "pip upgrade failed (non-fatal)" }

Write-Host "Installing runtime dependencies from requirements.txt..."
& $VENV_PIP install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install requirements.txt"; exit 1 }

Write-Host "Installing packaging dependencies (pyinstaller, waitress)..."
& $VENV_PIP install pyinstaller waitress
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install pyinstaller/waitress"; exit 1 }

if (-not (Test-Path -LiteralPath $PYINSTALLER)) {
    Write-Error "PyInstaller was not installed correctly."
    exit 1
}

# ---------------------------------------------------------------------------
# 3. Run Python compilation checks
# ---------------------------------------------------------------------------
Write-Section "Step 3 - Python compilation checks"

& $VENV_PYTHON -m compileall -q "config.py" "desktop_launcher.py" "app"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python compilation check failed."
    exit 1
}
Write-Host "Compilation checks passed."

# ---------------------------------------------------------------------------
# 4. Run the complete Pytest suite (stop the build if tests fail)
# ---------------------------------------------------------------------------
Write-Section "Step 4 - Running the Pytest suite (106 tests)"

& $VENV_PYTHON -m pytest -q
$testExitCode = $LASTEXITCODE
if ($testExitCode -ne 0) {
    Write-Error "Pytest suite failed (exit code $testExitCode). Build stopped."
    exit $testExitCode
}
Write-Host "All Pytest tests passed."

# ---------------------------------------------------------------------------
# 5. Clean previous packaging artifacts safely
# ---------------------------------------------------------------------------
Write-Section "Step 5 - Cleaning previous packaging artifacts"

foreach ($dir in @("dist", "build")) {
    $path = Join-Path $scriptDir $dir
    if (Test-Path -LiteralPath $path) {
        Write-Host "Removing $path ..."
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}

# ---------------------------------------------------------------------------
# 6. Build the ONEDIR version: dist/EcoTrack/EcoTrack.exe
# ---------------------------------------------------------------------------
Write-Section "Step 6 - Building ONEDIR version (dist/EcoTrack/EcoTrack.exe)"

& $PYINSTALLER --clean "EcoTrack.spec"
if ($LASTEXITCODE -ne 0) {
    Write-Error "ONEDIR build failed."
    exit 1
}

$onedirExe = Join-Path $scriptDir "dist\EcoTrack\EcoTrack.exe"
if (-not (Test-Path -LiteralPath $onedirExe)) {
    Write-Error "ONEDIR build did not produce $onedirExe"
    exit 1
}
Write-Host "ONEDIR build OK: $onedirExe"

# ---------------------------------------------------------------------------
# 7. Build the ONEFILE version: dist/EcoTrack.exe
# ---------------------------------------------------------------------------
Write-Section "Step 7 - Building ONEFILE version (dist/EcoTrack.exe)"

$env:ECO_TRACK_ONEFILE = "1"
& $PYINSTALLER --clean "EcoTrack.spec"
if ($LASTEXITCODE -ne 0) {
    Write-Error "ONEFILE build failed."
    exit 1
}

$onefileExe = Join-Path $scriptDir "dist\EcoTrack.exe"
if (-not (Test-Path -LiteralPath $onefileExe)) {
    Write-Error "ONEFILE build did not produce $onefileExe"
    exit 1
}
Write-Host "ONEFILE build OK: $onefileExe"

# ---------------------------------------------------------------------------
# 8. Copy required non-secret configuration templates
# ---------------------------------------------------------------------------
Write-Section "Step 8 - Copying non-secret configuration templates"

$envExample = Join-Path $scriptDir ".env.example"
if (Test-Path -LiteralPath $envExample) {
    Copy-Item -LiteralPath $envExample -Destination (Join-Path $scriptDir "dist\EcoTrack\.env.example") -Force
    Copy-Item -LiteralPath $envExample -Destination (Join-Path $scriptDir "dist\.env.example") -Force
    Write-Host "Copied .env.example next to both executable distributions."
} else {
    Write-Warning ".env.example not found; skipping."
}

# NOTE: The real .env file (with database credentials and SECRET_KEY) is
# intentionally NOT copied. It must be created externally by the user.

# ---------------------------------------------------------------------------
# 9. Build summary
# ---------------------------------------------------------------------------
Write-Section "BUILD SUMMARY"

$onedirSize = (Get-ChildItem -LiteralPath (Join-Path $scriptDir "dist\EcoTrack") -Recurse | Measure-Object -Property Length -Sum).Sum
$onefileSize = (Get-Item -LiteralPath $onefileExe).Length

Write-SummaryLine "ONEDIR version"   $onedirExe
Write-SummaryLine "ONEDIR size"      ("{0:N0} bytes" -f $onedirSize)
Write-SummaryLine "ONEFILE version"  $onefileExe
Write-SummaryLine "ONEFILE size"     ("{0:N0} bytes" -f $onefileSize)
Write-SummaryLine "Icon"             (Join-Path $scriptDir "assets\EcoTrack.ico")
Write-SummaryLine "Launcher"         (Join-Path $scriptDir "desktop_launcher.py")
Write-SummaryLine "Spec file"        (Join-Path $scriptDir "EcoTrack.spec")
Write-Host ""
Write-Host "Both executables were built successfully."
Write-Host "Next: run post-build tests (see README.md, Executable Build section)."
