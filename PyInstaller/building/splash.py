# -----------------------------------------------------------------------------
# Copyright (c) 2019-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

import array
import os
import struct
import sys

from .. import log as logging
from .datastruct import Target
from .utils import misc, _check_guts_eq
from ..compat import is_win
from ..utils.misc import Structure, grouper

logger = logging.getLogger(__name__)


class BITMAPFILEHEADER(Structure):
    """BITMAPFILEHEADER is at the start of any Windows bitmap file.

    All of the integer values are stored in little-endian format
    """
    _names_ = ("bfType", "bfSize", "bfReserved1", "bfReserved2", "bfOffBits")
    _format_ = "<2s L H H L"


class BITMAPINFOHEADER(Structure):
    """BITMAPINFOHEADER stores all the image-related data for an bitmap.

    All of the integer values are stored in little-endian format.
    """
    _names_ = ("biSize", "biWidth", "biHeight", "biPlanes", "biBitCount",
               "biCompression", "biSizeImage", "biXPelsPerMeter",
               "biYPelsPerMeter", "biClrUsed", "biClrImportant")
    _format_ = "<LllHHLLllLL"


def _convert_to_colorref(rgb):
    """
    Converts a RGB value specified by 0xRRGGBB into
    0x00BBGGRR (=win32 COLORREF)
    """
    return (((rgb << 16) & 0xFF0000)
            | (rgb & 0x00FF00)  # noqa: W503
            | ((rgb >> 16) & 0x0000FF))  # noqa: W503


def _win_pre_multiply(file, image_pixels):
    """
    Pre-multiplies the color values of each pixel with its alpha value

    This is necessary on Windows for per-pixel alpha.
    """
    # RGBQUAD structure
    rgbquad_size = struct.calcsize("<BBBB")

    bitmap_bits = array.array("B")  # array of bytes
    bitmap_bits.fromfile(file, image_pixels * rgbquad_size)

    # BGRA (Blue Green Red Alpha) structure for bitmap files
    # further reading:
    # https://docs.microsoft.com/windows/win32/gdi/alpha-blending or
    # https://docs.microsoft.com/windows/win32/api/wingdi/ns-wingdi-rgbquad
    # https://docs.microsoft.com/windows/win32/api/wingdi/ns-wingdi-blendfunction
    for i, (b, g, r, a) in enumerate(grouper(bitmap_bits, 4)):
        scalar = a / 255
        bitmap_bits[i * rgbquad_size + 0] = int(b * scalar)
        bitmap_bits[i * rgbquad_size + 1] = int(g * scalar)
        bitmap_bits[i * rgbquad_size + 2] = int(r * scalar)

    return bitmap_bits.tobytes()


