@echo off
rem Step 2a: make Instagram Reels for the newest episode. See docs/02a-make-reels.md.
cd /d "%~dp0.."
python -m intake.reels %*
echo.
pause
