import re
import logging
from spotipy import Spotify, SpotifyClientCredentials
from app.settings import settings

def get_track_info(url: str):
    try:
        sp = Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=settings.SPOTIPY_CLIENT_ID.get_secret_value(),
                client_secret=settings.SPOTIPY_CLIENT_SECRET.get_secret_value(),
            )
        )
        track_info = sp.track(url)
    except Exception as ex:
        logging.exception("get track info", ex)
        return None

    return track_info
