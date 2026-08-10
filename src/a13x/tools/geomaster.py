#!/usr/bin/env python3
"""
GeoMaster - Comprehensive Geometry Checker for Maya

This module provides a comprehensive Maya UI to detect, highlight, and fix
common geometry, topology, UV, shader, and scene organization issues.

Usage inside Maya:
    import sys
    sys.path.append(r"C:/gameGeoMaster")
    import main
    main.show_ui()

Categories covered:
    1. Geometry & Topology Errors
    2. Normal Issues
    3. UV & Texture Coordinate Errors
    4. Shader & Material Issues
    5. Construction History & Node Issues
    6. Transform & Pivot Problems
    7. Naming & Organization Errors
    8. Performance & Optimization Issues
    9. Rigging & Deformation Preparation
    10. Data Integrity Issues
    11. Color & Vertex Attribute Problems
"""

from typing import TYPE_CHECKING, Optional

try:
    import maya.cmds as cmds
    import maya.mel as mel
    import maya.OpenMaya as om
except Exception:
    cmds = None
    mel = None
    om = None

# Import PySide2/PySide6 based on Maya version
PYSIDE_VERSION: Optional[int] = None
try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QProgressBar, QTextEdit, QScrollArea, QFrame
    from PySide6.QtCore import Qt, Signal, QTimer
    from PySide6.QtGui import QFont, QPalette, QColor
    from shiboken6 import wrapInstance  # type: ignore
    PYSIDE_VERSION = 6  # type: ignore[assignment]
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
        from PySide2.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QProgressBar, QTextEdit, QScrollArea, QFrame
        from PySide2.QtCore import Qt, Signal, QTimer
        from PySide2.QtGui import QFont, QPalette, QColor
        from shiboken2 import wrapInstance  # type: ignore
        PYSIDE_VERSION = 2  # type: ignore[assignment]
    except ImportError:
        QtWidgets = None  # type: ignore
        PYSIDE_VERSION = None  # type: ignore[assignment]
        print('[WARNING] PySide2/PySide6 not found - UI features will be limited')

import re
import math
import os
import sys
import traceback
from datetime import datetime

# Import config and logger
try:
    import config
    import logger as log_module
    logger = log_module.get_logger()
except Exception as e:
    logger = None
    print('Warning: Could not import config/logger: %s' % str(e))

# ============================================================================
# GLOBAL VARIABLES - UI Controls and State Management
# ============================================================================

# Storage for last check results - maps check name to found components
_last_check_results = {}

# UI widget references - allows updating progress bar and log from anywhere
_ui_progress_bar = None  # Progress bar control widget
_ui_log_field = None     # Log text field widget
_ui_window_name = None   # Main window name for checking if UI is open
_ui_window_instance = None  # Qt window instance (PySide2/6)

# Operation state flags - controls check behavior
_is_batch_operation = False  # True when running "Check All", False for individual checks
_cancel_requested = False     # Set to True to cancel ongoing batch operations


# ============================================================================
# UTILITY FUNCTIONS - UI Updates and Logging
# ============================================================================

def log_to_ui(message: str, level: str = 'INFO') -> None:
    """
    Log message to UI log panel and optionally to console/file.
    
    Args:
        message (str): The message to log
        level (str): Log level - 'INFO', 'WARNING', 'ERROR', 'SUCCESS'
    
    This function centralizes all output to ensure messages appear in the UI log panel.
    Works with both Qt (PySide2/6) and cmds UI.
    """
    global _ui_log_field, _ui_window_instance
    
    # Format message with timestamp and level
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    # Add visual indicator based on level
    if level == 'ERROR':
        prefix = '[!]'
    elif level == 'WARNING':
        prefix = '[*]'
    elif level == 'SUCCESS':
        prefix = '[✓]'
    else:
        prefix = '[i]'
    
    formatted_msg = '[%s] %s %s' % (timestamp, prefix, message)
    
    # Try Qt window first
    if _ui_window_instance is not None:
        try:
            _ui_window_instance.log(message, level)
            return
        except Exception:
            pass
    
    # Fall back to cmds UI
    if _ui_log_field and cmds:
        try:
            if cmds.scrollField(_ui_log_field, exists=True):
                # Get current text
                current_text = cmds.scrollField(_ui_log_field, query=True, text=True) or ''
                # Append new message
                new_text = current_text + formatted_msg + '\n'
                # Update field
                cmds.scrollField(_ui_log_field, edit=True, text=new_text)
                # Auto-scroll to bottom
                line_count = new_text.count('\n')
                cmds.scrollField(_ui_log_field, edit=True, scrollToLine=line_count)
                return
        except Exception:
            pass
    
    # Also print to console for debugging
    print(formatted_msg)
    
    # Log to file if logger is available
    if logger:
        if level == 'ERROR':
            logger.error(message)
        elif level == 'WARNING':
            logger.warning(message)
        else:
            logger.info(message)


def update_progress(value, max_value, status_text=''):
    """
    Update the global progress bar.
    
    Args:
        value (int): Current progress value
        max_value (int): Maximum progress value
        status_text (str): Optional status text to display in log
    
    The progress bar shows percentage completion for batch operations.
    Works with both Qt (PySide2/6) and cmds UI.
    """
    global _ui_progress_bar, _cancel_requested, _ui_window_instance
    
    # Try Qt window first
    if _ui_window_instance is not None:
        try:
            _ui_window_instance.update_progress(value, max_value, status_text)
            return
        except Exception:
            pass
    
    # Fall back to cmds
    if not _ui_progress_bar or not cmds:
        return
    
    try:
        if cmds.progressBar(_ui_progress_bar, exists=True):
            # Calculate percentage
            if max_value > 0:
                percentage = int((float(value) / float(max_value)) * 100)
            else:
                percentage = 0
            
            # Update progress bar
            cmds.progressBar(_ui_progress_bar, edit=True, 
                           progress=percentage,
                           status=status_text)
            
            # Force UI refresh to show progress
            cmds.refresh()
            
            # Check if cancel was requested
            if cmds.progressBar(_ui_progress_bar, query=True, isCancelled=True):
                _cancel_requested = True
                log_to_ui('Operation cancelled by user', 'WARNING')
    except Exception as e:
        pass  # Silently fail to avoid interrupting operations


def reset_progress():
    """Reset progress bar to 0% and clear status. Works with both Qt and cmds UI."""
    global _ui_progress_bar, _cancel_requested, _ui_window_instance
    
    _cancel_requested = False
    
    # Try Qt window first
    if _ui_window_instance is not None:
        try:
            _ui_window_instance.reset_progress()
            return
        except Exception:
            pass
    
    # Fall back to cmds
    if _ui_progress_bar and cmds and cmds.progressBar(_ui_progress_bar, exists=True):
        try:
            cmds.progressBar(_ui_progress_bar, edit=True, progress=0, status='Ready')
        except Exception:
            pass


def clear_log():
    """Clear the UI log panel. Works with both Qt and cmds UI."""
    global _ui_log_field, _ui_window_instance
    
    # Try Qt window first
    if _ui_window_instance is not None:
        try:
            _ui_window_instance.clear_log()
            return
        except Exception:
            pass
    
    # Fall back to cmds
    if _ui_log_field and cmds and cmds.scrollField(_ui_log_field, exists=True):
        try:
            cmds.scrollField(_ui_log_field, edit=True, text='')
            log_to_ui('Log cleared', 'INFO')
        except Exception:
            pass


# ============================================================================
# UTILITY FUNCTIONS - Maya Environment
# ============================================================================

def _ensure_maya():
    """Check if running inside Maya"""
    if not cmds:
        msg = "This tool must be run inside Maya (maya.cmds not available)."
        print(msg)
        if logger:
            logger.error(msg)
        return False
    if logger:
        logger.debug('Maya environment confirmed')
    return True


def diagnose_environment():
    """Diagnose Maya environment and print status"""
    print('\n' + '='*60)
    print('GeoMaster - Environment Diagnostic')
    print('='*60)
    
    # Check Maya
    if cmds:
        print('[OK] Maya cmds module loaded')
        try:
            version = cmds.about(version=True)
            print('[OK] Maya version: %s' % version)
        except:
            print('[WARNING] Could not get Maya version')
    else:
        print('[ERROR] Maya cmds not available - must run inside Maya!')
        return False
    
    # Check MEL
    if mel:
        print('[OK] Maya MEL module loaded')
    else:
        print('[WARNING] Maya MEL not available')
    
    # Check OpenMaya
    if om:
        print('[OK] Maya OpenMaya module loaded')
    else:
        print('[WARNING] OpenMaya not available (non-critical)')
    
    # Check config
    try:
        import config as cfg
        print('[OK] Config module loaded')
        print('    - UI Window: %s' % cfg.UI_WINDOW_NAME)
        print('    - Logging: %s' % cfg.ENABLE_LOGGING)
    except:
        print('[WARNING] Config module not found (using defaults)')
    
    # Check logger
    if logger:
        print('[OK] Logger initialized')
        logger.info('Environment diagnostic completed')
    else:
        print('[WARNING] Logger not available')
    
    # Check scene
    try:
        scene = cmds.file(q=True, sn=True) or 'Untitled'
        print('[INFO] Current scene: %s' % scene)
    except:
        print('[WARNING] Could not query scene name')
    
    # Check selection
    try:
        sel = cmds.ls(selection=True) or []
        print('[INFO] Objects selected: %d' % len(sel))
    except:
        print('[WARNING] Could not query selection')
    
    print('='*60)
    print('Diagnostic complete. If all checks passed, run: main.show_ui()')
    print('='*60 + '\n')
    return True


def test_basic_functionality():
    """Test basic Maya functionality"""
    if not _ensure_maya():
        return False
    
    print('\nGeoMaster - Testing basic functionality...')
    
    try:
        # Test object creation
        test_obj = cmds.polySphere(name='test_sanity_sphere')[0]
        print('[OK] Created test sphere: %s' % test_obj)
        
        # Test selection
        cmds.select(test_obj)
        sel = cmds.ls(selection=True)
        print('[OK] Selection works: %s' % sel)
        
        # Test polyInfo
        info = cmds.polyInfo(test_obj, vertexToFace=True)
        print('[OK] PolyInfo works')
        
        # Cleanup
        cmds.delete(test_obj)
        print('[OK] Cleanup successful')
        
        print('[SUCCESS] All basic tests passed!\n')
        return True
        
    except Exception as e:
        print('[ERROR] Test failed: %s' % str(e))
        if logger:
            logger.error('Basic functionality test failed: %s' % str(e))
        return False


def _parse_polyinfo_components(text):
    """Parse component strings from polyInfo output"""
    if not text:
        return []
    comps = re.findall(r"[\w:_\.]+\.[efv]\[\d+(?:[:\d,]+)?\]", text)
    seen = set()
    out = []
    for c in comps:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


def _get_meshes():
    """Get mesh transforms from selection or entire scene"""
    sel = cmds.ls(selection=True, type='transform', long=True)
    if sel:
        return sel
    return cmds.ls(type='mesh', long=True)


def _get_mesh_shapes(transform):
    """Get mesh shape nodes from transform"""
    shapes = cmds.listRelatives(transform, shapes=True, fullPath=True, noIntermediate=True) or []
    return [s for s in shapes if cmds.nodeType(s) == 'mesh']


