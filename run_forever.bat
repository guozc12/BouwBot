@echo off
:start
python main.py
echo Program stopped, restarting in 5 seconds...
timeout /t 5
goto start 