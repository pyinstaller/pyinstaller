# hook-Image.py
# helper module for Gordon's Installer

hiddenimports = []

def install_Image(lis):
    import Image
    # PIL uses lazy initialization.
    # you candecide if you want only the
    # default stuff:
    Image.preinit()
    # or just everything:
    Image.init()
    import sys
    for name in sys.modules:
        if name[-11:] == "ImagePlugin":
            lis.append(name)

install_Image(hiddenimports)