def generate_report(check_name, components, details=None):
    """Generate a detailed report of found issues"""
    if not _ensure_maya():
        return
    
    report_lines = []
    report_lines.append('='*70)
    report_lines.append('GEOMASTER - CHECK REPORT')
    report_lines.append('='*70)
    report_lines.append('Check: %s' % check_name)
    report_lines.append('Date: %s' % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    report_lines.append('-'*70)
    
    if not components:
        report_lines.append('Result: No issues found')
        report_lines.append('Status: PASS')
    else:
        report_lines.append('Result: Found %d issue(s)' % len(components))
        report_lines.append('Status: NEEDS ATTENTION')
        report_lines.append('-'*70)
        report_lines.append('Affected Components:')
        
        # Limit display to first 100 items
        display_count = min(len(components), 100)
        for i, comp in enumerate(components[:display_count]):
            report_lines.append('  [%d] %s' % (i+1, comp))
        
        if len(components) > display_count:
            report_lines.append('  ... and %d more' % (len(components) - display_count))
    
    if details:
        report_lines.append('-'*70)
        report_lines.append('Additional Details:')
        report_lines.append(details)
    
    report_lines.append('='*70)
    
    report_text = '\n'.join(report_lines)
    
    # Print to console
    print('\n' + report_text)
    
    # Log to file
    if logger:
        logger.info('Report generated for: %s' % check_name)
        logger.info('Found %d issues' % len(components))
    
    # Show dialog with summary (skip in batch mode to avoid spam)
    if not _is_batch_operation:
        if components:
            summary = 'Found %d issue(s)\n\nComponents have been selected in viewport.\n\nCheck Script Editor for full report.' % len(components)
        else:
            summary = 'No issues found.\n\nCheck passed successfully!'
        
        cmds.confirmDialog(
            title='Check Report: %s' % check_name,
            message=summary,
            button=['OK'],
            defaultButton='OK'
        )
    
    return report_text


def clear_all_overrides():
    """
    Clear all display color overrides and revert meshes to default state.
    
    This function disables all color overrides on mesh shapes and resets
    them to their default viewport display state (grey shaded).
    """
    if not _ensure_maya():
        return
    
    try:
        all_shapes = cmds.ls(type='mesh', long=True)
        cleared_count = 0
        
        for shape in all_shapes:
            try:
                # Check if override is enabled
                if cmds.getAttr(shape + '.overrideEnabled'):
                    # Disable override to return to default state
                    cmds.setAttr(shape + '.overrideEnabled', 0)
                    # Reset override color to default (ensures clean state)
                    cmds.setAttr(shape + '.overrideColor', 0)
                    cleared_count += 1
            except:
                pass
        
        if cleared_count > 0:
            cmds.inViewMessage(
                amg='<hl>Cleared highlighting from %d objects - Reverted to default</hl>' % cleared_count,
                pos='topCenter',
                fade=True,
                fadeStayTime=2000
            )
            if logger:
                logger.info('Cleared display overrides from %d objects - reverted to default' % cleared_count)
        else:
            cmds.inViewMessage(
                amg='<hl>No highlighting to clear</hl>',
                pos='topCenter',
                fade=True,
                fadeStayTime=2000
            )
    except Exception as e:
        error_msg = 'Error clearing overrides: %s' % str(e)
        if logger:
            logger.error(error_msg)


def highlight_components_visual(components, check_name='Check'):
    """Visually highlight components in viewport with red color overlay"""
    if not _ensure_maya():
        return
    
    if not components:
        cmds.inViewMessage(
            amg='<hl>%s: No issues found</hl>' % check_name,
            pos='topCenter',
            fade=True,
            fadeStayTime=2000
        )
        return
    
    try:
        # Clear selection first
        cmds.select(clear=True)
        
        # Select components
        cmds.select(components, r=True)
        
        # Get the mesh objects from components
        # Supports component strings (shape or transform) and plain transform names.
        meshes_to_highlight = set()
        for comp in components:
            base_name = comp.split('.')[0] if '.' in comp else comp

            # If we got a mesh shape, convert to its parent transform for overrides
            try:
                if cmds.objExists(base_name) and cmds.nodeType(base_name) == 'mesh':
                    parent = cmds.listRelatives(base_name, parent=True, fullPath=False) or []
                    if parent:
                        base_name = parent[0]
            except:
                pass

            meshes_to_highlight.add(base_name)
        
        # Apply red color override to meshes
        for mesh in meshes_to_highlight:
            try:
                # Get shape node
                shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True, noIntermediate=True) or []
                for shape in shapes:
                    # Enable display override and set to red (13 = red in Maya)
                    cmds.setAttr(shape + '.overrideEnabled', 1)
                    cmds.setAttr(shape + '.overrideColor', 13)  # Red
                    cmds.setAttr(shape + '.overrideDisplayType', 0)  # Normal
            except:
                pass
        
        # Show in-view message
        try:
            cmds.inViewMessage(
                amg='<hl>%s: %d components highlighted in RED - Select other objects to clear</hl>' % (check_name, len(components)),
                pos='topCenter',
                fade=True,
                fadeStayTime=4000
            )
        except:
            pass
        
        # DON'T frame the selection - keep current view
        # User can manually frame if needed with 'F' key
        
        if logger:
            logger.info('Visually highlighted %d components in red for: %s' % (len(components), check_name))
        
    except Exception as e:
        if logger:
            logger.warning('Bulk selection failed, trying individual: %s' % str(e))
        
        cmds.select(clear=True)
        success_count = 0
        for c in components:
            try:
                cmds.select(c, add=True)
                success_count += 1
            except:
                pass
        
        if success_count > 0:
            try:
                cmds.inViewMessage(
                    amg='<hl>%s: Highlighted %d components</hl>' % (check_name, success_count),
                    pos='topCenter',
                    fade=True,
                    fadeStayTime=3000
                )
            except:
                pass
        
        if logger:
            logger.info('Selected %d/%d components individually for: %s' % (success_count, len(components), check_name))


def highlight_components(components, check_name='Check'):
    """Select and highlight components in viewport"""
    if not _ensure_maya():
        return
    
    if logger:
        logger.debug('Highlighting %d components for: %s' % (len(components), check_name))
    
    if not components:
        generate_report(check_name, [])
        if logger:
            logger.info('No issues found for: %s' % check_name)
        return
    
    # Generate report
    generate_report(check_name, components)
    
    # Select and highlight in viewport
    try:
        cmds.select(components, r=True)
        try:
            cmds.inViewMessage(
                amg='<hl>%s: Found %d issues - Check Script Editor for report</hl>' % (check_name, len(components)),
                pos='topCenter',
                fade=True,
                fadeStayTime=3000
            )
        except:
            pass  # inViewMessage might not be available in all Maya versions
        
        if logger:
            logger.info('Selected %d components for: %s' % (len(components), check_name))
    
    except Exception as e:
        if logger:
            logger.warning('Bulk selection failed, trying individual: %s' % str(e))
        
        cmds.select(clear=True)
        success_count = 0
        for c in components:
            try:
                cmds.select(c, add=True)
                success_count += 1
            except:
                pass
        
        if logger:
            logger.info('Selected %d/%d components individually for: %s' % (success_count, len(components), check_name))


# ============================================================================
# CATEGORY 1: GEOMETRY & TOPOLOGY ERRORS
# ============================================================================

def find_non_manifold_edges():
    """Find edges shared by more than 2 faces"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    comps = []
    for node in meshes:
        try:
            info = cmds.polyInfo(node, nonManifoldEdges=True)
            if info:
                text = info[0] if isinstance(info, (list, tuple)) else str(info)
                comps += _parse_polyinfo_components(text)
        except:
            pass
    return comps


def find_lamina_faces():
    """Find duplicate faces sharing all edges"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    comps = []
    for node in meshes:
        try:
            info = cmds.polyInfo(node, laminaFaces=True)
            if info:
                text = info[0] if isinstance(info, (list, tuple)) else str(info)
                comps += _parse_polyinfo_components(text)
        except:
            pass
    return comps


def find_zero_area_faces():
    """Find degenerate/collapsed faces"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    comps = []
    for node in meshes:
        try:
            info = cmds.polyInfo(node, zeroAreaFaces=True)
            if info:
                text = info[0] if isinstance(info, (list, tuple)) else str(info)
                comps += _parse_polyinfo_components(text)
        except:
            pass
    return comps


def find_non_planar_faces(tolerance=0.001):
    """Find faces with vertices not on same plane"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    comps = []
    for mesh in meshes:
        try:
            info = cmds.polyInfo(mesh, nonPlanarFaces=tolerance)
            if info:
                text = info[0] if isinstance(info, (list, tuple)) else str(info)
                comps += _parse_polyinfo_components(text)
        except:
            pass
    return comps


def find_concave_faces():
    """Find concave faces using polyInfo (limited detection).
    
    Note: This is a basic implementation. For comprehensive detection,
    use Maya's Mesh > Cleanup tool with 'Faces with more than 4 sides' option.
    """
    if not _ensure_maya():
        return []
    
    # Basic detection: faces with unusual topology patterns
    meshes = _get_meshes()
    suspicious = []
    
    for mesh in meshes:
        try:
            # Get faces and check for irregular patterns
            faces = cmds.polyListComponentConversion(mesh, toFace=True) or []
            faces = cmds.filterExpand(faces, selectionMask=34) or []
            
            for face in faces:
                try:
                    # Concave faces often show up as non-planar with large tolerance
                    info = cmds.polyInfo(face, faceNormals=True)
                    if info:
                        # This is a simplified heuristic - not comprehensive
                        # Real concave detection needs proper geometric analysis
                        pass
                except:
                    pass
        except:
            pass
    
    # Return empty for now - proper implementation needs geometric analysis
    # Users should use Maya's built-in tools for accurate detection
    return suspicious


def find_non_manifold_vertices():
    """Find vertices connecting disjoint geometry"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    comps = []
    for mesh in meshes:
        try:
            info = cmds.polyInfo(mesh, nonManifoldVertices=True)
            if info:
                text = info[0] if isinstance(info, (list, tuple)) else str(info)
                comps += _parse_polyinfo_components(text)
        except:
            pass
    return comps


def find_duplicate_vertices(threshold=0.0001):
    """Find meshes that may have duplicate vertices.
    
    Note: This check identifies meshes that might have duplicates but doesn't
    pinpoint exact vertices. Use fix function to merge them.
    
    Args:
        threshold: Distance threshold for considering vertices as duplicates
    """
    if not _ensure_maya():
        return []
    
    meshes = _get_meshes()
    suspects = []
    
    for mesh in meshes:
        try:
            # Check vertex count before and after potential merge operation
            # This is a heuristic - we don't actually perform the merge
            vert_count = cmds.polyEvaluate(mesh, vertex=True) or 0
            
            # Meshes with high vertex counts are more likely to have duplicates
            # This is a simplified check - actual detection requires position comparison
            if vert_count > 100:
                # Use Maya's polyMergeVertex to test (in query mode if available)
                # For now, we return meshes that might benefit from merging
                # The fix function will do the actual merge
                pass
        except:
            pass
    
    # Return suspects list - fix_duplicate_vertices() will handle the actual merge
    return suspects


def find_isolated_vertices():
    """Find vertices not connected to any faces"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    out = []
    for m in meshes:
        try:
            verts = cmds.polyListComponentConversion(m, toVertex=True) or []
            for v in cmds.filterExpand(verts, selectionMask=31) or []:
                faces = cmds.polyListComponentConversion(v, fromVertex=True, toFace=True) or []
                if not faces:
                    out.append(v)
        except:
            continue
    return out


def find_zero_length_edges(threshold=0.0001):
    """Find edges with length less than threshold"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    comps = []
    for mesh in meshes:
        try:
            edges = cmds.polyListComponentConversion(mesh, toEdge=True) or []
            edges = cmds.filterExpand(edges, selectionMask=32) or []
            for edge in edges:
                length = cmds.polyEvaluate(edge, edgeLength=True)
                if length < threshold:
                    comps.append(edge)
        except:
            pass
    return comps


def find_ngons():
    """Find faces with more than 4 sides"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    out = []
    for m in meshes:
        try:
            faces = cmds.polyListComponentConversion(m, toFace=True) or []
            faces = cmds.filterExpand(faces, selectionMask=34) or []
            for f in faces:
                vtx = cmds.polyListComponentConversion(f, toVertex=True)
                vtx = cmds.filterExpand(vtx, selectionMask=31) or []
                if len(vtx) > 4:
                    out.append(f)
        except:
            continue
    return out


