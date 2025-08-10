import asyncio
import time
from pathlib import Path
from typing import Optional

from yt_dlp import YoutubeDL


download_dir = Path("./music/downloads")
download_dir.mkdir(parents=True, exist_ok=True)

_queue = asyncio.Queue()
_active_downloads = set()


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
        video_id = await _queue.get()
        await download_song(video_id)
        _queue.task_done()


processing_task = asyncio.create_task(_process_queue())


def get_song_path(video_id: str) -> Optional[Path]:
    if is_downloading(video_id):
        return None

    files = list(download_dir.glob(f"{video_id}.*"))
    if files:
        return files[0]

    return None


def is_downloaded(video_id: str) -> bool:
    return bool(get_song_path(video_id))


def is_downloading(video_id: str) -> bool:
    return video_id in _active_downloads


async def download_song(video_id: str) -> Optional[Path]:
    downloaded_path = get_song_path(video_id)
    if downloaded_path:
        return downloaded_path

    if video_id in _active_downloads:
        return None  # Already being downloaded

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
        _active_downloads.remove(video_id)

    return get_song_path(video_id)


async def add_to_download_queue(video_id: str) -> None:
    await _queue.put(video_id)


def delete_song(video_id: str) -> None:
    path = get_song_path(video_id)
    if path:
        path.unlink(missing_ok=True)
