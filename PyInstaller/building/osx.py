#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import plistlib
import shutil
from ..compat import is_darwin, FileExistsError
from .api import EXE, COLLECT
from .datastruct import Target, TOC, logger
from .utils import _check_path_overlap, _rmtree, add_suffix_to_extensions, checkCache



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
            self.icon = os.path.join(os.path.dirname(os.path.dirname(__file__)),
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
        self.console = True

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
                self.console = arg.console
            elif isinstance(arg, TOC):
                self.toc.extend(arg)
                # TOC doesn't have a strip or upx attribute, so there is no way for us to
                # tell which cache we should draw from.
            elif isinstance(arg, COLLECT):
                self.toc.extend(arg.toc)
                self.strip = arg.strip_binaries
                self.upx = arg.upx_binaries
                self.console = arg.console
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

    _GUTS = (
        # BUNDLE always builds, just want the toc to be written out
        ('toc', None),
    )

    def _check_guts(self, data, last_build):
        # BUNDLE always needs to be executed, since it will clean the output
        # directory anyway to make sure there is no existing cruft accumulating
        return 1

    def assemble(self):
        if _check_path_overlap(self.name) and os.path.isdir(self.name):
            _rmtree(self.name)
        logger.info("Building BUNDLE %s", self.tocbasename)

        # Create a minimal Mac bundle structure
        os.makedirs(os.path.join(self.name, "Contents", "MacOS"))
        os.makedirs(os.path.join(self.name, "Contents", "Resources"))
        os.makedirs(os.path.join(self.name, "Contents", "Frameworks"))

        # Copy icns icon to Resources directory.
        if os.path.exists(self.icon):
            shutil.copy(self.icon, os.path.join(self.name, 'Contents', 'Resources'))
        else:
            logger.warning("icon not found %s", self.icon)

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

                           }

        # Setting EXE console=True implies LSBackgroundOnly=True.
        # But it still can be overwrite by the user.
        if self.console:
            info_plist_dict['LSBackgroundOnly'] = True

        # Merge info_plist settings from spec file
        if isinstance(self.info_plist, dict) and self.info_plist:
            info_plist_dict.update(self.info_plist)

        plist_filename = os.path.join(self.name, "Contents", "Info.plist")
        try:
            # python >= 3.4
            with open(plist_filename, "wb") as plist_fh:
                plistlib.dump(info_plist_dict, plist_fh)
        except AttributeError:
            # python 2.7
            plistlib.writePlist(info_plist_dict, plist_filename)

        links = []
        toc = add_suffix_to_extensions(self.toc)
        for inm, fnm, typ in toc:
            # Copy files from cache. This ensures that are used files with relative
            # paths to dynamic library dependencies (@executable_path)
            if typ in ('EXTENSION', 'BINARY'):
                fnm = checkCache(fnm, strip=self.strip, upx=self.upx, dist_nm=inm)
            if typ == 'DATA':  # add all data files to a list for symlinking later
                links.append((inm, fnm))
            else:
                tofnm = os.path.join(self.name, "Contents", "MacOS", inm)
                todir = os.path.dirname(tofnm)
                if not os.path.exists(todir):
                    os.makedirs(todir)
                shutil.copy(fnm, tofnm)

        logger.info('moving BUNDLE data files to Resource directory')

        # Mac OS X Code Signing does not work when .app bundle contains
        # data files in dir ./Contents/MacOS.
        #
        # Put all data files in ./Resources and create symlinks in ./MacOS.
        bin_dir = os.path.join(self.name, 'Contents', 'MacOS')
        res_dir = os.path.join(self.name, 'Contents', 'Resources')
        for inm, fnm in links:
            if inm != 'base_library.zip':  # Don't symlink the base_library.zip for python 3
                tofnm = os.path.join(res_dir, inm)
                todir = os.path.dirname(tofnm)
                if not os.path.exists(todir):
                    os.makedirs(todir)
                shutil.copy(fnm, tofnm)
                base_path = os.path.split(inm)[0]
                if base_path:
                    if not os.path.exists(os.path.join(bin_dir, inm)):
                        path = ''
                        for part in iter(base_path.split(os.path.sep)):
                            # Build path from previous path and the next part of the base path
                            path = os.path.join(path, part)
                            try:
                                relative_source_path = os.path.relpath(os.path.join(res_dir, path),
                                                                       os.path.split(os.path.join(bin_dir, path))[0])
                                dest_path = os.path.join(bin_dir, path)
                                os.symlink(relative_source_path, dest_path)
                                break
                            except FileExistsError:
                                pass
                        if not os.path.exists(os.path.join(bin_dir, inm)):
                            relative_source_path = os.path.relpath(os.path.join(res_dir, inm),
                                                                   os.path.split(os.path.join(bin_dir, inm))[0])
                            dest_path = os.path.join(bin_dir, inm)
                            os.symlink(relative_source_path, dest_path)
                else:  # If path is empty, e.g., a top level file, try to just symlink the file
                    os.symlink(os.path.relpath(os.path.join(res_dir, inm),
                                               os.path.split(os.path.join(bin_dir, inm))[0]),
                               os.path.join(bin_dir, inm))
            else:
                shutil.copy(fnm, bin_dir)
