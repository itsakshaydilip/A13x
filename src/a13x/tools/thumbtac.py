# thumbtac.py
# =======================================================================
# ThumbTac - Maya Pivot Grid / Thumbtack Tool [MODELING ONLY]
# =======================================================================

from functools import partial
import math
import maya.cmds as cmds

WINDOW_NAME = 'thumbtacWindow'
GRID_GROUP_ATTR = 'pivotGrid_target'
SCRIPTJOB_ATTR = 'pivotGrid_scriptJobId'
LOCATOR_TAG = 'pivotGrid_locator'

# --------------------
# CONFIG
# --------------------
DEFAULT_DIVISIONS = 3
NODE_SCALE_FACTOR = 0.02
MIN_NODE_SIZE = 0.001
CREATE_BUTTON_COLOR = (0.3, 0.5, 0.9)


def _unique_name(base):
    """Return a unique transform name in the scene based on base."""
    name = base
    i = 1
    while cmds.objExists(name):
        name = "%s_%d" % (base, i)
        i += 1
    return name


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
    """Set auto-key state if possible."""
    try:
        cmds.autoKeyframe(state=bool(state))
    except Exception:
        try:
            cmds.autoKeyframe(bool(state))
        except Exception:
            pass


def get_transform(node):
    """Return transform node for shapes."""
    if not node:
        return None
    if cmds.objectType(node) == 'transform':
        return node
    parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
    return parents[0] if parents else node


def create_pivot_grid(target=None, divisions=3, locator_size=None, name_prefix='pivotGrid', auto_apply=True):
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

    if locator_size is None:
        dx, dy, dz = xmax - xmin, ymax - ymin, zmax - zmin
        diag = math.sqrt(dx * dx + dy * dy + dz * dz)
        locator_size = max(diag * NODE_SCALE_FACTOR, MIN_NODE_SIZE)

    prev_ak = _get_autokey_state()
    _set_autokey_state(False)

    base_group = name_prefix + '_grp'
    group_name = _unique_name(base_group)
    group_name = cmds.group(empty=True, name=group_name)

    if not cmds.attributeQuery(GRID_GROUP_ATTR, node=group_name, exists=True):
        cmds.addAttr(group_name, ln=GRID_GROUP_ATTR, dt='string')
    cmds.setAttr('%s.%s' % (group_name, GRID_GROUP_ATTR), target, type='string')

    for child in cmds.listRelatives(group_name, children=True, fullPath=True) or []:
        cmds.delete(child)

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
                cmds.xform(loc, ws=True, t=(x, y, z))
                
                shapes = cmds.listRelatives(loc, shapes=True) or []
                for s in shapes:
                    try:
                        cmds.setAttr(s + '.localScaleX', locator_size)
                        cmds.setAttr(s + '.localScaleY', locator_size)
                        cmds.setAttr(s + '.localScaleZ', locator_size)
                    except Exception:
                        pass
                
                if not cmds.attributeQuery(LOCATOR_TAG, node=loc, exists=True):
                    cmds.addAttr(loc, ln=LOCATOR_TAG, at='bool')
                    cmds.setAttr('%s.%s' % (loc, LOCATOR_TAG), True)
                cmds.parent(loc, group_name)
                locators.append(loc)

    if auto_apply:
        install_selection_job(group_name)

    _set_autokey_state(prev_ak)
    cmds.select(target)
    return group_name


