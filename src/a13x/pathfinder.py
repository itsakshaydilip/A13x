"""
Locates the a13x package on disk when it isn't already on sys.path.

Why this exists: `pip install a13x` only puts the package where THAT
particular Python interpreter's site-packages lives. If someone runs
pip with a different interpreter than the one that later needs to
import it - a different mayapy, a system Python, a python.org
per-user install, Homebrew, conda, pyenv - `import a13x` fails for
the second interpreter even though the package is genuinely installed
somewhere on the machine.

This module searches EVERY common pip install location across
Windows, macOS, and Linux - not just Maya's own layouts - and either
patches sys.path so the import succeeds (ensure_importable), or
reports every single place it looked, found, or removed a copy
(find_all_installs / purge_all), so a "not found" result is never a
mystery.

This module is intentionally dependency-free (stdlib only, no `maya`
import) so the generated plug-in stub (a13x_plugin.py, written by
a13x.installer.install() into Maya's plug-ins folder) can copy this
logic inline and run it before a13x itself is importable, and so the
standalone install/purge_a13x.py script can run it with any Python -
no Maya, and no working a13x import, required.
"""

import glob
import os
import shutil
import sys


def _candidate_site_packages_dirs():
    """Yield every plausible site-packages directory to check. Doesn't
    require any package to already be importable, and intentionally
    over-searches rather than risk missing a real install location."""
    home = os.path.expanduser("~")
    seen = set()

    def _emit(*parts):
        for path in glob.glob(os.path.join(*parts)):
            path = os.path.normpath(path)
            if path not in seen:
                seen.add(path)
                yield path

    if sys.platform.startswith("win"):
        program_files = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                          os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
        localappdata = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        appdata = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))

        # Maya's own bundled Python (mayapy)
        for pf in program_files:
            for path in _emit(pf, "Autodesk", "Maya*", "Python", "Lib", "site-packages"):
                yield path
            for path in _emit(pf, "Autodesk", "Maya*", "Python3", "Lib", "site-packages"):
                yield path

        # python.org's current per-user installer (Python 3.13+, e.g.
        # pythoncore-3.14-64) - this is the layout that was missing
        # before, and is the DEFAULT for a plain "Install Python" from
        # python.org on a modern Windows machine.
        for path in _emit(localappdata, "Python", "pythoncore-3*-64", "Lib", "site-packages"):
            yield path
        for path in _emit(localappdata, "Python", "pythoncore-3*-32", "Lib", "site-packages"):
            yield path
        for path in _emit(localappdata, "Python", "pythoncore-3*-arm64", "Lib", "site-packages"):
            yield path

        # python.org's older per-user installer layout
        for path in _emit(localappdata, "Programs", "Python", "Python3*", "Lib", "site-packages"):
            yield path
        for path in _emit(appdata, "Python", "Python3*", "site-packages"):
            yield path

        # All-users / system-wide installs
        for pf in program_files:
            for path in _emit(pf, "Python3*", "Lib", "site-packages"):
                yield path
        for path in _emit("C:\\", "Python3*", "Lib", "site-packages"):
            yield path

        # Windows Store Python
        for path in _emit(localappdata, "Packages", "PythonSoftwareFoundation.Python.3*",
                           "LocalCache", "local-packages", "Python3*", "site-packages"):
            yield path

    elif sys.platform == "darwin":
        # Maya's own bundled Python (mayapy)
        for path in _emit("/Applications/Autodesk/maya*/Maya.app/Contents/Frameworks/"
                           "Python.framework/Versions/*/lib/python3*/site-packages"):
            yield path

        # python.org installer - per-user site
        for path in _emit(home, "Library", "Python", "3*", "lib", "python", "site-packages"):
            yield path
        # python.org installer - all-users framework install
        for path in _emit("/Library/Frameworks/Python.framework/Versions/3*/lib/python3*/site-packages"):
            yield path

        # Homebrew (Apple Silicon and Intel)
        for path in _emit("/opt/homebrew/lib/python3*/site-packages"):
            yield path
        for path in _emit("/usr/local/lib/python3*/site-packages"):
            yield path

        # pyenv
        for path in _emit(home, ".pyenv", "versions", "*", "lib", "python3*", "site-packages"):
            yield path

        # conda / miniconda / miniforge (base env and named envs)
        for conda_root in ("anaconda3", "miniconda3", "miniforge3"):
            for path in _emit(home, conda_root, "lib", "python3*", "site-packages"):
                yield path
            for path in _emit(home, conda_root, "envs", "*", "lib", "python3*", "site-packages"):
                yield path

    else:  # linux and other unix-likes
        # Maya's own bundled Python (mayapy)
        for path in _emit("/usr/autodesk/maya*/lib/python3*/site-packages"):
            yield path

        # pip --user installs
        for path in _emit(home, ".local", "lib", "python3*", "site-packages"):
            yield path

        # System package manager Pythons
        for path in _emit("/usr/lib/python3*/site-packages"):
            yield path
        for path in _emit("/usr/lib/python3/dist-packages"):  # Debian/Ubuntu
            yield path
        for path in _emit("/usr/local/lib/python3*/site-packages"):
            yield path

        # pyenv
        for path in _emit(home, ".pyenv", "versions", "*", "lib", "python3*", "site-packages"):
            yield path

        # conda / miniconda / miniforge
        for conda_root in ("anaconda3", "miniconda3", "miniforge3"):
            for path in _emit(home, conda_root, "lib", "python3*", "site-packages"):
                yield path
            for path in _emit(home, conda_root, "envs", "*", "lib", "python3*", "site-packages"):
                yield path

    # Cross-platform: any local virtualenv the user pip-installed into directly
    for path in _emit(home, ".virtualenvs", "*", "lib", "python3*", "site-packages"):
        yield path
    for path in _emit(home, ".venv", "lib", "python3*", "site-packages"):
        yield path


