from pathlib import Path
from typing import List

from pathlib import Path
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QProgressBar,
    QFileDialog, QComboBox,
    QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout, QScrollArea, QMenu
)

from echomux.ui_components import FileDropWidget, MaterialButton
from echomux.utils import process_paths, analyze_media_file, open_file_location
from echomux.worker import ProcessingJob, FFmpegWorker, MediaFile


class AudioExtractionTab(QWidget):
    def __init__(self):
        super().__init__()
        self.input_files = []
        self.setup_ui()

    def setup_ui(self):
        # Main layout for the tab
        top_layout = QVBoxLayout(self)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        top_layout.addWidget(scroll_area)

        # Content widget
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        # Layout for the content widget
        layout = QVBoxLayout(content_widget)

        # Input section
        input_group = QGroupBox("Input Files")
        input_layout = QVBoxLayout(input_group)

        self.file_table = QTableWidget()
        self.file_table.setColumnCount(3)
        self.file_table.setHorizontalHeaderLabels(["Filename", "Duration", "Audio Tracks"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self._show_context_menu)

        self.drop_widget = FileDropWidget(allowed_extensions=['.mp4', '.mkv', '.avi', '.mov', '.m4v'])
        self.drop_widget.files_dropped.connect(self.on_files_added)

        input_layout.addWidget(self.drop_widget)
        input_layout.addWidget(self.file_table)

        button_layout = QHBoxLayout()
        self.add_files_btn = MaterialButton("Add Files")
        self.add_files_btn.clicked.connect(self.add_files)
        self.add_folder_btn = MaterialButton("Add Folder")
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.clear_files_btn = MaterialButton("Clear")
        self.clear_files_btn.clicked.connect(self.clear_files)

        button_layout.addWidget(self.add_files_btn)
        button_layout.addWidget(self.add_folder_btn)
        button_layout.addWidget(self.clear_files_btn)
        button_layout.addStretch()

        input_layout.addLayout(button_layout)
        layout.addWidget(input_group)

        # Output section
        output_group = QGroupBox("Output Settings")
        output_layout = QGridLayout(output_group)

        output_layout.addWidget(QLabel("Output Directory:"), 0, 0)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Select output directory...")
        output_layout.addWidget(self.output_path, 0, 1)

        self.browse_output_btn = MaterialButton("Browse")
        self.browse_output_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.browse_output_btn, 0, 2)

        output_layout.addWidget(QLabel("Audio Format:"), 1, 0)
        self.audio_format = QComboBox()
        self.audio_format.addItems(["AAC", "MP3", "FLAC", "OGG"])
        output_layout.addWidget(self.audio_format, 1, 1)

        layout.addWidget(output_group)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Ready to extract audio tracks")

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)

        layout.addWidget(progress_group)

        # Control buttons
        control_layout = QHBoxLayout()
        self.extract_btn = MaterialButton("Extract Audio", primary=True)
        self.extract_btn.clicked.connect(self.start_extraction)
        self.cancel_btn = MaterialButton("Cancel")
        self.cancel_btn.setEnabled(False)

        control_layout.addStretch()
        control_layout.addWidget(self.extract_btn)
        control_layout.addWidget(self.cancel_btn)

        layout.addLayout(control_layout)
        layout.addStretch()

    def _show_context_menu(self, position):
        if not self.file_table.selectedItems():
            return

        menu = QMenu()
        remove_action = menu.addAction("Remove Selected")
        open_loc_action = menu.addAction("Open File Location")

        action = menu.exec(self.file_table.mapToGlobal(position))

        if action == remove_action:
            self._remove_selected_files()
        elif action == open_loc_action:
            self._open_selected_file_location()

    def _remove_selected_files(self):
        selected_rows = sorted(list(set(item.row() for item in self.file_table.selectedItems())), reverse=True)
        for row in selected_rows:
            self.input_files.pop(row)
            self.file_table.removeRow(row)

        if self.file_table.rowCount() == 0:
            self.drop_widget.setVisible(True)
            self.file_table.setVisible(False)

    def _open_selected_file_location(self):
        selected_rows = list(set(item.row() for item in self.file_table.selectedItems()))
        if not selected_rows:
            return
        # Open location for the first selected item
        file_to_open = self.input_files[selected_rows[0]]
        open_file_location(str(file_to_open.path))

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files",
            "", "Video Files (*.mp4 *.mkv *.avi *.mov *.m4v)"
        )
        if files:
            self.on_files_added(files)

    def add_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder")
        if directory:
            allowed_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.m4v']
            files = process_paths([directory], allowed_extensions)
            self.on_files_added(files)

    def on_files_added(self, files: List[str]):
        for file_path in files:
            if any(mf.path == Path(file_path) for mf in self.input_files):
                continue

            media_file = MediaFile(Path(file_path), Path(file_path).name)

            info = analyze_media_file(file_path)
            duration_str = "N/A"
            audio_info_str = "Analysis Failed"

            if info:
                try:
                    duration = float(info.get('format', {}).get('duration', 0))
                    duration_str = f"{duration:.2f}s"
                    media_file.duration = duration

                    audio_streams = [s for s in info.get('streams', []) if s.get('codec_type') == 'audio']
                    if not audio_streams:
                        audio_info_str = "⚠️ No Audio"
                    else:
                        audio_info_str = ", ".join([s.get('codec_name', 'unknown') for s in audio_streams])
                except (ValueError, TypeError):
                    # If parsing fails, keep the "Analysis Failed" message
                    pass

            self.input_files.append(media_file)

            row_position = self.file_table.rowCount()
            self.file_table.insertRow(row_position)
            self.file_table.setItem(row_position, 0, QTableWidgetItem(media_file.filename))
            self.file_table.setItem(row_position, 1, QTableWidgetItem(duration_str))
            self.file_table.setItem(row_position, 2, QTableWidgetItem(audio_info_str))

        self.drop_widget.setVisible(self.file_table.rowCount() == 0)
        self.file_table.setVisible(self.file_table.rowCount() > 0)


    def clear_files(self):
        self.file_table.setRowCount(0)
        self.input_files = []
        self.drop_widget.setVisible(True)
        self.file_table.setVisible(False)

    def browse_output(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_path.setText(directory)

    def start_extraction(self):
        if not self.input_files:
            QMessageBox.warning(self, "Warning", "Please add video files first.")
            return

        if not self.output_path.text():
            QMessageBox.warning(self, "Warning", "Please select an output directory.")
            return

        job = ProcessingJob(
            input_files=self.input_files,
            output_directory=Path(self.output_path.text()),
            job_type='extract',
            settings={'format': self.audio_format.currentText().lower()}
        )

        self.worker = FFmpegWorker(job)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.status_updated.connect(self.status_label.setText)
        self.worker.job_completed.connect(self.on_job_completed)
        self.cancel_btn.clicked.connect(self.worker.cancel)

        self.extract_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.worker.start()

    def on_job_completed(self, message, success):
        # Disconnect the cancel signal to prevent issues on subsequent runs
        try:
            self.cancel_btn.clicked.disconnect(self.worker.cancel)
        except TypeError: # Signal may already be disconnected
            pass

        self.extract_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText(message)

        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
