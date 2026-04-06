@echo off
REM Live Trading Scanner - Every 15 Minutes
REM Schedule this in Windows Task Scheduler

cd "C:\Users\yashs\Documents\Trading Bot\file1"
python live_scanner.py --scan
