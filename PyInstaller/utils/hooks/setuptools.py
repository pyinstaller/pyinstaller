# ----------------------------------------------------------------------------
# Copyright (c) 2024, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
from PyInstaller import log as logging
from PyInstaller import isolated

logger = logging.getLogger(__name__)


# Import setuptools and analyze its properties in an isolated subprocess. This function is called by `SetuptoolsInfo`
# to initialize its properties.
@isolated.decorate
def _retrieve_setuptools_info():
    import importlib

    try:
        setuptools = importlib.import_module("setuptools")  # noqa: F841
    except ModuleNotFoundError:
        return None

    # Delay these imports until after we have confirmed that setuptools is importable.
    import pathlib

    import packaging.version

    from PyInstaller.compat import importlib_metadata
    from PyInstaller.utils.hooks import (
        collect_data_files,
        collect_submodules,
    )

    # Try to retrieve the version. At this point, failure is consider an error.
    version_string = importlib_metadata.version("setuptools")
    version = packaging.version.Version(version_string).release  # Use the version tuple

    # setuptools >= 60.0 its vendored copy of distutils (mainly due to its removal from stdlib in python >= 3.12).
    distutils_vendored = False
    distutils_modules = []
    if version >= (60, 0):
        distutils_vendored = True
        distutils_modules += ["_distutils_hack"]
        distutils_modules += collect_submodules(
            "setuptools._distutils",
            # setuptools 71.0.1 ~ 71.0.4 include `setuptools._distutils.tests`; avoid explicitly collecting it
            # (t was not included in earlier setuptools releases).
            filter=lambda name: name != 'setuptools._distutils.tests',
        )

    # Check if `setuptools._vendor` exists. Some linux distributions opt to de-vendor `setuptools` and remove the
    # `setuptools._vendor` directory altogether. If this is the case, most of additional processing below should be
    # skipped to avoid errors and warnings about non-existent `setuptools._vendor` module.
    try:
        setuptools_vendor = importlib.import_module("setuptools._vendor")
    except ModuleNotFoundError:
        setuptools_vendor = None

    # Check for exposed packages/modules that are vendored by setuptools. If stand-alone version is not provided in the
    # environment, setuptools-vendored version is exposed (due to location of `setuptools._vendor` being appended to
    # `sys.path`. Applicable to v71.0.0 and later.
    vendored_status = dict()
    if version >= (71, 0) and setuptools_vendor is not None:
        VENDORED_CANDIDATES = (
            "autocommand",
            "backports.tarfile",
            "importlib_metadata",
            "importlib_resources",
            "inflect",
            "jaraco.context",
            "jaraco.functools",
            "jaraco.text",
            "more_itertools",
            "ordered_set",
            "packaging",
            "platformdirs",
            "tomli",
            "typeguard",
            "typing_extensions",
            "wheel",
            "zipp",
        )

        # Resolve path(s) of `setuptools_vendor` package.
        setuptools_vendor_paths = [pathlib.Path(path).resolve() for path in setuptools_vendor.__path__]

        # Process each candidate
        for candidate_name in VENDORED_CANDIDATES:
            try:
                candidate = importlib.import_module(candidate_name)
            except ImportError:
                continue

            # Check the __file__ attribute (modules and regular packages). Will not work with namespace packages, but
            # at the moment, there are none.
            candidate_file_attr = getattr(candidate, '__file__', None)
            if candidate_file_attr is not None:
                candidate_path = pathlib.Path(candidate_file_attr).parent.resolve()
                is_vendored = any([
                    setuptools_vendor_path in candidate_path.parents or candidate_path == setuptools_vendor_path
                    for setuptools_vendor_path in setuptools_vendor_paths
                ])
                vendored_status[candidate_name] = is_vendored

    # Collect submodules from `setuptools._vendor`, regardless of whether the vendored package is exposed or
    # not (because setuptools might need/use it either way).
    vendored_modules = []
    if setuptools_vendor is not None:
        EXCLUDED_VENDORED_MODULES = (
            # Prevent recursing into setuptools._vendor.pyparsing.diagram, which typically fails to be imported due
            # to missing dependencies (railroad, pyparsing (?), jinja2) and generates a warning... As the module is
            # usually unimportable, it is likely not to be used by setuptools. NOTE: pyparsing was removed from
            # vendored packages in setuptools v67.0.0; keep this exclude around for earlier versions.
            'setuptools._vendor.pyparsing.diagram',
            # Setuptools >= 71 started shipping vendored dependencies that include tests; avoid collecting those via
            # hidden imports. (Note that this also prevents creation of aliases for these module, but that should
            # not be an issue, as they should not be referenced from anywhere).
            'setuptools._vendor.importlib_resources.tests',
            # These appear to be utility scripts bundled with the jaraco.text package - exclude them.
            'setuptools._vendor.jaraco.text.show-newlines',
            'setuptools._vendor.jaraco.text.strip-prefix',
            'setuptools._vendor.jaraco.text.to-dvorak',
            'setuptools._vendor.jaraco.text.to-qwerty',
        )
        vendored_modules += collect_submodules(
            'setuptools._vendor',
            filter=lambda name: name not in EXCLUDED_VENDORED_MODULES,
        )

        # `collect_submodules` (and its underlying `pkgutil.iter_modules` do not discover namespace sub-packages, in
        # this case `setuptools._vendor.jaraco`. So force a manual scan of modules/packages inside it.
        vendored_modules += collect_submodules(
            'setuptools._vendor.jaraco',
            filter=lambda name: name not in EXCLUDED_VENDORED_MODULES,
        )

    # *** Data files for vendored packages ***
    vendored_data = []

    if version >= (71, 0) and setuptools_vendor is not None:
        # Since the vendored dependencies from `setuptools/_vendor` are now visible to the outside world, make
        # sure we collect their metadata. (We cannot use copy_metadata here, because we need to collect data
        # files to their original locations).
        vendored_data += collect_data_files('setuptools._vendor', includes=['**/*.dist-info'])
        # Similarly, ensure that `Lorem ipsum.txt` from vendored jaraco.text is collected
        vendored_data += collect_data_files('setuptools._vendor.jaraco.text', includes=['**/Lorem ipsum.txt'])

    # Return dictionary with collected information
    return {
        "available": True,
        "version": version,
        "distutils_vendored": distutils_vendored,
        "distutils_modules": distutils_modules,
        "vendored_status": vendored_status,
        "vendored_modules": vendored_modules,
        "vendored_data": vendored_data,
    }


