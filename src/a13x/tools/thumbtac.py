# thumbtac.py
# =======================================================================
# ThumbTac - Maya Pivot Grid / Thumbtack Tool [MODELING ONLY]
# =======================================================================
# Place this file in your Maya scripts folder or open it in Maya's Script Editor and execute.

# NOTE (quick edit):
# - To change defaults (divisions, node size factor, button color), edit the CONFIG block in this file.
# - Window name is `WINDOW_NAME` (used for UI deletion) near the top.
# - To change naming prefixes, edit the `name_prefix` arguments passed to create functions.

from functools import partial
import math
import maya.cmds as cmds

# Script name: ThumbTac
# To customize behavior, edit the CONFIG section below.
WINDOW_NAME = 'thumbtacWindow'
GRID_GROUP_ATTR = 'pivotGrid_target'
SCRIPTJOB_ATTR = 'pivotGrid_scriptJobId'
LOCATOR_TAG = 'pivotGrid_locator'


def _unique_name(base):
    """Return a unique transform name in the scene based on base."""
    name = base
    i = 1
    while cmds.objExists(name):
        name = "%s_%d" % (base, i)
        i += 1
    return name


# --------------------
# CONFIG (edit these)
# --------------------
# Default number of divisions for the grid (per axis). 3 => 3x3x3
DEFAULT_DIVISIONS = 3
# Fraction of bounding-box diagonal used for locator/node size
NODE_SCALE_FACTOR = 0.02
# Minimum node size in scene units
MIN_NODE_SIZE = 0.001
# Create button color (RGB tuple 0..1)
CREATE_BUTTON_COLOR = (0.3, 0.5, 0.9)


def _get_autokey_state():
    """Return current auto-key state (True/False). Works across Maya versions."""
    try:
        return bool(cmds.autoKeyframe(q=True, state=True))
    except Exception:
        try:
            return bool(cmds.autoKeyframe(q=True))
        except Exception:
            return False


def _set_autokey_state(state):
    """Set auto-key state if possible. Swallows errors on unsupported versions."""
    try:
        cmds.autoKeyframe(state=bool(state))
    except Exception:
        try:
            cmds.autoKeyframe(bool(state))
        except Exception:
            pass


def get_transform(node):
    # return transform node for shapes
    if not node:
        return None
    if cmds.objectType(node) == 'transform':
        return node
    parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
    return parents[0] if parents else node


