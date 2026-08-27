@echo off
title AI Market Analyzer
echo.
echo ========================================
echo   AI Market Analyzer - Iniciando...
echo ========================================
echo.

:: Kill existing Python processes on port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Matendo processo na porta 8000 (PID: %%a)...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: Start server
echo Iniciando servidor...
start /min cmd /c "cd /d "%~dp0backend" && py -m uvicorn main:app --host 0.0.0.0 --port 8000"

:: Wait for server to be ready
echo Aguardando servidor ficar pronto...
timeout /t 4 /nobreak >nul

:: Open browser
echo Abrindo navegador...
start http://localhost:8000

echo.
echo ========================================
echo   Servidor rodando!
echo.
echo   PC:       http://localhost:8000
echo   Celular:  http://192.168.15.8:8000
echo   (mesma rede WiFi)
echo.
echo   Para parar, execute stop.bat
echo ========================================
echo.
pause
