"""
Views for the Core app (Home & Unified Search).

Demonstrates cross-app queries across `artists`, `catalog`, and `library`.
"""

from django.db.models import Q

from artists.models import Artist
from catalog.models import Album, Track
from library.models import LikedSong, Playlist
from .utils import render_page


def _get_user_liked_ids(user):
    if not user.is_authenticated:
        return set()
    return set(LikedSong.objects.filter(user=user).values_list('track_id', flat=True))


def home_view(request):
    """
    Renders the main Amplitone discovery dashboard:
    - Editorial Hero ("Music that moves differently.")
    - "On repeat" 4-column Album grid
    - "For your frequency" / "Popular tracks" Track table
    """
    featured_albums = (
        Album.objects.select_related('artist')
        .prefetch_related('tracks')
        .all()[:4]
    )
    frequency_tracks = (
        Track.objects.select_related('album', 'album__artist')
        .order_by('-plays_count', 'id')[:10]
    )
    hero_track = frequency_tracks.first()
    user_playlists = (
        Playlist.objects.filter(owner=request.user)
        if request.user.is_authenticated
        else Playlist.objects.none()
    )

    return render_page(request, 'core/partials/home.html', {
        'featured_albums': featured_albums,
        'frequency_tracks': frequency_tracks,
        'hero_track': hero_track,
        'liked_track_ids': _get_user_liked_ids(request.user),
        'user_playlists': user_playlists,
    })


def search_view(request):
    """
    Searches Artists, Albums, and Tracks by name/title.
    Supports both debounced HTMX search from the navbar and direct URL visits.
    """
    query = request.GET.get('q', '').strip()

    if query:
        artists = Artist.objects.filter(
            Q(name__icontains=query) | Q(bio__icontains=query)
        ).prefetch_related('albums')[:12]

        albums = Album.objects.select_related('artist').filter(
            Q(title__icontains=query) | Q(artist__name__icontains=query)
        )[:12]

        tracks = Track.objects.select_related('album', 'album__artist').filter(
            Q(title__icontains=query)
            | Q(album__title__icontains=query)
            | Q(album__artist__name__icontains=query)
        )[:25]
    else:
        artists = Artist.objects.prefetch_related('albums')[:8]
        albums = Album.objects.select_related('artist')[:8]
        tracks = Track.objects.select_related('album', 'album__artist')[:15]

    user_playlists = (
        Playlist.objects.filter(owner=request.user)
        if request.user.is_authenticated
        else Playlist.objects.none()
    )

    return render_page(request, 'core/partials/search_results.html', {
        'query': query,
        'artists': artists,
        'albums': albums,
        'tracks': tracks,
        'liked_track_ids': _get_user_liked_ids(request.user),
        'user_playlists': user_playlists,
    })
