import PIL.Image

# disable "leaking" the installed version
PIL.Image.__file__ = '/'

im = PIL.Image.open("tinysample.tiff")
im.save("tinysample.png")
