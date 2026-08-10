from maya import cmds, mel
import maya.OpenMayaUI as omui

# PySide6 (Maya 2025+) first, then PySide2 (Maya 2022 and earlier) - same
# auto-detect pattern GeoMaster uses, so Umbra keeps working across Maya
# versions instead of hard-failing when only one binding is installed.
try:
    from PySide6 import QtWidgets, QtCore
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtWidgets, QtCore
    from shiboken2 import wrapInstance

def get_maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)

# ============================================================================
# CUSTOM BUTTON SUBCLASS
# ============================================================================
# This is a "smart button" that knows how to set itself up automatically.
# By creating a subclass of QPushButton, we inherit all button functionality
# and add our own custom behavior on top of it.
# ============================================================================

class UmbraButton(QtWidgets.QPushButton):
    """
    A custom button that automatically:
    1. Styles itself with blue background
    2. Adds itself to a grid layout at the specified position
    3. Connects its click signal to the provided function
    
    This eliminates the need to repeat these steps for every button.
    """
    
    def __init__(self, text, layout, row, col, click_fn, colspan=1, parent=None):
        """
        Args:
            text (str): The text to display on the button
            layout (QGridLayout): The grid layout to add this button to
            row (int): Which row in the grid (0 = first row)
            col (int): Which column in the grid (0 = first column)
            click_fn (function): The function to call when button is clicked
            colspan (int): How many columns the button should span (default: 1)
            parent (QWidget): The parent widget (optional)
        """
        # Call the parent class (QPushButton) constructor first
        # This gives us all the standard button functionality
        super(UmbraButton, self).__init__(text, parent=parent)
        
        # Define the blue styling for all our buttons
        blue_style = "background-color: #4d80e6; color: white; font-weight: bold; border: 1px solid #3366cc;"
        
        # Store the function that should be called when clicked
        # We store it as an attribute so we can access it later
        self.click_function = click_fn
        
        # Apply the blue style to THIS button (self refers to this button instance)
        self.setStyleSheet(blue_style)
        
        # Add this button to the grid layout at the specified position
        # columnSpan parameter makes the button stretch across multiple columns
        layout.addWidget(self, row, col, 1, colspan)
        
        # Connect the button's clicked signal to our function
        # When the button is clicked, it will automatically call click_fn
        self.clicked.connect(self.click_function)

# ============================================================================
# MAIN DIALOG CLASS
# ============================================================================

