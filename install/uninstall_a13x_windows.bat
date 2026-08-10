@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   A13x uninstaller - locating mayapy.exe
echo ============================================
echo.

set "PF=%ProgramFiles%"
set "PF86=%ProgramFiles(x86)%"
set COUNT=0

rem --- 1. Check if mayapy is already on PATH ---
where mayapy.exe >nul 2>nul
if %ERRORLEVEL%==0 (
    for /f "delims=" %%P in ('where mayapy.exe') do (
        call :ADD_CANDIDATE "%%P"
    )
)

rem --- 2. Scan default Autodesk install folders for any Maya version ---
for %%D in ("%PF%\Autodesk" "%PF86%\Autodesk") do (
    if exist "%%~D" (
        for /d %%M in ("%%~D\Maya*") do (
            if exist "%%M\bin\mayapy.exe" (
                call :ADD_CANDIDATE "%%M\bin\mayapy.exe"
            )
        )
    )
)

rem --- 3. MAYA_LOCATION environment variable, if set ---
if defined MAYA_LOCATION (
    if exist "%MAYA_LOCATION%\bin\mayapy.exe" (
        call :ADD_CANDIDATE "%MAYA_LOCATION%\bin\mayapy.exe"
    )
)

rem --- 4. Windows Registry - catches Maya installed to a custom drive/folder ---
for /f "tokens=*" %%A in ('reg query "HKLM\SOFTWARE\Autodesk\Maya" 2^>nul') do (
    echo %%A | findstr /I /C:"\Maya\" >nul
    if not errorlevel 1 (
        for /f "usebackq tokens=1,2,*" %%X in (`reg query "%%A\Setup\InstallPath" 2^>nul ^| findstr /I "REG_SZ"`) do (
            set "REG_INSTALLDIR=%%Z"
            if exist "!REG_INSTALLDIR!bin\mayapy.exe" call :ADD_CANDIDATE "!REG_INSTALLDIR!bin\mayapy.exe"
        )
    )
)

if "%COUNT%"=="0" (
    echo No Maya installation was found automatically - checked PATH, the default
    echo Program Files locations, MAYA_LOCATION, and the Windows Registry.
    echo.
    echo mayapy.exe cannot be separately downloaded - it only exists as part of
    echo an actual Autodesk Maya installation. Plain python.exe also works for
    echo this uninstall step specifically, if you have any Python 3 installed.
    echo.
    set /p MAYAPY_PATH="Paste a full path to mayapy.exe or python.exe: "
) else (
    set "MAYAPY_PATH=!MAYAPY_1!"
    echo Using: !MAYAPY_PATH!
    echo (only one mayapy is needed here - unlike installing, this cleans up
    echo  every Maya version's plug-in stub in one pass, not just this one^)
)

if not exist "!MAYAPY_PATH!" (
    echo.
    echo ERROR: "!MAYAPY_PATH!" does not exist. Aborting.
    pause
    exit /b 1
)

echo.
echo Delegating to a13x's own uninstaller (handles the Maya plug-in stub,
echo the pip package, and a sweep for stray copies in one step)...
"!MAYAPY_PATH!" -c "from a13x.uninstaller import cli_main; cli_main()"
if not errorlevel 1 (
    echo.
    echo ============================================
    echo   A13x fully removed
    echo ============================================
    echo To reinstall cleanly afterward, use install_a13x_windows.bat, or run:
    echo.
    echo     "!MAYAPY_PATH!" -m pip install --no-cache-dir --force-reinstall a13x
    echo.
    pause
    exit /b 0
)

echo a13x isn't importable under this mayapy - falling back to a manual sweep.
echo.
echo Step 1/2 - unregistering the Maya plug-in stub (if any)...
"!MAYAPY_PATH!" -c "import a13x.installer as installer; installer.uninstall()" 2>nul
if errorlevel 1 echo a13x package not importable with this mayapy - skipping plug-in stub removal.

echo.
echo Step 2/2 - sweeping every known Python install location for a13x...
echo (this catches a13x if it was pip-installed with a DIFFERENT Python than
echo  mayapy above - e.g. the python.org per-user installer, Windows Store
echo  Python, or a system-wide install)
set "SCRIPT_DIR=%~dp0"
"!MAYAPY_PATH!" "!SCRIPT_DIR!purge_a13x.py" --purge
if errorlevel 1 (
    where py >nul 2>nul && py "!SCRIPT_DIR!purge_a13x.py" --purge
    where python >nul 2>nul && python "!SCRIPT_DIR!purge_a13x.py" --purge
)

echo.
echo ============================================
echo   A13x fully removed
echo ============================================
echo To reinstall cleanly afterward, use install_a13x_windows.bat, or run:
echo.
echo     "!MAYAPY_PATH!" -m pip install --no-cache-dir --force-reinstall a13x
echo.
echo If a13x still shows up anywhere, run this for a full report of every
echo location on disk that was checked:
echo.
echo     py "!SCRIPT_DIR!purge_a13x.py"
echo.
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
