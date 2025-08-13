from PyQt6.QtWidgets import (
    QPushButton, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import (
    Qt, pyqtSignal
)
from PyQt6.QtGui import (
    QFont, QDragEnterEvent, QDropEvent
)
from pathlib import Path
from echomux.utils import process_paths

class MaterialButton(QPushButton):
    def __init__(self, text, primary=False):
        super().__init__(text)
        self.primary = primary
        self.setMinimumHeight(36)
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.update_style()

    def update_style(self):
        if self.primary:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #FAFAFA;
                    color: #212121;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #F5F5F5;
                }
                QPushButton:pressed {
                    background-color: #EEEEEE;
                }
            """)

class FileDropWidget(QListWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, allowed_extensions: list = None):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #BDBDBD;
                border-radius: 8px;
                background-color: #FAFAFA;
                padding: 20px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #E0E0E0;
            }
        """)

        # Set allowed file extensions
        if allowed_extensions is None:
            self.allowed_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.m4v']
        else:
            self.allowed_extensions = [ext.lower() for ext in allowed_extensions]

        # Add placeholder text
        self.placeholder = QListWidgetItem("Drop files here or click 'Add Files' button")
        self.placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        self.addItem(self.placeholder)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if not event.mimeData().hasUrls():
            return

        # Get a list of paths from the drop event
        dropped_paths = [url.toLocalFile() for url in event.mimeData().urls()]

        # Process paths to get a list of valid files
        files = process_paths(dropped_paths, self.allowed_extensions)

        if files:
            self.files_dropped.emit(files)


from PyQt6.QtWidgets import QTableWidget

class QTableWidgetWithDrop(QTableWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, allowed_extensions: list = None):
        super().__init__()
        self.setAcceptDrops(True)
        if allowed_extensions is None:
            self.allowed_extensions = []
        else:
            self.allowed_extensions = [ext.lower() for ext in allowed_extensions]

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            dropped_paths = [url.toLocalFile() for url in event.mimeData().urls()]
            files = process_paths(dropped_paths, self.allowed_extensions)
            if files:
                self.files_dropped.emit(files)
        else:
            super().dropEvent(event)
