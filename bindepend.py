#! /usr/bin/env python
# Find external dependencies of binary libraries.
# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

# use dumpbin.exe (if present) to find the binary
# dependencies of an extension module.
# if dumpbin not available, pick apart the PE hdr of the binary
# while this appears to work well, it is complex and subject to
# problems with changes to PE hdrs (ie, this works only on 32 bit Intel
# Windows format binaries)
#
# Note also that you should check the results to make sure that the
# dlls are redistributable. I've listed most of the common MS dlls
# under "excludes" below; add to this list as necessary (or use the
# "excludes" option in the INSTALL section of the config file).

import os
import time
import string
import sys
import re

seen = {}
_bpath = None
iswin = sys.platform[:3] == 'win'
cygwin = sys.platform == 'cygwin'
excludes = {'KERNEL32.DLL':1,
      'ADVAPI.DLL':1,
      'MSVCRT.DLL':1,
      'ADVAPI32.DLL':1,
      'COMCTL32.DLL':1,
      'CRTDLL.DLL':1,
      'GDI32.DLL':1,
      'MFC42.DLL':1,
      'NTDLL.DLL':1,
      'OLE32.DLL':1,
      'OLEAUT32.DLL':1,
      'RPCRT4.DLL':1,
      'SHELL32.DLL':1,
      'USER32.DLL':1,
      'WINSPOOL.DRV':1,
      'WS2HELP.DLL':1,
      'WS2_32.DLL':1,
      'WSOCK32.DLL':1,
      'MSWSOCK.DLL':1,
      'WINMM.DLL':1,
      'COMDLG32.DLL':1,
##      'ZLIB.DLL':1,   # test with python 1.5.2
      'ODBC32.DLL':1,
      'VERSION.DLL':1,
      'IMM32.DLL':1,
      'DDRAW.DLL':1,
      'DCIMAN32.DLL':1,
      'OPENGL32.DLL':1,
      'GLU32.DLL':1,
      'GLUB32.DLL':1,
      '/usr/lib':1,
      '/lib':1,}

def getfullnameof(mod, xtrapath = None):
  """Return the full path name of MOD.

      MOD is the basename of a dll or pyd.
      XTRAPATH is a path or list of paths to search first.
      Return the full path name of MOD.
      Will search the full Windows search path, as well as sys.path"""
  epath = getWindowsPath() + sys.path
  if xtrapath is not None:
    if type(xtrapath) == type(''):
      epath.insert(0, xtrapath)
    else:
      epath = xtrapath + epath
  for p in epath:
    npth = os.path.join(p, mod)
    if os.path.exists(npth):
      return npth
  return ''

def getImports1(pth):
    """Find the binary dependencies of PTH.

        This implementation (not used right now) uses the MSVC utility dumpbin"""
    import tempfile
    rslt = []
    tmpf = tempfile.mktemp()
    os.system('dumpbin /IMPORTS "%s" >%s' %(pth, tmpf))
    time.sleep(0.1)
    txt = open(tmpf,'r').readlines()
    os.remove(tmpf)
    i = 0
    while i < len(txt):
        tokens = string.split(txt[i])
        if len(tokens) == 1 and string.find(tokens[0], '.') > 0:
            rslt.append(string.strip(tokens[0]))
        i = i + 1
    return rslt

