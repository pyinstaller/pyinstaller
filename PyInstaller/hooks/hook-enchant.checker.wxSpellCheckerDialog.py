
# enchant.checker.wxSpellCheckerDialog causes pyinstaller to include
# whole gtk and wx libraries if they are installed. This module is
# thus ignored to prevent this.

# TODO find better workaround
def hook(mod):
    # Workaround DOES NOT work with well with python 2.6
    # let's just disable it
    #return None
    return mod
