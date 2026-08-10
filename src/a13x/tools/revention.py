"""
Revention Autosave

Maya script — autosave as Maya ASCII every N minutes with versioned filenames.

Usage (Maya Script Editor, Python):
    import revention_autosave
    revention_autosave.show_ui()

Features:
- Clean Qt UI (PySide2/PySide) to set interval, choose suffix (RIG/LDV/MDL/GRM/SIM), base name.
- Uses regex to validate base filename: only letters, digits, underscore and hyphen.
- Saves as `base_SUFFIX_V###.ma` and automatically increments the ###.
- Uses a Qt QTimer parented to the window so it stops cleanly on exit.
- Adds a Maya scriptJob to stop autosave on `quitApplication`.

"""
from __future__ import print_function
import os
import re
import json
import logging
from datetime import datetime

try:
    import maya.cmds as cmds
    import maya.OpenMayaUI as omui
except ImportError:
    raise ImportError('This script must be run inside Autodesk Maya (maya.cmds required)')

# Setup logging
logger = logging.getLogger('Revention')
logger.setLevel(logging.INFO)

# PySide6 (Maya 2025+) first, then PySide2 (Maya 2022 and earlier), then the
# legacy PySide/shiboken (Maya 2016 and earlier) as a last resort - same
# auto-detect pattern GeoMaster uses.
try:
    from PySide6 import QtWidgets, QtCore
    from shiboken6 import wrapInstance
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore
        from shiboken2 import wrapInstance
    except ImportError:
        try:
            from PySide import QtGui as QtWidgets, QtCore
            from shiboken import wrapInstance
        except ImportError:
            raise ImportError('PySide6, PySide2, or PySide (with matching shiboken) is required')


def get_maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    if not ptr:
        return None
    return wrapInstance(int(ptr), QtWidgets.QWidget)


def increment_version_filename(directory, base, suffix):
    """Return next filename path like base_SUFFIX_V001.ma in directory.

    Uses regex to scan existing files and find the highest V### then returns next.
    """
    pattern = re.compile(r'^' + re.escape(base) + r'_' + re.escape(suffix) + r'_V(\d{3})\.ma$', re.IGNORECASE)
    max_num = 0
    try:
        for f in os.listdir(directory):
            m = pattern.match(f)
            if m:
                try:
                    n = int(m.group(1))
                    if n > max_num:
                        max_num = n
                except Exception:
                    continue
    except Exception:
        # directory may not exist or not readable
        max_num = 0

    next_num = max_num + 1
    filename = f"{base}_{suffix}_V{next_num:03d}.ma"
    return os.path.join(directory, filename)


