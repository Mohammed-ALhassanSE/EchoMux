from pathlib import Path
from typing import List

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QProgressBar,
    QFileDialog, QCheckBox, QGroupBox, QMessageBox, QGridLayout, QScrollArea,
    QTextEdit, QComboBox, QMenu
)

from echomux.ui_components import FileListWidget, MaterialButton
from echomux.utils import analyze_media_file, get_languages, open_file_location
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

        # Video files widget
        self.video_files_widget = FileListWidget(
            title="Video Files",
            allowed_extensions=['.mp4', '.mkv', '.avi', '.mov', '.m4v'],
            table_headers=["Filename", "Duration", "Audio Tracks"]
        )
        self.video_files_widget.files_added.connect(self._on_video_files_added)
        self.video_files_widget.files_cleared.connect(self._clear_video_files)
        self.video_files_widget.table.customContextMenuRequested.connect(self._show_video_context_menu)
        layout.addWidget(self.video_files_widget)

        # Audio files widget
        self.audio_files_widget = FileListWidget(
            title="Audio Files to Merge",
            allowed_extensions=['.aac', '.mp3', '.flac', '.ogg', '.wav', '.m4a'],
            table_headers=["Audio File", "Language"]
        )
        self.audio_files_widget.files_added.connect(self._on_audio_files_added)
        self.audio_files_widget.files_cleared.connect(self._clear_audio_files)
        self.audio_files_widget.table.customContextMenuRequested.connect(self._show_audio_context_menu)
        layout.addWidget(self.audio_files_widget)

        # Settings section
        settings_group = QGroupBox("Merge Settings")
        settings_layout = QGridLayout(settings_group)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Select output directory...")
        self.browse_output_btn = MaterialButton("Browse")
        self.browse_output_btn.clicked.connect(self.browse_output)
        settings_layout.addWidget(QLabel("Output Directory:"), 0, 0)
        settings_layout.addWidget(self.output_path, 0, 1)
        settings_layout.addWidget(self.browse_output_btn, 0, 2)
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

    def _show_video_context_menu(self, position):
        self._show_context_menu_for_table(self.video_files_widget.table, position, self._remove_selected_videos, self._open_selected_video_location)

    def _show_audio_context_menu(self, position):
        self._show_context_menu_for_table(self.audio_files_widget.table, position, self._remove_selected_audio, self._open_selected_audio_location)

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
        selected_rows = sorted(list(set(item.row() for item in self.video_files_widget.table.selectedItems())), reverse=True)
        for row in selected_rows:
            self.video_files.pop(row)
            self.video_files_widget.table.removeRow(row)
        self.video_files_widget.update_visibility()
        self.update_preview()

    def _remove_selected_audio(self):
        selected_rows = sorted(list(set(item.row() for item in self.audio_files_widget.table.selectedItems())), reverse=True)
        for row in selected_rows:
            self.audio_files_data.pop(row)
            self.audio_files_widget.table.removeRow(row)
        self.audio_files_widget.update_visibility()
        self.update_preview()

    def _open_selected_video_location(self):
        self._open_location_for_table(self.video_files_widget.table, self.video_files, is_media_file=True)

    def _open_selected_audio_location(self):
        self._open_location_for_table(self.audio_files_widget.table, self.audio_files_data, is_media_file=False)

    def _open_location_for_table(self, table, data_list, is_media_file):
        selected_rows = list(set(item.row() for item in table.selectedItems()))
        if not selected_rows:
            return
        item = data_list[selected_rows[0]]
        path = item.path if is_media_file else item[0]
        open_file_location(str(path))

    def _on_video_files_added(self, files: List[str]):
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
            self.video_files_widget.add_row([media_file.filename, duration_str, audio_info_str])
        self.update_preview()

    def _clear_video_files(self):
        self.video_files.clear()
        self.update_preview()

    def _on_audio_files_added(self, files: List[str]):
        for file_path in files:
            if any(af[0] == file_path for af in self.audio_files_data):
                continue
            lang_combo = QComboBox()
            for name, code in self.languages:
                lang_combo.addItem(f"{name} ({code})", code)
            self.audio_files_data.append((file_path, lang_combo))
            self.audio_files_widget.add_row([Path(file_path).name, lang_combo])
        self.update_preview()

    def _clear_audio_files(self):
        self.audio_files_data.clear()
        self.update_preview()

    def refresh_language_dropdowns(self):
        self.languages = get_languages()
        for _, combo in self.audio_files_data:
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
