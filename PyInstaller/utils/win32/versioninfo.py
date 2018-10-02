# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import codecs
import struct

from ...compat import is_py3, text_read_mode, win32api

# ::TODO:: #1920 revert to using pypi version
import pefile


# TODO implement read/write version information with pefile library.
# PE version info doc: http://msdn.microsoft.com/en-us/library/ms646981.aspx
def pefile_read_version(filename):
    """
    Return structure like:

    {
        # Translation independent information.
        # VS_FIXEDFILEINFO - Contains version information about a file. This information is language and code page independent.
        u'FileVersion':      (1, 2, 3, 4),
        u'ProductVersion':   (9, 10, 11, 12),

        # PE files might contain several translations of version information.
        # VS_VERSIONINFO - Depicts the organization of data in a file-version resource. It is the root structure that contains all other file-version information structures.
        u'translations': {
            'lang_id1' : {
                u'Comments':         u'日本語, Unicode 対応.',
                u'CompanyName':      u'your company.',
                u'FileDescription':  u'your file desc.',
                u'FileVersion':      u'1, 2, 3, 4',
                u'InternalName':     u'your internal name.',
                u'LegalCopyright':   u'your legal copyright.',
                u'LegalTrademarks':  u'your legal trademarks.',
                u'OriginalFilename': u'your original filename.',
                u'PrivateBuild':     u'5, 6, 7, 8',
                u'ProductName':      u'your product name',
                u'ProductVersion':   u'9, 10, 11, 12',
                u'SpecialBuild':     u'13, 14, 15, 16',
            },

            'lang_id2' : {
                ...
            }
        }
    }

    Version info can contain multiple languages.
    """
    # TODO
    vers = {
        'FileVersion': (0, 0, 0, 0),
        'ProductVersion': (0, 0, 0, 0),
        'translations': {
            'lang_id1': {
                'Comments': '',
                'CompanyName': '',
                'FileDescription': '',
                'FileVersion': '',
                'InternalName': '',
                'LegalCopyright': '',
                'LegalTrademarks': '',
                'OriginalFilename': '',
                'PrivateBuild': '',
                'ProductName': '',
                'ProductVersion': '',
                'SpecialBuild': '',
            }
        }
    }
    pe = pefile.PE(filename)
    #ffi = pe.VS_FIXEDFILEINFO
    #vers['FileVersion'] = (ffi.FileVersionMS >> 16, ffi.FileVersionMS & 0xFFFF, ffi.FileVersionLS >> 16, ffi.FileVersionLS & 0xFFFF)
    #vers['ProductVersion'] = (ffi.ProductVersionMS >> 16, ffi.ProductVersionMS & 0xFFFF, ffi.ProductVersionLS >> 16, ffi.ProductVersionLS & 0xFFFF)
    #print(pe.VS_FIXEDFILEINFO.FileVersionMS)
    # TODO Only first available language is used for now.
    #vers = pe.FileInfo[0].StringTable[0].entries
    from pprint import pprint
    pprint(pe.VS_FIXEDFILEINFO)
    print(dir(pe.VS_FIXEDFILEINFO))
    print(repr(pe.VS_FIXEDFILEINFO))
    print(pe.dump_info())
    pe.close()
    return vers



# Ensures no code from the executable is executed.
LOAD_LIBRARY_AS_DATAFILE = 2


if is_py3:
    def getRaw(text):
        """
        Encodes text as UTF-16LE (Microsoft 'Unicode') for use in structs.
        `bytes` is not allowed on Python 3.
        """
        return text.encode('UTF-16LE')
else:
    def getRaw(text):
        """
        Encodes text as UTF-16LE (Microsoft 'Unicode') for use in structs.
        `unicode` is encoded to UTF-16LE, and `str` is first decoded from
        `mbcs` before being re-encoded.
        """
        if isinstance(text, str):
            text = text.decode('mbcs', errors='replace')

        return text.encode('UTF-16LE')


