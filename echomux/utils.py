import os
import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict


def process_paths(paths: List[str], allowed_extensions: List[str]) -> List[str]:
    """
    Processes a list of paths, which can be files or directories.
    Recursively finds all files with allowed extensions.

    Args:
        paths: A list of string paths to process.
        allowed_extensions: A list of allowed file extensions (e.g., ['.mp4', '.mkv']).

    Returns:
        A sorted, unique list of valid file paths.
    """
    found_files = set()
    lower_extensions = [ext.lower() for ext in allowed_extensions]

    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            continue

        if path.is_dir():
            for root, _, files in os.walk(path):
                for name in files:
                    file_path = Path(root) / name
                    if file_path.suffix.lower() in lower_extensions:
                        found_files.add(str(file_path))
        elif path.is_file():
            if path.suffix.lower() in lower_extensions:
                found_files.add(str(path))

    return sorted(list(found_files))


def get_ffmpeg_path() -> str:
    """
    Gets the path to the ffmpeg executable from settings, or returns 'ffmpeg'.
    """
    from PyQt6.QtCore import QSettings
    settings = QSettings("EchoMux", "EchoMux")
    ffmpeg_path = settings.value("ffmpeg_path", "ffmpeg", type=str)
    return ffmpeg_path if ffmpeg_path else "ffmpeg"


DEFAULT_LANGUAGES = [
    ("English", "eng"), ("Spanish", "spa"), ("French", "fra"),
    ("German", "ger"), ("Japanese", "jpn"), ("Arabic", "ara"),
    ("Russian", "rus"), ("Portuguese", "por"), ("Chinese", "chi"),
    ("Italian", "ita"), ("Korean", "kor"), ("Hindi", "hin")
]

def get_languages() -> List[Tuple[str, str]]:
    """
    Gets the list of languages, combining defaults with custom ones from settings.
    """
    from PyQt6.QtCore import QSettings
    settings = QSettings("EchoMux", "EchoMux")
    custom_languages_raw = settings.value("custom_languages", [], type=list)

    # Ensure custom languages are in the correct format
    custom_languages = []
    for lang in custom_languages_raw:
        if isinstance(lang, list) and len(lang) == 2:
            custom_languages.append(tuple(lang))

    # Combine and sort
    all_languages = sorted(list(set(DEFAULT_LANGUAGES + custom_languages)), key=lambda x: x[0])
    return all_languages

def add_language(name: str, code: str):
    """
    Adds a new custom language to the settings.
    """
    from PyQt6.QtCore import QSettings
    settings = QSettings("EchoMux", "EchoMux")
    custom_languages = settings.value("custom_languages", [], type=list)

    # Avoid duplicates
    if not any(c[1].lower() == code.lower() for c in custom_languages):
        custom_languages.append([name, code])
        settings.setValue("custom_languages", custom_languages)

def remove_language(code: str):
    """
    Removes a custom language from the settings by its code.
    """
    from PyQt6.QtCore import QSettings
    settings = QSettings("EchoMux", "EchoMux")
    custom_languages = settings.value("custom_languages", [], type=list)

    new_custom_languages = [lang for lang in custom_languages if lang[1].lower() != code.lower()]

    settings.setValue("custom_languages", new_custom_languages)

def analyze_media_file(file_path: str) -> Optional[Dict]:
    """
    Analyzes a media file using ffprobe to get stream information.
    """
    import json
    import subprocess
    ffmpeg_path = get_ffmpeg_path()
    ffprobe_path = str(Path(ffmpeg_path).parent / "ffprobe")

    cmd = [
        ffprobe_path,
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        file_path
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            encoding='utf-8',
            errors='ignore'
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return None

import sys
import subprocess

def open_file_location(file_path: str):
    """
    Opens the directory containing the given file in the system's file explorer.
    """
    path = Path(file_path)
    if not path.exists():
        # If the path is just a filename, it might not have a parent.
        # In this case, we can't do anything.
        return

    directory = path.parent

    if sys.platform == "win32":
        os.startfile(directory)
    elif sys.platform == "darwin": # macOS
        subprocess.call(["open", str(directory)])
    else: # Linux and other Unix-like systems
        subprocess.call(["xdg-open", str(directory)])

def extract_season_episode(filename: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract season and episode numbers from filename using various patterns.
    """
    patterns = [
        r'[Ss](\d+)[Ee](\d+)',                # S01E02
        r'(\d+)x(\d+)',                      # 1x02
        r'Season\s*(\d+).*Episode\s*(\d+)',  # Season 1 Episode 2
        r'(\d+)\s*-\s*(\d+)',                # 1-02
    ]

    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))

    return None, None
