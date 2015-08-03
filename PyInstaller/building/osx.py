#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import shutil
from PyInstaller import is_darwin
from PyInstaller.building.api import EXE, COLLECT
from PyInstaller.building.datastruct import Target, TOC, logger, _check_guts_eq
from PyInstaller.building.utils import _check_path_overlap, _rmtree, add_suffix_to_extensions, checkCache



class BUNDLE(Target):
    def __init__(self, *args, **kws):
        from ..config import CONF

        # BUNDLE only has a sense under Mac OS X, it's a noop on other platforms
        if not is_darwin:
            return

        # .icns icon for app bundle.
        # Use icon supplied by user or just use the default one from PyInstaller.
        self.icon = kws.get('icon')
        if not self.icon:
            self.icon = os.path.join(os.path.dirname(__file__),
                'bootloader', 'images', 'icon-windowed.icns')
        # Ensure icon path is absolute.
        self.icon = os.path.abspath(self.icon)

        Target.__init__(self)

        # .app bundle is created in DISTPATH.
        self.name = kws.get('name', None)
        base_name = os.path.basename(self.name)
        self.name = os.path.join(CONF['distpath'], base_name)

        self.appname = os.path.splitext(base_name)[0]
        self.version = kws.get("version", "0.0.0")
        self.toc = TOC()
        self.strip = False
        self.upx = False

        # .app bundle identifier for Code Signing
        self.bundle_identifier = kws.get('bundle_identifier')
        if not self.bundle_identifier:
            # Fallback to appname.
            self.bundle_identifier = self.appname

        self.info_plist = kws.get('info_plist', None)

        for arg in args:
            if isinstance(arg, EXE):
                self.toc.append((os.path.basename(arg.name), arg.name, arg.typ))
                self.toc.extend(arg.dependencies)
                self.strip = arg.strip
                self.upx = arg.upx
            elif isinstance(arg, TOC):
                self.toc.extend(arg)
                # TOC doesn't have a strip or upx attribute, so there is no way for us to
                # tell which cache we should draw from.
            elif isinstance(arg, COLLECT):
                self.toc.extend(arg.toc)
                self.strip = arg.strip_binaries
                self.upx = arg.upx_binaries
            else:
                logger.info("unsupported entry %s", arg.__class__.__name__)
        # Now, find values for app filepath (name), app name (appname), and name
        # of the actual executable (exename) from the first EXECUTABLE item in
        # toc, which might have come from a COLLECT too (not from an EXE).
        for inm, name, typ in self.toc:
            if typ == "EXECUTABLE":
                self.exename = name
                if self.name is None:
                    self.appname = "Mac%s" % (os.path.splitext(inm)[0],)
                    self.name = os.path.join(CONF['specpath'], self.appname + ".app")
                else:
                    self.name = os.path.join(CONF['specpath'], self.name)
                break
        self.__postinit__()

    _GUTS = (('toc', _check_guts_eq),  # additional check below
            )

    def _check_guts(self, data, last_build):
        # BUNDLE always needs to be executed, since it will clean the output
        # directory anyway to make sure there is no existing cruft accumulating
        return 1

    def assemble(self):
        if _check_path_overlap(self.name) and os.path.isdir(self.name):
            _rmtree(self.name)
        logger.info("Building BUNDLE %s", os.path.basename(self.out))

        # Create a minimal Mac bundle structure
        os.makedirs(os.path.join(self.name, "Contents", "MacOS"))
        os.makedirs(os.path.join(self.name, "Contents", "Resources"))
        os.makedirs(os.path.join(self.name, "Contents", "Frameworks"))

        # Copy icns icon to Resources directory.
        if os.path.exists(self.icon):
            shutil.copy(self.icon, os.path.join(self.name, 'Contents', 'Resources'))
        else:
            logger.warn("icon not found %s" % self.icon)

        # Key/values for a minimal Info.plist file
        info_plist_dict = {"CFBundleDisplayName": self.appname,
                           "CFBundleName": self.appname,

                           # Required by 'codesign' utility.
                           # The value for CFBundleIdentifier is used as the default unique
                           # name of your program for Code Signing purposes.
                           # It even identifies the APP for access to restricted OS X areas
                           # like Keychain.
                           #
                           # The identifier used for signing must be globally unique. The usal
                           # form for this identifier is a hierarchical name in reverse DNS
                           # notation, starting with the toplevel domain, followed by the
                           # company name, followed by the department within the company, and
                           # ending with the product name. Usually in the form:
                           #   com.mycompany.department.appname
                           # Cli option --osx-bundle-identifier sets this value.
                           "CFBundleIdentifier": self.bundle_identifier,

                           # Fix for #156 - 'MacOS' must be in the name - not sure why
                           "CFBundleExecutable": 'MacOS/%s' % os.path.basename(self.exename),
                           "CFBundleIconFile": os.path.basename(self.icon),
                           "CFBundleInfoDictionaryVersion": "6.0",
                           "CFBundlePackageType": "APPL",
                           "CFBundleShortVersionString": self.version,

                           # Setting this to 1 will cause Mac OS X *not* to show
                           # a dock icon for the PyInstaller process which
                           # decompresses the real executable's contents. As a
                           # side effect, the main application doesn't get one
                           # as well, but at startup time the loader will take
                           # care of transforming the process type.
                           "LSBackgroundOnly": "0",

                           }

        # Merge info_plist settings from spec file
        if isinstance(self.info_plist, dict) and self.info_plist:
            info_plist_dict = dict(info_plist_dict.items() + self.info_plist.items())

        info_plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>"""
        for k, v in info_plist_dict.items():
            info_plist += "<key>%s</key>\n<string>%s</string>\n" % (k, v)
        info_plist += """</dict>
