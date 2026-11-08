@echo off
REM Double-click to start the backend (:8000) and frontend (:5173) together.
REM The first run installs everything automatically.
cd /d "%~dp0"

if not exist "node_modules" goto setup
if not exist "..\frontend\node_modules" goto setup
goto run

:setup
call node setup.mjs
if errorlevel 1 goto end

:run
call npm run dev

:end
pause
