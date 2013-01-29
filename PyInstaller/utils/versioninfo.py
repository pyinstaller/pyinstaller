#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import win32api
import struct
import pywintypes

TEST=0

LOAD_LIBRARY_AS_DATAFILE = 2
RT_VERSION = 16

def getRaw(o):
    return str(buffer(o))


def decode(pathnm):
    h = win32api.LoadLibraryEx(pathnm, 0, LOAD_LIBRARY_AS_DATAFILE)
    nm = win32api.EnumResourceNames(h, RT_VERSION)[0]
    data = win32api.LoadResource(h, RT_VERSION, nm)
    vs = VSVersionInfo()
    j = vs.fromRaw(data)
    if TEST:
        print vs
        if data[:j] != vs.toRaw():
            print "AAAAAGGHHHH"
        glbls = {
            'VSVersionInfo': VSVersionInfo,
            'FixedFileInfo': FixedFileInfo,
            'StringFileInfo': StringFileInfo,
            'StringTable': StringTable,
            'StringStruct': StringStruct,
            'VarFileInfo': VarFileInfo,
            'VarStruct': VarStruct,
            }
        vs2 = eval(repr(vs), glbls)
        if vs.toRaw() != vs2.toRaw():
            print
            print 'reconstruction not the same!'
            print vs2
    win32api.FreeLibrary(h)
    return vs


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
        #vallen is length of the ffi, typ is 0, nm is 'VS_VERSION_INFO'
        i = ((i + 3) / 4) * 4
        # now a VS_FIXEDFILEINFO
        self.ffi = FixedFileInfo()
        j = self.ffi.fromRaw(data, i)
        #print ffi
        if TEST and data[i:j] != self.ffi.toRaw():
            print "raw:", `data[i:j]`
            print "ffi:", `self.ffi.toRaw()`
        i = j
        while i < sublen:
            j = i
            i, (csublen, cvallen, ctyp, nm) = parseCommon(data, i)
            if str(nm).strip() == "StringFileInfo":
                sfi = StringFileInfo()
                k = sfi.fromRaw(csublen, cvallen, nm, data, i, j+csublen)
                if TEST and data[j:k] != sfi.toRaw():
                    rd = data[j:k]
                    sd = sfi.toRaw()
                    for x in range(0, len(rd), 16):
                        rds = rd[x:x+16]
                        sds = sd[x:x+16]
                        if rds != sds:
                            print "rd[%s:%s+16]: %r" % (x, x, rds)
                            print "sd[%s:%s+16]: %r" % (x, x, sds)
                            print
                    print ("raw: len %d, wLength %d"
                           % (len(rd), struct.unpack('h', rd[:2])[0]))
                    print ("sfi: len %d, wLength %d"
                           % (len(sd), struct.unpack('h', sd[:2])[0]))
                self.kids.append(sfi)
                i = k
            else:
                vfi = VarFileInfo()
                k = vfi.fromRaw(csublen, cvallen, nm, data, i, j+csublen)
                self.kids.append(vfi)
                if TEST and data[j:k] != vfi.toRaw():
                    print "raw:", `data[j:k]`
                    print "vfi:", `vfi.toRaw()`
                i = k
            i = j + csublen
            i = ((i + 3) / 4) * 4
        return i

    def toRaw(self):
        nm = pywintypes.Unicode('VS_VERSION_INFO')
        rawffi = self.ffi.toRaw()
        vallen = len(rawffi)
        typ = 0
        sublen = 6 + 2*len(nm) + 2
        pad = ''
        if sublen % 4:
            pad = '\000\000'
        sublen = sublen + len(pad) + vallen
        pad2 = ''
        if sublen % 4:
            pad2 = '\000\000'
        tmp = "".join([kid.toRaw() for kid in self.kids ])
        sublen = sublen + len(pad2) + len(tmp)
        return (struct.pack('hhh', sublen, vallen, typ)
                + getRaw(nm) + '\000\000' + pad + rawffi + pad2 + tmp)

    def __repr__(self, indent=''):
        indent = indent + '  '
        tmp = [kid.__repr__(indent+'  ')
               for kid in self.kids]
        tmp = ', \n'.join(tmp)
        return ("VSVersionInfo(\n%sffi=%s,\n%skids=[\n%s\n%s]\n)"
                % (indent, self.ffi.__repr__(indent), indent,
                   tmp, indent))


def parseCommon(data, start=0):
    i = start + 6
    (wLength, wValueLength, wType) = struct.unpack('3h', data[start:i])
    #print "wLength, wValueLength, wType, i:", wLength, wValueLength, wType, i
    i, szKey = parseUString(data, i, i+wLength)
    #i = ((i + 3) / 4) * 4
    #print `data[start+6:start+wLength]`
    return i, (wLength, wValueLength, wType, szKey)

