from pathlib import Path
from typing import List

from pathlib import Path
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QProgressBar,
    QFileDialog, QCheckBox, QGroupBox, QMessageBox, QGridLayout, QScrollArea,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QMenu
)

from echomux.ui_components import FileDropWidget, MaterialButton
from echomux.utils import process_paths, analyze_media_file, get_languages, open_file_location
from echomux.worker import ProcessingJob, FFmpegWorker, MediaFile


class AudioMergingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.video_files = []
        self.audio_files_data = []  # List of tuples (filepath, QComboBox)
        self.languages = get_languages()
        self.setup_ui()

    def setup_ui(self):
        top_layout = QVBoxLayout(self)
        top_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        top_layout.addWidget(scroll_area)
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        layout = QVBoxLayout(content_widget)

        # Video files section
        video_group = QGroupBox("Video Files")
        video_layout = QVBoxLayout(video_group)
        self.video_table = QTableWidget()
        self.video_table.setColumnCount(3)
        self.video_table.setHorizontalHeaderLabels(["Filename", "Duration", "Audio Tracks"])
        self.video_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.video_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.video_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.video_table.customContextMenuRequested.connect(self._show_video_context_menu)
        self.video_drop_widget = FileDropWidget(allowed_extensions=['.mp4', '.mkv', '.avi', '.mov', '.m4v'])
        self.video_drop_widget.files_dropped.connect(self.on_video_files_added)
        video_layout.addWidget(self.video_drop_widget)
        video_layout.addWidget(self.video_table)
        video_button_layout = QHBoxLayout()
        self.add_videos_btn = MaterialButton("Add Video Files")
        self.add_videos_btn.clicked.connect(self.add_video_files)
        self.add_video_folder_btn = MaterialButton("Add Folder")
        self.add_video_folder_btn.clicked.connect(self.add_video_folder)
        self.clear_videos_btn = MaterialButton("Clear Videos")
        self.clear_videos_btn.clicked.connect(self.clear_video_files)
        video_button_layout.addWidget(self.add_videos_btn)
        video_button_layout.addWidget(self.add_video_folder_btn)
        video_button_layout.addWidget(self.clear_videos_btn)
        video_button_layout.addStretch()
        video_layout.addLayout(video_button_layout)
        layout.addWidget(video_group)

        # Audio files section
        audio_group = QGroupBox("Audio Files to Merge")
        audio_layout = QVBoxLayout(audio_group)
        self.audio_table = QTableWidget()
        self.audio_table.setColumnCount(2)
        self.audio_table.setHorizontalHeaderLabels(["Audio File", "Language"])
        self.audio_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.audio_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.audio_table.customContextMenuRequested.connect(self._show_audio_context_menu)
        self.audio_drop_widget = FileDropWidget(allowed_extensions=['.aac', '.mp3', '.flac', '.ogg', '.wav', '.m4a'])
        self.audio_drop_widget.files_dropped.connect(self.on_audio_files_added)
        audio_layout.addWidget(self.audio_drop_widget)
        audio_layout.addWidget(self.audio_table)
        audio_button_layout = QHBoxLayout()
        self.add_audio_btn = MaterialButton("Add Audio Files")
        self.add_audio_btn.clicked.connect(self.add_audio_files)
        self.add_audio_folder_btn = MaterialButton("Add Folder")
        self.add_audio_folder_btn.clicked.connect(self.add_audio_folder)
        self.clear_audio_btn = MaterialButton("Clear Audio")
        self.clear_audio_btn.clicked.connect(self.clear_audio_files)
        audio_button_layout.addWidget(self.add_audio_btn)
        audio_button_layout.addWidget(self.add_audio_folder_btn)
        audio_button_layout.addStretch()
        audio_button_layout.addWidget(self.clear_audio_btn)
        audio_layout.addLayout(audio_button_layout)
        layout.addWidget(audio_group)

        # Settings section
        settings_group = QGroupBox("Merge Settings")
        settings_layout = QGridLayout(settings_group)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Select output directory...")
        self.browse_output_btn = MaterialButton("Browse")
        self.browse_output_btn.clicked.connect(self.browse_output)
        self.preserve_original = QCheckBox("Preserve original audio track(s)")
        self.preserve_original.setChecked(True)
        settings_layout.addWidget(QLabel("Output Directory:"), 0, 0)
        settings_layout.addWidget(self.output_path, 0, 1)
        settings_layout.addWidget(self.browse_output_btn, 0, 2)
        settings_layout.addWidget(self.preserve_original, 1, 0, 1, 3)
        layout.addWidget(settings_group)

        # Preview section
        preview_group = QGroupBox("File Matching Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(150)
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)
        self.refresh_preview_btn = MaterialButton("Refresh Preview")
        self.refresh_preview_btn.clicked.connect(self.update_preview)
        preview_layout.addWidget(self.refresh_preview_btn)
        layout.addWidget(preview_group)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        layout.addWidget(progress_group)

        # Control buttons
        control_layout = QHBoxLayout()
        self.merge_btn = MaterialButton("Merge Audio", primary=True)
        self.merge_btn.clicked.connect(self.start_merging)
        self.cancel_btn = MaterialButton("Cancel")
        self.cancel_btn.setEnabled(False)
        control_layout.addStretch()
        control_layout.addWidget(self.merge_btn)
        control_layout.addWidget(self.cancel_btn)
        layout.addLayout(control_layout)
        layout.addStretch()

        self.video_table.setVisible(False)
        self.audio_table.setVisible(False)

    def _show_video_context_menu(self, position):
        self._show_context_menu_for_table(self.video_table, position, self._remove_selected_videos, self._open_selected_video_location)

    def _show_audio_context_menu(self, position):
        self._show_context_menu_for_table(self.audio_table, position, self._remove_selected_audio, self._open_selected_audio_location)

    def _show_context_menu_for_table(self, table, position, remove_callback, open_callback):
        if not table.selectedItems():
            return

        menu = QMenu()
        remove_action = menu.addAction("Remove Selected")
        open_loc_action = menu.addAction("Open File Location")

        action = menu.exec(table.mapToGlobal(position))

        if action == remove_action:
            remove_callback()
        elif action == open_loc_action:
            open_callback()

    def _remove_selected_videos(self):
        selected_rows = sorted(list(set(item.row() for item in self.video_table.selectedItems())), reverse=True)
        for row in selected_rows:
            self.video_files.pop(row)
            self.video_table.removeRow(row)
        if self.video_table.rowCount() == 0:
            self.video_drop_widget.setVisible(True)
            self.video_table.setVisible(False)
        self.update_preview()

    def _remove_selected_audio(self):
        selected_rows = sorted(list(set(item.row() for item in self.audio_table.selectedItems())), reverse=True)
        for row in selected_rows:
            self.audio_files_data.pop(row)
            self.audio_table.removeRow(row)
        if self.audio_table.rowCount() == 0:
            self.audio_drop_widget.setVisible(True)
            self.audio_table.setVisible(False)
        self.update_preview()

    def _open_selected_video_location(self):
        self._open_location_for_table(self.video_table, self.video_files, is_media_file=True)

    def _open_selected_audio_location(self):
        self._open_location_for_table(self.audio_table, self.audio_files_data, is_media_file=False)

    def _open_location_for_table(self, table, data_list, is_media_file):
        selected_rows = list(set(item.row() for item in table.selectedItems()))
        if not selected_rows:
            return

        item = data_list[selected_rows[0]]
        path = item.path if is_media_file else item[0]
        open_file_location(str(path))

    def add_video_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Video Files", "", "Video Files (*.mp4 *.mkv *.avi *.mov *.m4v)")
        if files:
            self.on_video_files_added(files)

    def add_video_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder")
        if directory:
            self.on_video_files_added(process_paths([directory], ['.mp4', '.mkv', '.avi', '.mov', '.m4v']))

    def on_video_files_added(self, files: List[str]):
        for file_path in files:
            if any(mf.path == Path(file_path) for mf in self.video_files):
                continue
            media_file = MediaFile(Path(file_path), Path(file_path).name)
            info = analyze_media_file(file_path)
            duration_str, audio_info_str = "N/A", "Analysis Failed"
            if info:
                try:
                    duration = float(info.get('format', {}).get('duration', 0))
                    duration_str = f"{duration:.2f}s"
                    media_file.duration = duration
                    audio_streams = [s for s in info.get('streams', []) if s.get('codec_type') == 'audio']
                    audio_info_str = ", ".join([s.get('codec_name', 'ukn') for s in audio_streams]) if audio_streams else "No Audio"
                except (ValueError, TypeError):
                    pass
            self.video_files.append(media_file)
            row_pos = self.video_table.rowCount()
            self.video_table.insertRow(row_pos)
            self.video_table.setItem(row_pos, 0, QTableWidgetItem(media_file.filename))
            self.video_table.setItem(row_pos, 1, QTableWidgetItem(duration_str))
            self.video_table.setItem(row_pos, 2, QTableWidgetItem(audio_info_str))

        self.video_drop_widget.setVisible(self.video_table.rowCount() == 0)
        self.video_table.setVisible(self.video_table.rowCount() > 0)
        self.update_preview()

    def clear_video_files(self):
        self.video_table.setRowCount(0)
        self.video_files = []
        self.video_drop_widget.setVisible(True)
        self.video_table.setVisible(False)
        self.update_preview()

    def add_audio_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Audio Files", "", "Audio Files (*.aac *.mp3 *.flac *.ogg *.wav *.m4a)")
        if files:
            self.on_audio_files_added(files)

    def add_audio_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder")
        if directory:
            self.on_audio_files_added(process_paths([directory], ['.aac', '.mp3', '.flac', '.ogg', '.wav', '.m4a']))

    def on_audio_files_added(self, files: List[str]):
        for file_path in files:
            if any(af[0] == file_path for af in self.audio_files_data):
                continue
            row_pos = self.audio_table.rowCount()
            self.audio_table.insertRow(row_pos)
            self.audio_table.setItem(row_pos, 0, QTableWidgetItem(Path(file_path).name))
            lang_combo = QComboBox()
            for name, code in self.languages:
                lang_combo.addItem(f"{name} ({code})", code)
            self.audio_table.setCellWidget(row_pos, 1, lang_combo)
            self.audio_files_data.append((file_path, lang_combo))
        self.audio_drop_widget.setVisible(self.audio_table.rowCount() == 0)
        self.audio_table.setVisible(self.audio_table.rowCount() > 0)
        self.update_preview()

    def clear_audio_files(self):
        self.audio_table.setRowCount(0)
        self.audio_files_data = []
        self.audio_drop_widget.setVisible(True)
        self.audio_table.setVisible(False)
        self.update_preview()

    def refresh_language_dropdowns(self):
        self.languages = get_languages()
        for i in range(self.audio_table.rowCount()):
            combo = self.audio_table.cellWidget(i, 1)
            if combo:
                current_code = combo.currentData()
                combo.clear()
                for n, c in self.languages:
                    combo.addItem(f"{n} ({c})", c)
                combo.setCurrentIndex(combo.findData(current_code))

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_language_dropdowns()

    def browse_output(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_path.setText(directory)

    def update_preview(self):
        if not self.video_files or not self.audio_files_data:
            self.preview_text.clear()
            return
        preview_text = "File Matching Preview:\n\n"
        audio_paths = [af[0] for af in self.audio_files_data]
        for video_file in self.video_files:
            base_name = video_file.path.stem.lower()
            matching_audio = [Path(p).name for p in audio_paths if base_name in Path(p).stem.lower() or Path(p).stem.lower() in base_name]
            preview_text += f"📹 {video_file.filename}\n"
            if matching_audio:
                for audio in matching_audio:
                    preview_text += f"  └── 🎵 {audio}\n"
            else:
                preview_text += "  └── ⚠️ No matching audio found\n"
            preview_text += "\n"
        self.preview_text.setText(preview_text)

    def start_merging(self):
        if not self.video_files:
            QMessageBox.warning(self, "Warning", "Please add video files first.")
            return
        if not self.audio_files_data:
            QMessageBox.warning(self, "Warning", "Please add audio files to merge.")
            return
        if not self.output_path.text():
            QMessageBox.warning(self, "Warning", "Please select an output directory.")
            return

        audio_files = [af[0] for af in self.audio_files_data]
        languages = [af[1].currentData() for af in self.audio_files_data]

        job = ProcessingJob(
            input_files=self.video_files,
            output_directory=Path(self.output_path.text()),
            job_type='merge',
            settings={
                'audio_files': audio_files,
                'languages': languages,
                'preserve_original': self.preserve_original.isChecked()
            }
        )
        self.worker = FFmpegWorker(job)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.status_updated.connect(self.status_label.setText)
        self.worker.job_completed.connect(self.on_job_completed)
        self.cancel_btn.clicked.connect(self.worker.cancel)

        self.merge_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.worker.start()

    def on_job_completed(self, message, success):
        try:
            self.cancel_btn.clicked.disconnect(self.worker.cancel)
        except TypeError:
            pass

        self.merge_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText(message)
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
