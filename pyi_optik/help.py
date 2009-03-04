"""optik.help

Provides HelpFormatter and subclasses -- used by OptionParser
to generate formatted help text.
"""

# Copyright (c) 2001-2004 Gregory P. Ward.  All rights reserved.
# See the README.txt distributed with Optik for licensing terms.

import os
import string
import textwrap
from pyi_optik.option import NO_DEFAULT
from pyi_optik.errors import gettext
_ = gettext

__revision__ = "$Id: help.py 470 2004-12-07 01:39:56Z gward $"

__all__ = ['HelpFormatter', 'IndentedHelpFormatter', 'TitledHelpFormatter']

class HelpFormatter:

    """
    Abstract base class for formatting option help.  OptionParser
    instances should use one of the HelpFormatter subclasses for
    formatting help; by default IndentedHelpFormatter is used.

    Instance attributes:
      parser : OptionParser
        the controlling OptionParser instance
      indent_increment : int
        the number of columns to indent per nesting level
      max_help_position : int
        the maximum starting column for option help text
      help_position : int
        the calculated starting column for option help text;
        initially the same as the maximum
      width : int
        total number of columns for output (pass None to constructor for
        this value to be taken from the $COLUMNS environment variable)
      level : int
        current indentation level
      current_indent : int
        current indentation level (in columns)
      help_width : int
        number of columns available for option help text (calculated)
      default_tag : str
        text to replace with each option's default value, "%default"
        by default.  Set to false value to disable default value expansion.
      option_strings : { Option : str }
        maps Option instances to the snippet of help text explaining
        the syntax of that option, e.g. "-h, --help" or
        "-fFILE, --file=FILE"
      _short_opt_fmt : str
        format string controlling how short options with values are
        printed in help text.  Must be either "%s%s" ("-fFILE") or
        "%s %s" ("-f FILE"), because those are the two syntaxes that
        Optik supports.
      _long_opt_fmt : str
        similar but for long options; must be either "%s %s" ("--file FILE")
        or "%s=%s" ("--file=FILE").
    """

    NO_DEFAULT_VALUE = "none"

    def __init__(self,
                 indent_increment,
                 max_help_position,
                 width,
                 short_first):
        self.parser = None
        self.indent_increment = indent_increment
        self.help_position = self.max_help_position = max_help_position
        if width is None:
            try:
                width = int(os.environ['COLUMNS'])
            except (KeyError, ValueError):
                width = 80
            width = width - 2
        self.width = width
        self.current_indent = 0
        self.level = 0
        self.help_width = None          # computed later
        self.short_first = short_first
        self.default_tag = "%default"
        self.option_strings = {}
        self._short_opt_fmt = "%s %s"
        self._long_opt_fmt = "%s=%s"

    def set_parser(self, parser):
        self.parser = parser

    def set_short_opt_delimiter(self, delim):
        if delim not in ("", " "):
            raise ValueError(
                "invalid metavar delimiter for short options: %r" % delim)
        self._short_opt_fmt = "%s" + delim + "%s"

    def set_long_opt_delimiter(self, delim):
        if delim not in ("=", " "):
            raise ValueError(
                "invalid metavar delimiter for long options: %r" % delim)
        self._long_opt_fmt = "%s" + delim + "%s"

    def indent(self):
        self.current_indent = self.current_indent + self.indent_increment
        self.level = self.level + 1

    def dedent(self):
        self.current_indent = self.current_indent - self.indent_increment
        assert self.current_indent >= 0, "Indent decreased below 0."
        self.level = self.level - 1

    def format_usage(self, usage):
        raise NotImplementedError, "subclasses must implement"

    def format_heading(self, heading):
        raise NotImplementedError, "subclasses must implement"

    def format_description(self, description):
        if not description:
            return ""
        desc_width = self.width - self.current_indent
        indent = " "*self.current_indent
        return textwrap.fill(description,
                             desc_width,
                             initial_indent=indent,
                             subsequent_indent=indent) + "\n"

    def expand_default(self, option):
        if self.parser is None or not self.default_tag:
            return option.help

        default_value = self.parser.defaults.get(option.dest)
        if default_value is NO_DEFAULT or default_value is None:
            default_value = self.NO_DEFAULT_VALUE

        return string.replace(option.help, self.default_tag, str(default_value))

    def format_option(self, option):
        # The help for each option consists of two parts:
        #   * the opt strings and metavars
        #     eg. ("-x", or "-fFILENAME, --file=FILENAME")
        #   * the user-supplied help string
        #     eg. ("turn on expert mode", "read data from FILENAME")
        #
        # If possible, we write both of these on the same line:
        #   -x      turn on expert mode
        #
        # But if the opt string list is too long, we put the help
        # string on a second line, indented to the same column it would
        # start in if it fit on the first line.
        #   -fFILENAME, --file=FILENAME
        #           read data from FILENAME
        result = []
        opts = self.option_strings[option]
        opt_width = self.help_position - self.current_indent - 2
        if len(opts) > opt_width:
            opts = "%*s%s\n" % (self.current_indent, "", opts)
            indent_first = self.help_position
        else:                       # start help on same line as opts
            opts = "%*s%-*s  " % (self.current_indent, "", opt_width, opts)
            indent_first = 0
        result.append(opts)
        if option.help:
            help_text = self.expand_default(option)
            help_lines = textwrap.wrap(help_text, self.help_width)
            result.append("%*s%s\n" % (indent_first, "", help_lines[0]))
            for line in help_lines[1:]:
                result.append("%*s%s\n" % (self.help_position, "", line))
        elif opts[-1] != "\n":
            result.append("\n")
        return string.join(result, "")

    def store_option_strings(self, parser):
        self.indent()
        max_len = 0
        for opt in parser.option_list:
            strings = self.format_option_strings(opt)
            self.option_strings[opt] = strings
            max_len = max(max_len, len(strings) + self.current_indent)
        self.indent()
        for group in parser.option_groups:
            for opt in group.option_list:
                strings = self.format_option_strings(opt)
                self.option_strings[opt] = strings
                max_len = max(max_len, len(strings) + self.current_indent)
        self.dedent()
        self.dedent()
        self.help_position = min(max_len + 2, self.max_help_position)
        self.help_width = self.width - self.help_position

    def format_option_strings(self, option):
        """Return a comma-separated list of option strings & metavariables."""
        if option.takes_value():
            metavar = option.metavar or string.upper(option.dest)
            short_opts = []
            for sopt in option._short_opts:
                short_opts.append(self._short_opt_fmt % (sopt, metavar))
            long_opts = []
            for lopt in option._long_opts:
                long_opts.append(self._long_opt_fmt % (lopt, metavar))
        else:
            short_opts = option._short_opts
            long_opts = option._long_opts

        if self.short_first:
            opts = short_opts + long_opts
        else:
            opts = long_opts + short_opts

        return string.join(opts, ", ")

class IndentedHelpFormatter (HelpFormatter):
    """Format help with indented section bodies.
    """

    def __init__(self,
                 indent_increment=2,
                 max_help_position=24,
                 width=None,
                 short_first=1):
        HelpFormatter.__init__(
            self, indent_increment, max_help_position, width, short_first)

    def format_usage(self, usage):
        return _("usage: %s\n") % usage

    def format_heading(self, heading):
        return "%*s%s:\n" % (self.current_indent, "", heading)


class TitledHelpFormatter (HelpFormatter):
    """Format help with underlined section headers.
    """

    def __init__(self,
                 indent_increment=0,
                 max_help_position=24,
                 width=None,
                 short_first=0):
        HelpFormatter.__init__ (
            self, indent_increment, max_help_position, width, short_first)

    def format_usage(self, usage):
        return "%s  %s\n" % (self.format_heading(_("Usage")), usage)

    def format_heading(self, heading):
        return "%s\n%s\n" % (heading, "=-"[self.level] * len(heading))
