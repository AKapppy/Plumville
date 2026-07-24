from __future__ import annotations

_APPLIED = False


def apply() -> None:
    """Compatibility shim for the former worldgen planner monkeypatch."""
    global _APPLIED
    _APPLIED = True
