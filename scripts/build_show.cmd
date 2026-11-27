@echo off
rem Step 2: build the show from its Bandcamp playlist. See docs/02-create-show.md.
cd /d "%~dp0.."
python -m intake.build_show %*
echo.
pause
