"""
Configuration file for GeoMaster
"""

# Detection thresholds
DUPLICATE_VERTEX_THRESHOLD = 0.0001
ZERO_LENGTH_EDGE_THRESHOLD = 0.0001
NON_PLANAR_TOLERANCE = 0.001
HIGH_POLY_THRESHOLD = 50000

# UI Settings
UI_WINDOW_NAME = 'geoMaster_window'
UI_WINDOW_TITLE = 'GeoMaster'
UI_WIDTH = 520
UI_HEIGHT = 750

# Logging
ENABLE_LOGGING = True
LOG_FILE = 'gameGeoMaster.log'
DEBUG_MODE = True

# Performance
MAX_VERTICES_PER_CHECK = 100000  # Skip extremely heavy meshes
BATCH_SIZE = 50  # Process meshes in batches

# Color scheme (RGB 0-1) - All Grey
COLOR_CATEGORY_HEADER = [0.35, 0.35, 0.35]
COLOR_FIND_BUTTON = [0.40, 0.40, 0.40]
COLOR_FIX_BUTTON = [0.42, 0.42, 0.42]
COLOR_HIGHLIGHT_BUTTON = [0.38, 0.38, 0.38]
COLOR_DISABLED_BUTTON = [0.30, 0.30, 0.30]
