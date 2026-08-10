"""
A13x shelf builder.

Builds (or rebuilds) a shelf tab named "A13x" with one button per tool
command, then pins it into Maya's shelf preferences the same way the
Shelf Editor's "Save All Shelves" does - so it survives a Maya restart
without the plug-in needing to run again first.
"""

import os

import maya.cmds as cmds
import maya.mel as mel

SHELF_NAME = "A13x"

_THUMBNAILS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thumbnails")

# command name -> (button label, tooltip, icon filename)
_BUTTON_INFO = {
    "a13xGeoMaster": ("GeoMaster", "GeoMaster - geometry / UV / shader sanity checker", "geomaster_thumbnail.png"),
    "a13xNomenclator": ("Nomenclator", "Nomenclator - hierarchy renamer (GRP / SGRP / GEO / LOC)", "nomenclator_thumbnail.png"),
    "a13xThumbTac": ("ThumbTac", "ThumbTac - interactive pivot grid tool", "thumbtac_thumbnail.png"),
    "a13xRevention": ("Revention", "Revention - versioned autosave utility", "revention_thumbnail.png"),
    "a13xSubstanceLoader": ("SubstanceLdr", "Substance Loader - Arnold PBR texture loader", "substance_loader_thumbnail.png"),
    "a13xUmbra": ("Umbra", "Umbra - scene cleaner & character model checker", "umbra_thumbnail.png"),
}

# Used only if a tool's PNG icon is somehow missing from thumbnails/ -
# every tool listed above ships with a real icon, so this should not
# normally be hit.
_FALLBACK_ICON = "commandButton.png"


def _icon_path(cmd_name):
    _, _, icon_filename = _BUTTON_INFO.get(cmd_name, (cmd_name, cmd_name, None))
    if icon_filename:
        full_path = os.path.join(_THUMBNAILS_DIR, icon_filename)
        if os.path.isfile(full_path):
            return full_path
    return _FALLBACK_ICON


def _shelf_top_level():
    return mel.eval("global string $gShelfTopLevel; $temp = $gShelfTopLevel;")


def build_and_pin_shelf(tool_entry_points):
    """Create the A13x shelf tab and populate it with one button per
    command in tool_entry_points, then pin/save it."""
    top_shelf = _shelf_top_level()
    if not top_shelf or not cmds.tabLayout(top_shelf, exists=True):
        cmds.warning("A13x: Maya shelf UI is not available (e.g. batch mode) - skipping shelf build.")
        return

    existing_tabs = cmds.tabLayout(top_shelf, query=True, childArray=True) or []
    if SHELF_NAME in existing_tabs:
        cmds.deleteUI(SHELF_NAME)

    cmds.setParent(top_shelf)
    cmds.shelfLayout(SHELF_NAME)

    for cmd_name in tool_entry_points:
        label, tooltip, _ = _BUTTON_INFO.get(cmd_name, (cmd_name, cmd_name, None))
        cmds.shelfButton(
            parent=SHELF_NAME,
            label=label,
            annotation=tooltip,
            image1=_icon_path(cmd_name),
            style="iconAndTextVertical",
            sourceType="python",
            command="import maya.cmds as cmds; cmds.{0}()".format(cmd_name),
        )

    cmds.tabLayout(top_shelf, edit=True, selectTab=SHELF_NAME)
    _pin_shelf()


def _pin_shelf():
    """Persist the shelf to disk so it survives a Maya restart - identical
    mechanism to clicking "Save All Shelves" in the Shelf Editor."""
    try:
        cmds.saveAllShelves(_shelf_top_level())
    except Exception:
        mel.eval("saveAllShelves $gShelfTopLevel;")


def remove_shelf():
    """Deletes the A13x shelf tab entirely. Called automatically from
    plugin.uninitializePlugin() when the plug-in is unloaded/disabled in
    Plug-in Manager, so unticking "Loaded" removes the shelf as well as
    the commands - can also be run manually from the Script Editor."""
    top_shelf = _shelf_top_level()
    if top_shelf and cmds.tabLayout(top_shelf, exists=True):
        tabs = cmds.tabLayout(top_shelf, query=True, childArray=True) or []
        if SHELF_NAME in tabs:
            cmds.deleteUI(SHELF_NAME)
            _pin_shelf()
