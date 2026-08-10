"""
a13x.tools
================
Each module in this package is one of the six A13x tools, kept as close
to the original standalone script as possible (see the "Editing and
Modification" section of the documentation for the two small changes
that WERE necessary).

geomaster.py does a bare `import config` / `import logger` (this is how
it shipped, written for Maya's flat "scripts/" folder convention rather
than a real Python package). Rather than rewrite geomaster.py's internals,
we add this package's own folder to sys.path once, on first import, so
those bare imports keep resolving exactly as they did before packaging.
"""

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.append(_THIS_DIR)