def getImports2x(pth):
    """Find the binary dependencies of PTH.

        This implementation walks through the PE header"""
    import struct
    rslt = []
    try:
      f = open(pth, 'rb').read()
      pehdrd = struct.unpack('l', f[60:64])[0]  #after the MSDOS loader is the offset of the peheader
      magic = struct.unpack('l', f[pehdrd:pehdrd+4])[0] # pehdr starts with magic 'PE\000\000' (or 17744)
                                                        # then 20 bytes of COFF header
      numsecs = struct.unpack('h', f[pehdrd+6:pehdrd+8])[0] # whence we get number of sections
      opthdrmagic = struct.unpack('h', f[pehdrd+24:pehdrd+26])[0]
      if opthdrmagic == 0x10b: # PE32 format
          numdictoffset = 116
          importoffset = 128
      elif opthdrmagic == 0x20b: # PE32+ format
          numdictoffset = 132
          importoffset = 148
      else:
          print "E: bindepend cannot analyze %s - unknown header format! %x" % (pth, opthdrmagic)
          return rslt
      numdirs = struct.unpack('l', f[pehdrd+numdictoffset:pehdrd+numdictoffset+4])[0]
      idata = ''
      if magic == 17744:
          importsec, sz = struct.unpack('2l', f[pehdrd+importoffset:pehdrd+importoffset+8])
          if sz == 0:
              return rslt
          secttbl = pehdrd + numdictoffset + 4 + 8*numdirs
          secttblfmt = '8s7l2h'
          seclist = []
          for i in range(numsecs):
              seclist.append(struct.unpack(secttblfmt, f[secttbl+i*40:secttbl+(i+1)*40]))
              #nm, vsz, va, rsz, praw, preloc, plnnums, qrelocs, qlnnums, flags \
              # = seclist[-1]
          for i in range(len(seclist)-1):
              if seclist[i][2] <= importsec < seclist[i+1][2]:
                  break
          vbase = seclist[i][2]
          raw = seclist[i][4]
          idatastart = raw + importsec - vbase
          idata = f[idatastart:idatastart+seclist[i][1]]
          i = 0
          while 1:
              chunk = idata[i*20:(i+1)*20]
              if len(chunk) != 20:
                  print "E: premature end of import table (chunk is %d, not 20)" % len(chunk)
                  break
              vsa =  struct.unpack('5l', chunk)[3]
              if vsa == 0:
                  break
              sa = raw + vsa - vbase
              end = string.find(f, '\000', sa)
              nm = f[sa:end]
              if nm:
                  rslt.append(nm)
              i = i + 1
      else:
          print "E: bindepend cannot analyze %s - file is not in PE format!" % pth
    except IOError:
        print "E: bindepend cannot analyze %s - file not found!" % pth
    #except struct.error:
    #    print "E: bindepend cannot analyze %s - error walking thru pehdr" % pth
    return rslt

def getImports2(path):
    """Find the binary dependencies of PTH.

        This implementation walks through the PE header"""
    import struct
    f = open(path, 'rb')
    # skip the MSDOS loader
    f.seek(60)
    # get offset to PE header
    offset = struct.unpack('l', f.read(4))[0]
    f.seek(offset)
    signature = struct.unpack('l', f.read(4))[0]
    coffhdrfmt = 'hhlllhh'
    rawcoffhdr = f.read(struct.calcsize(coffhdrfmt))
    coffhdr = struct.unpack(coffhdrfmt, rawcoffhdr)
    coffhdr_numsections = coffhdr[1]

    opthdrfmt = 'hbblllllllllhhhhhhllllhhllllll'
    rawopthdr = f.read(struct.calcsize(opthdrfmt))
    opthdr = struct.unpack(opthdrfmt, rawopthdr)
    opthdr_numrvas = opthdr[-1]

    datadirs = []
    datadirsize = struct.calcsize('ll') # virtual address, size
    for i in range(opthdr_numrvas):
        rawdatadir = f.read(datadirsize)
        datadirs.append(struct.unpack('ll', rawdatadir))

    sectionfmt = '8s6l2hl'
    sectionsize = struct.calcsize(sectionfmt)
    sections = []
    for i in range(coffhdr_numsections):
        rawsection = f.read(sectionsize)
        sections.append(struct.unpack(sectionfmt, rawsection))

    importva, importsz = datadirs[1]
    if importsz == 0:
        return []
    # figure out what section it's in
    NAME, MISC, VIRTADDRESS, RAWSIZE, POINTERTORAW = range(5)
    for j in range(len(sections)-1):
        if sections[j][VIRTADDRESS] <= importva < sections[j+1][VIRTADDRESS]:
            importsection = sections[j]
            break
    else:
        if importva >= sections[-1][VIRTADDRESS]:
            importsection = sections[-1]
        else:
            print "E: import section is unavailable"
            return []
    f.seek(importsection[POINTERTORAW] + importva - importsection[VIRTADDRESS])
    data = f.read(importsz)
    iidescrfmt = 'lllll'
    CHARACTERISTICS, DATETIME, FWDRCHAIN, NAMERVA, FIRSTTHUNK = range(5)
    iidescrsz = struct.calcsize(iidescrfmt)
    dlls = []
    while data:
        iid = struct.unpack(iidescrfmt, data[:iidescrsz])
        if iid[NAMERVA] == 0:
            break
        f.seek(importsection[POINTERTORAW] + iid[NAMERVA] - importsection[VIRTADDRESS])
        nm = f.read(256)
        nm, jnk = string.split(nm, '\0', 1)
        if nm:
            dlls.append(nm)
        data = data[iidescrsz:]
    return dlls

