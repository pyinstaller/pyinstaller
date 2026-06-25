#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.compat import is_darwin
from PyInstaller.utils.hooks import copy_metadata, logger, get_hook_config
from PyInstaller import isolated


@isolated.decorate
def _get_configured_default_backend():
    """
    Return the configured default matplotlib backend name, if available as matplotlib.rcParams['backend'] (or overridden
    by MPLBACKEND environment variable. If the value of matplotlib.rcParams['backend'] corresponds to the auto-sentinel
    object, returns None
    """
    import matplotlib
    # matplotlib.rcParams overrides the __getitem__ implementation and attempts to determine and load the default
    # backend using pyplot.switch_backend(). Therefore, use dict.__getitem__().
    val = dict.__getitem__(matplotlib.rcParams, 'backend')
    if isinstance(val, str):
        return val
    return None


@isolated.decorate
def _resolve_backend_modules(backends):
    """
    Returns the names of all available matplotlib backends and their corresponding module names.
    """
    try:
        # In matplotlib >= 3.9, the lists of all available / built-in backends can be obtained from
        # `matplotlib.backends.backend_registry`.
        #
        # NOTE: `backend_registry.list_all()` loads entry-points, and therefore we need to call it even if we already
        # have a list of backend names to resolve; otherwise, `_backend_module_name()` fails to resolve modules for
        # backends that are loaded via entry-points.
        from matplotlib.backends import backend_registry
        all_backends = backend_registry.list_all()
        _backend_module_name = backend_registry._backend_module_name
    except ImportError:
        # In earlier versions, the list of all backends available in `matplotlib.rcsetup.all_backends`; this was
        # deprecated in matplotlib 3.9 and removed in 3.11.
        import matplotlib
        all_backends = matplotlib.rcsetup.all_backends
        from matplotlib.cbook import _backend_module_name

    if not backends:
        backends = all_backends

    return {backend: _backend_module_name(backend) for backend in backends}


@isolated.decorate
def _check_mpl_backend_importable(module_name):
    """
    Attempts to import the given module name (matplotlib backend module).

    Exceptions are propagated to caller.
    """
    import importlib
    importlib.import_module(module_name)


# Bytecode scanning
def _recursive_scan_code_objects_for_mpl_use(co):
    """
    Recursively scan the bytecode for occurrences of matplotlib.use() or mpl.use() calls with const arguments, and
    collect those arguments into list of used matplotlib backend names.
    """

    from PyInstaller.depend.bytecode import any_alias, recursive_function_calls

    mpl_use_names = {
        *any_alias("matplotlib.use"),
        *any_alias("mpl.use"),  # matplotlib is commonly aliased as mpl
    }

    backends = []
    for calls in recursive_function_calls(co).values():
        for name, args in calls:
            # matplotlib.use(backend) or matplotlib.use(backend, force)
            # We support only literal arguments. Similarly, kwargs are
            # not supported.
            if len(args) not in {1, 2} or not isinstance(args[0], str):
                continue
            if name in mpl_use_names:
                backends.append(args[0])

    return backends


def _autodetect_used_backends(hook_api):
    """
    Tries to auto-select matplotlib backend(s) to collect into frozen application (the 'auto' backend selection method),
    using the following semantics:
     - scan the code for use of matplotlib.use() to auto-discover used backend(s)
     - try to determine the configured default backend
     - try to select first importable backend from hard-coded list of platform-specific defaults
    Returns dictionary of backend names and their corresponding module names.
    """
    # Scan the code for matplotlib.use()
    modulegraph = hook_api.analysis.graph
    mpl_code_objs = modulegraph.get_code_using("matplotlib")
    used_backends = []
    for name, co in mpl_code_objs.items():
        co_backends = _recursive_scan_code_objects_for_mpl_use(co)
        if co_backends:
            logger.info(
                "Discovered Matplotlib backend(s) via `matplotlib.use()` call in module %r: %r", name, co_backends
            )
            used_backends += co_backends

    # Deduplicate and sort the list of used backends before displaying it.
    used_backends = sorted(set(used_backends))

    if used_backends:
        HOOK_CONFIG_DOCS = 'https://pyinstaller.org/en/stable/hooks-config.html#matplotlib-hooks'
        logger.info(
            "The following Matplotlib backends were discovered by scanning for `matplotlib.use()` calls: %r. If your "
            "backend of choice is not in this list, either add a `matplotlib.use()` call to your code, or configure "
            "the backend collection via hook options (see: %s).", used_backends, HOOK_CONFIG_DOCS
        )
        return _resolve_backend_modules(used_backends)

    # Determine the default matplotlib backend.
    #
    # Ideally, this would be done by calling ``matplotlib.get_backend()``. However, that function tries to switch to the
    # default backend (calling ``matplotlib.pyplot.switch_backend()``), which seems to occasionally fail on our linux CI
    # with an error and, on other occasions, returns the headless Agg backend instead of the GUI one (even with display
    # server running). Furthermore, using ``matplotlib.get_backend()`` returns headless 'Agg' when display server is
    # unavailable, which is not ideal for automated builds.
    #
    # Therefore, we try to emulate ``matplotlib.get_backend()`` ourselves. First, we try to obtain the configured
    # default backend from settings (rcparams and/or MPLBACKEND environment variable). If that is unavailable, we try to
    # find the first importable GUI-based backend, using the same list as matplotlib.pyplot.switch_backend() uses for
    # automatic backend selection. The difference is that we only test whether the backend module is importable, without
    # trying to switch to it.
    default_backend = _get_configured_default_backend()  # isolated sub-process
    if default_backend:
        logger.info("Found configured default matplotlib backend: %s", default_backend)
        return _resolve_backend_modules([default_backend])

    # `QtAgg` supersedes `Qt5Agg`; however, we keep `Qt5Agg` in the candidate list to support older versions of
    # matplotlib that do not have `QtAgg`.
    candidates = ["QtAgg", "Qt5Agg", "Gtk4Agg", "Gtk3Agg", "TkAgg", "WxAgg"]
    if is_darwin:
        candidates = ["MacOSX"] + candidates
    logger.info("Trying determine the default backend as first importable candidate from the list: %r", candidates)

    candidates = _resolve_backend_modules(candidates)  # [name] -> {name: module_name}
    for name, module_name in candidates.items():
        try:
            _check_mpl_backend_importable(module_name)  # NOTE: uses an isolated sub-process.
        except Exception:
            continue
        return {name: module_name}

    # Fall back to headless Agg backend
    logger.info("None of the backend candidates could be imported; falling back to headless Agg!")
    return _resolve_backend_modules(['Agg'])


