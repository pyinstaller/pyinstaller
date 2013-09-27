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

FORMAT = '%(relativeCreated)d %(levelname)s: %(message)s'

try:
    logging.basicConfig(format=FORMAT, level=logging.INFO)
except TypeError:
    # In Python 2.3 basicConfig does not accept arguments
    # :todo: remove when dropping Python 2.3 compatibility
    logging.basicConfig()
    root = logging.getLogger()
    assert len(root.handlers) == 1
    root.handlers[0].setFormatter(logging.Formatter(FORMAT))
    root.setLevel(logging.INFO)

logger = getLogger('PyInstaller')


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
    try:
        level = getattr(logging, opts.loglevel.upper())
    except AttributeError:
        parser.error('Unknown log level `%s`' % opts.loglevel)
    logger.setLevel(level)