def parseUString(data, start, limit):
    i = start
    while i < limit:
        if data[i:i+2] == '\000\000':
            break
        i += 2
    szKey = pywintypes.UnicodeFromRaw(data[start:i])
    i += 2
    #print "szKey:", repr(szKey), "(consumed", i-start, "bytes - to", i, ")"
    return i, szKey


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
        self.sig = 0xfeef04bdL
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

    def __repr__(self, indent=''):
        fv = (self.fileVersionMS >> 16, self.fileVersionMS & 0xffff,
              self.fileVersionLS >> 16, self.fileVersionLS & 0xFFFF)
        pv = (self.productVersionMS >> 16, self.productVersionMS & 0xffff,
              self.productVersionLS >> 16, self.productVersionLS & 0xFFFF)
        fd = (self.fileDateMS, self.fileDateLS)
        tmp = ["FixedFileInfo(",
               "filevers=%s," % fv,
               "prodvers=%s," % pv,
               "mask=%s," % hex(self.fileFlagsMask),
               "flags=%s," % hex(self.fileFlags),
               "OS=%s," % hex(self.fileOS),
               "fileType=%s," % hex(self.fileType),
               "subtype=%s," % hex(self.fileSubtype),
               "date=%s" % fd,
               ")"
              ]
        return ('\n'+indent+'  ').join(tmp)


##StringFileInfo {
##};

class StringFileInfo:
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
        self.name = "StringFileInfo"
        self.kids = kids or []

    def fromRaw(self, sublen, vallen, name, data, i, limit):
        self.name = name
        while i < limit:
            st = StringTable()
            j = st.fromRaw(data, i, limit)
            if TEST and data[i:j] != st.toRaw():
                rd = data[i:j]
                sd = st.toRaw()
                for x in range(0, len(rd), 16):
                    rds = rd[x:x+16]
                    sds = sd[x:x+16]
                    if rds != sds:
                        print "rd[%s:%s+16]: %r" % (x, x, rds)
                        print "sd[%s:%s+16]: %r" % (x, x, sds)
                        print
                print ("raw: len %d, wLength %d"
                       % (len(rd), struct.unpack('h', rd[:2])[0]))
                print (" st: len %d, wLength %d"
                       % (len(sd), struct.unpack('h', sd[:2])[0]))
            self.kids.append(st)
            i = j
        return i

    def toRaw(self):
        if type(self.name) is STRINGTYPE:
            self.name = pywintypes.Unicode(self.name)
        vallen = 0
        typ = 1
        sublen = 6 + 2*len(self.name) + 2
        pad = ''
        if sublen % 4:
            pad = '\000\000'
        tmp = ''.join([kid.toRaw() for kid in self.kids])
        sublen = sublen + len(pad) + len(tmp)
        if tmp[-2:] == '\000\000':
            sublen = sublen - 2
        return (struct.pack('hhh', sublen, vallen, typ)
                + getRaw(self.name) + '\000\000' + pad + tmp)

    def __repr__(self, indent=''):
        newindent = indent + '  '
        tmp = [kid.__repr__(newindent)
               for kid in self.kids]
        tmp = ', \n'.join(tmp)
        return ("%sStringFileInfo(\n%s[\n%s\n%s])"
                % (indent, newindent, tmp, newindent))


