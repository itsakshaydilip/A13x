"""
A13x Maya Plug-in
=================
This is the module Maya's Plug-in Manager actually loads and unloads.
Ticking/unticking the checkbox in Windows > Settings/Preferences >
Plug-in Manager calls initializePlugin()/uninitializePlugin() below.

It does two things on load:
  1. Registers one lightweight Maya command per A13x tool
     (e.g. `cmds.a13xGeoMaster()` launches GeoMaster's UI).
  2. Builds and pins the "A13x" shelf, with one button per command.

Day to day tool changes should happen in tools/<toolname>.py, NOT here -
this file only wires things together and rarely needs editing.
"""

import importlib

import maya.api.OpenMaya as om2
import maya.cmds as cmds

from . import shelf

PLUGIN_VENDOR = "A13x Pipeline"
PLUGIN_VERSION = "3.5.0"

# command name -> (module path, launcher function name inside that module)
TOOL_ENTRY_POINTS = {
    "a13xGeoMaster":       ("a13x.tools.geomaster", "show_ui"),
    "a13xNomenclator":     ("a13x.tools.nomenclator", "show_ui"),
    "a13xThumbTac":        ("a13x.tools.thumbtac", "show_ui"),
    "a13xRevention":       ("a13x.tools.revention", "show_ui"),
    "a13xSubstanceLoader": ("a13x.tools.substance_loader", "create_drag_drop_ui"),
    "a13xUmbra":           ("a13x.tools.umbra", "show_umbra"),
}

_registered_commands = []


def maya_useNewAPI():
    """Marker function - tells Maya this plug-in uses Python API 2.0."""
    pass


def _make_command_class(cmd_name, module_path, func_name):
    """Build a small MPxCommand subclass that lazily imports and launches
    one tool's UI. Lazy import means the tool's module (and any UI it
    builds) is only touched when someone actually clicks the shelf
    button / runs the command - not when the plug-in itself loads."""

    class _ToolCommand(om2.MPxCommand):
        @staticmethod
        def creator():
            return _ToolCommand()

        def doIt(self, args):
            module = importlib.import_module(module_path)
            importlib.reload(module)
            getattr(module, func_name)()

    _ToolCommand.__name__ = str(cmd_name)
    return _ToolCommand


def initializePlugin(mobject):
    plugin_fn = om2.MFnPlugin(mobject, PLUGIN_VENDOR, PLUGIN_VERSION)

    for cmd_name, (module_path, func_name) in TOOL_ENTRY_POINTS.items():
        cmd_class = _make_command_class(cmd_name, module_path, func_name)
        try:
            plugin_fn.registerCommand(cmd_name, cmd_class.creator)
            _registered_commands.append(cmd_name)
        except Exception as exc:
            om2.MGlobal.displayError(
                "A13x: failed to register command '{0}': {1}".format(cmd_name, exc)
            )

    try:
        shelf.build_and_pin_shelf(TOOL_ENTRY_POINTS)
    except Exception as exc:
        om2.MGlobal.displayWarning("A13x: could not build the A13x shelf: {0}".format(exc))

    om2.MGlobal.displayInfo("A13x pipeline tools loaded (v{0}).".format(PLUGIN_VERSION))


def uninitializePlugin(mobject):
    plugin_fn = om2.MFnPlugin(mobject)

    for cmd_name in list(_registered_commands):
        try:
            plugin_fn.deregisterCommand(cmd_name)
        except Exception as exc:
            om2.MGlobal.displayWarning(
                "A13x: failed to deregister command '{0}': {1}".format(cmd_name, exc)
            )
        _registered_commands.remove(cmd_name)

    try:
        shelf.remove_shelf()
    except Exception as exc:
        om2.MGlobal.displayWarning("A13x: could not remove the A13x shelf: {0}".format(exc))

    om2.MGlobal.displayInfo("A13x pipeline tools unloaded.")
