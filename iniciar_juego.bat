@echo off
setlocal enabledelayedexpansion
title HexaWorld IA - Explorador Autonomo

chcp 65001 >nul 2>&1

echo ========================================================
echo       Iniciando HexaWorld IA - Mundo Hexagonal
echo ========================================================
echo.

set "PY_CMD="

REM 1. Probar comando 'python'
python --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :python_found
)

REM 2. Probar lanzador oficial de Windows 'py'
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3"
    goto :python_found
)

REM 3. Probar comando 'python3'
python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python3"
    goto :python_found
)

REM 4. Buscar instalaciones tipicas de Python en Windows cuando no se anadio al PATH
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD="%%D\python.exe""
        goto :python_found
    )
)
for /d %%D in ("%ProgramFiles%\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD="%%D\python.exe""
        goto :python_found
    )
)

:python_not_found
echo.
echo [ERROR] No se ha podido detectar Python en el sistema o en el PATH.
echo.
echo Si ya tienes Python instalado en este PC:
echo   Es muy probable que durante la instalacion no estuviera marcada la opcion
echo   "Add python.exe to PATH" (o "Agregar Python a las variables de entorno").
echo.
echo Solucion facil:
echo   1. Ejecuta de nuevo el instalador de Python descargado de https://www.python.org
echo   2. Elige "Modify" (Modificar) y asegurate de marcar "Add Python to environment variables".
echo   3. O abre PowerShell o CMD e instala Python facilmente con:
echo        winget install Python.Python.3.11
echo.
pause
exit /b 1

:python_found
echo [INFO] Python detectado: !PY_CMD!
!PY_CMD! --version
echo.

echo [1/3] Verificando dependencias necesarias (FastAPI, uvicorn)...
!PY_CMD! -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [AVISO] Fallo 'pip install --quiet', mostrando proceso de instalacion completo...
    !PY_CMD! -m pip install -r requirements.txt
)

echo.
echo [2/3] Conectando con LM Studio...
echo Configura la IP del servidor de inferencia desde el boton superior de la web o el modal de inicio.
echo (Por defecto: 127.0.0.1:1234 si corre en este mismo PC).
echo.
echo [3/3] Iniciando servidor web en: http://127.0.0.1:8000
echo.

start "" "http://127.0.0.1:8000"
!PY_CMD! -m uvicorn server:app --app-dir backend --host 127.0.0.1 --port 8000 --reload

pause
