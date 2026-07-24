from __future__ import annotations

_APPLIED = False


def apply() -> None:
    """Compatibility shim for former worldgen speedup monkeypatches."""
    global _APPLIED
    _APPLIED = True
