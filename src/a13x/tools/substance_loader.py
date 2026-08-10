"""
Substance Loader - Drag and Drop Texture Loader for Arnold (Maya)
Automatically assigns correct color spaces based on texture type
"""

import maya.cmds as cmds
import os
import re


import functools

# Global variable to store remembered faces
_REMEMBERED_FACE_SELECTION = []

# Color space configuration for Arnold textures
COLORSPACE_CONFIG = {
    'diffuse': 'sRGB',
    'basecolor': 'sRGB',
    'albedo': 'sRGB',
    'base_color': 'sRGB',
    'roughness': 'Raw',
    'metalness': 'Raw',
    'metallic': 'Raw',
    'normal': 'Raw'
}

# UI slot definitions to avoid duplication
TEXTURE_SLOTS = [
    ('diffuse', 'Diffuse'),
    ('roughness', 'Roughness'),
    ('metalness', 'Metalness'),
    ('normal', 'Normal')
]

UDIM_TOKEN = '<UDIM>'
UDIM_NUMBER_PATTERN = re.compile(r'(?:^|[^0-9])(1[0-9]{3})(?:[^0-9]|$)')


def detect_texture_type(filename):
    """
    Detect texture type from filename
    Returns: texture type string or None
    """
    filename_lower = filename.lower()
    
    # Check for each texture type
    if any(keyword in filename_lower for keyword in ['diffuse', 'basecolor', 'albedo', 'base_color', '_bc', '_diff']):
        return 'diffuse'
    elif any(keyword in filename_lower for keyword in ['roughness', 'rough', '_r']):
        return 'roughness'
    elif any(keyword in filename_lower for keyword in ['metalness', 'metallic', 'metal', '_m']):
        return 'metalness'
    elif any(keyword in filename_lower for keyword in ['normal', 'nrm', '_n']):
        return 'normal'
    
    return None


def create_file_node(texture_path, texture_type):
    """
    Create file node with proper color space settings
    """
    file_node = cmds.shadingNode('file', asTexture=True, isColorManaged=True)
    udim_path, is_udim = get_udim_placeholder_path(texture_path)
    cmds.setAttr(f"{file_node}.fileTextureName", udim_path, type="string")
    if is_udim:
        cmds.setAttr(f"{file_node}.uvTilingMode", 3)
    
    # Set color space
    colorspace = COLORSPACE_CONFIG.get(texture_type, 'Raw')
    cmds.setAttr(f"{file_node}.colorSpace", colorspace, type="string")
    
    # Special handling for roughness and metalness - alpha is luminance
    if texture_type in ['roughness', 'metalness']:
        cmds.setAttr(f"{file_node}.alphaIsLuminance", 1)
    
    return file_node


def get_udim_placeholder_path(texture_path):
    """
    Convert a UDIM-numbered filename to Maya's <UDIM> pattern if applicable
    Returns (path, is_udim)
    """
    if UDIM_TOKEN in texture_path:
        return texture_path, True

    directory, filename = os.path.split(texture_path)
    name, ext = os.path.splitext(filename)

    match = UDIM_NUMBER_PATTERN.search(name)
    if not match:
        return texture_path, False

    udim_number = int(match.group(1))
    if udim_number < 1001:
        return texture_path, False

    new_name = name.replace(match.group(1), UDIM_TOKEN, 1) + ext
    return os.path.join(directory, new_name), True


def create_normal_setup(normal_file_node):
    """
    Create aiNormalMap node and connect the file node to it
    """
    normal_map_node = cmds.shadingNode('aiNormalMap', asUtility=True)
    cmds.connectAttr(f"{normal_file_node}.outColor", f"{normal_map_node}.input")
    
    return normal_map_node


def create_color_balance_node(file_node):
    """
    Create aiColorCorrect node for color balance adjustments
    """
    color_balance = cmds.shadingNode('aiColorCorrect', asUtility=True)
    cmds.connectAttr(f"{file_node}.outColor", f"{color_balance}.input")
    
    return color_balance


