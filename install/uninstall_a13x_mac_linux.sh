#!/usr/bin/env bash
# A13x uninstaller - locates mayapy automatically regardless of Maya version,
# unregisters the Maya plug-in stub, then removes the pip package - with
# --no-cache-dir so a later reinstall can't be served a stale cached wheel.
set -e

echo "============================================"
echo "  A13x uninstaller - locating mayapy"
echo "============================================"
echo

CANDIDATES=()

# 1. Already on PATH?
if command -v mayapy >/dev/null 2>&1; then
    CANDIDATES+=("$(command -v mayapy)")
fi

# 2. macOS default install locations (any version)
for d in /Applications/Autodesk/maya*/Maya.app/Contents/bin/mayapy; do
    [ -x "$d" ] && CANDIDATES+=("$d")
done

# 3. Linux default install locations (any version)
for d in /usr/autodesk/maya*/bin/mayapy; do
    [ -x "$d" ] && CANDIDATES+=("$d")
done

# 4. MAYA_LOCATION environment variable, if set
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
    echo "mayapy cannot be separately downloaded - it only exists as part of an"
    echo "actual Autodesk Maya installation. Plain python3 also works for this"
    echo "uninstall step specifically, if you have any Python 3 installed."
    echo
    read -r -p "Paste a full path to mayapy or python3: " MAYAPY
else
    MAYAPY="${CANDIDATES[0]}"
    echo "Using: $MAYAPY"
    echo "(only one mayapy is needed here - unlike installing, this cleans up"
    echo " every Maya version's plug-in stub in one pass, not just this one)"
fi

if [ ! -x "$MAYAPY" ]; then
    echo
    echo "ERROR: '$MAYAPY' does not exist or is not executable. Aborting."
    exit 1
fi

echo
echo "Delegating to a13x's own uninstaller (handles the Maya plug-in stub,"
echo "the pip package, and a sweep for stray copies in one step)..."
if "$MAYAPY" -c "from a13x.uninstaller import cli_main; cli_main()"; then
    echo
    echo "============================================"
    echo "  A13x fully removed"
    echo "============================================"
    echo "To reinstall cleanly afterward, use install_a13x_mac_linux.sh, or run:"
    echo
    echo "    $MAYAPY -m pip install --no-cache-dir --force-reinstall a13x"
    exit 0
fi

echo "a13x isn't importable under this mayapy - falling back to a manual sweep."
echo
echo "Step 1/2 - unregistering the Maya plug-in stub (if any)..."
"$MAYAPY" -c "
try:
    import a13x.installer as installer
    installer.uninstall()
except ImportError:
    print('a13x package not importable with this mayapy - skipping plug-in stub removal.')
" || true

echo
echo "Step 2/2 - sweeping every known Python install location for a13x..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_FOR_SWEEP="$MAYAPY"
if ! command -v "$PY_FOR_SWEEP" >/dev/null 2>&1 && [ ! -x "$PY_FOR_SWEEP" ]; then
    PY_FOR_SWEEP="python3"
fi
"$PY_FOR_SWEEP" "$SCRIPT_DIR/purge_a13x.py" --purge || python3 "$SCRIPT_DIR/purge_a13x.py" --purge || true

echo
echo "============================================"
echo "  A13x fully removed"
echo "============================================"
echo "To reinstall cleanly afterward, use install_a13x_mac_linux.sh, or run:"
echo
echo "    $MAYAPY -m pip install --no-cache-dir --force-reinstall a13x"
echo
echo "If a13x still shows up anywhere, run this for a full report of every"
echo "location on disk that was checked:"
echo
echo "    python3 $SCRIPT_DIR/purge_a13x.py"
echo
