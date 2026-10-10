"""Check the installed analysis environment without connecting hardware."""

import importlib
import platform
import sys


def main():
    print(f"Python {platform.python_version()} on {platform.system()}")
    if not (3, 11) <= sys.version_info[:2] < (3, 13):
        raise SystemExit("Use Python 3.11 or 3.12 for this project.")
    for name in ("emoemg", "numpy", "scipy", "pandas", "sklearn", "matplotlib"):
        module = importlib.import_module(name)
        print(f"{name}: {getattr(module, '__version__', 'import OK')}")
    print("Analysis environment ready. Hardware connection has not been tested.")


if __name__ == "__main__":
    main()
