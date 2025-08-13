import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from PyQt6.QtCore import QThread, pyqtSignal

from echomux.utils import get_ffmpeg_path, analyze_media_file


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

    def _get_duration(self, file_path: Path) -> float:
        """Gets the duration of a media file in seconds using ffprobe."""
        ffmpeg_path = get_ffmpeg_path()
        ffprobe_path = str(Path(ffmpeg_path).parent / "ffprobe")
        cmd = [
            ffprobe_path,
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(file_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            return 0.0

    def _time_str_to_seconds(self, time_str: str) -> float:
        """Converts FFmpeg's time string (HH:MM:SS.ms) to seconds."""
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds

    def build_extract_audio_cmd(self, media_file: MediaFile) -> List[str]:
        audio_format = self.job.settings.get('format', 'aac')
        codecs = {'mp3': 'libmp3lame', 'flac': 'flac', 'ogg': 'libvorbis'}
        # Use filename from MediaFile object for the output to respect changes from renamer tab
        output_stem = Path(media_file.filename).stem
        output_path = self.job.output_directory / f"{output_stem}.{audio_format}"
        ffmpeg_path = get_ffmpeg_path()

        cmd = [ffmpeg_path, '-i', str(media_file.path), '-vn']

        # This logic was flawed. If the source is not AAC, we can't 'copy' it to an AAC container.
        # Let's just always specify the AAC codec for simplicity and correctness.
        if audio_format == 'aac':
            cmd.extend(['-acodec', 'aac'])
        else:
            codec = codecs.get(audio_format)
            if codec:
                cmd.extend(['-acodec', codec])
        cmd.extend(['-y', str(output_path)])
        return cmd

    def extract_audio(self):
        total_files = len(self.job.input_files)
        for i, media_file in enumerate(self.job.input_files):
            if self.is_cancelled:
                break

            self.status_updated.emit(f"({i+1}/{total_files}) Extracting from {media_file.filename}...")
            duration = self._get_duration(media_file.path)
            if duration == 0:
                self.status_updated.emit(f"Could not get duration for {media_file.filename}. Progress will not be shown.")

            cmd = self.build_extract_audio_cmd(media_file)

            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, universal_newlines=True)

                time_regex = re.compile(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})")

                for line in iter(process.stderr.readline, ""):
                    if self.is_cancelled:
                        process.terminate()
                        break

                    match = time_regex.search(line)
                    if match and duration > 0:
                        elapsed_time = self._time_str_to_seconds(match.group(1))
                        progress = int((elapsed_time / duration) * 100)
                        # Scale progress to the overall job progress
                        overall_progress = int(((i + progress / 100) / total_files) * 100)
                        self.progress_updated.emit(overall_progress)

                process.wait()

                if process.returncode != 0 and not self.is_cancelled:
                    error_message = f"Failed to extract from {media_file.filename}.\n"
                    self.job_completed.emit(error_message, False)
                    return

            except Exception as e:
                self.job_completed.emit(f"An error occurred with {media_file.filename}: {str(e)}", False)
                return

        if not self.is_cancelled:
            self.progress_updated.emit(100)
            self.job_completed.emit("Audio extraction completed!", True)

    def build_merge_audio_cmd(self, video_file: MediaFile, matching_audio: List[str], languages: List[str]) -> List[str]:
        ffmpeg_path = get_ffmpeg_path()
        output_path = self.job.output_directory / f"{video_file.path.stem}_merged.mkv"
        cmd = [ffmpeg_path, '-i', str(video_file.path)]
        for audio_path in matching_audio:
            cmd.extend(['-i', str(audio_path)])

        if self.job.settings.get('preserve_original', True):
            # Map all streams from video, but specifically exclude its audio streams
            cmd.extend(['-map', '0', '-map', '-0:a'])
        else:
            # Map only video and subtitle streams
            cmd.extend(['-map', '0:v', '-map', '0:s?'])

        # Map the new audio streams
        for i in range(len(matching_audio)):
            cmd.extend(['-map', f'{i + 1}:a'])

        # Add language metadata to the new audio streams
        for i, lang in enumerate(languages):
            cmd.extend([f'-metadata:s:a:{i}', f'language={lang}'])

        cmd.extend(['-c', 'copy', '-y', str(output_path)])
        return cmd

    def merge_audio(self):
        total_files = len(self.job.input_files)
        for i, video_file in enumerate(self.job.input_files):
            if self.is_cancelled:
                break

            self.status_updated.emit(f"({i+1}/{total_files}) Merging audio into {video_file.filename}...")

            audio_files = self.job.settings.get('audio_files', [])
            matching_audio = [
                audio_path for audio_path in audio_files
                if video_file.path.stem.lower() in Path(audio_path).stem.lower() or
                   Path(audio_path).stem.lower() in video_file.path.stem.lower()
            ]

            if not matching_audio:
                self.status_updated.emit(f"No matching audio found for {video_file.filename}")
                continue

            duration = self._get_duration(video_file.path)
            if duration == 0:
                self.status_updated.emit(f"Could not get duration for {video_file.filename}. Progress will not be shown.")

            cmd = self._build_merge_audio_cmd(video_file, matching_audio)

            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, universal_newlines=True)
                time_regex = re.compile(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})")

                for line in iter(process.stderr.readline, ""):
                    if self.is_cancelled:
                        process.terminate()
                        break

                    match = time_regex.search(line)
                    if match and duration > 0:
                        elapsed_time = self._time_str_to_seconds(match.group(1))
                        progress = int((elapsed_time / duration) * 100)
                        overall_progress = int(((i + progress / 100) / total_files) * 100)
                        self.progress_updated.emit(overall_progress)

                process.wait()

                if process.returncode != 0 and not self.is_cancelled:
                    self.job_completed.emit(f"Failed to merge audio for {video_file.filename}", False)
                    return

            except Exception as e:
                self.job_completed.emit(f"Error processing {video_file.filename}: {str(e)}", False)
                return

        if not self.is_cancelled:
            self.progress_updated.emit(100)
            self.job_completed.emit("Audio merging completed!", True)

    def build_embed_subtitles_cmd(self, video_file: MediaFile, matching_subs: List[str], languages: List[str]) -> List[str]:
        ffmpeg_path = get_ffmpeg_path()
        output_path = self.job.output_directory / f"{video_file.path.stem}_subtitled.mkv"

        # Handle hard vs soft subtitles
        subtitle_type = self.job.settings.get('subtitle_type', 'Soft Subtitles (Toggleable)')
        if subtitle_type == 'Hard Subtitles (Burned-in)':
            # NOTE: This only supports burning in the FIRST matched subtitle.
            # A more complex filter_complex graph would be needed for multiple.
            if not matching_subs: return []
            # Need to escape path for ffmpeg filter
            escaped_sub_path = str(matching_subs[0]).replace('\\', '/').replace(':', '\\:')
            return [
                ffmpeg_path, '-i', str(video_file.path),
                '-vf', f"subtitles='{escaped_sub_path}'",
                '-y', str(output_path)
            ]

        # Soft subtitles logic
        cmd = [ffmpeg_path, '-i', str(video_file.path)]
        for sub_path in matching_subs:
            cmd.extend(['-i', str(sub_path)])

        # Map all streams from original video and all new subtitle streams
        cmd.extend(['-map', '0', '-map', '1'])
        if len(matching_subs) > 1:
             for i in range(1, len(matching_subs)):
                 cmd.extend(['-map', f'{i+1}'])

        # Copy all streams, but specify subtitle codec
        cmd.extend(['-c', 'copy', '-c:s', 'mov_text'])

        # Add language metadata
        for i, lang in enumerate(languages):
            cmd.extend([f'-metadata:s:s:{i}', f'language={lang}'])

        # Set first subtitle as default if checked
        if self.job.settings.get('default_subtitle', False) and languages:
             cmd.extend(['-disposition:s:0', 'default'])

        cmd.extend(['-y', str(output_path)])
        return cmd

    def embed_subtitles(self):
        total_files = len(self.job.input_files)
        for i, video_file in enumerate(self.job.input_files):
            if self.is_cancelled:
                break

            self.status_updated.emit(f"({i+1}/{total_files}) Embedding subtitles in {video_file.filename}...")

            subtitle_files = self.job.settings.get('subtitle_files', [])
            matching_subs = [
                sub_path for sub_path in subtitle_files
                if video_file.path.stem.lower() in Path(sub_path).stem.lower() or
                   Path(sub_path).stem.lower() in video_file.path.stem.lower()
            ]

            if not matching_subs:
                self.status_updated.emit(f"No matching subtitles found for {video_file.filename}")
                continue

            duration = self._get_duration(video_file.path)
            if duration == 0:
                self.status_updated.emit(f"Could not get duration for {video_file.filename}. Progress will not be shown.")

            cmd = self._build_embed_subtitles_cmd(video_file, matching_subs)

            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, universal_newlines=True)
                time_regex = re.compile(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})")

                for line in iter(process.stderr.readline, ""):
                    if self.is_cancelled:
                        process.terminate()
                        break

                    match = time_regex.search(line)
                    if match and duration > 0:
                        elapsed_time = self._time_str_to_seconds(match.group(1))
                        progress = int((elapsed_time / duration) * 100)
                        overall_progress = int(((i + progress / 100) / total_files) * 100)
                        self.progress_updated.emit(overall_progress)

                process.wait()

                if process.returncode != 0 and not self.is_cancelled:
                    self.job_completed.emit(f"Failed to embed subtitles for {video_file.filename}", False)
                    return

            except Exception as e:
                self.job_completed.emit(f"Error processing {video_file.filename}: {str(e)}", False)
                return

        if not self.is_cancelled:
            self.progress_updated.emit(100)
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
            mode = "Preview completed" if self.job.settings.get('preview_mode',
                                                                 False) else f"Renamed {renamed_count} files"
            self.job_completed.emit(f"Bulk renaming completed! {mode}", True)

    def extract_season_episode(self, filename: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract season and episode numbers from filename"""
        patterns = [
            r'[Ss](\d{1,2})[Ee](\d{1,2})',  # S01E01
            r'(\d{1,2})x(\d{1,2})',  # 1x01
            r'Season\s*(\d{1,2}).*Episode\s*(\d{1,2})',  # Season 1 Episode 1
            r'(\d{1,2})\s*-\s*(\d{1,2})',  # 1-01
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
        template = settings.get('filename_template', '{name} - S{season:02d}E{episode:02d} - {title}{ext}')

        # Clean up names
        clean_name = re.sub(r'[<>:"/\\|?*]', '', show_name)
        clean_title = re.sub(r'[<>:"/\\|?*]', '', episode_title) if episode_title else ''
        year_match = re.search(r'\((\d{4})\)', clean_name)
        year = year_match.group(1) if year_match else ""

        try:
            return template.format(
                name=clean_name,
                season=season,
                episode=episode,
                title=clean_title,
                ext=extension,
                year=year
            )
        except:
            # Fallback format
            return f"{clean_name} - S{season:02d}E{episode:02d}{extension}"

    def cancel(self):
        self.is_cancelled = True
