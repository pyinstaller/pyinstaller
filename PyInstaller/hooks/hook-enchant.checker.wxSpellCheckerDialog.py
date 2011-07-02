
# enchant.checker.wxSpellCheckerDialog causes pyinstaller to include
# whole gtk and wx libraries if they are installed. This module is
# thus ignored to prevent this.
# TODO find better workaround
def hook(mod):
    return None
