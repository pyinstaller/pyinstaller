#!/usr/bin/env python
"""
Helper script for generating namespace packages for test-cases.
"""

import os
import shutil

declare_namespace_template = """
import pkg_resources
pkg_resources.declare_namespace(__name__)
"""

pkgutil_extend_path_template = """
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)
"""

module_template = """
print ('this is module %s' % __name__)
"""

setup_template = """
from setuptools import setup, find_packages

setup(
    name='%(pkgname)s',
    version='0.1',
    description='A test package for name-spaces',
    zip_safe=%(zip_safe)r,
    packages=find_packages(),
    namespace_packages = %(namespace_packages)r
    )
"""

workdir = os.getcwd()
OLDPWD = os.getcwd()

def make_package(pkgname, namespace_packages, modules, zip_safe=False,
                 declare_namespace_template=declare_namespace_template):
    base = os.path.join(workdir, pkgname)
    if os.path.exists(base):
        shutil.rmtree(base)
    os.mkdir(base)
    os.chdir(base)
    # write __init__-files for each namespaced package
    for ns in namespace_packages:
        ns = os.path.join(*ns.split('.'))
        if not os.path.exists(ns):
            os.mkdir(ns)
        ns = os.path.join(ns, '__init__.py')
        with open(ns, 'w') as outfh:
            outfh.write(declare_namespace_template)
    # write the module itself
    for mod in modules:
        mod = os.path.join(*mod.split('/'))
        ns = os.path.dirname(mod)
        if not os.path.exists(ns):
            os.mkdir(ns)
        with open(mod, 'w') as outfh:
            outfh.write(module_template)
    # write the setup.py
    with open('setup.py', 'w') as outfh:
        outfh.write(setup_template % locals())

    os.chdir(OLDPWD)


# collection of packages to be installed using
#   PYTHONPATH=. python setup.py install --install-lib .
# This will keep the __init__files of the namespace-packages.
make_package('nspkg1-aaa',
             ['nspkg1'],
             ['nspkg1/aaa/__init__.py'])
make_package('nspkg1-bbb',
             ['nspkg1', 'nspkg1.bbb'],
             ['nspkg1/bbb/zzz/__init__.py'],
             zip_safe=True)
make_package('nspkg1-ccc',
             ['nspkg1'],
             ['nspkg1/ccc.py'])
make_package('nspkg1-empty',
             ['nspkg1'],
             [],
             zip_safe=True)


# collection of packages to be installed using
#   python setup.py install --install-lib . \
#     --single-version-externally-managed --record ./install.log
# This will omit the __init__files of the namespace-packages, but
# generate a -nspkg.pth file.
make_package('nspkg2-aaa',
             ['nspkg2'],
             ['nspkg2/aaa/__init__.py'])
make_package('nspkg2-bbb',
             ['nspkg2', 'nspkg2.bbb'],
             ['nspkg2/bbb/zzz/__init__.py'],
             zip_safe=True)
make_package('nspkg2-ccc',
             ['nspkg2'],
             ['nspkg2/ccc.py'])
make_package('nspkg2-empty',
             ['nspkg2'],
             [],
             zip_safe=True)

# collection of packages to be installed using
#   PYTHONPATH=. python setup.py install --install-lib .
# This will keep the __init__files of the namespace-packages.
make_package('nspkg3-a',
             # zipped egg in front of nspkg3-aaa!
             ['nspkg3', 'nspkg3.a'],
             ['nspkg3/a/__init__.py'],
             zip_safe=True,
             declare_namespace_template=pkgutil_extend_path_template)
make_package('nspkg3-aaa',
             ['nspkg3'],
             ['nspkg3/aaa/__init__.py'],
             declare_namespace_template=pkgutil_extend_path_template)
make_package('nspkg3-bbb',
             ['nspkg3', 'nspkg3.bbb'],
             ['nspkg3/bbb/zzz/__init__.py'],
             zip_safe=True,
             declare_namespace_template=pkgutil_extend_path_template)
make_package('nspkg3-ccc',
             ['nspkg3'],
             ['nspkg3/ccc.py'],
             declare_namespace_template=pkgutil_extend_path_template)
make_package('nspkg3-empty',
             ['nspkg3'],
             [],
             zip_safe=True,
             declare_namespace_template=pkgutil_extend_path_template)
