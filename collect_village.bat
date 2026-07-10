@echo off
rem Village forecast: publish times 02,05,08,11,14,17,20,23 +15min
cd /d "%~dp0"
if not exist logs mkdir logs
set PY=python
if exist "C:\Users\kimna\AppData\Local\Programs\Python\Python314\python.exe" set PY=C:\Users\kimna\AppData\Local\Programs\Python\Python314\python.exe
if defined PYTHON_EXE set PY=%PYTHON_EXE%
"%PY%" run.py village >> logs\collect.log 2>&1
