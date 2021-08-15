#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Copyright (c) 2015-2021, PyInstaller Development Team.
# Copyright (c) 2015-2020, Hartmut Goebel.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
This script reformats the output of `myprog --help` to decent rst.

There are two sphinx plugins which could replace this eventually:
  - https://github.com/ashb/sphinx-argparse
  - https://github.com/gaborbernat/sphinx-argparse-cli
The former's output looks really nice, but lacks support for cross-referencing arguments. The latter supports
cross-referencing, but its output looks hideous. Hopefully either one of them will eventually evolve into something
we can use.

The main functions here are parser_to_rst() and help_to_rst(). Throughout this code the, **cross_references** option
controls whether or not section headings and options should be given cross reference targets.
"""

from textwrap import indent, wrap, dedent
import re
from argparse import ArgumentParser
from functools import partial


def parser_to_rst(parser: ArgumentParser, cross_references=True):
    """
    Extract the ``--help`` output from an argparse parser and convert it to restructured text.
    """
    help = parser.format_help()
    return help_to_rst(help, cross_references)


# Matches headings followed by indented blocks.
SECTION_REGEX = re.compile(
    r"""
    # A non-empty line with no indentation.
    ^\S.*\n

    # Followed by a non-zero number of either blank lines or indented lines.
    (?:(?:\ +.*)?\n)+
""", re.MULTILINE | re.VERBOSE
)


def help_to_rst(help: str, cross_references=True):
    """
    Convert the output of a ``cli --help`` call to rst.
    """
    summary, *sections = SECTION_REGEX.findall(help)

    # We could stick the summary (``usage: pyinstaller [-h] [--help] ...``) into a code block, but it is pretty
    # unhelpful, so I choose to omit it.
    sections = "\n".join(section_to_rst(section, cross_references) for section in sections)

    return sections


def section_to_rst(section: str, cross_references=True) -> str:
    """
    Convert a single option group's ``--help`` output to rst.

    This generates a heading for the option group followed by each option within that group.
    """
    title, body = section.split("\n", maxsplit=1)

    rst_title = rst_headerise(title, cross_references)
    rst_body = OPTION_REGEX.sub(partial(option_to_rst, cross_references=cross_references), body)

    return rst_title + rst_body


OPTION_REGEX = re.compile(
    r"""
    # Matches:
    #   --name, --other-name, -n VALUE  Some description
    #                                   and some more description.

    # An option name prefixed with at least 1 space.
    ^(\ +)(.*?)
    # Optionally followed by at least 2 spaces and the start of the desciption.
    (?:\ {2,}(.*))?\n

    # More lines of description.
    # Each line starts with more spaces than which prefixed the option name (so as to avoid picking up the next option).
    # Blank lines are allowed.
    (((?:\1\ +(.*))?\n)*)

""", re.MULTILINE | re.VERBOSE
)


def option_to_rst(m: re.Match, cross_references=True) -> str:
    """
    Convert a single option to rst.

    The output should look like::

        .. option:: --option-name -n

            The help for that option nicely text-wrapped.
    """
    name = m.group(2)
    assert name
    body = " ".join(i for i in m.group(3, 4) if i)
    # Escape characters which turn into invalid rst.
    body = body.replace("*", r"\*")
    # Re-wrap the help block.
    body = "\n".join(wrap(dedent(body), width=75, break_on_hyphens=False, break_long_words=False))

    template = ".. option:: {}\n\n{}\n\n" if cross_references else "{}\n\n{}\n\n"

    return template.format(name, indent(body, "    "))


def rst_headerise(title: str, cross_references=True) -> str:
    """
    Create a title with the correct length '---' underline.
    """
    title = title.strip(" \n:").title()
    out = f"{title}\n{'-' * len(title)}\n\n"
    if cross_references:
        out = f".. _`{title}`:\n\n" + out
    return out