def decode(pathnm):
    h = win32api.LoadLibraryEx(pathnm, 0, LOAD_LIBRARY_AS_DATAFILE)
    res = win32api.EnumResourceNames(h, pefile.RESOURCE_TYPE['RT_VERSION'])
    if not len(res):
        return None
    data = win32api.LoadResource(h, pefile.RESOURCE_TYPE['RT_VERSION'],
                                 res[0])
    vs = VSVersionInfo()
    j = vs.fromRaw(data)
    win32api.FreeLibrary(h)
    return vs


def nextDWord(offset):
    """ Align `offset` to the next 4-byte boundary """
    return ((offset + 3) >> 2) << 2

if is_py3:
    def _py3_str_compat(cls):
        """
        On Python 3, the special method __str__ is equivalent to the Python 2
        method __unicode__.
        """
        cls.__str__ = cls.__unicode__
        return cls
else:
    def _py3_str_compat(cls):
        return cls

@_py3_str_compat
class VSVersionInfo:
    """
    WORD  wLength;        // length of the VS_VERSION_INFO structure
    WORD  wValueLength;   // length of the Value member
    WORD  wType;          // 1 means text, 0 means binary
    WCHAR szKey[];        // Contains the Unicode string "VS_VERSION_INFO".
    WORD  Padding1[];
    VS_FIXEDFILEINFO Value;
    WORD  Padding2[];
    WORD  Children[];     // zero or more StringFileInfo or VarFileInfo
                          // structures (or both) that are children of the
                          // current version structure.
    """

    def __init__(self, ffi=None, kids=None):
        self.ffi = ffi
        self.kids = kids or []

    def fromRaw(self, data):
        i, (sublen, vallen, wType, nm) = parseCommon(data)
        #vallen is length of the ffi, typ is 0, nm is 'VS_VERSION_INFO'.
        i = nextDWord(i)
        # Now a VS_FIXEDFILEINFO
        self.ffi = FixedFileInfo()
        j = self.ffi.fromRaw(data, i)
        i = j
        while i < sublen:
            j = i
            i, (csublen, cvallen, ctyp, nm) = parseCommon(data, i)
            if nm.strip() == u'StringFileInfo':
                sfi = StringFileInfo()
                k = sfi.fromRaw(csublen, cvallen, nm, data, i, j+csublen)
                self.kids.append(sfi)
                i = k
            else:
                vfi = VarFileInfo()
                k = vfi.fromRaw(csublen, cvallen, nm, data, i, j+csublen)
                self.kids.append(vfi)
                i = k
            i = j + csublen
            i = nextDWord(i)
        return i

    def toRaw(self):
        raw_name = getRaw(u'VS_VERSION_INFO')
        rawffi = self.ffi.toRaw()
        vallen = len(rawffi)
        typ = 0
        sublen = 6 + len(raw_name) + 2
        pad = b''
        if sublen % 4:
            pad = b'\000\000'
        sublen = sublen + len(pad) + vallen
        pad2 = b''
        if sublen % 4:
            pad2 = b'\000\000'
        tmp = b''.join([kid.toRaw() for kid in self.kids ])
        sublen = sublen + len(pad2) + len(tmp)
        return (struct.pack('hhh', sublen, vallen, typ)
                + raw_name + b'\000\000' + pad + rawffi + pad2 + tmp)

    def __unicode__(self, indent=u''):
        indent = indent + u'  '
        tmp = [kid.__unicode__(indent+u'  ')
               for kid in self.kids]
        tmp = u', \n'.join(tmp)
        return (u"""# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
%sffi=%s,
%skids=[
%s
%s]
)
""" % (indent, self.ffi.__unicode__(indent), indent, tmp, indent))


def parseCommon(data, start=0):
    i = start + 6
    (wLength, wValueLength, wType) = struct.unpack('3h', data[start:i])
    i, text = parseUString(data, i, i+wLength)
    return i, (wLength, wValueLength, wType, text)

def parseUString(data, start, limit):
    i = start
    while i < limit:
        if data[i:i+2] == b'\000\000':
            break
        i += 2
    text = data[start:i].decode('UTF-16LE')
    i += 2
    return i, text

