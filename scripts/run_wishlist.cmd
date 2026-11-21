@echo off
rem Run by Windows Task Scheduler once a day. See docs/wishlist.md.
cd /d "%~dp0.."
python -m intake.wishlist %*
