"""
A13x standalone uninstaller - console command `a13x-uninstall`.

Unlike a13x.installer.uninstall() (which requires maya.cmds and must
be run from inside Maya's Script Editor), this module needs nothing
but a plain terminal. It's exposed as a console-script entry point, so
it is GUARANTEED to exist after `pip install a13x` - from PyPI or
TestPyPI - on Windows, macOS, or Linux, unlike the install/uninstall
.bat and .sh files, which live outside the `a13x` package and are
never part of the published wheel or sdist.

What it does, in order:
  1. Removes any Maya plug-in stub (a13x_plugin.py) it can find in the
     standard per-user Maya plug-ins folders - searched directly on
     disk, since maya.cmds isn't available outside Maya.
  2. Uninstalls the pip package using THIS SAME interpreter
     (sys.executable) - guaranteed to be the right one, since pip just
     installed a13x-uninstall itself using this exact interpreter.
  3. Sweeps every other known Python install location (see
     a13x.pathfinder) for stray copies left by a previous mismatched
     pip install, and offers to remove those too.
"""

import glob
import os
import subprocess
import sys

from a13x.pathfinder import find_all_installs, purge_all

_STUB_FILENAME = "a13x_plugin.py"


def _maya_plugins_dirs():
    """Every per-user Maya plug-ins folder that might exist on this
    machine, across every installed Maya version - found directly on
    disk, without needing maya.cmds."""
    home = os.path.expanduser("~")
    dirs = []

    if sys.platform.startswith("win"):
        dirs += glob.glob(os.path.join(home, "Documents", "maya", "*", "plug-ins"))
    elif sys.platform == "darwin":
        dirs += glob.glob(os.path.join(home, "Library", "Preferences", "Autodesk", "maya", "*", "plug-ins"))
    else:
        dirs += glob.glob(os.path.join(home, "maya", "*", "plug-ins"))

    return dirs


def remove_maya_stub(verbose=True):
    """Delete a13x_plugin.py from every Maya version's plug-ins folder
    found on this machine. Returns the list of stub paths removed."""
    removed = []
    for plugins_dir in _maya_plugins_dirs():
        stub_path = os.path.join(plugins_dir, _STUB_FILENAME)
        if os.path.exists(stub_path):
            try:
                os.remove(stub_path)
                removed.append(stub_path)
                if verbose:
                    print("A13x: removed Maya plug-in stub: {0}".format(stub_path))
            except OSError as exc:
                print("A13x: couldn't remove {0}: {1}".format(stub_path, exc))

    if verbose and not removed:
        print("A13x: no Maya plug-in stub found (checked {0} Maya version folder(s)).".format(
            len(_maya_plugins_dirs())))
        print("Note: this only removes the stub file. If Plug-in Manager still lists it, "
              "untick it there too, or run installer.uninstall() from Maya's Script Editor.")

    return removed


def uninstall_pip_package(verbose=True):
    """Uninstall a13x using THIS interpreter's pip - guaranteed to
    match wherever this command itself was installed from."""
    if verbose:
        print("A13x: uninstalling the pip package using {0} ...".format(sys.executable))
    result = subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "a13x"],
        capture_output=not verbose,
    )
    return result.returncode == 0


def cli_main():
    """Entry point for the `a13x-uninstall` console command."""
    print("============================================")
    print("  A13x uninstaller")
    print("============================================")
    print("")

    print("Step 1/3 - removing the Maya plug-in stub (if any)...")
    remove_maya_stub()
    print("")

    print("Step 2/3 - uninstalling the pip package via this interpreter...")
    uninstall_pip_package()
    print("")

    print("Step 3/3 - sweeping every other known Python install location...")
    print("(catches a13x if it was ALSO pip-installed with a different Python)")
    others = [d for d in find_all_installs() if os.path.dirname(sys.executable) not in d]
    if others:
        purge_all()
    else:
        print("A13x: no other install locations found.")
    print("")

    print("============================================")
    print("  Done")
    print("============================================")
    print("To reinstall cleanly afterward:")
    print("    {0} -m pip install --no-cache-dir --force-reinstall a13x".format(
        os.path.basename(sys.executable)))


if __name__ == "__main__":
    cli_main()
