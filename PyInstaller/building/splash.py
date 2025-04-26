# -----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------
import io
import os
import re
import struct
import pathlib

from PyInstaller import log as logging
from PyInstaller.archive.writers import SplashWriter
from PyInstaller.building import splash_templates
from PyInstaller.building.datastruct import Target
from PyInstaller.building.utils import _check_guts_eq, _check_guts_toc, misc
from PyInstaller.compat import is_aix, is_darwin
from PyInstaller.depend import bindepend
from PyInstaller.utils.hooks.tcl_tk import tcltk_info

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

logger = logging.getLogger(__name__)

# These requirement files are checked against the current splash screen script. If you wish to modify the splash screen
# and run into tcl errors/bad behavior, this is a good place to start and add components your implementation of the
# splash screen might use.
# NOTE: these paths use the *destination* layout for Tcl/Tk scripts, which uses unversioned tcl and tk directories
# (see `PyInstaller.utils.hooks.tcl_tk.collect_tcl_tk_files`).
splash_requirements = [
    # prepended tcl/tk binaries
    os.path.join(tcltk_info.TK_ROOTNAME, "license.terms"),
    os.path.join(tcltk_info.TK_ROOTNAME, "text.tcl"),
    os.path.join(tcltk_info.TK_ROOTNAME, "tk.tcl"),
    # Used for customizable font
    os.path.join(tcltk_info.TK_ROOTNAME, "ttk", "ttk.tcl"),
    os.path.join(tcltk_info.TK_ROOTNAME, "ttk", "fonts.tcl"),
    os.path.join(tcltk_info.TK_ROOTNAME, "ttk", "cursors.tcl"),
    os.path.join(tcltk_info.TK_ROOTNAME, "ttk", "utils.tcl"),
]


