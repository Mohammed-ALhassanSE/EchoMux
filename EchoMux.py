import sys
import os
import subprocess
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import threading
import time
from dataclasses import dataclass
import urllib.request
import urllib.parse

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QProgressBar,
    QFileDialog, QListWidget, QCheckBox, QComboBox, QSpinBox,
    QGroupBox, QScrollArea, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QSplitter, QFrame, QGridLayout, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QHeaderView
)

from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSettings, QSize
)
from PyQt6.QtGui import (
    QFont, QPalette, QColor, QIcon, QDragEnterEvent, QDropEvent,
    QPixmap, QPainter
)

# Data classes for managing media files
@dataclass
class MediaFile:
    path: Path
    filename: str
    duration: float = 0.0
    audio_tracks: List[Dict] = None
    subtitle_tracks: List[Dict] = None
    
    def __post_init__(self):
        if self.audio_tracks is None:
            self.audio_tracks = []
        if self.subtitle_tracks is None:
            self.subtitle_tracks = []

@dataclass
class ProcessingJob:
    input_files: List[MediaFile]
    output_directory: Path
    job_type: str  # 'extract', 'merge', 'embed', 'rename'
    settings: Dict

class FFmpegWorker(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    job_completed = pyqtSignal(str, bool)
    
    def __init__(self, job: ProcessingJob):
        super().__init__()
        self.job = job
        self.is_cancelled = False
    
    def run(self):
        try:
            if self.job.job_type == 'extract':
                self.extract_audio()
            elif self.job.job_type == 'merge':
                self.merge_audio()
            elif self.job.job_type == 'embed':
                self.embed_subtitles()
            elif self.job.job_type == 'rename':
                self.bulk_rename()
        except Exception as e:
            self.job_completed.emit(f"Error: {str(e)}", False)
    
    def extract_audio(self):
        total_files = len(self.job.input_files)
        for i, media_file in enumerate(self.job.input_files):
            if self.is_cancelled:
                break
                
            self.status_updated.emit(f"Extracting audio from {media_file.filename}")
            
            output_path = self.job.output_directory / f"{media_file.path.stem}.aac"
            cmd = [
                'ffmpeg', '-i', str(media_file.path),
                '-vn', '-acodec', 'copy',
                '-y', str(output_path)
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
            except subprocess.CalledProcessError as e:
                self.job_completed.emit(f"Failed to extract from {media_file.filename}", False)
                return
        
        self.job_completed.emit("Audio extraction completed!", True)
    
    def merge_audio(self):
        total_files = len(self.job.input_files)
        for i, video_file in enumerate(self.job.input_files):
            if self.is_cancelled:
                break
            
            self.status_updated.emit(f"Merging audio into {video_file.filename}")
            
            # Find matching audio files for this video
            audio_files = self.job.settings.get('audio_files', [])
            matching_audio = []
            
            base_name = video_file.path.stem
            for audio_path in audio_files:
                audio_name = Path(audio_path).stem
                # Fuzzy matching - check if audio filename contains video base name
                if base_name.lower() in audio_name.lower() or audio_name.lower() in base_name.lower():
                    matching_audio.append(audio_path)
            
            if not matching_audio:
                self.status_updated.emit(f"No matching audio found for {video_file.filename}")
                continue
            
            # Build FFmpeg command for merging
            output_path = self.job.output_directory / f"{base_name}_merged.mkv"
            cmd = ['ffmpeg', '-i', str(video_file.path)]
            
            # Add audio inputs
            for audio_path in matching_audio:
                cmd.extend(['-i', str(audio_path)])
            
            # Map video stream
            cmd.extend(['-map', '0:v'])
            
            # Map original audio
            cmd.extend(['-map', '0:a'])
            
            # Map additional audio tracks
            for j, _ in enumerate(matching_audio):
                cmd.extend(['-map', f'{j+1}:a'])
            
            # Set metadata for language tags
            cmd.extend(['-metadata:s:a:0', 'language=eng'])  # Original audio
            for j, _ in enumerate(matching_audio):
                lang = self.job.settings.get('languages', ['spa'])[min(j, len(self.job.settings.get('languages', ['spa']))-1)]
                cmd.extend(['-metadata:s:a:' + str(j+1), f'language={lang}'])
            
            # Copy codecs to avoid re-encoding
            cmd.extend(['-c:v', 'copy', '-c:a', 'copy'])
            cmd.extend(['-y', str(output_path)])
            
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                while True:
                    if self.is_cancelled:
                        process.terminate()
                        break
                    output = process.stderr.readline()
                    if output == '' and process.poll() is not None:
                        break
                    # Could parse FFmpeg progress here if needed
                
                if process.returncode == 0 and not self.is_cancelled:
                    progress = int((i + 1) / total_files * 100)
                    self.progress_updated.emit(progress)
                else:
                    self.job_completed.emit(f"Failed to merge audio for {video_file.filename}", False)
                    return
                    
            except Exception as e:
                self.job_completed.emit(f"Error processing {video_file.filename}: {str(e)}", False)
                return
        
        if not self.is_cancelled:
            self.job_completed.emit("Audio merging completed!", True)
    
    def embed_subtitles(self):
        total_files = len(self.job.input_files)
        for i, video_file in enumerate(self.job.input_files):
            if self.is_cancelled:
                break
                
            self.status_updated.emit(f"Embedding subtitles in {video_file.filename}")
            
            # Find matching subtitle files
            subtitle_files = self.job.settings.get('subtitle_files', [])
            matching_subs = []
            
            base_name = video_file.path.stem
            for sub_path in subtitle_files:
                sub_name = Path(sub_path).stem
                if base_name.lower() in sub_name.lower() or sub_name.lower() in base_name.lower():
                    matching_subs.append(sub_path)
            
            if not matching_subs:
                self.status_updated.emit(f"No matching subtitles found for {video_file.filename}")
                continue
            
            # Build FFmpeg command for embedding subtitles
            output_path = self.job.output_directory / f"{base_name}_subtitled.mkv"
            cmd = ['ffmpeg', '-i', str(video_file.path)]
            
            # Add subtitle inputs
            for sub_path in matching_subs:
                cmd.extend(['-i', str(sub_path)])
            
            # Map video and audio streams
            cmd.extend(['-map', '0:v', '-map', '0:a'])
            
            # Map subtitle streams
            for j, _ in enumerate(matching_subs):
                cmd.extend(['-map', f'{j+1}:s'])
            
            # Set subtitle metadata
            for j, sub_path in enumerate(matching_subs):
                # Try to detect language from filename
                sub_name = Path(sub_path).stem.lower()
                if 'spanish' in sub_name or 'spa' in sub_name or 'es' in sub_name:
                    lang = 'spa'
                elif 'french' in sub_name or 'fra' in sub_name or 'fr' in sub_name:
                    lang = 'fra'
                elif 'german' in sub_name or 'ger' in sub_name or 'de' in sub_name:
                    lang = 'ger'
                else:
                    lang = 'eng'  # Default to English
                
                cmd.extend(['-metadata:s:s:' + str(j), f'language={lang}'])
                
                # Check if it's forced subtitles
                if 'forced' in sub_name:
                    cmd.extend(['-disposition:s:' + str(j), 'forced'])
            
            # Copy streams without re-encoding
            cmd.extend(['-c:v', 'copy', '-c:a', 'copy', '-c:s', 'copy'])
            cmd.extend(['-y', str(output_path)])
            
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                while True:
                    if self.is_cancelled:
                        process.terminate()
                        break
                    output = process.stderr.readline()
                    if output == '' and process.poll() is not None:
                        break
                
                if process.returncode == 0 and not self.is_cancelled:
                    progress = int((i + 1) / total_files * 100)
                    self.progress_updated.emit(progress)
                else:
                    self.job_completed.emit(f"Failed to embed subtitles for {video_file.filename}", False)
                    return
                    
            except Exception as e:
                self.job_completed.emit(f"Error processing {video_file.filename}: {str(e)}", False)
                return
        
        if not self.is_cancelled:
            self.job_completed.emit("Subtitle embedding completed!", True)
    
    def bulk_rename(self):
        total_files = len(self.job.input_files)
        renamed_count = 0
        
        for i, media_file in enumerate(self.job.input_files):
            if self.is_cancelled:
                break
            
            self.status_updated.emit(f"Processing {media_file.filename}")
            
            # Extract season/episode info
            season, episode = self.extract_season_episode(media_file.filename)
            
            if season and episode:
                # Get show info from settings
                show_name = self.job.settings.get('show_name', 'Unknown Show')
                use_api = self.job.settings.get('use_api', False)
                episode_title = ""
                
                if use_api:
                    episode_title = self.get_episode_title(show_name, season, episode)
                
                # Build new filename
                new_name = self.build_new_filename(
                    show_name, season, episode, episode_title,
                    media_file.path.suffix, self.job.settings
                )
                
                new_path = media_file.path.parent / new_name
                
                # Rename the file
                try:
                    if not self.job.settings.get('preview_mode', False):
                        media_file.path.rename(new_path)
                    renamed_count += 1
                    self.status_updated.emit(f"Renamed: {media_file.filename} → {new_name}")
                except Exception as e:
                    self.status_updated.emit(f"Failed to rename {media_file.filename}: {str(e)}")
            
            progress = int((i + 1) / total_files * 100)
            self.progress_updated.emit(progress)
        
        if not self.is_cancelled:
            mode = "Preview completed" if self.job.settings.get('preview_mode', False) else f"Renamed {renamed_count} files"
            self.job_completed.emit(f"Bulk renaming completed! {mode}", True)
    
    def extract_season_episode(self, filename: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract season and episode numbers from filename"""
        patterns = [
            r'[Ss](\d{1,2})[Ee](\d{1,2})',  # S01E01
            r'(\d{1,2})x(\d{1,2})',         # 1x01
            r'Season\s*(\d{1,2}).*Episode\s*(\d{1,2})',  # Season 1 Episode 1
            r'(\d{1,2})\s*-\s*(\d{1,2})',   # 1-01
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1)), int(match.group(2))
        
        return None, None
    
    def get_episode_title(self, show_name: str, season: int, episode: int) -> str:
        """Fetch episode title from TMDb (simplified mock implementation)"""
        try:
            # In a real implementation, you'd use the TMDb API
            # For now, return a placeholder
            return f"Episode {episode}"
        except:
            return f"Episode {episode}"
    
    def build_new_filename(self, show_name: str, season: int, episode: int, 
                          episode_title: str, extension: str, settings: Dict) -> str:
        """Build the new filename according to template"""
        template = settings.get('filename_template', '{show} - S{season:02d}E{episode:02d} - {title}{ext}')
        
        # Clean up names
        clean_show = re.sub(r'[<>:"/\\|?*]', '', show_name)
        clean_title = re.sub(r'[<>:"/\\|?*]', '', episode_title) if episode_title else ''
        
        try:
            return template.format(
                show=clean_show,
                season=season,
                episode=episode,
                title=clean_title,
                ext=extension
            )
        except:
            # Fallback format
            return f"{clean_show} - S{season:02d}E{episode:02d}{extension}"
    
    def cancel(self):
        self.is_cancelled = True

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
    
    def __init__(self):
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
        
        # Add placeholder text
        self.placeholder = QListWidgetItem("Drop video files here or click 'Add Files' button")
        self.placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        self.addItem(self.placeholder)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.m4v')):
                files.append(file_path)
        
        if files:
            self.clear()  # Remove placeholder
            for file_path in files:
                self.addItem(Path(file_path).name)
            self.files_dropped.emit(files)

class AudioExtractionTab(QWidget):
    def __init__(self):
        super().__init__()
        self.input_files = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Input section
        input_group = QGroupBox("Input Files")
        input_layout = QVBoxLayout(input_group)
        
        self.file_list = FileDropWidget()
        self.file_list.files_dropped.connect(self.on_files_added)
        input_layout.addWidget(self.file_list)
        
        button_layout = QHBoxLayout()
        self.add_files_btn = MaterialButton("Add Files")
        self.add_files_btn.clicked.connect(self.add_files)
        self.clear_files_btn = MaterialButton("Clear")
        self.clear_files_btn.clicked.connect(self.clear_files)
        
        button_layout.addWidget(self.add_files_btn)
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
    
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files",
            "", "Video Files (*.mp4 *.mkv *.avi *.mov *.m4v)"
        )
        if files:
            self.on_files_added(files)
    
    def on_files_added(self, files):
        self.file_list.clear()
        self.input_files = []
        
        for file_path in files:
            media_file = MediaFile(Path(file_path), Path(file_path).name)
            self.input_files.append(media_file)
            self.file_list.addItem(media_file.filename)
    
    def clear_files(self):
        self.file_list.clear()
        self.input_files = []
        placeholder = QListWidgetItem("Drop video files here or click 'Add Files' button")
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        self.file_list.addItem(placeholder)
    
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
        
        self.extract_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.worker.start()
    
    def on_job_completed(self, message, success):
        self.extract_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText(message)
        
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

class AudioMergingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.video_files = []
        self.audio_files = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Video files section
        video_group = QGroupBox("Video Files")
        video_layout = QVBoxLayout(video_group)
        
        self.video_list = FileDropWidget()
        self.video_list.files_dropped.connect(self.on_video_files_added)
        video_layout.addWidget(self.video_list)
        
        video_button_layout = QHBoxLayout()
        self.add_videos_btn = MaterialButton("Add Video Files")
        self.add_videos_btn.clicked.connect(self.add_video_files)
        self.clear_videos_btn = MaterialButton("Clear Videos")
        self.clear_videos_btn.clicked.connect(self.clear_video_files)
        
        video_button_layout.addWidget(self.add_videos_btn)
        video_button_layout.addWidget(self.clear_videos_btn)
        video_button_layout.addStretch()
        
        video_layout.addLayout(video_button_layout)
        layout.addWidget(video_group)
        
        # Audio files section
        audio_group = QGroupBox("Audio Files to Merge")
        audio_layout = QVBoxLayout(audio_group)
        
        self.audio_list = QListWidget()
        self.audio_list.setMinimumHeight(120)
        self.audio_list.setStyleSheet("""
            QListWidget {
                border: 2px dashed #BDBDBD;
                border-radius: 8px;
                background-color: #FAFAFA;
                padding: 10px;
            }
        """)
        audio_layout.addWidget(self.audio_list)
        
        audio_button_layout = QHBoxLayout()
        self.add_audio_btn = MaterialButton("Add Audio Files")
        self.add_audio_btn.clicked.connect(self.add_audio_files)
        self.clear_audio_btn = MaterialButton("Clear Audio")
        self.clear_audio_btn.clicked.connect(self.clear_audio_files)
        
        audio_button_layout.addWidget(self.add_audio_btn)
        audio_button_layout.addWidget(self.clear_audio_btn)
        audio_button_layout.addStretch()
        
        audio_layout.addLayout(audio_button_layout)
        layout.addWidget(audio_group)
        
        # Settings section
        settings_group = QGroupBox("Merge Settings")
        settings_layout = QGridLayout(settings_group)
        
        settings_layout.addWidget(QLabel("Output Directory:"), 0, 0)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Select output directory...")
        settings_layout.addWidget(self.output_path, 0, 1)
        
        self.browse_output_btn = MaterialButton("Browse")
        self.browse_output_btn.clicked.connect(self.browse_output)
        settings_layout.addWidget(self.browse_output_btn, 0, 2)
        
        settings_layout.addWidget(QLabel("Audio Languages:"), 1, 0)
        self.languages_input = QLineEdit()
        self.languages_input.setText("spa,fra,ger")
        self.languages_input.setPlaceholderText("Enter language codes (e.g., spa,fra,ger)")
        settings_layout.addWidget(self.languages_input, 1, 1, 1, 2)
        
        self.preserve_original = QCheckBox("Preserve original audio track")
        self.preserve_original.setChecked(True)
        settings_layout.addWidget(self.preserve_original, 2, 0, 1, 3)
        
        layout.addWidget(settings_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Ready to merge audio tracks")
        
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
    
    def add_video_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files",
            "", "Video Files (*.mp4 *.mkv *.avi *.mov *.m4v)"
        )
        if files:
            self.on_video_files_added(files)
    
    def on_video_files_added(self, files):
        self.video_list.clear()
        self.video_files = []
        
        for file_path in files:
            media_file = MediaFile(Path(file_path), Path(file_path).name)
            self.video_files.append(media_file)
            self.video_list.addItem(media_file.filename)
    
    def clear_video_files(self):
        self.video_list.clear()
        self.video_files = []
        placeholder = QListWidgetItem("Drop video files here or click 'Add Video Files' button")
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        self.video_list.addItem(placeholder)
    
    def add_audio_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Audio Files",
            "", "Audio Files (*.aac *.mp3 *.flac *.ogg *.wav *.m4a)"
        )
        if files:
            self.audio_list.clear()
            self.audio_files = files
            for file_path in files:
                self.audio_list.addItem(Path(file_path).name)
    
    def clear_audio_files(self):
        self.audio_list.clear()
        self.audio_files = []
    
    def browse_output(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_path.setText(directory)
    
    def start_merging(self):
        if not self.video_files:
            QMessageBox.warning(self, "Warning", "Please add video files first.")
            return
        
        if not self.audio_files:
            QMessageBox.warning(self, "Warning", "Please add audio files to merge.")
            return
        
        if not self.output_path.text():
            QMessageBox.warning(self, "Warning", "Please select an output directory.")
            return
        
        languages = [lang.strip() for lang in self.languages_input.text().split(',') if lang.strip()]
        
        job = ProcessingJob(
            input_files=self.video_files,
            output_directory=Path(self.output_path.text()),
            job_type='merge',
            settings={
                'audio_files': self.audio_files,
                'languages': languages,
                'preserve_original': self.preserve_original.isChecked()
            }
        )
        
        self.worker = FFmpegWorker(job)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.status_updated.connect(self.status_label.setText)
        self.worker.job_completed.connect(self.on_job_completed)
        
        self.merge_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.clicked.connect(self.worker.cancel)
        self.worker.start()
    
    def on_job_completed(self, message, success):
        self.merge_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText(message)
        
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

class SubtitleEmbeddingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.video_files = []
        self.subtitle_files = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Video files section
        video_group = QGroupBox("Video Files")
        video_layout = QVBoxLayout(video_group)
        
        self.video_list = FileDropWidget()
        self.video_list.files_dropped.connect(self.on_video_files_added)
        video_layout.addWidget(self.video_list)
        
        video_button_layout = QHBoxLayout()
        self.add_videos_btn = MaterialButton("Add Video Files")
        self.add_videos_btn.clicked.connect(self.add_video_files)
        self.clear_videos_btn = MaterialButton("Clear Videos")
        self.clear_videos_btn.clicked.connect(self.clear_video_files)
        
        video_button_layout.addWidget(self.add_videos_btn)
        video_button_layout.addWidget(self.clear_videos_btn)
        video_button_layout.addStretch()
        
        video_layout.addLayout(video_button_layout)
        layout.addWidget(video_group)
        
        # Subtitle files section
        subtitle_group = QGroupBox("Subtitle Files")
        subtitle_layout = QVBoxLayout(subtitle_group)
        
        self.subtitle_list = QListWidget()
        self.subtitle_list.setMinimumHeight(120)
        self.subtitle_list.setStyleSheet("""
            QListWidget {
                border: 2px dashed #BDBDBD;
                border-radius: 8px;
                background-color: #FAFAFA;
                padding: 10px;
            }
        """)
        subtitle_layout.addWidget(self.subtitle_list)
        
        subtitle_button_layout = QHBoxLayout()
        self.add_subtitle_btn = MaterialButton("Add Subtitle Files")
        self.add_subtitle_btn.clicked.connect(self.add_subtitle_files)
        self.clear_subtitle_btn = MaterialButton("Clear Subtitles")
        self.clear_subtitle_btn.clicked.connect(self.clear_subtitle_files)
        
        subtitle_button_layout.addWidget(self.add_subtitle_btn)
        subtitle_button_layout.addWidget(self.clear_subtitle_btn)
        subtitle_button_layout.addStretch()
        
        subtitle_layout.addLayout(subtitle_button_layout)
        layout.addWidget(subtitle_group)
        
        # Settings section
        settings_group = QGroupBox("Embedding Settings")
        settings_layout = QGridLayout(settings_group)
        
        settings_layout.addWidget(QLabel("Output Directory:"), 0, 0)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Select output directory...")
        settings_layout.addWidget(self.output_path, 0, 1)
        
        self.browse_output_btn = MaterialButton("Browse")
        self.browse_output_btn.clicked.connect(self.browse_output)
        settings_layout.addWidget(self.browse_output_btn, 0, 2)
        
        settings_layout.addWidget(QLabel("Subtitle Type:"), 1, 0)
        self.subtitle_type = QComboBox()
        self.subtitle_type.addItems(["Soft Subtitles (Toggleable)", "Hard Subtitles (Burned-in)"])
        settings_layout.addWidget(self.subtitle_type, 1, 1, 1, 2)
        
        self.auto_language = QCheckBox("Auto-detect language from filename")
        self.auto_language.setChecked(True)
        settings_layout.addWidget(self.auto_language, 2, 0, 1, 3)
        
        self.default_subtitle = QCheckBox("Set first subtitle as default")
        self.default_subtitle.setChecked(True)
        settings_layout.addWidget(self.default_subtitle, 3, 0, 1, 3)
        
        layout.addWidget(settings_group)
        
        # Preview section
        preview_group = QGroupBox("File Matching Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(100)
        self.preview_text.setPlaceholderText("File matching preview will appear here...")
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
        self.status_label = QLabel("Ready to embed subtitles")
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self.embed_btn = MaterialButton("Embed Subtitles", primary=True)
        self.embed_btn.clicked.connect(self.start_embedding)
        self.cancel_btn = MaterialButton("Cancel")
        self.cancel_btn.setEnabled(False)
        
        control_layout.addStretch()
        control_layout.addWidget(self.embed_btn)
        control_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(control_layout)
    
    def add_video_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files",
            "", "Video Files (*.mp4 *.mkv *.avi *.mov *.m4v)"
        )
        if files:
            self.on_video_files_added(files)
    
    def on_video_files_added(self, files):
        self.video_list.clear()
        self.video_files = []
        
        for file_path in files:
            media_file = MediaFile(Path(file_path), Path(file_path).name)
            self.video_files.append(media_file)
            self.video_list.addItem(media_file.filename)
        
        self.update_preview()
    
    def clear_video_files(self):
        self.video_list.clear()
        self.video_files = []
        placeholder = QListWidgetItem("Drop video files here or click 'Add Video Files' button")
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        self.video_list.addItem(placeholder)
        self.update_preview()
    
    def add_subtitle_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Subtitle Files",
            "", "Subtitle Files (*.srt *.ass *.vtt *.sub)"
        )
        if files:
            self.subtitle_list.clear()
            self.subtitle_files = files
            for file_path in files:
                self.subtitle_list.addItem(Path(file_path).name)
            self.update_preview()
    
    def clear_subtitle_files(self):
        self.subtitle_list.clear()
        self.subtitle_files = []
        self.update_preview()
    
    def browse_output(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_path.setText(directory)
    
    def update_preview(self):
        if not self.video_files or not self.subtitle_files:
            self.preview_text.clear()
            return
        
        preview_text = "File Matching Preview:\n\n"
        
        for video_file in self.video_files:
            base_name = video_file.path.stem
            matching_subs = []
            
            for sub_path in self.subtitle_files:
                sub_name = Path(sub_path).stem
                if base_name.lower() in sub_name.lower() or sub_name.lower() in base_name.lower():
                    matching_subs.append(Path(sub_path).name)
            
            preview_text += f"📹 {video_file.filename}\n"
            if matching_subs:
                for sub in matching_subs:
                    preview_text += f"  └── 📝 {sub}\n"
            else:
                preview_text += "  └── ⚠️ No matching subtitles found\n"
            preview_text += "\n"
        
        self.preview_text.setText(preview_text)
    
    def start_embedding(self):
        if not self.video_files:
            QMessageBox.warning(self, "Warning", "Please add video files first.")
            return
        
        if not self.subtitle_files:
            QMessageBox.warning(self, "Warning", "Please add subtitle files to embed.")
            return
        
        if not self.output_path.text():
            QMessageBox.warning(self, "Warning", "Please select an output directory.")
            return
        
        job = ProcessingJob(
            input_files=self.video_files,
            output_directory=Path(self.output_path.text()),
            job_type='embed',
            settings={
                'subtitle_files': self.subtitle_files,
                'subtitle_type': self.subtitle_type.currentText(),
                'auto_language': self.auto_language.isChecked(),
                'default_subtitle': self.default_subtitle.isChecked()
            }
        )
        
        self.worker = FFmpegWorker(job)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.status_updated.connect(self.status_label.setText)
        self.worker.job_completed.connect(self.on_job_completed)
        
        self.embed_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.clicked.connect(self.worker.cancel)
        self.worker.start()
    
    def on_job_completed(self, message, success):
        self.embed_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText(message)
        
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

class BulkRenamingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.media_files = []
        self.preview_data = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Input files section
        input_group = QGroupBox("Media Files")
        input_layout = QVBoxLayout(input_group)
        
        self.file_list = FileDropWidget()
        self.file_list.files_dropped.connect(self.on_files_added)
        input_layout.addWidget(self.file_list)
        
        button_layout = QHBoxLayout()
        self.add_files_btn = MaterialButton("Add Files")
        self.add_files_btn.clicked.connect(self.add_files)
        self.clear_files_btn = MaterialButton("Clear")
        self.clear_files_btn.clicked.connect(self.clear_files)
        
        button_layout.addWidget(self.add_files_btn)
        button_layout.addWidget(self.clear_files_btn)
        button_layout.addStretch()
        
        input_layout.addLayout(button_layout)
        layout.addWidget(input_group)
        
        # Renaming settings section
        settings_group = QGroupBox("Renaming Settings")
        settings_layout = QGridLayout(settings_group)
        
        settings_layout.addWidget(QLabel("Show Name:"), 0, 0)
        self.show_name = QLineEdit()
        self.show_name.setPlaceholderText("Enter TV show or series name...")
        self.show_name.textChanged.connect(self.update_preview)
        settings_layout.addWidget(self.show_name, 0, 1, 1, 2)
        
        settings_layout.addWidget(QLabel("Filename Template:"), 1, 0)
        self.filename_template = QLineEdit()
        self.filename_template.setText("{show} - S{season:02d}E{episode:02d} - {title}{ext}")
        self.filename_template.textChanged.connect(self.update_preview)
        settings_layout.addWidget(self.filename_template, 1, 1, 1, 2)
        
        # Template help
        template_help = QLabel("Template variables: {show}, {season}, {episode}, {title}, {ext}")
        template_help.setStyleSheet("color: #666; font-size: 10px;")
        settings_layout.addWidget(template_help, 2, 1, 1, 2)
        
        self.use_api = QCheckBox("Fetch episode titles from online database")
        self.use_api.stateChanged.connect(self.update_preview)
        settings_layout.addWidget(self.use_api, 3, 0, 1, 3)
        
        self.preview_mode = QCheckBox("Preview mode (don't actually rename files)")
        self.preview_mode.setChecked(True)
        settings_layout.addWidget(self.preview_mode, 4, 0, 1, 3)
        
        layout.addWidget(settings_group)
        
        # Preview section
        preview_group = QGroupBox("Renaming Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["Current Name", "→", "New Name"])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setMinimumHeight(200)
        
        preview_layout.addWidget(self.preview_table)
        
        preview_button_layout = QHBoxLayout()
        self.refresh_preview_btn = MaterialButton("Refresh Preview")
        self.refresh_preview_btn.clicked.connect(self.update_preview)
        preview_button_layout.addWidget(self.refresh_preview_btn)
        preview_button_layout.addStretch()
        
        preview_layout.addLayout(preview_button_layout)
        layout.addWidget(preview_group)
        
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
    
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Media Files",
            "", "Media Files (*.mp4 *.mkv *.avi *.mov *.m4v *.mp3 *.flac *.srt *.ass)"
        )
        if files:
            self.on_files_added(files)
    
    def on_files_added(self, files):
        self.file_list.clear()
        self.media_files = []
        
        for file_path in files:
            media_file = MediaFile(Path(file_path), Path(file_path).name)
            self.media_files.append(media_file)
            self.file_list.addItem(media_file.filename)
        
        self.update_preview()
    
    def clear_files(self):
        self.file_list.clear()
        self.media_files = []
        self.preview_table.setRowCount(0)
        placeholder = QListWidgetItem("Drop media files here or click 'Add Files' button")
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        self.file_list.addItem(placeholder)
    
    def extract_season_episode(self, filename: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract season and episode numbers from filename"""
        patterns = [
            r'[Ss](\d{1,2})[Ee](\d{1,2})',  # S01E01
            r'(\d{1,2})x(\d{1,2})',         # 1x01
            r'Season\s*(\d{1,2}).*Episode\s*(\d{1,2})',  # Season 1 Episode 1
            r'(\d{1,2})\s*-\s*(\d{1,2})',   # 1-01
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1)), int(match.group(2))
        
        return None, None
    
    def update_preview(self):
        if not self.media_files or not self.show_name.text().strip():
            self.preview_table.setRowCount(0)
            return
        
        self.preview_table.setRowCount(len(self.media_files))
        self.preview_data = []
        
        for i, media_file in enumerate(self.media_files):
            season, episode = self.extract_season_episode(media_file.filename)
            
            if season and episode:
                episode_title = f"Episode {episode}" if self.use_api.isChecked() else ""
                new_name = self.build_new_filename(
                    self.show_name.text().strip(), season, episode, 
                    episode_title, media_file.path.suffix
                )
            else:
                new_name = f"⚠️ Could not parse season/episode from: {media_file.filename}"
            
            # Add to table
            current_item = QTableWidgetItem(media_file.filename)
            arrow_item = QTableWidgetItem("→")
            arrow_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            new_item = QTableWidgetItem(new_name)
            
            # Color code the rows
            if "⚠️" in new_name:
                current_item.setBackground(QColor(255, 235, 235))  # Light red
                new_item.setBackground(QColor(255, 235, 235))
            else:
                current_item.setBackground(QColor(235, 255, 235))  # Light green
                new_item.setBackground(QColor(235, 255, 235))
            
            self.preview_table.setItem(i, 0, current_item)
            self.preview_table.setItem(i, 1, arrow_item)
            self.preview_table.setItem(i, 2, new_item)
            
            self.preview_data.append({
                'original': media_file,
                'new_name': new_name,
                'valid': "⚠️" not in new_name
            })
    
    def build_new_filename(self, show_name: str, season: int, episode: int, 
                          episode_title: str, extension: str) -> str:
        """Build the new filename according to template"""
        template = self.filename_template.text()
        
        # Clean up names
        clean_show = re.sub(r'[<>:"/\\|?*]', '', show_name)
        clean_title = re.sub(r'[<>:"/\\|?*]', '', episode_title) if episode_title else ''
        
        try:
            return template.format(
                show=clean_show,
                season=season,
                episode=episode,
                title=clean_title,
                ext=extension
            )
        except Exception as e:
            # Fallback format
            return f"{clean_show} - S{season:02d}E{episode:02d}{extension}"
    
    def start_renaming(self):
        if not self.media_files:
            QMessageBox.warning(self, "Warning", "Please add media files first.")
            return
        
        if not self.show_name.text().strip():
            QMessageBox.warning(self, "Warning", "Please enter a show name.")
            return
        
        # Count valid files
        valid_count = sum(1 for item in self.preview_data if item['valid'])
        if valid_count == 0:
            QMessageBox.warning(self, "Warning", "No files have valid season/episode information.")
            return
        
        # Confirmation dialog
        mode_text = "preview" if self.preview_mode.isChecked() else "rename"
        reply = QMessageBox.question(
            self, "Confirm Renaming",
            f"This will {mode_text} {valid_count} files. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        job = ProcessingJob(
            input_files=self.media_files,
            output_directory=Path(),  # Not used for renaming
            job_type='rename',
            settings={
                'show_name': self.show_name.text().strip(),
                'filename_template': self.filename_template.text(),
                'use_api': self.use_api.isChecked(),
                'preview_mode': self.preview_mode.isChecked()
            }
        )
        
        self.worker = FFmpegWorker(job)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.status_updated.connect(self.status_label.setText)
        self.worker.job_completed.connect(self.on_job_completed)
        
        self.rename_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.clicked.connect(self.worker.cancel)
        self.worker.start()
    
    def on_job_completed(self, message, success):
        self.rename_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText(message)
        
        if success:
            if not self.preview_mode.isChecked():
                # Refresh the file list to show new names
                self.update_preview()
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Track Video Remuxer & Media Manager")
        self.setGeometry(100, 100, 1200, 800)
        self.setup_ui()
        self.apply_material_theme()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Header
        header = QLabel("🎬 Multi-Track Video Remuxer & Media Manager")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("padding: 20px; color: #1976D2;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Main tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)

        # Add tabs
        self.tab_widget.addTab(AudioExtractionTab(), "🎵 Audio Extraction")
        self.tab_widget.addTab(AudioMergingTab(), "🔄 Audio Merging")
        self.tab_widget.addTab(SubtitleEmbeddingTab(), "📝 Subtitle Embedding")
        self.tab_widget.addTab(BulkRenamingTab(), "🗃 Bulk Renaming")
        # self.tab_widget.addTab(AdvancedSettingsTab(), "⚙️ Settings")  # Uncomment if implemented

        layout.addWidget(self.tab_widget)

        # Status bar
        self.statusBar().showMessage("Ready")
    
    def apply_material_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
                color: #212121;
            }
            QTabWidget::pane {
                border: 1px solid #E0E0E0;
                background-color: #FFFFFF;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #F5F5F5;
                color: #666666;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #2196F3;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #E3F2FD;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #1976D2;
            }
            QLineEdit {
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                padding: 8px;
                background-color: #FFFFFF;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
            QComboBox {
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                padding: 8px;
                background-color: #FFFFFF;
            }
            QProgressBar {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: #F5F5F5;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)

def check_dependencies():
    """Check if required dependencies are available"""
    missing = []
    
    # Check FFmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append("FFmpeg")
    
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
    icon_path = Path(__file__).parent / "icons" / "icon.ico"
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