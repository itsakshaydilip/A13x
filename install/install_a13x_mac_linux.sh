#!/usr/bin/env bash
# A13x installer - finds EVERY Maya version on this machine and installs +
# registers the plug-in into all of them automatically. No picking required.
set -e

echo "============================================"
echo "  A13x installer - locating Maya"
echo "============================================"
echo

CANDIDATES=()

# 1. Already on PATH?
if command -v mayapy >/dev/null 2>&1; then
    CANDIDATES+=("$(command -v mayapy)")
fi

# 2. macOS default install locations (every version found)
for d in /Applications/Autodesk/maya*/Maya.app/Contents/bin/mayapy; do
    [ -x "$d" ] && CANDIDATES+=("$d")
done

# 3. Linux default install locations (every version found)
for d in /usr/autodesk/maya*/bin/mayapy; do
    [ -x "$d" ] && CANDIDATES+=("$d")
done

# 4. MAYA_LOCATION environment variable, if Maya or a launcher set it
if [ -n "$MAYA_LOCATION" ] && [ -x "$MAYA_LOCATION/bin/mayapy" ]; then
    CANDIDATES+=("$MAYA_LOCATION/bin/mayapy")
fi

# De-duplicate while preserving order
UNIQUE=()
for c in "${CANDIDATES[@]}"; do
    skip=0
    for u in "${UNIQUE[@]}"; do
        [ "$c" == "$u" ] && skip=1 && break
    done
    [ "$skip" -eq 0 ] && UNIQUE+=("$c")
done
CANDIDATES=("${UNIQUE[@]}")

if [ ${#CANDIDATES[@]} -eq 0 ]; then
    echo "No Maya installation was found automatically - checked PATH, the"
    echo "default Autodesk folders, and MAYA_LOCATION."
    echo
    echo "IMPORTANT: mayapy cannot be separately downloaded or installed - it"
    echo "only exists as part of an actual Autodesk Maya installation. If Maya"
    echo "genuinely isn't installed on this machine, install Maya first; this"
    echo "script cannot substitute a regular Python install for it."
    echo
    echo "If Maya IS installed here, the surest way to get the exact path: open"
    echo "Maya, go to the Script Editor (Python tab), and run:"
    echo
    echo "    import sys; print(sys.executable)"
    echo
    read -r -p "Paste the full path to mayapy: " MANUAL_PATH
    CANDIDATES=("$MANUAL_PATH")
fi

echo "Found ${#CANDIDATES[@]} Maya install(s):"
for c in "${CANDIDATES[@]}"; do
    echo "  $c"
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"

PIP_FLAGS=(--upgrade)
if [ "$1" == "--force" ]; then
    echo
    echo "Force mode: bypassing pip's cache and reinstalling all files."
    PIP_FLAGS=(--upgrade --force-reinstall --no-cache-dir)
fi

SUCCEEDED=()
FAILED=()

for MAYAPY in "${CANDIDATES[@]}"; do
    if [ ! -x "$MAYAPY" ]; then
        echo
        echo "SKIPPING '$MAYAPY' - does not exist or is not executable."
        FAILED+=("$MAYAPY")
        continue
    fi

    echo
    echo "============================================"
    echo "  Installing into: $MAYAPY"
    echo "============================================"

    if ! "$MAYAPY" -m pip install "${PIP_FLAGS[@]}" a13x >/dev/null 2>&1; then
        echo "PyPI copy not available yet - installing from the bundled local copy instead..."
        if ! "$MAYAPY" -m pip install --no-index --find-links "$PACKAGE_ROOT/dist" "${PIP_FLAGS[@]}" a13x; then
            echo "pip install FAILED for this Maya version."
            FAILED+=("$MAYAPY")
            continue
        fi
    fi

    echo "Registering the plug-in (headless, no need to open Maya)..."
    if "$MAYAPY" -c "from a13x.headless import cli_main; cli_main()"; then
        SUCCEEDED+=("$MAYAPY")
    else
        echo "Registration did not complete for this Maya version - pip install still succeeded."
        FAILED+=("$MAYAPY")
    fi
done

echo
echo "============================================"
echo "  Done"
echo "============================================"
echo "Installed and registered successfully in ${#SUCCEEDED[@]} of ${#CANDIDATES[@]} Maya install(s):"
for s in "${SUCCEEDED[@]}"; do
    echo "  OK    $s"
done
for f in "${FAILED[@]}"; do
    echo "  FAILED  $f"
done
echo
if [ ${#SUCCEEDED[@]} -gt 0 ]; then
    echo "Open any of the succeeded Maya versions normally - the A13x shelf builds"
    echo "itself automatically on that first launch (it needs Maya's UI to attach"
    echo "to, so it couldn't appear from this terminal directly)."
fi
if [ ${#FAILED[@]} -gt 0 ]; then
    echo "For any Maya version listed as FAILED above, finish it manually instead -"
    echo "open that Maya version, go to the Script Editor (Python tab), and run:"
    echo
    echo "    import a13x.installer as installer"
    echo "    installer.install()"
fi
echo
echo "Tip: re-run this script with --force to force a clean reinstall everywhere"
echo "(bypasses pip's cache) instead of --upgrade. To fully remove A13x, use"
echo "uninstall_a13x_mac_linux.sh."
echo
