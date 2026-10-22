@echo off
REM Sistema real: requiere IMPRESORA_IP, IMPRESORA_SERIE, IMPRESORA_CODIGO_ACCESO en .env y OPENAI_API_KEY.
cd /d "%~dp0"
python -m orquestador
pause
