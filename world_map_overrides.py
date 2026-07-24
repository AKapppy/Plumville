from __future__ import annotations

_APPLIED = False


def apply() -> None:
    """Compatibility shim for former world-map viewer monkeypatches."""
    global _APPLIED
    _APPLIED = True
