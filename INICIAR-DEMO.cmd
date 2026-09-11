@echo off
cd /d "%~dp0"
echo Iniciando prueba DEMO de oro. Sin stop ni timeout; target activo.
echo Ctrl+C detiene nuevas entradas. Las posiciones abiertas no se cierran.
if not exist ".venv\Scripts\python.exe" (
  echo Falta .venv. Siga los pasos de instalacion del README en esta carpeta.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m bot.live_demo --send-demo
pause
