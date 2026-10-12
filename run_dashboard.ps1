$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

$VirtualEnvironmentPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $VirtualEnvironmentPython) {
    & $VirtualEnvironmentPython app.py
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 app.py
} else {
    & python app.py
}