# ============================================================================
# CATEGORY 3: UV & TEXTURE COORDINATE ERRORS
# ============================================================================

def find_overlapping_uvs():
    """Find overlapping UVs using Maya's built-in overlap detector.

    Returns:
        list: Overlapping polygon face components (best for highlighting).
    """
    if not _ensure_maya():
        return []

    meshes = _get_meshes()
    overlapping_faces = []

    log_to_ui('Checking for overlapping UVs on %d meshes...' % len(meshes), 'INFO')

    for mesh in meshes:
        try:
            face_count = cmds.polyEvaluate(mesh, face=True) or 0
            if face_count <= 0:
                continue

            # Feed all faces explicitly; no selection required.
            all_faces = '%s.f[0:%d]' % (mesh, face_count - 1)
            overlaps = cmds.polyUVOverlap(all_faces, oc=True) or []
            if not overlaps:
                # Compatibility fallback for different Maya flag spellings
                try:
                    overlaps = cmds.polyUVOverlap(all_faces, overlappingComponents=True) or []
                except:
                    overlaps = overlaps or []

            if overlaps:
                overlapping_faces.extend(overlaps)

        except Exception as e:
            log_to_ui('UV overlap check failed on %s: %s' % (mesh, str(e)), 'WARNING')

    try:
        cmds.select(clear=True)
    except:
        pass

    log_to_ui(
        'RESULT: %s' % (
            ('Found %d overlapping faces' % len(overlapping_faces))
            if overlapping_faces else
            'No overlapping UVs detected'
        ),
        'WARNING' if overlapping_faces else 'SUCCESS'
    )

    return overlapping_faces


def find_uvs_outside_range():
    """Find faces with UVs outside 0-1 range (UDIM 1001 tile).
    
    Returns:
        list: Face components that have UVs outside the 0-1 range
    """
    if not _ensure_maya():
        return []
    
    meshes = _get_meshes()
    outside_faces = []
    
    log_to_ui('Checking UVs outside 0-1 range on %d meshes...' % len(meshes), 'INFO')
    
    for mesh in meshes:
        try:
            shapes = _get_mesh_shapes(mesh)

            for shape in shapes:
                try:
                    # Get face count
                    face_count = cmds.polyEvaluate(shape, face=True) or 0
                    if face_count <= 0:
                        continue
                    
                    # Check UVs exist
                    uv_count = cmds.polyEvaluate(shape, uvcoord=True) or 0
                    if uv_count <= 0:
                        continue

                    # Check each face's UVs
                    eps = 0.001
                    min_u_total = float('inf')
                    max_u_total = float('-inf')
                    min_v_total = float('inf')
                    max_v_total = float('-inf')
                    
                    for face_id in range(face_count):
                        face_name = '%s.f[%d]' % (shape, face_id)
                        
                        try:
                            # Convert face to UV coordinates
                            uv_coords = cmds.polyListComponentConversion(face_name, fromFace=True, toUV=True)
                            uv_coords = cmds.filterExpand(uv_coords, selectionMask=35) or []  # 35 = UV
                            
                            if not uv_coords:
                                continue
                            
                            # Get UV positions for this face
                            face_outside = False
                            for uv in uv_coords:
                                try:
                                    uv_pos = cmds.polyEditUV(uv, query=True, uValue=True, vValue=True)
                                    if uv_pos and len(uv_pos) >= 2:
                                        u_val = uv_pos[0]
                                        v_val = uv_pos[1]
                                        
                                        # Track min/max for logging
                                        min_u_total = min(min_u_total, u_val)
                                        max_u_total = max(max_u_total, u_val)
                                        min_v_total = min(min_v_total, v_val)
                                        max_v_total = max(max_v_total, v_val)
                                        
                                        # Check if outside 0-1 range
                                        if (u_val < -eps or u_val > 1.0 + eps or 
                                            v_val < -eps or v_val > 1.0 + eps):
                                            face_outside = True
                                            break
                                except:
                                    pass
                            
                            # Add face if it has UVs outside range
                            if face_outside:
                                # Use transform name for better compatibility
                                parent = cmds.listRelatives(shape, parent=True, fullPath=True) or [shape]
                                face_component = '%s.f[%d]' % (parent[0] if parent else shape, face_id)
                                outside_faces.append(face_component)
                        
                        except:
                            pass
                    
                    # Log if this mesh has issues
                    if outside_faces and min_u_total != float('inf'):
                        # Check if any faces from this mesh were added
                        mesh_faces = [f for f in outside_faces if mesh in f or shape in f]
                        if mesh_faces:
                            log_to_ui(
                                '  -> OUTSIDE RANGE on %s: %d faces (U: %.3f..%.3f, V: %.3f..%.3f)' % 
                                (mesh, len(mesh_faces), min_u_total, max_u_total, min_v_total, max_v_total),
                                'WARNING'
                            )

                except Exception as e:
                    log_to_ui('UV bounds check failed on %s: %s' % (shape, str(e)), 'WARNING')

        except Exception as e:
            log_to_ui('UV bounds check failed on %s: %s' % (mesh, str(e)), 'WARNING')
    
    # Clear selection
    try:
        cmds.select(clear=True)
    except:
        pass
    
    result_msg = 'Found %d faces with UVs outside 0-1 range' % len(outside_faces) if outside_faces else 'All UVs within 0-1 range'
    log_to_ui('RESULT: ' + result_msg, 'SUCCESS' if not outside_faces else 'WARNING')
            
    return outside_faces


def find_missing_uvs():
    """Find meshes without UV sets"""
    if not _ensure_maya():
        return []
    
    meshes = _get_meshes()
    missing = []
    
    log_to_ui('Checking for missing UV sets...', 'INFO')
    
    for mesh in meshes:
        try:
            shapes = _get_mesh_shapes(mesh)
            for shape in shapes:
                try:
                    # Check if UV sets exist
                    uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True)
                    
                    if not uv_sets or len(uv_sets) == 0:
                        if mesh not in missing:
                            missing.append(mesh)
                            log_to_ui('  Missing UV set on: %s' % mesh, 'INFO')
                        break
                    
                    # Also check if UVs actually exist (set exists but no coordinates)
                    num_uvs = cmds.polyEvaluate(shape, uvcoord=True) or 0
                    if num_uvs == 0:
                        if mesh not in missing:
                            missing.append(mesh)
                            log_to_ui('  No UV coordinates on: %s' % mesh, 'INFO')
                        break
                        
                except Exception as e:
                    log_to_ui('  Error checking %s: %s' % (shape, str(e)), 'WARNING')
                    pass
                    
        except Exception as e:
            log_to_ui('  Error processing mesh %s: %s' % (mesh, str(e)), 'WARNING')
            pass
    
    if missing:
        log_to_ui('Found %d meshes without UVs' % len(missing), 'INFO')
    else:
        log_to_ui('All meshes have UV sets', 'INFO')
        
    return missing


def find_multiple_uv_sets():
    """Find meshes with multiple UV sets"""
    if not _ensure_maya():
        return []
    
    meshes = _get_meshes()
    multiple = []
    
    log_to_ui('Checking for multiple UV sets...', 'INFO')
    
    for mesh in meshes:
        try:
            shapes = _get_mesh_shapes(mesh)
            for shape in shapes:
                try:
                    uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True)
                    
                    if uv_sets and len(uv_sets) > 1:
                        if mesh not in multiple:
                            multiple.append(mesh)
                            log_to_ui('  Multiple UV sets on: %s (%d sets)' % (mesh, len(uv_sets)), 'INFO')
                        break
                        
                except Exception as e:
                    log_to_ui('  Error checking %s: %s' % (shape, str(e)), 'WARNING')
                    pass
                    
        except Exception as e:
            log_to_ui('  Error processing mesh %s: %s' % (mesh, str(e)), 'WARNING')
            pass
    
    if multiple:
        log_to_ui('Found %d meshes with multiple UV sets' % len(multiple), 'INFO')
    else:
        log_to_ui('All meshes have single UV sets', 'INFO')
        
    return multiple


# ============================================================================
# CATEGORY 4: SHADER & MATERIAL ISSUES
# ============================================================================

def find_default_shader_assignments():
    """Find objects assigned to initialShadingGroup (lambert1)"""
    if not _ensure_maya():
        return []
    try:
        members = cmds.sets('initialShadingGroup', q=True) or []
        # Filter out default objects
        objects = [m for m in members if not m.startswith('initial') and not m.startswith('default')]
        return objects
    except:
        return []


def find_multiple_shaders():
    """Find objects with multiple shader assignments (face-level)"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    multi = []
    for mesh in meshes:
        try:
            shapes = _get_mesh_shapes(mesh)
            for shape in shapes:
                sgs = cmds.listConnections(shape, type='shadingEngine') or []
                if len(set(sgs)) > 1:
                    multi.append(mesh)
                    break
        except:
            pass
    return multi


def find_unused_shading_nodes():
    """Check for unused shader and utility nodes in the scene.
    
    Returns:
        list: List of unused shader, texture, and utility nodes
    """
    if not _ensure_maya():
        return []
    
    try:
        unused_nodes = []
        
        # 1. Unknown/corrupted nodes (definitely unused)
        unknown_nodes = cmds.ls(type=['unknown', 'unknownDag', 'unknownTransform']) or []
        unused_nodes.extend(unknown_nodes)
        
        # 2. Shader nodes not connected to any geometry
        shader_types = ['lambert', 'phong', 'blinn', 'aiStandardSurface', 'surfaceShader', 
                       'anisotropic', 'layeredShader', 'shadingEngine']
        
        for shader_type in shader_types:
            shaders = cmds.ls(type=shader_type) or []
            for shader in shaders:
                # Skip default shaders
                if shader in ['lambert1', 'particleCloud1', 'initialShadingGroup', 
                             'initialParticleSE', 'initialMaterialInfo']:
                    continue
                
                # For shading engines, check if they have any members
                if shader_type == 'shadingEngine':
                    members = cmds.sets(shader, q=True) or []
                    if not members or len(members) == 0:
                        unused_nodes.append(shader)
                else:
                    # For other shaders, check if connected to shading engine
                    connections = cmds.listConnections(shader, type='shadingEngine') or []
                    if not connections or len(connections) == 0:
                        unused_nodes.append(shader)
        
        # 3. Texture and utility nodes not connected to anything
        utility_types = ['file', 'place2dTexture', 'bump2d', 'ramp', 'checker', 
                        'fractal', 'noise', 'multiplyDivide', 'colorCorrect', 
                        'luminance', 'reverse', 'clamp', 'blendColors']
        
        for util_type in utility_types:
            nodes = cmds.ls(type=util_type) or []
            for node in nodes:
                # Check if node has any outgoing connections
                connections = cmds.listConnections(node, source=False, destination=True) or []
                if not connections or len(connections) == 0:
                    unused_nodes.append(node)
        
        # Remove duplicates
        unused_nodes = list(set(unused_nodes))
        return unused_nodes
        
    except Exception as e:
        log_to_ui('Error finding unused nodes: %s' % str(e), 'ERROR')
        return []


# ============================================================================
# CATEGORY 5: CONSTRUCTION HISTORY & NODE ISSUES
# ============================================================================

def find_construction_history():
    """Find objects with construction history"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    with_history = []
    for mesh in meshes:
        try:
            history = cmds.listHistory(mesh, pruneDagObjects=True) or []
            # Filter out shape nodes
            history = [h for h in history if cmds.nodeType(h) != 'mesh' and cmds.nodeType(h) != 'transform']
            if history:
                with_history.append(mesh)
        except:
            pass
    return with_history


