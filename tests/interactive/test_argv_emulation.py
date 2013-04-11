import sys
print "Argv from python:", sys.argv



# testing the argv capturing capability on the Mac is not that easy, but doable.  First, build the app bundle
# with PyInstaller.  The result should be TestArgvEmu.app.  Then, create a file called Info.plist and place the attached
# text into it, and copy it to TestArgvEmu.app/Contents/.  Finally, create a file called "a.foo", and drag/drop that 
# file onto the TestArgvEmu.app's icon in the Finder.  The app will very briefly run, and should print an output to 
# stdout, which is viewable in the Mac's Console app.  The output should read something like:
#   
#   Argv from python: ['/the/path/to/the/app','/the/path/to/the/file/a.foo'] 



"""
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
        <key>CFBundleDevelopmentRegion</key>
        <string>English</string>
        <key>CFBundleDisplayName</key>
        <string>TestArgvEmu</string>
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
        <string>TestArgvEmu</string>
        <key>CFBundleIdentifier</key>
        <string>org.pythonmac.unspecified.TestArgvEmu</string>
        <key>CFBundleInfoDictionaryVersion</key>
        <string>6.0</string>
        <key>CFBundleName</key>
        <string>TestArgvEmu</string>
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