def load_texture(texture_path, texture_type):
    """
    Main function to load a texture with proper setup
    texture_type should be: 'diffuse', 'roughness', 'metalness', or 'normal'
    """
    if not os.path.exists(texture_path):
        cmds.warning(f"File does not exist: {texture_path}")
        return None
    
    filename = os.path.basename(texture_path)
    print(f"Loading {texture_type} texture: {filename}")
    
    # Create file node
    file_node = create_file_node(texture_path, texture_type)
    
    result_node = file_node
    
    # Special setup for normal maps
    if texture_type == 'normal':
        result_node = create_normal_setup(file_node)
        print(f"Created aiNormalMap node: {result_node}")
    
    # Special setup for roughness and metalness - add color balance
    elif texture_type in ['roughness', 'metalness']:
        result_node = create_color_balance_node(file_node)
        print(f"Created aiColorCorrect node: {result_node}")
    
    print(f"Successfully loaded {texture_type} texture with color space: {COLORSPACE_CONFIG.get(texture_type)}")
    
    return result_node


def load_textures_batch(texture_paths):
    """
    Load multiple textures at once
    """
    loaded_nodes = {}
    
    for path in texture_paths:
        filename = os.path.basename(path)
        texture_type = detect_texture_type(filename)
        
        if texture_type:
            node = load_texture(path)
            if node:
                loaded_nodes[texture_type] = node
    
    return loaded_nodes


def create_drag_drop_ui():
    """
    Create a simple UI for texture loading with individual slots
    """
    window_name = "substanceLoaderWindow"
    
    # Delete window if it exists
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)
    
    # Create window
    window = cmds.window(window_name, title="Substance Loader", widthHeight=(550, 440))
    
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAttach=('both', 10))
    
    cmds.text(label="Substance Texture Loader", font="boldLabelFont", height=30)
    cmds.separator(height=10, style='in')
    
    # Selection section
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(100, 410),
                   columnAttach=[(1, 'left', 5), (2, 'both', 5)])
    cmds.text(label="Selection:", align='left')
    cmds.textField('selectedObjectField', editable=False, text="None")
    cmds.setParent('..')
    
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(275, 235),
                   columnAttach=[(1, 'both', 5), (2, 'both', 5)])
    cmds.button(label="Select", command=lambda x: select_object(), height=30, backgroundColor=(0.3, 0.5, 0.9))
    cmds.text(label="Apply To:", align='left')
    cmds.setParent('..')
    
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 180),
                   columnAttach=[(1, 'both', 5), (2, 'both', 5)])
    cmds.radioCollection('scopeCollection')
    cmds.radioButton('scopeObject', label='First selected object', select=True)
    cmds.radioButton('scopeFaces', label='Selected faces')
    cmds.setParent('..')
    
    cmds.separator(height=10, style='in')
    
    # Individual texture slots
    cmds.text(label="Texture Slots:", align='left', font='boldLabelFont')
    for tex_type, label in TEXTURE_SLOTS:
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(80, 335, 105),
                       columnAttach=[(1, 'left', 5), (2, 'both', 5), (3, 'both', 5)])
        cmds.text(label=f"{label}:", align='left')
        cmds.textField(f'{tex_type}Field', editable=False, text="")
        cmds.button(label="Browse", command=lambda x, t=tex_type: browse_texture(t), backgroundColor=(0.3, 0.5, 0.9))
        cmds.setParent('..')
    
    cmds.separator(height=15, style='in')
    
    # Action buttons
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(265, 265), 
                   columnAttach=[(1, 'both', 5), (2, 'both', 5)])
    cmds.button(label="Apply Textures", command=lambda x: apply_textures_to_object(), 
                height=40, backgroundColor=(0.3, 0.5, 0.9))
    cmds.button(label="Clear All", command=lambda x: clear_all_fields(), height=40, backgroundColor=(0.3, 0.5, 0.9))
    cmds.setParent('..')
    
    cmds.separator(height=10, style='in')
    cmds.text(label="Color Spaces: Diffuse (sRGB), Roughness/Metalness (Raw+Luminance), Normal (Raw+aiNormalMap)", 
              align='left', font='smallPlainLabelFont')
    
    update_selection_summary()
    cmds.showWindow(window)


