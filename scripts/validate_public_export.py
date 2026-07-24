from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
sys.path.insert(0, str(REPO_ROOT))

from plumville.core import public_export


def main() -> None:
    public_export.validate_public_docs(DOCS_ROOT)
    print("OK: public docs export contains no known private/local fields or path fragments.")


if __name__ == "__main__":
    main()
