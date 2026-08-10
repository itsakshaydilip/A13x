# A13x

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[[![DOI](https://zenodo.org/badge/DOI/PENDING.svg)](#how-to-cite)](https://doi.org/10.5281/zenodo.21879886)
<!-- Replace the DOI badge above with the real one Zenodo issues after your first tagged release. -->

A Maya pipeline plug-in that bundles six tools behind a single pinned
shelf named **A13x**:

- **GeoMaster** - geometry / UV / shader sanity checker
- **Nomenclator** - hierarchy renamer (GRP / SGRP / GEO / LOC)
- **ThumbTac** - interactive pivot grid tool
- **Revention** - versioned autosave utility
- **Substance Loader** - Arnold PBR texture loader
- **Umbra** - scene cleaner & character model checker

Full prerequisites, installation, customization, and licensing details
are in the accompanying documentation (`docs/A13x_Quick_Start.pdf`),
not repeated here.

## Quick start

### 1. Install

`mayapy` is not on PATH by default, and its full path changes with
every Maya version - so rather than typing a pip command by hand,
run the installer script included in this package:

- **Windows:** double-click `install/install_a13x_windows.bat`
- **macOS / Linux:** run `./install/install_a13x_mac_linux.sh`

Either script scans the default Autodesk install folders for whichever
Maya version(s) are on that machine, and installs `a13x` into the
right one automatically - asking you to pick if more than one Maya
version is present, or to paste a path only if nothing is found
automatically. The script calls pip internally; you never need to
type a pip command yourself.

Prefer a terminal? The same result, run manually:

```bash
# Straight from this repository
mayapy -m pip install git+https://github.com/itsakshaydilip/A13x.git

# Or from a local clone, using the pre-built wheel in dist/
mayapy -m pip install dist/a13x-3.5.0-py3-none-any.whl
```

Either command installs `a13x` into mayapy's own site-packages - see
`docs/A13x_Quick_Start.pdf`, Section 2.5, for the exact path per OS.

### 2. Register the plug-in in Maya

The install scripts above already do this for you automatically,
right after the pip install - via `a13x-register-plugin` (see
`a13x.headless`), which briefly starts a headless Maya session just
long enough to register the plug-in, no Maya UI required. Command
registration works fully that way; the **A13x** shelf itself needs
Maya's actual UI to attach to, so it can't appear in a headless
session - it builds itself automatically the next time you open Maya
normally, since Autoload gets turned on either way.

Prefer to do it by hand, or running the install script wasn't an
option? Same result, from Maya's Script Editor (Python tab):

```python
import a13x.installer as installer
installer.install()
```

Either way, this is a one-time, once-per-machine step. It also opens
`A13x_Quick_Start.pdf` automatically once it's done, located relative
to wherever pip actually installed the package on this machine.
`Windows > Settings/Preferences > Plug-in Manager` shows **A13x**
ticked afterward either way, and the shelf is pinned next to your
other shelves on every subsequent Maya launch - no manual imports, no
editing any files by hand.

Prefer not to open Maya at all, and don't want to run the full install
script again? Run this directly from a terminal any time - it's the
same command the install scripts already call:

```bash
a13x-register-plugin
```

(if that command isn't on PATH, `mayapy -m a13x.headless` does the
same thing). And `a13x-quickstart`, from a terminal, opens the same
PDF the same way without touching Maya at all.

### 3. If Maya can't find `a13x`

If you accidentally ran pip with a different interpreter than the
mayapy that launches Maya, `installer.install()` will still try: it
searches the common pip install locations for Windows, macOS, and
Linux and patches `sys.path` automatically before importing. See
`docs/A13x_Quick_Start.pdf`, Section 2.8, for exactly where it looks.
This is a safety net, not a substitute for installing with the right
mayapy in the first place.

### 4. Force-reinstalling or uninstalling

**Note:** `install/*.bat` and `install/*.sh` are part of this repository,
not the installed `a13x` package itself - they will not be present on
disk after `pip install` alone if you installed from a wheel elsewhere
without keeping a copy of this repo. For anything that must work
regardless of whether you still have this folder around, use the
console commands the package installs automatically instead:

```bash
a13x-uninstall           # unregisters the Maya plug-in stub, uninstalls
                          # the pip package, and sweeps for stray copies
                          # left by a previous mismatched install
a13x-purge                # lists every a13x install found on the machine
a13x-purge --dry-run       # preview what a13x-purge --purge would remove
a13x-purge --purge         # remove every install found, anywhere
```

These are guaranteed to exist after installing `a13x` by any method
described above, on Windows, macOS, or Linux - see
`docs/A13x_Quick_Start.pdf`, Section 2.7, for exactly how and why.

If you do still have this local folder, the install scripts remain a
convenience for a first install (`--force` bypasses pip's cache and
any files left over from a previous install):

```bash
./install/install_a13x_mac_linux.sh --force      # macOS / Linux
install\install_a13x_windows.bat --force         # Windows
```

### 5. Checking consistency

`install/check_a13x.bat` (or `check_a13x.sh`) is a read-only diagnostic,
not an installer - it finds every Maya/Python environment on the
machine and reports, for each: whether a13x is importable and its
version, whether a PySide binding is available, Maya plug-in
registration + Autoload status, and every a13x install found anywhere
on disk (flagging stray duplicates left by past mismatched installs).
Ends with a plain verdict rather than raw output.

## Community and support

For installation help, usage questions, or general discussion about the
A13x workflow, use GitHub Discussions rather than opening an issue.
For bugs and feature requests, use the issue templates in the repository.

- GitHub Discussions: https://github.com/itsakshaydilip/A13x/discussions
- Setup guide: [docs/GITHUB_DISCUSSIONS.md](docs/GITHUB_DISCUSSIONS.md)

## Contributing

Bug reports, feature requests, and DCC-port proposals (Blender, Houdini)
are welcome - see [`CONTRIBUTING.md`](CONTRIBUTING.md) for the workflow
and code conventions before opening a PR.

## Changelog

Version history lives in [`CHANGELOG.md`](CHANGELOG.md).

## How to Cite

If you use A13x in a pipeline, a paper, or another project, please cite
it using the metadata in [`CITATION.cff`](CITATION.cff) - GitHub renders
a ready-to-copy citation from this file via the **"Cite this repository"**
button in the sidebar.

Once a release is archived on Zenodo, this repository also carries a DOI
(see the badge at the top of this file), which resolves to a permanent,
versioned snapshot suitable for formal citation.

## License

Apache License 2.0 - see [`LICENSE`](LICENSE) for full terms.