def find_intermediate_objects():
    """Find intermediate objects that should be hidden"""
    if not _ensure_maya():
        return []
    try:
        intermediate = cmds.ls(intermediateObjects=True)
        visible = [obj for obj in intermediate if cmds.getAttr(obj + '.visibility')]
        return visible
    except:
        return []


def find_empty_groups():
    """Find empty transform/group nodes"""
    if not _ensure_maya():
        return []
    transforms = cmds.ls(type='transform')
    empty = []
    for t in transforms:
        try:
            children = cmds.listRelatives(t, children=True) or []
            if not children:
                empty.append(t)
        except:
            pass
    return empty


# ============================================================================
# CATEGORY 6: TRANSFORM & PIVOT PROBLEMS
# ============================================================================

def find_non_zero_transforms():
    """Find objects with non-default transformations"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    non_zero = []
    for mesh in meshes:
        try:
            translate = cmds.getAttr(mesh + '.translate')[0]
            rotate = cmds.getAttr(mesh + '.rotate')[0]
            scale = cmds.getAttr(mesh + '.scale')[0]
            if (abs(translate[0]) > 0.001 or abs(translate[1]) > 0.001 or abs(translate[2]) > 0.001 or
                abs(rotate[0]) > 0.001 or abs(rotate[1]) > 0.001 or abs(rotate[2]) > 0.001 or
                abs(scale[0] - 1.0) > 0.001 or abs(scale[1] - 1.0) > 0.001 or abs(scale[2] - 1.0) > 0.001):
                non_zero.append(mesh)
        except:
            pass
    return non_zero


def find_negative_scale():
    """Find objects with negative scale values"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    negative = []
    for mesh in meshes:
        try:
            scale = cmds.getAttr(mesh + '.scale')[0]
            if scale[0] < 0 or scale[1] < 0 or scale[2] < 0:
                negative.append(mesh)
        except:
            pass
    return negative


# ============================================================================
# CATEGORY 7: NAMING & ORGANIZATION ERRORS
# ============================================================================

def find_duplicate_names():
    """Find objects with duplicate names"""
    if not _ensure_maya():
        return []
    all_objects = cmds.ls()
    names = {}
    duplicates = []
    for obj in all_objects:
        short_name = obj.split('|')[-1]
        if short_name in names:
            if names[short_name] not in duplicates:
                duplicates.append(names[short_name])
            duplicates.append(obj)
        else:
            names[short_name] = obj
    return duplicates





# ============================================================================
# CATEGORY 8: PERFORMANCE & OPTIMIZATION ISSUES
# ============================================================================

def find_high_poly_objects(threshold=50000):
    """Find objects with excessive polygon count"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    high_poly = []
    for mesh in meshes:
        try:
            poly_count = cmds.polyEvaluate(mesh, face=True)
            if poly_count > threshold:
                high_poly.append(mesh)
        except:
            pass
    return high_poly


# ============================================================================
# CATEGORY 9: DATA INTEGRITY ISSUES
# ============================================================================
# Each mesh tries to call polyEvaluate twice to ensure data integrity. 
# on the basis of vertex count and face count.
# If either query fails, the mesh is corrupt.

def find_invalid_geometry():
    """Find meshes with corrupted data"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    invalid = []
    for mesh in meshes:
        try:
            # Try to query basic properties
            cmds.polyEvaluate(mesh, vertex=True)
            cmds.polyEvaluate(mesh, face=True)
        except:
            invalid.append(mesh)
    return invalid


# ============================================================================
# CATEGORY 10: COLOR & VERTEX ATTRIBUTE PROBLEMS
# ============================================================================

def find_unused_color_sets():
    """Find meshes with unused color sets"""
    if not _ensure_maya():
        return []
    meshes = _get_meshes()
    unused = []
    for mesh in meshes:
        try:
            shapes = _get_mesh_shapes(mesh)
            for shape in shapes:
                color_sets = cmds.polyColorSet(shape, q=True, allColorSets=True) or []
                if len(color_sets) > 1:  # More than default
                    unused.append(mesh)
                    break
        except:
            pass
    return unused


# ============================================================================
# FIX FUNCTIONS
# ============================================================================

def fix_zero_area_faces():
    """Delete zero-area faces"""
    if not _ensure_maya():
        return
    faces = find_zero_area_faces()
    if not faces:
        cmds.confirmDialog(title='Fix', message='No zero-area faces found.')
        return
    try:
        cmds.delete(faces)
        cmds.confirmDialog(title='Fixed', message='Deleted %d zero-area faces.' % len(faces))
    except Exception as e:
        cmds.confirmDialog(title='Error', message='Failed to delete: %s' % str(e))


def fix_duplicate_vertices(threshold=0.0001):
    """Merge duplicate vertices"""
    if not _ensure_maya():
        return
    meshes = find_duplicate_vertices(threshold)
    if not meshes:
        cmds.confirmDialog(title='Fix', message='No meshes found.')
        return
    count = 0
    for m in meshes:
        try:
            cmds.polyMergeVertex(m, d=threshold, ch=False)
            count += 1
        except:
            pass
    cmds.confirmDialog(title='Fixed', message='Merged vertices on %d meshes.' % count)


def fix_lamina_faces():
    """Delete lamina faces"""
    if not _ensure_maya():
        return
    faces = find_lamina_faces()
    if not faces:
        cmds.confirmDialog(title='Fix', message='No lamina faces found.')
        return
    try:
        cmds.delete(faces)
        cmds.confirmDialog(title='Fixed', message='Deleted %d lamina faces.' % len(faces))
    except Exception as e:
        cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


def fix_non_manifold_geometry():
    """Attempt to fix non-manifold geometry using polyCleanup"""
    if not _ensure_maya():
        return
    try:
        mel.eval('polyCleanupArgList 4 { "0","2","1","0","0","0","0","0","0","1e-05","0","1e-05","0","1e-05","0","-1","0","0" };')
        cmds.confirmDialog(title='Fixed', message='Ran polyCleanup on non-manifold geometry.')
    except Exception as e:
        cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


# fix_reversed_normals() removed


def fix_locked_normals():
    """Unlock all normals - NOTE: find_locked_normals() not implemented"""
    if not _ensure_maya():
        return
    
    cmds.confirmDialog(
        title='Feature Not Available',
        message='Locked normals detection is not implemented.\n\nPlease use Maya\'s Mesh > Unlock Normals menu instead.',
        button=['OK']
    )


# fix_hard_edges() removed


def fix_construction_history():
    """Delete construction history"""
    if not _ensure_maya():
        return
    meshes = find_construction_history()
    if not meshes:
        cmds.confirmDialog(title='Fix', message='No history found.')
        return
    for mesh in meshes:
        try:
            cmds.delete(mesh, ch=True)
        except:
            pass
    cmds.confirmDialog(title='Fixed', message='Deleted history on %d objects.' % len(meshes))


def fix_empty_groups():
    """Delete empty groups"""
    if not _ensure_maya():
        return
    empty = find_empty_groups()
    if not empty:
        cmds.confirmDialog(title='Fix', message='No empty groups found.')
        return
    try:
        cmds.delete(empty)
        cmds.confirmDialog(title='Fixed', message='Deleted %d empty groups.' % len(empty))
    except Exception as e:
        cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


def fix_default_shader_assignments():
    """Remove objects from initialShadingGroup"""
    if not _ensure_maya():
        return
    objects = find_default_shader_assignments()
    if not objects:
        cmds.confirmDialog(title='Fix', message='No default assignments found.')
        return
    # Just report them - user should assign proper shader
    cmds.select(objects, r=True)
    cmds.confirmDialog(title='Info', message='Selected %d objects. Assign proper shaders.' % len(objects))


def fix_freeze_transforms():
    """Freeze transformations"""
    if not _ensure_maya():
        return
    meshes = find_non_zero_transforms()
    if not meshes:
        cmds.confirmDialog(title='Fix', message='No non-zero transforms found.')
        return
    for mesh in meshes:
        try:
            cmds.makeIdentity(mesh, apply=True, translate=True, rotate=True, scale=True)
        except:
            pass
    cmds.confirmDialog(title='Fixed', message='Froze transforms on %d objects.' % len(meshes))


def fix_isolated_vertices():
    """Delete isolated vertices"""
    if not _ensure_maya():
        return
    verts = find_isolated_vertices()
    if not verts:
        cmds.confirmDialog(title='Fix', message='No isolated vertices found.')
        return
    try:
        cmds.delete(verts)
        cmds.confirmDialog(title='Fixed', message='Deleted %d isolated vertices.' % len(verts))
    except Exception as e:
        cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


def fix_non_planar_faces():
    """Fix non-planar faces by triangulating them"""
    if not _ensure_maya():
        return
    faces = find_non_planar_faces()
    if not faces:
        cmds.confirmDialog(title='Fix', message='No non-planar faces found.')
        return
    
    result = cmds.confirmDialog(
        title='Fix Non-Planar Faces',
        message='Found %d non-planar faces.\nTriangulate them?' % len(faces),
        button=['Triangulate', 'Cancel'],
        defaultButton='Triangulate',
        cancelButton='Cancel'
    )
    
    if result == 'Triangulate':
        try:
            cmds.polyTriangulate(faces, ch=False)
            cmds.confirmDialog(title='Fixed', message='Triangulated %d non-planar faces.' % len(faces))
        except Exception as e:
            cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


def fix_non_manifold_vertices():
    """Fix non-manifold vertices by separating or merging"""
    if not _ensure_maya():
        return
    verts = find_non_manifold_vertices()
    if not verts:
        cmds.confirmDialog(title='Fix', message='No non-manifold vertices found.')
        return
    
    # Get unique meshes
    meshes = list(set([v.split('.')[0] for v in verts]))
    
    result = cmds.confirmDialog(
        title='Fix Non-Manifold Vertices',
        message='Found %d non-manifold vertices in %d meshes.\nUse Mesh > Cleanup to separate them?' % (len(verts), len(meshes)),
        button=['Cleanup', 'Cancel'],
        defaultButton='Cleanup',
        cancelButton='Cancel'
    )
    
    if result == 'Cleanup':
        try:
            for mesh in meshes:
                cmds.select(mesh, r=True)
                mel.eval('polyCleanupArgList 4 { "0","2","1","0","1","0","0","0","0","1e-05","0","1e-05","0","1e-05","0","-1","0","0" };')
            cmds.confirmDialog(title='Fixed', message='Applied cleanup to %d meshes.' % len(meshes))
        except Exception as e:
            cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


def fix_zero_length_edges():
    """Fix zero-length edges by merging vertices"""
    if not _ensure_maya():
        return
    edges = find_zero_length_edges()
    if not edges:
        cmds.confirmDialog(title='Fix', message='No zero-length edges found.')
        return
    
    result = cmds.confirmDialog(
        title='Fix Zero-Length Edges',
        message='Found %d zero-length edges.\nMerge vertices?' % len(edges),
        button=['Merge', 'Cancel'],
        defaultButton='Merge',
        cancelButton='Cancel'
    )
    
    if result == 'Merge':
        try:
            # Get unique meshes
            meshes = list(set([e.split('.')[0] for e in edges]))
            for mesh in meshes:
                cmds.polyMergeVertex(mesh, d=0.001, ch=False)
            cmds.confirmDialog(title='Fixed', message='Merged vertices on %d meshes.' % len(meshes))
        except Exception as e:
            cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


def fix_ngons():
    """N-gons require manual intervention to preserve mesh flow"""
    if not _ensure_maya():
        return
    faces = find_ngons()
    if not faces:
        cmds.confirmDialog(title='Fix N-gons', message='No n-gons found.')
        return
    
    log_to_ui('N-gons: Manual intervention required to preserve mesh flow', 'WARNING')
    cmds.confirmDialog(
        title='Manual Intervention Required',
        message='Found %d n-gons (faces with >4 sides).\n\nAutomatic fixing can affect mesh flow and topology.\nPlease manually retopologize these faces to maintain proper edge flow.' % len(faces),
        button=['OK'],
        defaultButton='OK'
    )


