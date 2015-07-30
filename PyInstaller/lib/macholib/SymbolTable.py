"""
Class to read the symbol table from a Mach-O header
"""

from PyInstaller.lib.macholib.mach_o import *

__all__ = ['SymbolTable']

# XXX: Does not support 64-bit, probably broken anyway

class SymbolTable(object):
    def __init__(self, macho, openfile=None):
        if openfile is None:
            openfile = open
        self.macho = macho.headers[0]
        self.symtab = macho.getSymbolTableCommand()
        self.dysymtab = macho.getDynamicSymbolTableCommand()
        fh = openfile(self.macho.filename, 'rb')
        try:
            if self.symtab is not None:
                self.readSymbolTable(fh)
            if self.dysymtab is not None:
                self.readDynamicSymbolTable(fh)
        finally:
            fh.close()

    def readSymbolTable(self, fh):
        cmd = self.symtab
        fh.seek(cmd.stroff)
        strtab = fh.read(cmd.strsize)
        fh.seek(cmd.symoff)
        nlists = []
        for i in xrange(cmd.nsyms):
            cmd = nlist.from_fileobj(fh)
            if cmd.n_un == 0:
                nlists.append((cmd, ''))
            else:
                nlists.append((cmd, strtab[cmd.n_un:strtab.find(b'\x00', cmd.n_un)]))
        self.nlists = nlists

    def readDynamicSymbolTable(self, fh):
        cmd = self.dysymtab
        nlists = self.nlists
        self.localsyms = nlists[cmd.ilocalsym:cmd.ilocalsym+cmd.nlocalsym]
        self.extdefsyms = nlists[cmd.iextdefsym:cmd.iextdefsym+cmd.nextdefsym]
        self.undefsyms = nlists[cmd.iundefsym:cmd.iundefsym+cmd.nundefsym]
        #if cmd.tocoff == 0:
        #    self.toc = None
        #else:
        #    self.toc = self.readtoc(fh, cmd.tocoff, cmd.ntoc)
        #if cmd.modtaboff == 0:
        #    self.modtab = None
        #else:
        #    self.modtab = self.readmodtab(fh, cmd.modtaboff, cmd.nmodtab)
        if cmd.extrefsymoff == 0:
            self.extrefsym = None
        else:
            self.extrefsym = self.readsym(fh, cmd.extrefsymoff, cmd.nextrefsyms)
        #if cmd.indirectsymoff == 0:
        #    self.indirectsym = None
        #else:
        #    self.indirectsym = self.readsym(fh, cmd.indirectsymoff, cmd.nindirectsyms)
        #if cmd.extreloff == 0:
        #    self.extrel = None
        #else:
        #    self.extrel = self.readrel(fh, cmd.extreloff, cmd.nextrel)
        #if cmd.locreloff == 0:
        #    self.locrel = None
        #else:
        #    self.locrel = self.readrel(fh, cmd.locreloff, cmd.nlocrel)

    def readtoc(self, fh, off, n):
        #print 'toc', off, n
        fh.seek(off)
        return [dylib_table_of_contents.from_fileobj(fh) for i in xrange(n)]

    def readmodtab(self, fh, off, n):
        #print 'modtab', off, n
        fh.seek(off)
        return [dylib_module.from_fileobj(fh) for i in xrange(n)]

    def readsym(self, fh, off, n):
        #print 'sym', off, n
        fh.seek(off)
        refs = []
        for i in xrange(n):
            ref = dylib_reference.from_fileobj(fh)
            isym, flags = divmod(ref.isym_flags, 256)
            refs.append((self.nlists[isym], flags))
        return refs

    def readrel(self, fh, off, n):
        #print 'rel', off, n
        fh.seek(off)
        return [relocation_info.from_fileobj(fh) for i in xrange(n)]
