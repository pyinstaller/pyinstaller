import pytest


@pytest.mark.skip()
def test_multipackage1(pyi_builder_spec):
    pyi_builder_spec.test_spec('test_multipackage1.spec')


def test_multipackage2(pyi_builder_spec):
    pyi_builder_spec.test_spec('test_multipackage2.spec')


def test_multipackage3(pyi_builder_spec):
    pyi_builder_spec.test_spec('test_multipackage3.spec')


def test_multipackage4(pyi_builder_spec):
    pyi_builder_spec.test_spec('test_multipackage4.spec')


def test_multipackage5(pyi_builder_spec):
    pyi_builder_spec.test_spec('test_multipackage5.spec')