def create_pivot_grid(target=None, divisions=3, locator_size=None, name_prefix='pivotGrid', auto_apply=True):
    """Create a grid of locators over the target object's bounding box.
    - target: transform or shape name. If None, uses current selection (first item).
    - divisions: number of points per axis (3 for 3x3x3)
    Returns the group name containing locators.
    """
    if not target:
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.error('Select a mesh or transform to place the grid on.')
        target = sel[0]

    target = get_transform(target)
    if not target or not cmds.objExists(target):
        cmds.error('Target not found: %s' % target)

    bbox = cmds.exactWorldBoundingBox(target)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox

    # compute a sensible default locator size relative to the object's size
    if locator_size is None:
        dx = xmax - xmin
        dy = ymax - ymin
        dz = zmax - zmin
        diag = math.sqrt(dx * dx + dy * dy + dz * dz)
        locator_size = max(diag * NODE_SCALE_FACTOR, MIN_NODE_SIZE)

    # disable auto-key while creating objects and moving them to avoid creating animation keys
    prev_ak = _get_autokey_state()
    _set_autokey_state(False)

    # create group to hold locators (use unique name if needed)
    base_group = name_prefix + '_grp'
    group_name = _unique_name(base_group)
    group_name = cmds.group(empty=True, name=group_name)
    # store target name on the group
    if not cmds.attributeQuery(GRID_GROUP_ATTR, node=group_name, exists=True):
        cmds.addAttr(group_name, ln=GRID_GROUP_ATTR, dt='string')
    cmds.setAttr('%s.%s' % (group_name, GRID_GROUP_ATTR), target, type='string')

    # remove old locators under group if any
    for child in cmds.listRelatives(group_name, children=True, fullPath=True) or []:
        cmds.delete(child)

    # compute grid positions
    if divisions < 2:
        divisions = 2
    xs = [xmin + (x / float(divisions - 1)) * (xmax - xmin) for x in range(divisions)]
    ys = [ymin + (y / float(divisions - 1)) * (ymax - ymin) for y in range(divisions)]
    zs = [zmin + (z / float(divisions - 1)) * (zmax - zmin) for z in range(divisions)]

    locators = []
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            for k, z in enumerate(zs):
                loc_name = '%s_%d_%d_%d_loc' % (name_prefix, i, j, k)
                loc = cmds.spaceLocator(name=loc_name)[0]
                # move locator to position
                cmds.xform(loc, ws=True, t=(x, y, z))
                # small scale via local scale on shape
                shapes = cmds.listRelatives(loc, shapes=True) or []
                for s in shapes:
                    try:
                        cmds.setAttr(s + '.localScaleX', locator_size)
                        cmds.setAttr(s + '.localScaleY', locator_size)
                        cmds.setAttr(s + '.localScaleZ', locator_size)
                    except Exception:
                        pass
                # tag locator with an attribute so we can identify it
                if not cmds.attributeQuery(LOCATOR_TAG, node=loc, exists=True):
                    cmds.addAttr(loc, ln=LOCATOR_TAG, at='bool')
                    cmds.setAttr('%s.%s' % (loc, LOCATOR_TAG), True)
                cmds.parent(loc, group_name)
                locators.append(loc)

    # create (or update) scriptJob that listens to selection changes only if auto_apply requested
    if auto_apply:
        install_selection_job(group_name)

    # restore autokey state
    _set_autokey_state(prev_ak)
    cmds.select(target)
    return group_name


def install_selection_job(group_name):
    # remove existing job if present on this group
    if cmds.objExists(group_name) and cmds.attributeQuery(SCRIPTJOB_ATTR, node=group_name, exists=True):
        try:
            old_job = cmds.getAttr('%s.%s' % (group_name, SCRIPTJOB_ATTR))
            if old_job:
                try:
                    cmds.scriptJob(kill=int(old_job), force=True)
                except Exception:
                    pass
        except Exception:
            pass

    # create new scriptJob
    job_id = cmds.scriptJob(event=['SelectionChanged', partial(on_selection_changed, group_name)], protected=True)
    # store job id as attribute on group
    try:
        if not cmds.attributeQuery(SCRIPTJOB_ATTR, node=group_name, exists=True):
            cmds.addAttr(group_name, ln=SCRIPTJOB_ATTR, at='long')
        cmds.setAttr('%s.%s' % (group_name, SCRIPTJOB_ATTR), job_id)
    except Exception:
        # attribute creation might fail in some Maya versions; ignore if so
        pass


def on_selection_changed(group_name):
    """Called when selection changes. If a pivotGrid locator is selected, set the pivot of the target object to that locator's world position."""
    sel = cmds.ls(selection=True, long=True) or []
    if not sel:
        return
    # take first selected
    node = sel[0]
    # ensure node exists and belongs to our group
    if not cmds.objExists(group_name):
        return

    # check if this node or its transform has our locator tag
    transform = get_transform(node)
    if not transform:
        return
    # check tag attribute
    if not cmds.attributeQuery(LOCATOR_TAG, node=transform, exists=True):
        return
    try:
        is_tagged = cmds.getAttr('%s.%s' % (transform, LOCATOR_TAG))
    except Exception:
        is_tagged = False
    if not is_tagged:
        return

    # read target name from group
    try:
        target = cmds.getAttr('%s.%s' % (group_name, GRID_GROUP_ATTR))
    except Exception:
        target = None
    if not target or not cmds.objExists(target):
        # try to find a transform under the group with attribute pointing to target
        # fallback: use currently selected second item (if user clicked locator while also selecting target)
        pass

    # get locator world position
    pos = cmds.xform(transform, q=True, ws=True, t=True)

    # set pivot of the target
    if target and cmds.objExists(target):
        try:
            # disable autokey while setting pivot
            prev_ak = _get_autokey_state()
            _set_autokey_state(False)
            # ensure we're operating on the transform
            targ_transform = get_transform(target)
            if not targ_transform:
                targ_transform = target
            cmds.xform(targ_transform, ws=True, piv=pos)
            # select the target to give user feedback
            cmds.select(targ_transform)
            # delete any keyframes that may have been created on the target
            try:
                cmds.cutKey(targ_transform, clear=True, attribute=['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz'])
            except Exception:
                pass
            # after applying pivot, remove the grid and associated scriptJob/data
            try:
                delete_pivot_grid(group_name)
            except Exception:
                pass
            # restore autokey
            _set_autokey_state(prev_ak)
        except Exception as e:
            cmds.warning('Failed to set pivot: %s' % e)


