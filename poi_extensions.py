from __future__ import annotations

_APPLIED = False


def apply() -> None:
    """Compatibility shim for former PoI dialog monkeypatches."""
    global _APPLIED
    _APPLIED = True
