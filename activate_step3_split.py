from __future__ import annotations

from pathlib import Path
import shutil


WRAPPER_SOURCE = """from __future__ import annotations

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
"""


def main() -> None:
    folder = Path(__file__).resolve().parent
    metro_path = folder / "metro_stops.py"
    legacy_path = folder / "plumville_legacy_core.py"
    backup_path = folder / "metro_stops.step3.backup.py"

    if not metro_path.exists():
        raise SystemExit("metro_stops.py was not found in this folder.")

    current_text = metro_path.read_text(encoding="utf-8")

    if not legacy_path.exists():
        legacy_path.write_text(current_text, encoding="utf-8")
        print(f"Created {legacy_path.name}")

    if not backup_path.exists():
        shutil.copy2(metro_path, backup_path)
        print(f"Created {backup_path.name}")

    metro_path.write_text(WRAPPER_SOURCE, encoding="utf-8")
    print(f"Wrote fixed wrapper to {metro_path.name}")
    print("Done. Launch with either:")
    print("  python3 metro_stops.py")
    print("or")
    print("  python3 plumville_app.py")


if __name__ == "__main__":
    main()
