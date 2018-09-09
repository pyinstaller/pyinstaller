#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.depend import analysis
from PyInstaller.building.build_main import Analysis

def test_issue_2492(monkeypatch, tmpdir):
    # Crash if an extension module has an hidden import to ctypes (e.g. added
    # by the hook).

    # Need to set up some values
    monkeypatch.setattr('PyInstaller.config.CONF',
                        {'workpath': str(tmpdir),
                         'spec': str(tmpdir),
                         'warnfile': str(tmpdir.join('warn.txt')),
                         'dot-file': str(tmpdir.join('imports.dot')),
                         'xref-file': str(tmpdir.join('imports.xref')),
                         'hiddenimports': [],
                         'specnm': 'issue_2492_script'})
    # Speedup: avoid analyzing base_library.zip
    monkeypatch.setattr(analysis, 'PY3_BASE_MODULES', [])

    script = tmpdir.join('script.py')
    script.write('import _struct')
    # create a hook
    tmpdir.join('hook-_struct.py').write('hiddenimports = ["ctypes"]')
    a = Analysis([str(script)], hookspath=[str(tmpdir)],
                 excludes=['encodings', 'pydoc', 'xml', 'distutils'])
