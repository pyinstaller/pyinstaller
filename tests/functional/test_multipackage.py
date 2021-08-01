import pytest

from PyInstaller.utils.tests import importorskip


@importorskip('psutil')  # Used as test for nested extension
@pytest.mark.parametrize(
    "spec_file", (
        "test_multipackage1.spec",
        "test_multipackage2.spec",
        "test_multipackage3.spec",
        "test_multipackage4.spec",
        "test_multipackage5.spec",
    ),
    ids=(
        "onefile_depends_on_onefile",
        "onedir_depends_on_onefile",
        "onefile_depends_on_onedir",
        "onedir_depends_on_onedir",
        "onedir_and_onefile_depends_on_onedir",
    )
)
def test_spec_with_multipackage(pyi_builder_spec, spec_file):
    pyi_builder_spec.test_spec(spec_file)
