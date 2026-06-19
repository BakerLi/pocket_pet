"""Windows-specific OS integration. All Win32/DWM/DPI code lives here so the
core simulation stays OS-agnostic and testable. See DESIGN.md section 2.

Note: this subpackage is named ``platform`` only within the ``pocket_pet``
namespace; it never shadows the stdlib ``platform`` module (Python 3 has no
implicit relative imports, so ``import platform`` always resolves to stdlib).
"""
