"""optik.errors

Exception classes used by Optik.
"""

# Copyright (c) 2001-2004 Gregory P. Ward.  All rights reserved.
# See the README.txt distributed with Optik for licensing terms.

import string
try:
    from gettext import gettext
except ImportError:
    def gettext(message):
        return message
_ = gettext

__revision__ = "$Id: errors.py 470 2004-12-07 01:39:56Z gward $"

__all__ = ['OptikError', 'OptionError', 'OptionConflictError',
           'OptionValueError', 'BadOptionError']


class OptikError (Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class OptionError (OptikError):
    """
    Raised if an Option instance is created with invalid or
    inconsistent arguments.
    """

    def __init__(self, msg, option):
        self.msg = msg
        self.option_id = str(option)

    def __str__(self):
        if self.option_id:
            return "option %s: %s" % (self.option_id, self.msg)
        else:
            return self.msg

class OptionConflictError (OptionError):
    """
    Raised if conflicting options are added to an OptionParser.
    """

class OptionValueError (OptikError):
    """
    Raised if an invalid option value is encountered on the command
    line.
    """

class BadOptionError (OptikError):
    """
    Raised if an invalid option is seen on the command line.
    """
    def __init__(self, opt_str):
        self.opt_str = opt_str

    def __str__(self):
        return _("no such option: %s") % self.opt_str

class AmbiguousOptionError (BadOptionError):
    """
    Raised if an ambiguous option is seen on the command line.
    """
    def __init__(self, opt_str, possibilities):
        BadOptionError.__init__(self, opt_str)
        self.possibilities = possibilities

    def __str__(self):
        return (_("ambiguous option: %s (%s?)")
                % (self.opt_str, string.join(self.possibilities, ", ")))