def get_scope_selection():
    """
    Read the current scope radio button selection
    """
    selected = cmds.radioCollection('scopeCollection', query=True, select=True)
    if selected == 'scopeFaces':
        return 'faces'
    return 'object'


def get_shapes_from_selection(selection_list):
    """
    Return unique shape nodes from a selection list (handles transforms and components)
    """
    shapes = []
    for sel in selection_list:
        if '.' in sel:
            # Component selection; ls -o gets owning shape
            owners = cmds.ls(sel, objectsOnly=True, long=True) or []
            shapes.extend(owners)
        elif cmds.objectType(sel, isAType='shape'):
            shapes.append(sel)
        else:
            rel = cmds.listRelatives(sel, shapes=True, fullPath=True, noIntermediate=True) or []
            shapes.extend(rel)
    # Preserve order while removing duplicates
    unique_shapes = []
    for sh in shapes:
        if sh not in unique_shapes:
            unique_shapes.append(sh)
    return unique_shapes


def get_selection_data():
    """
    Get selection, shapes, and polygon faces in one place
    """
    selection = cmds.ls(selection=True, long=True, flatten=True) or []
    shapes = get_shapes_from_selection(selection)
    faces = cmds.filterExpand(selection, selectionMask=34) or []  # 34 = polygon faces
    return selection, shapes, faces


def resolve_shape_from_faces(faces, no_faces_message, no_shape_message):
    """
    Resolve a shape from a face selection with consistent warnings
    """
    if not faces:
        cmds.warning(no_faces_message)
        return None
    owners = cmds.ls(faces[0], objectsOnly=True, long=True) or []
    if not owners:
        cmds.warning(no_shape_message)
        return None
    return owners[0]


def update_selection_summary(selection=None, shapes=None, faces=None):
    """
    Update the UI field to show how many objects/components are selected
    """
    if selection is None or shapes is None or faces is None:
        selection, shapes, faces = get_selection_data()
    if not selection:
        summary = "None"
    else:
        summary = f"Objects: {len(shapes)} | Faces: {len(faces)}"
    cmds.textField('selectedObjectField', edit=True, text=summary)


def select_object():
    """
    Refresh selection info and, when not in face scope, prepare a shader
    """
    global _REMEMBERED_FACE_SELECTION
    selection, shapes, faces = get_selection_data()
    update_selection_summary(selection, shapes, faces)

    if not selection:
        cmds.warning("No selection found. Please select objects or faces.")
        _REMEMBERED_FACE_SELECTION = []
        return None

    if not shapes:
        cmds.warning("No mesh or surface shapes found in the selection.")
        _REMEMBERED_FACE_SELECTION = []
        return None

    if get_scope_selection() == 'faces':
        # Remember the current face selection
        _REMEMBERED_FACE_SELECTION = faces.copy() if faces else []
        primary_shape = resolve_shape_from_faces(
            faces,
            "No faces selected for face assignment.",
            "Could not resolve a shape from the selected faces."
        )
        if not primary_shape:
            return None
        shader = get_or_create_shader(primary_shape, assign_to_shape=False, force_new=True)
        if shader:
            shading_group = ensure_shading_group(shader)
            cmds.sets(faces, edit=True, forceElement=shading_group)
            short_name = primary_shape.split('|')[-1]
            print(f"Assigned shader to selected faces on {short_name}")
        return primary_shape

    _REMEMBERED_FACE_SELECTION = []
    primary_shape = shapes[0]
    shader = get_or_create_shader(primary_shape)
    if shader:
        short_name = primary_shape.split('|')[-1]
        print(f"Prepared aiStandardSurface shader for {short_name}")
    return primary_shape


