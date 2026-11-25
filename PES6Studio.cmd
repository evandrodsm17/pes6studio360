@echo off
setlocal
cd /d "%~dp0"
set "PES6PY=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if not exist "%PES6PY%" set "PES6PY=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not exist "%PES6PY%" (
  echo Python nao localizado. Consulte PES6STUDIO_LEIA-ME.md.
  pause
  exit /b 1
)
set "PES6ISO=%~1"
if not defined PES6ISO set "PES6ISO=%~dp0..\Pro Evolution Soccer 2006 [PAL].iso"
if not exist "%PES6ISO%" (
  echo ISO original nao encontrada. Arraste sua ISO original sobre este arquivo.
  pause
  exit /b 1
)
"%PES6PY%" -c "import json,sys,urllib.request,webbrowser; from pathlib import Path; c=json.load(urllib.request.urlopen('http://127.0.0.1:8765/config',timeout=1)); assert c.get('version')=='0.16' and Path(c['iso']).resolve()==Path(sys.argv[1]).resolve(); webbrowser.open('http://127.0.0.1:8765')" "%PES6ISO%" >nul 2>nul
if not errorlevel 1 exit /b 0
"%PES6PY%" pes6_studio_v10.py cv_extraido_v03 rv_e_extraido --we00 cv_we00_texturas --iso "%PES6ISO%"
if errorlevel 1 pause
