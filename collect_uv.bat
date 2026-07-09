@echo off
rem UV index: publish times 06, 18 +40min
cd /d "%~dp0"
if not exist logs mkdir logs
"C:\Users\kimna\AppData\Local\Programs\Python\Python314\python.exe" run.py uv >> logs\collect.log 2>&1