def browse_texture(texture_type):
    """
    Open file browser for specific texture slot
    """
    file_path = cmds.fileDialog2(fileMode=1, caption=f"Select {texture_type.capitalize()} Texture",
                                  fileFilter="Image Files (*.png *.jpg *.jpeg *.tif *.tiff *.exr *.tx *.tga);;All Files (*.*)")
    
    if file_path:
        field_name = f"{texture_type}Field"
        cmds.textField(field_name, edit=True, text=file_path[0])
        print(f"Selected {texture_type} texture: {os.path.basename(file_path[0])}")


def clear_all_fields():
    """
    Clear all texture fields
    """
    for tex_type, _ in TEXTURE_SLOTS:
        cmds.textField(f'{tex_type}Field', edit=True, text="")
    print("Cleared all texture fields")


def apply_textures_to_object():
    """
    Apply all loaded textures to the selected object's shader
    """
    global _REMEMBERED_FACE_SELECTION
    selection, shapes, faces = get_selection_data()
    update_selection_summary(selection, shapes, faces)

    if not selection:
        cmds.warning("Please select objects or components before applying textures.")
        return

    scope = get_scope_selection()

    textures = get_selected_textures()
    if not textures:
        cmds.warning("No textures selected. Please browse and select at least one texture.")
        return

    if scope == 'faces':
        # Use remembered faces if available
        faces_to_use = _REMEMBERED_FACE_SELECTION if _REMEMBERED_FACE_SELECTION else faces
        if not faces_to_use:
            cmds.warning("No faces remembered or selected for face assignment.")
            return
        primary_shape = resolve_shape_from_faces(
            faces_to_use,
            "No faces selected for face assignment.",
            "Could not resolve a shape from the selected components."
        )
        if not primary_shape:
            return
        assign_whole_shape = False
        force_new_shader = True
        shader = get_or_create_shader(primary_shape, assign_to_shape=assign_whole_shape, force_new=force_new_shader)
        if not shader:
            cmds.warning("Failed to get or create shader. Cannot apply textures.")
            return
        shading_group = ensure_shading_group(shader)
        # Load and connect textures
        loaded_nodes = {}
        for texture_type, texture_path in textures.items():
            if os.path.exists(texture_path):
                node = load_texture(texture_path, texture_type)
                if node:
                    loaded_nodes[texture_type] = node
                    connect_texture_to_shader(shader, node, texture_type)
        cmds.sets(faces_to_use, edit=True, forceElement=shading_group)
        assigned_count = len(faces_to_use)
    else:
        if not shapes:
            cmds.warning("No object found in the selection.")
            return
        primary_shape = shapes[0]
        assign_whole_shape = True
        force_new_shader = False
        shader = get_or_create_shader(primary_shape, assign_to_shape=assign_whole_shape, force_new=force_new_shader)
        if not shader:
            cmds.warning("Failed to get or create shader. Cannot apply textures.")
            return
        shading_group = ensure_shading_group(shader)
        loaded_nodes = {}
        for texture_type, texture_path in textures.items():
            if os.path.exists(texture_path):
                node = load_texture(texture_path, texture_type)
                if node:
                    loaded_nodes[texture_type] = node
                    connect_texture_to_shader(shader, node, texture_type)
        cmds.sets(primary_shape, edit=True, forceElement=shading_group)
        assigned_count = 1

    if loaded_nodes:
        message = f"Applied {len(loaded_nodes)} texture(s) to {assigned_count} target(s)."
        cmds.confirmDialog(title='Success', message=message, button=['OK'])
        print(message)


def get_selected_textures():
    """
    Gather non-empty texture paths from UI fields using the shared slot list
    """
    textures = {tex_type: cmds.textField(f'{tex_type}Field', query=True, text=True) for tex_type, _ in TEXTURE_SLOTS}
    return {k: v for k, v in textures.items() if v and v.strip()}


