"""
A13x environment check - a quick health check, not an installer.

Reports, for whichever Python interpreter runs this script:
  - Is a13x importable, and what version
  - Where it's installed
  - Is a PySide binding available (GeoMaster/Umbra need one)
  - If run with mayapy: Maya version, plug-in registration, Autoload status
  - Every a13x install found anywhere on the machine (via a13x.pathfinder),
    to catch stray/duplicate copies left by past mismatched installs

Ends with a plain-language verdict rather than just raw facts.

Usage:
    mayapy check_a13x.py       # full check, including Maya-side status
    python check_a13x.py       # package/PySide/stray-copy check only
"""

import importlib
import os
import sys


def _try_import(name):
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def check():
    issues = []
    notes = []

    print("=" * 50)
    print("A13x environment check")
    print("Interpreter: {0}".format(sys.executable))
    print("=" * 50)

    # 1. a13x itself
    a13x = _try_import("a13x")
    if a13x:
        version = getattr(a13x, "__version__", "unknown")
        location = os.path.dirname(a13x.__file__)
        print("a13x package:       FOUND  (v{0})".format(version))
        print("a13x location:      {0}".format(location))
    else:
        print("a13x package:       NOT FOUND on this interpreter's sys.path")
        notes.append("This interpreter can't import a13x - run this check with the "
                      "mayapy (or python) that a13x was actually pip-installed with.")

    # 2. PySide binding
    pyside6 = _try_import("PySide6")
    pyside2 = _try_import("PySide2")
    if pyside6:
        print("PySide6:            FOUND  ({0})".format(getattr(pyside6, "__version__", "unknown")))
    if pyside2:
        print("PySide2:            FOUND  ({0})".format(getattr(pyside2, "__version__", "unknown")))
    if not pyside6 and not pyside2:
        print("PySide:             NOT FOUND")
        if a13x:
            issues.append("a13x is installed but no PySide binding (PySide2 or PySide6) is "
                           "available on this interpreter - GeoMaster and Umbra's windows will "
                           "fail to open. Maya normally ships one of these itself; this usually "
                           "means the check is running with a different Python than mayapy.")

    # 3. Maya-side status (only meaningful under mayapy)
    maya_cmds = _try_import("maya.cmds")
    registered = False
    if maya_cmds:
        already_initialized = False
        try:
            maya_cmds.about(version=True)
            already_initialized = True
        except Exception:
            pass

        standalone_started = False
        if not already_initialized:
            try:
                import maya.standalone
                maya.standalone.initialize(name="python")
                standalone_started = True
            except Exception as exc:
                print("Maya:               maya.cmds present but couldn't start a headless "
                      "session ({0})".format(exc))
                maya_cmds = None

        if maya_cmds:
            try:
                ver = maya_cmds.about(version=True)
                print("Maya version:       {0}".format(ver))

                plugins_dir = os.path.join(maya_cmds.internalVar(userAppDir=True), ver, "plug-ins")
                stub = os.path.join(plugins_dir, "a13x_plugin.py")
                if os.path.exists(stub):
                    print("Plug-in stub:       FOUND  ({0})".format(stub))
                else:
                    print("Plug-in stub:       NOT FOUND  (expected in {0})".format(plugins_dir))

                try:
                    registered = bool(maya_cmds.pluginInfo("a13x_plugin.py", query=True, registered=True))
                except Exception:
                    registered = False

                if registered:
                    try:
                        loaded = maya_cmds.pluginInfo("a13x_plugin.py", query=True, loaded=True)
                        print("Plug-in loaded:     {0}".format(loaded))
                    except Exception:
                        pass
                    try:
                        autoload = maya_cmds.pluginInfo("a13x_plugin.py", query=True, autoload=True)
                        print("Autoload enabled:   {0}".format(autoload))
                        if not autoload:
                            issues.append("The plug-in is registered but Autoload is OFF - it won't "
                                          "load automatically next time Maya starts. Re-run "
                                          "installer.install() or a13x-register-plugin.")
                    except Exception:
                        print("Autoload enabled:   unknown (couldn't query)")
                else:
                    print("Plug-in registered: NO")
                    if a13x:
                        issues.append("a13x is importable but not yet registered as a Maya plug-in - "
                                      "run installer.install() from Maya's Script Editor, or "
                                      "a13x-register-plugin from a terminal.")
            except Exception as exc:
                print("Maya:               check skipped ({0})".format(exc))
            finally:
                if standalone_started:
                    try:
                        maya.standalone.uninitialize()
                    except Exception:
                        pass
    else:
        print("Maya:               maya.cmds not importable (this isn't mayapy, or Maya isn't installed)")

    # 4. Every a13x install found anywhere on the machine (stray-copy check)
    pf = _try_import("a13x.pathfinder")
    all_installs = []
    if pf:
        try:
            all_installs = pf.find_all_installs()
        except Exception:
            pass
        print("")
        print("All a13x installs found on this machine:")
        if all_installs:
            for i in all_installs:
                print("  - {0}".format(i))
        else:
            print("  (filesystem search found none either)")
        if len(all_installs) > 1:
            issues.append("{0} separate a13x installs found on this machine - likely leftovers "
                          "from installing with more than one Python over time. Consider running "
                          "a13x-purge (or a13x-purge --dry-run first) to clean up.".format(len(all_installs)))
    else:
        notes.append("Couldn't check for other stray installs (a13x.pathfinder not importable here).")

    # 5. Verdict
    print("")
    print("=" * 50)
    print("Verdict")
    print("=" * 50)
    if not issues:
        print("No issues found - this environment looks consistent.")
    else:
        for i in issues:
            print("  ! {0}".format(i))
    for n in notes:
        print("  (note) {0}".format(n))
    print("")


if __name__ == "__main__":
    check()
