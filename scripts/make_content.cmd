@echo off
rem Step 2a: make the newest episode's baseline content. See docs/02a-make-episode-content.md.
cd /d "%~dp0.."
python -m intake.content %*
echo.
pause