def _collect_all_importable_backends():
    """
    Return a dictionary of all importable matplotlib backends and their corresponding module names.
    Implements the 'all' backend selection method.
    """
    # Get names and corresponding module names for all available backends.
    available_backends = _resolve_backend_modules(None)  # NOTE: retrieved in an isolated sub-process.
    logger.info("All available matplotlib backends: %r", list(available_backends.keys()))

    # Try to import the module(s).
    importable_backends = {}

    # List of backends to exclude; Qt4 is not supported by PyInstaller anymore.
    exclude_backends = {'Qt4Agg', 'Qt4Cairo'}

    # Ignore "CocoaAgg" on OSes other than macOS; attempting to import it on other OSes halts the current
    # (sub)process without printing output or raising exceptions, preventing reliable detection. Apply the
    # same logic for the (newer) "MacOSX" backend.
    if not is_darwin:
        exclude_backends |= {'CocoaAgg', 'MacOSX'}

    # Starting with matplotlib 3.9, the backend names are lower-case...
    exclude_backends = {backend.lower() for backend in exclude_backends}

    # For safety, attempt to import each backend in an isolated sub-process.
    for backend_name, module_name in available_backends.items():
        if backend_name.lower() in exclude_backends:
            logger.info('  Matplotlib backend %r: excluded', backend_name)
            continue

        try:
            _check_mpl_backend_importable(module_name)  # NOTE: uses an isolated sub-process.
        except Exception:
            # Backend is not importable, for whatever reason.
            logger.info('  Matplotlib backend %r: ignored due to import error', backend_name)
            continue

        logger.info('  Matplotlib backend %r: added', backend_name)
        importable_backends[backend_name] = module_name

    return importable_backends


def _find_dists_for_backends(backends):
    """
    Return list of dist names for backends that are not built into matplotlib.
    """
    from PyInstaller.compat import importlib_metadata

    backend_modules = set(backends.values())  # set of backend module names

    backend_dists = set()
    for entry_point in importlib_metadata.entry_points(group="matplotlib.backend"):
        if entry_point.module in backend_modules:
            backend_dists.add(entry_point.dist.name)

    return sorted(backend_dists)


def hook(hook_api):
    # Backend collection setting
    backends_method = get_hook_config(hook_api, 'matplotlib', 'backends')
    if backends_method is None:
        backends_method = 'auto'  # default method

    # Select backend(s)
    if backends_method == 'auto':
        logger.info("Matplotlib backend selection method: automatic discovery of used backends")
        backends = _autodetect_used_backends(hook_api)
    elif backends_method == 'all':
        logger.info("Matplotlib backend selection method: collection of all importable backends")
        backends = _collect_all_importable_backends()
    else:
        logger.info("Matplotlib backend selection method: user-provided name(s)")
        if isinstance(backends_method, str):
            backend_names = [backends_method]
        else:
            assert isinstance(backends_method, list), "User-provided backend name(s) must be either a string or a list!"
            backend_names = backends_method

        # Resolve backend names into module names
        backends = _resolve_backend_modules(backend_names)

    # Resolve dists for backends that are not built into matplotlib
    backend_dists = _find_dists_for_backends(backends)

    # Display the final list of selected backends
    logger.info("Selected matplotlib backends: %r", sorted(backends.keys()))
    logger.info("Extra dists for selected matplotlib backends: %r", backend_dists)

    # Set module names as hiddenimports
    hook_api.add_imports(*list(backends.values()))

    # Copy metadata for extra dists
    for dist_name in backend_dists:
        hook_api.add_datas(copy_metadata(dist_name))
