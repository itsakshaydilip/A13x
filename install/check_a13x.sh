#!/usr/bin/env bash
# A13x check - quick consistency check across every Python/Maya environment
# found on this machine. Not an installer - read-only diagnostics.
set -e

echo "============================================"
echo "  A13x check - locating Python/Maya environments"
echo "============================================"
echo

CANDIDATES=()

if command -v mayapy >/dev/null 2>&1; then
    CANDIDATES+=("$(command -v mayapy)")
fi
for d in /Applications/Autodesk/maya*/Maya.app/Contents/bin/mayapy /usr/autodesk/maya*/bin/mayapy; do
    [ -x "$d" ] && CANDIDATES+=("$d")
done
if [ -n "$MAYA_LOCATION" ] && [ -x "$MAYA_LOCATION/bin/mayapy" ]; then
    CANDIDATES+=("$MAYA_LOCATION/bin/mayapy")
fi
if command -v python3 >/dev/null 2>&1; then
    CANDIDATES+=("$(command -v python3)")
fi

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
    echo "No Python or Maya interpreter found automatically."
    read -r -p "Path to mayapy or python3 (blank to give up): " MANUAL
    [ -z "$MANUAL" ] && echo "Nothing to check." && exit 1
    CANDIDATES=("$MANUAL")
fi

echo "Found ${#CANDIDATES[@]} interpreter(s) to check:"
for c in "${CANDIDATES[@]}"; do echo "  $c"; done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for PY in "${CANDIDATES[@]}"; do
    echo
    "$PY" "$SCRIPT_DIR/check_a13x.py" || true
done

echo
echo "============================================"
echo "  Check complete"
echo "============================================"
