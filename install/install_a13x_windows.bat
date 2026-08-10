@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   A13x installer - locating Maya
echo ============================================
echo.

set "PF=%ProgramFiles%"
set "PF86=%ProgramFiles(x86)%"
set COUNT=0

rem --- helper: add a candidate path only if it exists and isn't already in the list ---
rem (called via "call :ADD_CANDIDATE path" - see label at bottom of script)

rem --- 1. Check if mayapy is already on PATH ---
where mayapy.exe >nul 2>nul
if %ERRORLEVEL%==0 (
    for /f "delims=" %%P in ('where mayapy.exe') do (
        call :ADD_CANDIDATE "%%P"
    )
)

rem --- 2. Scan default Autodesk install folders for every Maya version ---
for %%D in ("%PF%\Autodesk" "%PF86%\Autodesk") do (
    if exist "%%~D" (
        for /d %%M in ("%%~D\Maya*") do (
            if exist "%%M\bin\mayapy.exe" (
                call :ADD_CANDIDATE "%%M\bin\mayapy.exe"
            )
        )
    )
)

rem --- 3. MAYA_LOCATION environment variable, if Maya or a launcher set it ---
if defined MAYA_LOCATION (
    if exist "%MAYA_LOCATION%\bin\mayapy.exe" (
        call :ADD_CANDIDATE "%MAYA_LOCATION%\bin\mayapy.exe"
    )
)

rem --- 4. Windows Registry - catches Maya installed to a custom drive/folder,
rem     which steps 1-2 above would miss entirely. Best-effort: registry key
rem     names/values have varied slightly across Maya releases, so this may
rem     not catch every version - it's an addition, not a replacement, for
rem     steps 1-3 above. ---
for /f "tokens=*" %%A in ('reg query "HKLM\SOFTWARE\Autodesk\Maya" 2^>nul') do (
    echo %%A | findstr /I /C:"\Maya\" >nul
    if not errorlevel 1 (
        for /f "usebackq tokens=1,2,*" %%X in (`reg query "%%A\Setup\InstallPath" 2^>nul ^| findstr /I "REG_SZ"`) do (
            set "REG_INSTALLDIR=%%Z"
            if exist "!REG_INSTALLDIR!bin\mayapy.exe" call :ADD_CANDIDATE "!REG_INSTALLDIR!bin\mayapy.exe"
        )
    )
)

if "%COUNT%"=="0" goto NOT_FOUND
goto FOUND_SOME

:NOT_FOUND
echo No Maya installation was found automatically - checked PATH, the default
echo Program Files locations, MAYA_LOCATION, and the Windows Registry.
echo.
echo IMPORTANT: mayapy.exe cannot be separately downloaded or installed - it
echo only exists as part of an actual Autodesk Maya installation. If Maya
echo genuinely isn't installed on this machine, install Maya first; this
echo script cannot substitute a regular Python install for it.
echo.
echo If Maya IS installed here, the surest way to get the exact path: open
echo Maya, go to the Script Editor (Python tab), and run:
echo.
echo     import sys; print(sys.executable)
echo.
echo That prints mayapy's real path even if it's on a custom drive/folder.
echo.
:RETRY_PATH
set /p MAYAPY_1="Paste the full path to mayapy.exe (or leave blank to give up): "
if "%MAYAPY_1%"=="" (
    echo Aborting - nothing was installed.
    pause
    exit /b 1
)
if not exist "%MAYAPY_1%" (
    echo That path doesn't exist. Try again, or paste blank to give up.
    echo.
    goto RETRY_PATH
)
set COUNT=1

:FOUND_SOME
echo Found %COUNT% Maya install(s):
for /l %%i in (1,1,%COUNT%) do (
    call echo   !MAYAPY_%%i!
)

set "PIP_FLAGS=--upgrade"
if /I "%~1"=="--force" (
    echo.
    echo Force mode: bypassing pip's cache and reinstalling all files.
    set "PIP_FLAGS=--upgrade --force-reinstall --no-cache-dir"
)

set OK_COUNT=0
set FAIL_COUNT=0

for /l %%i in (1,1,%COUNT%) do (
    call set "MAYAPY_PATH=%%MAYAPY_%%i%%"
    call :INSTALL_ONE "!MAYAPY_PATH!"
)

echo.
echo ============================================
echo   Done
echo ============================================
echo Installed and registered successfully in %OK_COUNT% of %COUNT% Maya install(s^).
echo.
if %OK_COUNT% GTR 0 (
    echo Open any of the succeeded Maya versions normally - the A13x shelf builds
    echo itself automatically on that first launch ^(it needs Maya's UI to attach
    echo to, so it couldn't appear from this terminal directly^).
)
if %FAIL_COUNT% GTR 0 (
    echo.
    echo For any Maya version that failed above, finish it manually instead -
    echo open that Maya version, go to the Script Editor ^(Python tab^), and run:
    echo.
    echo     import a13x.installer as installer
    echo     installer.install()
)
echo.
echo Tip: re-run this script with --force to force a clean reinstall everywhere
echo instead of --upgrade. To fully remove A13x, use uninstall_a13x_windows.bat.
echo.
pause
exit /b 0

:INSTALL_ONE
set "THIS_MAYAPY=%~1"
if not exist "%THIS_MAYAPY%" (
    echo.
    echo SKIPPING "%THIS_MAYAPY%" - does not exist.
    set /a FAIL_COUNT+=1
    exit /b 1
)

echo.
echo ============================================
echo   Installing into: %THIS_MAYAPY%
echo ============================================
"%THIS_MAYAPY%" -m pip install %PIP_FLAGS% a13x >nul 2>nul
if errorlevel 1 (
    echo PyPI copy not available yet - installing from the bundled local copy instead...
    "%THIS_MAYAPY%" -m pip install --no-index --find-links "%~dp0..\dist" %PIP_FLAGS% a13x
    if errorlevel 1 (
        echo pip install FAILED for this Maya version.
        set /a FAIL_COUNT+=1
        exit /b 1
    )
)

echo Registering the plug-in (headless, no need to open Maya^)...
"%THIS_MAYAPY%" -c "from a13x.headless import cli_main; cli_main()"
if errorlevel 1 (
    echo Registration did not complete for this Maya version - pip install still succeeded.
    set /a FAIL_COUNT+=1
    exit /b 1
)

set /a OK_COUNT+=1
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