def create_lined_grid(target=None, divisions=3, name_prefix='pivotGrid', auto_apply=True, line_width=1.0, node_size=None):
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

    if node_size is None:
        dx, dy, dz = xmax - xmin, ymax - ymin, zmax - zmin
        diag = math.sqrt(dx * dx + dy * dy + dz * dz)
        node_size = max(diag * NODE_SCALE_FACTOR, MIN_NODE_SIZE)

    prev_ak = _get_autokey_state()
    _set_autokey_state(False)

    base_group = name_prefix + '_lined_grp'
    group_name = _unique_name(base_group)
    group_name = cmds.group(empty=True, name=group_name)

    if not cmds.attributeQuery(GRID_GROUP_ATTR, node=group_name, exists=True):
        cmds.addAttr(group_name, ln=GRID_GROUP_ATTR, dt='string')
    cmds.setAttr('%s.%s' % (group_name, GRID_GROUP_ATTR), target, type='string')

    created = []

    # X Lines
    for y in ys:
        for z in zs:
            crv = cmds.curve(p=[(xs[0], y, z), (xs[-1], y, z)], degree=1, name='%s_line_x' % name_prefix)
            created.append(crv)

    # Y Lines
    for x in xs:
        for z in zs:
            crv = cmds.curve(p=[(x, ys[0], z), (x, ys[-1], z)], degree=1, name='%s_line_y' % name_prefix)
            created.append(crv)

    # Z Lines
    for x in xs:
        for y in ys:
            crv = cmds.curve(p=[(x, y, zs[0]), (x, y, zs[-1])], degree=1, name='%s_line_z' % name_prefix)
            created.append(crv)

    # Intersection Spheres
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            for k, z in enumerate(zs):
                node_name = '%s_node_%d_%d_%d' % (name_prefix, i, j, k)
                sph = cmds.sphere(name=node_name, radius=node_size, axis=(0, 1, 0))[0]
                cmds.xform(sph, ws=True, t=(x, y, z))
                try:
                    if not cmds.attributeQuery(LOCATOR_TAG, node=sph, exists=True):
                        cmds.addAttr(sph, ln=LOCATOR_TAG, at='bool')
                        cmds.setAttr('%s.%s' % (sph, LOCATOR_TAG), True)
                except Exception:
                    pass
                cmds.parent(sph, group_name)

    for obj in created:
        try:
            cmds.parent(obj, group_name)
        except Exception:
            pass

    if auto_apply:
        install_selection_job(group_name)

    _set_autokey_state(prev_ak)
    cmds.select(target)
    return group_name


def install_selection_job(group_name):
    if cmds.objExists(group_name) and cmds.attributeQuery(SCRIPTJOB_ATTR, node=group_name, exists=True):
        try:
            old_job = cmds.getAttr('%s.%s' % (group_name, SCRIPTJOB_ATTR))
            if old_job:
                cmds.scriptJob(kill=int(old_job), force=True)
        except Exception:
            pass

    job_id = cmds.scriptJob(event=['SelectionChanged', partial(on_selection_changed, group_name)], protected=True)
    try:
        if not cmds.attributeQuery(SCRIPTJOB_ATTR, node=group_name, exists=True):
            cmds.addAttr(group_name, ln=SCRIPTJOB_ATTR, at='long')
        cmds.setAttr('%s.%s' % (group_name, SCRIPTJOB_ATTR), job_id)
    except Exception:
        pass


