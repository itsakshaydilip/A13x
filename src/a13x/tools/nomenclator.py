"""
Asset Renamer for Maya
-----------------------
Select the top-level node(s) of an asset (or several assets) and run this
script. It will walk the full hierarchy underneath your selection and
rename every node according to its role:

    Top-level groups        -> [name]_GRP
    Nested groups           -> [name]_SGRP
    Geometry (mesh)         -> [name]_GEO
    Locators                -> [NAME]_LOC   (locator names are uppercased)

Any existing _GRP / _SGRP / _GEO / _LOC suffix (any case) is stripped
before the new suffix is applied, so you can re-run the tool safely.

Usage:
    1. Select one or more top-level asset groups in the Outliner / viewport.
    2. Run this script (paste into the Script Editor, or source the file,
       then call show_ui()).
    3. Click "Rename Selected Hierarchy".
"""

import maya.cmds as cmds

SUFFIXES = ['_GRP', '_SGRP', '_GEO', '_LOC']


def get_short_name(node):
    """Return just the node's own name, no path or namespace."""
    return node.split('|')[-1].split(':')[-1]


def strip_suffix(name):
    """Remove any known suffix (case-insensitive) from the end of a name."""
    upper = name.upper()
    for suf in SUFFIXES:
        if upper.endswith(suf):
            return name[:-len(suf)]
    return name


def classify(node, is_root):
    """Work out what category a node falls into."""
    shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
    for shape in shapes:
        shape_type = cmds.nodeType(shape)
        if shape_type == 'mesh':
            return 'GEO'
        if shape_type == 'locator':
            return 'LOC'

    # No relevant shape -> it's a group of some kind.
    return 'GRP' if is_root else 'SGRP'


def rename_hierarchy(root):
    """Rename root and everything beneath it, deepest nodes first so that
    long-name lookups stay valid while renaming."""
    descendants = cmds.listRelatives(
        root, allDescendents=True, fullPath=True, type='transform'
    ) or []
    all_nodes = descendants + [root]
    # Deepest (most pipe characters in the path) first.
    all_nodes.sort(key=lambda n: n.count('|'), reverse=True)

    for node in all_nodes:
        if not cmds.objExists(node):
            continue

        is_root = (node == root)
        category = classify(node, is_root)
        base_name = strip_suffix(get_short_name(node))

        if category == 'LOC':
            new_name = base_name.upper() + '_LOC'
        else:
            new_name = base_name + '_' + category

        if get_short_name(node) != new_name:
            cmds.rename(node, new_name)


def run_rename(*_args):
    selection = cmds.ls(selection=True, long=True)
    if not selection:
        cmds.warning('Please select at least one top-level group first.')
        return

    for node in selection:
        rename_hierarchy(node)

    cmds.confirmDialog(
        title='Asset Renamer',
        message='Renaming complete.',
        button=['OK']
    )


def show_ui():
    win_name = 'assetRenamerWin'
    if cmds.window(win_name, exists=True):
        cmds.deleteUI(win_name)

    dark_blue = (0.04, 0.07, 0.22)
    accent_blue = (0.10, 0.30, 0.62)

    win = cmds.window(
        win_name,
        title='Asset Renamer',
        widthHeight=(340, 210),
        backgroundColor=dark_blue,
        sizeable=False
    )

    cmds.columnLayout(
        adjustableColumn=True,
        rowSpacing=8,
        columnAttach=('both', 20),
        backgroundColor=dark_blue
    )

    cmds.text(
        label='Rename Groups / Geo / Locators',
        height=28,
        font='boldLabelFont',
        backgroundColor=dark_blue
    )
    cmds.separator(height=8, style='in')
    cmds.text(
        label=(
            'Naming convention applied to selection:\n\n'
            '  Groups        ->  [name]_GRP\n'
            '  Subgroups     ->  [name]_SGRP\n'
            '  Geometry      ->  [name]_GEO\n'
            '  Locators      ->  [NAME]_LOC'
        ),
        align='left',
        backgroundColor=dark_blue
    )
    cmds.separator(height=8, style='in')
    cmds.button(
        label='Rename Selected Hierarchy',
        height=40,
        backgroundColor=accent_blue,
        command=run_rename
    )

    cmds.showWindow(win)


# NOTE (A13x packaging change): the original script called show_ui()
# unconditionally at import time, which meant simply `import`-ing this
# module popped the UI as a side effect. That's fine for pasting into the
# Script Editor by hand, but breaks a shelf-button/plugin launcher, which
# needs to control *when* the UI appears. Guarded the same way as the
# other five tools instead:
if __name__ == "__main__":
    show_ui()