</plist>"""
        f = open(os.path.join(self.name, "Contents", "Info.plist"), "w")
        f.write(info_plist)
        f.close()

        toc = add_suffix_to_extensions(self.toc)
        for inm, fnm, typ in toc:
            # Copy files from cache. This ensures that are used files with relative
            # paths to dynamic library dependencies (@executable_path)
            if typ in ('EXTENSION', 'BINARY'):
                fnm = checkCache(fnm, strip=self.strip, upx=self.upx, dist_nm=inm)
            tofnm = os.path.join(self.name, "Contents", "MacOS", inm)
            todir = os.path.dirname(tofnm)
            if not os.path.exists(todir):
                os.makedirs(todir)
            shutil.copy2(fnm, tofnm)

        logger.info('moving BUNDLE data files to Resource directory')

        ## For some hooks move resource to ./Contents/Resources dir.
        # PyQt4/PyQt5 hooks: On Mac Qt requires resources 'qt_menu.nib'.
        # It is moved from MacOS directory to Resources.
        qt_menu_dir = os.path.join(self.name, 'Contents', 'MacOS', 'qt_menu.nib')
        qt_menu_dest = os.path.join(self.name, 'Contents', 'Resources', 'qt_menu.nib')
        if os.path.exists(qt_menu_dir):
            shutil.move(qt_menu_dir, qt_menu_dest)

        # Mac OS X Code Signing does not work when .app bundle contains
        # data files in dir ./Contents/MacOS.
        #
        # Move all directories from ./MacOS/ to ./Resources and create symlinks
        # in ./MacOS.
        bin_dir =os.path.join(self.name, 'Contents', 'MacOS')
        res_dir =os.path.join(self.name, 'Contents', 'Resources')
        # Qt plugin directories does not contain data files.
        ignore_dirs = set(['qt4_plugins', 'qt5_plugins'])
        dirs = os.listdir(bin_dir)
        for d in dirs:
            abs_d = os.path.join(bin_dir, d)
            res_d = os.path.join(res_dir, d)
            if os.path.isdir(abs_d) and d not in ignore_dirs:
                shutil.move(abs_d, res_d)
                os.symlink(os.path.relpath(res_d, os.path.dirname(abs_d)), abs_d)

        return 1