#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Main command-line interface to PyInstaller.
"""


import os
import optparse
import sys

import PyInstaller.makespec
import PyInstaller.build
import PyInstaller.compat
import PyInstaller.log


# Warn when old command line option is used

from PyInstaller import get_version
from PyInstaller.log import logger
from PyInstaller.utils import misc


def run_makespec(opts, args):
    # Split pathex by using the path separator
    temppaths = opts.pathex[:]
    opts.pathex = []
    for p in temppaths:
        opts.pathex.extend(p.split(os.pathsep))

    spec_file = PyInstaller.makespec.main(args, **opts.__dict__)
    logger.info('wrote %s' % spec_file)
    return spec_file


def run_build(opts, spec_file, pyi_config):
    PyInstaller.build.main(pyi_config, spec_file, **opts.__dict__)


def __add_options(parser):
    parser.add_option('-v', '--version', default=False, action='store_true',
                      help='Show program version info and exit.')

def run(pyi_args=sys.argv[1:], pyi_config=None):
    """
    pyi_args     allows running PyInstaller programatically without a subprocess
    pyi_config   allows checking configuration once when running multiple tests
    """
    misc.check_not_running_as_root()

    try:
        parser = optparse.OptionParser(
            usage='%prog [opts] <scriptname> [ <scriptname> ...] | <specfile>'
            )
        __add_options(parser)
        PyInstaller.makespec.__add_options(parser)
        PyInstaller.build.__add_options(parser)
        PyInstaller.log.__add_options(parser)
        PyInstaller.compat.__add_obsolete_options(parser)

        opts, args = parser.parse_args(pyi_args)
        PyInstaller.log.__process_options(parser, opts)

        # Print program version and exit
        if opts.version:
            print(get_version())
            raise SystemExit(0)

        if not args:
            parser.error('Requires at least one scriptname file '
                         'or exactly one .spec-file')

        # Skip creating .spec when .spec file is supplied
        if args[0].endswith('.spec'):
            spec_file = args[0]
        else:
            spec_file = run_makespec(opts, args)

        run_build(opts, spec_file, pyi_config)

    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")


if __name__ == '__main__':
        run()