@_py3_str_compat
class FixedFileInfo:
    """
    DWORD dwSignature;        //Contains the value 0xFEEFO4BD
    DWORD dwStrucVersion;     // binary version number of this structure.
                              // The high-order word of this member contains
                              // the major version number, and the low-order
                              // word contains the minor version number.
    DWORD dwFileVersionMS;    // most significant 32 bits of the file's binary
                              // version number
    DWORD dwFileVersionLS;    //
    DWORD dwProductVersionMS; // most significant 32 bits of the binary version
                              // number of the product with which this file was
                              // distributed
    DWORD dwProductVersionLS; //
    DWORD dwFileFlagsMask;    // bitmask that specifies the valid bits in
                              // dwFileFlags. A bit is valid only if it was
                              // defined when the file was created.
    DWORD dwFileFlags;        // VS_FF_DEBUG, VS_FF_PATCHED etc.
    DWORD dwFileOS;           // VOS_NT, VOS_WINDOWS32 etc.
    DWORD dwFileType;         // VFT_APP etc.
    DWORD dwFileSubtype;      // 0 unless VFT_DRV or VFT_FONT or VFT_VXD
    DWORD dwFileDateMS;
    DWORD dwFileDateLS;
    """
    def __init__(self, filevers=(0, 0, 0, 0), prodvers=(0, 0, 0, 0),
                 mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1,
                 subtype=0x0, date=(0, 0)):
        self.sig = 0xfeef04bd
        self.strucVersion = 0x10000
        self.fileVersionMS = (filevers[0] << 16) | (filevers[1] & 0xffff)
        self.fileVersionLS = (filevers[2] << 16) | (filevers[3] & 0xffff)
        self.productVersionMS = (prodvers[0] << 16) | (prodvers[1] & 0xffff)
        self.productVersionLS = (prodvers[2] << 16) | (prodvers[3] & 0xffff)
        self.fileFlagsMask = mask
        self.fileFlags = flags
        self.fileOS = OS
        self.fileType = fileType
        self.fileSubtype = subtype
        self.fileDateMS = date[0]
        self.fileDateLS = date[1]

    def fromRaw(self, data, i):
        (self.sig,
         self.strucVersion,
         self.fileVersionMS,
         self.fileVersionLS,
         self.productVersionMS,
         self.productVersionLS,
         self.fileFlagsMask,
         self.fileFlags,
         self.fileOS,
         self.fileType,
         self.fileSubtype,
         self.fileDateMS,
         self.fileDateLS) = struct.unpack('13l', data[i:i+52])
        return i+52

    def toRaw(self):
        return struct.pack('L12l', self.sig,
                             self.strucVersion,
                             self.fileVersionMS,
                             self.fileVersionLS,
                             self.productVersionMS,
                             self.productVersionLS,
                             self.fileFlagsMask,
                             self.fileFlags,
                             self.fileOS,
                             self.fileType,
                             self.fileSubtype,
                             self.fileDateMS,
                             self.fileDateLS)

    def __unicode__(self, indent=u''):
        fv = (self.fileVersionMS >> 16, self.fileVersionMS & 0xffff,
              self.fileVersionLS >> 16, self.fileVersionLS & 0xFFFF)
        pv = (self.productVersionMS >> 16, self.productVersionMS & 0xffff,
              self.productVersionLS >> 16, self.productVersionLS & 0xFFFF)
        fd = (self.fileDateMS, self.fileDateLS)
        tmp = [u'FixedFileInfo(',
            u'# filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)',
            u'# Set not needed items to zero 0.',
            u'filevers=%s,' % (fv,),
            u'prodvers=%s,' % (pv,),
            u"# Contains a bitmask that specifies the valid bits 'flags'r",
            u'mask=%s,' % hex(self.fileFlagsMask),
            u'# Contains a bitmask that specifies the Boolean attributes of the file.',
            u'flags=%s,' % hex(self.fileFlags),
            u'# The operating system for which this file was designed.',
            u'# 0x4 - NT and there is no need to change it.',
            u'OS=%s,' % hex(self.fileOS),
            u'# The general type of file.',
            u'# 0x1 - the file is an application.',
            u'fileType=%s,' % hex(self.fileType),
            u'# The function of the file.',
            u'# 0x0 - the function is not defined for this fileType',
            u'subtype=%s,' % hex(self.fileSubtype),
            u'# Creation date and time stamp.',
            u'date=%s' % (fd,),
            u')'
        ]
        return (u'\n'+indent+u'  ').join(tmp)


