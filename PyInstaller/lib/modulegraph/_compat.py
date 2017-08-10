import sys

if sys.version_info[0] == 2:
    PY2 = True

    from StringIO import StringIO
    BytesIO = StringIO
    from urllib import pathname2url
    _cOrd = ord

    # File open mode for reading (univeral newlines)
    _READ_MODE = "rU"

    def Bchr(value):
        return chr(value)

else:
    PY2 = False

    from urllib.request import pathname2url
    from io import BytesIO, StringIO
    _cOrd = int
    _READ_MODE = "r"

    def Bchr(value):
        return value


if sys.version_info >= (3,4):
    # In Python 3.4 or later the dis module has a much nicer interface
    # for working with bytecode, use that instead of peeking into the
    # raw bytecode.
    # Note: This nicely sidesteps any issues caused by moving from bytecode
    # to wordcode in python 3.6.
    get_instructions = dis.get_instructions
else:
    assert 'SET_LINENO' not in dis.opmap  # safty belt

    def get_instructions(code):
        """
        Iterator parsing the bytecode into easy-usable minimal emulation of
        Python 3.4 `dis.Instruction` instances.
        """

        # shortcuts
        HAVE_ARGUMENT = dis.HAVE_ARGUMENT
        EXTENDED_ARG = dis.EXTENDED_ARG

        class Instruction:
            # Minimal emulation of Python 3.4 dis.Instruction
            def __init__(self, opcode, oparg):
                self.opname = dis.opname[opcode]
                self.arg = oparg
                # opcode, argval, argrepr, offset, is_jump_target and
                # starts_line are not used by our code, so we leave them away
                # here.

        code = code.co_code
        extended_arg = 0
        i = 0
        n = len(code)
        while i < n:
            c = code[i]
            i = i + 1
            op = _cOrd(c)
            if op >= HAVE_ARGUMENT:
                oparg = _cOrd(code[i]) + _cOrd(code[i + 1]) * 256 + extended_arg
                extended_arg = 0
                i += 2
                if op == EXTENDED_ARG:
                    extended_arg = oparg*65536
            else:
                oparg = None
            yield Instruction(op, oparg)