class SetuptoolsInfo:
    def __init__(self):
        pass

    def __repr__(self):
        return "SetuptoolsInfo"

    # Delay initialization of setuptools information until until the corresponding attributes are first requested.
    def __getattr__(self, name):
        if 'available' in self.__dict__:
            # Initialization was already done, but requested attribute is not available.
            raise AttributeError(name)

        # Load setuptools info...
        self._load_setuptools_info()
        # ... and return the requested attribute
        return getattr(self, name)

    def _load_setuptools_info(self):
        logger.info("%s: initializing cached setuptools info...", self)

        # Initialize variables so that they might be accessed even if setuptools is unavailable or if initialization
        # fails for some reason.
        self.available = False
        self.version = None
        self.distutils_vendored = False
        self.distutils_modules = []
        self.vendored_status = dict()
        self.vendored_modules = []
        self.vendored_data = []

        try:
            setuptools_info = _retrieve_setuptools_info()
        except Exception as e:
            logger.warning("%s: failed to obtain setuptools info: %s", self, e)
            return

        # If package could not be imported, `_retrieve_setuptools_info` returns None. In such cases, emit a debug
        # message instead of a warning, because this initialization might be triggered by a helper function that is
        # trying to determine availability of `setuptools` by inspecting the `available` attribute.
        if setuptools_info is None:
            logger.debug("%s: failed to obtain setuptools info: setuptools could not be imported.", self)
            return

        # Copy properties
        for key, value in setuptools_info.items():
            setattr(self, key, value)

    def is_vendored(self, module_name):
        return self.vendored_status.get(module_name, False)

    @staticmethod
    def _create_vendored_aliases(vendored_name, module_name, modules_list):
        # Create aliases for all submodules
        prefix_len = len(vendored_name)  # Length of target-name prefix to remove
        return ((module_name + vendored_module[prefix_len:], vendored_module) for vendored_module in modules_list
                if vendored_module.startswith(vendored_name))

    def get_vendored_aliases(self, module_name):
        vendored_name = f"setuptools._vendor.{module_name}"
        return self._create_vendored_aliases(vendored_name, module_name, self.vendored_modules)

    def get_distutils_aliases(self):
        vendored_name = "setuptools._distutils"
        return self._create_vendored_aliases(vendored_name, "distutils", self.distutils_modules)


setuptools_info = SetuptoolsInfo()


def pre_safe_import_module(api):
    """
    A common implementation of pre_safe_import_module hook function.

    This function can be either called from the `pre_safe_import_module` function in a pre-safe-import-module hook, or
    just imported into the hook.
    """
    module_name = api.module_name

    # Check if the package/module is a vendored copy. This also returns False is setuptools is unavailable, because
    # vendored module status dictionary will be empty.
    if not setuptools_info.is_vendored(module_name):
        return

    vendored_name = f"setuptools._vendor.{module_name}"
    logger.info(
        "Setuptools: %r appears to be a setuptools-vendored copy - creating alias to %r!", module_name, vendored_name
    )

    # Create aliases for all (sub)modules
    for aliased_name, real_vendored_name in setuptools_info.get_vendored_aliases(module_name):
        api.add_alias_module(real_vendored_name, aliased_name)
