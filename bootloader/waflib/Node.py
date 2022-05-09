#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! https://waf.io/book/index.html#_obtaining_the_waf_file

import os, re, sys, shutil
from waflib import Utils, Errors

exclude_regs = '''
**/*~
**/#*#
**/.#*
**/%*%
**/._*
**/*.swp
**/CVS
**/CVS/**
**/.cvsignore
**/SCCS
**/SCCS/**
**/vssver.scc
**/.svn
**/.svn/**
**/BitKeeper
**/.git
**/.git/**
**/.gitignore
**/.bzr
**/.bzrignore
**/.bzr/**
**/.hg
**/.hg/**
**/_MTN
**/_MTN/**
**/.arch-ids
**/{arch}
**/_darcs
**/_darcs/**
**/.intlcache
**/.DS_Store'''


def ant_matcher(s, ignorecase):
    reflags = re.I if ignorecase else 0
    ret = []
    for x in Utils.to_list(s):
        x = x.replace('\\', '/').replace('//', '/')
        if x.endswith('/'):
            x += '**'
        accu = []
        for k in x.split('/'):
            if k == '**':
                accu.append(k)
            else:
                k = k.replace('.', '[.]').replace('*', '.*').replace('?', '.').replace('+', '\\+')
                k = '^%s$' % k
                try:
                    exp = re.compile(k, flags=reflags)
                except Exception as e:
                    raise Errors.WafError('Invalid pattern: %s' % k, e)
                else:
                    accu.append(exp)
        ret.append(accu)
    return ret


def ant_sub_filter(name, nn):
    ret = []
    for lst in nn:
        if not lst:
            pass
        elif lst[0] == '**':
            ret.append(lst)
            if len(lst) > 1:
                if lst[1].match(name):
                    ret.append(lst[2:])
            else:
                ret.append([])
        elif lst[0].match(name):
            ret.append(lst[1:])
    return ret


def ant_sub_matcher(name, pats):
    nacc = ant_sub_filter(name, pats[0])
    nrej = ant_sub_filter(name, pats[1])
    if [] in nrej:
        nacc = []
    return [nacc, nrej]


