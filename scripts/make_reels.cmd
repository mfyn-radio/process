@echo off
rem Step 3: make Instagram Reels for the newest episode. See docs/03-make-reels.md.
cd /d "%~dp0.."
python -m intake.reels %*
echo.
pause
