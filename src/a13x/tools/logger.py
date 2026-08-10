"""
Logging utility for GeoMaster
"""

import os
from datetime import datetime

try:
    import config
except:
    class config:
        ENABLE_LOGGING = True
        LOG_FILE = 'gameGeoMaster.log'
        DEBUG_MODE = True


class Logger:
    """Simple logger for debugging GeoMaster"""
    
    def __init__(self):
        self.log_file = os.path.join(os.path.dirname(__file__), config.LOG_FILE)
        self.enabled = config.ENABLE_LOGGING
        self.debug_mode = config.DEBUG_MODE
        
        if self.enabled:
            try:
                with open(self.log_file, 'a') as f:
                    f.write('\n' + '='*80 + '\n')
                    f.write('GeoMaster - Session started: %s\n' % datetime.now())
                    f.write('='*80 + '\n')
            except:
                pass
    
    def log(self, message, level='INFO'):
        """Write log message"""
        if not self.enabled:
            return
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = '[%s] [%s] %s\n' % (timestamp, level, message)
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_line)
        except:
            pass
        
        if self.debug_mode:
            print(log_line.strip())
    
    def info(self, message):
        self.log(message, 'INFO')
    
    def warning(self, message):
        self.log(message, 'WARNING')
    
    def error(self, message):
        self.log(message, 'ERROR')
    
    def debug(self, message):
        if self.debug_mode:
            self.log(message, 'DEBUG')


# Global logger instance
_logger = None

def get_logger():
    """Get or create global logger instance"""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger
