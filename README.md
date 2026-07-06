# A13x

A13x is a pipeline created to simplify production and solve issues along the way that can happen as part of the universities software versions and lack of scripts or tools that may lead to slow production speeds, the student requesting for more help or even delay in submission due to unforeseen events. The pipeline also supports reverse compatibility as well as eliminates unwanted nodes and even slower load up times for Auto-desk Maya.


# Software's

This version of the pipeline is built on older versions of Maya (2023) and Z-brush as well as CC-5. We will be using unreal 5.5.4 that is being used at the University that does not support the metahuman pugin.

# Dependencies and plugins.

 - Python - 3.10 or Anaconda (latest release)


# Production 

All assets start as regular concepts and go through the usual sculpting and re-topo phase as well as quality checks and file finalization. Assets are rendered in both Arnold and unreal in the exact same studio setup with matching lighting if not the closest.


# Quality Checks

Quality checks pave the way for perfectly versioned and organized files with optimized geo, pivot as well as sanity checks that prevent files are optimized for rigging. The part we'd like to focus here is the fact that the pipelines scripts and tools can be used in other productions. Making this compatible across multiole industries be it game, animation or AR/VR. 

Knowledge comes through experience and having to fight with production co-ordinators and leads to solve issues with client tools and formats are a pain. Giving them a framework to develop over is a great way to solve issues and collaboration over github or git bridges gaps and solves issues even before they can ever exist.

Quality check include :

- maya mesh check.
- rigging check - (outdated or irrelevant when it comes to CC5 or metahuman).
- Revention - Maya autosave utility with auto versioning. (honestly disk space isnt much of an issue should you use it wisely).
- A pivot tool that manualy selts the pivot based on your input via a grid.
- model scene check and cleaner
- substance file loader - (makes it easy to lead file with proper color spaces)

Github Repo - [Link](https://github.com/itsakshaydilip)

# Texture quality and preset (substance)

The textures will be set up using a substance preset that allows rendering in both Arnold as well as Unreal.

These presets will be included with the zip.

# Finalization

Finalization includes folder organization and notes.