class SplashResourceWriter(object):
    """
    Writer for the SPLASH resources.

    This class creates the binary data that can be appended to an application.
    The bootloader can use it to display a splash screen. This binary data can
    be easily read and processed by the bootloader.
    """

    # SPLASH contains the essential data for the splash screen. C struct format
    # definition. '!' at the beginning means network byte order.
    # C struct looks like:
    #
    #    typedef struct _splash {
    #        [...]
    #        int wnd_width;
    #        int wnd_height;
    #
    #        [...]
    #        struct {
    #            int left;
    #            int top;
    #            int right;
    #            int bottom;
    #        } txt_rect;
    #        int  txt_clr;
    #        int  txt_fontsize;
    #        char txt_fontname[64];
    #
    #        [...]
    #        int  img_datalen;
    #        int  img_width;
    #        int  img_height;
    #        char img_bit_count;
    #        char bitmap[1];
    #    } SPLASH;
    #
    _splash_format_ = "!II iiii ii64s IIIb"  # followed by bitmap
    _splash_size_ = struct.calcsize(_splash_format_)

    def __init__(self, **kwargs):
        """
        kwargs:
            Window keyword arguments:
            -------------------------
            wnd_width (int):
                The width of the splash screen window.
            wnd_height (int):
                The height of the splash screen window.


            Text keyword arguments:
            -------------------------
            txt_rect (tuple):
                4x integer tuple that represents a text window on the
                splash screen where text can be displayed.
            txt_clr (int):
                Color value of the text, which can be displayed in text_rect.
            txt_fontsize (int):
                Font size for the text. The size is specified in point (pt).
            txt_fontname (str):
                Font for the text on the splash screen. The font must be
                installed on the user system, otherwise the default font is
                used.


            Image keyword arguments:
            -------------------------
            img_width (int):
                The width of the splash screen image
            img_height (int):
                The width of the splash screen image
            img_bit_count (int):
                Per-pixel bit count of the image.
            bitmap (bytes):
                Bytes that contain the color information for the splash screen.
        """
        self._wnd_width = kwargs.get('wnd_width')
        self._wnd_height = kwargs.get('wnd_height')

        (self._txt_rect_left,
         self._txt_rect_top,
         self._txt_rect_right,
         self._txt_rect_bottom) = kwargs.get('txt_rect', (0, 0, 0, 0))
        self._txt_clr = kwargs.get('txt_clr', 0)
        self._txt_fontsize = kwargs.get('txt_fontsize', 15)
        self._txt_fontname = kwargs.get('txt_fontname', "")
        if not isinstance(self._txt_fontname, bytes):
            self._txt_fontname = self._txt_fontname.encode("utf-8")

        self._img_width = kwargs.get('img_width')
        self._img_height = kwargs.get('img_height')
        self._img_bit_count = kwargs.get('img_bit_count')
        self._img_bitmap = kwargs.get('bitmap', b'')

    def write_to_file(self, path):
        header = struct.pack(
            self._splash_format_,
            # Window Dimensions
            self._wnd_width, self._wnd_height,
            # Text
            self._txt_rect_left, self._txt_rect_top,
            self._txt_rect_right, self._txt_rect_bottom,
            self._txt_clr,
            self._txt_fontsize,
            self._txt_fontname,
            # Image
            len(self._img_bitmap),
            self._img_width,
            self._img_height,
            self._img_bit_count,
        )

        with open(path, 'wb') as file:
            file.write(header)
            file.write(self._img_bitmap)
            file.flush()