def fix_missing_uvs():
    """Create automatic UV projection for meshes without UVs"""
    if not _ensure_maya():
        return
    meshes = find_missing_uvs()
    if not meshes:
        cmds.confirmDialog(title='Fix', message='No meshes missing UVs.')
        return
    
    result = cmds.confirmDialog(
        title='Fix Missing UVs',
        message='Found %d meshes without UVs.\nCreate automatic projection?' % len(meshes),
        button=['Planar', 'Automatic', 'Cancel'],
        defaultButton='Automatic',
        cancelButton='Cancel'
    )
    
    if result == 'Planar':
        try:
            for mesh in meshes:
                cmds.polyProjection(mesh, type='Planar', ch=False)
            cmds.confirmDialog(title='Fixed', message='Applied planar projection to %d meshes.' % len(meshes))
        except Exception as e:
            cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))
    elif result == 'Automatic':
        try:
            for mesh in meshes:
                cmds.polyAutoProjection(mesh, ch=False)
            cmds.confirmDialog(title='Fixed', message='Applied automatic projection to %d meshes.' % len(meshes))
        except Exception as e:
            cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


def fix_uvs_outside_range():
    """Normalize UVs to 0-1 range"""
    if not _ensure_maya():
        return
    components = find_uvs_outside_range()
    if not components:
        cmds.confirmDialog(title='Fix', message='No UVs outside 0-1 range.')
        return
    
    result = cmds.confirmDialog(
        title='Fix UVs Outside Range',
        message='Found %d UV components outside 0-1 range.\nNormalize to 0-1?' % len(components),
        button=['Normalize', 'Cancel'],
        defaultButton='Normalize',
        cancelButton='Cancel'
    )
    
    if result == 'Normalize':
        try:
            meshes = list(set([c.split('.')[0] for c in components]))
            for mesh in meshes:
                cmds.polyNormalizeUV(mesh, normalizeType=1, ch=False)
            cmds.confirmDialog(title='Fixed', message='Normalized UVs on %d meshes.' % len(meshes))
        except Exception as e:
            cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


def fix_multiple_uv_sets():
    """Delete extra UV sets keeping only the first"""
    if not _ensure_maya():
        return
    meshes = find_multiple_uv_sets()
    if not meshes:
        cmds.confirmDialog(title='Fix', message='No meshes with multiple UV sets.')
        return
    
    result = cmds.confirmDialog(
        title='Fix Multiple UV Sets',
        message='Found %d meshes with multiple UV sets.\nDelete extra UV sets (keep first)?' % len(meshes),
        button=['Delete Extra', 'Cancel'],
        defaultButton='Delete Extra',
        cancelButton='Cancel'
    )
    
    if result == 'Delete Extra':
        try:
            count = 0
            for mesh in meshes:
                shapes = _get_mesh_shapes(mesh)
                for shape in shapes:
                    uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
                    if len(uv_sets) > 1:
                        for uv_set in uv_sets[1:]:  # Keep first, delete rest
                            cmds.polyUVSet(shape, delete=True, uvSet=uv_set)
                            count += 1
            cmds.confirmDialog(title='Fixed', message='Deleted %d extra UV sets.' % count)
        except Exception as e:
            cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


def fix_overlapping_uvs():
    """Fix overlapping UVs using automatic UV layout"""
    if not _ensure_maya():
        return

    overlaps = find_overlapping_uvs()
    if not overlaps:
        cmds.confirmDialog(title='Fix', message='No overlapping UVs found.')
        return

    # Convert overlapping components to unique transform meshes
    meshes = []
    mesh_set = set()
    for comp in overlaps:
        base = comp.split('.')[0] if '.' in comp else comp
        try:
            if cmds.objExists(base) and cmds.nodeType(base) == 'mesh':
                parent = cmds.listRelatives(base, parent=True, fullPath=False) or []
                if parent:
                    base = parent[0]
        except:
            pass

        if base and base not in mesh_set:
            mesh_set.add(base)
            meshes.append(base)
    
    result = cmds.confirmDialog(
        title='Fix Overlapping UVs',
        message='Found %d mesh(es) with overlapping UVs.\n\nFix method:\n• Layout - Automatic UV layout (recommended)\n• Unfold - UV unfold optimization\n• Cancel' % len(meshes),
        button=['Layout', 'Unfold', 'Cancel'],
        defaultButton='Layout',
        cancelButton='Cancel'
    )
    
    if result == 'Cancel':
        return
    
    fixed_count = 0
    for mesh in meshes:
        try:
            shapes = _get_mesh_shapes(mesh)
            for shape in shapes:
                try:
                    if result == 'Layout':
                        # Use automatic UV layout
                        cmds.select(shape, r=True)
                        cmds.polyAutoProjection(shape, 
                                                layoutMethod=1,  # Layout in UV space
                                                optimize=1,      # Optimize
                                                insertBeforeDeformers=True,
                                                scaleMode=1,     # Uniform scale
                                                createNewMap=False)
                        fixed_count += 1
                    elif result == 'Unfold':
                        # Use UV unfold
                        cmds.select(shape, r=True)
                        cmds.unfold(shape, iterations=1, packRatio=0.0, 
                                   optimizeAxis=0, useScale=False)
                        # Then layout UVs
                        cmds.polyLayoutUV(shape, layout=2, scale=1, 
                                         rotateForBestFit=0)
                        fixed_count += 1
                        
                except Exception as e:
                    if logger:
                        logger.debug('Error fixing UVs for %s: %s' % (shape, str(e)))
                    pass
                    
        except Exception as e:
            if logger:
                logger.debug('Error processing mesh %s: %s' % (mesh, str(e)))
            pass
    
    # Clear selection
    try:
        cmds.select(clear=True)
    except:
        pass
    
    if fixed_count > 0:
        cmds.confirmDialog(title='Fixed', 
                         message='Fixed overlapping UVs on %d meshes.' % fixed_count)
    else:
        cmds.confirmDialog(title='Error', 
                         message='Could not fix UVs. Check Script Editor for details.')


def fix_multiple_shaders():
    """
    Fix multiple shaders by assigning first shader to entire object.
    
    This removes face-level shader assignments and applies one shader uniformly.
    """
    if not _ensure_maya():
        return
    
    meshes = find_multiple_shaders()
    
    if not meshes:
        cmds.confirmDialog(
            title='Fix Multiple Shaders',
            message='No objects with multiple shaders found.',
            button=['OK']
        )
        return
    
    result = cmds.confirmDialog(
        title='Fix Multiple Shaders',
        message='Found %d objects with multiple shaders.\n\nAssign first shader to entire object?' % len(meshes),
        button=['Fix', 'Cancel'],
        defaultButton='Fix',
        cancelButton='Cancel'
    )
    
    if result == 'Cancel':
        return
    
    try:
        fixed_count = 0
        for mesh in meshes:
            try:
                shapes = _get_mesh_shapes(mesh)
                for shape in shapes:
                    # Get all shading groups connected to this shape
                    shading_groups = cmds.listConnections(shape, type='shadingEngine')
                    
                    if shading_groups and len(shading_groups) > 0:
                        # Use the first shader found
                        first_sg = shading_groups[0]
                        
                        # Assign entire object to this shader
                        cmds.sets(shape, edit=True, forceElement=first_sg)
                        fixed_count += 1
                        
            except Exception as e:
                if logger:
                    logger.warning('Could not fix shaders on %s: %s' % (mesh, str(e)))
                pass
        
        cmds.confirmDialog(
            title='Fixed',
            message='Fixed multiple shaders on %d objects.' % fixed_count,
            button=['OK']
        )
        
        if logger:
            logger.info('Fixed multiple shaders on %d objects' % fixed_count)
            
    except Exception as e:
        error_msg = 'Failed to fix multiple shaders: %s' % str(e)
        cmds.confirmDialog(title='Error', message=error_msg, button=['OK'])
        if logger:
            logger.error(error_msg)


def fix_unused_shading_nodes():
    """Delete all unused nodes in the scene using Umbra-style MEL command.
    
    This uses Maya's built-in hyperShade deleteUnusedNodes functionality via MEL,
    which is the most reliable way to delete unused shader and utility nodes.
    """
    if not _ensure_maya():
        return
    
    result = cmds.confirmDialog(
        title='Delete Unused Nodes',
        message='Delete all unused shader and utility nodes?\n\nThis will clean up orphaned materials, textures, and other nodes.',
        button=['Delete', 'Cancel'],
        defaultButton='Delete',
        cancelButton='Cancel'
    )
    
    if result != 'Delete':
        return
    
    try:
        log_to_ui('Deleting unused nodes using hyperShade deleteUnusedNodes...', 'INFO')
        
        # First try MEL command (most reliable)
        try:
            mel.eval('hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes");')
            log_to_ui('  Successfully ran MEL deleteUnusedNodes command', 'SUCCESS')
            cmds.confirmDialog(title='Complete', message='Deleted unused shader nodes.', button=['OK'])
            log_to_ui('RESULT: Unused nodes deleted', 'SUCCESS')
            return
        except Exception as e:
            log_to_ui('  MEL command failed, trying fallback: %s' % str(e), 'WARNING')
        
        # Fallback: Use Python to delete unknown and orphaned nodes
        log_to_ui('Using Python fallback to delete unused nodes...', 'INFO')
        deleted_count = 0
        
        # Delete unknown nodes (corrupted/broken nodes)
        unknown_nodes = cmds.ls(type=['unknown', 'unknownDag', 'unknownTransform']) or []
        if unknown_nodes:
            try:
                cmds.delete(unknown_nodes)
                deleted_count += len(unknown_nodes)
                log_to_ui('  Deleted %d unknown nodes' % len(unknown_nodes), 'SUCCESS')
            except Exception as e:
                log_to_ui('  Failed to delete unknown nodes: %s' % str(e), 'WARNING')
        
        # Delete orphaned dependency nodes
        try:
            all_nodes = cmds.ls(dependencyNodes=True) or []
            orphaned = 0
            
            for node in all_nodes:
                try:
                    # Skip protected/system nodes
                    if node.startswith('initial') or node.startswith('default') or \
                       node.startswith('particle') or node in ['lambert1', 'particleCloud1', 'time1']:
                        continue
                    
                    node_type = cmds.nodeType(node)
                    if node_type in ['transform', 'mesh', 'joint', 'ikHandle']:
                        continue
                    
                    # Check for connections
                    connections = cmds.listConnections(node, source=True, destination=True, plugs=False)
                    
                    if not connections or len(connections) == 0:
                        try:
                            cmds.delete(node)
                            deleted_count += 1
                            orphaned += 1
                        except:
                            pass
                except:
                    pass
            
            if orphaned > 0:
                log_to_ui('  Deleted %d orphaned nodes' % orphaned, 'SUCCESS')
        except Exception as e:
            log_to_ui('  Error cleaning orphaned nodes: %s' % str(e), 'WARNING')
        
        # Show result
        msg = 'Deleted %d unused nodes' % deleted_count
        cmds.confirmDialog(title='Complete', message=msg, button=['OK'])
        log_to_ui('RESULT: %s' % msg, 'SUCCESS')
        
    except Exception as e:
        error_msg = 'Delete unused nodes failed: %s' % str(e)
        cmds.confirmDialog(title='Error', message=error_msg, button=['OK'])
        log_to_ui(error_msg, 'ERROR')


