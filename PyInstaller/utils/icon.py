from typing import Tuple

import os

def validate_icon(icon_path: str, allowed_types: Tuple[str], convert_type: str, workpath: str) -> str:
    """
    Outputs or a valid icon path or raises an Exception trying
    Checks to be sure the icon exists, and attempts to use PIL to convert
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

    extension = os.path.splitext(icon_path)[1]

    if extension not in allowed_types:
        try:
            from PIL import Image as PILImage
            import PIL
        except ImportError:
            PILImage = None

        if PILImage:
            try:
                generated_icon = os.path.join(workpath, f"generated.{convert_type}")
                with PILImage.open(icon_path) as im:
                    im.save(generated_icon)
                icon_path = generated_icon
            except PIL.UnidentifiedImageError:
                raise ValueError(
                    f"Something went wrong converting icon image '{icon_path}' to '.{convert_type}' with PIL, perhaps the image format"
                    " is unsupported. Try again with a different file or use a file that can be used without conversion"
                    f" on this platform: {allowed_types}"
                )
        # if PIL isn't found, the user is notified that they can either try and install PIL or translate to .ico
        # however they see fit
        else:
            raise ValueError(
                f"Received icon image '{icon_path}' which exists but is not in the correct format. On this platform, only {allowed_types} "
                f"images may be used as icons. If PIL is installed, automatic conversion "
                f"will be attempted. Please install PIL or convert your '{extension}' file to one of {allowed_types} "
                "and try again."
            )
    
    return icon_path
