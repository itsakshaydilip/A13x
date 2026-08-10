"""
A13x installer.

`pip install a13x` (run against mayapy, Maya's own Python) puts the
package on Maya's sys.path, but it does NOT make the plug-in show up in
Plug-in Manager - Maya's plug-in loader only scans folders on
MAYA_PLUG_IN_PATH, not site-packages.

install() bridges that gap: it writes a tiny stub file into Maya's user
plug-ins folder that just imports the real plugin.py from this package,
loads it once, and switches "Auto load" on. From then on the checkbox in
Plug-in Manager is the only thing controlling it - same as any other
plug-in, and no Maya.env / userSetup.py editing required.

Usage (once per machine, in Maya's Script Editor):

    import a13x.installer as installer
    installer.install()

Prefer not to open Maya first? The install_a13x_* scripts (and the
a13x-register-plugin console command - see a13x.headless) run this
same install() from a plain terminal instead, via a temporary headless
Maya session. Command registration works fully that way; the A13x
shelf itself still needs Maya's UI to attach to, so it appears the
next time you open Maya normally rather than immediately.

install() also opens the Quick Start PDF once it's done, the same way
the standalone `a13x-quickstart` terminal command does (see
a13x.quickstart.open_quick_start). The PDF is located relative to
this module's own install path - i.e. wherever pip put the `a13x`
package on THIS machine (mayapy's site-packages on Windows, macOS, or
Linux) - so it resolves correctly regardless of platform or which
index (PyPI or TestPyPI) it was installed from.
"""

import os

import maya.cmds as cmds

from a13x.quickstart import open_quick_start

_STUB_FILENAME = "a13x_plugin.py"

_STUB_CONTENTS = '''"""Auto-generated A13x plug-in stub - do not hand-edit.
Regenerate any time with:
    import a13x.installer as installer
    installer.install()

This stub locates the a13x package itself before importing it, in
case it was pip-installed with a different interpreter than the one
launching Maya (see a13x.pathfinder for the full, documented version
of this same search - kept here as a plain, dependency-free copy so
it still works even if a13x isn't on sys.path yet).
"""
import glob
import os
import sys


def _find_a13x():
    try:
        import a13x  # noqa: F401
        return True
    except ImportError:
        pass

    home = os.path.expanduser("~")
    candidates = []

    if sys.platform.startswith("win"):
        pf_dirs = (os.environ.get("ProgramFiles", r"C:\\Program Files"),
                   os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)"))
        localappdata = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        appdata = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        for pf in pf_dirs:
            candidates += glob.glob(os.path.join(pf, "Autodesk", "Maya*", "Python", "Lib", "site-packages"))
            candidates += glob.glob(os.path.join(pf, "Autodesk", "Maya*", "Python3", "Lib", "site-packages"))
            candidates += glob.glob(os.path.join(pf, "Python3*", "Lib", "site-packages"))
        # python.org's current per-user installer (Python 3.13+), e.g. pythoncore-3.14-64
        candidates += glob.glob(os.path.join(localappdata, "Python", "pythoncore-3*-64", "Lib", "site-packages"))
        candidates += glob.glob(os.path.join(localappdata, "Python", "pythoncore-3*-32", "Lib", "site-packages"))
        candidates += glob.glob(os.path.join(localappdata, "Python", "pythoncore-3*-arm64", "Lib", "site-packages"))
        # python.org's older per-user installer layout
        candidates += glob.glob(os.path.join(localappdata, "Programs", "Python", "Python3*", "Lib", "site-packages"))
        candidates += glob.glob(os.path.join(appdata, "Python", "Python3*", "site-packages"))
        candidates += glob.glob(os.path.join("C:\\\\", "Python3*", "Lib", "site-packages"))
    elif sys.platform == "darwin":
        candidates += glob.glob("/Applications/Autodesk/maya*/Maya.app/Contents/Frameworks/"
                                 "Python.framework/Versions/*/lib/python3*/site-packages")
        candidates += glob.glob(os.path.join(home, "Library", "Python", "3*", "lib", "python", "site-packages"))
        candidates += glob.glob("/Library/Frameworks/Python.framework/Versions/3*/lib/python3*/site-packages")
        candidates += glob.glob("/opt/homebrew/lib/python3*/site-packages")
        candidates += glob.glob("/usr/local/lib/python3*/site-packages")
        candidates += glob.glob(os.path.join(home, ".pyenv", "versions", "*", "lib", "python3*", "site-packages"))
        for conda_root in ("anaconda3", "miniconda3", "miniforge3"):
            candidates += glob.glob(os.path.join(home, conda_root, "lib", "python3*", "site-packages"))
            candidates += glob.glob(os.path.join(home, conda_root, "envs", "*", "lib", "python3*", "site-packages"))
    else:
        candidates += glob.glob("/usr/autodesk/maya*/lib/python3*/site-packages")
        candidates += glob.glob(os.path.join(home, ".local", "lib", "python3*", "site-packages"))
        candidates += glob.glob("/usr/lib/python3*/site-packages")
        candidates += glob.glob("/usr/lib/python3/dist-packages")
        candidates += glob.glob("/usr/local/lib/python3*/site-packages")
        candidates += glob.glob(os.path.join(home, ".pyenv", "versions", "*", "lib", "python3*", "site-packages"))
        for conda_root in ("anaconda3", "miniconda3", "miniforge3"):
            candidates += glob.glob(os.path.join(home, conda_root, "lib", "python3*", "site-packages"))
            candidates += glob.glob(os.path.join(home, conda_root, "envs", "*", "lib", "python3*", "site-packages"))
    candidates += glob.glob(os.path.join(home, ".virtualenvs", "*", "lib", "python3*", "site-packages"))
    candidates += glob.glob(os.path.join(home, ".venv", "lib", "python3*", "site-packages"))

    for site_dir in candidates:
        if os.path.isdir(os.path.join(site_dir, "a13x")):
            if site_dir not in sys.path:
                sys.path.insert(0, site_dir)
            try:
                import a13x  # noqa: F401
                print("A13x: found package in {0}, added to sys.path.".format(site_dir))
                return True
            except ImportError:
                continue

    print("A13x: could not locate the 'a13x' package on this machine. "
          "Run 'mayapy -m pip install a13x' using the SAME mayapy that "
          "launches this copy of Maya, then reload the plug-in.")
    return False


_find_a13x()

from a13x.plugin import initializePlugin, uninitializePlugin, maya_useNewAPI
'''


