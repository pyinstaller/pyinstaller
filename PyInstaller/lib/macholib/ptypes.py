"""
This module defines packable types, that is types than can be easily converted to a binary format
as used in MachO headers.
"""
import struct
import sys
from itertools import izip, imap, chain, starmap
from macholib._compat import B, bytes
import warnings

__all__ = """
sizeof
BasePackable
Structure
pypackable
p_char
p_byte
p_ubyte
p_short
p_ushort
p_int
p_uint
p_long
p_ulong
p_longlong
p_ulonglong
p_int8
p_uint8
p_int16
p_uint16
p_int32
p_uint32
p_int64
p_uint64
p_float
p_double
""".split()

def sizeof(s):
    """
    Return the size of an object when packed
    """
    if hasattr(s, '_size_'):
        return s._size_

    elif isinstance(s, bytes):
        return len(s)

    raise ValueError(s)

class MetaPackable(type):
    """
    Fixed size struct.unpack-able types use from_tuple as their designated initializer
    """
    def from_mmap(cls, mm, ptr, **kw):
        return cls.from_str(mm[ptr:ptr+cls._size_], **kw)

    def from_fileobj(cls, f, **kw):
        return cls.from_str(f.read(cls._size_), **kw)

    def from_str(cls, s, **kw):
        endian = kw.get('_endian_', cls._endian_)
        return cls.from_tuple(struct.unpack(endian + cls._format_, s), **kw)

    def from_tuple(cls, tpl, **kw):
        return cls(tpl[0], **kw)

class BasePackable(object):
    _endian_ = '>'

    def to_str(self):
        raise NotImplementedError

    def to_fileobj(self, f):
        f.write(self.to_str())

    def to_mmap(self, mm, ptr):
        mm[ptr:ptr+self._size_] = self.to_str()

class Packable(BasePackable):
    """
    Fixed size single object that is (un)packable by a struct format
    """
    __metaclass__ = MetaPackable

    def to_str(self):
        cls = type(self)
        endian = getattr(self, '_endian_', cls._endian_)
        return struct.pack(endian + cls._format_, self)

def pypackable(name, pytype, format):
    """
    Create a "mix-in" class with a python type and a
    Packable with the given struct format
    """
    size, items = _formatinfo(format)
    return type(Packable)(name, (pytype, Packable), {
        '_format_': format,
        '_size_': size,
        '_items_': items,
    })

def _formatinfo(format):
    """
    Calculate the size and number of items in a struct format.
    """
    size = struct.calcsize(format)
    return size, len(struct.unpack(format, B('\x00') * size))

class MetaStructure(MetaPackable):
    """
    The metaclass of Structure objects that does all the magic.

    Since we can assume that all Structures have a fixed size,
    we can do a bunch of calculations up front and pack or
    unpack the whole thing in one struct call.
    """
    def __new__(cls, clsname, bases, dct):
        fields = dct['_fields_']
        names = []
        types = []
        structmarks = []
        format = ''
        items = 0
        size = 0

        def struct_property(name, typ):
            def _get(self):
                return self._objects_[name]
            def _set(self, obj):
                if type(obj) is not typ:
                    obj = typ(obj)
                self._objects_[name] = obj
            return property(_get, _set, typ.__name__)

        for name, typ in fields:
            dct[name] = struct_property(name, typ)
            names.append(name)
            types.append(typ)
            format += typ._format_
            size += typ._size_
            if (typ._items_ > 1):
                structmarks.append((items, typ._items_, typ))
            items += typ._items_

        dct['_structmarks_'] = structmarks
        dct['_names_'] = names
        dct['_types_'] = types
        dct['_size_'] = size
        dct['_items_'] = items
        dct['_format_'] = format
        return super(MetaStructure, cls).__new__(cls, clsname, bases, dct)

    def from_tuple(cls, tpl, **kw):
        values = []
        current = 0
        for begin, length, typ in cls._structmarks_:
            if begin > current:
                values.extend(tpl[current:begin])
            current = begin + length
            values.append(typ.from_tuple(tpl[begin:current], **kw))
        values.extend(tpl[current:])
        return cls(*values, **kw)

class Structure(BasePackable):
    __metaclass__ = MetaStructure
    _fields_ = ()

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and not kwargs and type(args[0]) is type(self):
            kwargs = args[0]._objects_
            args = ()
        self._objects_ = {}
        iargs = chain(izip(self._names_, args), kwargs.iteritems())
        for key, value in iargs:
            if key not in self._names_ and key != "_endian_":
                raise TypeError
            setattr(self, key, value)
        for key, typ in izip(self._names_, self._types_):
            if key not in self._objects_:
                self._objects_[key] = typ()

    def _get_packables(self):
        for obj in imap(self._objects_.__getitem__, self._names_):
            if obj._items_ == 1:
                yield obj
            else:
                for obj in obj._get_packables():
                    yield obj

    def to_str(self):
        return struct.pack(self._endian_ + self._format_, *self._get_packables())

    def __cmp__(self, other):
        if type(other) is not type(self):
            raise TypeError('Cannot compare objects of type %r to objects of type %r' % (type(other), type(self)))
        if sys.version_info[0] == 2:
            _cmp = cmp
        else:
            def _cmp(a, b):
                if a < b:
                    return -1
                elif a > b:
                    return 1
                elif a == b:
                    return 0
                else:
                    raise TypeError()

        for cmpval in starmap(_cmp, izip(self._get_packables(), other._get_packables())):
            if cmpval != 0:
                return cmpval
        return 0

    def __eq__(self, other):
        r = self.__cmp__(other)
        return r == 0

    def __ne__(self, other):
        r = self.__cmp__(other)
        return r != 0

    def __lt__(self, other):
        r = self.__cmp__(other)
        return r < 0

    def __le__(self, other):
        r = self.__cmp__(other)
        return r <= 0

    def __gt__(self, other):
        r = self.__cmp__(other)
        return r > 0

    def __ge__(self, other):
        r = self.__cmp__(other)
        return r >= 0


# export common packables with predictable names
p_char = pypackable('p_char', bytes, 'c')
p_int8 = pypackable('p_int8', int, 'b')
p_uint8 = pypackable('p_uint8', int, 'B')
p_int16 = pypackable('p_int16', int, 'h')
p_uint16 = pypackable('p_uint16', int, 'H')
p_int32 = pypackable('p_int32', int, 'i')
p_uint32 = pypackable('p_uint32', long, 'I')
p_int64 = pypackable('p_int64', long, 'q')
p_uint64 = pypackable('p_uint64', long, 'Q')
p_float = pypackable('p_float', float, 'f')
p_double = pypackable('p_double', float, 'd')

# Deprecated names, need trick to emit deprecation warning.
p_byte = p_int8
p_ubyte = p_uint8
p_short = p_int16
p_ushort = p_uint16
p_int = p_long = p_int32
p_uint = p_ulong = p_uint32
p_longlong = p_int64
p_ulonglong = p_uint64
