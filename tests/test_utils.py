import os
from pathlib import Path
import tempfile
import pytest

from echomux.utils import process_paths


def test_process_paths_with_files():
    """
    Tests if the utility correctly processes a list of files.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some dummy files
        file1 = Path(tmpdir) / "video1.mp4"
        file1.touch()
        file2 = Path(tmpdir) / "video2.mkv"
        file2.touch()
        file3 = Path(tmpdir) / "document.txt"
        file3.touch()

        paths_to_process = [str(file1), str(file2), str(file3)]
        allowed_extensions = ['.mp4', '.mkv']

        result = process_paths(paths_to_process, allowed_extensions)

        assert len(result) == 2
        assert str(file1) in result
        assert str(file2) in result
        assert str(file3) not in result


def test_process_paths_with_directory():
    """
    Tests if the utility correctly processes a directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dummy files and subdirectories
        (Path(tmpdir) / "video1.mp4").touch()
        (Path(tmpdir) / "audio1.mp3").touch()
        subdir = Path(tmpdir) / "subdir"
        subdir.mkdir()
        (subdir / "video2.MP4").touch()  # Test case-insensitivity
        (subdir / "image.jpg").touch()

        result = process_paths([tmpdir], ['.mp4', '.mp3'])

        assert len(result) == 3
        assert str(Path(tmpdir) / "video1.mp4") in result
        assert str(Path(tmpdir) / "audio1.mp3") in result
        assert str(subdir / "video2.MP4") in result
        assert str(subdir / "image.jpg") not in result


def test_process_paths_mixed_content():
    """
    Tests a mix of files and directories as input.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir) / "media"
        dir_path.mkdir()
        (dir_path / "video.mkv").touch()

        file_path = Path(tmpdir) / "audio.flac"
        file_path.touch()

        paths_to_process = [str(dir_path), str(file_path)]
        allowed_extensions = ['.mkv', '.flac']

        result = process_paths(paths_to_process, allowed_extensions)
        assert len(result) == 2
        assert str(dir_path / "video.mkv") in result
        assert str(file_path) in result


def test_process_paths_avoids_duplicates():
    """
    Tests that duplicate files are not returned.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = Path(tmpdir) / "file.mp4"
        file1.touch()

        paths_to_process = [str(file1), str(file1)]
        result = process_paths(paths_to_process, ['.mp4'])
        assert len(result) == 1
        assert str(file1) in result


def test_process_paths_empty():
    """
    Tests the utility with an empty list of paths.
    """
    result = process_paths([], ['.mp4'])
    assert len(result) == 0


@pytest.mark.parametrize("filename, expected_season, expected_episode", [
    ("My.Show.S01E02.mkv", 1, 2),
    ("my show s01e02.mp4", 1, 2),
    ("Another.Show.1x05.avi", 1, 5),
    ("The.Series.2x12.mkv", 2, 12),
    ("Show Name - Season 3 Episode 4.mp4", 3, 4),
    ("Show.Name.S04E01.1080p.x265.mkv", 4, 1),
    ("S05E06 - Episode Title.mkv", 5, 6),
    ("Invalid.Filename.mkv", None, None),
    ("S01E.mp4", None, None),
    ("S01E999.mkv", 1, 999), # It should parse numbers, even if they are large
    ("series.10-11.mkv", 10, 11),
])
def test_extract_season_episode(filename, expected_season, expected_episode):
    """
    Tests the season and episode extraction logic from filenames.
    """
    from echomux.utils import extract_season_episode
    season, episode = extract_season_episode(filename)
    assert season == expected_season
    assert episode == expected_episode
