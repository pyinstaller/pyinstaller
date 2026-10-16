#-----------------------------------------------------------------------------
# Copyright (c) 2015-2026, PyInstaller Development Team.
# Copyright (c) 2015-2020, Hartmut Goebel.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import argparse
import textwrap


def parser_to_rst(parser: argparse.ArgumentParser, section_references=True, option_directive=True):
    """
    Extract the option groups and option description from an argparse parser, and generate restructured text to be used
    with sphinx-generated documentation.

    There are two sphinx plugins which could replace this eventually:
    - https://github.com/ashb/sphinx-argparse
    - https://github.com/gaborbernat/sphinx-argparse-cli
    The former's output looks really nice, but lacks support for cross-referencing arguments. The latter supports
    cross-referencing, but its output looks hideous. Hopefully either one of them will eventually evolve into something
    we can use.

    Parameters
    ----------
    hook_type : ArgumentParser
        Instance of argument parser from which options should be extracted.
    section_references : bool
        Flag indicating whether to add a reference directive to each option-group section or not. These can be used for
        cross-referencing from other parts of documentation
    option_directives : bool
        Flag indicating whether to use `.. option::` directive or not.

    Returns
    ----------
    str
        Restructured text with extracted option description.
    """

    rst_lines = []

    parser.color = False  # No-op in python < 3.14
    formatter = parser._get_formatter()  # Used to simplify arguments formatting

    # If this is special PyInstaller parser with forbidden makespec options, create a set for lookup.
    if hasattr(parser, '_pyi_action_groups'):
        makespec_options = set(parser._pyi_action_groups.get('makespec', []))
    else:
        makespec_options = set()

    # Go over positionals, optionals, and user-defined groups
    for action_group in parser._action_groups:
        # Check actions in a group, and skip groups where help for all actions are suppressed.
        active_actions = [action for action in action_group._group_actions if action.help != argparse.SUPPRESS]
        if not active_actions:
            continue

        # Capitalize group title
        title = action_group.title.title()

        # Optional section reference (for cross-referencing)
        if section_references:
            rst_lines.append(f".. _`{title}`:")
            rst_lines.append('')

        # Section title, and corresponding amount of underscores
        rst_lines.append(title)
        rst_lines.append('-' * len(title))
        rst_lines.append('')

        # All actions in the group
        for action in active_actions:
            # Prepare parts of the option string:
            # .. option:: -n, --option-name, --option-alias OPTION_ARGS
            option_parts = []
            if option_directive:
                option_parts.append('.. option::')

            if not action.option_strings:
                default = formatter._get_default_metavar_for_positional(action)
                args_string = ' '.join(formatter._metavar_formatter(action, default)(1))

                option_parts.append(args_string)  # Note: do not use placeholder curly braces here!
            else:
                option_parts.append(', '.join(action.option_strings))
                if action.nargs != 0:
                    # Option with value argument(s)
                    default = formatter._get_default_metavar_for_optional(action)
                    args_string = formatter._format_args(action, default)

                    # If `.. option::` directive is used, escape the curly braces that are used for choices. Then add
                    # curly braces around the argument string, so we can use `option_emphasise_placeholders` option.
                    if option_directive:
                        args_string = args_string.replace('{', r'\{')
                        args_string = args_string.replace('}', r'\}')
                        args_string = '{' + args_string + '}'

                    option_parts.append(args_string)

            rst_lines.append(' '.join(option_parts))

            rst_lines.append('')

            if action.help:
                body = action.help

                # Escape characters which turn into invalid rst.
                body = body.replace('*', r'\*')

                # Wrap
                body_lines = textwrap.wrap(
                    body,
                    width=75,
                    break_on_hyphens=False,
                    break_long_words=False,
                )

                # Apply indent
                rst_lines += [4 * ' ' + line for line in body_lines]

            # Add note for options that are disallowed
            if makespec_options and action in makespec_options:
                rst_lines += [
                    '',
                    4 * ' ' + '.. note::',
                    '',
                    8 * ' ' + "This option is not allowed when building from .spec file.",
                    '',
                ]

            rst_lines.append('')

        rst_lines.append('')

    return '\n'.join(rst_lines)
