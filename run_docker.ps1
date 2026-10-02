# SPDX-License-Identifier: Apache-2.0
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Instala Docker Desktop primero. / Install Docker Desktop first."
}
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Abre Docker Desktop y espera a que este listo. / Start Docker Desktop and wait until ready." }
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw "No se pudo iniciar. Revisa los mensajes anteriores. / Startup failed; check the messages above." }
Write-Host "Abre / Open: http://127.0.0.1:8501"
Start-Process "http://127.0.0.1:8501"
