# Contributing to A13x

Thanks for considering a contribution. A13x is a small, single-maintainer
project, so please read this before opening a PR — it keeps review fast for
both of us.

## Before you start

- **Bug fixes and small improvements** — open an issue first using the
  Bug Report template, or go straight to a PR if the fix is small and obvious.
- **New tools or significant features** — open a Feature Request issue first
  so we can agree on scope before you put in the work.
- **New DCC ports** (Blender/Houdini, see the open transferability issues) —
  these are welcome as separate, clearly-scoped PRs; please keep them in
  their own module rather than mixing Maya-specific and DCC-agnostic code.

## Code conventions

- Each tool remains a **single, self-contained Python file** under
  `src/a13x/tools/`, exposing a `show_ui()` (or equivalent) entry point.
  Tools must not open a window as a side effect of import — only when
  their entry point is called.
- Follow the existing naming convention used throughout the codebase
  (see `nomenclator.py` for the canonical suffix rules: `_GRP`, `_SGRP`,
  `_GEO`, `_LOC`).
- Qt code should follow the existing PySide6-first, PySide2-fallback
  import pattern (see `umbra.py` for reference) so tools keep working
  across Maya 2022–2025+.
- Keep `logger.py` as the single shared logging utility; avoid introducing
  a second logging mechanism.

## Submitting a change

1. Fork the repo and create a branch off `main`:
   `git checkout -b fix/short-description` or `feature/short-description`.
2. Keep commits focused — one logical change per commit where practical.
3. Update `CHANGELOG.md` under an `[Unreleased]` heading.
4. Open a PR describing what changed and why, and link the issue it closes
   (e.g. `Closes #4`).

## Questions and support

Use GitHub Discussions for general questions, installation help, workflow
questions, or ideas that are not specific bugs or feature requests.
The repository includes a discussion template and setup notes in
[docs/GITHUB_DISCUSSIONS.md](docs/GITHUB_DISCUSSIONS.md).

## Reporting bugs

Use the Bug Report issue template. Please include the Maya version,
OS, and Qt binding in use — most reported issues so far have come down to
one of those three variables.

## Code of conduct

Be respectful and constructive. This is a small open-source project run
in spare time — patience and clear reproduction steps go a long way.
