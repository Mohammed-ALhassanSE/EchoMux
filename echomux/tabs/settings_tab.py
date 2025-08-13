from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QComboBox, QMessageBox, QListWidget, QInputDialog, QListWidgetItem
)

from echomux.utils import get_languages, add_language, remove_language, DEFAULT_LANGUAGES
from echomux.ui_components import MaterialButton

class SettingsTab(QWidget):
    theme_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.settings = QSettings("EchoMux", "EchoMux")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Appearance Settings
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QGridLayout(appearance_group)
        appearance_layout.addWidget(QLabel("Theme:"), 0, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        appearance_layout.addWidget(self.theme_combo, 0, 1)
        layout.addWidget(appearance_group)

        # General Settings
        general_group = QGroupBox("General Settings")
        general_layout = QGridLayout(general_group)
        general_layout.addWidget(QLabel("FFmpeg Executable Path:"), 0, 0)
        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_path_edit.setPlaceholderText("e.g., C:/ffmpeg/bin/ffmpeg.exe or /usr/bin/ffmpeg")
        general_layout.addWidget(self.ffmpeg_path_edit, 0, 1)
        layout.addWidget(general_group)

        # Renaming settings
        renaming_group = QGroupBox("Bulk Renaming")
        renaming_layout = QGridLayout(renaming_group)
        renaming_layout.addWidget(QLabel("Default Filename Template:"), 0, 0)
        self.rename_template_edit = QLineEdit()
        renaming_layout.addWidget(self.rename_template_edit, 0, 1)
        layout.addWidget(renaming_group)

        # API Settings
        api_group = QGroupBox("API Settings")
        api_layout = QGridLayout(api_group)
        api_layout.addWidget(QLabel("The Movie Database (TMDB) API Key:"), 0, 0)
        self.tmdb_api_key_edit = QLineEdit()
        self.tmdb_api_key_edit.setPlaceholderText("Enter your TMDB v3 API key...")
        self.tmdb_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(self.tmdb_api_key_edit, 0, 1)
        layout.addWidget(api_group)

        # Language Management
        lang_group = QGroupBox("Custom Language Management")
        lang_layout = QVBoxLayout(lang_group)
        self.lang_list_widget = QListWidget()
        lang_layout.addWidget(self.lang_list_widget)
        lang_button_layout = QHBoxLayout()
        self.add_lang_btn = MaterialButton("Add Language")
        self.remove_lang_btn = MaterialButton("Remove Selected")
        lang_button_layout.addStretch()
        lang_button_layout.addWidget(self.add_lang_btn)
        lang_button_layout.addWidget(self.remove_lang_btn)
        lang_layout.addLayout(lang_button_layout)
        layout.addWidget(lang_group)

        layout.addStretch()

        # Save button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.save_btn = MaterialButton("Save Settings", primary=True)
        button_layout.addWidget(self.save_btn)
        layout.addLayout(button_layout)

        # Connect signals
        self.save_btn.clicked.connect(self.save_settings)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        self.add_lang_btn.clicked.connect(self.add_new_language)
        self.remove_lang_btn.clicked.connect(self.remove_selected_language)

        self.load_settings()

    def populate_language_list(self):
        self.lang_list_widget.clear()
        self.languages = get_languages()
        for name, code in self.languages:
            item = QListWidgetItem(f"{name} ({code})")
            item.setData(Qt.ItemDataRole.UserRole, code)
            if not any(c[1] == code for c in DEFAULT_LANGUAGES):
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable)
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                item.setForeground(self.palette().color(self.palette().ColorGroup.Disabled, self.palette().ColorRole.WindowText))
            self.lang_list_widget.addItem(item)

    def load_settings(self):
        self.ffmpeg_path_edit.setText(self.settings.value("ffmpeg_path", "", type=str))
        default_template = "{name} - S{season:02d}E{episode:02d} - {title}{ext}"
        self.rename_template_edit.setText(self.settings.value("rename_template", default_template, type=str))
        self.tmdb_api_key_edit.setText(self.settings.value("tmdb_api_key", "", type=str))
        theme = self.settings.value("theme", "System", type=str)
        self.theme_combo.setCurrentText(theme)
        self.populate_language_list()

    def save_settings(self):
        self.settings.setValue("ffmpeg_path", self.ffmpeg_path_edit.text())
        self.settings.setValue("rename_template", self.rename_template_edit.text())
        self.settings.setValue("theme", self.theme_combo.currentText())
        self.settings.setValue("tmdb_api_key", self.tmdb_api_key_edit.text())
        QMessageBox.information(self, "Settings Saved", "Your settings have been saved.")

    def on_theme_changed(self, theme_name: str):
        self.settings.setValue("theme", self.theme_combo.currentText())
        self.theme_changed.emit()

    def add_new_language(self):
        name, ok1 = QInputDialog.getText(self, 'Add Custom Language', 'Enter full language name (e.g., German):')
        if ok1 and name:
            code, ok2 = QInputDialog.getText(self, 'Add Custom Language', f"Enter 3-letter ISO 639-2 code for {name}:")
            if ok2 and code and len(code) == 3:
                add_language(name, code)
                self.populate_language_list()
            elif ok2:
                QMessageBox.warning(self, "Invalid Code", "The language code must be 3 letters long.")

    def remove_selected_language(self):
        selected_items = self.lang_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a custom language to remove.")
            return

        item = selected_items[0]
        code = item.data(Qt.ItemDataRole.UserRole)

        if any(c[1] == code for c in DEFAULT_LANGUAGES):
            QMessageBox.warning(self, "Cannot Remove", "Default languages cannot be removed.")
            return

        reply = QMessageBox.question(self, "Confirm Remove", f"Are you sure you want to remove {item.text()}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            remove_language(code)
            self.populate_language_list()