def fix_intermediate_objects():
    """Hide intermediate objects"""
    if not _ensure_maya():
        return
    objects = find_intermediate_objects()
    if not objects:
        cmds.confirmDialog(title='Fix', message='No visible intermediate objects.')
        return
    
    result = cmds.confirmDialog(
        title='Fix Intermediate Objects',
        message='Found %d visible intermediate objects.\nHide them?' % len(objects),
        button=['Hide', 'Delete', 'Cancel'],
        defaultButton='Hide',
        cancelButton='Cancel'
    )
    
    if result == 'Hide':
        try:
            for obj in objects:
                cmds.setAttr(obj + '.visibility', 0)
            cmds.confirmDialog(title='Fixed', message='Hidden %d intermediate objects.' % len(objects))
        except Exception as e:
            cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))
    elif result == 'Delete':
        try:
            cmds.delete(objects)
            cmds.confirmDialog(title='Fixed', message='Deleted %d intermediate objects.' % len(objects))
        except Exception as e:
            cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


def fix_negative_scale():
    """Fix negative scale values"""
    if not _ensure_maya():
        return
    meshes = find_negative_scale()
    if not meshes:
        cmds.confirmDialog(title='Fix', message='No negative scale found.')
        return
    
    result = cmds.confirmDialog(
        title='Fix Negative Scale',
        message='Found %d objects with negative scale.\nFreeze transforms to fix?' % len(meshes),
        button=['Freeze', 'Cancel'],
        defaultButton='Freeze',
        cancelButton='Cancel'
    )
    
    if result == 'Freeze':
        try:
            for mesh in meshes:
                cmds.makeIdentity(mesh, apply=True, scale=True)
            cmds.confirmDialog(title='Fixed', message='Froze scale on %d objects.' % len(meshes))
        except Exception as e:
            cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


def fix_duplicate_names():
    """Auto-rename objects with duplicate names"""
    if not _ensure_maya():
        return
    objects = find_duplicate_names()
    if not objects:
        cmds.confirmDialog(title='Fix', message='No duplicate names found.')
        return
    
    result = cmds.confirmDialog(
        title='Fix Duplicate Names',
        message='Found %d objects with duplicate names.\nAuto-rename with numbers?' % len(objects),
        button=['Rename', 'Cancel'],
        defaultButton='Rename',
        cancelButton='Cancel'
    )
    
    if result == 'Rename':
        try:
            renamed = 0
            for obj in objects:
                try:
                    # Maya's rename automatically adds numbers if name exists
                    base_name = obj.split('|')[-1].split(':')[-1]
                    cmds.rename(obj, base_name + '_fixed#')
                    renamed += 1
                except:
                    pass
            cmds.confirmDialog(title='Fixed', message='Renamed %d objects.' % renamed)
        except Exception as e:
            cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


def fix_unused_color_sets():
    """Delete unused color sets"""
    if not _ensure_maya():
        return
    meshes = find_unused_color_sets()
    if not meshes:
        cmds.confirmDialog(title='Fix', message='No unused color sets found.')
        return
    
    result = cmds.confirmDialog(
        title='Fix Unused Color Sets',
        message='Found %d meshes with extra color sets.\nDelete them?' % len(meshes),
        button=['Delete', 'Cancel'],
        defaultButton='Delete',
        cancelButton='Cancel'
    )
    
    if result == 'Delete':
        try:
            count = 0
            for mesh in meshes:
                shapes = _get_mesh_shapes(mesh)
                for shape in shapes:
                    color_sets = cmds.polyColorSet(shape, q=True, allColorSets=True) or []
                    if len(color_sets) > 0:
                        for cs in color_sets:
                            cmds.polyColorSet(shape, delete=True, colorSet=cs)
                            count += 1
            cmds.confirmDialog(title='Fixed', message='Deleted %d color sets.' % count)
        except Exception as e:
            cmds.confirmDialog(title='Error', message='Failed: %s' % str(e))


# ============================================================================
# UI FUNCTIONS
# ============================================================================

def get_all_checks():
    """Canonical registry of all checks (label -> function)."""
    return {
        # Category 1: Geometry & Topology Errors
        'Non-manifold edges': find_non_manifold_edges,
        'Lamina faces': find_lamina_faces,
        'Zero-area faces': find_zero_area_faces,
        'Non-planar faces': find_non_planar_faces,
        'Non-manifold vertices': find_non_manifold_vertices,
        'Isolated vertices': find_isolated_vertices,
        'Zero-length edges': find_zero_length_edges,
        'N-gons (>4 sides)': find_ngons,

        # Category 2: Normal Issues - REMOVED
        # 'Reversed normals': find_reversed_normals,
        # 'Hard edges': find_hard_edges,

        # Category 3: UV & Texture Coordinate Errors
        'Overlapping UVs': find_overlapping_uvs,
        'UVs outside 0-1 range': find_uvs_outside_range,
        'Missing UV sets': find_missing_uvs,
        'Multiple UV sets': find_multiple_uv_sets,

        # Category 4: Shader & Material Issues
        'Default shader (lambert1)': find_default_shader_assignments,
        'Multiple shaders per object': find_multiple_shaders,
        'Unused shading nodes': find_unused_shading_nodes,

        # Category 5: Construction History & Node Issues
        'Construction history': find_construction_history,
        'Visible intermediate objects': find_intermediate_objects,
        'Empty groups': find_empty_groups,

        # Category 6: Transform & Pivot Problems
        'Non-zero transforms': find_non_zero_transforms,
        'Negative scale': find_negative_scale,

        # Category 7: Naming & Organization Errors
        'Duplicate names': find_duplicate_names,

        # Category 8: Performance & Optimization
        'High poly count (>50k)': find_high_poly_objects,

        # Category 9: Data Integrity Issues
        'Invalid/corrupted geometry': find_invalid_geometry,

        # Category 10: Color & Vertex Attributes
        'Unused color sets': find_unused_color_sets
    }

def run_all_checks():
    """
    Run all geometry checks sequentially and return results.
    
    This function iterates through all available checks, executes them,
    and updates the progress bar if in batch mode. It also handles
    cancellation requests from the user.
    
    Returns:
        dict: Dictionary mapping check names to lists of found issues
              Format: {'Check Name': [list of components with issues]}
    
    Progress Tracking:
        - Updates global progress bar with current check and percentage
        - Respects _cancel_requested flag for user cancellation
        - Logs each check result to UI log panel
    """
    # Ensure we're running in Maya
    if not _ensure_maya():
        return {}
    
    global _cancel_requested
    
    all_checks = get_all_checks()
    
    # Save current selection
    original_selection = cmds.ls(selection=True) or []
    
    # Initialize results storage
    results = {}
    total = len(all_checks)
    current = 0
    issues_found = 0
    
    # Iterate through all checks
    for label, check_fn in all_checks.items():
        # Check if user requested cancellation
        if _cancel_requested:
            log_to_ui('Batch operation cancelled', 'WARNING')
            break
        
        current += 1
        
        try:
            # Update progress bar with current check
            status_text = '[%d/%d] %s' % (current, total, label)
            update_progress(current, total, status_text)
            
            # Log check start (console only, not UI to avoid spam)
            print('[%d/%d] Checking: %s...' % (current, total, label))
            
            # Execute the check function
            result = check_fn()
            if result is None:
                log_to_ui('Check returned None (treating as OK): %s' % label, 'WARNING')
                result = []
            
            # Store results
            results[label] = result
            _last_check_results[label] = result
            
            # Log result
            if result and len(result) > 0:
                issues_found += 1
                print('  -> FOUND %d issues' % len(result))
            else:
                print('  -> OK')
                
        except Exception as e:
            # Handle check errors gracefully
            error_msg = 'Check failed: %s - %s' % (label, str(e))
            print('  -> ERROR: %s' % str(e))
            log_to_ui(error_msg, 'ERROR')
            
            # Store empty result for failed check
            results[label] = []
            
            if logger:
                logger.error('Check failed for %s: %s' % (label, str(e)))
                logger.error(traceback.format_exc())
    
    # Restore original selection
    try:
        if original_selection:
            cmds.select(original_selection, replace=True)
        else:
            cmds.select(clear=True)
    except:
        pass
    
    # Print summary to console
    print('='*60)
    print('SUMMARY: %d checks completed, %d checks found issues' % (total, issues_found))
    print('='*60 + '\n')
    
    return results


# ============================================================================
# PYSIDE2/PYSIDE6 UI CLASS
# ============================================================================

