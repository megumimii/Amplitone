"""
Custom Template Context Processor for Amplitone.

Provides the Left Sidebar with live counts (Liked Songs count, Albums count)
and the logged-in user's Playlists on every request.
"""

from catalog.models import Album, Track
from library.models import LikedSong, Playlist


def _get_user_avatar_url(user):
    """Returns the URL of the user's uploaded profile picture (or artist portrait fallback)."""
    if not user or not user.is_authenticated:
        return None
    profile = getattr(user, 'user_profile', None)
    if profile and profile.avatar:
        return profile.avatar.url
    artist = getattr(user, 'artist_profile', None)
    if artist and artist.image:
        return artist.image.url
    return None


def sidebar_context(request):
    """
    Injects global authentication state (`is_user_authenticated`), user avatar URL,
    sidebar navigation metrics, and user playlists into all template contexts.
    """
    is_authenticated = bool(getattr(request, 'user', None) and request.user.is_authenticated)
    albums_count = Album.objects.count()
    tracks_count = Track.objects.count()

    if is_authenticated:
        liked_songs_count = LikedSong.objects.filter(user=request.user).count()
        user_playlists = Playlist.objects.filter(owner=request.user).order_by('-created_at')
        avatar_url = _get_user_avatar_url(request.user)
    else:
        liked_songs_count = 0
        user_playlists = Playlist.objects.none()
        avatar_url = None

    return {
        'is_user_authenticated': is_authenticated,
        'user_avatar_url': avatar_url,
        'sidebar_albums_count': albums_count,
        'sidebar_tracks_count': tracks_count,
        'sidebar_liked_count': liked_songs_count,
        'sidebar_playlists': user_playlists,
    }

