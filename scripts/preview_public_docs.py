from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
sys.path.insert(0, str(REPO_ROOT))

from plumville.core import public_export


class NoCacheDocsHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def validate_public_preview() -> None:
    public_export.validate_public_docs(DOCS_ROOT)
    if not (DOCS_ROOT / "index.html").exists():
        raise FileNotFoundError(f"Public preview is missing index.html: {DOCS_ROOT}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and preview the sanitized public docs export.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--check", action="store_true", help="validate only; do not start a server")
    args = parser.parse_args()

    validate_public_preview()
    if args.check:
        print("OK: public docs preview is validated.")
        return

    handler = partial(NoCacheDocsHandler, directory=str(DOCS_ROOT))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving sanitized public docs at http://{args.host}:{args.port}/")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped public docs preview.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
