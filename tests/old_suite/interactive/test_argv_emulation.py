#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from __future__ import print_function

import sys
print("Argv from python:", sys.argv)


# Testing the argv capturing capability on the Mac is not that easy, but doable.  First, build the app bundle
# with PyInstaller, like this:
#
# python $path_to_your_pyinstaller/pyinstaller.py -w -d test_argv_emulation.py
#
# The result should be test_argv_emulation.app.  Then, create a file called Info.plist and place the attached
# text into it, and copy it to test_argv_emulation.app/Contents/.  Finally, create a file called "a.foo", and drag/drop that 
# file onto the test_argv_emulation.app's icon in the Finder.  The app will very briefly run, and should print an output to 
# stdout, which is viewable in the Mac's Console app.  The output should read something like:
#   
#   Argv from python: ['/the/path/to/the/app','/the/path/to/the/file/a.foo'] 
#
# The Mac's Console app is not terminal. Mac's Console app is a log viewer of system's messages.
# This app can be found in your Applications (icon in the taskbar), then utilities, then Console.app.
#   http://en.wikipedia.org/wiki/Console_(OS_X)


"""
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
        <key>CFBundleDevelopmentRegion</key>
        <string>English</string>
        <key>CFBundleDisplayName</key>
        <string>test_argv_emulation</string>
        <key>CFBundleDocumentTypes</key>
        <array>
                <dict>
                        <key>CFBundleTypeExtensions</key>
                        <array>
                                <string>foo</string>
                        </array>
                        <key>CFBundleTypeName</key><string>Foo Test Document</string>
                        <key>CFBundleTypeRole</key>
                        <string>Viewer</string>
                </dict>
        </array>
        <key>CFBundleExecutable</key>
        <string>test_argv_emulation</string>
        <key>CFBundleIdentifier</key>
        <string>org.pythonmac.unspecified.test_argv_emulation</string>
        <key>CFBundleInfoDictionaryVersion</key>
        <string>6.0</string>
        <key>CFBundleName</key>
        <string>test_argv_emulation</string>
        <key>CFBundlePackageType</key>
        <string>APPL</string>
        <key>CFBundleShortVersionString</key>
        <string>0.0.0</string>
        <key>CFBundleSignature</key>
        <string>????</string>
        <key>CFBundleVersion</key>
        <string>0.0.0</string>
        <key>LSHasLocalizedDisplayName</key>
        <false/>
        <key>NSHumanReadableCopyright</key>
        <string>Copyright not specified</string>
        <key>NSMainNibFile</key>
        <string>MainMenu</string>
        <key>NSPrincipalClass</key>
        <string>NSApplication</string>
</dict>
</plist>
"""
