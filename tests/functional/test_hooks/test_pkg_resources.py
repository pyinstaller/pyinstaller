from PyInstaller.utils.tests import importorskip

@importorskip('pkg_resources')
def test_pkg_resources_importable(pyi_builder):
    """
    Check that a trivial example using pkg_resources does build.
    """
    pyi_builder.test_script('pyi_hooks/use_pkg_resources.py')
