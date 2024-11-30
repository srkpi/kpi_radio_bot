import re
import logging
import aiohttp
from typing import Optional, Tuple
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

AIOHTTP_SESSION = None
_RE_GENIUS_BRACKETS = re.compile(r" \([\w\d ]+\)")


async def search_lyrics(name: str) -> Optional[Tuple[str, str]]:
    global AIOHTTP_SESSION
    if AIOHTTP_SESSION is None:
        AIOHTTP_SESSION = aiohttp.ClientSession()

    try:
        search_json = await _search(name)
        song = _get_song_section(search_json["response"]["sections"])
        lyrics = await _get_lyrics(song["url"])
        title = _delete_translit_from_title(song["full_title"])
        return title, lyrics
    except Exception as ex:
        logging.exception(ex)
        return None


async def _search(name: str) -> dict:
    url = "https://genius.com/api/search/multi?q=" + quote_plus(name)
    async with AIOHTTP_SESSION.get(url) as res:
        res.raise_for_status()
        return await res.json(content_type=None)


def _get_song_section(sections: dict) -> dict:
    for sec in sections:
        if sec["type"] == "song" and sec["hits"]:
            return sec["hits"][0]["result"]
    raise LookupError("type==song not found")


def _delete_translit_from_title(title: str) -> str:
    return _RE_GENIUS_BRACKETS.sub("", title)


async def _get_lyrics(url: str) -> Optional[str]:
    async with AIOHTTP_SESSION.get(url) as res:
        res.raise_for_status()
        html = await res.text()

    soup = BeautifulSoup(html, "html.parser")
    lyrics = soup.find("div", id="lyrics-root")

    for child in list(lyrics.children):
        if "data-lyrics-container" not in child.attrs:
            child.decompose()

    for br in lyrics.find_all("br"):
        br.string = "\n"

    return lyrics.get_text()
