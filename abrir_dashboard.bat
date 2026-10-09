@echo off
cd /d "%~dp0"
title Dashboard Meta Ads
".venv\Scripts\python.exe" dashboard\servidor.py %*
pause
