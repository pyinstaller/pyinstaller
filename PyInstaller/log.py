#-----------------------------------------------------------------------------
# Copyright (c) 2013-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Logging module for PyInstaller.
"""

__all__ = ['getLogger', 'INFO', 'WARN', 'DEBUG', 'TRACE', 'ERROR', 'FATAL']

import logging
from logging import DEBUG, ERROR, FATAL, INFO, WARN, getLogger

TRACE = logging.TRACE = DEBUG - 5
logging.addLevelName(TRACE, 'TRACE')

FORMAT = '%(relativeCreated)d %(levelname)s: %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)
logger = getLogger('PyInstaller')


def __add_options(parser):
    levels = ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL')
    parser.add_argument(
        '--log-level',
        choices=levels,
        metavar="LEVEL",
        default='INFO',
        dest='loglevel',
        help='Amount of detail in build-time console messages. LEVEL may be one of %s (default: %%(default)s).' %
        ', '.join(levels),
    )


def __process_options(parser, opts):
    try:
        level = getattr(logging, opts.loglevel.upper())
    except AttributeError:
        parser.error('Unknown log level `%s`' % opts.loglevel)
    else:
        logger.setLevel(level)
