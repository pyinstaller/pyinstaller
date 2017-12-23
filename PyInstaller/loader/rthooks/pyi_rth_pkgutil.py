from pkgutil import iter_importer_modules
def _iter_frozenimport_modules(importer, prefix=''):
    yielded = {}
    _prefix = importer._entry_name 

    for fn in sorted(importer.toc):
        if not fn.startswith(_prefix):
            continue
        nfn = fn[len(_prefix)+1:].split('.')
        modname = nfn[0]
        if modname and '.' not in modname and modname not in yielded:
            yielded[modname] = 1
            yield prefix + modname, importer.is_package(fn)

iter_importer_modules.register(eval("pyimod03_importers.FrozenPackageImporter"), _iter_frozenimport_modules)
