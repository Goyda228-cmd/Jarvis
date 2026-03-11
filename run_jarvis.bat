@echo off
cd /d "C:\Users\it\Desktop\2 год\Сидоров Павел 2-4\java_script_2_4"

:loop
echo Starting Jarvis...
call .venv\Scripts\activate
python jarvis.py

echo Jarvis stopped. Restarting in 5 seconds...
timeout /t 5
goto loop