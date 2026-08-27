@echo off
title AI Market Analyzer - Instalar Inicializacao
echo.
echo ========================================
echo   Configurando inicializacao automatica...
echo ========================================
echo.

:: Kill existing server
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul

:: Create shortcut in Startup folder (does not need admin)
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

:: Create powershell command to make the shortcut
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTUP%\AI-Market-Analyzer.lnk'); $s.TargetPath = 'C:\Users\Paulo Roberto\OneDrive\Documentos\Default Project\AI-Market-Analyzer\start_silent.vbs'; $s.WorkingDirectory = 'C:\Users\Paulo Roberto\OneDrive\Documentos\Default Project\AI-Market-Analyzer'; $s.Save()"

echo [OK] Atalho criado na pasta Inicializacao.
echo     - O servidor vai iniciar automaticamente ao fazer login no Windows
echo     - Roda em background sem janela
echo.

echo Iniciando o servidor agora...
start "" "C:\Users\Paulo Roberto\OneDrive\Documentos\Default Project\AI-Market-Analyzer\iniciar_background.bat"
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   Servidor rodando!
echo.
echo   PC:       http://localhost:8000
echo   Celular:  http://192.168.15.8:8000
echo   (mesma rede WiFi)
echo.
echo   Para parar: execute stop.bat
echo ========================================
echo.
pause
