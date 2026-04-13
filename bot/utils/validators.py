import re
from urllib.parse import urlparse

def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def detect_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if 'youtube.com' in domain or 'youtu.be' in domain:
        return 'YouTube'
    elif 'instagram.com' in domain:
        return 'Instagram'
    elif 'tiktok.com' in domain:
        return 'TikTok'
    elif 'twitter.com' in domain or 'x.com' in domain:
        return 'X (Twitter)'
    elif 'facebook.com' in domain or 'fb.watch' in domain:
        return 'Facebook'
    elif 'vimeo.com' in domain:
        return 'Vimeo'
    elif 'soundcloud.com' in domain:
        return 'SoundCloud'
    else:
        return 'Direct Link / Other'
