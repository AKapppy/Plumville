from __future__ import annotations

_APPLIED = False


def apply() -> None:
    """Compatibility shim for former path rendering monkeypatches."""
    global _APPLIED
    _APPLIED = True
