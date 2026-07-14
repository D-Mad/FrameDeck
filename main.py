import os
import sys
import traceback
from pathlib import Path

from PySide6 import QtWidgets

from widgets import MainWindow


def _configure_portable_runtime():
    """Set portable defaults without overriding studio/user configuration."""
    documents = Path.home() / "Documents"
    os.environ.setdefault("FRAMEDECK_PROFILE_ROOT", str(documents))


def _install_crash_log():
    """Write startup/runtime errors to a file for windowed builds."""
    log_dir = Path(os.environ["FRAMEDECK_PROFILE_ROOT"]) / "framedeck" / "logs"

    def handle_exception(exc_type, exc_value, exc_traceback):
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "framedeck-crash.log"
        log_file.write_text(
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
            encoding="utf-8",
        )
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception


def main():
    """
    Application entry point.
    """

    _configure_portable_runtime()
    _install_crash_log()

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("FrameDeck")
    app.setOrganizationName("FrameDeck")

    window = MainWindow()
    window.show()

    # Files passed from Explorer (Open with / drag onto EXE) become one local
    # playlist, in the same order supplied by Windows.
    media_paths = [path for path in sys.argv[1:] if Path(path).is_file()]
    if media_paths:
        window.import_media_files(media_paths)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
