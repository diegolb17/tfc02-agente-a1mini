@echo off
REM Bot real de Telegram con impresora, camara y modelo simulados.
REM El primer /start privado queda registrado como operador autorizado.
cd /d "%~dp0"
python -m orquestador --simular --registrar-operador
pause
