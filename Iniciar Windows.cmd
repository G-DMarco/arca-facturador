@echo off
rem SPDX-License-Identifier: Apache-2.0
cd /d "%~dp0"
docker info >nul 2>&1
if errorlevel 1 (
    echo Abre Docker Desktop y espera a que este listo. Despues volve a ejecutar este archivo.
    pause
    exit /b 1
)
echo Preparando el facturador. La primera vez puede tardar varios minutos.
docker compose up -d --build
if errorlevel 1 (
    echo No pudimos iniciar. Conserva este mensaje para pedir ayuda.
    pause
    exit /b 1
)
start "" "http://127.0.0.1:8501"
echo Listo. Si el navegador tarda en cargar, espera unos segundos y actualiza la pagina.
pause