def _plugins_dir():
    version_dir = cmds.about(version=True).split(" ")[0]
    path = os.path.join(cmds.internalVar(userAppDir=True), version_dir, "plug-ins")
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def install():
    """Write the plug-in stub, load it, turn Auto load on, then open
    the Quick Start guide from wherever pip installed this package."""
    plugins_dir = _plugins_dir()
    stub_path = os.path.join(plugins_dir, _STUB_FILENAME)

    with open(stub_path, "w") as fh:
        fh.write(_STUB_CONTENTS)

    already_loaded = False
    if cmds.pluginInfo(_STUB_FILENAME, query=True, registered=True):
        already_loaded = cmds.pluginInfo(_STUB_FILENAME, query=True, loaded=True)

    if not already_loaded:
        cmds.loadPlugin(stub_path)

    cmds.pluginInfo(_STUB_FILENAME, edit=True, autoload=True)

    print("A13x installed successfully.")
    print("Stub plug-in written to: {0}".format(stub_path))
    print("Toggle it any time via Windows > Settings/Preferences > "
          "Plug-in Manager > {0}".format(_STUB_FILENAME))

    open_quick_start()


def uninstall():
    """Unload the plug-in and remove the stub file. Leaves the pip
    package itself installed - run the a13x-uninstall console command
    from a terminal (installed alongside the package by pip - see
    a13x.uninstaller) to remove that too, and sweep for stray copies
    installed by a different interpreter."""
    plugins_dir = _plugins_dir()
    stub_path = os.path.join(plugins_dir, _STUB_FILENAME)

    if cmds.pluginInfo(_STUB_FILENAME, query=True, registered=True):
        if cmds.pluginInfo(_STUB_FILENAME, query=True, loaded=True):
            cmds.unloadPlugin(_STUB_FILENAME)

    if os.path.exists(stub_path):
        os.remove(stub_path)

    print("A13x plug-in stub removed from Plug-in Manager.")
    print("The pip package itself is still installed. To fully remove it - "
          "and sweep for any stray copies left by a previous mismatched "
          "install - run from a terminal (not Maya's Script Editor):")
    print("")
    print("    a13x-uninstall")
    print("")
    print("This command is installed automatically by pip alongside a13x "
          "itself, so it's always available after 'pip install a13x' - "
          "unlike a standalone .bat/.sh script, it doesn't depend on still "
          "having the original zip/repo the package was published from.")
