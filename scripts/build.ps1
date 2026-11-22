$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (Test-Path -LiteralPath '.venv\Scripts\python.exe') {
    $trackerPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
} elseif (Test-Path -LiteralPath '.tools\python\python.exe') {
    $trackerPython = Join-Path (Get-Location) '.tools\python\python.exe'
} else {
    $trackerPython = 'python'
}
& $trackerPython -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Testy nie powiodły się' }
& $trackerPython -m PyInstaller --clean --noconfirm ETS2AcademyTracker.spec
if ($LASTEXITCODE -ne 0) { throw 'Budowanie nie powiodło się' }
