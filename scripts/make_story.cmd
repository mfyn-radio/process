@echo off
rem Make a featured-album Instagram Story from MFYN_Library. See docs/featured-album-story.md.
cd /d "%~dp0.."
python -m intake.stories %*
echo.
pause
