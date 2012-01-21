# Contributed by jkp@kirkconsulting.co.uk
# This hook checks for the distutils hacks present when using the 
# virtualenv package.
def hook(mod):
    import distutils
    if hasattr(distutils, "distutils_path"):
        import os
        import marshal
        mod_path = os.path.join(distutils.distutils_path, "__init__.pyc")
        try:
            parsed_code = marshal.loads(open(mod_path, "rb").read()[8:])
        except IOError:
            co = compile(open(mod_path[:-1], 'rU').read(), map_path, 'exec')
        mod.__init__('distutils', mod_path, parsed_code)
    return mod
