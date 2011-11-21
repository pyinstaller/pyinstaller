import Image

# disable "leaking" the installed version
Image.__file__ = '/'

im = Image.open("tinysample.tiff")
im.save("tinysample.png")