def on_selection_changed(group_name):
    sel = cmds.ls(selection=True, long=True) or []
    if not sel or not cmds.objExists(group_name):
        return

    node = sel[0]
    transform = get_transform(node)
    if not transform or not cmds.attributeQuery(LOCATOR_TAG, node=transform, exists=True):
        return

    try:
        if not cmds.getAttr('%s.%s' % (transform, LOCATOR_TAG)):
            return
    except Exception:
        return

    try:
        target = cmds.getAttr('%s.%s' % (group_name, GRID_GROUP_ATTR))
    except Exception:
        target = None

    pos = cmds.xform(transform, q=True, ws=True, t=True)

    if target and cmds.objExists(target):
        try:
            prev_ak = _get_autokey_state()
            _set_autokey_state(False)
            targ_transform = get_transform(target) or target
            
            cmds.xform(targ_transform, ws=True, piv=pos)
            cmds.select(targ_transform)
            
            try:
                cmds.cutKey(targ_transform, clear=True, attribute=['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz'])
            except Exception:
                pass
            
            delete_pivot_grid(group_name)
            _set_autokey_state(prev_ak)
            cmds.inViewMessage(amg='Pivot updated and grid cleared.', pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning('Failed to set pivot: %s' % e)


def delete_pivot_grid(group_name=None):
    if not group_name:
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.warning('Select the pivot grid group to delete.')
            return
        group_name = sel[0]
        
    if not cmds.objExists(group_name):
        return

    if cmds.attributeQuery(SCRIPTJOB_ATTR, node=group_name, exists=True):
        try:
            job_id = cmds.getAttr('%s.%s' % (group_name, SCRIPTJOB_ATTR))
            if job_id:
                cmds.scriptJob(kill=int(job_id), force=True)
        except Exception:
            pass
            
    try:
        cmds.delete(group_name)
    except Exception as e:
        cmds.warning('Failed to delete group: %s' % e)


# --- UI ---

def show_ui():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    cmds.window(WINDOW_NAME, title='ThumbTac - Pivot Grid Tool', widthHeight=(320, 140))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnOffset=['both', 8])

    cmds.text(label='Select a target mesh, then press Create Grid:', align='left')

    # Controls Row
    cmds.rowLayout(numberOfColumns=3, columnWidth3=[80, 80, 100], adjustableColumn=2)
    cmds.text(label='Divisions:')
    divisions_field = cmds.intField(value=DEFAULT_DIVISIONS, minValue=2)
    lined_checkbox = cmds.checkBox(label='Draw Lines', value=False)
    cmds.setParent('..')

    cmds.separator(height=4, style='single')

    # Action Buttons: Create Grid & Toggle Visibility
    cmds.rowLayout(numberOfColumns=2, columnWidth2=[150, 150], columnAttach2=['both', 'both'], columnOffset2=[2, 2])
    cmds.button(label='Create Grid', command=lambda *a: on_create_grid(divisions_field, lined_checkbox), bgc=CREATE_BUTTON_COLOR, height=30)
    cmds.button(label='Toggle Visibility', command=lambda *a: on_toggle_visibility(), height=30)
    cmds.setParent('..')

    cmds.separator(height=2, style='none')
    cmds.text(label='Click any node to set pivot and automatically clean up.', align='center')

    cmds.showWindow(WINDOW_NAME)


def on_create_grid(divisions_field, lined_checkbox=None):
    div = cmds.intField(divisions_field, q=True, value=True)
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning('Select a target transform or shape first.')
        return
    target = sel[0]

    lined = False
    if lined_checkbox:
        try:
            lined = bool(cmds.checkBox(lined_checkbox, q=True, value=True))
        except Exception:
            lined = False

    if lined:
        group = create_lined_grid(target=target, divisions=div, name_prefix='pivotGrid', auto_apply=True)
    else:
        group = create_pivot_grid(target=target, divisions=div, auto_apply=True)
    cmds.select(group)


def on_toggle_visibility():
    """Smart visibility toggle: works whether grid group, node locator, target, or nothing is selected."""
    sel = cmds.ls(selection=True, long=True) or []
    group = None

    if sel:
        node = sel[0]
        # 1. If grid group is directly selected
        if cmds.attributeQuery(GRID_GROUP_ATTR, node=node, exists=True):
            group = node
        else:
            # 2. Check parents in case a child node/locator is selected
            parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
            while parents:
                p = parents[0]
                if cmds.attributeQuery(GRID_GROUP_ATTR, node=p, exists=True):
                    group = p
                    break
                parents = cmds.listRelatives(p, parent=True, fullPath=True) or []

    # 3. Fallback: Find the most recently created grid group in the scene
    if not group:
        all_groups = [obj for obj in cmds.ls(transforms=True) if cmds.attributeQuery(GRID_GROUP_ATTR, node=obj, exists=True)]
        if all_groups:
            group = all_groups[-1]

    if not group or not cmds.objExists(group):
        cmds.warning('No active Pivot Grid found in the scene or selection.')
        return

    current_vis = cmds.getAttr(group + '.visibility')
    cmds.setAttr(group + '.visibility', not current_vis)


if __name__ == '__main__':
    show_ui()
