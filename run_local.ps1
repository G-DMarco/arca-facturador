# SPDX-License-Identifier: Apache-2.0
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$PythonPath = Join-Path $PSScriptRoot ".venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Primero crea .venv e instala requirements.txt. / Create .venv and install requirements.txt first."
}
& $PythonPath -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
exit $LASTEXITCODE
