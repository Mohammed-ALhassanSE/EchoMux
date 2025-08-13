import re
from pathlib import Path
from typing import List

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QProgressBar,
    QFileDialog, QCheckBox,
    QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout, QScrollArea,
    QComboBox, QPushButton, QMenu, QInputDialog, QApplication
)

from echomux.ui_components import QTableWidgetWithDrop, MaterialButton
from echomux.utils import process_paths, extract_season_episode, open_file_location
from echomux.worker import ProcessingJob, FFmpegWorker, MediaFile
from echomux.api_client import ApiClient


class BulkRenamingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.media_files = []
        self.preview_data = []
        self.api_client = ApiClient()
        self.show_search_cache = {}
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

        # Input files section
        input_group = QGroupBox("Media Files")
        input_layout = QVBoxLayout(input_group)

        allowed_extensions = [
            '.mp4', '.mkv', '.avi', '.mov', '.m4v',
            '.mp3', '.flac', '.aac', '.ogg', '.wav', '.m4a',
            '.srt', '.ass', '.vtt', '.sub'
        ]
        self.preview_table = QTableWidgetWithDrop(allowed_extensions=allowed_extensions)
        self.preview_table.files_dropped.connect(self.on_files_added)
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["Current Name", "→", "New Name"])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setMinimumHeight(200)
        self.preview_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.preview_table.customContextMenuRequested.connect(self.show_context_menu)
        input_layout.addWidget(self.preview_table)

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

        # Renaming settings section
        settings_group = QGroupBox("Renaming Settings")
        settings_layout = QGridLayout(settings_group)
        settings_layout.addWidget(QLabel("Series/Movie Name:"), 0, 0)
        self.show_name = QLineEdit()
        self.show_name.setPlaceholderText("Enter Series or Movie Name...")
        self.show_name.textChanged.connect(self.update_preview)
        settings_layout.addWidget(self.show_name, 0, 1, 1, 2)
        settings_layout.addWidget(QLabel("Template Presets:"), 1, 0)
        self.template_presets = QComboBox()
        self.template_presets.addItems(["Custom", "TV Show", "Movie (Title First)"])
        self.template_presets.currentIndexChanged.connect(self.on_preset_changed)
        settings_layout.addWidget(self.template_presets, 1, 1, 1, 2)
        settings_layout.addWidget(QLabel("Filename Template:"), 2, 0)
        self.filename_template = QLineEdit()
        settings = QSettings("EchoMux", "EchoMux")
        default_template = "{name} - S{season:02d}E{episode:02d} - {title}{ext}"
        self.filename_template.setText(settings.value("rename_template", default_template, type=str))
        self.filename_template.textChanged.connect(self.update_preview)
        settings_layout.addWidget(self.filename_template, 2, 1, 1, 2)
        token_layout = QHBoxLayout()
        tokens = ["{name}", "{season:02d}", "{episode:02d}", "{title}", "{ext}", "{year}"]
        for token in tokens:
            btn = QPushButton(token)
            btn.clicked.connect(lambda _, t=token: self.insert_token(t))
            token_layout.addWidget(btn)
        token_layout.addStretch()
        settings_layout.addLayout(token_layout, 3, 1, 1, 2)
        self.use_api = QCheckBox("Fetch episode titles from The Movie Database")
        self.use_api.stateChanged.connect(self.update_preview)
        settings_layout.addWidget(self.use_api, 4, 0, 1, 3)
        self.preview_mode = QCheckBox("Preview mode (don't actually rename files)")
        self.preview_mode.setChecked(True)
        settings_layout.addWidget(self.preview_mode, 5, 0, 1, 3)
        layout.addWidget(settings_group)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Ready to rename files")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        layout.addWidget(progress_group)

        # Control buttons
        control_layout = QHBoxLayout()
        self.rename_btn = MaterialButton("Start Renaming", primary=True)
        self.rename_btn.clicked.connect(self.start_renaming)
        self.cancel_btn = MaterialButton("Cancel")
        self.cancel_btn.setEnabled(False)
        control_layout.addStretch()
        control_layout.addWidget(self.rename_btn)
        control_layout.addWidget(self.cancel_btn)
        layout.addLayout(control_layout)
        layout.addStretch()

        self.check_api_status()

    def showEvent(self, event):
        super().showEvent(event)
        self.check_api_status()

    def check_api_status(self):
        if self.api_client.is_configured():
            self.use_api.setEnabled(True)
            self.use_api.setToolTip("Fetch episode titles using the configured TMDB API key.")
        else:
            self.use_api.setEnabled(False)
            self.use_api.setToolTip("Please set your TMDB API key in the Settings tab to use this feature.")

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Media Files", "", "Media Files (*.mp4 *.mkv *.avi *.mov *.m4v *.mp3 *.flac *.srt *.ass)"
        )
        if files:
            self.on_files_added(files)

    def add_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder")
        if directory:
            self.on_files_added(process_paths([directory], self.preview_table.allowed_extensions))

    def on_files_added(self, files: List[str]):
        for file_path in files:
            if any(mf.path == Path(file_path) for mf in self.media_files):
                continue
            media_file = MediaFile(Path(file_path), Path(file_path).name)
            self.media_files.append(media_file)
        self.update_preview()

    def clear_files(self):
        self.media_files = []
        self.update_preview()

    def on_preset_changed(self, index):
        if index == 1:
            self.filename_template.setText("{name} - S{season:02d}E{episode:02d} - {title}{ext}")
        elif index == 2:
            self.filename_template.setText("{title} ({year}) - {name}{ext}")

    def insert_token(self, token):
        self.filename_template.insert(token)

    def show_context_menu(self, position):
        if not self.preview_table.selectedItems():
            return

        menu = QMenu()

        open_loc_action = menu.addAction("Open File Location")
        menu.addSeparator()
        remove_action = menu.addAction("Remove Selected")
        menu.addSeparator()
        find_replace_action = menu.addAction("Find & Replace in Filenames...")
        add_prefix_action = menu.addAction("Add Prefix...")
        add_suffix_action = menu.addAction("Add Suffix...")

        action = menu.exec(self.preview_table.mapToGlobal(position))

        if action == remove_action:
            self._remove_selected_files()
        elif action == open_loc_action:
            self._open_selected_file_location()
        elif action == find_replace_action:
            self.handle_find_replace()
        elif action == add_prefix_action:
            self.handle_add_prefix_suffix(is_prefix=True)
        elif action == add_suffix_action:
            self.handle_add_prefix_suffix(is_prefix=False)

    def _remove_selected_files(self):
        selected_rows = sorted(list(set(item.row() for item in self.preview_table.selectedItems())), reverse=True)
        for row in selected_rows:
            self.media_files.pop(row)
        self.update_preview()

    def _open_selected_file_location(self):
        selected_rows = list(set(item.row() for item in self.preview_table.selectedItems()))
        if not selected_rows:
            return
        file_to_open = self.media_files[selected_rows[0]]
        open_file_location(str(file_to_open.path))

    def handle_find_replace(self):
        find_text, ok1 = QInputDialog.getText(self, 'Find & Replace', 'Text to find:')
        if not (ok1 and find_text): return
        replace_text, ok2 = QInputDialog.getText(self, 'Find & Replace', f'Replace "{find_text}" with:')
        if not ok2: return
        for media_file in self.media_files:
            media_file.filename = media_file.filename.replace(find_text, replace_text)
        self.update_preview()

    def handle_add_prefix_suffix(self, is_prefix=True):
        title = "Add Prefix" if is_prefix else "Add Suffix"
        text, ok = QInputDialog.getText(self, title, f'{title}:')
        if not (ok and text): return
        for media_file in self.media_files:
            p = Path(media_file.filename)
            new_stem = text + p.stem if is_prefix else p.stem + text
            media_file.filename = new_stem + p.suffix
        self.update_preview()

    def update_preview(self):
        self.preview_table.setRowCount(0)
        if not self.media_files:
            return

        self.preview_table.setRowCount(len(self.media_files))
        self.preview_data = []
        show_name = self.show_name.text().strip()

        show = None
        if show_name and self.use_api.isChecked() and self.api_client.is_configured():
            if show_name in self.show_search_cache:
                show = self.show_search_cache[show_name]
            else:
                show = self.api_client.search_show(show_name)
                self.show_search_cache[show_name] = show

        for i, media_file in enumerate(self.media_files):
            self.preview_table.setItem(i, 0, QTableWidgetItem(media_file.filename))
            self.preview_table.setItem(i, 1, QTableWidgetItem("→"))
            new_name = ""
            if show_name:
                season, episode = extract_season_episode(media_file.filename)
                if season and episode:
                    episode_title = ""
                    if show:
                        QApplication.processEvents() # Keep UI responsive during API calls
                        title = self.api_client.get_episode_title(show.id, season, episode)
                        episode_title = title if title else "Episode Not Found"

                    new_name = self.build_new_filename(show_name, season, episode, episode_title, Path(media_file.filename).suffix)
                else:
                    new_name = "⚠️ Could not parse S/E"
            self.preview_table.setItem(i, 2, QTableWidgetItem(new_name))
            self.preview_data.append({
                'original': media_file,
                'new_name': new_name,
                'valid': bool(new_name and "⚠️" not in new_name and "Not Found" not in new_name)
            })

    def build_new_filename(self, show_name, season, episode, episode_title, extension):
        template = self.filename_template.text()
        clean_name = re.sub(r'[<>:"/\\|?*]', '', show_name)
        clean_title = re.sub(r'[<>:"/\\|?*]', '', episode_title) if episode_title else ''
        year_match = re.search(r'\((\d{4})\)', clean_name)
        year = year_match.group(1) if year_match else ""

        try:
            return template.format(name=clean_name, season=season, episode=episode, title=clean_title, ext=extension, year=year)
        except Exception:
            return f"{clean_name} - S{season:02d}E{episode:02d}{extension}"

    def start_renaming(self):
        if not self.media_files:
            QMessageBox.warning(self, "Warning", "Please add media files first.")
            return
        if not self.show_name.text().strip():
            QMessageBox.warning(self, "Warning", "Please enter a show name.")
            return
        valid_count = sum(1 for item in self.preview_data if item['valid'])
        if valid_count == 0:
            QMessageBox.warning(self, "Warning", "No files have valid season/episode information.")
            return

        if not self.preview_mode.isChecked():
            overwrites = []
            for item in self.preview_data:
                if not item['valid']: continue
                original_path = item['original'].path
                new_path = original_path.parent / item['new_name']
                if new_path.exists() and new_path != original_path:
                    overwrites.append(item['new_name'])
            if overwrites:
                msg = f"The following files already exist and will be overwritten:\n\n" + "\\n".join(overwrites[:5])
                if len(overwrites) > 5: msg += f"\n...and {len(overwrites) - 5} more."
                msg += "\n\nDo you want to continue?"
                reply = QMessageBox.warning(self, "Overwrite Warning", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply != QMessageBox.StandardButton.Yes: return

        mode_text = "preview" if self.preview_mode.isChecked() else "rename"
        reply = QMessageBox.question(self, "Confirm Renaming", f"This will {mode_text} {valid_count} files. Continue?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return

        job = ProcessingJob(input_files=self.media_files, output_directory=Path(), job_type='rename', settings={'show_name': self.show_name.text().strip(),'filename_template': self.filename_template.text(),'use_api': self.use_api.isChecked(),'preview_mode': self.preview_mode.isChecked()})
        self.worker = FFmpegWorker(job)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.status_updated.connect(self.status_label.setText)
        self.worker.job_completed.connect(self.on_job_completed)
        self.cancel_btn.clicked.connect(self.worker.cancel)

        self.rename_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.worker.start()

    def on_job_completed(self, message, success):
        try:
            self.cancel_btn.clicked.disconnect(self.worker.cancel)
        except TypeError:
            pass

        self.rename_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText(message)
        if success and not self.preview_mode.isChecked():
            self.clear_files()
            QMessageBox.information(self, "Success", message + "\nFile list has been cleared.")
        elif success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
