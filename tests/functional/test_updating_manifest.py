# -*- encoding: utf-8 -*-

__author__ = 'Suzumizaki-Kimitaka(鈴見咲 君高)'

# -----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------

import tempfile, os, locale, codecs
import PyInstaller.utils.win32.winmanifest as winmanifest
from PyInstaller.utils.tests import skipif_notwin, skipif


test_manifest_which_uses_non_ascii = \
    r'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <assembly manifestVersion="1.0" xmlns="urn:schemas-microsoft-com:asm.v1">
      <assemblyIdentity name="日本語で書かれた名前" processorArchitecture="amd64" type="win32" version="1.0.0.0"/>
      <dependency>
        <dependentAssembly>
          <assemblyIdentity language="*" name="Microsoft.Windows.Common-Controls" processorArchitecture="*" publicKeyToken="6595b64144ccf1df" type="win32" version="6.0.0.0"/>
          <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1"/>
        </dependentAssembly>
      </dependency>
      <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
        <application>
          <supportedOS Id="{e2011457-1546-43c5-a5fe-008deee3d3f0}"/>
          <supportedOS Id="{35138b9a-5d96-4fbd-8e2d-a2440225f93a}"/>
          <supportedOS Id="{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}"/>
          <supportedOS Id="{1f676c76-80e1-4239-95bb-83d0f6d0da78}"/>
          <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
        </application>
      </compatibility>
    </assembly>
    '''


@skipif(
    codecs.lookup(locale.getpreferredencoding()).name == 'utf-8',
    reason='This test requires built-in "open" doesn\'t use UTF-8, '
           'that generally means localized Windows.'
)
@skipif_notwin
def test_reading_manifest_under_windows():
    """Check not using invalid encoding when reading XML manifest files

    Currently, Python 3.6.5, 2018-04-23, "open" built-in functions uses the
    encoding which locale.getpreferredencoding() returns. But generally,
    XML files are written with UTF-8. Because of this reason, as a convenience
    to hard coded, we should use open the manifest file with UTF-8.
    Of course, for Ideal, we should read the encoding of preamble
    ( <?xml ... > ) to determine the real encoding.
    """
    temp_handle, temp_path = tempfile.mkstemp()
    try:
        os.close(temp_handle)
        with open(temp_path, 'wt', encoding='utf-8') as write_handle:
            write_handle.write(test_manifest_which_uses_non_ascii)
        # If the code is incorrect, UnicodeDecodeError raises at next line.
        winmanifest.create_manifest(temp_path, None, None)
        assert True
    finally:
        os.remove(temp_path)


