@echo off
rem Run by Windows Task Scheduler once a day. See docs/event-calendar.md.
cd /d "%~dp0.."
python -m intake.events %*