class Node(object):
    dict_class = dict
    __slots__ = ('name', 'parent', 'children', 'cache_abspath', 'cache_isdir')

    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        if parent:
            if name in parent.children:
                raise Errors.WafError('node %s exists in the parent files %r already' % (name, parent))
            parent.children[name] = self

    def __setstate__(self, data):
        self.name = data[0]
        self.parent = data[1]
        if data[2] is not None:
            self.children = self.dict_class(data[2])

    def __getstate__(self):
        return (self.name, self.parent, getattr(self, 'children', None))

    def __str__(self):
        return self.abspath()

    def __repr__(self):
        return self.abspath()

    def __copy__(self):
        raise Errors.WafError('nodes are not supposed to be copied')

    def read(self, flags='r', encoding='latin-1'):
        return Utils.readf(self.abspath(), flags, encoding)

    def write(self, data, flags='w', encoding='latin-1'):
        Utils.writef(self.abspath(), data, flags, encoding)

    def read_json(self, convert=True, encoding='utf-8'):
        import json
        object_pairs_hook = None
        if convert and sys.hexversion < 0x3000000:
            try:
                _type = unicode
            except NameError:
                _type = str

            def convert(value):
                if isinstance(value, list):
                    return [convert(element) for element in value]
                elif isinstance(value, _type):
                    return str(value)
                else:
                    return value

            def object_pairs(pairs):
                return dict((str(pair[0]), convert(pair[1])) for pair in pairs)

            object_pairs_hook = object_pairs
        return json.loads(self.read(encoding=encoding), object_pairs_hook=object_pairs_hook)

    def write_json(self, data, pretty=True):
        import json
        indent = 2
        separators = (',', ': ')
        sort_keys = pretty
        newline = os.linesep
        if not pretty:
            indent = None
            separators = (',', ':')
            newline = ''
        output = json.dumps(data, indent=indent, separators=separators, sort_keys=sort_keys) + newline
        self.write(output, encoding='utf-8')

    def exists(self):
        return os.path.exists(self.abspath())

    def isdir(self):
        return os.path.isdir(self.abspath())

    def chmod(self, val):
        os.chmod(self.abspath(), val)

    def delete(self, evict=True):
        try:
            try:
                if os.path.isdir(self.abspath()):
                    shutil.rmtree(self.abspath())
                else:
                    os.remove(self.abspath())
            except OSError:
                if os.path.exists(self.abspath()):
                    raise
        finally:
            if evict:
                self.evict()

    def evict(self):
        del self.parent.children[self.name]

    def suffix(self):
        k = max(0, self.name.rfind('.'))
        return self.name[k:]

    def height(self):
        d = self
        val = -1
        while d:
            d = d.parent
            val += 1
        return val

    def listdir(self):
        lst = Utils.listdir(self.abspath())
        lst.sort()
        return lst

    def mkdir(self):
        if self.isdir():
            return
        try:
            self.parent.mkdir()
        except OSError:
            pass
        if self.name:
            try:
                os.makedirs(self.abspath())
            except OSError:
                pass
            if not self.isdir():
                raise Errors.WafError('Could not create the directory %r' % self)
            try:
                self.children
            except AttributeError:
                self.children = self.dict_class()

    def find_node(self, lst):
        if isinstance(lst, str):
            lst = [x for x in Utils.split_path(lst) if x and x != '.']
        if lst and lst[0].startswith('\\\\') and not self.parent:
            node = self.ctx.root.make_node(lst[0])
            node.cache_isdir = True
            return node.find_node(lst[1:])
        cur = self
        for x in lst:
            if x == '..':
                cur = cur.parent or cur
                continue
            try:
                ch = cur.children
            except AttributeError:
                cur.children = self.dict_class()
            else:
                try:
                    cur = ch[x]
                    continue
                except KeyError:
                    pass
            cur = self.__class__(x, cur)
            if not cur.exists():
                cur.evict()
                return None
        if not cur.exists():
            cur.evict()
            return None
        return cur

    def make_node(self, lst):
        if isinstance(lst, str):
            lst = [x for x in Utils.split_path(lst) if x and x != '.']
        cur = self
        for x in lst:
            if x == '..':
                cur = cur.parent or cur
                continue
            try:
                cur = cur.children[x]
            except AttributeError:
                cur.children = self.dict_class()
            except KeyError:
                pass
            else:
                continue
            cur = self.__class__(x, cur)
        return cur

    def search_node(self, lst):
        if isinstance(lst, str):
            lst = [x for x in Utils.split_path(lst) if x and x != '.']
        cur = self
        for x in lst:
            if x == '..':
                cur = cur.parent or cur
            else:
                try:
                    cur = cur.children[x]
                except (AttributeError, KeyError):
                    return None
        return cur

    def path_from(self, node):
        c1 = self
        c2 = node
        c1h = c1.height()
        c2h = c2.height()
        lst = []
        up = 0
        while c1h > c2h:
            lst.append(c1.name)
            c1 = c1.parent
            c1h -= 1
        while c2h > c1h:
            up += 1
            c2 = c2.parent
            c2h -= 1
        while not c1 is c2:
            lst.append(c1.name)
            up += 1
            c1 = c1.parent
            c2 = c2.parent
        if c1.parent:
            lst.extend(['..'] * up)
            lst.reverse()
            return os.sep.join(lst) or '.'
        else:
            return self.abspath()

    def abspath(self):
        try:
            return self.cache_abspath
        except AttributeError:
            pass
        if not self.parent:
            val = os.sep
        elif not self.parent.name:
            val = os.sep + self.name
        else:
            val = self.parent.abspath() + os.sep + self.name
        self.cache_abspath = val
        return val

    if Utils.is_win32:

        def abspath(self):
            try:
                return self.cache_abspath
            except AttributeError:
                pass
            if not self.parent:
                val = ''
            elif not self.parent.name:
                val = self.name + os.sep
            else:
                val = self.parent.abspath().rstrip(os.sep) + os.sep + self.name
            self.cache_abspath = val
            return val

    def is_child_of(self, node):
        p = self
        diff = self.height() - node.height()
        while diff > 0:
            diff -= 1
            p = p.parent
        return p is node

    def ant_iter(self, accept=None, maxdepth=25, pats=[], dir=False, src=True, remove=True, quiet=False):
        dircont = self.listdir()
        try:
            lst = set(self.children.keys())
        except AttributeError:
            self.children = self.dict_class()
        else:
            if remove:
                for x in lst - set(dircont):
                    self.children[x].evict()
        for name in dircont:
            npats = accept(name, pats)
            if npats and npats[0]:
                accepted = [] in npats[0]
                node = self.make_node([name])
                isdir = node.isdir()
                if accepted:
                    if isdir:
                        if dir:
                            yield node
                    elif src:
                        yield node
                if isdir:
                    node.cache_isdir = True
                    if maxdepth:
                        for k in node.ant_iter(
                            accept=accept,
                            maxdepth=maxdepth - 1,
                            pats=npats,
                            dir=dir,
                            src=src,
                            remove=remove,
                            quiet=quiet
                        ):
                            yield k

    def ant_glob(self, *k, **kw):
        src = kw.get('src', True)
        dir = kw.get('dir')
        excl = kw.get('excl', exclude_regs)
        incl = k and k[0] or kw.get('incl', '**')
        remove = kw.get('remove', True)
        maxdepth = kw.get('maxdepth', 25)
        ignorecase = kw.get('ignorecase', False)
        quiet = kw.get('quiet', False)
        pats = (ant_matcher(incl, ignorecase), ant_matcher(excl, ignorecase))
        if kw.get('generator'):
            return Utils.lazy_generator(self.ant_iter, (ant_sub_matcher, maxdepth, pats, dir, src, remove, quiet))
        it = self.ant_iter(ant_sub_matcher, maxdepth, pats, dir, src, remove, quiet)
        if kw.get('flat'):
            return ' '.join(x.path_from(self) for x in it)
        return list(it)

    def is_src(self):
        cur = self
        x = self.ctx.srcnode
        y = self.ctx.bldnode
        while cur.parent:
            if cur is y:
                return False
            if cur is x:
                return True
            cur = cur.parent
        return False

    def is_bld(self):
        cur = self
        y = self.ctx.bldnode
        while cur.parent:
            if cur is y:
                return True
            cur = cur.parent
        return False

    def get_src(self):
        cur = self
        x = self.ctx.srcnode
        y = self.ctx.bldnode
        lst = []
        while cur.parent:
            if cur is y:
                lst.reverse()
                return x.make_node(lst)
            if cur is x:
                return self
            lst.append(cur.name)
            cur = cur.parent
        return self

    def get_bld(self):
        cur = self
        x = self.ctx.srcnode
        y = self.ctx.bldnode
        lst = []
        while cur.parent:
            if cur is y:
                return self
            if cur is x:
                lst.reverse()
                return self.ctx.bldnode.make_node(lst)
            lst.append(cur.name)
            cur = cur.parent
        lst.reverse()
        if lst and Utils.is_win32 and len(lst[0]) == 2 and lst[0].endswith(':'):
            lst[0] = lst[0][0]
        return self.ctx.bldnode.make_node(['__root__'] + lst)

    def find_resource(self, lst):
        if isinstance(lst, str):
            lst = [x for x in Utils.split_path(lst) if x and x != '.']
        node = self.get_bld().search_node(lst)
        if not node:
            node = self.get_src().find_node(lst)
        if node and node.isdir():
            return None
        return node

    def find_or_declare(self, lst):
        if isinstance(lst, str) and os.path.isabs(lst):
            node = self.ctx.root.make_node(lst)
        else:
            node = self.get_bld().make_node(lst)
        node.parent.mkdir()
        return node

    def find_dir(self, lst):
        if isinstance(lst, str):
            lst = [x for x in Utils.split_path(lst) if x and x != '.']
        node = self.find_node(lst)
        if node and not node.isdir():
            return None
        return node

    def change_ext(self, ext, ext_in=None):
        name = self.name
        if ext_in is None:
            k = name.rfind('.')
            if k >= 0:
                name = name[:k] + ext
            else:
                name = name + ext
        else:
            name = name[:-len(ext_in)] + ext
        return self.parent.find_or_declare([name])

    def bldpath(self):
        return self.path_from(self.ctx.bldnode)

    def srcpath(self):
        return self.path_from(self.ctx.srcnode)

    def relpath(self):
        cur = self
        x = self.ctx.bldnode
        while cur.parent:
            if cur is x:
                return self.bldpath()
            cur = cur.parent
        return self.srcpath()

    def bld_dir(self):
        return self.parent.bldpath()

    def h_file(self):
        return Utils.h_file(self.abspath())

    def get_bld_sig(self):
        try:
            cache = self.ctx.cache_sig
        except AttributeError:
            cache = self.ctx.cache_sig = {}
        try:
            ret = cache[self]
        except KeyError:
            p = self.abspath()
            try:
                ret = cache[self] = self.h_file()
            except EnvironmentError:
                if self.isdir():
                    st = os.stat(p)
                    ret = cache[self] = Utils.h_list([p, st.st_ino, st.st_mode])
                    return ret
                raise
        return ret


pickle_lock = Utils.threading.Lock()


class Nod3(Node):
    pass
