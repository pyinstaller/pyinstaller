import eyed3.plugins
from PyInstaller.utils.hooks import logger

def pre_find_module_path(api):
    api.search_dirs += eyed3.plugins.__path__
    logger.debug('Adding eyed3 default plugins search path: %r' % api.search_dirs)
