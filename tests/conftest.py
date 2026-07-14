"""Shared pytest configuration for the FrameDeck test suite.

The whole suite runs headless: we force Qt's ``offscreen`` platform plugin so
widgets can be constructed, rendered to a ``QImage`` and pixel-probed without a
display. Environment variables are set at import time -- before any PySide6 or
OpenCV import -- because Qt reads ``QT_QPA_PLATFORM`` once at ``QApplication``
construction and OpenCV reads its FFmpeg options once per ``VideoCapture``.
"""

import os
import sys
import tempfile
from pathlib import Path

# Headless Qt + single-threaded FFmpeg decode (same guard the app relies on).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "threads;1")

# Keep the app's profile/cache writes inside a throwaway dir instead of the real
# user Documents folder (main.py points FRAMEDECK_PROFILE_ROOT at Documents).
os.environ.setdefault(
    "FRAMEDECK_PROFILE_ROOT",
    tempfile.mkdtemp(prefix="framedeck-test-"),
)

# Make the repo root importable so `import constants`, `import widgets...` work
# regardless of where pytest is invoked from.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest


@pytest.fixture(scope="session")
def qapp():
    """A single ``QApplication`` shared by every test that touches Qt widgets."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
    # Do not call app.quit(): a session-wide instance is reused across tests.
