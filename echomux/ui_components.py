from PyQt6.QtWidgets import (
    QPushButton, QListWidget, QListWidgetItem, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QTableWidget, QHeaderView, QFileDialog, QTableWidgetItem
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


class FileListWidget(QWidget):
    files_added = pyqtSignal(list)
    files_cleared = pyqtSignal()

    def __init__(self, title: str, allowed_extensions: list, table_headers: list):
        super().__init__()
        self.allowed_extensions = [ext.lower() for ext in allowed_extensions]
        self.table_headers = table_headers

        # --- UI Components ---
        self.group_box = QGroupBox(title)
        self.drop_widget = FileDropWidget(self.allowed_extensions)
        self.table = QTableWidget()
        self.add_files_btn = MaterialButton("Add Files")
        self.add_folder_btn = MaterialButton("Add Folder")
        self.clear_btn = MaterialButton("Clear")

        self._setup_layout()
        self._connect_signals()

    def _setup_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.group_box)

        group_layout = QVBoxLayout(self.group_box)
        group_layout.addWidget(self.drop_widget)
        group_layout.addWidget(self.table)

        self.table.setColumnCount(len(self.table_headers))
        self.table.setHorizontalHeaderLabels(self.table_headers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setVisible(False)
        # Allow context menu from parent
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_files_btn)
        button_layout.addWidget(self.add_folder_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.clear_btn)
        group_layout.addLayout(button_layout)

    def _connect_signals(self):
        self.drop_widget.files_dropped.connect(self._on_files_dropped)
        self.add_files_btn.clicked.connect(self._add_files_handler)
        self.add_folder_btn.clicked.connect(self._add_folder_handler)
        self.clear_btn.clicked.connect(self.clear_files)

    def _on_files_dropped(self, files: list):
        self.files_added.emit(files)

    def _add_files_handler(self):
        file_filter = f"Files ({' '.join(['*' + ext for ext in self.allowed_extensions])})"
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", file_filter)
        if files:
            self.files_added.emit(files)

    def _add_folder_handler(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder")
        if directory:
            files = process_paths([directory], self.allowed_extensions)
            if files:
                self.files_added.emit(files)

    def add_row(self, row_data: list):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        for i, item_data in enumerate(row_data):
            if isinstance(item_data, QWidget):
                 self.table.setCellWidget(row_position, i, item_data)
            else:
                 self.table.setItem(row_position, i, QTableWidgetItem(str(item_data)))
        self.update_visibility()
        return row_position

    def clear_files(self):
        self.table.setRowCount(0)
        self.update_visibility()
        self.files_cleared.emit()

    def update_visibility(self):
        is_empty = self.table.rowCount() == 0
        self.drop_widget.setVisible(is_empty)
        self.table.setVisible(not is_empty)
