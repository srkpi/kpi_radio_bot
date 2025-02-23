import asyncio
from pathlib import Path
from typing import Optional
from yt_dlp import YoutubeDL


download_dir = Path("./music/downloads")
download_dir.mkdir(parents=True, exist_ok=True)
for file in download_dir.iterdir():
    file.unlink()

_queue = asyncio.Queue()
_active_downloads = set()


async def _process_queue():
    while True:
        video_id = await _queue.get()
        await download_song(video_id)
        _queue.task_done()


processing_task = asyncio.create_task(_process_queue())


def _get_song_download_path(video_id: str) -> Path:
    return download_dir / f"{video_id}.mp3"


def get_song_path(video_id: str) -> Optional[Path]:
    path = _get_song_download_path(video_id)
    return path if path.exists() and not is_downloading(video_id) else None


def is_downloaded(video_id: str) -> bool:
    return _get_song_download_path(video_id).exists() and not is_downloading(video_id)


def is_downloading(video_id: str) -> bool:
    return video_id in _active_downloads


async def download_song(video_id: str) -> Optional[Path]:
    if is_downloaded(video_id):
        return _get_song_download_path(video_id)

    if video_id in _active_downloads:
        return None  # Already being downloaded

    _active_downloads.add(video_id)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(_get_song_download_path(video_id).with_suffix(".%(ext)s")),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
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

    return _get_song_download_path(video_id) if is_downloaded(video_id) else None


async def add_to_download_queue(video_id: str):
    await _queue.put(video_id)


def delete_song(video_id: str):
    _get_song_download_path(video_id).unlink(missing_ok=True)
