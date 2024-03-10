"""Utils functions for generate playlist."""
import logging

import spotipy

LOGGER = logging.getLogger(__name__)

def get_user_songs(sp: spotipy.Spotify) -> list[dict[str, str]]:
    """Return saved songs of current user."""
    # cache???
    results = sp.current_user_saved_tracks(limit=50)
    # total - total songs number
    # limit - limit of songs per 1 request
    # TODO: add pages in form
    # TODO: save all selected tracks
    songs = []
    # TODO: add some cache?
    for idx, item in enumerate(results['items']):
        track = item['track']
        songs.append(
            {
                "id": idx,
                "track_id": track.get("id"),
                "artist": ", ".join(map(lambda artist: artist.get("name"), track['artists'])),
                "name": track['name']
            }
        )
    return songs

def create_playlist_for_current_user(
    sp: spotipy.Spotify,
    name: str,
    songs: list[str],
) -> str:
    """Create playlist with given songs. Return id of created playlist."""
    user = sp.current_user()
    LOGGER.info("Creating new playlist for user %s with name %s.", user["id"], name)
    playlist = sp.user_playlist_create(
        user=user["id"],
        name=name,
        public=False,
        description="Playlist created with playlist-selection app.",
    )
    LOGGER.info("Adding %s songs to %s playlist of %s user.", len(songs), playlist["id"], user["id"])
    sp.playlist_add_items(playlist_id=playlist["id"], items=songs)
    return playlist["id"]
