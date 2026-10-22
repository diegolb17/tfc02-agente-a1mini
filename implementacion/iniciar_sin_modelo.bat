@echo off
REM Impresora y camara reales, modelo con respuestas fijas (sin gasto en OpenAI).
cd /d "%~dp0"
python -m orquestador --simular-modelo
pause
