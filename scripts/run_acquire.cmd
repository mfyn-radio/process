@echo off
rem Run by Windows Task Scheduler once a day. See docs/01-acquire.md.
cd /d "%~dp0.."
python -m intake.acquire %*
