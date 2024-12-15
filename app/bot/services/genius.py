import logging
import aiohttp
from typing import Optional
from urllib.parse import quote_plus

from app.settings import settings

AIOHTTP_SESSION = None

async def get_song_language(name: str) -> Optional[str]:
    global AIOHTTP_SESSION
    if AIOHTTP_SESSION is None:
        AIOHTTP_SESSION = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {settings.GENIUS_API_TOKEN.get_secret_value()}"
            }
        )

    try:
        search_json = await _search(name)
        search_status = search_json["meta"]["status"]
        if search_status != 200:
            raise Exception(f"Genius search error. Status code: {search_status}")

        song = _get_song_section(search_json["response"]["hits"])
        song_id = song["id"]
        song_json = await _get_song_json(song_id)

        get_info_status = song_json["meta"]["status"]
        if get_info_status != 200:
            raise Exception(
                f"Genius get song info error. Status code: {get_info_status}. Song id: {song_id}"
            )

        language = song_json["response"]["song"].get("language")

        return language
    except Exception as ex:
        logging.exception(ex)
        return None


async def _search(name: str) -> dict:
    url = "https://api.genius.com/search?q=" + quote_plus(name)
    async with AIOHTTP_SESSION.get(url) as res:
        res.raise_for_status()
        return await res.json(content_type=None)


def _get_song_section(sections: dict) -> dict:
    for sec in sections:
        if sec["type"] == "song" and sec["result"]:
            return sec["result"]

    raise LookupError("type==song not found")


async def _get_song_json(id: int) -> str:
    url = f"https://api.genius.com/songs/{id}"
    async with AIOHTTP_SESSION.get(url) as res:
        res.raise_for_status()
        return await res.json(content_type=None)
