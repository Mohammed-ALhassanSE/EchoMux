# 🎬 EchoMux — Multi-Track Video Remuxer & Media Manager

**EchoMux** is a modern, cross-platform desktop application for managing multi-language audio tracks, subtitles, and file naming for large video collections.  
Built with **Python (PyQt6)** and powered by **FFmpeg**, it features a clean, Material Design-inspired interface that makes complex media processing simple.

---

## ✨ Features

- **🎵 Audio Extraction** — Extract audio from multiple videos at once, preserving original quality.
- **🔄 Audio Merging** — Merge extra audio tracks (e.g., different languages) into existing videos.
- **📝 Subtitle Embedding** — Embed soft or hard subtitles directly into videos.
- **🗃 Bulk Renaming** — Automatically rename videos, audios, and subtitle files with season/episode detection.
- **📂 Drag & Drop Support** — Quickly add files by dropping them into the app.
- **🌐 Optional Metadata Fetching** — Fetch episode titles from online databases (planned for future).
- **🎯 Smart Matching** — Matches audio/subtitle files to videos by filename.
- **💡 Modern UI** — Tabbed interface with Material Design theme and progress tracking.
- **🔍 Preview Modes** — Test renaming or matching before making changes.
- **💾 Profile Settings** — Save preferences for repeated workflows (future feature).

---

## 📦 Installation

### 1. Install Python (3.9+ recommended)
Download from: [https://www.python.org/downloads/](https://www.python.org/downloads/)

### 2. Install Dependencies
```bash
pip install PyQt6
````

You must also have **FFmpeg** installed and available in your system's PATH:

* Windows: [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
* macOS: `brew install ffmpeg` (via Homebrew)
* Linux: Use your package manager, e.g., `sudo apt install ffmpeg`

### 3. Clone or Download the Project

```bash
git clone https://github.com/yourusername/EchoMux.git
cd EchoMux
```

### 4. Run the Application

```bash
python EchoMux.py
```

---

## 💻 Usage

When you launch **EchoMux**, you'll see four main tabs:

1. **🎵 Audio Extraction**

   * Add video files via drag-and-drop or file picker.
   * Choose output format (AAC, MP3, FLAC, OGG).
   * Click "Extract Audio" to process.

2. **🔄 Audio Merging**

   * Add video files and matching audio files.
   * Set language tags and choose output directory.
   * Click "Merge Audio" to embed multiple audio tracks.

3. **📝 Subtitle Embedding**

   * Add video files and subtitle files.
   * Choose soft (toggleable) or hard (burned-in) subtitles.
   * Preview file matching before embedding.

4. **🗃 Bulk Renaming**

   * Add media files (video, audio, subtitles).
   * Set show name and filename template.
   * Preview renaming before applying changes.

---

## ⚙️ Requirements

* **Python** 3.9+
* **PyQt6**
* **FFmpeg** (required for all processing)
* **psutil** (optional, for system info display)

---

## 📌 Notes

* **FFmpeg is required** for all audio/video operations.
* This application is designed for **lossless remuxing** — it does not re-encode video unless required (e.g., hard subtitles).
* Recommended output format is **MKV** for best multi-track support.

---

## 🚀 Building an Executable (Windows)

If you want a `.exe` version without requiring Python:

### Option 1: PyInstaller

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icons/icon.ico EchoMux.py
```

### Option 2: Auto-py-to-exe

```bash
pip install auto-py-to-exe
auto-py-to-exe
```

* Select `EchoMux.py` as the script.
* Choose **Onefile** and **Window Based**.
* Add `icons/icon.ico` as the icon.

---

## 📄 License

MIT License — feel free to modify and distribute.

---

## 👨‍💻 Author

Developed by **\[Mohammed AL-hassan]** — Modern media management made simple.

```

---

Do you want me to also make you a **shorter “GitHub-friendly” version** with badges and screenshots so it looks professional on your repository page? That would make EchoMux look like a polished open-source app.
```
