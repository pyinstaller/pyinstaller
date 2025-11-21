#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
import fnmatch

from PyInstaller import compat
from PyInstaller import isolated
from PyInstaller import log as logging
from PyInstaller.depend import bindepend

if compat.is_darwin:
    from PyInstaller.utils import osx as osxutils

logger = logging.getLogger(__name__)


@isolated.decorate
def _get_tcl_tk_info():
    """
    Isolated-subprocess helper to retrieve the basic Tcl/Tk information:
     - tkinter_extension_file = the value of __file__ attribute of the _tkinter binary extension (path to file).
     - tcl_data_dir = path to the Tcl library/data directory.
     - tcl_version = Tcl version
     - tk_version = Tk version
     - tcl_theaded = boolean indicating whether Tcl/Tk is built with multi-threading support.
    """
    try:
        import tkinter
        import _tkinter
    except ImportError:
        # tkinter unavailable
        return None
    try:
        tcl = tkinter.Tcl()
    except tkinter.TclError:  # e.g. "Can't find a usable init.tcl in the following directories: ..."
        return None

    # Query the location of Tcl library/data directory.
    tcl_data_dir = tcl.eval("info library")

    # Check if Tcl/Tk is built with multi-threaded support (built with --enable-threads), as indicated by the presence
    # of optional `threaded` member in `tcl_platform` array.
    try:
        tcl.getvar("tcl_platform(threaded)")  # Ignore the actual value.
        tcl_threaded = True
    except tkinter.TclError:
        tcl_threaded = False

    return {
        "available": True,
        # If `_tkinter` is a built-in (as opposed to an extension), it does not have a `__file__` attribute.
        "tkinter_extension_file": getattr(_tkinter, '__file__', None),
        "tcl_version": _tkinter.TCL_VERSION,
        "tk_version": _tkinter.TK_VERSION,
        "tcl_threaded": tcl_threaded,
        "tcl_data_dir": tcl_data_dir,
    }