@_py3_str_compat
class StringFileInfo(object):
    """
    WORD        wLength;      // length of the version resource
    WORD        wValueLength; // length of the Value member in the current
                              // VS_VERSION_INFO structure
    WORD        wType;        // 1 means text, 0 means binary
    WCHAR       szKey[];      // Contains the Unicode string 'StringFileInfo'.
    WORD        Padding[];
    StringTable Children[];   // list of zero or more String structures
    """
    def __init__(self, kids=None):
        self.name = u'StringFileInfo'
        self.kids = kids or []

    def fromRaw(self, sublen, vallen, name, data, i, limit):
        self.name = name
        while i < limit:
            st = StringTable()
            j = st.fromRaw(data, i, limit)
            self.kids.append(st)
            i = j
        return i

    def toRaw(self):
        raw_name = getRaw(self.name)
        vallen = 0
        typ = 1
        sublen = 6 + len(raw_name) + 2
        pad = b''
        if sublen % 4:
            pad = b'\000\000'
        tmp = b''.join([kid.toRaw() for kid in self.kids])
        sublen = sublen + len(pad) + len(tmp)
        return (struct.pack('hhh', sublen, vallen, typ)
                + raw_name + b'\000\000' + pad + tmp)

    def __unicode__(self, indent=u''):
        newindent = indent + u'  '
        tmp = [kid.__unicode__(newindent)
               for kid in self.kids]
        tmp = u', \n'.join(tmp)
        return (u'%sStringFileInfo(\n%s[\n%s\n%s])'
                % (indent, newindent, tmp, newindent))


@_py3_str_compat
class StringTable:
    """
    WORD   wLength;
    WORD   wValueLength;
    WORD   wType;
    WCHAR  szKey[];
    String Children[];    // list of zero or more String structures.
    """
    def __init__(self, name=None, kids=None):
        self.name = name or u''
        self.kids = kids or []

    def fromRaw(self, data, i, limit):
        i, (cpsublen, cpwValueLength, cpwType, self.name) = parseCodePage(data, i, limit) # should be code page junk
        i = nextDWord(i)
        while i < limit:
            ss = StringStruct()
            j = ss.fromRaw(data, i, limit)
            i = j
            self.kids.append(ss)
            i = nextDWord(i)
        return i

    def toRaw(self):
        raw_name = getRaw(self.name)
        vallen = 0
        typ = 1
        sublen = 6 + len(raw_name) + 2
        tmp = []
        for kid in self.kids:
            raw = kid.toRaw()
            if len(raw) % 4:
                raw = raw + b'\000\000'
            tmp.append(raw)
        tmp = b''.join(tmp)
        sublen += len(tmp)
        return (struct.pack('hhh', sublen, vallen, typ)
                + raw_name + b'\000\000' + tmp)

    def __unicode__(self, indent=u''):
        newindent = indent + u'  '
        tmp = (u',\n%s' % newindent).join(u'%s' % (kid,) for kid in self.kids)
        return (u"%sStringTable(\n%su'%s',\n%s[%s])"
                % (indent, newindent, self.name, newindent, tmp))


@_py3_str_compat
class StringStruct:
    """
    WORD   wLength;
    WORD   wValueLength;
    WORD   wType;
    WCHAR  szKey[];
    WORD   Padding[];
    String Value[];
    """
    def __init__(self, name=None, val=None):
        self.name = name or u''
        self.val = val or u''

    def fromRaw(self, data, i, limit):
        i, (sublen, vallen, typ, self.name) = parseCommon(data, i)
        limit = i + sublen
        i = nextDWord(i)
        i, self.val = parseUString(data, i, limit)
        return i

    def toRaw(self):
        raw_name = getRaw(self.name)
        raw_val = getRaw(self.val)
        # TODO document the size of vallen and sublen.
        vallen = len(raw_val) + 2
        typ = 1
        sublen = 6 + len(raw_name) + 2
        pad = b''
        if sublen % 4:
            pad = b'\000\000'
        sublen = sublen + len(pad) + vallen
        abcd = (struct.pack('hhh', sublen, vallen, typ)
                + raw_name + b'\000\000' + pad
                + raw_val + b'\000\000')
        return abcd

    def __unicode__(self, indent=''):
        return u"StringStruct(u'%s', u'%s')" % (self.name, self.val)


