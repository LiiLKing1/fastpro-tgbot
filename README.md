# Media Downloader Telegram Bot

A modern, fast, and secure Telegram bot that downloads publicly accessible media from social platforms using `yt-dlp` and `aiogram`.

## Supported Platforms
- YouTube
- Instagram
- TikTok
- Facebook
- X / Twitter
- Vimeo
- SoundCloud
- Direct Media URLs

## Setup Instructions

### Prerequisites
- Python 3.12+
- FFmpeg installed and in your system PATH

### FFmpeg Installation
- **Windows:** Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/), extract it, and add the `bin` folder to your Environment Variables PATH.
- **Linux (Ubuntu/Debian):** `sudo apt update && sudo apt install ffmpeg`
- **macOS:** `brew install ffmpeg`

### Installation

1. **Clone the repository (or copy the files):**
   ```bash
   git clone <repo-url>
   cd Telegram-Bot
   ```

2. **Create a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   # Activate on Windows
   venv\Scripts\activate
   # Activate on Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   - Copy `.env.example` to `.env`
   - Open `.env` and configure your variables:
     - `BOT_TOKEN`: Get this from [@BotFather](https://t.me/BotFather) on Telegram.
     - `ADMIN_IDS`: Comma-separated list of Telegram User IDs for admin commands.
     - `DATABASE_URL`: SQLite connection string (default provided).
     - `TEMP_DIR`: Directory for temporary downloads.

### Running the Bot
```bash
python bot.py
```