def get_or_create_shader(obj, assign_to_shape=True, force_new=False):
    """
    Get existing shader or create a new aiStandardSurface shader for the object
    assign_to_shape controls whether a newly created shader is applied to the shape.
    force_new forces creation of a new shader and shading group.
    """
    # Get shape node - handle both direct shape selection and transform selection
    shapes = None
    
    # Check if the selected object itself is a shape
    if cmds.objectType(obj, isAType='shape'):
        shapes = [obj]
    else:
        # Try to get shape nodes from transform
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True, noIntermediate=True)
        
        # If still no shapes, try to find mesh in the scene by similar name
        if not shapes:
            obj_short = obj.split('|')[-1]
            # Common pattern: polySphere1 -> pSphere1 or pSphereShape1
            possible_names = [
                obj_short.replace('poly', 'p'),
                obj_short.replace('poly', 'p') + 'Shape',
                obj_short + 'Shape',
                'p' + obj_short[4:] if obj_short.startswith('poly') else obj_short
            ]
            
            for name in possible_names:
                if cmds.objExists(name):
                    test_shapes = cmds.listRelatives(name, shapes=True, fullPath=True, noIntermediate=True)
                    if test_shapes:
                        shapes = test_shapes
                        print(f"Found mesh: {name}")
                        break
    
    if not shapes:
        cmds.warning(f"No shape node found for the selected object: {obj}")
        cmds.warning("Make sure you've selected the mesh transform node (e.g., pSphere1, not polySphere1).")
        cmds.warning("Try selecting the object in the viewport or Outliner.")
        return None
    
    shape = shapes[0]
    
    if not force_new:
        # Get shading engine
        shading_groups = cmds.listConnections(shape, type='shadingEngine')
        
        if shading_groups:
            # Get the shader from existing shading group
            shaders = cmds.listConnections(shading_groups[0] + '.surfaceShader')
            if shaders and cmds.objectType(shaders[0]) == 'aiStandardSurface':
                print(f"Using existing aiStandardSurface shader: {shaders[0]}")
                return shaders[0]
    
    # Create new aiStandardSurface shader
    shader = cmds.shadingNode('aiStandardSurface', asShader=True)
    shading_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=shader + 'SG')
    cmds.connectAttr(shader + '.outColor', shading_group + '.surfaceShader', force=True)
    
    if assign_to_shape:
        cmds.sets(shape, edit=True, forceElement=shading_group)
        print(f"Created and assigned aiStandardSurface shader: {shader}")
    else:
        print(f"Created aiStandardSurface shader (not assigned): {shader}")
    return shader


def ensure_shading_group(shader):
    """
    Make sure a shading group exists for the shader and return it
    """
    shading_groups = cmds.listConnections(shader, type='shadingEngine')
    if shading_groups:
        return shading_groups[0]
    shading_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=shader + 'SG')
    cmds.connectAttr(shader + '.outColor', shading_group + '.surfaceShader', force=True)
    return shading_group


def connect_texture_to_shader(shader, texture_node, texture_type):
    """
    Connect the texture node to the appropriate shader attribute
    """
    if texture_type == 'diffuse':
        cmds.connectAttr(f"{texture_node}.outColor", f"{shader}.baseColor", force=True)
        print(f"Connected diffuse to {shader}.baseColor")
    
    elif texture_type == 'roughness':
        # texture_node is the aiColorCorrect node
        cmds.connectAttr(f"{texture_node}.outColor.outColorR", f"{shader}.specularRoughness", force=True)
        print(f"Connected roughness to {shader}.specularRoughness")
    
    elif texture_type == 'metalness':
        # texture_node is the aiColorCorrect node
        cmds.connectAttr(f"{texture_node}.outColor.outColorR", f"{shader}.metalness", force=True)
        print(f"Connected metalness to {shader}.metalness")
    
    elif texture_type == 'normal':
        # texture_node is the aiNormalMap node
        cmds.connectAttr(f"{texture_node}.outValue", f"{shader}.normalCamera", force=True)
        print(f"Connected normal to {shader}.normalCamera")


# Launch the UI
if __name__ == "__main__":
    create_drag_drop_ui()