class StringTable:
    """
    WORD   wLength;
    WORD   wValueLength;
    WORD   wType;
    WCHAR  szKey[];
    String Children[];    // list of zero or more String structures.
    """
    def __init__(self, name=None, kids=None):
        self.name = name or ''
        self.kids = kids or []

    def fromRaw(self, data, i, limit):
        #print "Parsing StringTable"
        i, (cpsublen, cpwValueLength, cpwType, self.name) = parseCodePage(data, i, limit) # should be code page junk
        #i = ((i + 3) / 4) * 4
        while i < limit:
            ss = StringStruct()
            j = ss.fromRaw(data, i, limit)
            if TEST and data[i:j] != ss.toRaw():
                print "raw:", `data[i:j]`
                print " ss:", `ss.toRaw()`
            i = j
            self.kids.append(ss)
            i = ((i + 3) / 4) * 4
        return i

    def toRaw(self):
        if type(self.name) is STRINGTYPE:
            self.name = pywintypes.Unicode(self.name)
        vallen = 0
        typ = 1
        sublen = 6 + 2*len(self.name) + 2
        tmp = []
        for kid in self.kids:
            raw = kid.toRaw()
            if len(raw) % 4:
                raw = raw + '\000\000'
            tmp.append(raw)
        tmp = ''.join(tmp)
        sublen += len(tmp)
        if tmp[-2:] == '\000\000':
            sublen -= 2
        return (struct.pack('hhh', sublen, vallen, typ)
                + getRaw(self.name) + '\000\000' + tmp)

    def __repr__(self, indent=''):
        newindent = indent + '  '
        tmp = map(repr, self.kids)
        tmp = (',\n%s' % newindent).join(tmp)
        return ("%sStringTable(\n%s%r,\n%s[%s])"
                % (indent, newindent, self.name, newindent, tmp))


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
        self.name = name or ''
        self.val = val or ''

    def fromRaw(self, data, i, limit):
        i, (sublen, vallen, typ, self.name) = parseCommon(data, i)
        limit = i + sublen
        i = ((i + 3) / 4) * 4
        i, self.val = parseUString(data, i, limit)
        return i

    def toRaw(self):
        if type(self.name) is STRINGTYPE:
            self.name = pywintypes.Unicode(self.name)
        if type(self.val) is STRINGTYPE:
            self.val = pywintypes.Unicode(self.val)
        vallen = len(self.val) + 1
        typ = 1
        sublen = 6 + 2*len(self.name) + 2
        pad = ''
        if sublen % 4:
            pad = '\000\000'
        sublen = sublen + len(pad) + 2*vallen
        return (struct.pack('hhh', sublen, vallen, typ)
                + getRaw(self.name) + '\000\000' + pad
                + getRaw(self.val) + '\000\000')

    def __repr__(self, indent=''):
        return "StringStruct(%r, %r)" % (self.name, self.val)


def parseCodePage(data, i, limit):
    #print "Parsing CodePage"
    i, (sublen, wValueLength, wType, nm) = parseCommon(data, i)
    #i = ((i + 3) / 4) * 4
    return i, (sublen, wValueLength, wType, nm)


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
        i = ((i + 3) / 4) * 4
        while i < limit:
            vs = VarStruct()
            j = vs.fromRaw(data, i, limit)
            self.kids.append(vs)
            if TEST and data[i:j] != vs.toRaw():
                print "raw:", `data[i:j]`
                print "cmp:", `vs.toRaw()`
            i = j
        return i

    def toRaw(self):
        self.vallen = 0
        self.wType = 1
        self.name = pywintypes.Unicode('VarFileInfo')
        sublen = 6 + 2*len(self.name) + 2
        pad = ''
        if sublen % 4:
            pad = '\000\000'
        tmp = ''.join([kid.toRaw() for kid in self.kids])
        self.sublen = sublen + len(pad) + len(tmp)
        return (struct.pack('hhh', self.sublen, self.vallen, self.wType)
                + getRaw(self.name) + '\000\000' + pad + tmp)

    def __repr__(self, indent=''):
        tmp = map(repr, self.kids)
        return "%sVarFileInfo([%s])" % (indent, ', '.join(tmp))


STRINGTYPE = type('')

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
        self.name = name or ''
        self.kids = kids or []

    def fromRaw(self, data, i, limit):
        i, (self.sublen, self.wValueLength, self.wType, self.name) = parseCommon(data, i)
        i = ((i + 3) / 4) * 4
        for j in range(self.wValueLength/2):
            kid = struct.unpack('h', data[i:i+2])[0]
            self.kids.append(kid)
            i += 2
        return i

    def toRaw(self):
        self.wValueLength = len(self.kids) * 2
        self.wType = 0
        if type(self.name) is STRINGTYPE:
            self.name = pywintypes.Unicode(self.name)
        sublen = 6 + 2*len(self.name) + 2
        pad = ''
        if sublen % 4:
            pad = '\000\000'
        self.sublen = sublen + len(pad) + self.wValueLength
        tmp = ''.join([struct.pack('h', kid) for kid in self.kids])
        return (struct.pack('hhh', self.sublen, self.wValueLength, self.wType)
                + getRaw(self.name) + '\000\000' + pad + tmp)

    def __repr__(self, indent=''):
        return "VarStruct(%r, %r)" % (self.name, self.kids)


def SetVersion(exenm, versionfile):
    txt = open(versionfile, 'rU').read()
    vs = eval(txt)
    hdst = win32api.BeginUpdateResource(exenm, 0)
    win32api.UpdateResource(hdst, RT_VERSION, 1, vs.toRaw())
    win32api.EndUpdateResource (hdst, 0)


if __name__ == '__main__':
    import sys
    TEST = 1
    if len(sys.argv) < 2:
        decode('c:/Program Files/Netscape/Communicator/Program/netscape.exe')
    else:
        print "Examining", sys.argv[1]
        decode(sys.argv[1])
