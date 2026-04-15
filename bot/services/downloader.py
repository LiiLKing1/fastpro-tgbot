import asyncio
import glob
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
from html.parser import HTMLParser
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import aiohttp
import yt_dlp

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
INSTAGRAM_COOKIE = os.getenv("INSTAGRAM_COOKIE", "").strip()
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=30)


class MetaTagParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta: Dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != 'meta':
            return

        attributes = {}
        for key, value in attrs:
            if key and value:
                attributes[key.lower()] = value

        meta_key = (attributes.get('property') or attributes.get('name') or '').lower()
        content = attributes.get('content')
        if meta_key and content and meta_key not in self.meta:
            self.meta[meta_key] = html.unescape(content)


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

    def _build_headers(self, url: Optional[str] = None) -> dict:
        headers = DEFAULT_HEADERS.copy()
        if url and self._is_instagram_url(url):
            headers['Referer'] = 'https://www.instagram.com/'
            if INSTAGRAM_COOKIE:
                headers['Cookie'] = INSTAGRAM_COOKIE
        return headers

    def _base_opts(self, url: Optional[str] = None) -> dict:
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
            'http_headers': self._build_headers(url),
        }
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

    def _instagram_candidate_urls(self, url: str) -> list[str]:
        parsed = urlsplit(url)
        base_path = parsed.path.rstrip('/')
        if not base_path:
            return [url]

        base_url = f"{parsed.scheme}://{parsed.netloc}{base_path}/"
        return [
            f"{base_url}embed/captioned/",
            f"{base_url}embed/",
            base_url,
        ]

    def _decode_json_string(self, value: str) -> str:
        try:
            return json.loads(f'"{value}"')
        except json.JSONDecodeError:
            return html.unescape(value.replace('\\/', '/'))

    def _extract_json_string(self, page_html: str, key: str) -> Optional[str]:
        match = re.search(rf'"{key}"\s*:\s*"([^"]+)"', page_html)
        if match:
            return self._decode_json_string(match.group(1))
        return None

    def _extract_html_title(self, page_html: str) -> Optional[str]:
        match = re.search(r'<title>(.*?)</title>', page_html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        title = html.unescape(match.group(1)).strip()
        return ' '.join(title.split()) if title else None

    def _extract_instagram_page_info(self, page_html: str) -> Optional[dict]:
        parser = MetaTagParser()
        parser.feed(page_html)
        meta = parser.meta

        video_url = meta.get('og:video:secure_url') or meta.get('og:video')
        image_url = meta.get('og:image:secure_url') or meta.get('og:image')

        if not video_url:
            for key in ('video_url', 'contentUrl'):
                video_url = self._extract_json_string(page_html, key)
                if video_url:
                    break

        if not image_url:
            for key in ('display_url', 'image_url', 'thumbnail_url', 'thumbnail_src', 'thumbnailUrl'):
                image_url = self._extract_json_string(page_html, key)
                if image_url:
                    break

        title = (
            meta.get('og:title')
            or meta.get('twitter:title')
            or self._extract_json_string(page_html, 'caption')
            or self._extract_html_title(page_html)
            or 'Instagram'
        )

        if not video_url and not image_url:
            return None

        return {
            'title': title,
            'video_url': video_url,
            'image_url': image_url,
        }

    async def _fetch_instagram_page_info_with_session(
        self,
        session: aiohttp.ClientSession,
        url: str,
    ) -> Optional[dict]:
        for candidate_url in self._instagram_candidate_urls(url):
            try:
                async with session.get(candidate_url, allow_redirects=True) as response:
                    if response.status >= 400:
                        continue
                    page_html = await response.text(errors='ignore')
            except (aiohttp.ClientError, asyncio.TimeoutError):
                continue

            page_info = self._extract_instagram_page_info(page_html)
            if page_info:
                return page_info

        return None

    async def _fetch_instagram_page_info(self, url: str) -> Optional[dict]:
        async with aiohttp.ClientSession(
            headers=self._build_headers(url),
            timeout=REQUEST_TIMEOUT,
        ) as session:
            return await self._fetch_instagram_page_info_with_session(session, url)

    def _guess_extension(self, media_url: str, content_type: str, media_type: str) -> str:
        url_ext = os.path.splitext(urlsplit(media_url).path)[1].lower().lstrip('.')
        if url_ext:
            if url_ext == 'jpe':
                return 'jpg'
            return url_ext

        mime = content_type.split(';', 1)[0].strip().lower()
        guessed_ext = mimetypes.guess_extension(mime, strict=False) or ''
        guessed_ext = guessed_ext.lstrip('.')
        if guessed_ext == 'jpe':
            guessed_ext = 'jpg'

        if guessed_ext:
            return guessed_ext

        return 'mp4' if media_type == 'video' else 'jpg'

    async def _download_remote_file(
        self,
        session: aiohttp.ClientSession,
        media_url: str,
        prefix: str,
        media_type: str,
    ) -> str:
        async with session.get(media_url, allow_redirects=True) as response:
            response.raise_for_status()
            ext = self._guess_extension(media_url, response.headers.get('Content-Type', ''), media_type)
            file_path = f"{prefix}.{ext}"

            with open(file_path, 'wb') as file_obj:
                async for chunk in response.content.iter_chunked(64 * 1024):
                    file_obj.write(chunk)

        return file_path

    def _convert_video_to_audio(self, input_path: str, prefix: str) -> str:
        output_path = f"{prefix}.mp3"
        if os.path.exists(output_path):
            os.remove(output_path)

        subprocess.run(
            [
                FFMPEG_PATH,
                '-y',
                '-loglevel',
                'error',
                '-i',
                input_path,
                '-vn',
                '-acodec',
                'libmp3lame',
                '-q:a',
                '2',
                output_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return output_path

    async def _download_instagram_fallback(
        self,
        url: str,
        format_choice: str,
        prefix: str,
    ) -> Tuple[Optional[str], str, str]:
        async with aiohttp.ClientSession(
            headers=self._build_headers(url),
            timeout=REQUEST_TIMEOUT,
        ) as session:
            page_info = await self._fetch_instagram_page_info_with_session(session, url)
            if not page_info:
                raise RuntimeError('Instagram public fallback failed')

            title = page_info['title']

            if format_choice == 'thumbnail':
                image_url = page_info.get('image_url')
                if not image_url:
                    raise RuntimeError('Instagram thumbnail fallback failed')
                file_path = await self._download_remote_file(session, image_url, prefix, 'thumbnail')
                return file_path, title, 'thumbnail'

            if format_choice == 'audio':
                video_url = page_info.get('video_url')
                if not video_url:
                    raise RuntimeError('Instagram audio fallback failed')
                video_path = await self._download_remote_file(session, video_url, prefix, 'video')
                try:
                    audio_path = await asyncio.to_thread(self._convert_video_to_audio, video_path, prefix)
                finally:
                    if os.path.exists(video_path):
                        os.remove(video_path)
                return audio_path, title, 'audio'

            video_url = page_info.get('video_url')
            image_url = page_info.get('image_url')
            media_url = video_url or image_url
            media_type = 'video' if video_url else 'thumbnail'
            if not media_url:
                raise RuntimeError('Instagram media fallback failed')

            file_path = await self._download_remote_file(session, media_url, prefix, media_type)
            return file_path, title, media_type

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

        try:
            return await asyncio.to_thread(run)
        except Exception:
            if self._is_instagram_url(normalized_url):
                page_info = await self._fetch_instagram_page_info(normalized_url)
                if page_info:
                    return {'title': page_info['title']}
            raise

    async def download(self, url: str, format_choice: str, user_id: int) -> Tuple[Optional[str], str, str]:
        normalized_url = self._normalize_url(url)
        prefix = os.path.join(self.temp_dir, f"dl_{user_id}")

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

        try:
            title = await asyncio.to_thread(run)
        except Exception:
            if not self._is_instagram_url(normalized_url):
                raise
            return await self._download_instagram_fallback(normalized_url, format_choice, prefix)

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