class Umbra(QtWidgets.QDialog):
    def __init__(self, parent=get_maya_main_window()):
        super(Umbra, self).__init__(parent)
        self.setWindowTitle("Umbra")
        self.setMinimumSize(450, 800)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
        # Set dark color scheme for the dialog
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        
        # ====================================================================
        # BUTTON LISTS
        # ====================================================================
        # These lists will store references to our buttons.
        # This allows us to loop through all buttons in the "Run All" functions
        # instead of hard-coding each function call.
        # ====================================================================
        self._cleanup_buttons = []  # Stores Model Scene Cleaner buttons
        self._check_buttons = []    # Stores Character Model Check buttons
        
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # --- Model Scene Cleaner Section ---
        cleaner_label = QtWidgets.QLabel("<b>Model Scene Cleaner</b>")
        layout.addWidget(cleaner_label)

        # ====================================================================
        # MODEL SCENE CLEANER BUTTONS (Using our custom UmbraButton class)
        # ====================================================================
        # Notice how each button creation is now just ONE line instead of THREE:
        # - No need to manually add to layout
        # - No need to manually set style
        # - No need to manually connect signal
        # The UmbraButton class handles all of that automatically!
        # ====================================================================
        
        button_layout = QtWidgets.QGridLayout()
        
        # Each button is created with: (text, layout, row, col, function_to_call)
        # append() adds the button to our list so we can loop through it later
        self._cleanup_buttons.append(
            UmbraButton("Delete Unwanted Nodes", button_layout, 0, 0, 
                         self.delete_unwanted_nodes, parent=self)
        )
        self._cleanup_buttons.append(
            UmbraButton("Delete Empty Groups", button_layout, 0, 1, 
                         self.delete_empty_groups, parent=self)
        )
        self._cleanup_buttons.append(
            UmbraButton("Center Pivot", button_layout, 1, 0, 
                         self.center_pivot, parent=self)
        )
        self._cleanup_buttons.append(
            UmbraButton("Bounding Box + Frame", button_layout, 1, 1, 
                         self.set_viewport_bounding_box, parent=self)
        )
        self._cleanup_buttons.append(
            UmbraButton("Delete Unused Nodes", button_layout, 2, 0, 
                         self.delete_unused_nodes, parent=self)
        )
        self._cleanup_buttons.append(
            UmbraButton("Group Visible as 'GEO'", button_layout, 2, 1, 
                         self.group_geo, parent=self)
        )
        
        layout.addLayout(button_layout)
        
        # The "Run All" button spans 2 columns (colspan=2)
        # We DON'T add it to the list to avoid infinite recursion!
        # (If we did, clicking "Run All" would call itself forever)
        UmbraButton("Run All Cleanup", button_layout, 3, 0, 
                     self.run_all, colspan=2, parent=self)

        # ====================================================================
        # CHARACTER MODEL CHECKS SECTION
        # ====================================================================
        # Same pattern as above - each button is one line!
        # Compare this to the old code that required:
        # - 1 line to create
        # - 1 line to add to layout  
        # - 1 line to set style
        # - 1 line to connect signal
        # That's 4 lines reduced to 1 line per button!
        # ====================================================================
        
        char_label = QtWidgets.QLabel("<b>Character Model Checks</b>")
        layout.addWidget(char_label)

        char_button_layout = QtWidgets.QGridLayout()
        
        # Create all check buttons and add them to the _check_buttons list
        self._check_buttons.append(
            UmbraButton("Check Color Sets", char_button_layout, 0, 0, 
                         self.check_colorsets, parent=self)
        )
        self._check_buttons.append(
            UmbraButton("Check UV Sets", char_button_layout, 0, 1, 
                         self.check_uvsets, parent=self)
        )
        self._check_buttons.append(
            UmbraButton("Check Max Influences", char_button_layout, 1, 0, 
                         self.check_max_influences, parent=self)
        )
        self._check_buttons.append(
            UmbraButton("Check Unnecessary History", char_button_layout, 1, 1, 
                         self.check_history, parent=self)
        )
        self._check_buttons.append(
            UmbraButton("Check Transformed Mesh (and Pivot)", char_button_layout, 2, 0, 
                         self.check_transform, parent=self)
        )
        self._check_buttons.append(
            UmbraButton("Check Rotated Joints", char_button_layout, 2, 1, 
                         self.check_rot_joints, parent=self)
        )
        self._check_buttons.append(
            UmbraButton("Check Scaled Joints", char_button_layout, 3, 0, 
                         self.check_scale_joints, parent=self)
        )
        self._check_buttons.append(
            UmbraButton("Check Same Name GEO", char_button_layout, 3, 1, 
                         self.check_same_name, parent=self)
        )
        
        layout.addLayout(char_button_layout)
        
        # "Run All" button spans 2 columns and is NOT added to the list
        UmbraButton("Run All Character Model Checks", char_button_layout, 4, 0, 
                     self.run_all_char_checks, colspan=2, parent=self)

        # ====================================================================
        # LOG OUTPUT
        # ====================================================================
        self.log_output = QtWidgets.QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555;")
        layout.addWidget(self.log_output)
        
        # ====================================================================
        # NOTICE: No more signal connections or styling needed!
        # ====================================================================
        # All those connections and styling are now handled automatically
        # by the UmbraButton class. This eliminates 33+ lines of code!
        # ====================================================================
        # OLD WAY (what was removed):
        #   - 17 lines of .clicked.connect() calls
        #   - 17 lines of .setStyleSheet() calls  
        #   - 17 lines of .addWidget() calls
        # NEW WAY:
        #   - All handled in UmbraButton.__init__()
        # ====================================================================

    def log(self, message, color=None):
        if color:
            self.log_output.append(f'<span style="color: {color};">{message}</span>')
        else:
            self.log_output.append(message)
        print(message)

    def delete_unwanted_nodes(self):
        nodes = cmds.ls(type=["unknown", "unknownDag", "unknownTransform"])
        if nodes:
            cmds.delete(nodes)
            self.log(f"Deleted {len(nodes)} unwanted nodes.", color='lime')
        else:
            self.log("No unwanted nodes found.", color='lime')

    def delete_empty_groups(self):
        groups = [grp for grp in cmds.ls(type="transform") if not cmds.listRelatives(grp)]
        if groups:
            cmds.delete(groups)
            self.log(f"Deleted {len(groups)} empty groups.", color='lime')
        else:
            self.log("No empty groups found.", color='lime')

    def center_pivot(self):
        all_objects = cmds.ls(dag=True, long=True)
        for obj in all_objects:
            try:
                cmds.select(obj, r=True)
                mel.eval("CenterPivot;")
            except Exception:
                pass
        self.log("Centered pivot on all objects.", color='lime')

    def set_viewport_bounding_box(self):
        try:
            panels = cmds.getPanel(type="modelPanel")
            for panel in panels:
                cmds.modelEditor(panel, edit=True, displayAppearance="boundingBox")
            mel.eval("FrameAll;")
            self.log("Set all viewports to Bounding Box shading mode and framed viewport.", color='lime')
        except Exception as e:
            self.log(f"Viewport update failed: {e}", color='red')

    def delete_unused_nodes(self):
        try:
            mel.eval('hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes");')
            self.log("Deleted unused shader nodes.", color='lime')
        except Exception as e:
            self.log(f"Failed to delete unused nodes: {e}", color='red')

    def group_geo(self):
        objs = cmds.ls(visible=True, long=True)
        if objs:
            ungrouped_objs = [obj for obj in objs if not cmds.listRelatives(obj, parent=True)]
            if ungrouped_objs:
                cmds.group(ungrouped_objs, name="GEO")
                self.log(f"Grouped {len(ungrouped_objs)} visible, ungrouped objects into 'GEO'.", color='lime')
            else:
                self.log("No ungrouped objects to group.", color='lime')
        else:
            self.log("No visible objects to group.", color='lime')

    def run_all(self):
        """
        Runs all cleanup functions by looping through the _cleanup_buttons list.
        
        OLD WAY: Hard-code each function call
            self.delete_unwanted_nodes()
            self.delete_empty_groups()
            ... etc ...
        
        NEW WAY: Loop through buttons and call their stored functions
            for button in self._cleanup_buttons:
                button.click_function()
        
        BENEFITS:
        - Adding a new button automatically adds it to "Run All"
        - No need to update this function when adding/removing buttons
        - Less code, fewer places to make mistakes
        """
        self.log("Running all cleanup actions...")
        
        # Loop through each cleanup button and call its associated function
        for button in self._cleanup_buttons:
            # Remember: we stored the function in the button's click_function attribute
            button.click_function()
        
        self.log("Umbra cleanup finished.")

    # --- Character Model Checks Functions ---
    def check_colorsets(self):
        correct_colorset_count = 1  # Default, can be made user-configurable
        meshes = cmds.ls(type='mesh', long=True)
        error_meshes = []
        for mesh in meshes:
            if not cmds.getAttr(mesh + '.intermediateObject'):
                color_sets = cmds.polyColorSet(mesh, q=True, acs=True)
                if color_sets is not None:
                    if len(color_sets) != correct_colorset_count:
                        error_meshes.append(mesh)
                elif correct_colorset_count != 0:
                    error_meshes.append(mesh)
        if error_meshes:
            cmds.select(error_meshes, r=True)
            self.log(f"Meshes with incorrect color set count: {error_meshes}", color='red')
        else:
            self.log("All meshes have the correct number of color sets.", color='lime')

    def check_uvsets(self):
        correct_uvset_count = 1  # Default, can be made user-configurable
        meshes = cmds.ls(type='mesh', long=True)
        error_meshes = []
        for mesh in meshes:
            if not cmds.getAttr(mesh + '.intermediateObject'):
                uv_sets = cmds.polyUVSet(mesh, q=True, auv=True)
                if uv_sets is not None:
                    if len(uv_sets) != correct_uvset_count:
                        error_meshes.append(mesh)
                elif correct_uvset_count != 0:
                    error_meshes.append(mesh)
        if error_meshes:
            cmds.select(error_meshes, r=True)
            self.log(f"Meshes with incorrect UV set count: {error_meshes}", color='red')
        else:
            self.log("All meshes have the correct number of UV sets.", color='lime')

    def check_max_influences(self):
        max_influences = 4  # Default, can be made user-configurable
        meshes = cmds.ls(type='mesh', long=True)
        error_verts = []
        for mesh in meshes:
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)
            if not transform:
                continue
            transform = transform[0]
            vtx_list = cmds.ls(f'{transform}.vtx[*]', fl=True)
            sc = None
            for history in cmds.listHistory(transform):
                if cmds.objectType(history) == 'skinCluster':
                    sc = history
                    break
            if sc is not None:
                for vtx in vtx_list:
                    skin_values = cmds.skinPercent(sc, vtx, q=True, v=True)
                    non_zero_values = [v for v in skin_values if v != 0]
                    if len(non_zero_values) > max_influences:
                        error_verts.append(vtx)
        if error_verts:
            cmds.select(error_verts, r=True)
            self.log(f"Vertices with more than {max_influences} influences: {error_verts}", color='red')
        else:
            self.log("No vertices exceed the max influences.", color='lime')

    def check_history(self):
        meshes = cmds.ls(type='mesh', long=True)
        error_meshes = []
        for mesh in meshes:
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)
            if not transform:
                continue
            transform = transform[0]
            his_list = cmds.listHistory(transform, pdo=True)
            bad_his = []
            if his_list is not None:
                for his in his_list:
                    node_type = cmds.nodeType(his)
                    if node_type in ['skinCluster', 'tweak', 'groupParts', 'groupId', 'shadingEngine']:
                        continue
                    elif node_type == 'blendShape':
                        continue  # Optionally allow blendShape
                    else:
                        bad_his.append(his)
                if len(bad_his) >= 1:
                    error_meshes.append(transform)
        if error_meshes:
            cmds.select(error_meshes, r=True)
            self.log(f"Meshes with unnecessary history: {error_meshes}", color='red')
        else:
            self.log("No unnecessary history found.", color='lime')

    def check_transform(self):
        decimal_places = 3  # Default, can be made user-configurable
        meshes = cmds.ls(type='mesh', long=True)
        error_meshes = []
        for mesh in meshes:
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)
            if not transform:
                continue
            transform = transform[0]
            attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz',
                     'rotatePivotX', 'rotatePivotY', 'rotatePivotZ',
                     'scalePivotX', 'scalePivotY', 'scalePivotZ']
            values = [cmds.getAttr(f'{transform}.{attr}') for attr in attrs]
            # Check translation/rotation != 0, scale != 1, pivots != 0
            if (round(values[0], decimal_places) != 0 or
                round(values[1], decimal_places) != 0 or
                round(values[2], decimal_places) != 0 or
                round(values[3], decimal_places) != 0 or
                round(values[4], decimal_places) != 0 or
                round(values[5], decimal_places) != 0 or
                round(values[6], decimal_places) != 1 or
                round(values[7], decimal_places) != 1 or
                round(values[8], decimal_places) != 1 or
                round(values[9], decimal_places) != 0 or
                round(values[10], decimal_places) != 0 or
                round(values[11], decimal_places) != 0 or
                round(values[12], decimal_places) != 0 or
                round(values[13], decimal_places) != 0 or
                round(values[14], decimal_places) != 0):
                error_meshes.append(transform)
        if error_meshes:
            cmds.select(error_meshes, r=True)
            self.log(f"Meshes with non-identity transform or pivot: {error_meshes}", color='red')
        else:
            self.log("All meshes have identity transform and pivot.", color='lime')

    def check_rot_joints(self):
        decimal_places = 3  # Default, can be made user-configurable
        joints = cmds.ls(type='joint', long=True)
        error_joints = []
        for joint in joints:
            rx = cmds.getAttr(f'{joint}.rx')
            ry = cmds.getAttr(f'{joint}.ry')
            rz = cmds.getAttr(f'{joint}.rz')
            if (round(rx, decimal_places) != 0 or
                round(ry, decimal_places) != 0 or
                round(rz, decimal_places) != 0):
                error_joints.append(joint)
        if error_joints:
            cmds.select(error_joints, r=True)
            self.log(f"Joints with non-zero rotation: {error_joints}", color='red')
        else:
            self.log("All joints have zero rotation.", color='lime')

    def check_scale_joints(self):
        decimal_places = 3  # Default, can be made user-configurable
        joints = cmds.ls(type='joint', long=True)
        error_joints = []
        for joint in joints:
            sx = cmds.getAttr(f'{joint}.sx')
            sy = cmds.getAttr(f'{joint}.sy')
            sz = cmds.getAttr(f'{joint}.sz')
            if (round(sx, decimal_places) != 1 or
                round(sy, decimal_places) != 1 or
                round(sz, decimal_places) != 1):
                error_joints.append(joint)
        if error_joints:
            cmds.select(error_joints, r=True)
            self.log(f"Joints with non-identity scale: {error_joints}", color='red')
        else:
            self.log("All joints have identity scale.", color='lime')

    def check_same_name(self):
        transforms = cmds.ls(type='transform')
        error_nodes = []
        for node in transforms:
            if '|' in node:
                error_nodes.append(node)
        if error_nodes:
            cmds.select(error_nodes, r=True)
            self.log(f"Nodes with duplicate names: {error_nodes}", color='red')
        else:
            self.log("No duplicate node names found.", color='lime')

    def run_all_char_checks(self):
        """
        Runs all character model checks by looping through the _check_buttons list.
        
        Same principle as run_all() above - we loop through the buttons
        instead of hard-coding each function call.
        """
        # Loop through each check button and call its associated function
        for button in self._check_buttons:
            button.click_function()
        
        self.log("All character model checks complete.")

def show_umbra():
    for widget in QtWidgets.QApplication.allWidgets():
        if isinstance(widget, Umbra):
            widget.close()
    win = Umbra()
    win.show()

# NOTE (A13x packaging change): originally show_umbra() was called
# unconditionally at import time here, same issue as nomenclator.py -
# importing the module would pop the UI. Guarded so the shelf
# button/plugin command controls when it launches:
if __name__ == "__main__":
    show_umbra()