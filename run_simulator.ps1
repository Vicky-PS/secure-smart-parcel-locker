$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

$VirtualEnvironmentPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $VirtualEnvironmentPython) {
    & $VirtualEnvironmentPython simulate_scenarios.py
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 simulate_scenarios.py
} else {
    & python simulate_scenarios.py
}