def set_pivot_from_selection(group_name=None, delete_after=True):
    """Set pivot from the current selection. If a locator from a pivot grid is selected,
    this will set the target's pivot to that locator position. If delete_after is True,
    the pivot grid group will be deleted afterwards (including its scriptJob).
    Returns True if pivot was set, False otherwise."""
    sel = cmds.ls(selection=True, long=True) or []
    if not sel:
        cmds.warning('Select a locator from the pivot grid first.')
        return False
    node = sel[0]

    transform = get_transform(node)
    if not transform:
        return False

    # ensure this is one of our locators
    if not cmds.attributeQuery(LOCATOR_TAG, node=transform, exists=True):
        cmds.warning('Selected object is not a pivot grid locator.')
        return False

    try:
        is_tagged = cmds.getAttr('%s.%s' % (transform, LOCATOR_TAG))
    except Exception:
        is_tagged = False
    if not is_tagged:
        cmds.warning('Selected object is not a pivot grid locator.')
        return False

    # find group name (parent)
    parent = cmds.listRelatives(transform, parent=True, fullPath=True) or []
    grp = parent[0] if parent else group_name
    if not grp:
        cmds.warning('Pivot grid group not found.')
        return False

    # read target name from group
    try:
        target = cmds.getAttr('%s.%s' % (grp, GRID_GROUP_ATTR))
    except Exception:
        target = None

    pos = cmds.xform(transform, q=True, ws=True, t=True)

    if target and cmds.objExists(target):
        try:
            # disable autokey while setting pivot
            prev_ak = _get_autokey_state()
            _set_autokey_state(False)
            targ_transform = get_transform(target)
            if not targ_transform:
                targ_transform = target
            cmds.xform(targ_transform, ws=True, piv=pos)
            cmds.select(targ_transform)
            # delete any keyframes that may have been created on the target
            try:
                cmds.cutKey(targ_transform, clear=True, attribute=['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz'])
            except Exception:
                pass
            if delete_after:
                try:
                    delete_pivot_grid(grp)
                except Exception:
                    pass
            # restore autokey
            _set_autokey_state(prev_ak)
            return True
        except Exception as e:
            cmds.warning('Failed to set pivot: %s' % e)
            return False
    else:
        cmds.warning('Target object missing or deleted.')
        return False


