import yt_dlp
import asyncio
import os
import glob
from typing import Optional, Tuple
import imageio_ffmpeg

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

# Optional: path to a cookies file exported from browser (Netscape format)
# Export it via "Get cookies.txt LOCALLY" Chrome extension or similar.
COOKIES_FILE = "cookies.txt"

class DownloaderService:
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir

    def _base_opts(self) -> dict:
        opts = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'geo_bypass': True,
            'restrictfilenames': True,
            'socket_timeout': 30,
            'ffmpeg_location': FFMPEG_PATH,
        }
        # If cookies file exists, use it (helps with Instagram, TikTok, etc.)
        if os.path.exists(COOKIES_FILE):
            opts['cookiefile'] = COOKIES_FILE
        return opts

    def _get_opts(self, format_choice: str, file_path_prefix: str) -> dict:
        opts = self._base_opts()
        opts['outtmpl'] = f'{file_path_prefix}.%(ext)s'

        if format_choice == 'bestvideo':
            opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            opts['merge_output_format'] = 'mp4'
        elif format_choice == '720p':
            opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best'
            opts['merge_output_format'] = 'mp4'
        elif format_choice == '360p':
            opts['format'] = 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best'
            opts['merge_output_format'] = 'mp4'
        elif format_choice == 'audio':
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif format_choice == 'thumbnail':
            opts['skip_download'] = True
            opts['writethumbnail'] = True

        return opts

    def _find_downloaded_file(self, prefix: str, exts: list) -> Optional[str]:
        for ext in exts:
            path = f"{prefix}.{ext}"
            if os.path.exists(path):
                return path
        matches = glob.glob(f"{prefix}.*")
        if matches:
            return matches[0]
        return None

    async def extract_info(self, url: str) -> dict:
        def run():
            opts = self._base_opts()
            opts['extract_flat'] = True
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        return await asyncio.to_thread(run)

    async def download(self, url: str, format_choice: str, user_id: int) -> Tuple[Optional[str], str, str]:
        prefix = os.path.join(self.temp_dir, f"dl_{user_id}")

        # Clean up leftover files
        for old in glob.glob(f"{prefix}.*"):
            try:
                os.remove(old)
            except OSError:
                pass

        opts = self._get_opts(format_choice, prefix)

        def run():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info.get("title", "Unknown Title") if info else "Unknown Title"

        title = await asyncio.to_thread(run)

        if format_choice == 'audio':
            file_path = self._find_downloaded_file(prefix, ['mp3', 'm4a', 'ogg', 'wav'])
            media_type = 'audio'
        elif format_choice == 'thumbnail':
            file_path = self._find_downloaded_file(prefix, ['jpg', 'jpeg', 'png', 'webp'])
            media_type = 'thumbnail'
        else:
            file_path = self._find_downloaded_file(prefix, ['mp4', 'mkv', 'webm', 'mov'])
            media_type = 'video'

        return file_path, title, media_type
