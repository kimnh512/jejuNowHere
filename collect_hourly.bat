@echo off
rem Hourly collect: nowcast + ultra + jeju_air (run at :50)
cd /d "%~dp0"
if not exist logs mkdir logs
set PY=python
if exist "C:\Users\kimna\AppData\Local\Programs\Python\Python314\python.exe" set PY=C:\Users\kimna\AppData\Local\Programs\Python\Python314\python.exe
if defined PYTHON_EXE set PY=%PYTHON_EXE%
"%PY%" run.py nowcast  >> logs\collect.log 2>&1
"%PY%" run.py ultra    >> logs\collect.log 2>&1
"%PY%" run.py jeju_air >> logs\collect.log 2>&1
