"""
A13x quick start opener.

This module has no dependency on Maya - it's meant to be run from a plain
terminal (or mayapy, without a Maya session) immediately after

    pip install a13x                                          (PyPI)
    pip install --index-url https://test.pypi.org/simple/ a13x  (TestPyPI)

Installing the package with pip does NOT run any code automatically -
pip/wheel deliberately does not execute arbitrary code as part of an
install. So instead this module is exposed as a console-script entry
point (see pyproject.toml), which gives you a single command to run
right after pip finishes:

    a13x-quickstart

That's the recommended first step after installing, before you ever
open Maya. The separate, Maya-side `a13x.installer.install()` call
(run once from Maya's Script Editor) only registers the plug-in in
Plug-in Manager - it no longer opens this guide itself, so the two
steps stay independent.
"""

import os
import sys
import subprocess


def _quick_start_pdf_path():
    return os.path.join(os.path.dirname(__file__), "docs", "A13x_Quick_Start.pdf")


def open_quick_start():
    """Open the Quick Start PDF with the OS's default PDF viewer.
    Never raises - prints the path instead if it can't launch a viewer."""
    pdf_path = _quick_start_pdf_path()

    if not os.path.isfile(pdf_path):
        print("A13x: Quick Start PDF not found at: {0}".format(pdf_path))
        return

    try:
        if sys.platform.startswith("win"):
            os.startfile(pdf_path)  # noqa: only exists on Windows
        elif sys.platform == "darwin":
            subprocess.Popen(["open", pdf_path])
        else:
            subprocess.Popen(["xdg-open", pdf_path])
        print("A13x: opening Quick Start guide ({0})".format(pdf_path))
    except Exception as exc:
        print("A13x: couldn't auto-open the Quick Start guide ({0}). "
              "You can open it manually from: {1}".format(exc, pdf_path))


if __name__ == "__main__":
    open_quick_start()
