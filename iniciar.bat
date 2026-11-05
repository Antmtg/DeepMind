@echo off
chcp 65001 >nul
title Deep Mind Apnea - Servidor

echo ========================================
echo  Deep Mind Apnea - Iniciando servidor...
echo ========================================
echo.

REM Ir a la carpeta del backend
cd /d "%~dp0backend"

REM Instalar dependencias si no estan instaladas
echo [1/3] Instalando dependencias de Python...
python -m pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias.
    echo Asegurate de tener Python instalado y vuelve a intentarlo.
    pause
    exit /b 1
)
echo    Dependencias listas.

REM Levantar el servidor en segundo plano
echo [2/3] Levantando servidor en http://localhost:8000 ...
start "uvicorn" /min python -m uvicorn app.main:app --reload

REM Esperar a que el servidor responda
echo [3/3] Esperando a que el servidor este listo...
set /a intentos=0
:espera
set /a intentos+=1
if %intentos% gtr 30 (
    echo Tiempo agotado. Revisa la consola para ver errores.
    pause
    exit /b 1
)
timeout /t 1 >nul
powershell -command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto espera

echo    Servidor listo.

REM Abrir el navegador
echo.
echo ========================================
echo  Abriendo la app en tu navegador...
echo ========================================
start "" "http://localhost:8000/"

echo.
echo La app esta corriendo en: http://localhost:8000/
echo Para cerrar el servidor, presiona Ctrl+C en la consola negra.
echo.
pause