class AutosaveWindow(QtWidgets.QDialog):
    WINDOW_TITLE = 'Revention Autosave'

    VALID_NAME_RE = re.compile(r'^[A-Za-z0-9_\-]+$')

    def __init__(self, parent=None):
        super(AutosaveWindow, self).__init__(parent or get_maya_main_window())
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setObjectName('reventionAutosaveWindow')
        self.setMinimumWidth(420)
        
        # Enable custom title bar by removing default frame
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self._script_job_id = None
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(False)
        # preferences save suppression flag
        self._suppress_save = False
        
        # For window dragging
        self._drag_pos = None
        
        # Version caching to avoid redundant file system scans
        self._cached_version = None
        self._cached_directory = None
        self._cached_base = None
        self._cached_suffix = None
        
        # Countdown timer for UI updates
        self._countdown_timer = QtCore.QTimer(self)
        self._countdown_timer.setSingleShot(False)
        self._countdown_timer.setInterval(1000)  # Update every second
        self._save_start_time = None
        
        # Last save info
        self._last_save_path = None
        self._last_save_time = None

        self.build_ui()
        self._timer.timeout.connect(self.on_autosave_timeout)
        self._countdown_timer.timeout.connect(self.update_countdown)

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Apply a blue-themed color scheme
        dark_style = '''
        QDialog, QWidget { background-color: #1a2332; color: #e8f0f7; }
        QLabel { color: #c8dae8; }
        QLineEdit, QComboBox, QSpinBox { background-color: #0d1b2a; color: #e8f0f7; border: 1px solid #2d4663; }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #4a90e2; }
        QFileDialog { background-color: #1a2332; color: #e8f0f7; }
        QPushButton { background-color: #2d4663; color: #e8f0f7; border: 1px solid #4a90e2; border-radius:4px; padding:6px; }
        QPushButton:hover { background-color: #3a5a7a; }
        QPushButton:pressed { background-color: #1f3347; }
        QPushButton:disabled { background-color: #1a2a3a; color: #6a7a8a; border: 1px solid #2a3a4a; }
        QScrollArea { background-color: transparent; }
        QToolTip { color: #e8f0f7; background-color: #2d4663; border: 1px solid #4a90e2; }
        '''
        try:
            self.setStyleSheet(dark_style)
        except Exception:
            pass

        # Custom title bar
        title_bar = QtWidgets.QWidget()
        title_bar.setFixedHeight(35)
        title_bar.setStyleSheet('background-color: #0d1b2a; border-bottom: 1px solid #4a90e2;')
        title_bar_layout = QtWidgets.QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(12, 0, 0, 0)
        title_bar_layout.setSpacing(0)
        
        # Title label
        self.title_label = QtWidgets.QLabel('Revention Autosave')
        self.title_label.setStyleSheet('color: #e8f0f7; font-weight: bold; border: none; padding: 0px 8px;')
        self.title_label.setMaximumWidth(300)
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch(1)
        
        # Minimize button styled like Windows
        self.minimize_btn = QtWidgets.QPushButton('_')
        self.minimize_btn.setFixedSize(46, 35)
        self.minimize_btn.setStyleSheet('''QPushButton { 
            background-color: transparent; 
            color: #e8f0f7; 
            border: none; 
            font-size: 16px; 
            font-weight: bold;
        }
        QPushButton:hover { background-color: #2d4663; }
        QPushButton:pressed { background-color: #1f3347; }''')
        title_bar_layout.addWidget(self.minimize_btn)
        
        # Close button styled like Windows
        self.close_btn = QtWidgets.QPushButton('X')
        self.close_btn.setFixedSize(46, 35)
        self.close_btn.setStyleSheet('''QPushButton { 
            background-color: transparent; 
            color: #e8f0f7; 
            border: none; 
            font-size: 20px; 
            font-weight: normal;
        }
        QPushButton:hover { background-color: #e81123; }
        QPushButton:pressed { background-color: #c50f1f; }''')
        title_bar_layout.addWidget(self.close_btn)
        
        layout.addWidget(title_bar)
        
        # Make title bar draggable
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move
        self.title_label.mousePressEvent = self.title_bar_mouse_press
        self.title_label.mouseMoveEvent = self.title_bar_mouse_move

        # Row: Base name
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel('Base name:'))
        self.base_edit = QtWidgets.QLineEdit()
        self.base_edit.setPlaceholderText('leave empty to use current scene name')
        row.addWidget(self.base_edit)
        layout.addLayout(row)

        # Row: Suffix dropdown
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel('Suffix:'))
        self.suffix_combo = QtWidgets.QComboBox()
        # Extended suffixes for character tech art workflows
        self.suffix_combo.addItems(['RIG', 'LDV', 'MDL', 'GRM', 'SIM', 'ANM', 'SKN', 'WGT', 'BLD'])
        row.addWidget(self.suffix_combo)
        layout.addLayout(row)

        # Row: Interval
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel('Interval (minutes):'))
        self.interval_spin = QtWidgets.QSpinBox()
        self.interval_spin.setMinimum(1)
        self.interval_spin.setMaximum(1440)
        self.interval_spin.setValue(15)
        row.addWidget(self.interval_spin)
        layout.addLayout(row)

        # Row: Custom save path
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel('Custom Path:'))
        self.custom_path_edit = QtWidgets.QLineEdit()
        self.custom_path_edit.setPlaceholderText('Optional — leave empty to use scene/project folders')
        row.addWidget(self.custom_path_edit)
        self.browse_btn = QtWidgets.QPushButton('Browse')
        row.addWidget(self.browse_btn)
        layout.addLayout(row)

        # Row: Validation label
        self.validation_label = QtWidgets.QLabel('Base name must match regex: [A-Za-z0-9_-]')
        layout.addWidget(self.validation_label)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton('Start Save')
        self.stop_btn = QtWidgets.QPushButton('Stop Save')
        self.stop_btn.setEnabled(False)

        # Buttons follow the blue theme
        btn_style = '''QPushButton { background-color: #2d4663; color: #e8f0f7; border: 1px solid #4a90e2; border-radius:4px; padding:6px; }
        QPushButton:hover { background-color: #3a5a7a; }
        QPushButton:disabled { background-color: #1a2a3a; color: #6a7a8a; border: 1px solid #2a3a4a; }'''
        self.start_btn.setStyleSheet(btn_style)
        self.stop_btn.setStyleSheet(btn_style)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        layout.addLayout(btn_row)

        # Preview and status
        self.preview_label = QtWidgets.QLabel('Preview: —')
        layout.addWidget(self.preview_label)
        
        self.status_label = QtWidgets.QLabel('Status: Stopped')
        layout.addWidget(self.status_label)
        
        # Countdown timer display
        self.countdown_label = QtWidgets.QLabel('Next save in: --:--')
        self.countdown_label.setStyleSheet('color: #4a90e2; font-weight: bold;')
        layout.addWidget(self.countdown_label)
        
        # Error display
        self.error_label = QtWidgets.QLabel('')
        self.error_label.setStyleSheet('color: #ff6b6b; font-weight: bold;')
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        
        # Last save info
        self.last_save_label = QtWidgets.QLabel('Last save: Never')
        self.last_save_label.setStyleSheet('color: #8ac926;')
        layout.addWidget(self.last_save_label)
        
        # Scene statistics (for tech art context)
        self.stats_label = QtWidgets.QLabel('Scene: —')
        self.stats_label.setStyleSheet('color: #c8dae8; font-size: 10px;')
        layout.addWidget(self.stats_label)
        self.update_scene_stats()

        # Connect
        self.start_btn.clicked.connect(self.start_autosave)
        self.stop_btn.clicked.connect(self.stop_autosave)
        self.minimize_btn.clicked.connect(self.showMinimized)
        self.close_btn.clicked.connect(self.close)
        self.browse_btn.clicked.connect(self.on_browse_path)
        self.base_edit.textChanged.connect(self.update_preview)
        # Persist important options when changed
        try:
            self.custom_path_edit.textChanged.connect(self.save_prefs)
        except Exception:
            pass
        try:
            self.suffix_combo.currentIndexChanged.connect(self.save_prefs)
        except Exception:
            pass
        try:
            self.interval_spin.valueChanged.connect(self.save_prefs)
        except Exception:
            pass
        self.suffix_combo.currentIndexChanged.connect(self.update_preview)
        self.interval_spin.valueChanged.connect(self.update_preview)

        self.update_preview()

        # Load preferences after UI is built (non-fatal)
        try:
            self.load_prefs()
        except Exception:
            pass

    def title_bar_mouse_press(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def title_bar_mouse_move(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
    
    def update_scene_stats(self):
        """Display scene statistics relevant to character tech art."""
        try:
            poly_count = len(cmds.ls(type='mesh') or [])
            joint_count = len(cmds.ls(type='joint') or [])
            skin_count = len(cmds.ls(type='skinCluster') or [])
            
            stats = f'Scene: {poly_count} meshes | {joint_count} joints | {skin_count} skin clusters'
            if hasattr(self, 'stats_label'):
                self.stats_label.setText(stats)
        except (RuntimeError, AttributeError) as e:
            if hasattr(self, 'stats_label'):
                self.stats_label.setText('Scene: Stats unavailable')
            logger.debug(f'Could not update scene stats: {e}')
    
    def show_error(self, msg):
        """Display error message in UI with auto-clear."""
        if hasattr(self, 'error_label'):
            self.error_label.setText(f'⚠ {msg}')
            logger.error(msg)
            # Auto-clear after 8 seconds
            QtCore.QTimer.singleShot(8000, lambda: self.error_label.setText(''))
    
    def show_success(self, msg):
        """Display success message in UI with auto-clear."""
        if hasattr(self, 'error_label'):
            self.error_label.setStyleSheet('color: #8ac926; font-weight: bold;')
            self.error_label.setText(f'✓ {msg}')
            logger.info(msg)
            # Auto-clear after 5 seconds and reset color
            def reset():
                if hasattr(self, 'error_label'):
                    self.error_label.setText('')
                    self.error_label.setStyleSheet('color: #ff6b6b; font-weight: bold;')
            QtCore.QTimer.singleShot(5000, reset)
    
    def update_countdown(self):
        """Update countdown timer display."""
        if not self._timer.isActive() or self._save_start_time is None:
            if hasattr(self, 'countdown_label'):
                self.countdown_label.setText('Next save in: --:--')
            return
        
        try:
            elapsed = (datetime.now() - self._save_start_time).total_seconds()
            interval_seconds = self.interval_spin.value() * 60
            remaining = max(0, interval_seconds - elapsed)
            
            mins, secs = divmod(int(remaining), 60)
            if hasattr(self, 'countdown_label'):
                self.countdown_label.setText(f'Next save in: {mins:02d}:{secs:02d}')
        except (RuntimeError, AttributeError) as e:
            logger.debug(f'Countdown update failed: {e}')

    def get_save_directory(self):
        """Get the save directory with environment variable expansion."""
        # If the user supplied a custom path in the UI, prefer it (expanded).
        try:
            custom = getattr(self, 'custom_path_edit', None)
            if custom:
                p = custom.text().strip()
                if p:
                    p = os.path.expandvars(os.path.expanduser(p))
                    return p
        except (RuntimeError, AttributeError) as e:
            logger.debug(f'Custom path retrieval failed: {e}')

        # Prefer current scene's directory, else project scenes folder
        try:
            scene = cmds.file(query=True, sceneName=True)
            if scene:
                return os.path.dirname(scene)
        except RuntimeError as e:
            logger.debug(f'Scene query failed: {e}')
        
        try:
            proj = cmds.workspace(query=True, rootDirectory=True)
            scenes_dir = os.path.join(proj, 'scenes')
            if os.path.exists(scenes_dir):
                return scenes_dir
            return proj
        except (RuntimeError, OSError) as e:
            logger.debug(f'Workspace query failed: {e}')
            return os.path.expanduser('~')
    
    def get_next_version(self, base, suffix, directory, force_refresh=False):
        """Get next version number with caching to avoid redundant file system scans."""
        # Check if we can use cached value
        if (not force_refresh and 
            self._cached_version is not None and
            self._cached_directory == directory and
            self._cached_base == base and
            self._cached_suffix == suffix):
            return self._cached_version
        
        # Scan directory for existing versions
        pattern = re.compile(r'^' + re.escape(base) + r'_' + re.escape(suffix) + r'_V(\d{3})\.ma$', re.IGNORECASE)
        max_num = 0
        try:
            if os.path.exists(directory):
                for f in os.listdir(directory):
                    m = pattern.match(f)
                    if m:
                        try:
                            n = int(m.group(1))
                            if n > max_num:
                                max_num = n
                        except ValueError:
                            continue
        except (OSError, IOError) as e:
            logger.warning(f'Could not scan directory {directory}: {e}')
            max_num = 0
        
        next_num = max_num + 1
        
        # Cache the result
        self._cached_version = next_num
        self._cached_directory = directory
        self._cached_base = base
        self._cached_suffix = suffix
        
        return next_num

    def on_browse_path(self):
        """Open a folder chooser dialog and set the custom path field."""
        try:
            initial = ''
            # prefer current value or scene dir
            cur = self.custom_path_edit.text().strip()
            if cur:
                initial = os.path.expandvars(os.path.expanduser(cur))
            else:
                try:
                    scene = cmds.file(query=True, sceneName=True)
                    if scene:
                        initial = os.path.dirname(scene)
                    else:
                        initial = cmds.workspace(query=True, rootDirectory=True)
                except RuntimeError:
                    initial = os.path.expanduser('~')

            folder = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Save Directory', initial)
            if folder:
                self.custom_path_edit.setText(folder)
                self._invalidate_version_cache()
                self.update_preview()
                self.save_prefs()
        except (RuntimeError, OSError) as e:
            self.show_error(f'Browse failed: {str(e)}')
            logger.error(f'Browse path failed: {e}')
    
    def _invalidate_version_cache(self):
        """Clear version cache when directory or parameters change."""
        self._cached_version = None
        self._cached_directory = None
        self._cached_base = None
        self._cached_suffix = None

    # Preferences persistence -------------------------------------------------
    def prefs_path(self):
        """Return full path to the prefs JSON file (per-user)."""
        try:
            # Maya user prefs directory via cmds.internalVar
            up = cmds.internalVar(userAppDir=True)
            return os.path.join(up, 'revention_autosave_prefs.json')
        except Exception:
            # fallback to home dir
            return os.path.join(os.path.expanduser('~'), 'revention_autosave_prefs.json')

    def load_prefs(self):
        """Load user preferences from JSON file."""
        path = self.prefs_path()
        if not os.path.exists(path):
            return
        try:
            self._suppress_save = True
            with open(path, 'r') as f:
                data = json.load(f)
            # set fields if present
            if 'custom_path' in data and getattr(self, 'custom_path_edit', None) is not None:
                self.custom_path_edit.setText(data.get('custom_path', ''))
            if 'suffix' in data and getattr(self, 'suffix_combo', None) is not None:
                suf = data.get('suffix')
                idx = self.suffix_combo.findText(suf)
                if idx >= 0:
                    self.suffix_combo.setCurrentIndex(idx)
            if 'interval' in data and getattr(self, 'interval_spin', None) is not None:
                try:
                    val = int(data.get('interval'))
                    self.interval_spin.setValue(val)
                except (ValueError, TypeError) as e:
                    logger.debug(f'Invalid interval value: {e}')
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f'Failed to load Revention Autosave prefs: {e}')
        finally:
            self._suppress_save = False

    def save_prefs(self):
        """Save user preferences to JSON file."""
        if getattr(self, '_suppress_save', False):
            return
        path = self.prefs_path()
        data = {}
        try:
            if getattr(self, 'custom_path_edit', None) is not None:
                data['custom_path'] = self.custom_path_edit.text().strip()
            if getattr(self, 'suffix_combo', None) is not None:
                data['suffix'] = self.suffix_combo.currentText()
            if getattr(self, 'interval_spin', None) is not None:
                data['interval'] = int(self.interval_spin.value())
            # ensure folder exists for prefs
            try:
                ddir = os.path.dirname(path)
                if ddir and not os.path.exists(ddir):
                    os.makedirs(ddir)
            except OSError as e:
                logger.warning(f'Could not create prefs directory: {e}')
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except (IOError, OSError) as e:
            logger.error(f'Failed to save Revention Autosave prefs: {e}')

    def build_preview_name(self):
        """Build preview filename using cached version lookup."""
        base = self.base_edit.text().strip()
        if not base:
            try:
                scene = cmds.file(query=True, sceneName=True)
                if scene and scene.strip():
                    base = os.path.splitext(os.path.basename(scene))[0]
                    # Ensure base is valid and not empty
                    if not base or not base.strip():
                        base = 'untitled'
                else:
                    base = 'untitled'
            except RuntimeError:
                base = 'untitled'

        suffix = self.suffix_combo.currentText()
        dirpath = self.get_save_directory()
        
        # Use cached version lookup
        next_ver = self.get_next_version(base, suffix, dirpath)
        candidate = f"{base}_{suffix}_V{next_ver:03d}.ma"
        return os.path.join(dirpath, candidate)

    def update_preview(self):
        """Update preview filename and validation status."""
        name = self.base_edit.text().strip()
        if name and not self.VALID_NAME_RE.match(name):
            self.validation_label.setText('Invalid base name — use A-Z a-z 0-9 _ -')
            self.start_btn.setEnabled(False)
        else:
            self.validation_label.setText('Base name valid' if name else 'Using scene name')
            self.start_btn.setEnabled(True)
        
        # Invalidate cache when user changes base name or suffix
        self._invalidate_version_cache()
        
        try:
            preview = self.build_preview_name()
            self.preview_label.setText(f'Preview: {preview}')
        except (RuntimeError, OSError) as e:
            self.preview_label.setText(f'Preview: Error - {str(e)}')
            logger.error(f'Preview generation failed: {e}')

    def start_autosave(self):
        """Start the autosave timer and initialize countdown."""
        interval = int(self.interval_spin.value())
        ms = interval * 60 * 1000
        self._save_start_time = datetime.now()
        self._timer.start(ms)
        self._countdown_timer.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText('Status: Running')
        
        # Update scene stats
        self.update_scene_stats()

        # Create a scriptJob to stop on quit
        try:
            if self._script_job_id is None:
                self._script_job_id = cmds.scriptJob(event=['quitApplication', self.stop_autosave], protected=True)
        except RuntimeError as e:
            logger.warning(f'Could not create scriptJob: {e}')

        # Do an immediate save when starting
        QtCore.QTimer.singleShot(200, self.on_autosave_timeout)

    def stop_autosave(self):
        """Stop the autosave timer and cleanup."""
        if self._timer.isActive():
            self._timer.stop()
        if self._countdown_timer.isActive():
            self._countdown_timer.stop()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText('Status: Stopped')
        if hasattr(self, 'countdown_label'):
            self.countdown_label.setText('Next save in: --:--')

        if self._script_job_id is not None:
            try:
                if cmds.scriptJob(exists=self._script_job_id):
                    cmds.scriptJob(kill=self._script_job_id, force=True)
            except RuntimeError as e:
                logger.debug(f'ScriptJob cleanup warning: {e}')
            self._script_job_id = None

    def on_autosave_timeout(self):
        # Run autosave operation deferred in Maya main thread
        try:
            self.perform_autosave()
        except Exception as e:
            print('Autosave error:', e)

    def perform_autosave(self):
        """Perform the autosave operation using safer export method."""
        base = self.base_edit.text().strip()
        if base and not self.VALID_NAME_RE.match(base):
            self.show_error('Autosave skipped: invalid base name')
            return

        try:
            scene = cmds.file(query=True, sceneName=True)
            if not base:
                if scene and scene.strip():
                    base = os.path.splitext(os.path.basename(scene))[0]
                    # Ensure base is valid and not empty
                    if not base or not base.strip():
                        base = 'untitled'
                else:
                    base = 'untitled'
            # Additional validation: ensure base only has valid characters
            if not self.VALID_NAME_RE.match(base):
                # Clean the name by replacing invalid chars with underscores
                base = re.sub(r'[^A-Za-z0-9_\-]+', '_', base)
                if not base:
                    base = 'untitled'
        except RuntimeError as e:
            self.show_error(f'Could not query scene: {str(e)}')
            return

        suffix = self.suffix_combo.currentText()
        directory = self.get_save_directory()
        
        # Ensure directory exists
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except OSError as e:
                self.show_error(f'Could not create directory: {str(e)}')
                logger.error(f'Could not create save directory {directory}: {e}')
                return

        # Get next version using cached method and build target path
        next_ver = self.get_next_version(base, suffix, directory, force_refresh=True)
        target_path = os.path.join(directory, f"{base}_{suffix}_V{next_ver:03d}.ma")

        try:
            # Safer method: export selection (or all) to target without renaming current scene
            # First save current scene to ensure no data loss
            if scene:
                try:
                    cmds.file(save=True, force=True)
                except RuntimeError:
                    pass  # Scene might be untitled
            
            # Export all to target path as Maya ASCII
            cmds.file(target_path, type='mayaAscii', exportAll=True, force=True)
            
            # Update tracking
            self._last_save_path = target_path
            self._last_save_time = datetime.now()
            
            # Invalidate cache since we created a new version
            self._invalidate_version_cache()
            
            # Update UI
            self.preview_label.setText(f'Preview: {self.build_preview_name()}')
            if hasattr(self, 'last_save_label'):
                time_str = self._last_save_time.strftime('%H:%M:%S')
                filename = os.path.basename(target_path)
                self.last_save_label.setText(f'Last save: {filename} at {time_str}')
            
            # Update scene stats
            self.update_scene_stats()
            
            # Reset countdown timer
            self._save_start_time = datetime.now()
            
            self.show_success(f'Saved: {os.path.basename(target_path)}')
            logger.info(f'Autosaved to: {target_path}')
            
        except RuntimeError as e:
            self.show_error(f'Save failed: {str(e)}')
            logger.error(f'Autosave failed: {e}')
        except (IOError, OSError) as e:
            self.show_error(f'File system error: {str(e)}')
            logger.error(f'Autosave IO error: {e}')

    def closeEvent(self, event):
        """Ensure clean shutdown of timers and scriptJob."""
        try:
            self.stop_autosave()
        except RuntimeError as e:
            logger.debug(f'Close event cleanup warning: {e}')
        super(AutosaveWindow, self).closeEvent(event)


_window_instance = None


def show_ui():
    """Show or raise the Revention Autosave window."""
    global _window_instance
    parent = get_maya_main_window()
    try:
        if _window_instance is None or not _window_instance.isVisible():
            _window_instance = AutosaveWindow(parent)
            _window_instance.show()
        else:
            _window_instance.raise_()
            _window_instance.activateWindow()
    except (RuntimeError, AttributeError) as e:
        # fallback: create a new window
        logger.warning(f'Window recreation required: {e}')
        _window_instance = AutosaveWindow(parent)
        _window_instance.show()


if __name__ == '__main__':
    show_ui()
