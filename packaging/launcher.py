"""Frozen-app entry point for PyInstaller (see ../build.ps1).

``pocket_pet/main.py`` uses package-relative imports, so it can't be run as a
bare script (PyInstaller would execute it as ``__main__`` with no package
context). Import the installed package's ``main()`` instead.
"""

from __future__ import annotations

from pocket_pet.main import main

if __name__ == "__main__":
    raise SystemExit(main())
