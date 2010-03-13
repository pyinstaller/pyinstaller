#!/usr/bin/env python

# Author: David Goodger
# Contact: goodger@users.sourceforge.net
# Revision: $Revision: 2504 $
# Date: $Date: 2004-07-29 06:36:53 +0200 (Thu, 29 Jul 2004) $
# Copyright: This module has been placed in the public domain.

# Addapted by William Caban to look for .rst by default instead of .txt
# added docutils availability

"""
Generates .html from all the .rst files in a directory.

Ordinary .rst files are understood to be standalone reStructuredText.
Files named ``pep-*.rst`` are interpreted as reStructuredText PEPs.
"""
# Once PySource is here, build .html from .py as well.

__docformat__ = 'reStructuredText'


try:
    import locale
    locale.setlocale(locale.LC_ALL, '')
except:
    pass

import sys
import os
import os.path
import copy
try:
    import docutils
    from docutils import ApplicationError
    from docutils import core, frontend
    from docutils.parsers import rst
    from docutils.readers import standalone, pep
    from docutils.writers import html4css1, pep_html
except:
    print "################################################################"
    print "# You need 'docutils' installed to execute this program.       #"
    print "# 'docutils' is available from http://docutils.sourceforge.net #"
    print "################################################################"
    sys.exit(1)


usage = '%prog [options] [<directory> ...]'
description = ('Generates .html from all the reStructuredText .rst files '
               '(including PEPs) in each <directory> '
               '(default is the current directory).')


