#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Logging module for PyInstaller
"""


__all__ = ['getLogger', 'INFO', 'WARN', 'DEBUG', 'ERROR', 'FATAL']

import logging
from logging import getLogger, INFO, WARN, DEBUG, ERROR, FATAL

def __add_options(parser):
    levels = ('DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL')
    parser.add_option('--log-level',
                      choices=levels,
                      default='INFO',
                      dest='loglevel',
                      help=('Amount of detail in build-time console messages '
                            '(default: %%default, choose one of %s)'
                            % ', '.join(levels))
                      )

def __process_options(parser, opts):
    FORMAT = '%(relativeCreated)d %(levelname)s: %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    logger = getLogger('PyInstaller')

    try:
        level = getattr(logging, opts.loglevel.upper())
    except AttributeError:
        parser.error('Unknown log level `%s`' % opts.loglevel)
    else:
        logger.setLevel(level)