class TclTkInfo:
    # Root directory names of Tcl and Tk library/data directories in the frozen application. These directories are
    # originally fully versioned (e.g., tcl8.6 and tk8.6); we want to remap them to unversioned variants, so that our
    # run-time hook (pyi_rthook__tkinter.py) does not have to determine version numbers when setting `TCL_LIBRARY`
    # and `TK_LIBRARY` environment variables.
    #
    # We also cannot use plain "tk" and "tcl", because on macOS, the Tcl and Tk shared libraries might come from
    # framework bundles, and would therefore end up being collected as "Tcl" and "Tk" in the top-level application
    # directory, causing clash due to filesystem being case-insensitive by default.
    TCL_ROOTNAME = '_tcl_data'
    TK_ROOTNAME = '_tk_data'

    def __init__(self):
        pass

    def __repr__(self):
        return "TclTkInfo"

    # Delay initialization of Tcl/Tk information until until the corresponding attributes are first requested.
    def __getattr__(self, name):
        if 'available' in self.__dict__:
            # Initialization was already done, but requested attribute is not available.
            raise AttributeError(name)

        # Load Qt library info...
        self._load_tcl_tk_info()
        # ... and return the requested attribute
        return getattr(self, name)

    def _load_tcl_tk_info(self):
        logger.info("%s: initializing cached Tcl/Tk info...", self)

        # Initialize variables so that they might be accessed even if tkinter/Tcl/Tk is unavailable or if initialization
        # fails for some reason.
        self.available = False
        self.tkinter_extension_file = None
        self.tcl_version = None
        self.tk_version = None
        self.tcl_threaded = False
        self.tcl_data_dir = None

        self.tk_data_dir = None
        self.tcl_module_dir = None

        self.is_macos_system_framework = False
        self.tcl_shared_library = None
        self.tk_shared_library = None

        self.data_files = []

        try:
            tcl_tk_info = _get_tcl_tk_info()
        except Exception as e:
            logger.warning("%s: failed to obtain Tcl/Tk info: %s", self, e)
            return

        # If tkinter could not be imported, `_get_tcl_tk_info` returns None. In such cases, emit a debug message instead
        # of a warning, because this initialization might be triggered by a helper function that is trying to determine
        # availability of `tkinter` by inspecting the `available` attribute.
        if tcl_tk_info is None:
            logger.debug("%s: failed to obtain Tcl/Tk info: tkinter/_tkinter could not be imported.", self)
            return

        # Copy properties
        for key, value in tcl_tk_info.items():
            setattr(self, key, value)

        # Parse Tcl/Tk version into (major, minor) tuple.
        self.tcl_version = tuple((int(x) for x in self.tcl_version.split(".")[:2]))
        self.tk_version = tuple((int(x) for x in self.tk_version.split(".")[:2]))

        # Determine full path to Tcl and Tk shared libraries against which the `_tkinter` extension module is linked.
        # This can only be done when `_tkinter` is in fact an extension, and not a built-in. In the latter case, the
        # Tcl/Tk libraries are statically linked into python shared library, so there are no shared libraries for us
        # to discover.
        if self.tkinter_extension_file:
            try:
                (
                    self.tcl_shared_library,
                    self.tk_shared_library,
                ) = self._find_tcl_tk_shared_libraries(self.tkinter_extension_file)
            except Exception:
                logger.warning("%s: failed to determine Tcl and Tk shared library location!", self, exc_info=True)

            # macOS: check if _tkinter is linked against system-provided Tcl.framework and Tk.framework. This is the
            # case with python3 from XCode tools (and was the case with very old homebrew python builds). In such cases,
            # we should not be collecting Tcl/Tk files.
            if compat.is_darwin:
                self.is_macos_system_framework = self._check_macos_system_framework(self.tcl_shared_library)

                # Emit a warning in the unlikely event that we are dealing with Teapot-distributed version of ActiveTcl.
                if not self.is_macos_system_framework:
                    self._warn_if_using_activetcl_or_teapot(self.tcl_data_dir)

        # Infer location of Tk library/data directory. Ideally, we could infer this by running
        #
        # import tkinter
        # root = tkinter.Tk()
        # tk_data_dir = root.tk.exprstring('$tk_library')
        #
        # in the isolated subprocess as part of `_get_tcl_tk_info`. However, that is impractical, as it shows the empty
        # window, and on some platforms (e.g., linux) requires display server. Therefore, try to guess the location,
        # based on the following heuristic:
        #  - if TK_LIBRARY is defined use it.
        #  - if Tk is built as macOS framework bundle, look for Scripts sub-directory in Resources directory next to
        #    the shared library.
        #  - otherwise, look for: $tcl_root/../tkX.Y, where X and Y are Tk major and minor version.
        if "TK_LIBRARY" in os.environ:
            self.tk_data_dir = os.environ["TK_LIBRARY"]
        elif compat.is_darwin and self.tk_shared_library and (
            # is_framework_bundle_lib handles only fully-versioned framework library paths...
            (osxutils.is_framework_bundle_lib(self.tk_shared_library)) or
            # ... so manually handle top-level-symlinked variant for now.
            (self.tk_shared_library).endswith("Tk.framework/Tk")
        ):
            # Fully resolve the library path, in case it is a top-level symlink; for example, resolve
            # /Library/Frameworks/Python.framework/Versions/3.13/Frameworks/Tk.framework/Tk
            # into
            # /Library/Frameworks/Python.framework/Versions/3.13/Frameworks/Tk.framework/Versions/8.6/Tk
            tk_lib_realpath = os.path.realpath(self.tk_shared_library)
            # Resources/Scripts directory next to the shared library
            self.tk_data_dir = os.path.join(os.path.dirname(tk_lib_realpath), "Resources", "Scripts")
        else:
            self.tk_data_dir = os.path.join(
                os.path.dirname(self.tcl_data_dir),
                f"tk{self.tk_version[0]}.{self.tk_version[1]}",
            )

        # Infer location of Tcl module directory. The modules directory is separate from the library/data one, and
        # is located at $tcl_root/../tclX, where X is the major Tcl version.
        self.tcl_module_dir = os.path.join(
            os.path.dirname(self.tcl_data_dir),
            f"tcl{self.tcl_version[0]}",
        )

        # Find all data files
        if self.is_macos_system_framework:
            logger.info("%s: using macOS system Tcl/Tk framework - not collecting data files.", self)
        else:
            # Collect Tcl and Tk scripts from their corresponding library/data directories. See comment at the
            # definition of TK_ROOTNAME and TK_ROOTNAME variables.
            if os.path.isdir(self.tcl_data_dir):
                self.data_files += self._collect_files_from_directory(
                    self.tcl_data_dir,
                    prefix=self.TCL_ROOTNAME,
                    excludes=['demos', '*.lib', 'tclConfig.sh'],
                )
            else:
                logger.warning("%s: Tcl library/data directory %r does not exist!", self, self.tcl_data_dir)

            if os.path.isdir(self.tk_data_dir):
                self.data_files += self._collect_files_from_directory(
                    self.tk_data_dir,
                    prefix=self.TK_ROOTNAME,
                    excludes=['demos', '*.lib', 'tkConfig.sh'],
                )
            else:
                logger.warning("%s: Tk library/data directory %r does not exist!", self, self.tk_data_dir)

            # Collect Tcl modules from modules directory
            if os.path.isdir(self.tcl_module_dir):
                self.data_files += self._collect_files_from_directory(
                    self.tcl_module_dir,
                    prefix=os.path.basename(self.tcl_module_dir),
                )
            else:
                logger.warning("%s: Tcl module directory %r does not exist!", self, self.tcl_module_dir)

    @staticmethod
    def _collect_files_from_directory(root, prefix=None, excludes=None):
        """
        A minimal port of PyInstaller.building.datastruct.Tree() functionality, which allows us to avoid using Tree
        here. This way, the TclTkInfo data structure can be used without having PyInstaller's config context set up.
        """
        excludes = excludes or []

        todo = [(root, prefix)]
        output = []
        while todo:
            target_dir, prefix = todo.pop()

            for entry in os.listdir(target_dir):
                # Basic name-based exclusion
                if any((fnmatch.fnmatch(entry, exclude) for exclude in excludes)):
                    continue

                src_path = os.path.join(target_dir, entry)
                dest_path = os.path.join(prefix, entry) if prefix else entry

                if os.path.isdir(src_path):
                    todo.append((src_path, dest_path))
                else:
                    # Return 3-element tuples with fully-resolved dest path, since other parts of code depend on that.
                    output.append((dest_path, src_path, 'DATA'))

        return output

    @staticmethod
    def _find_tcl_tk_shared_libraries(tkinter_ext_file):
        """
        Find Tcl and Tk shared libraries against which the _tkinter extension module is linked.
        """
        tcl_lib = None
        tk_lib = None

        for _, lib_path in bindepend.get_imports(tkinter_ext_file):  # (name, fullpath) tuple
            if lib_path is None:
                continue  # Skip unresolved entries

            # For comparison, take basename of lib_path. On macOS, lib_name returned by get_imports is in fact
            # referenced name, which is not necessarily just a basename.
            lib_name = os.path.basename(lib_path)
            lib_name_lower = lib_name.lower()  # lower-case for comparisons

            if 'tcl' in lib_name_lower:
                tcl_lib = lib_path
            elif 'tk' in lib_name_lower:
                tk_lib = lib_path

        return tcl_lib, tk_lib

    @staticmethod
    def _check_macos_system_framework(tcl_shared_lib):
        # Starting with macOS 11, system libraries are hidden (unless both Python and PyInstaller's bootloader are built
        # against macOS 11.x SDK). Therefore, Tcl shared library might end up unresolved (None); but that implicitly
        # indicates that the system framework is used.
        if tcl_shared_lib is None:
            return True

        # Check if the path corresponds to the system framework, i.e., [/System]/Library/Frameworks/Tcl.framework/Tcl
        return 'Library/Frameworks/Tcl.framework' in tcl_shared_lib

    @staticmethod
    def _warn_if_using_activetcl_or_teapot(tcl_root):
        """
        Check if Tcl installation is a Teapot-distributed version of ActiveTcl, and log a non-fatal warning that the
        resulting frozen application will (likely) fail to run on other systems.

        PyInstaller does *not* freeze all ActiveTcl dependencies -- including Teapot, which is typically ignorable.
        Since Teapot is *not* ignorable in this case, this function warns of impending failure.

        See Also
        -------
        https://github.com/pyinstaller/pyinstaller/issues/621
        """
        if tcl_root is None:
            return

        # Read the "init.tcl" script and look for mentions of "activetcl" and "teapot"
        init_tcl = os.path.join(tcl_root, 'init.tcl')
        if not os.path.isfile(init_tcl):
            return

        mentions_activetcl = False
        mentions_teapot = False

        # Tcl/Tk reads files using the system encoding (https://www.tcl.tk/doc/howto/i18n.html#system_encoding);
        # on macOS, this is UTF-8.
        with open(init_tcl, 'r', encoding='utf8') as fp:
            for line in fp.readlines():
                line = line.strip().lower()
                if line.startswith('#'):
                    continue
                if 'activetcl' in line:
                    mentions_activetcl = True
                if 'teapot' in line:
                    mentions_teapot = True
                if mentions_activetcl and mentions_teapot:
                    break

        if mentions_activetcl and mentions_teapot:
            logger.warning(
                "You appear to be using an ActiveTcl build of Tcl/Tk, which PyInstaller has\n"
                "difficulty freezing. To fix this, comment out all references to 'teapot' in\n"
                f"{init_tcl!r}\n"
                "See https://github.com/pyinstaller/pyinstaller/issues/621 for more information."
            )


tcltk_info = TclTkInfo()
