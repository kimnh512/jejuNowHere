@echo off
rem FastAPI server (uvicorn) - auto-restart loop. Registered as a startup task on the server.
cd /d "%~dp0"
if not exist logs mkdir logs
set PY=python
if exist "C:\Users\kimna\AppData\Local\Programs\Python\Python314\python.exe" set PY=C:\Users\kimna\AppData\Local\Programs\Python\Python314\python.exe
if defined PYTHON_EXE set PY=%PYTHON_EXE%
:loop
"%PY%" -m uvicorn api:app --host 0.0.0.0 --port 8000 >> logs\api.log 2>&1
timeout /t 5 /nobreak >nul
goto loop