class SettingsSpec(docutils.SettingsSpec):

    """
    Runtime settings & command-line options for the front end.
    """

    # Can't be included in OptionParser below because we don't want to
    # override the base class.
    settings_spec = (
        'Build-HTML Options',
        None,
        (('Recursively scan subdirectories for files to process.  This is '
          'the default.',
          ['--recurse'],
          {'action': 'store_true', 'default': 1,
           'validator': frontend.validate_boolean}),
         ('Generate output files in the specified directory.  The default is '
          'to put them in the same directory of the input files.',
          ['--outpath'], {'metavar': '<directory>', 'type': 'string'}),
         ('Do not scan subdirectories for files to process.',
          ['--local'], {'dest': 'recurse', 'action': 'store_false'}),
         ('Do not process files in <directory>.  This option may be used '
          'more than once to specify multiple directories.',
          ['--prune'],
          {'metavar': '<directory>', 'action': 'append',
           'validator': frontend.validate_colon_separated_string_list}),
         ('Work silently (no progress messages).  Independent of "--quiet".',
          ['--silent'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),))

    relative_path_settings = ('prune',)
    config_section = 'buildhtml application'
    config_section_dependencies = ('applications',)


class OptionParser(frontend.OptionParser):

    """
    Command-line option processing for the ``buildhtml.py`` front end.
    """

    def check_values(self, values, args):
        frontend.OptionParser.check_values(self, values, args)
        values._source = None
        return values

    def check_args(self, args):
        source = destination = None
        if args:
            self.values._directories = args
        else:
            self.values._directories = [os.getcwd()]
        return source, destination


class Struct:

    """Stores data attributes for dotted-attribute access."""

    def __init__(self, **keywordargs):
        self.__dict__.update(keywordargs)


class Builder:

    def __init__(self):
        self.publishers = {
            '': Struct(components=(pep.Reader, rst.Parser, pep_html.Writer,
                                   SettingsSpec)),
            '.rst': Struct(components=(rst.Parser, standalone.Reader,
                                       html4css1.Writer, SettingsSpec),
                           reader_name='standalone',
                           writer_name='html'),
            'PEPs': Struct(components=(rst.Parser, pep.Reader,
                                       pep_html.Writer, SettingsSpec),
                           reader_name='pep',
                           writer_name='pep_html')}
        """Publisher-specific settings.  Key '' is for the front-end script
        itself.  ``self.publishers[''].components`` must contain a superset of
        all components used by individual publishers."""

        self.setup_publishers()

    def setup_publishers(self):
        """
        Manage configurations for individual publishers.

        Each publisher (combination of parser, reader, and writer) may have
        its own configuration defaults, which must be kept separate from those
        of the other publishers.  Setting defaults are combined with the
        config file settings and command-line options by
        `self.get_settings()`.
        """
        for name, publisher in self.publishers.items():
            option_parser = OptionParser(
                components=publisher.components, read_config_files=1,
                usage=usage, description=description)
            publisher.option_parser = option_parser
            publisher.setting_defaults = option_parser.get_default_values()
            frontend.make_paths_absolute(publisher.setting_defaults.__dict__,
                                         option_parser.relative_path_settings)
            publisher.config_settings = (
                option_parser.get_standard_config_settings())
        self.settings_spec = self.publishers[''].option_parser.parse_args(
            values=frontend.Values())   # no defaults; just the cmdline opts
        self.initial_settings = self.get_settings('')

    def get_settings(self, publisher_name, directory=None):
        """
        Return a settings object, from multiple sources.

        Copy the setting defaults, overlay the startup config file settings,
        then the local config file settings, then the command-line options.
        Assumes the current directory has been set.
        """
        publisher = self.publishers[publisher_name]
        settings = frontend.Values(publisher.setting_defaults.__dict__)
        settings.update(publisher.config_settings, publisher.option_parser)
        if directory:
            local_config = publisher.option_parser.get_config_file_settings(
                os.path.join(directory, 'docutils.conf'))
            frontend.make_paths_absolute(
                local_config, publisher.option_parser.relative_path_settings,
                directory)
            settings.update(local_config, publisher.option_parser)
        settings.update(self.settings_spec.__dict__, publisher.option_parser)
        return settings

    def run(self, directory=None, recurse=1):
        recurse = recurse and self.initial_settings.recurse
        if directory:
            self.directories = [directory]
        elif self.settings_spec._directories:
            self.directories = self.settings_spec._directories
        else:
            self.directories = [os.getcwd()]
        for directory in self.directories:
            os.path.walk(directory, self.visit, recurse)

    def visit(self, recurse, directory, names):
        settings = self.get_settings('', directory)
        if settings.prune and (os.path.abspath(directory) in settings.prune):
            print >>sys.stderr, '/// ...Skipping directory (pruned):', directory
            sys.stderr.flush()
            names[:] = []
            return
        if not self.initial_settings.silent:
            print >>sys.stderr, '/// Processing directory:', directory
            sys.stderr.flush()
        prune = 0
        for name in names:
            if name.endswith('.rst'):
                prune = self.process_rst(directory, name)
                if prune:
                    break
        if not recurse:
            del names[:]

    def process_rst(self, directory, name):
        if name.startswith('pep-'):
            publisher = 'PEPs'
        else:
            publisher = '.rst'
        settings = self.get_settings(publisher, directory)
        pub_struct = self.publishers[publisher]
        if settings.prune and (directory in settings.prune):
            return 1
        settings._source = os.path.normpath(os.path.join(directory, name))
        settings._destination = settings._source[:-4]+'.html'
        if settings.outpath:
            # FIXME: we should probably try and recreate the exising structure here,
            # but that's more work than we need right now.
            settings._destination = os.path.join(settings.outpath, os.path.basename(settings._destination))
        if not self.initial_settings.silent:
            print >>sys.stderr, '    ::: Processing:', name
            sys.stderr.flush()
        try:
            core.publish_file(source_path=settings._source,
                              destination_path=settings._destination,
                              reader_name=pub_struct.reader_name,
                              parser_name='restructuredtext',
                              writer_name=pub_struct.writer_name,
                              settings=settings)
        except ApplicationError, error:
            print >>sys.stderr, ('        Error (%s): %s'
                                 % (error.__class__.__name__, error))


if __name__ == "__main__":
    Builder().run()
