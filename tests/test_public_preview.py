from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicPreviewTests(unittest.TestCase):
    def test_public_preview_check_validates_without_serving(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/preview_public_docs.py", "--check"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("OK: public docs preview is validated.", result.stdout)


if __name__ == "__main__":
    unittest.main()