def Dependencies(lTOC):
  """Expand LTOC to include all the closure of binary dependencies.

     LTOC is a logical table of contents, ie, a seq of tuples (name, path).
     Return LTOC expanded by all the binary dependencies of the entries
     in LTOC, except those listed in the module global EXCLUDES"""
  for nm, pth, typ in lTOC:
    fullnm = string.upper(os.path.basename(pth))
    if seen.get(string.upper(nm),0):
      continue
    #print "I: analyzing", pth
    seen[string.upper(nm)] = 1
    dlls = getImports(pth)
    for lib in dlls:
        #print "I: found", lib
        if not iswin and not cygwin:
            npth = lib
            dir, lib = os.path.split(lib)
            if excludes.get(dir,0):
                continue
        if excludes.get(string.upper(lib),0):
            continue
        if seen.get(string.upper(lib),0):
            continue
        if iswin or cygwin:
            npth = getfullnameof(lib, os.path.dirname(pth))
        if npth:
            lTOC.append((lib, npth, 'BINARY'))
        else:
            print "E: lib not found:", lib, "dependency of", pth
  return lTOC

def getImports3(pth):
    """Find the binary dependencies of PTH.

        This implementation is for ldd platforms"""
    rslt = []
    for line in os.popen('ldd "%s"' % pth).readlines():
        m = re.search(r"\s+(.*?)\s+=>\s+(.*?)\s+\(.*\)", line)
        if m:
            name, lib = m.group(1), m.group(2)
            if name[:10] == 'linux-gate':
                # linux-gate is a fake library which does not exist and
                # should be ignored. See also:
                # http://www.trilithium.com/johan/2005/08/linux-gate/
                continue
            if os.path.exists(lib):
                rslt.append(lib)
            else:
                print 'E: cannot find %s in path %s (needed by %s)' % \
                      (name, lib, pth)
    return rslt

def getImports(pth):
    """Forwards to either getImports2 or getImports3
    """
    if sys.platform[:3] == 'win' or sys.platform == 'cygwin':
        return getImports2(pth)
    return getImports3(pth)

def getWindowsPath():
    """Return the path that Windows will search for dlls."""
    global _bpath
    if _bpath is None:
        _bpath = []
        if iswin:
            try:
                import win32api
            except ImportError:
                print "W: Cannot determine your Windows or System directories"
                print "W: Please add them to your PATH if .dlls are not found"
                print "W: or install starship.python.net/skippy/win32/Downloads.html"
            else:
                sysdir = win32api.GetSystemDirectory()
                sysdir2 = os.path.normpath(os.path.join(sysdir, '..', 'SYSTEM'))
                windir = win32api.GetWindowsDirectory()
                _bpath = [sysdir, sysdir2, windir]
        _bpath.extend(string.split(os.environ.get('PATH', ''), os.pathsep))
    return _bpath

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print "Usage: python %s BINARYFILE" % sys.argv[0]
    sys.exit(0)
  print getImports(sys.argv[1])
