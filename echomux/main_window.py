from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QTabWidget, QApplication

from echomux.tabs.audio_extraction_tab import AudioExtractionTab
from echomux.tabs.audio_merging_tab import AudioMergingTab
from echomux.tabs.bulk_renaming_tab import BulkRenamingTab
from echomux.tabs.settings_tab import SettingsTab
from echomux.tabs.subtitle_embedding_tab import SubtitleEmbeddingTab
from echomux.theme import LIGHT_STYLESHEET, DARK_STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("EchoMux", "EchoMux")
        self.setWindowTitle("EchoMux - Media Toolkit")

        self.setup_ui()
        self.apply_theme()
        self._read_settings()

    def _read_settings(self):
        """Read and apply window geometry settings."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Default size if no settings are found
            self.setGeometry(100, 100, 1200, 800)

    def closeEvent(self, event):
        """Save window geometry settings on close."""
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.header = QLabel("🎬 EchoMux - Media Toolkit")
        self.header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.header)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)

        # Instantiate tabs
        self.audio_extraction_tab = AudioExtractionTab()
        self.audio_merging_tab = AudioMergingTab()
        self.subtitle_embedding_tab = SubtitleEmbeddingTab()
        self.bulk_renaming_tab = BulkRenamingTab()
        self.settings_tab = SettingsTab()

        # Add tabs
        self.tab_widget.addTab(self.audio_extraction_tab, "🎵 Audio Extraction")
        self.tab_widget.addTab(self.audio_merging_tab, "🔄 Audio Merging")
        self.tab_widget.addTab(self.subtitle_embedding_tab, "📝 Subtitle Embedding")
        self.tab_widget.addTab(self.bulk_renaming_tab, "🗃 Bulk Renaming")
        self.tab_widget.addTab(self.settings_tab, "⚙️ Settings")

        layout.addWidget(self.tab_widget)
        self.statusBar().showMessage("Ready")

        # Connect signals
        self.settings_tab.theme_changed.connect(self.apply_theme)

    def apply_theme(self):
        """Applies the selected theme stylesheet to the application."""
        theme = self.settings.value("theme", "System", type=str)

        if theme == "Dark":
            stylesheet = DARK_STYLESHEET
        else: # Default to Light for "System" or "Light"
            stylesheet = LIGHT_STYLESHEET

        QApplication.instance().setStyleSheet(stylesheet)

        # Adjust header color based on theme
        if theme == "Dark":
            self.header.setStyleSheet("padding: 20px; color: #42A5F5;")
        else:
            self.header.setStyleSheet("padding: 20px; color: #1E88E5;")
