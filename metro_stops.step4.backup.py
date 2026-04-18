from __future__ import annotations

import plumville_legacy_core as base
import plumville_ui_extensions as _extensions


_EXTENSIONS_APPLIED = False


def _apply_extensions_once() -> None:
    global _EXTENSIONS_APPLIED
    if _EXTENSIONS_APPLIED:
        return
    _extensions.apply()
    _EXTENSIONS_APPLIED = True


def plot_stops(*args, **kwargs):
    _apply_extensions_once()
    return base.plot_stops(*args, **kwargs)


def main() -> None:
    _apply_extensions_once()
    base.main()


if __name__ == "__main__":
    main()
