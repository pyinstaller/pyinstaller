#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! https://waf.io/book/index.html#_obtaining_the_waf_file

from waflib import Utils, Errors
from waflib.Configure import conf


def get_extensions(lst):
    ret = []
    for x in Utils.to_list(lst):
        if not isinstance(x, str):
            x = x.name
        ret.append(x[x.rfind('.') + 1:])
    return ret


def sniff_features(**kw):
    exts = get_extensions(kw.get('source', []))
    typ = kw['typ']
    feats = []
    for x in 'cxx cpp c++ cc C'.split():
        if x in exts:
            feats.append('cxx')
            break
    if 'c' in exts or 'vala' in exts or 'gs' in exts:
        feats.append('c')
    if 's' in exts or 'S' in exts:
        feats.append('asm')
    for x in 'f f90 F F90 for FOR'.split():
        if x in exts:
            feats.append('fc')
            break
    if 'd' in exts:
        feats.append('d')
    if 'java' in exts:
        feats.append('java')
        return 'java'
    if typ in ('program', 'shlib', 'stlib'):
        will_link = False
        for x in feats:
            if x in ('cxx', 'd', 'fc', 'c', 'asm'):
                feats.append(x + typ)
                will_link = True
        if not will_link and not kw.get('features', []):
            raise Errors.WafError('Unable to determine how to link %r, try adding eg: features="c cshlib"?' % kw)
    return feats


def set_features(kw, typ):
    kw['typ'] = typ
    kw['features'] = Utils.to_list(kw.get('features', [])) + Utils.to_list(sniff_features(**kw))


@conf
def program(bld, *k, **kw):
    set_features(kw, 'program')
    return bld(*k, **kw)


@conf
def shlib(bld, *k, **kw):
    set_features(kw, 'shlib')
    return bld(*k, **kw)


@conf
def stlib(bld, *k, **kw):
    set_features(kw, 'stlib')
    return bld(*k, **kw)


@conf
def objects(bld, *k, **kw):
    set_features(kw, 'objects')
    return bld(*k, **kw)
