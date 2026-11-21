@echo off
rem Copy the repo's Processing sketches to H:\My Drive\MFYN_Processing, so the
rem Drive copy always matches the repo. The repo is the master: never edit the
rem Drive copy. Run after `git pull`. See docs/working-on-the-pc.md.
rem Overwrites changed files on Drive, deletes nothing. Skips each sketch's
rem input\ and output\ folders and temporary files.
cd /d "%~dp0.."
set "DEST=%MFYN_SKETCHES_DRIVE%"
if "%DEST%"=="" set "DEST=H:\My Drive\MFYN_Processing"
for /d %%S in (processing\MFYN_*) do (
  robocopy "%%S" "%DEST%\%%~nxS" /E /XD input output /XF cover_tmp.png /NP /NJH /NJS
  if errorlevel 8 (
    echo Copying %%~nxS failed.
    exit /b 1
  )
)
echo Sketches copied to %DEST%.
exit /b 0
