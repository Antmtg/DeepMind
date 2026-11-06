@echo off
setlocal
chcp 65001 >nul
title Deep Mind Apnea - Servidor

echo ========================================
echo  Deep Mind Apnea - Iniciando servidor...
echo ========================================
echo.

cd /d "%~dp0backend"
if errorlevel 1 (
    echo ERROR: No se encontro la carpeta backend.
    pause
    exit /b 1
)

REM Detectar Python: primero "python", luego el lanzador "py".
set "PYTHON=python"
where python >nul 2>&1
if errorlevel 1 set "PYTHON=py"
where %PYTHON% >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en el PATH.
    echo Instala Python 3.11 o superior desde https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Si ya hay un servidor respondiendo, no lanzar otro.
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo El servidor ya esta corriendo. Abriendo la app...
    start "" "http://127.0.0.1:8000/"
    exit /b 0
)

REM Comprobar dependencias y, solo si faltan, instalarlas.
echo [1/3] Comprobando dependencias...
%PYTHON% -c "import fastapi, uvicorn, sqlalchemy, pydantic" >nul 2>&1
if errorlevel 1 (
    echo    Faltan dependencias. Instalando desde requirements.txt...
    %PYTHON% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: No se pudieron instalar las dependencias.
        echo Revisa tu conexion a internet o ejecuta manualmente:
        echo    %PYTHON% -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)
echo    Dependencias listas.

REM Levantar el servidor en segundo plano.
echo [2/3] Levantando servidor en http://127.0.0.1:8000 ...
start "Deep Mind Apnea" /min %PYTHON% -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

REM Esperar a que el servidor responda.
echo [3/3] Esperando a que el servidor este listo...
set /a intentos=0
:espera
set /a intentos+=1
if %intentos% gtr 40 (
    echo.
    echo ERROR: El servidor no respondio en 40 segundos.
    echo Abre la ventana minimizada "Deep Mind Apnea" para ver el error.
    echo Tambien puedes ejecutar manualmente:
    echo    cd backend
    echo    %PYTHON% -m uvicorn app.main:app --reload
    pause
    exit /b 1
)
timeout /t 1 >nul
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto espera

echo    Servidor listo.
echo.
echo ========================================
echo  Abriendo la app en tu navegador...
echo ========================================
start "" "http://127.0.0.1:8000/"

echo.
echo La app esta corriendo en: http://127.0.0.1:8000/
echo Para detenerla, cierra la ventana minimizada "Deep Mind Apnea"
echo o presiona Ctrl+C en esa consola.
echo.
pause
