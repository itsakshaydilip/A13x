#!/usr/bin/env python3
"""
Standalone A13x purge / locate utility.

Unlike `mayapy -m pip uninstall a13x`, this script does NOT need to be
run with the specific interpreter that originally installed a13x, and
does NOT require a13x (or even pip) to be importable. It searches every
common Python install layout on Windows, macOS, and Linux directly on
disk - including mayapy, python.org's newer per-user installer
(pythoncore-3.14-64 and similar), Homebrew, conda, and pyenv - and
reports (or removes) every copy of a13x it finds.

This is the tool to reach for when `pip uninstall a13x` says the
package isn't installed, but you know it's on the machine somewhere -
that almost always means it was installed with a DIFFERENT Python
than the one pip is currently uninstalling from.

Usage:
    python purge_a13x.py                 # list every install found
    python purge_a13x.py --dry-run       # show what --purge would remove
    python purge_a13x.py --purge         # actually remove every copy found

Can be run with ANY Python 3 interpreter - it does not need to be
mayapy, and does not need a13x installed under that interpreter.
"""

import os
import sys

# This script lives in <package_root>/install/. The pathfinder module
# lives in <package_root>/src/a13x/pathfinder.py. Reach it directly by
# path so this script works standalone even when a13x isn't
# importable under whichever Python is running it right now.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(os.path.dirname(_THIS_DIR), "src")

if os.path.isdir(os.path.join(_SRC_DIR, "a13x")):
    # Running from within the source checkout / extracted zip.
    sys.path.insert(0, _SRC_DIR)
    from a13x.pathfinder import find_all_installs, purge_all
else:
    # Running standalone (e.g. copied out on its own) - fall back to
    # whatever a13x.pathfinder is reachable on sys.path, if any.
    try:
        from a13x.pathfinder import find_all_installs, purge_all
    except ImportError:
        print("Could not find a13x.pathfinder. Run this script from inside the "
              "a13x_package/install/ folder, or with a13x already on sys.path.")
        sys.exit(1)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--purge", action="store_true",
                         help="Remove every a13x install found (package folder, dist-info, console script).")
    parser.add_argument("--dry-run", action="store_true",
                         help="Show what --purge would remove, without removing anything.")
    args = parser.parse_args()

    if args.purge or args.dry_run:
        cleaned = purge_all(dry_run=args.dry_run)
        verb = "Would clean" if args.dry_run else "Cleaned"
        print("")
        print("{0} {1} location(s).".format(verb, len(cleaned)))
        if not args.dry_run and cleaned:
            print("Note: the Maya plug-in stub (if any) is separate - run "
                  "installer.uninstall() from Maya's Script Editor, or the "
                  "uninstall_a13x_* script, to remove that too.")
    else:
        installs = find_all_installs()
        if installs:
            print("Found a13x in {0} location(s):".format(len(installs)))
            for i in installs:
                print("  {0}".format(i))
            print("")
            print("Run with --purge to remove all of these, or --dry-run to preview first.")
        else:
            print("No a13x install found in any searched location.")
            print("(This searches Maya's mayapy, python.org installers - including the "
                  "newer per-user 'pythoncore-<version>-64' layout - Homebrew, conda, "
                  "pyenv, and standard system Python locations. See a13x/pathfinder.py "
                  "for the exact list.)")


if __name__ == "__main__":
    main()
