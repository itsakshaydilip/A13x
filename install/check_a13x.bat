@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   A13x check - locating Python/Maya environments
echo ============================================
echo.

set "PF=%ProgramFiles%"
set "PF86=%ProgramFiles(x86)%"
set COUNT=0

rem --- 1. mayapy already on PATH ---
where mayapy.exe >nul 2>nul
if %ERRORLEVEL%==0 (
    for /f "delims=" %%P in ('where mayapy.exe') do call :ADD_CANDIDATE "%%P"
)

rem --- 2. Default Autodesk install folders, every Maya version ---
for %%D in ("%PF%\Autodesk" "%PF86%\Autodesk") do (
    if exist "%%~D" (
        for /d %%M in ("%%~D\Maya*") do (
            if exist "%%M\bin\mayapy.exe" call :ADD_CANDIDATE "%%M\bin\mayapy.exe"
        )
    )
)

rem --- 3. MAYA_LOCATION, if set ---
if defined MAYA_LOCATION (
    if exist "%MAYA_LOCATION%\bin\mayapy.exe" call :ADD_CANDIDATE "%MAYA_LOCATION%\bin\mayapy.exe"
)

rem --- 4. Plain python/py on PATH too, to catch a13x installed outside Maya entirely ---
where python.exe >nul 2>nul
if %ERRORLEVEL%==0 (
    for /f "delims=" %%P in ('where python.exe') do call :ADD_CANDIDATE "%%P"
)

if "%COUNT%"=="0" (
    echo No Python or Maya interpreter was found automatically on PATH or in the
    echo default Autodesk locations. Paste one to check directly, or leave blank
    echo to give up.
    echo.
    set /p MAYAPY_1="Path to mayapy.exe or python.exe: "
    if "!MAYAPY_1!"=="" (
        echo Nothing to check. Exiting.
        pause
        exit /b 1
    )
    set COUNT=1
)

echo Found %COUNT% interpreter(s) to check:
for /l %%i in (1,1,%COUNT%) do call echo   !MAYAPY_%%i!

set "SCRIPT_DIR=%~dp0"

for /l %%i in (1,1,%COUNT%) do (
    call set "THIS_PY=%%MAYAPY_%%i%%"
    echo.
    "!THIS_PY!" "%SCRIPT_DIR%check_a13x.py"
)

echo.
echo ============================================
echo   Check complete
echo ============================================
pause
exit /b 0

:ADD_CANDIDATE
set "NEW_PATH=%~1"
if "%NEW_PATH%"=="" exit /b 0
if not exist "%NEW_PATH%" exit /b 0
if %COUNT% GTR 0 (
    for /l %%j in (1,1,%COUNT%) do (
        call set "EXISTING=%%MAYAPY_%%j%%"
        if /I "!EXISTING!"=="%NEW_PATH%" exit /b 0
    )
)
set /a COUNT+=1
set "MAYAPY_%COUNT%=%NEW_PATH%"
exit /b 0
