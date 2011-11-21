import sys
import iu

# Search all import directors for a PYZOwner one
for im in sys.importManager.metapath:
    if isinstance(im, iu.PathImportDirector):
        for arch in im.shadowpath.values():
            if isinstance(arch, archive.PYZOwner):
                # import all modules `*ImagePlugin`
                for name in arch.pyz.contents():
                    if name.startswith('PIL.') and name.endswith('ImagePlugin'):
                        __import__(name)
