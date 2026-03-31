import asyncio
import hashlib
import time
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from yt_dlp import YoutubeDL

if TYPE_CHECKING:
    from aiogram import Bot


download_dir = Path("./music/downloads")
download_dir.mkdir(parents=True, exist_ok=True)

_queue = asyncio.Queue()
_active_downloads: set[str] = set()
_bot_instance: Optional["Bot"] = None


def set_bot_instance(bot: "Bot") -> None:
    """Set the bot instance for Telegram file downloads."""
    global _bot_instance
    _bot_instance = bot


def get_telegram_file_key(file_id: str) -> str:
    """Generate a short, filesystem-safe cache key from a Telegram file_id."""
    return "tg_" + hashlib.md5(file_id.encode()).hexdigest()


def delete_old_songs(delta: int) -> None:
    cutoff = time.time() - delta
    for file in download_dir.iterdir():
        if file.is_file():
            try:
                ctime = file.stat().st_ctime
                if ctime < cutoff:
                    file.unlink(missing_ok=True)
            except Exception as e:
                print(f"Error deleting {file}: {e}")


delete_old_songs(48 * 3600)


async def _process_queue() -> None:
    while True:
        item = await _queue.get()
        try:
            if isinstance(item, dict):
                if item.get("type") == "telegram":
                    await download_telegram_file(item["file_id"])
            else:
                await download_song(item)
        except Exception as e:
            print(f"Queue processing error: {e}")
        finally:
            _queue.task_done()


processing_task = asyncio.create_task(_process_queue())


def get_song_path(key: str) -> Optional[Path]:
    """Return cached file path for a video_id or telegram file key, or None."""
    if is_downloading(key):
        return None

    files = list(download_dir.glob(f"{key}.*"))
    if files:
        return files[0]

    return None


def is_downloaded(key: str) -> bool:
    return bool(get_song_path(key))


def is_downloading(key: str) -> bool:
    return key in _active_downloads


async def download_song(video_id: str) -> Optional[Path]:
    """Download a YouTube song by video_id."""
    downloaded_path = get_song_path(video_id)
    if downloaded_path:
        return downloaded_path

    if video_id in _active_downloads:
        return None

    _active_downloads.add(video_id)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str((download_dir / video_id).with_suffix(".%(ext)s")),
    }

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: YoutubeDL(ydl_opts).download(
                [f"https://www.youtube.com/watch?v={video_id}"]
            ),
        )
    except Exception as e:
        print(f"Error downloading {video_id}: {e}")
    finally:
        _active_downloads.discard(video_id)

    return get_song_path(video_id)


async def download_telegram_file(file_id: str) -> Optional[Path]:
    """Download a file from Telegram using its file_id."""
    key = get_telegram_file_key(file_id)

    existing = get_song_path(key)
    if existing:
        return existing

    if key in _active_downloads:
        return None

    if _bot_instance is None:
        print("Bot instance not set — cannot download Telegram file")
        return None

    _active_downloads.add(key)
    try:
        file = await _bot_instance.get_file(file_id)
        suffix = Path(file.file_path).suffix if file.file_path else ".oga"
        if not suffix:
            suffix = ".oga"
        output_path = download_dir / f"{key}{suffix}"
        await _bot_instance.download_file(file.file_path, destination=output_path)
        print(f"Downloaded Telegram file {file_id} → {output_path}")
        return output_path
    except Exception as e:
        print(f"Error downloading Telegram file {file_id}: {e}")
        return None
    finally:
        _active_downloads.discard(key)


async def add_to_download_queue(video_id: str) -> None:
    await _queue.put(video_id)


async def add_telegram_to_download_queue(file_id: str) -> None:
    await _queue.put({"type": "telegram", "file_id": file_id})


def delete_song(video_id: str) -> None:
    path = get_song_path(video_id)
    if path:
        path.unlink(missing_ok=True)
