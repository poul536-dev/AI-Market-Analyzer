@echo off
title AI Market Analyzer - Parando...
echo.
echo ========================================
echo   Parando AI Market Analyzer...
echo ========================================
echo.

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Matendo processo (PID: %%a)...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Servidor parado com sucesso!
echo.
pause
