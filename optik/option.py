"""optik.option

Defines the Option class and some standard value-checking functions.
"""

# Copyright (c) 2001-2004 Gregory P. Ward.  All rights reserved.
# See the README.txt distributed with Optik for licensing terms.

import sys
import types
from optik.errors import OptionError, OptionValueError, gettext as _

__revision__ = "$Id: option.py 470 2004-12-07 01:39:56Z gward $"

__all__ = ['Option']

# Do the right thing with boolean values for all known Python versions.
try:
    True, False
except NameError:
    (True, False) = (1, 0)

_idmax = 2L * sys.maxint + 1

def _repr(self):
    return "<%s at 0x%x: %s>" % (self.__class__.__name__,
                                 id(self) & _idmax,
                                 self)

def _parse_num(val, type):
    if val[:2].lower() == "0x":         # hexadecimal
        radix = 16
    elif val[:2].lower() == "0b":       # binary
        radix = 2
        val = val[2:] or "0"            # have to remove "0b" prefix
    elif val[:1] == "0":                # octal
        radix = 8
    else:                               # decimal
        radix = 10

    return type(val, radix)

def _parse_int(val):
    return _parse_num(val, int)

def _parse_long(val):
    return _parse_num(val, long)

_builtin_cvt = { "int" : (_parse_int, _("integer")),
                 "long" : (_parse_long, _("long integer")),
                 "float" : (float, _("floating-point")),
                 "complex" : (complex, _("complex")) }

def check_builtin(option, opt, value):
    (cvt, what) = _builtin_cvt[option.type]
    try:
        return cvt(value)
    except ValueError:
        raise OptionValueError(
            _("option %s: invalid %s value: %r") % (opt, what, value))

def check_choice(option, opt, value):
    if value in option.choices:
        return value
    else:
        choices = ", ".join(map(repr, option.choices))
        raise OptionValueError(
            _("option %s: invalid choice: %r (choose from %s)")
            % (opt, value, choices))

# Not supplying a default is different from a default of None,
# so we need an explicit "not supplied" value.
NO_DEFAULT = ("NO", "DEFAULT")


