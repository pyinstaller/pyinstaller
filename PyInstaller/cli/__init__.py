# -----------------------------------------------------------------------------
# Copyright (c) 2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

import click

from PyInstaller import __version__, compat
from . import opts

CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__)
@click.pass_context
def cli(_ctx: click.Context):
    """Main Help Text
    """

    # This function is run whenever one of the subcommands is called, so we can add global-code here.
    compat.check_requirements()


@cli.command('build')
@opts.add_logging_options
@opts.add_build_options
@opts.add_makespec_options
@click.argument(
    'file', metavar='SCRIPTNAME',
)
def build_cmd(**kwargs):
    """Freeze a python script

    SCRIPTNAME is the name of the script to process
    """
    print(kwargs)


@cli.command('makespec')
@opts.add_makespec_options
@click.argument(
    'file', metavar='SCRIPTNAME',
)
def makespec_cmd(**kwargs):
    """Create a specfile from command-line options.
    """
    print(kwargs)


@cli.command('buildspec')
@opts.add_logging_options
@opts.add_build_options
def buildspec_cmd(**kwargs):
    """Build a specfile
    """
    print(kwargs)


@cli.command('archive-viewer')
def buildspec_cmd(**kwargs):
    """TODO: this command will repalce pyi-archive_viewer"""


def run():
    cli(prog_name='pyinstaller')
