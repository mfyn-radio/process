@echo off
rem Run by Windows Task Scheduler once a day. See docs/show-calendar.md.
cd /d "%~dp0.."
python -m intake.events %*
