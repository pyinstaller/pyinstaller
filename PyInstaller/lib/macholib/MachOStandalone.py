import os

from macholib.MachOGraph import MachOGraph, MissingMachO
from macholib.util import iter_platform_files, in_system_path, mergecopy, \
    mergetree, flipwritable, has_filename_filter
from macholib.dyld import framework_info
from collections import deque

class ExcludedMachO(MissingMachO):
    pass

class FilteredMachOGraph(MachOGraph):
    def __init__(self, delegate, *args, **kwargs):
        super(FilteredMachOGraph, self).__init__(*args, **kwargs)
        self.delegate = delegate

    def createNode(self, cls, name):
        cls = self.delegate.getClass(name, cls)
        res = super(FilteredMachOGraph, self).createNode(cls, name)
        return res

    def locate(self, filename):
        newname = super(FilteredMachOGraph, self).locate(filename)
        if newname is None:
            return None
        return self.delegate.locate(newname)

class MachOStandalone(object):
    def __init__(self, base, dest=None, graph=None, env=None,
            executable_path=None):
        self.base = os.path.join(os.path.abspath(base), '')
        if dest is None:
            dest = os.path.join(self.base, 'Contents', 'Frameworks')
        self.dest = dest
        self.mm = FilteredMachOGraph(self, graph=graph, env=env,
            executable_path=executable_path)
        self.changemap = {}
        self.excludes = []
        self.pending = deque()

    def getClass(self, name, cls):
        if in_system_path(name):
            return ExcludedMachO
        for base in self.excludes:
            if name.startswith(base):
                return ExcludedMachO
        return cls

    def locate(self, filename):
        if in_system_path(filename):
            return filename
        if filename.startswith(self.base):
            return filename
        for base in self.excludes:
            if filename.startswith(base):
                return filename
        if filename in self.changemap:
            return self.changemap[filename]
        info = framework_info(filename)
        if info is None:
            res = self.copy_dylib(filename)
            self.changemap[filename] = res
            return res
        else:
            res = self.copy_framework(info)
            self.changemap[filename] = res
            return res

    def copy_dylib(self, filename):
        dest = os.path.join(self.dest, os.path.basename(filename))
        if not os.path.exists(dest):
            self.mergecopy(filename, dest)
        return dest

    def mergecopy(self, src, dest):
        return mergecopy(src, dest)

    def mergetree(self, src, dest):
        return mergetree(src, dest)

    def copy_framework(self, info):
        dest = os.path.join(self.dest, info['shortname'] + '.framework')
        destfn = os.path.join(self.dest, info['name'])
        src = os.path.join(info['location'], info['shortname'] + '.framework')
        if not os.path.exists(dest):
            self.mergetree(src, dest)
            self.pending.append((destfn, iter_platform_files(dest)))
        return destfn

    def run(self, platfiles=None, contents=None):
        mm = self.mm
        if contents is None:
            contents = '@executable_path/..'
        if platfiles is None:
            platfiles = iter_platform_files(self.base)

        for fn in platfiles:
            mm.run_file(fn)

        while self.pending:
            fmwk, files = self.pending.popleft()
            ref = mm.findNode(fmwk)
            for fn in files:
                mm.run_file(fn, caller=ref)

        changemap = {}
        skipcontents = os.path.join(os.path.dirname(self.dest), '')
        machfiles = []

        for node in mm.flatten(has_filename_filter):
            machfiles.append(node)
            dest = os.path.join(contents, node.filename[len(skipcontents):])
            changemap[node.filename] = dest

        def changefunc(path):
            res = mm.locate(path)
            return changemap.get(res)

        for node in machfiles:
            fn = mm.locate(node.filename)
            if fn is None:
                continue
            rewroteAny = False
            for header in node.headers:
                if node.rewriteLoadCommands(changefunc):
                    rewroteAny = True
            if rewroteAny:
                old_mode = flipwritable(fn)
                try:
                    f = open(fn, 'rb+')
                    for header in node.headers:
                        f.seek(0)
                        node.write(f)
                    f.seek(0, 2)
                    f.flush()
                    f.close()
                finally:
                    flipwritable(fn, old_mode)

        allfiles = [mm.locate(node.filename) for node in machfiles]
        return set(filter(None, allfiles))