class Option:
    """
    Instance attributes:
      _short_opts : [string]
      _long_opts : [string]

      action : string
      type : string
      dest : string
      default : any
      nargs : int
      const : any
      choices : [string]
      callback : function
      callback_args : (any*)
      callback_kwargs : { string : any }
      help : string
      metavar : string
    """

    # The list of instance attributes that may be set through
    # keyword args to the constructor.
    ATTRS = ['action',
             'type',
             'dest',
             'default',
             'nargs',
             'const',
             'choices',
             'callback',
             'callback_args',
             'callback_kwargs',
             'help',
             'metavar']

    # The set of actions allowed by option parsers.  Explicitly listed
    # here so the constructor can validate its arguments.
    ACTIONS = ("store",
               "store_const",
               "store_true",
               "store_false",
               "append",
               "append_const",
               "count",
               "callback",
               "help",
               "version")

    # The set of actions that involve storing a value somewhere;
    # also listed just for constructor argument validation.  (If
    # the action is one of these, there must be a destination.)
    STORE_ACTIONS = ("store",
                     "store_const",
                     "store_true",
                     "store_false",
                     "append",
                     "append_const",
                     "count")

    # The set of actions for which it makes sense to supply a value
    # type, ie. which may consume an argument from the command line.
    TYPED_ACTIONS = ("store",
                     "append",
                     "callback")

    # The set of actions which *require* a value type, ie. that
    # always consume an argument from the command line.
    ALWAYS_TYPED_ACTIONS = ("store",
                            "append")

    # The set of actions which take a 'const' attribute.
    CONST_ACTIONS = ("store_const",
                     "append_const")

    # The set of known types for option parsers.  Again, listed here for
    # constructor argument validation.
    TYPES = ("string", "int", "long", "float", "complex", "choice")

    # Dictionary of argument checking functions, which convert and
    # validate option arguments according to the option type.
    #
    # Signature of checking functions is:
    #   check(option : Option, opt : string, value : string) -> any
    # where
    #   option is the Option instance calling the checker
    #   opt is the actual option seen on the command-line
    #     (eg. "-a", "--file")
    #   value is the option argument seen on the command-line
    #
    # The return value should be in the appropriate Python type
    # for option.type -- eg. an integer if option.type == "int".
    #
    # If no checker is defined for a type, arguments will be
    # unchecked and remain strings.
    TYPE_CHECKER = { "int"    : check_builtin,
                     "long"   : check_builtin,
                     "float"  : check_builtin,
                     "complex": check_builtin,
                     "choice" : check_choice,
                   }


    # CHECK_METHODS is a list of unbound method objects; they are called
    # by the constructor, in order, after all attributes are
    # initialized.  The list is created and filled in later, after all
    # the methods are actually defined.  (I just put it here because I
    # like to define and document all class attributes in the same
    # place.)  Subclasses that add another _check_*() method should
    # define their own CHECK_METHODS list that adds their check method
    # to those from this class.
    CHECK_METHODS = None


    # -- Constructor/initialization methods ----------------------------

    def __init__(self, *opts, **attrs):
        # Set _short_opts, _long_opts attrs from 'opts' tuple.
        # Have to be set now, in case no option strings are supplied.
        self._short_opts = []
        self._long_opts = []
        opts = self._check_opt_strings(opts)
        self._set_opt_strings(opts)

        # Set all other attrs (action, type, etc.) from 'attrs' dict
        self._set_attrs(attrs)

        # Check all the attributes we just set.  There are lots of
        # complicated interdependencies, but luckily they can be farmed
        # out to the _check_*() methods listed in CHECK_METHODS -- which
        # could be handy for subclasses!  The one thing these all share
        # is that they raise OptionError if they discover a problem.
        for checker in self.CHECK_METHODS:
            checker(self)

    def _check_opt_strings(self, opts):
        # Filter out None because early versions of Optik had exactly
        # one short option and one long option, either of which
        # could be None.
        opts = filter(None, opts)
        if not opts:
            raise TypeError("at least one option string must be supplied")
        return opts

    def _set_opt_strings(self, opts):
        for opt in opts:
            if len(opt) < 2:
                raise OptionError(
                    "invalid option string %r: "
                    "must be at least two characters long" % opt, self)
            elif len(opt) == 2:
                if not (opt[0] == "-" and opt[1] != "-"):
                    raise OptionError(
                        "invalid short option string %r: "
                        "must be of the form -x, (x any non-dash char)" % opt,
                        self)
                self._short_opts.append(opt)
            else:
                if not (opt[0:2] == "--" and opt[2] != "-"):
                    raise OptionError(
                        "invalid long option string %r: "
                        "must start with --, followed by non-dash" % opt,
                        self)
                self._long_opts.append(opt)

    def _set_attrs(self, attrs):
        for attr in self.ATTRS:
            if attrs.has_key(attr):
                setattr(self, attr, attrs[attr])
                del attrs[attr]
            else:
                if attr == 'default':
                    setattr(self, attr, NO_DEFAULT)
                else:
                    setattr(self, attr, None)
        if attrs:
            raise OptionError(
                "invalid keyword arguments: %s" % ", ".join(attrs.keys()),
                self)


    # -- Constructor validation methods --------------------------------

    def _check_action(self):
        if self.action is None:
            self.action = "store"
        elif self.action not in self.ACTIONS:
            raise OptionError("invalid action: %r" % self.action, self)

    def _check_type(self):
        if self.type is None:
            if self.action in self.ALWAYS_TYPED_ACTIONS:
                if self.choices is not None:
                    # The "choices" attribute implies "choice" type.
                    self.type = "choice"
                else:
                    # No type given?  "string" is the most sensible default.
                    self.type = "string"
        else:
            # Allow type objects as an alternative to their names.
            if type(self.type) is type:
                self.type = self.type.__name__
            if self.type == "str":
                self.type = "string"

            if self.type not in self.TYPES:
                raise OptionError("invalid option type: %r" % self.type, self)
            if self.action not in self.TYPED_ACTIONS:
                raise OptionError(
                    "must not supply a type for action %r" % self.action, self)

    def _check_choice(self):
        if self.type == "choice":
            if self.choices is None:
                raise OptionError(
                    "must supply a list of choices for type 'choice'", self)
            elif type(self.choices) not in (types.TupleType, types.ListType):
                raise OptionError(
                    "choices must be a list of strings ('%s' supplied)"
                    % str(type(self.choices)).split("'")[1], self)
        elif self.choices is not None:
            raise OptionError(
                "must not supply choices for type %r" % self.type, self)

    def _check_dest(self):
        # No destination given, and we need one for this action.  The
        # self.type check is for callbacks that take a value.
        takes_value = (self.action in self.STORE_ACTIONS or
                       self.type is not None)
        if self.dest is None and takes_value:

            # Glean a destination from the first long option string,
            # or from the first short option string if no long options.
            if self._long_opts:
                # eg. "--foo-bar" -> "foo_bar"
                self.dest = self._long_opts[0][2:].replace('-', '_')
            else:
                self.dest = self._short_opts[0][1]

    def _check_const(self):
        if self.action not in self.CONST_ACTIONS and self.const is not None:
            raise OptionError(
                "'const' must not be supplied for action %r" % self.action,
                self)

    def _check_nargs(self):
        if self.action in self.TYPED_ACTIONS:
            if self.nargs is None:
                self.nargs = 1
        elif self.nargs is not None:
            raise OptionError(
                "'nargs' must not be supplied for action %r" % self.action,
                self)

    def _check_callback(self):
        if self.action == "callback":
            if not callable(self.callback):
                raise OptionError(
                    "callback not callable: %r" % self.callback, self)
            if (self.callback_args is not None and
                type(self.callback_args) is not types.TupleType):
                raise OptionError(
                    "callback_args, if supplied, must be a tuple: not %r"
                    % self.callback_args, self)
            if (self.callback_kwargs is not None and
                type(self.callback_kwargs) is not types.DictType):
                raise OptionError(
                    "callback_kwargs, if supplied, must be a dict: not %r"
                    % self.callback_kwargs, self)
        else:
            if self.callback is not None:
                raise OptionError(
                    "callback supplied (%r) for non-callback option"
                    % self.callback, self)
            if self.callback_args is not None:
                raise OptionError(
                    "callback_args supplied for non-callback option", self)
            if self.callback_kwargs is not None:
                raise OptionError(
                    "callback_kwargs supplied for non-callback option", self)


    CHECK_METHODS = [_check_action,
                     _check_type,
                     _check_choice,
                     _check_dest,
                     _check_const,
                     _check_nargs,
                     _check_callback]


    # -- Miscellaneous methods -----------------------------------------

    def __str__(self):
        return "/".join(self._short_opts + self._long_opts)

    __repr__ = _repr

    def takes_value(self):
        return self.type is not None

    def get_opt_string(self):
        if self._long_opts:
            return self._long_opts[0]
        else:
            return self._short_opts[0]


    # -- Processing methods --------------------------------------------

    def check_value(self, opt, value):
        checker = self.TYPE_CHECKER.get(self.type)
        if checker is None:
            return value
        else:
            return checker(self, opt, value)

    def convert_value(self, opt, value):
        if value is not None:
            if self.nargs == 1:
                return self.check_value(opt, value)
            else:
                return tuple([self.check_value(opt, v) for v in value])

    def process(self, opt, value, values, parser):

        # First, convert the value(s) to the right type.  Howl if any
        # value(s) are bogus.
        value = self.convert_value(opt, value)

        # And then take whatever action is expected of us.
        # This is a separate method to make life easier for
        # subclasses to add new actions.
        return self.take_action(
            self.action, self.dest, opt, value, values, parser)

    def take_action(self, action, dest, opt, value, values, parser):
        if action == "store":
            setattr(values, dest, value)
        elif action == "store_const":
            setattr(values, dest, self.const)
        elif action == "store_true":
            setattr(values, dest, True)
        elif action == "store_false":
            setattr(values, dest, False)
        elif action == "append":
            values.ensure_value(dest, []).append(value)
        elif action == "append_const":
            values.ensure_value(dest, []).append(self.const)
        elif action == "count":
            setattr(values, dest, values.ensure_value(dest, 0) + 1)
        elif action == "callback":
            args = self.callback_args or ()
            kwargs = self.callback_kwargs or {}
            self.callback(self, opt, value, parser, *args, **kwargs)
        elif action == "help":
            parser.print_help()
            parser.exit()
        elif action == "version":
            parser.print_version()
            parser.exit()
        else:
            raise RuntimeError, "unknown action %r" % self.action

        return 1

# class Option
