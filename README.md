# A13x

A13x is a production pipeline built to simplify workflows and solve issues that arise from university software versions, missing scripts/tools, and the resulting slow production speeds, extra support requests, or submission delays. The pipeline also supports reverse compatibility, eliminates unwanted nodes, and reduces load times in Autodesk Maya.

## Table of Contents

- [Software](#software)
- [Dependencies and Plugins](#dependencies-and-plugins)
- [Production](#production)
- [Quality Checks](#quality-checks)
- [Texture Quality and Presets (Substance)](#texture-quality-and-presets-substance)
- [Finalization](#finalization)

## Software

| Software | Version | Notes |
|---|---|---|
| Maya | `2023` | |
| ZBrush | latest release | |
| Character Creator | `CC-5` | |
| Unreal Engine | `5.5.4` | MetaHuman plugin not supported at this version (university build) |

## Dependencies and Plugins

- `Python 3.10` or Anaconda (latest release)

## Production

All assets start as regular concepts and go through the standard sculpting and re-topology phase, followed by quality checks and file finalization. Assets are rendered in both **Arnold** and **Unreal**, using the same studio setup with matching (or closely matched) lighting.

## Quality Checks

Quality checks ensure perfectly versioned, organized files with optimized geometry and pivots, alongside sanity checks that confirm files are properly optimized for rigging.

A key goal here is that these scripts and tools are reusable across other productions — making the pipeline compatible across multiple industries, whether game, animation, or AR/VR.

This kind of knowledge comes from experience — from working through production issues with coordinators and leads around client tools and formats. Giving teams a shared framework to build on solves these problems, and collaborating over GitHub (or Git bridges) closes gaps before they can even become issues.

**Checklist:**

- [x] Maya mesh check
- [x] Rigging check *(outdated/irrelevant for CC5 or MetaHuman)*
- [x] Revention — Maya autosave utility with auto-versioning *(disk space usage is manageable if used wisely)*
- [x] Pivot tool — sets pivot manually via grid-based input
- [x] Model/scene checker and cleaner
- [x] Substance file loader — loads files with correct color spaces

**GitHub Repo:** [itsakshaydilip](https://github.com/itsakshaydilip)

## Texture Quality and Presets (Substance)

Textures are set up using a Substance preset that allows consistent rendering in both **Arnold** and **Unreal**. These presets are included with the pipeline's `.zip` package.

## Finalization

Finalization includes folder organization and accompanying notes.
