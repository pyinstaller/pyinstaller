from setuptools import setup

setup(
    name='pyi_example_package',
    setup_requires="setuptools >= 40.0.0",
    packages=['pyi_example_package'],
    author='PyInstaller development team',
    entry_points={'pyinstaller40': ['hooks = pyi_example_package.__init__:get_hook_dirs']}
)
