"""
a13x-register-plugin console command.

Registering the A13x plug-in has always required opening Maya and
running installer.install() from the Script Editor - the install
scripts only ever pip-installed the package and then printed those two
lines for you to paste in yourself. This module closes that gap: it
lets you run the same registration from a plain terminal, right after
`pip install a13x`, by briefly spinning up a headless Maya session
(mayapy + maya.standalone) just long enough to do it.

Two things happen when this runs, and it's worth knowing which is
which - see docs/A13x_Quick_Start.pdf, Section 2.6, for the full
explanation:

  1. Command registration (a13xGeoMaster, etc.) works fully headless -
     these don't need Maya's UI at all.
  2. Building the A13x shelf does NOT work headless - shelf.py needs
     Maya's actual shelf UI ($gShelfTopLevel) to attach to, which
     doesn't exist in a headless session. shelf.py already detects
     this and skips with a warning rather than erroring. Since
     Autoload gets turned on either way, the shelf builds itself
     automatically the very next time you open Maya normally - you
     just won't see it appear from this command directly.

This module deliberately does NOT import a13x.installer (or
maya.cmds) at the top level. maya.cmds isn't safely callable in a
plain mayapy process until maya.standalone.initialize() has run, so
that has to happen first, before anything else in this package
touches maya.cmds - importing a13x.installer at module level here
would do that too early.
"""

import sys


def cli_main():
    """Entry point for the `a13x-register-plugin` console command."""
    try:
        import maya.standalone
    except ImportError:
        print("A13x: maya.standalone is not available. This command must be run "
              "with mayapy (Maya's own Python) - e.g.:")
        print("")
        print("    mayapy -m a13x.headless")
        print("")
        print("not a regular 'python' or 'python3'.")
        sys.exit(1)

    # If this is somehow already running inside an initialized Maya
    # session, don't double-initialize (and don't tear it down after).
    already_initialized = False
    try:
        import maya.cmds as cmds
        cmds.about(version=True)
        already_initialized = True
    except Exception:
        pass

    if not already_initialized:
        print("A13x: starting a temporary headless Maya session to register the plug-in...")
        maya.standalone.initialize(name="python")

    try:
        import a13x.installer as installer
        installer.install()
        print("")
        print("Note: the A13x shelf itself needs Maya's UI to attach to, so it did")
        print("NOT build in this headless session - that's expected, not an error.")
        print("It will appear automatically the next time you open Maya normally,")
        print("since Autoload was just turned on.")
    finally:
        if not already_initialized:
            try:
                maya.standalone.uninitialize()
            except Exception:
                pass


if __name__ == "__main__":
    cli_main()
