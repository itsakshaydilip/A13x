"""
A13x
====
A Maya pipeline toolset (GeoMaster, Nomenclator, ThumbTac, Revention,
Substance Loader, Umbra) packaged as a single auto-loading Maya plug-in
with its own pinned "A13x" shelf.

Typical setup, run once per machine:

    1. Install the package using the installer script included in the
       distribution (install/install_a13x_windows.bat, or
       install/install_a13x_mac_linux.sh) - these auto-detect mayapy
       regardless of which Maya version is installed, and now also
       run step 2 below for you automatically, headlessly, right
       after the pip install.
    2. Only needed if step 1's automatic registration didn't run:
       either inside Maya's Script Editor -

           import a13x.installer as installer
           installer.install()

       - or from a plain terminal, no Maya UI needed (see
         a13x.headless):

           a13x-register-plugin

After that, the A13x plug-in appears in Windows > Settings/Preferences >
Plug-in Manager, ticked and set to Auto load, and the A13x shelf is
pinned next to your other shelves - the shelf specifically needs
Maya's UI to attach to, so a headless registration (terminal or
install script) shows it on your next normal Maya launch rather than
immediately.
"""

__version__ = "3.5.0"
