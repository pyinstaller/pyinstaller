"""Common fixutres and test setup code for all tests in the suite"""

import pytest


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--skip-onefile"):
        return

    skip_onefile = pytest.mark.skip(reason="'onefile' tests disabled")
    for item in items:
        if "onefile" in item.keywords:
            item.add_marker(skip_onefile)


def pytest_addoption(parser):
    """Add our command line options to pytest"""
    parser.addoption("--use-default-hook",
                     action="store_true",
                     default=False,
                     help="Run tests with the '--use-default-hook option'")
    parser.addoption("--skip-onefile",
                     action="store_true",
                     default=False,
                     help="Skip 'onefile' tests and only run 'onedir'")
