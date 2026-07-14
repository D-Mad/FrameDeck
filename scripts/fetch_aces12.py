"""Download and verify the official ACES 1.2 OCIO config archive."""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import urllib.request
from pathlib import Path


URL = (
    "https://github.com/colour-science/OpenColorIO-Configs/releases/download/"
    "v1.2/OpenColorIO-Config-ACES-1.2.zip"
)
SHA256 = "299b55ab69d045e49199c750b1045ebe250bf2ec4ffa93a304bd40608b5d7ec4"
ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "resources" / "ocio" / "OpenColorIO-Config-ACES-1.2.zip"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if DESTINATION.is_file() and file_sha256(DESTINATION) == SHA256:
        print(f"ACES 1.2 archive verified: {DESTINATION}")
        return 0

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="aces12-", suffix=".zip", dir=str(DESTINATION.parent)
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        print(f"Downloading official ACES 1.2 config from {URL}")
        with urllib.request.urlopen(URL, timeout=60) as response, temporary.open(
            "wb"
        ) as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        actual = file_sha256(temporary)
        if actual != SHA256:
            raise RuntimeError(
                f"ACES 1.2 SHA-256 mismatch: expected {SHA256}, received {actual}"
            )
        os.replace(temporary, DESTINATION)
        print(f"ACES 1.2 archive ready: {DESTINATION}")
        return 0
    finally:
        if temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Unable to prepare ACES 1.2: {error}", file=sys.stderr)
        raise SystemExit(1)