class Splash(Target):
    typ = 'SPLASH'

    def __init__(self, image_file, **kwargs):
        """
        args
            image_file
                A path-like object to the image to be used. Only bitmaps (.bmp)
                or "device independent bitmaps" are supported. This bitmap can
                have 24bit or 32bit per pixel, using the BI_RGB or BI_BITFIELDS
                compression method, i.e. no compression. Compressed bitmaps
                are not supported.
        kwargs:
            Splash screen options:
                text_rect
                    An optional 4x integer tuple that represents a text window
                    on the splash screen where text can be displayed. The rect
                    defines a rectangle on the bitmap by the coordinates of its
                    upper left and lower right corners.
                text_size
                    Font size for the text on the splash screen.
                    The size is measured in pt (points). (Default: 15)
                text_font
                    An optional name of a font for the text. This font must be
                    installed on the user system, otherwise the system default
                    font is used. If this parameter is omitted, the default
                    font is also used. (by default on Windows: 'Segoe UI')
                text_color
                    An optional RGB color of the text, which can be displayed
                    in text_rect. In hex color format, i.e. 0xRRGGBB, where
                    RR (red), GG (green) and BB (blue) are between 0 and 0xFF.
                    An alpha channel is not supported. (Default: 0x2b2b2b)
            Target options
                name
                    An optional alternative filename for the *.res file. If
                    not specified, a name is generated.
        """
        from ..config import CONF
        Target.__init__(self)

        # Make image path relative to .spec file
        if not os.path.isabs(image_file):
            image_file = os.path.join(CONF['specpath'], image_file)
        image_file = os.path.normpath(image_file)
        if not os.path.exists(image_file):
            raise ValueError("Image file '%s' not found" % image_file)

        self.image_file = image_file
        self.text_rect = kwargs.get("text_rect", (0, 0, 0, 0))
        self._check_txt_rect()
        self.text_color = kwargs.get("text_color", 0x2b2b2b)
        if not 0x000000 <= self.text_color <= 0xFFFFFF:
            raise ValueError("text_color has to be in rgb color range")
        self.text_size = kwargs.get("text_size", 15)
        self.text_font = kwargs.get("text_font", "")
        self.name = kwargs.get("name", None)

        if is_win:
            # On windows the text color is in BBGGRR format
            self.text_color = _convert_to_colorref(self.text_color)

        # Save the generated file separately so that it is not necessary to
        # generate the data again and again
        if self.name is None:
            self.name = os.path.splitext(self.tocfilename)[0] + '.res'

        # Warn the user that the feature may not be supported
        if sys.platform not in ["win32"]:
            logger.warning("The bootloader of the target platform '%s' does"
                           " not yet support splash screens. This platform may"
                           " be supported in future versions." % sys.platform)

        self.__postinit__()

    _GUTS = (
        # input parameters
        ('image_file', _check_guts_eq),
        ('text_rect', _check_guts_eq),
        ('text_color', _check_guts_eq),
        ('text_size', _check_guts_eq),
        ('text_font', _check_guts_eq),
        ('name', _check_guts_eq),
    )

    def _check_guts(self, data, last_build):
        if Target._check_guts(self, data, last_build):
            return True

        # check if the bitmap file was modified
        if misc.mtime(self.image_file) > last_build:
            logger.info("Building %s because file %s changed",
                        self.tocbasename, self.image_file)
            return True
        return False

    def _check_txt_rect(self):
        if len(self.text_rect) != 4:
            raise ValueError(
                "wnd_text_rect must be a tuple of four positive integers!")
        if any(not (isinstance(a, int) and a >= 0) for a in self.text_rect):
            raise ValueError(
                "wnd_text_rect must be a tuple of four positive integers!")

    def assemble(self):
        logger.info("Building Splash %s", self.name)

        with open(self.image_file, 'rb') as file:
            # analyse bitmap file header
            file_header = BITMAPFILEHEADER()
            file_header.fromfile(file)

            # Check if the bitmap magic number is correct
            if not file_header.bfType == b"BM":
                raise SystemExit('Supplied file is not a valid bitmap.')

            # Load bitmap info from file
            info_header = BITMAPINFOHEADER()
            info_header.fromfile(file)

            # Skip data from extended headers
            file.seek(file_header.bfOffBits)

            # Total number of pixels in the bitmap
            image_size = info_header.biWidth * info_header.biHeight

            # Only bitmaps with 32 bit and BI_BITFIELD
            # or with 24 bit and BI_RGB are supported.
            bitmap_type_info = (info_header.biBitCount,
                                info_header.biCompression)
            # BitCount == 32 and Compression == BI_BITFIELDS
            if bitmap_type_info == (32, 3):
                # Under Windows, at 32 bit the pixels have to be
                # pre-multiplied with their alpha values.
                if is_win:
                    logger.info("Using 32bit Bitmap, pre-multiply RGB values.")
                    bitmap_bits = _win_pre_multiply(file, image_size)

                else:
                    color_struct = struct.calcsize("<BBBB")
                    bitmap_bits = file.read(image_size * color_struct)

            # BitCount == 24 and Compression == BI_RGB
            elif bitmap_type_info == (24, 0):
                # RGBTRIPLE structure
                color_struct = struct.calcsize("<BBB")
                bitmap_bits = file.read(image_size * color_struct)

            else:
                raise SystemExit("Bitmap file format is not supported."
                                 " Please refer to the documentation.")

        splash_res = SplashResourceWriter(wnd_width=info_header.biWidth,
                                          wnd_height=info_header.biHeight,
                                          # Text
                                          txt_rect=self.text_rect,
                                          txt_clr=self.text_color,
                                          txt_fontsize=self.text_size,
                                          txt_fontname=self.text_font,
                                          # Image
                                          img_width=info_header.biWidth,
                                          img_height=info_header.biHeight,
                                          img_bit_count=info_header.biBitCount,
                                          bitmap=bitmap_bits)
        splash_res.write_to_file(self.name)
