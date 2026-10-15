import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Iterable, Optional, Sequence

PLAY_PLAYLIST_USAGE = (
    "Невірний формат команди! /play_playlist [макс. хвилин] {youtube_playlist_url}\n"
    "Наприклад: /play_playlist 30 https://music.youtube.com/playlist?list=..."
)

_NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")


class PlayPlaylistArgsError(ValueError):
    """Bad /play_playlist arguments. The message is safe to show to the admin."""


class StopReason(Enum):
    PLAYLIST_END = "playlist_end"
    MAX_TIME = "max_time"
    ETHER_END = "ether_end"


@dataclass(frozen=True)
class PlaylistTrack:
    video_id: str
    title: str
    duration: int  # seconds


@dataclass(frozen=True)
class PlannedTrack:
    track: PlaylistTrack
    expected_play_time: datetime


@dataclass(frozen=True)
class PlaylistPlan:
    tracks: list[PlannedTrack]
    stop_reason: StopReason
    # Cumulative time taken by the selected tracks, including switch delays
    total_seconds: int


def parse_play_playlist_args(args: Optional[str]) -> tuple[Optional[float], str]:
    """Parse "[max_minutes] url" into (max_minutes or None, url)."""
    tokens = (args or "").split()

    max_minutes: Optional[float] = None
    if len(tokens) == 2 and _NUMBER_PATTERN.fullmatch(tokens[0]):
        max_minutes = float(tokens[0].replace(",", "."))
        tokens = tokens[1:]

    if len(tokens) != 1 or _NUMBER_PATTERN.fullmatch(tokens[0]):
        raise PlayPlaylistArgsError(PLAY_PLAYLIST_USAGE)

    if max_minutes is not None and max_minutes <= 0:
        raise PlayPlaylistArgsError("Максимальний час має бути більшим за 0 хвилин.")

    return max_minutes, tokens[0]


def extract_playlist_id(url: str) -> Optional[str]:
    playlist_id = None
    if "list=" in url:
        playlist_id = url.split("list=")[-1].split("&")[0]
    elif "/playlist/" in url:
        playlist_id = url.split("/playlist/")[-1].split("?")[0]

    return playlist_id or None


def parse_playlist_tracks(
    raw_tracks: Iterable[dict[str, Any]],
    clean_title: Callable[[str], str] = lambda title: title,
) -> list[PlaylistTrack]:
    """Keep only the playlist entries that can actually be ordered."""
    tracks: list[PlaylistTrack] = []

    for raw in raw_tracks:
        video_id = raw.get("videoId")
        title = clean_title(raw.get("title") or "")

        try:
            duration = int(raw.get("duration_seconds") or 0)
        except (TypeError, ValueError):
            duration = 0

        if not video_id or not title or duration <= 0:
            continue

        if raw.get("isAvailable") is False:
            continue

        tracks.append(PlaylistTrack(video_id=video_id, title=title, duration=duration))

    return tracks


def estimate_queue_end(
    now: datetime,
    queued_durations: Sequence[int],
    playing_elapsed: int,
    switch_delay: int,
) -> datetime:
    """
    When the current queue is expected to be over (same estimate that is used for
    a regular order that is confirmed into a running ether).

    queued_durations: durations of all not yet played confirmed orders, including
    the one that is playing right now; playing_elapsed: seconds it already played.
    """
    remaining = sum(queued_durations) - playing_elapsed
    remaining += switch_delay * len(queued_durations)

    return now + timedelta(seconds=max(remaining, 0))


def plan_playlist(
    tracks: Sequence[PlaylistTrack],
    start: datetime,
    ether_end: datetime,
    max_seconds: Optional[float],
    switch_delay: int,
) -> PlaylistPlan:
    """
    Take tracks from the beginning of the playlist while they fit.

    Every track takes its duration plus the switch delay. Selection stops at the
    first track that would not fit, so the playlist order is never rearranged.
    A track does not fit when it would end after the ether is over, or when the
    cumulative time of the selected tracks would exceed max_seconds.
    """
    planned: list[PlannedTrack] = []
    consumed = 0
    cursor = start
    stop_reason = StopReason.PLAYLIST_END

    for track in tracks:
        if cursor + timedelta(seconds=track.duration) > ether_end:
            stop_reason = StopReason.ETHER_END
            break

        step = track.duration + switch_delay
        if max_seconds is not None and consumed + step > max_seconds:
            stop_reason = StopReason.MAX_TIME
            break

        planned.append(PlannedTrack(track=track, expected_play_time=cursor))
        consumed += step
        cursor += timedelta(seconds=step)

    return PlaylistPlan(
        tracks=planned, stop_reason=stop_reason, total_seconds=consumed
    )
