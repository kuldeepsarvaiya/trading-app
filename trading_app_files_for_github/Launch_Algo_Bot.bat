@echo off
title Intraday Algo Trading Bot Software
cd /d "C:\Users\Kuldeep\.gemini\antigravity\scratch\intraday-algo-bot"
set "PATH=C:\Users\Kuldeep\AppData\Local\Programs\Python\Python312;C:\Users\Kuldeep\AppData\Local\Programs\Python\Python312\Scripts;%PATH%"
echo Starting Intraday Algo Trading Bot Desktop Software...
start "" pythonw gui_app.py
exit
