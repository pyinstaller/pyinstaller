import os
import sys


def setup_vendored_packages(mode):
    # Resolve _vendored directory within this package.
    vendored_path = os.path.join(os.path.dirname(__file__), '_vendored')

    # Prepend or append the vendored path to sys.path.
    if mode == 'prepend':
        sys.path.insert(0, vendored_path)
    elif mode == 'append':
        sys.path.append(vendored_path)
    else:
        raise ValueError(f"Invalid mode: {mode}")
