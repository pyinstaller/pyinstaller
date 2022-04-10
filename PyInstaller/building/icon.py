#-----------------------------------------------------------------------------
# Copyright (c) 2013-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from typing import Tuple

import os


def validate_icon(icon_path: str, allowed_types: Tuple[str], convert_type: str, workpath: str) -> str:
    """
    Outputs a valid icon path or raises an Exception trying
    Checks to be sure the icon exists, and attempts to use Pillow to convert
    it to the right format if it's in an unsupported format

    Takes:
    icon_path - the icon entered by the user
    allowed_types - a tuple of icon formats that should be allowed through
        EX: ("ico", "exe")
    convert_type - the type to attempt conversion too if necessary
        EX: "icns"
    workpath - the temp directory to save any newly generated image files
    """

    # explicitly error if file not found
    if not os.path.exists(icon_path):
        raise FileNotFoundError(f"Icon input file {icon_path} not found")

    _, extension = os.path.splitext(icon_path)
    extension = extension[1:] # get rid of the "." in ".whatever"

    if extension not in allowed_types:
        try:
            from PIL import Image as PILImage
            import PIL
        except ImportError:
            PILImage = None

        if PILImage:
            try:
                generated_icon = os.path.join(workpath, f"generated{os.getpid()}.{convert_type}")
                with PILImage.open(icon_path) as im:
                    im.save(generated_icon)
                icon_path = generated_icon
            except PIL.UnidentifiedImageError:
                raise ValueError(
                    f"Something went wrong converting icon image '{icon_path}' to '.{convert_type}' with Pillow, perhaps the image format"
                    " is unsupported. Try again with a different file or use a file that can be used without conversion"
                    f" on this platform: {allowed_types}"
                )
        # if Pillow isn't found, the user is notified that they can either try and install Pillow or translate to .ico
        # however they see fit
        else:
            raise ValueError(
                f"Received icon image '{icon_path}' which exists but is not in the correct format. On this platform, only {allowed_types} "
                f"images may be used as icons. If Pillow is installed, automatic conversion "
                f"will be attempted. Please install Pillow or convert your '{extension}' file to one of {allowed_types} "
                "and try again."
            )

    return icon_path
