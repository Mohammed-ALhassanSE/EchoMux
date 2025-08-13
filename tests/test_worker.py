import unittest
from pathlib import Path

from echomux.worker import ProcessingJob, FFmpegWorker, MediaFile

class TestFFmpegWorker(unittest.TestCase):
    def test_build_extract_command_aac(self):
        # Setup
        input_file = MediaFile(path=Path("/test/video.mkv"), filename="video.mkv")
        job = ProcessingJob(
            input_files=[input_file],
            output_directory=Path("/test/output"),
            job_type='extract',
            settings={'format': 'aac'}
        )
        worker = FFmpegWorker(job)

        # Action
        command = worker.build_extract_audio_cmd(input_file)

        # Assert
        expected_command = [
            'ffmpeg', '-i', '/test/video.mkv', '-vn', '-acodec', 'aac',
            '-y', '/test/output/video.aac'
        ]
        self.assertEqual(command, expected_command)

    def test_build_extract_command_mp3(self):
        # Setup
        input_file = MediaFile(path=Path("/test/video.mp4"), filename="video.mp4")
        job = ProcessingJob(
            input_files=[input_file],
            output_directory=Path("/test/output"),
            job_type='extract',
            settings={'format': 'mp3'}
        )
        worker = FFmpegWorker(job)

        # Action
        command = worker.build_extract_audio_cmd(input_file)

        # Assert
        expected_command = [
            'ffmpeg', '-i', '/test/video.mp4', '-vn', '-acodec', 'libmp3lame',
            '-y', '/test/output/video.mp3'
        ]
        self.assertEqual(command, expected_command)

    def test_build_merge_command_preserve(self):
        # Setup
        video_file = MediaFile(path=Path("/test/video.mkv"), filename="video.mkv")
        audio_files = ['/test/audio1.aac', '/test/audio2.mp3']
        languages = ['eng', 'ger']
        job = ProcessingJob(
            input_files=[video_file],
            output_directory=Path("/test/output"),
            job_type='merge',
            settings={'preserve_original': True}
        )
        worker = FFmpegWorker(job)

        # Action
        command = worker.build_merge_audio_cmd(video_file, audio_files, languages)

        # Assert
        expected_command = [
            'ffmpeg', '-i', '/test/video.mkv', '-i', '/test/audio1.aac', '-i', '/test/audio2.mp3',
            '-map', '0', '-map', '-0:a',
            '-map', '1:a', '-map', '2:a',
            '-metadata:s:a:0', 'language=eng', '-metadata:s:a:1', 'language=ger',
            '-c', 'copy', '-y', '/test/output/video_merged.mkv'
        ]
        self.assertEqual(command, expected_command)

    def test_build_merge_command_no_preserve(self):
        # Setup
        video_file = MediaFile(path=Path("/test/video.mkv"), filename="video.mkv")
        audio_files = ['/test/audio1.aac']
        languages = ['jpn']
        job = ProcessingJob(
            input_files=[video_file],
            output_directory=Path("/test/output"),
            job_type='merge',
            settings={'preserve_original': False}
        )
        worker = FFmpegWorker(job)

        # Action
        command = worker.build_merge_audio_cmd(video_file, audio_files, languages)

        # Assert
        expected_command = [
            'ffmpeg', '-i', '/test/video.mkv', '-i', '/test/audio1.aac',
            '-map', '0:v', '-map', '0:s?',
            '-map', '1:a',
            '-metadata:s:a:0', 'language=jpn',
            '-c', 'copy', '-y', '/test/output/video_merged.mkv'
        ]
        self.assertEqual(command, expected_command)

    def test_build_embed_command_soft(self):
        # Setup
        video_file = MediaFile(path=Path("/test/video.mkv"), filename="video.mkv")
        subtitle_files = ['/test/sub1.srt', '/test/sub2.ass']
        languages = ['eng', 'fre']
        job = ProcessingJob(
            input_files=[video_file],
            output_directory=Path("/test/output"),
            job_type='embed',
            settings={
                'subtitle_type': 'Soft Subtitles (Toggleable)',
                'default_subtitle': True
            }
        )
        worker = FFmpegWorker(job)

        # Action
        command = worker.build_embed_subtitles_cmd(video_file, subtitle_files, languages)

        # Assert
        expected_command = [
            'ffmpeg', '-i', '/test/video.mkv', '-i', '/test/sub1.srt', '-i', '/test/sub2.ass',
            '-map', '0', '-map', '1', '-map', '2',
            '-c', 'copy', '-c:s', 'mov_text',
            '-metadata:s:s:0', 'language=eng', '-metadata:s:s:1', 'language=fre',
            '-disposition:s:0', 'default',
            '-y', '/test/output/video_subtitled.mkv'
        ]
        self.assertEqual(command, expected_command)

    def test_build_embed_command_hard(self):
        # Setup
        video_file = MediaFile(path=Path("/test/video.mkv"), filename="video.mkv")
        subtitle_files = ['/test/sub1.srt']
        languages = ['eng']
        job = ProcessingJob(
            input_files=[video_file],
            output_directory=Path("/test/output"),
            job_type='embed',
            settings={
                'subtitle_type': 'Hard Subtitles (Burned-in)',
                'default_subtitle': False
            }
        )
        worker = FFmpegWorker(job)

        # Action
        command = worker.build_embed_subtitles_cmd(video_file, subtitle_files, languages)

        # Assert
        expected_command = [
            'ffmpeg', '-i', '/test/video.mkv', '-vf', "subtitles='/test/sub1.srt'",
            '-y', '/test/output/video_subtitled.mkv'
        ]
        self.assertEqual(command, expected_command)

if __name__ == '__main__':
    unittest.main()