class Splash(Target):
    """
    Bundles the required resources for the splash screen into a file, which will be included in the CArchive.

    A Splash has two outputs, one is itself and one is stored in splash.binaries. Both need to be passed to other
    build targets in order to enable the splash screen.
    """
    def __init__(self, image_file, binaries, datas, **kwargs):
        """
        :param str image_file:
            A path-like object to the image to be used. Only the PNG file format is supported.

            .. note:: If a different file format is supplied and PIL (Pillow) is installed, the file will be converted
                automatically.

            .. note:: *Windows*: The color ``'magenta'`` / ``'#ff00ff'`` must not be used in the image or text, as it is
                used by splash screen to indicate transparent areas. Use a similar color (e.g., ``'#ff00fe'``) instead.

            .. note:: If PIL (Pillow) is installed and the image is bigger than max_img_size, the image will be resized
                to fit into the specified area.
        :param list binaries:
            The TOC list of binaries the Analysis build target found. This TOC includes all extension modules and their
            binary dependencies. This is required to determine whether the user's program uses `tkinter`.
        :param list datas:
            The TOC list of data the Analysis build target found. This TOC includes all data-file dependencies of the
            modules. This is required to check if all splash screen requirements can be bundled.

        :keyword text_pos:
            An optional two-integer tuple that represents the origin of the text on the splash screen image. The
            origin of the text is its lower left corner. A unit in the respective coordinate system is a pixel of the
            image, its origin lies in the top left corner of the image. This parameter also acts like a switch for
            the text feature. If omitted, no text will be displayed on the splash screen. This text will be used to
            show textual progress in onefile mode.
        :type text_pos: Tuple[int, int]
        :keyword text_size:
            The desired size of the font. If the size argument is a positive number, it is interpreted as a size in
            points. If size is a negative number, its absolute value is interpreted as a size in pixels. Default: ``12``
        :type text_size: int
        :keyword text_font:
            An optional name of a font for the text. This font must be installed on the user system, otherwise the
            system default font is used. If this parameter is omitted, the default font is also used.
        :keyword text_color:
            An optional color for the text. HTML color codes (``'#40e0d0'``) and color names (``'turquoise'``) are
            supported. Default: ``'black'``
            (Windows: the color ``'magenta'`` / ``'#ff00ff'`` is used to indicate transparency, and should not be used)
        :type text_color: str
        :keyword text_default:
            The default text which will be displayed before the extraction starts. Default: ``"Initializing"``
        :type text_default: str
        :keyword full_tk:
            By default Splash bundles only the necessary files for the splash screen (some tk components). This
            options enables adding full tk and making it a requirement, meaning all tk files will be unpacked before
            the splash screen can be started. This is useful during development of the splash screen script.
            Default: ``False``
        :type full_tk: bool
        :keyword minify_script:
            The splash screen is created by executing an Tcl/Tk script. This option enables minimizing the script,
            meaning removing all non essential parts from the script. Default: ``True``
        :keyword name:
            An optional alternative filename for the .res file. If not specified, a name is generated.
        :type name: str
        :keyword script_name:
            An optional alternative filename for the Tcl script, that will be generated. If not specified, a name is
            generated.
        :type script_name: str
        :keyword max_img_size:
            Maximum size of the splash screen image as a tuple. If the supplied image exceeds this limit, it will be
            resized to fit the maximum width (to keep the original aspect ratio). This option can be disabled by
            setting it to None. Default: ``(760, 480)``
        :type max_img_size: Tuple[int, int]
        :keyword always_on_top:
            Force the splashscreen to be always on top of other windows. If disabled, other windows (e.g., from other
            applications) can cover the splash screen by user bringing them to front. This might be useful for
            frozen applications with long startup times. Default: ``True``
        :type always_on_top: bool
        """
        from ..config import CONF
        Target.__init__(self)

        # Splash screen is not supported on macOS. It operates in a secondary thread and macOS disallows UI operations
        # in any thread other than main.
        if is_darwin:
            raise SystemExit("ERROR: Splash screen is not supported on macOS.")

        # Ensure tkinter (and thus Tcl/Tk) is available.
        if not tcltk_info.available:
            raise SystemExit(
                "ERROR: Your platform does not support the splash screen feature, since tkinter is not installed. "
                "Please install tkinter and try again."
            )

        # Check if the Tcl/Tk version is supported.
        logger.info("Verifying Tcl/Tk compatibility with splash screen requirements")
        self._check_tcl_tk_compatibility()

        # Make image path relative to .spec file
        if not os.path.isabs(image_file):
            image_file = os.path.join(CONF['specpath'], image_file)
        image_file = os.path.normpath(image_file)
        if not os.path.exists(image_file):
            raise ValueError("Image file '%s' not found" % image_file)

        # Copy all arguments
        self.image_file = image_file
        self.full_tk = kwargs.get("full_tk", False)
        self.name = kwargs.get("name", None)
        self.script_name = kwargs.get("script_name", None)
        self.minify_script = kwargs.get("minify_script", True)
        self.max_img_size = kwargs.get("max_img_size", (760, 480))

        # text options
        self.text_pos = kwargs.get("text_pos", None)
        self.text_size = kwargs.get("text_size", 12)
        self.text_font = kwargs.get("text_font", "TkDefaultFont")
        self.text_color = kwargs.get("text_color", "black")
        self.text_default = kwargs.get("text_default", "Initializing")

        # always-on-top behavior
        self.always_on_top = kwargs.get("always_on_top", True)

        # Save the generated file separately so that it is not necessary to generate the data again and again
        root = os.path.splitext(self.tocfilename)[0]
        if self.name is None:
            self.name = root + '.res'
        if self.script_name is None:
            self.script_name = root + '_script.tcl'

        # Internal variables
        # Store path to _tkinter extension module, so that guts check can detect if the path changed for some reason.
        self._tkinter_file = tcltk_info.tkinter_extension_file

        # Calculated / analysed values
        self.uses_tkinter = self._uses_tkinter(self._tkinter_file, binaries)
        logger.debug("Program uses tkinter: %r", self.uses_tkinter)
        self.script = self.generate_script()
        self.tcl_lib = tcltk_info.tcl_shared_library  # full path to shared library
        self.tk_lib = tcltk_info.tk_shared_library

        assert self.tcl_lib is not None
        assert self.tk_lib is not None

        logger.debug("Using Tcl shared library: %r", self.tcl_lib)
        logger.debug("Using Tk shared library: %r", self.tk_lib)

        self.splash_requirements = set([
            # NOTE: the implicit assumption here is that Tcl and Tk shared library are collected into top-level
            # application directory, which, at tme moment, is true in practically all cases.
            os.path.basename(self.tcl_lib),
            os.path.basename(self.tk_lib),
            *splash_requirements,
        ])

        logger.info("Collect Tcl/Tk data files for the splash screen")
        tcltk_tree = tcltk_info.data_files  # 3-element tuple TOC
        if self.full_tk:
            # The user wants a full copy of Tk, so make all Tk files a requirement.
            self.splash_requirements.update(entry[0] for entry in tcltk_tree)

        # Scan for binary dependencies of the Tcl/Tk shared libraries, and add them to `binaries` TOC list (which
        # should really be called `dependencies` as it is not limited to binaries. But it is too late now, and
        # existing spec files depend on this naming). We specify these binary dependencies (which include the
        # Tcl and Tk shared libaries themselves) even if the user's program uses tkinter and they would be collected
        # anyway; let the collection mechanism deal with potential duplicates.
        tcltk_libs = [(os.path.basename(src_name), src_name, 'BINARY') for src_name in (self.tcl_lib, self.tk_lib)]
        self.binaries = bindepend.binary_dependency_analysis(tcltk_libs)

        # Put all shared library dependencies in `splash_requirements`, so they are made available in onefile mode.
        self.splash_requirements.update(entry[0] for entry in self.binaries)

        # If the user's program does not use tkinter, add resources from Tcl/Tk tree to the dependencies list.
        # Do so only for the resources that are part of splash requirements.
        if not self.uses_tkinter:
            self.binaries.extend(entry for entry in tcltk_tree if entry[0] in self.splash_requirements)

        # Check if all requirements were found.
        collected_files = set(entry[0] for entry in (binaries + datas + self.binaries))

        def _filter_requirement(filename):
            if filename not in collected_files:
                # Item is not bundled, so warn the user about it. This actually may happen on some tkinter installations
                # that are missing the license.terms file - as this file has no effect on operation of splash screen,
                # suppress the warning for it.
                if os.path.basename(filename) == 'license.terms':
                    return False

                logger.warning(
                    "The local Tcl/Tk installation is missing the file %s. The behavior of the splash screen is "
                    "therefore undefined and may be unsupported.", filename
                )
                return False
            return True

        # Remove all files which were not found.
        self.splash_requirements = set(filter(_filter_requirement, self.splash_requirements))

        logger.debug("Splash Requirements: %s", self.splash_requirements)

        # On AIX, the Tcl and Tk shared libraries might in fact be ar archives with shared object inside it, and need to
        # be `dlopen`'ed with full name (for example, `libtcl.a(libtcl.so.8.6)` and `libtk.a(libtk.so.8.6)`. So if the
        # library's suffix is .a, adjust the name accordingly, assuming fixed format for the shared object name.
        # Adjust the names at the end of this method, because preceding steps use `self.tcl_lib` and `self.tk_lib` for
        # filesystem-based operations and need the original filenames.
        if is_aix:
            _, ext = os.path.splitext(self.tcl_lib)
            if ext == '.a':
                tcl_major, tcl_minor = tcltk_info.tcl_version
                self.tcl_lib += f"(libtcl.so.{tcl_major}.{tcl_minor})"
            _, ext = os.path.splitext(self.tk_lib)
            if ext == '.a':
                tk_major, tk_minor = tcltk_info.tk_version
                self.tk_lib += f"(libtk.so.{tk_major}.{tk_minor})"

        self.__postinit__()

    _GUTS = (
        # input parameters
        ('image_file', _check_guts_eq),
        ('name', _check_guts_eq),
        ('script_name', _check_guts_eq),
        ('text_pos', _check_guts_eq),
        ('text_size', _check_guts_eq),
        ('text_font', _check_guts_eq),
        ('text_color', _check_guts_eq),
        ('text_default', _check_guts_eq),
        ('always_on_top', _check_guts_eq),
        ('full_tk', _check_guts_eq),
        ('minify_script', _check_guts_eq),
        ('max_img_size', _check_guts_eq),
        # calculated/analysed values
        ('uses_tkinter', _check_guts_eq),
        ('script', _check_guts_eq),
        ('tcl_lib', _check_guts_eq),
        ('tk_lib', _check_guts_eq),
        ('splash_requirements', _check_guts_eq),
        ('binaries', _check_guts_toc),
        # internal value
        # Check if the tkinter installation changed. This is theoretically possible if someone uses two different python
        # installations of the same version.
        ('_tkinter_file', _check_guts_eq),
    )

    def _check_guts(self, data, last_build):
        if Target._check_guts(self, data, last_build):
            return True

        # Check if the image has been modified.
        if misc.mtime(self.image_file) > last_build:
            logger.info("Building %s because file %s changed", self.tocbasename, self.image_file)
            return True

        return False

    def assemble(self):
        logger.info("Building Splash %s", self.name)

        # Function to resize a given image to fit into the area defined by max_img_size.
        def _resize_image(_image, _orig_size):
            if PILImage:
                _w, _h = _orig_size
                _ratio_w = self.max_img_size[0] / _w
                if _ratio_w < 1:
                    # Image width exceeds limit
                    _h = int(_h * _ratio_w)
                    _w = self.max_img_size[0]

                _ratio_h = self.max_img_size[1] / _h
                if _ratio_h < 1:
                    # Image height exceeds limit
                    _w = int(_w * _ratio_h)
                    _h = self.max_img_size[1]

                # If a file is given it will be open
                if isinstance(_image, PILImage.Image):
                    _img = _image
                else:
                    _img = PILImage.open(_image)
                _img_resized = _img.resize((_w, _h))

                # Save image into a stream
                _image_stream = io.BytesIO()
                _img_resized.save(_image_stream, format='PNG')
                _img.close()
                _img_resized.close()
                _image_data = _image_stream.getvalue()
                logger.info("Resized image %s from dimensions %r to (%d, %d)", self.image_file, _orig_size, _w, _h)
                return _image_data
            else:
                raise ValueError(
                    "The splash image dimensions (w: %d, h: %d) exceed max_img_size (w: %d, h:%d), but the image "
                    "cannot be resized due to missing PIL.Image! Either install the Pillow package, adjust the "
                    "max_img_size, or use an image of compatible dimensions." %
                    (_orig_size[0], _orig_size[1], self.max_img_size[0], self.max_img_size[1])
                )

        # Open image file
        image_file = open(self.image_file, 'rb')

        # Check header of the file to identify it
        if image_file.read(8) == b'\x89PNG\r\n\x1a\n':
            # self.image_file is a PNG file
            image_file.seek(16)
            img_size = (struct.unpack("!I", image_file.read(4))[0], struct.unpack("!I", image_file.read(4))[0])

            if img_size > self.max_img_size:
                # The image exceeds the maximum image size, so resize it
                image = _resize_image(self.image_file, img_size)
            else:
                image = os.path.abspath(self.image_file)
        elif PILImage:
            # Pillow is installed, meaning the image can be converted automatically
            img = PILImage.open(self.image_file, mode='r')

            if img.size > self.max_img_size:
                image = _resize_image(img, img.size)
            else:
                image_data = io.BytesIO()
                img.save(image_data, format='PNG')
                img.close()
                image = image_data.getvalue()
            logger.info("Converted image %s to PNG format", self.image_file)
        else:
            raise ValueError(
                "The image %s needs to be converted to a PNG file, but PIL.Image is not available! Either install the "
                "Pillow package, or use a PNG image for you splash screen." % (self.image_file,)
            )

        image_file.close()

        SplashWriter(
            self.name,
            self.splash_requirements,
            os.path.basename(self.tcl_lib),  # tcl86t.dll
            os.path.basename(self.tk_lib),  # tk86t.dll
            tcltk_info.TK_ROOTNAME,
            image,
            self.script
        )

    @staticmethod
    def _check_tcl_tk_compatibility():
        tcl_version = tcltk_info.tcl_version  # (major, minor) tuple
        tk_version = tcltk_info.tk_version

        if is_darwin and tcltk_info.is_macos_system_framework:
            # Outdated Tcl/Tk 8.5 system framework is not supported.
            raise SystemExit(
                "ERROR: The splash screen feature does not support macOS system framework version of Tcl/Tk."
            )

        # Test if tcl/tk version is supported
        if tcl_version < (8, 6) or tk_version < (8, 6):
            logger.warning(
                "The installed Tcl/Tk (%d.%d / %d.%d) version might not work with the splash screen feature of the "
                "bootloader, which was tested against Tcl/Tk 8.6", *tcl_version, *tk_version
            )

        # This should be impossible, since tcl/tk is released together with the same version number, but just in case
        if tcl_version != tk_version:
            logger.warning(
                "The installed version of Tcl (%d.%d) and Tk (%d.%d) do not match. PyInstaller is tested against "
                "matching versions", *tcl_version, *tk_version
            )

        # Ensure that Tcl is built with multi-threading support.
        if not tcltk_info.tcl_threaded:
            # This is a feature breaking problem, so exit.
            raise SystemExit(
                "ERROR: The installed Tcl version is not threaded. PyInstaller only supports the splash screen "
                "using threaded Tcl."
            )

        # Ensure that Tcl and Tk shared libraries are available
        if tcltk_info.tcl_shared_library is None or tcltk_info.tk_shared_library is None:
            message = \
                "ERROR: Could not determine the path to Tcl and/or Tk shared library, " \
                "which are required for splash screen."
            if not tcltk_info.tkinter_extension_file:
                message += (
                    " The _tkinter module appears to be a built-in, which likely means that python was built with "
                    "statically-linked Tcl/Tk libraries and is incompatible with splash screen."
                )
            raise SystemExit(message)

    def generate_script(self):
        """
        Generate the script for the splash screen.

        If minify_script is True, all unnecessary parts will be removed.
        """
        d = {}
        if self.text_pos is not None:
            logger.debug("Add text support to splash screen")
            d.update({
                'pad_x': self.text_pos[0],
                'pad_y': self.text_pos[1],
                'color': self.text_color,
                'font': self.text_font,
                'font_size': self.text_size,
                'default_text': self.text_default,
            })
        script = splash_templates.build_script(text_options=d, always_on_top=self.always_on_top)

        if self.minify_script:
            # Remove any documentation, empty lines and unnecessary spaces
            script = '\n'.join(
                line for line in map(lambda line: line.strip(), script.splitlines())
                if not line.startswith('#')  # documentation
                and line  # empty lines
            )
            # Remove unnecessary spaces
            script = re.sub(' +', ' ', script)

        # Write script to disk, so that it is transparent to the user what script is executed.
        with open(self.script_name, "w", encoding="utf-8") as script_file:
            script_file.write(script)
        return script

    @staticmethod
    def _uses_tkinter(tkinter_file, binaries):
        # Test for _tkinter extension instead of tkinter module, because user might use a different wrapping library for
        # Tk. Use `pathlib.PurePath` in comparisons to account for case normalization and separator normalization.
        tkinter_file = pathlib.PurePath(tkinter_file)
        for dest_name, src_name, typecode in binaries:
            if pathlib.PurePath(src_name) == tkinter_file:
                return True
        return False
