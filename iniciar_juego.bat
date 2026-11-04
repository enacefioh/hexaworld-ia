@echo off
title HexaWorld IA - Explorador Autónomo
chcp 65001 >nul
echo ========================================================
echo       Iniciando HexaWorld IA - Mundo Hexagonal
echo ========================================================
echo.

REM Comprobar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se ha encontrado Python en el sistema.
    echo Por favor, instala Python 3.10 o superior y añádelo al PATH.
    pause
    exit /b 1
)

echo [1/3] Verificando dependencias necesarias...
pip install -r requirements.txt --quiet

echo.
echo [2/3] Conectando con LM Studio...
echo Por defecto busca LM Studio en http://localhost:1234 o red local.
echo Si tienes LM Studio en otra IP/puerto, define la variable LM_STUDIO_HOST.
echo.
echo [3/3] Iniciando servidor web en: http://127.0.0.1:8000
echo.

start "" "http://127.0.0.1:8000"
python -m uvicorn server:app --app-dir backend --host 127.0.0.1 --port 8000 --reload

pause
