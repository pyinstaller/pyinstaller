#-----------------------------------------------------------------------------
# Copyright (c) 2017-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Documentation roles for PyInstaller

:issue:`1234` - link to github issue

:commit:`1a2b3c4d5e6fa23b` - link to commit-id, text will be shortened to 8 digits for readability
"""
# Based on examples taken from
# <http://docutils.sourceforge.net/docs/howto/rst-roles.html> and
# <http://protips.readthedocs.io/link-roles.html>

from docutils import nodes


def commit(name, rawtext, text, lineno, inliner, options={}, content=[]):
    msg = None
    try:
        # verify this is a hex string
        int(text, 16)
    except ValueError:
        msg = 'The commit-id must be a hex-string; "%s" is invalid.' % text
    if len(text) < 8:
        msg = 'The commit-id "%s" is to short, please provide at least 8 characters.' % text
    if msg:
        msg = inliner.reporter.error(msg, line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]
    options.setdefault('classes', []).append("commitid")
    url = "https://github.com/pyinstaller/pyinstaller/commit/" + text
    node = nodes.reference(rawtext, text[:8], refuri=url, **options)
    return [node], []


def blob(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Reference a file within this repo and get a link to it on Github.
    """
    options.setdefault('classes', []).append("blob")
    url = "https://github.com/pyinstaller/pyinstaller/tree/develop/" + text
    node = nodes.reference(rawtext, text, refuri=url, **options)
    return [node], []


def issue(name, rawtext, text, lineno, inliner, options={}, content=[]):
    msg = None
    try:
        # strip leading numner sign which e.g. towncrier adds
        if text.startswith("#"):
            text = text[1:]
        # verify this is a number
        num = int(text)
        if num <= 0:
            raise ValueError
    except ValueError:
        msg = inliner.reporter.error(
            'The issue number must be a number larger then zero; "%s" is invalid.' % text, line=lineno
        )
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]
    options.setdefault('classes', []).append("issue")
    url = "https://github.com/pyinstaller/pyinstaller/issues/%i" % num
    node = nodes.reference(rawtext, "#%i" % num, refuri=url, **options)
    return [node], []


def autolink(pattern):
    def role(name, rawtext, text, lineno, inliner, options={}, content=[]):
        url = pattern % (text,)
        node = nodes.reference(rawtext, text, refuri=url, **options)
        return [node], []

    return role


def setup(app):
    app.add_role('issue', issue)
    app.add_role('commit', commit)
    app.add_role('blob', blob)
