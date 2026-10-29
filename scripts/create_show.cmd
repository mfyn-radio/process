@echo off
rem Step 2: make an episode from a Bandcamp playlist, then its Reels. See docs/02-create-show.md.
cd /d "%~dp0.."
python -m intake.create_show %*
echo.
pause
