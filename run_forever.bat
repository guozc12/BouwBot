@echo off
:start
call "C:\Users\%USERNAME%\anaconda3\Scripts\activate.bat" base
start /b pythonw main.py
timeout /t 5 /nobreak >nul
goto start 