def parseCodePage(data, i, limit):
    i, (sublen, wValueLength, wType, nm) = parseCommon(data, i)
    return i, (sublen, wValueLength, wType, nm)


@_py3_str_compat
class VarFileInfo:
    """
    WORD  wLength;        // length of the version resource
    WORD  wValueLength;   // length of the Value member in the current
                          // VS_VERSION_INFO structure
    WORD  wType;          // 1 means text, 0 means binary
    WCHAR szKey[];        // Contains the Unicode string 'VarFileInfo'.
    WORD  Padding[];
    Var   Children[];     // list of zero or more Var structures
    """
    def __init__(self, kids=None):
        self.kids = kids or []

    def fromRaw(self, sublen, vallen, name, data, i, limit):
        self.sublen = sublen
        self.vallen = vallen
        self.name = name
        i = nextDWord(i)
        while i < limit:
            vs = VarStruct()
            j = vs.fromRaw(data, i, limit)
            self.kids.append(vs)
            i = j
        return i

    def toRaw(self):
        self.vallen = 0
        self.wType = 1
        self.name = u'VarFileInfo'
        raw_name = getRaw(self.name)
        sublen = 6 + len(raw_name) + 2
        pad = b''
        if sublen % 4:
            pad = b'\000\000'
        tmp = b''.join([kid.toRaw() for kid in self.kids])
        self.sublen = sublen + len(pad) + len(tmp)
        return (struct.pack('hhh', self.sublen, self.vallen, self.wType)
                + raw_name + b'\000\000' + pad + tmp)

    def __unicode__(self, indent=''):
        return "%sVarFileInfo([%s])" % (indent, ', '.join(u'%s' % (kid,) for kid in self.kids))


@_py3_str_compat
class VarStruct:
    """
    WORD  wLength;        // length of the version resource
    WORD  wValueLength;   // length of the Value member in the current
                          // VS_VERSION_INFO structure
    WORD  wType;          // 1 means text, 0 means binary
    WCHAR szKey[];        // Contains the Unicode string 'Translation'
                          // or a user-defined key string value
    WORD  Padding[];      //
    WORD  Value[];        // list of one or more values that are language
                          // and code-page identifiers
    """
    def __init__(self, name=None, kids=None):
        self.name = name or u''
        self.kids = kids or []

    def fromRaw(self, data, i, limit):
        i, (self.sublen, self.wValueLength, self.wType, self.name) = parseCommon(data, i)
        i = nextDWord(i)
        for j in range(0, self.wValueLength, 2):
            kid = struct.unpack('h', data[i:i+2])[0]
            self.kids.append(kid)
            i += 2
        return i

    def toRaw(self):
        self.wValueLength = len(self.kids) * 2
        self.wType = 0
        raw_name = getRaw(self.name)
        sublen = 6 + len(raw_name) + 2
        pad = b''
        if sublen % 4:
            pad = b'\000\000'
        self.sublen = sublen + len(pad) + self.wValueLength
        tmp = b''.join([struct.pack('h', kid) for kid in self.kids])
        return (struct.pack('hhh', self.sublen, self.wValueLength, self.wType)
                + raw_name + b'\000\000' + pad + tmp)

    def __unicode__(self, indent=u''):
        return u"VarStruct(u'%s', %r)" % (self.name, self.kids)


def SetVersion(exenm, versionfile):
    if isinstance(versionfile, VSVersionInfo):
        vs = versionfile
    else:
        with codecs.open(versionfile, text_read_mode, 'utf-8') as fp:
            txt = fp.read()
        vs = eval(txt)
    hdst = win32api.BeginUpdateResource(exenm, 0)
    win32api.UpdateResource(hdst, pefile.RESOURCE_TYPE['RT_VERSION'], 1, vs.toRaw())
    win32api.EndUpdateResource (hdst, 0)
