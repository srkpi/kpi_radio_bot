import logging
import requests
from typing import Optional
from urllib.parse import quote_plus

def get_song_language(name: str) -> Optional[str]:
    url = "https://genius-song-language-api.vercel.app/search?q=" + quote_plus(name)
    res = requests.get(url)
    if res.status_code != 200:
        if res.status_code == 404:
            logging.info(f"GENIUS | Song not found: {name}")
        else:
            logging.error(f"GENIUS | Error: {res.status_code}. Response: {res.json()}")

        return None

    language: Optional[str] = res.json().get("language")

    logging.info(f"GENIUS | Song language: {language if language else 'not specified'}")

    return language
