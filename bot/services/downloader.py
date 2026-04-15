import yt_dlp
import asyncio
import os
import glob
from typing import Optional, Tuple
import shutil
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

FFMPEG_PATH = shutil.which("ffmpeg") or "ffmpeg"
DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/135.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
}
INSTAGRAM_TRACKING_QUERY_KEYS = {
    'fbclid',
    'igsh',
    'igshid',
    'utm_campaign',
    'utm_content',
    'utm_medium',
    'utm_source',
    'utm_term',
}

# Optional: path to a cookies file exported from browser (Netscape format)
# Export it via "Get cookies.txt LOCALLY" Chrome extension or similar.
COOKIES_FILE = "cookies.txt"

class DownloaderService:
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir

    def _is_instagram_url(self, url: str) -> bool:
        return 'instagram.com' in (urlsplit(url).netloc or '').lower()

    def _normalize_url(self, url: str) -> str:
        cleaned_url = url.strip()
        parsed = urlsplit(cleaned_url)

        if not self._is_instagram_url(cleaned_url):
            return cleaned_url

        filtered_query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in INSTAGRAM_TRACKING_QUERY_KEYS
        ]
        normalized_path = parsed.path.rstrip('/') or parsed.path or '/'

        return urlunsplit((
            parsed.scheme,
            parsed.netloc,
            normalized_path,
            urlencode(filtered_query, doseq=True),
            '',
        ))

    def _base_opts(self, url: Optional[str] = None) -> dict:
        headers = DEFAULT_HEADERS.copy()
        if url and self._is_instagram_url(url):
            headers['Referer'] = 'https://www.instagram.com/'

        opts = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'geo_bypass': True,
            'restrictfilenames': True,
            'socket_timeout': 30,
            'retries': 3,
            'extractor_retries': 3,
            'fragment_retries': 3,
            'ffmpeg_location': FFMPEG_PATH,
            'http_headers': headers,
        }
        # If cookies file exists, use it (helps with Instagram, TikTok, etc.)
        if os.path.exists(COOKIES_FILE):
            opts['cookiefile'] = COOKIES_FILE
        return opts

    def _get_opts(self, format_choice: str, file_path_prefix: str, url: str) -> dict:
        opts = self._base_opts(url)
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

    def _pick_title(self, info: Optional[dict], fallback: str = "Unknown Title") -> str:
        if not info:
            return fallback

        title = info.get("title")
        if title:
            return title

        entries = info.get("entries") or []
        for entry in entries:
            if entry and entry.get("title"):
                return entry["title"]

        return fallback

    async def extract_info(self, url: str) -> dict:
        normalized_url = self._normalize_url(url)

        def run():
            attempts = (
                {},
                {'extract_flat': True},
            )
            last_error = None

            for extra_opts in attempts:
                try:
                    opts = self._base_opts(normalized_url)
                    opts.update(extra_opts)
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(normalized_url, download=False)
                        if info:
                            return info
                except Exception as exc:
                    last_error = exc

            if last_error:
                raise last_error
            return {}

        return await asyncio.to_thread(run)

    async def download(self, url: str, format_choice: str, user_id: int) -> Tuple[Optional[str], str, str]:
        normalized_url = self._normalize_url(url)
        prefix = os.path.join(self.temp_dir, f"dl_{user_id}")

        # Clean up leftover files
        for old in glob.glob(f"{prefix}.*"):
            try:
                os.remove(old)
            except OSError:
                pass

        opts = self._get_opts(format_choice, prefix, normalized_url)

        def run():
            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(normalized_url, download=True)
                except yt_dlp.utils.DownloadError:
                    if format_choice not in {'bestvideo', '720p', '360p'}:
                        raise

                    fallback_opts = self._get_opts('bestvideo', prefix, normalized_url)
                    fallback_opts['format'] = 'best'
                    fallback_opts.pop('merge_output_format', None)
                    with yt_dlp.YoutubeDL(fallback_opts) as fallback_ydl:
                        info = fallback_ydl.extract_info(normalized_url, download=True)

                return self._pick_title(info)

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
            if not file_path:
                file_path = self._find_downloaded_file(prefix, ['jpg', 'jpeg', 'png', 'webp'])
                if file_path:
                    media_type = 'thumbnail'

        return file_path, title, media_type
