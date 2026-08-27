@echo off
echo Starting LocalChef...
where python >nul 2>nul
if %errorlevel% equ 0 (
    "C:\Users\bschl\AppData\Local\Programs\Python\Python313\python.exe" app.py
) else (
    "C:\Users\bschl\AppData\Local\Programs\Python\Python313\python.exe" app.py
)
pause