def find_all_installs(package_name="a13x"):
    """Return a list of every site-packages directory that actually
    contains `package_name`, searching ALL candidate locations rather
    than stopping at the first hit. Useful for spotting duplicate /
    stale installs left behind by pip-installing with more than one
    interpreter over time."""
    found = []
    for site_dir in _candidate_site_packages_dirs():
        if os.path.isdir(os.path.join(site_dir, package_name)):
            found.append(site_dir)
    return found


def dist_info_dirs(site_dir, package_name="a13x"):
    """Return any *.dist-info / *.egg-info directories for
    `package_name` inside `site_dir` (there should be exactly one per
    install, but stale ones from old versions can linger)."""
    pattern_a = os.path.join(site_dir, "{0}-*.dist-info".format(package_name))
    pattern_b = os.path.join(site_dir, "{0}-*.egg-info".format(package_name))
    return sorted(glob.glob(pattern_a) + glob.glob(pattern_b))


def purge_all(package_name="a13x", dry_run=False, verbose=True):
    """Manually remove `package_name` (its module folder, dist-info /
    egg-info, and console-script entry points) from every location it
    is found in, across every interpreter's site-packages. This is a
    filesystem-level fallback for when `pip uninstall` can't be run
    with the right interpreter - it does not require pip, or a13x
    itself, to be importable. Returns the list of site-packages
    directories that were (or, in dry_run mode, would be) cleaned."""
    cleaned = []
    for site_dir in find_all_installs(package_name):
        pkg_dir = os.path.join(site_dir, package_name)
        targets = [pkg_dir] + dist_info_dirs(site_dir, package_name)

        # Console scripts (a13x-quickstart[.exe]) live in ../Scripts or
        # ../bin relative to site-packages, not inside site-packages
        # itself - try both common layouts.
        for scripts_subdir in ("Scripts", "bin"):
            scripts_dir = os.path.normpath(os.path.join(site_dir, "..", "..", scripts_subdir))
            for name in ("a13x-quickstart", "a13x-quickstart.exe"):
                candidate = os.path.join(scripts_dir, name)
                if os.path.exists(candidate):
                    targets.append(candidate)

        if verbose:
            print("A13x: found install in {0}".format(site_dir))
            for t in targets:
                if os.path.exists(t):
                    print("    {0} {1}".format("[would remove]" if dry_run else "[removing]", t))

        if not dry_run:
            for t in targets:
                try:
                    if os.path.isdir(t):
                        shutil.rmtree(t)
                    elif os.path.exists(t):
                        os.remove(t)
                except OSError as exc:
                    print("A13x: couldn't remove {0}: {1}".format(t, exc))

        cleaned.append(site_dir)

    if verbose and not cleaned:
        print("A13x: no '{0}' install found in any searched location.".format(package_name))

    return cleaned


def ensure_importable(package_name="a13x", verbose=True):
    """Make sure `package_name` can be imported, searching common pip
    install locations across Windows/macOS/Linux if it isn't already
    on sys.path. Returns True if the package is importable afterward."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        pass

    for site_dir in _candidate_site_packages_dirs():
        if not os.path.isdir(os.path.join(site_dir, package_name)):
            continue
        if site_dir not in sys.path:
            sys.path.insert(0, site_dir)
        try:
            __import__(package_name)
            if verbose:
                print("A13x: found '{0}' in {1}, added to sys.path.".format(package_name, site_dir))
            return True
        except ImportError:
            continue

    if verbose:
        print("A13x: could not locate '{0}' in any known install location on this "
              "machine (see a13x.pathfinder for the full search list, or run "
              "install/purge_a13x.py --dry-run to see everywhere that was checked). "
              "Run 'mayapy -m pip install {0}' using the SAME mayapy that launches "
              "this copy of Maya.".format(package_name))
    return False


def cli_main():
    """Entry point for the `a13x-purge` console command."""
    import argparse
    parser = argparse.ArgumentParser(description="Locate (and optionally remove) a13x installs.")
    parser.add_argument("--purge", action="store_true", help="Remove every install found.")
    parser.add_argument("--dry-run", action="store_true", help="Report what --purge would remove, without removing it.")
    args = parser.parse_args()

    if args.purge or args.dry_run:
        purge_all(dry_run=args.dry_run)
    else:
        installs = find_all_installs()
        if installs:
            print("Found a13x in:")
            for i in installs:
                print("  {0}".format(i))
        else:
            print("No a13x install found in any searched location.")


if __name__ == "__main__":
    cli_main()
