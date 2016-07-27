

def test_pytest_runner(pyi_builder):
    """
    Check if pytest runner builds correctly.
    """
    pyi_builder.test_source(
        """
        import pytest
        import sys
        sys.exit(pytest.main(['--help']))
        """)
