from PyInstaller.utils.tests import importorskip

@importorskip('pkg_resources')
def test_pkg_resources_importable(pyi_builder):
    """
    Check that a trivial example using pkg_resources does build.
    """
    pyi_builder.test_source(
        """
        import pkg_resources
        pkg_resources.working_set.require()
        """)