def create_lined_grid(target=None, divisions=3, name_prefix='pivotGrid', auto_apply=True, visual_nodes=True, line_width=1.0, node_size=None):
    """Create a lined grid using nurbs curves for lines and small spheres for nodes.
    - target: transform or shape name. If None, uses current selection.
    - divisions: samples per axis
    - visual_nodes: if True, nodes will be templated (visual-only / non-selectable)
    Returns the created group name.
    """
    if not target:
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.error('Select a mesh or transform to place the grid on.')
        target = sel[0]

    target = get_transform(target)
    if not target or not cmds.objExists(target):
        cmds.error('Target not found: %s' % target)

    bbox = cmds.exactWorldBoundingBox(target)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox

    if divisions < 2:
        divisions = 2
    xs = [xmin + (x / float(divisions - 1)) * (xmax - xmin) for x in range(divisions)]
    ys = [ymin + (y / float(divisions - 1)) * (ymax - ymin) for y in range(divisions)]
    zs = [zmin + (z / float(divisions - 1)) * (zmax - zmin) for z in range(divisions)]

    # compute default node size from bbox if not provided
    if node_size is None:
        dx = xmax - xmin
        dy = ymax - ymin
        dz = zmax - zmin
        diag = math.sqrt(dx * dx + dy * dy + dz * dz)
        node_size = max(diag * NODE_SCALE_FACTOR, MIN_NODE_SIZE)

    # disable autokey during creation
    prev_ak = _get_autokey_state()
    _set_autokey_state(False)

    # create unique group
    base_group = name_prefix + '_lined_grp'
    group_name = _unique_name(base_group)
    group_name = cmds.group(empty=True, name=group_name)
    # store target
    if not cmds.attributeQuery(GRID_GROUP_ATTR, node=group_name, exists=True):
        cmds.addAttr(group_name, ln=GRID_GROUP_ATTR, dt='string')
    cmds.setAttr('%s.%s' % (group_name, GRID_GROUP_ATTR), target, type='string')

    created = []

    # create lines along X for each Y,Z
    for y in ys:
        for z in zs:
            p0 = (xs[0], y, z)
            p1 = (xs[-1], y, z)
            name = '%s_line_x_%.3f_%.3f' % (name_prefix, y, z)
            crv = cmds.curve(p=[p0, p1], degree=1, name=name)
            # set line thickness where supported via displayScale on shape (viewport may ignore)
            created.append(crv)

    # lines along Y
    for x in xs:
        for z in zs:
            p0 = (x, ys[0], z)
            p1 = (x, ys[-1], z)
            name = '%s_line_y_%.3f_%.3f' % (name_prefix, x, z)
            crv = cmds.curve(p=[p0, p1], degree=1, name=name)
            created.append(crv)

    # lines along Z
    for x in xs:
        for y in ys:
            p0 = (x, y, zs[0])
            p1 = (x, y, zs[-1])
            name = '%s_line_z_%.3f_%.3f' % (name_prefix, x, y)
            crv = cmds.curve(p=[p0, p1], degree=1, name=name)
            created.append(crv)

    # create small sphere nodes at intersections
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            for k, z in enumerate(zs):
                node_name = '%s_node_%d_%d_%d' % (name_prefix, i, j, k)
                sph = cmds.sphere(name=node_name, radius=node_size, axis=(0,1,0))[0]
                # move to position
                cmds.xform(sph, ws=True, t=(x, y, z))
                # tag with locator tag for compatibility
                # tag the transform as a pivot-grid node (so selection handlers detect it)
                try:
                    if not cmds.attributeQuery(LOCATOR_TAG, node=sph, exists=True):
                        cmds.addAttr(sph, ln=LOCATOR_TAG, at='bool')
                        cmds.setAttr('%s.%s' % (sph, LOCATOR_TAG), True)
                except Exception:
                    pass
                # also tag the shape(s) where possible for compatibility
                shapes = cmds.listRelatives(sph, shapes=True) or []
                for s in shapes:
                    try:
                        if not cmds.attributeQuery(LOCATOR_TAG, node=s, exists=True):
                            cmds.addAttr(s, ln=LOCATOR_TAG, at='bool')
                            cmds.setAttr('%s.%s' % (s, LOCATOR_TAG), True)
                    except Exception:
                        pass
                # nodes are selectable by default (no templating)
                cmds.parent(sph, group_name)
                created.append(sph)

    # parent curves under group
    for obj in created:
        try:
            cmds.parent(obj, group_name)
        except Exception:
            pass

    # install selection job only if auto_apply
    if auto_apply:
        install_selection_job(group_name)

    # restore autokey state
    _set_autokey_state(prev_ak)
    cmds.select(target)
    return group_name


