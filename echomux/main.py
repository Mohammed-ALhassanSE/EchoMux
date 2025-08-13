import subprocess
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from echomux.main_window import MainWindow
from echomux.utils import get_ffmpeg_path


def check_dependencies():
    """Check if required dependencies are available"""
    missing = []
    ffmpeg_path = get_ffmpeg_path()

    # Check FFmpeg
    try:
        subprocess.run([ffmpeg_path, '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append(f"FFmpeg (path: {ffmpeg_path})")

    # Check psutil (optional for system info)
    try:
        import psutil
    except ImportError:
        missing.append("psutil (optional)")

    return missing


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("EchoMux")
    app.setApplicationDisplayName("EchoMux - Video Remuxer & Media Manager")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("EchoMux")
    app.setOrganizationDomain("echomux.app")

    # Set application icon
    icon_path = Path(__file__).parent.parent / "icon" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Check for dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Missing Dependencies")
        msg.setText(f"Some dependencies are missing: {', '.join(missing_deps)}")

        if "FFmpeg" in missing_deps:
            msg.setInformativeText("FFmpeg is required for media processing. "
                                 "Please install FFmpeg and make sure it's accessible from the command line.\n\n"
                                 "Other missing dependencies are optional but recommended.")
        else:
            msg.setInformativeText("These dependencies are optional but provide additional functionality.")

        msg.exec()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
