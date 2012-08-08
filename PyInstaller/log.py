#! -*- mode: python; coding: utf-8 -*-
"""
Logging module for PyInstaller
"""
#
# Copyright 2011 by Hartmut Goebel <h.goebel@goebel-consult.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

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
                      help=('Log level '
                            '(default: %%default, choose one of %s)'
                            % ', '.join(levels))
                      )

def __process_options(parser, opts):
    try:
        level = getattr(logging, opts.loglevel.upper())
    except AttributeError:
        parser.error('Unknown log level `%s`' % opts.loglevel)
    logger.setLevel(level)