def delete_pivot_grid(group_name=None):
    """Delete the pivot grid group and kill the scriptJob if present."""
    if not group_name:
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.warning('Select the pivot grid group to delete or provide its name.')
            return
        group_name = sel[0]
    if not cmds.objExists(group_name):
        cmds.warning('Group does not exist: %s' % group_name)
        return

    # kill scriptJob if stored
    if cmds.attributeQuery(SCRIPTJOB_ATTR, node=group_name, exists=True):
        try:
            job_id = cmds.getAttr('%s.%s' % (group_name, SCRIPTJOB_ATTR))
            if job_id:
                cmds.scriptJob(kill=int(job_id), force=True)
        except Exception:
            pass
    # delete the group
    try:
        cmds.delete(group_name)
    except Exception as e:
        cmds.warning('Failed to delete group: %s' % e)


# --- UI ---

def show_ui():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)
    # make UI a bit larger to accommodate buttons
    cmds.window(WINDOW_NAME, title='ThumbTac - Pivot Grid Tool', widthHeight=(460, 160))
    form = cmds.columnLayout(adjustableColumn=True)

    cmds.text(label='Select a target mesh/transform then press Create Grid')
    cmds.separator(height=6)

    # Top row: divisions
    row = cmds.rowLayout(numberOfColumns=3, columnAlign3=['left','left','left'], columnWidth3=[80,80,80], adjustableColumn=2)
    cmds.text(label='Divisions:')
    divisions_field = cmds.intField(value=DEFAULT_DIVISIONS, minValue=2)
    cmds.text(label='')
    cmds.setParent('..')

    # Second row: options
    opts = cmds.rowLayout(numberOfColumns=1, columnAlign2=['left','left'], columnWidth2=[320,160])
    lined_checkbox = cmds.checkBox(label='Draw Lines', value=False)
    cmds.setParent('..')

    cmds.separator(height=6)
    cmds.rowLayout(numberOfColumns=4, columnWidth4=[120,100,120,80])
    create_btn = cmds.button(label='Create Grid', command=lambda *a: on_create_grid(divisions_field, lined_checkbox), bgc=CREATE_BUTTON_COLOR)
    set_btn = cmds.button(label='Set Pivot', command=lambda *a: on_set_pivot())
    vis_btn = cmds.button(label='Toggle Visibility', command=lambda *a: on_toggle_visibility())
    del_btn = cmds.button(label='Delete Grid', command=lambda *a: on_delete_grid())
    cmds.setParent('..')

    cmds.separator(height=6)
    cmds.text(label='Usage: Click any grid node/locator to set the pivot of the target object.')

    cmds.showWindow(WINDOW_NAME)


def on_create_grid(divisions_field, lined_checkbox=None):
    div = cmds.intField(divisions_field, q=True, value=True)
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning('Select a target transform or shape first.')
        return
    target = sel[0]
    # auto-apply is always enabled (click will set pivot and remove the grid)
    auto_apply = True
    # check if user wants lined grid
    lined = False
    if lined_checkbox:
        try:
            lined = bool(cmds.checkBox(lined_checkbox, q=True, value=True))
        except Exception:
            lined = False

    if lined:
        group = create_lined_grid(target=target, divisions=div, name_prefix='pivotGrid', auto_apply=auto_apply)
    else:
        group = create_pivot_grid(target=target, divisions=div, auto_apply=auto_apply)
    cmds.select(group)


def on_set_pivot():
    # attempt to set pivot from selection and delete grid afterwards
    ok = set_pivot_from_selection()
    if ok:
        cmds.inViewMessage(amg='Pivot set and grid removed.', pos='midCenter', fade=True)


def on_toggle_visibility():
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning('Select the pivot grid group to toggle.')
        return
    group = sel[0]
    if not cmds.objExists(group):
        cmds.warning('Group does not exist: %s' % group)
        return
    children = cmds.listRelatives(group, children=True, fullPath=True) or []
    if not children:
        cmds.warning('No locators under: %s' % group)
        return
    # check first child's visibility
    vis = cmds.getAttr(children[0] + '.visibility')
    for c in children:
        try:
            cmds.setAttr(c + '.visibility', not vis)
        except Exception:
            pass


def on_delete_grid():
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning('Select the pivot grid group to delete.')
        return
    group = sel[0]
    delete_pivot_grid(group)


# allow running as script
if __name__ == '__main__':
    show_ui()