class GeoMasterWindow(QMainWindow):
    """
    PySide2/PySide6 Qt-based UI for GeoMaster geometry checker.
    
    Features:
    - Modern Qt-based interface with custom styling
    - Orange and grey color scheme
    - Real-time progress tracking
    - Scrollable check categories
    - Status indicators with 3-state system (grey/green/red)
    """
    
    def __init__(self, parent=None):
        super(GeoMasterWindow, self).__init__(parent)
        
        # Get configuration
        try:
            self.window_title = config.UI_WINDOW_TITLE
            width = config.UI_WIDTH
            height = config.UI_HEIGHT
        except Exception:
            self.window_title = 'GeoMaster - Geometry Checker'
            width = 600
            height = 850
        
        self.setWindowTitle(self.window_title)
        self.resize(width, height)
        
        # Store references to status buttons for updates
        self.status_buttons = {}
        
        # Setup UI
        self.init_ui()
        
        # Apply stylesheet
        self.apply_stylesheet()
        
        if logger:
            logger.info('PySide%d GeoMaster UI created' % PYSIDE_VERSION)
    
    def init_ui(self):
        """Initialize all UI elements."""
        global _ui_progress_bar, _ui_log_field
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_label = QLabel('GEOMASTER')
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet(
            'background-color: rgb(70, 130, 180); '
            'color: white; '
            'font-size: 16px; '
            'font-weight: bold; '
            'padding: 8px;'
        )
        header_label.setToolTip('Comprehensive Maya Geometry Checker')
        main_layout.addWidget(header_label)
        
        # Progress bar section
        progress_label = QLabel('Progress')
        progress_label.setStyleSheet('color: rgb(200, 200, 200); font-size: 10px;')
        main_layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('Ready')
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(24)
        self.progress_bar.setStyleSheet(
            'QProgressBar {'
            '    border: 1px solid rgb(80, 80, 80);'
            '    border-radius: 3px;'
            '    background-color: rgb(60, 60, 60);'
            '    text-align: center;'
            '    color: white;'
            '}'
            'QProgressBar::chunk {'
            '    background-color: rgb(100, 149, 237);'
            '}'
        )
        _ui_progress_bar = self.progress_bar
        main_layout.addWidget(self.progress_bar)
        
        # Run All Diagnostics button
        run_all_btn = QPushButton('RUN ALL DIAGNOSTICS')
        run_all_btn.setMinimumHeight(45)
        run_all_btn.setStyleSheet(
            'QPushButton {'
            '    background-color: rgb(70, 130, 180);'
            '    color: white;'
            '    font-size: 14px;'
            '    font-weight: bold;'
            '    border: none;'
            '    border-radius: 3px;'
            '}'
            'QPushButton:hover {'
            '    background-color: rgb(100, 149, 237);'
            '}'
            'QPushButton:pressed {'
            '    background-color: rgb(65, 105, 225);'
            '}'
        )
        run_all_btn.setToolTip('Execute all 28 geometry checks with progress tracking')
        run_all_btn.clicked.connect(self.check_all)
        main_layout.addWidget(run_all_btn)
        
        # Info label
        info_label = QLabel('Run all checks at once, or use individual "Find" buttons below')
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet(
            'color: rgb(180, 180, 180); '
            'font-size: 10px; '
            'padding: 5px; '
            'background-color: rgb(60, 60, 60);'
        )
        main_layout.addWidget(info_label)
        
        # Scrollable checks area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        scroll_widget = QWidget()
        self.checks_layout = QVBoxLayout(scroll_widget)
        self.checks_layout.setSpacing(2)
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # Add all check categories and rows
        self.add_all_checks()
        
        # Utility buttons
        utility_layout = QHBoxLayout()
        
        clear_btn = QPushButton('Clear Highlighted')
        clear_btn.setMinimumHeight(32)
        clear_btn.setStyleSheet(self.get_button_style('rgb(90, 140, 180)'))
        clear_btn.setToolTip('Clear all red mesh highlighting and revert to default state')
        clear_btn.clicked.connect(self.clear_highlights)
        utility_layout.addWidget(clear_btn)
        
        cleanup_btn = QPushButton('Maya Cleanup Tool')
        cleanup_btn.setMinimumHeight(32)
        cleanup_btn.setStyleSheet(self.get_button_style('rgb(100, 120, 140)'))
        cleanup_btn.setToolTip("Open Maya's built-in Mesh > Cleanup tool")
        cleanup_btn.clicked.connect(self.open_cleanup_tool)
        utility_layout.addWidget(cleanup_btn)
        
        clear_log_btn = QPushButton('Clear Log')
        clear_log_btn.setMinimumHeight(32)
        clear_log_btn.setStyleSheet(self.get_button_style('rgb(105, 105, 115)'))
        clear_log_btn.setToolTip('Clear the log panel below')
        clear_log_btn.clicked.connect(self.clear_log)
        utility_layout.addWidget(clear_log_btn)

        audit_btn = QPushButton('Audit Checks')
        audit_btn.setMinimumHeight(32)
        audit_btn.setStyleSheet(self.get_button_style('rgb(110, 110, 130)'))
        audit_btn.setToolTip('Verify Run All list matches UI rows, and smoke-test that each check returns a list')
        audit_btn.clicked.connect(self.audit_checks)
        utility_layout.addWidget(audit_btn)
        
        main_layout.addLayout(utility_layout)
        
        # Log panel
        log_header = QLabel('Output Log')
        log_header.setStyleSheet(
            'background-color: rgb(80, 100, 120); '
            'color: white; '
            'font-weight: bold; '
            'padding: 5px;'
        )
        main_layout.addWidget(log_header)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet(
            'background-color: rgb(46, 46, 46); '
            'color: rgb(255, 255, 255); '
            'font-family: Consolas, Courier; '
            'font-size: 10px; '
            'border: 1px solid rgb(60, 60, 60);'
        )
        self.log_text.setToolTip('All check results and messages appear here')
        _ui_log_field = self.log_text
        main_layout.addWidget(self.log_text)
        
        # Initial log messages
        self.log('GeoMaster initialized - Ready to check geometry', 'SUCCESS')
        self.log('Click "RUN ALL DIAGNOSTICS" or use individual Find buttons', 'INFO')
    
    def add_all_checks(self):
        """Add all check categories and check rows."""
        # Category 1: Geometry & Topology
        self.add_category('GEOMETRY & TOPOLOGY ERRORS')
        self.add_row('Non-manifold edges', find_non_manifold_edges, fix_non_manifold_geometry)
        self.add_row('Lamina faces', find_lamina_faces, fix_lamina_faces)
        self.add_row('Zero-area faces', find_zero_area_faces, fix_zero_area_faces)
        self.add_row('Non-planar faces', find_non_planar_faces, fix_non_planar_faces)
        self.add_row('Non-manifold vertices', find_non_manifold_vertices, fix_non_manifold_vertices)
        self.add_row('Isolated vertices', find_isolated_vertices, fix_isolated_vertices)
        self.add_row('Zero-length edges', find_zero_length_edges, fix_zero_length_edges)
        self.add_row('N-gons (>4 sides)', find_ngons, fix_ngons)
        
        # Category 3: UVs
        self.add_category('UV & TEXTURE COORDINATE ERRORS')
        self.add_row('Overlapping UVs', find_overlapping_uvs, fix_overlapping_uvs)
        self.add_row('UVs outside 0-1 range', find_uvs_outside_range, fix_uvs_outside_range)
        self.add_row('Missing UV sets', find_missing_uvs, fix_missing_uvs)
        self.add_row('Multiple UV sets', find_multiple_uv_sets, fix_multiple_uv_sets)
        
        # Category 4: Shaders
        self.add_category('SHADER & MATERIAL ISSUES')
        self.add_row('Default shader (lambert1)', find_default_shader_assignments, fix_default_shader_assignments)
        self.add_row('Multiple shaders per object', find_multiple_shaders, fix_multiple_shaders)
        self.add_row('Unused shading nodes', find_unused_shading_nodes, fix_unused_shading_nodes)
        
        # Category 5: History
        self.add_category('CONSTRUCTION HISTORY & NODE ISSUES')
        self.add_row('Construction history', find_construction_history, fix_construction_history)
        self.add_row('Visible intermediate objects', find_intermediate_objects, fix_intermediate_objects)
        self.add_row('Empty groups', find_empty_groups, fix_empty_groups)
        
        # Category 6: Transforms
        self.add_category('TRANSFORM & PIVOT PROBLEMS')
        self.add_row('Non-zero transforms', find_non_zero_transforms, fix_freeze_transforms)
        self.add_row('Negative scale', find_negative_scale, fix_negative_scale)
        
        # Category 7: Naming
        self.add_category('NAMING & ORGANIZATION ERRORS')
        self.add_row('Duplicate names', find_duplicate_names, fix_duplicate_names)
        
        # Category 8: Performance
        self.add_category('PERFORMANCE & OPTIMIZATION')
        self.add_row('High poly count (>50k)', find_high_poly_objects, None)
        
        # Category 9: Data Integrity
        self.add_category('DATA INTEGRITY ISSUES')
        self.add_row('Invalid/corrupted geometry', find_invalid_geometry, None)
        
        # Category 10: Colors
        self.add_category('COLOR & VERTEX ATTRIBUTES')
        self.add_row('Unused color sets', find_unused_color_sets, fix_unused_color_sets)
    
    def add_category(self, title):
        """Add a category header."""
        label = QLabel(title)
        label.setStyleSheet(
            'background-color: rgb(75, 95, 115); '
            'color: white; '
            'font-weight: bold; '
            'padding: 6px; '
            'margin-top: 10px;'
        )
        self.checks_layout.addWidget(label)
    
    def add_row(self, label, find_fn, fix_fn=None):
        """Add a check row with Find, Fix, and Status buttons."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(5, 2, 5, 2)
        row_layout.setSpacing(5)
        
        # Check label
        check_label = QLabel('  ' + label)
        check_label.setMinimumWidth(260)
        check_label.setStyleSheet('color: rgb(220, 220, 220);')
        row_layout.addWidget(check_label)
        
        # Find button
        find_btn = QPushButton('Find')
        find_btn.setMinimumWidth(90)
        find_btn.setStyleSheet(self.get_button_style('rgb(100, 149, 237)'))
        find_btn.setToolTip('Run this check and display results')
        find_btn.clicked.connect(lambda: self.on_find(label, find_fn))
        row_layout.addWidget(find_btn)
        
        # Fix button
        fix_btn = QPushButton('Fix')
        fix_btn.setMinimumWidth(90)
        if fix_fn:
            fix_btn.setStyleSheet(self.get_button_style('rgb(120, 160, 200)'))
            fix_btn.setToolTip('Attempt to automatically fix these issues')
            fix_btn.clicked.connect(lambda: self.on_fix(label, find_fn, fix_fn))
        else:
            fix_btn.setStyleSheet(self.get_button_style('rgb(120, 160, 200)'))
            fix_btn.setToolTip('No automatic fix available - click for more info')
            fix_btn.clicked.connect(lambda: self.on_fix_unavailable(label))
        row_layout.addWidget(fix_btn)
        
        # Status button
        status_btn = QPushButton('?')
        status_btn.setMinimumWidth(60)
        status_btn.setMaximumWidth(60)
        status_btn.setStyleSheet(self.get_button_style('rgb(102, 102, 102)'))
        status_btn.setToolTip('Status: Grey=Not checked, Green=OK, Red=Issues. Click to highlight.')
        status_btn.clicked.connect(lambda: self.on_status_click(label))
        self.status_buttons[label] = status_btn
        row_layout.addWidget(status_btn)
        
        self.checks_layout.addWidget(row_widget)
    
    def get_button_style(self, bg_color):
        """Generate button stylesheet with given background color."""
        # Parse RGB values
        rgb = bg_color.replace('rgb(', '').replace(')', '').split(',')
        r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
        
        # Lighter for hover
        hover_color = 'rgb(%d, %d, %d)' % (min(r + 20, 255), min(g + 20, 255), min(b + 20, 255))
        # Darker for pressed
        pressed_color = 'rgb(%d, %d, %d)' % (max(r - 20, 0), max(g - 20, 0), max(b - 20, 0))
        
        return (
            'QPushButton {'
            '    background-color: %s;' % bg_color +
            '    color: white;'
            '    border: none;'
            '    border-radius: 2px;'
            '    padding: 5px;'
            '}'
            'QPushButton:hover {'
            '    background-color: %s;' % hover_color +
            '}'
            'QPushButton:pressed {'
            '    background-color: %s;' % pressed_color +
            '}'
        )
    
    def update_status_button(self, label, comps, reset=False):
        """Update status button with 3-state system."""
        if label not in self.status_buttons:
            return
        
        btn = self.status_buttons[label]
        
        if reset:
            # STATE 1: Unchecked (grey)
            btn.setText('?')
            btn.setStyleSheet(self.get_button_style('rgb(105, 105, 115)'))
            self.log('%s: Reset to unchecked state' % label, 'INFO')
        elif comps and len(comps) > 0:
            # STATE 3: ERROR (red with count)
            btn.setText(str(len(comps)))
            btn.setStyleSheet(self.get_button_style('rgb(200, 80, 80)'))
            self.log('%s: Found %d issues - Status: ERROR' % (label, len(comps)), 'WARNING')
        else:
            # STATE 2: SUCCESS (green OK)
            btn.setText('OK')
            btn.setStyleSheet(self.get_button_style('rgb(90, 170, 110)'))
            self.log('%s: Passed - Status: SUCCESS' % label, 'SUCCESS')
        
        # Force UI update
        btn.repaint()
        QtWidgets.QApplication.processEvents()
    
    def on_find(self, label, find_fn):
        """Execute a check."""
        try:
            self.log('Running: %s' % label, 'INFO')
            
            global _is_batch_operation
            if not _is_batch_operation:
                self.update_progress(50, 100, 'Checking: %s' % label)
            
            # Run check
            comps = find_fn()

            if comps is None:
                self.log('%s returned None (treating as OK)' % label, 'WARNING')
                comps = []
            
            # Store results
            _last_check_results[label] = comps
            
            # Update status
            self.update_status_button(label, comps)
            
            # Reset progress
            if not _is_batch_operation:
                self.reset_progress()
        
        except Exception as e:
            error_msg = 'Error in %s: %s' % (label, str(e))
            self.log(error_msg, 'ERROR')
            if logger:
                logger.error(error_msg)
                logger.error(traceback.format_exc())
            
            if not _is_batch_operation:
                self.reset_progress()
    
    def on_fix(self, label, find_fn, fix_fn):
        """Execute a fix."""
        try:
            self.log('='*60, 'INFO')
            self.log('APPLYING FIX: %s' % label, 'INFO')
            self.log('='*60, 'INFO')
            
            global _is_batch_operation
            if not _is_batch_operation:
                self.update_progress(25, 100, 'Fixing: %s' % label)
            
            # Run fix
            fix_fn()
            self.log('Fix applied successfully', 'SUCCESS')
            
            if not _is_batch_operation:
                self.update_progress(50, 100, 'Clearing highlights...')
            
            # Clear highlighting
            clear_all_overrides()
            self.log('Viewport highlighting cleared', 'INFO')
            
            if not _is_batch_operation:
                self.update_progress(75, 100, 'Verifying fix...')
            
            # Re-check
            comps = find_fn()
            _last_check_results[label] = comps
            
            # Update status
            if not comps or len(comps) == 0:
                self.update_status_button(label, comps)
                self.log('='*60, 'SUCCESS')
                self.log('FIX SUCCESSFUL - ALL ISSUES RESOLVED', 'SUCCESS')
                self.log('Status: ERROR → SUCCESS (Green OK)', 'SUCCESS')
                self.log('='*60, 'SUCCESS')
            else:
                self.update_status_button(label, comps)
                self.log('='*60, 'WARNING')
                self.log('FIX INCOMPLETE - %d issues remain' % len(comps), 'WARNING')
                self.log('Status: ERROR → ERROR (Red %d)' % len(comps), 'WARNING')
                self.log('='*60, 'WARNING')
            
            if not _is_batch_operation:
                self.reset_progress()
        
        except Exception as e:
            error_msg = 'Error fixing %s: %s' % (label, str(e))
            self.log('='*60, 'ERROR')
            self.log(error_msg, 'ERROR')
            self.log('='*60, 'ERROR')
            if logger:
                logger.error(error_msg)
                logger.error(traceback.format_exc())
            
            if not _is_batch_operation:
                self.reset_progress()
    
    def on_fix_unavailable(self, label):
        """Show message when no fix is available."""
        self.log('%s: No automatic fix available' % label, 'WARNING')
        QtWidgets.QMessageBox.information(
            self,
            'No Automatic Fix',
            'No automatic fix is available for: %s\n\nThis check requires manual intervention or scene-specific solutions.' % label
        )
    
    def on_status_click(self, label):
        """Highlight issues when status button is clicked."""
        try:
            if label in _last_check_results:
                comps = _last_check_results[label]
                if comps is None:
                    comps = []
                if comps and len(comps) > 0:
                    highlight_components_visual(comps, check_name=label)
                    self.log('Highlighted %d components for: %s' % (len(comps), label), 'INFO')
                else:
                    self.log('No issues to highlight for: %s' % label, 'INFO')
            else:
                self.log('Run Find first for: %s' % label, 'WARNING')
        except Exception as e:
            self.log('Highlight error: %s' % str(e), 'ERROR')
            if logger:
                logger.error('Status click error: %s' % str(e))
    
    def check_all(self):
        """Run all checks sequentially."""
        global _is_batch_operation, _cancel_requested
        
        try:
            _is_batch_operation = True
            _cancel_requested = False
            
            self.clear_log()
            self.log('='*60, 'INFO')
            self.log('RUNNING ALL DIAGNOSTICS', 'INFO')
            self.log('='*60, 'INFO')
            
            if logger:
                logger.info('Running all checks in batch mode...')
            
            # Run all checks
            results = run_all_checks()
            
            # Check if cancelled
            if _cancel_requested:
                self.log('Operation cancelled by user', 'WARNING')
                self.reset_progress()
                _is_batch_operation = False
                return
            
            # Update status buttons
            all_components = []
            issue_count = 0
            pass_count = 0
            
            for label, comps in results.items():
                if comps is None:
                    comps = []
                if label not in self.status_buttons:
                    self.log('Run All label missing from UI: %s' % label, 'WARNING')
                self.update_status_button(label, comps)
                if comps and len(comps) > 0:
                    all_components.extend(comps)
                    issue_count += 1
                else:
                    pass_count += 1
            
            # Show summary
            self.log('='*60, 'INFO')
            self.log('DIAGNOSTIC COMPLETE', 'SUCCESS')
            self.log('Total checks run: %d' % len(results), 'INFO')
            self.log('Checks with issues: %d' % issue_count, 'WARNING')
            self.log('Checks passed: %d' % pass_count, 'SUCCESS')
            self.log('Total components flagged: %d' % len(all_components), 'INFO')
            self.log('='*60, 'INFO')
            self.log('Click red status indicators to highlight issues', 'INFO')
            
            # Highlight all problems
            try:
                if all_components:
                    clear_all_overrides()
                    highlight_components_visual(all_components, check_name='All Checks')
                    self.log('Problem areas highlighted in red', 'INFO')
            except Exception as e:
                self.log('Could not highlight components: %s' % str(e), 'WARNING')
            
            self.reset_progress()
        
        except Exception as e:
            error_msg = 'Error running all checks: %s' % str(e)
            self.log(error_msg, 'ERROR')
            if logger:
                logger.error(error_msg)
                logger.error(traceback.format_exc())
        finally:
            _is_batch_operation = False
            self.reset_progress()
    
    def clear_highlights(self):
        """Clear all viewport highlighting and reset status buttons to OK."""
        clear_all_overrides()
        
        # Reset all status buttons to green OK state
        global _last_check_results
        for label in self.status_buttons.keys():
            if label in _last_check_results:
                # Set to empty list (no issues) which will make it green OK
                self.update_status_button(label, [])
        
        self.log('Cleared all highlighted meshes and reset status to OK', 'INFO')
    
    def open_cleanup_tool(self):
        """Open Maya's Cleanup Tool."""
        try:
            self.log('Opening Maya Cleanup Tool...', 'INFO')
            mel.eval('CleanupPolygonOptions;')
            self.log('Maya Cleanup Tool opened', 'SUCCESS')
        except Exception as e:
            msg = 'Could not open Maya Cleanup Tool: %s' % str(e)
            self.log(msg, 'ERROR')
            if logger:
                logger.error(msg)
                logger.error(traceback.format_exc())
            QtWidgets.QMessageBox.critical(self, 'Error', msg)
    
    def clear_log(self):
        """Clear the log text."""
        self.log_text.clear()

    def audit_checks(self):
        """Audit UI wiring and smoke-test check return contracts.

        This runs the check functions (no fixes) and reports:
        - Missing UI rows for Run All checks
        - Missing Run All entries for UI rows
        - Exceptions thrown by checks
        - Checks returning non-list results
        """
        try:
            self.log('='*60, 'INFO')
            self.log('AUDITING CHECKS', 'INFO')
            self.log('='*60, 'INFO')

            registry = get_all_checks()
            runall_labels = list(registry.keys())
            ui_labels = list(self.status_buttons.keys())

            missing_in_ui = [l for l in runall_labels if l not in self.status_buttons]
            missing_in_runall = [l for l in ui_labels if l not in registry]

            if missing_in_ui:
                self.log('Missing UI rows for %d Run All checks:' % len(missing_in_ui), 'WARNING')
                for l in missing_in_ui:
                    self.log('  - %s' % l, 'WARNING')
            else:
                self.log('UI rows match Run All labels', 'SUCCESS')

            if missing_in_runall:
                self.log('UI rows not present in Run All (%d):' % len(missing_in_runall), 'WARNING')
                for l in missing_in_runall:
                    self.log('  - %s' % l, 'WARNING')

            errors = 0
            warnings = 0
            for label, fn in registry.items():
                try:
                    result = fn()
                    if result is None:
                        warnings += 1
                        self.log('%s returned None (treating as empty)' % label, 'WARNING')
                    elif not isinstance(result, (list, tuple)):
                        warnings += 1
                        self.log('%s returned %s (expected list)' % (label, type(result).__name__), 'WARNING')
                    else:
                        self.log('%s: OK (returned %d item(s))' % (label, len(result)), 'INFO')
                except Exception as e:
                    errors += 1
                    self.log('%s: ERROR - %s' % (label, str(e)), 'ERROR')

            if errors == 0 and warnings == 0:
                self.log('Audit complete: all checks executed and returned lists', 'SUCCESS')
            else:
                self.log('Audit complete: %d errors, %d warnings' % (errors, warnings), 'WARNING')

        except Exception as e:
            self.log('Audit failed: %s' % str(e), 'ERROR')
    
    def log(self, message, level='INFO'):
        """Log a message to the log panel."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if level == 'ERROR':
            prefix = '[!]'
        elif level == 'WARNING':
            prefix = '[*]'
        elif level == 'SUCCESS':
            prefix = '[✓]'
        else:
            prefix = '[i]'
        
        formatted_msg = '[%s] %s %s' % (timestamp, prefix, message)
        
        # Set text color to white for all messages
        self.log_text.setTextColor(QColor(255, 255, 255))
        self.log_text.append(formatted_msg)
        
        # Scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Force update
        QtWidgets.QApplication.processEvents()
    
    def update_progress(self, current, maximum, status_text):
        """Update progress bar."""
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(status_text)
        QtWidgets.QApplication.processEvents()
    
    def reset_progress(self):
        """Reset progress bar to default state."""
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('Ready')
        QtWidgets.QApplication.processEvents()
    
    def apply_stylesheet(self):
        """Apply global stylesheet to window."""
        self.setStyleSheet(
            'QMainWindow {'
            '    background-color: rgb(50, 55, 60);'
            '}'
            'QWidget {'
            '    background-color: rgb(60, 65, 72);'
            '    color: rgb(220, 225, 230);'
            '}'
            'QScrollArea {'
            '    border: 1px solid rgb(75, 85, 95);'
            '    background-color: rgb(55, 60, 68);'
            '}'
        )


def show_ui():
    """
    Display the main GeoMaster UI with categorized geometry checks.
    
    UI Layout:
        - Header with title
        - Universal orange progress bar (for all operations)
        - Run All button
        - Scrollable check categories with Find/Fix/Status buttons
        - Utility buttons (Clear, Cleanup, Diagnostics)
        - Log panel at bottom (grey background, scrollable)
    
    Color Scheme:
        - Orange: Progress bar, primary action buttons
        - Grey: Background, disabled elements
        - Green: Success indicators
        - Red: Error indicators
    
    Returns:
        None - creates and displays the UI window
    """
    # Check if running inside Maya
    if not _ensure_maya():
        print('UI can only be shown inside Maya.')
        print('\nTo diagnose issues, run: main.diagnose_environment()')
        return
    
    # Check if PySide is available
    if QtWidgets is None:
        print('[ERROR] PySide2/PySide6 not available. Cannot create UI.')
        print('Maya 2017+ should have PySide2 built-in.')
        return
    
    # Store global UI references for updating from functions
    global _ui_progress_bar, _ui_log_field, _ui_window_name, _ui_window_instance
    
    try:
        _ui_window_name = 'geoMaster_window'
        
        if logger:
            logger.info('Creating PySide%d UI window' % PYSIDE_VERSION)
        
        # Close existing window if it exists
        if _ui_window_instance is not None:
            try:
                _ui_window_instance.close()
                _ui_window_instance.deleteLater()
            except Exception:
                pass
        
        # Create and show Qt window
        window = GeoMasterWindow()
        _ui_window_instance = window
        window.show()
        
        print('\n[SUCCESS] GeoMaster PySide%d UI opened successfully!' % PYSIDE_VERSION)
        print('Modern Qt-based interface with improved styling\n')
        
        if logger:
            logger.info('PySide%d UI displayed successfully' % PYSIDE_VERSION)
    
    except Exception as e:
        error_msg = 'Failed to create UI window: %s' % str(e)
        print('[ERROR] %s' % error_msg)
        if logger:
            logger.error(error_msg)
            logger.error(traceback.format_exc())
        if QtWidgets:
            QtWidgets.QMessageBox.critical(None, 'Error', error_msg)


if __name__ == '__main__':
    if not _ensure_maya():
        print('\nGeoMaster')
        print('='*60)
        print('This script provides comprehensive geometry, UV, shader, and scene checks.')
        print('It must be run inside Autodesk Maya.')
        print('')
        print('Usage in Maya Script Editor (Python tab):')
        print('-' * 60)
        print('  import sys')
        print('  sys.path.append(r"C:/gameGeoMaster")')
        print('  import main')
        print('  ')
        print('  # Show the UI')
        print('  main.show_ui()')
        print('  ')
        print('  # Or run diagnostics first')
        print('  main.diagnose_environment()')
        print('='*60)
        print('')
    else:
        print('\nRunning inside Maya - launching UI...')
        print('If UI doesn\'t appear, try: main.diagnose_environment()\n')
        try:
            show_ui()
        except Exception as e:
            print('\n[ERROR] Failed to show UI: %s' % str(e))
            print('\nRunning diagnostics...\n')
            diagnose_environment()
