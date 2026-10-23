@echo off
rem Run by Windows Task Scheduler every hour. See docs/01-acquire.md.
cd /d "%~dp0.."
python -m intake.acquire %*
