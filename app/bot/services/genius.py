import logging
import requests
from typing import Optional
from urllib.parse import quote_plus

LANGUAGE_FLAGS = {
    "en": "🇬🇧",  # English (UK flag)
    "us": "🇺🇸",  # United States (US flag for English)
    "de": "🇩🇪",  # German
    "uk": "🇺🇦",  # Ukrainian
    "ru": "🇷🇺",  # Russian
    "fr": "🇫🇷",  # French
    "es": "🇪🇸",  # Spanish
    "it": "🇮🇹",  # Italian
    "ja": "🇯🇵",  # Japanese
    "cn": "🇨🇳",  # Chinese
    "ko": "🇰🇷",  # Korean
    "in": "🇮🇳",  # Hindi (Indian flag)
    "br": "🇧🇷",  # Portuguese (Brazil flag)
    "ar": "🇸🇦",  # Arabic (Saudi Arabia flag)
    "pt": "🇵🇹",  # Portuguese (Portugal flag)
    "nl": "🇳🇱",  # Dutch
    "pl": "🇵🇱",  # Polish
    "tr": "🇹🇷",  # Turkish
    "sv": "🇸🇪",  # Swedish
    "no": "🇳🇴",  # Norwegian
    "fi": "🇫🇮",  # Finnish
    "dk": "🇩🇰",  # Danish
    "gr": "🇬🇷",  # Greek
    "cz": "🇨🇿",  # Czech
    "hu": "🇭🇺",  # Hungarian
    "ro": "🇷🇴",  # Romanian
    "bg": "🇧🇬",  # Bulgarian
    "sk": "🇸🇰",  # Slovak
    "si": "🇸🇮",  # Slovenian
    "hr": "🇭🇷",  # Croatian
    "lt": "🇱🇹",  # Lithuanian
    "lv": "🇱🇻",  # Latvian
    "ee": "🇪🇪",  # Estonian
    "il": "🇮🇱",  # Hebrew (Israel flag)
    "th": "🇹🇭",  # Thai
    "vn": "🇻🇳",  # Vietnamese
    "ph": "🇵🇭",  # Filipino (Philippines flag)
    "romanization": "🇯🇵",  # Assume that romanized lyrics are Japanese
}


def get_song_language(name: str) -> Optional[str]:
    url = "https://genius-song-language-api.vercel.app/search?q=" + quote_plus(name)
    res = requests.get(url)
    if res.status_code != 200:
        if res.status_code == 404:
            return logging.info(f"GENIUS | Song: {name}. 404 Not Found")

        try:
            res_formatted = res.json()
        except Exception:
            res_formatted = res.text

        return logging.error(
            f"GENIUS | Song: {name}. Error: {res.status_code}. Response: {res_formatted}"
        )

    language: Optional[str] = res.json().get("language")

    logging.info(
        f"GENIUS | Song: {name}. Language: {language if language else 'not specified'}"
    )

    return language


def get_language_flag(language: str) -> str:
    return LANGUAGE_FLAGS.get(language, f"[{language}]")
