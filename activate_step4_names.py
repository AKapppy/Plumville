from __future__ import annotations

from pathlib import Path
import shutil


WRAPPER_SOURCE = """from __future__ import annotations

import legacy_core as base
import ui_extensions as _extensions


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


def _pick_legacy_source(folder: Path) -> Path:
    candidates = [
        folder / "legacy_core.py",
        folder / "plumville_legacy_core.py",
        folder / "metro_stops.step3.backup.py",
        folder / "metro_stops.step4.backup.py",
        folder / "metro_stops.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit("Could not find a source file to create legacy_core.py.")


def main() -> None:
    folder = Path(__file__).resolve().parent
    metro_path = folder / "metro_stops.py"
    legacy_path = folder / "legacy_core.py"
    backup_path = folder / "metro_stops.step4.backup.py"

    source_path = _pick_legacy_source(folder)

    if not legacy_path.exists():
        source_text = source_path.read_text(encoding="utf-8")
        if "import legacy_core as base" in source_text or "import plumville_legacy_core as base" in source_text:
            source_path = folder / "plumville_legacy_core.py"
            if not source_path.exists():
                raise SystemExit(
                    "Found only a wrapper metro_stops.py, but plumville_legacy_core.py was not found."
                )
            source_text = source_path.read_text(encoding="utf-8")
        legacy_path.write_text(source_text, encoding="utf-8")
        print(f"Created {legacy_path.name} from {source_path.name}")
    else:
        print(f"{legacy_path.name} already exists")

    if metro_path.exists():
        current_text = metro_path.read_text(encoding="utf-8")
        if not backup_path.exists():
            shutil.copy2(metro_path, backup_path)
            print(f"Created {backup_path.name}")
        if current_text != WRAPPER_SOURCE:
            metro_path.write_text(WRAPPER_SOURCE, encoding="utf-8")
            print(f"Wrote short-name wrapper to {metro_path.name}")
        else:
            print(f"{metro_path.name} already has the short-name wrapper")
    else:
        metro_path.write_text(WRAPPER_SOURCE, encoding="utf-8")
        print(f"Created {metro_path.name}")

    print("")
    print("Done. Launch with either:")
    print("  python3 metro_stops.py")
    print("or")
    print("  python3 plumville_app.py")
    print("")
    print("Old plumville_* helper files can stay for now. They are no longer required by the new wrapper.")


if __name__ == "__main__":
    main()
