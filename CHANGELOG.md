# Changelog

All notable changes to A13x are documented in this file.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/).

## [3.5.0] — 2026-08-10

### Added
- Public GitHub release with Zenodo-archivable structure (`CITATION.cff`, tagged release).
- `CONTRIBUTING.md` and issue templates for external contributors.

### Changed
- Cross-version Qt handling standardised across all UI tools: PySide6 attempted
  first, falling back to PySide2 automatically (fixes tools that previously
  only supported PySide2 and would fail on Maya 2025+).
- Distribution renamed and decoupled from the internal `a13x` import path;
  `a13x-uninstall` / `a13x-purge` updated to locate the correct `dist-info`
  folder after the rename.

### Fixed
- `mayapy` path resolution across mixed Maya-version installs via the
  OS-specific installer scripts (`install_a13x_windows.bat`,
  `install_a13x_mac_linux.sh`).

---

## Earlier development history

Prior to 3.5.0, the project was developed and iterated on privately during
production use (MetaHuman → Unreal pipeline, then generalised to custom
character grooming). See the accompanying technical report for the full
development narrative.

<!--
Template for future entries:

## [X.Y.Z] — YYYY-MM-DD
### Added
### Changed
### Fixed
### Removed
-->
