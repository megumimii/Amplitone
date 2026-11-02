"""
Views for the Library app (Playlists CRUD, Liked Songs, Recently Played).

Security & Ownership Rules:
- All Library pages require authentication (`@login_required`).
- Only a playlist's `owner` may edit, delete, or add/remove tracks on that playlist.
  Attempting to mutate another user's playlist raises `403 PermissionDenied`.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from catalog.models import Track
from core.utils import consume_toast_messages, is_htmx, render_page
from .forms import PlaylistForm
from .models import LikedSong, Playlist, PlaylistTrack, RecentlyPlayed


def _verify_playlist_owner(playlist, user):
    """Raises 403 PermissionDenied if `user` is not the owner of `playlist`."""
    if playlist.owner_id != user.id:
        raise PermissionDenied("You do not have permission to modify this playlist.")


def _get_user_liked_ids(user):
    """Returns a set of Track IDs liked by `user`."""
    return set(LikedSong.objects.filter(user=user).values_list('track_id', flat=True))


# ============================================================================
# PLAYLIST CRUD
# ============================================================================

@login_required
def playlist_list_view(request):
    """Displays the logged-in user's playlists."""
    playlists = Playlist.objects.filter(owner=request.user).prefetch_related('tracks')
    return render_page(request, 'library/playlist_list.html', {
        'playlists': playlists,
    })


@login_required
def playlist_detail_view(request, pk):
    """Displays a playlist's metadata and ordered tracklist."""
    playlist = get_object_or_404(
        Playlist.objects.select_related('owner'),
        pk=pk,
    )
    if playlist.is_private and playlist.owner_id != request.user.id:
        raise PermissionDenied("This playlist is private.")

    entries = (
        PlaylistTrack.objects.filter(playlist=playlist)
        .select_related('track', 'track__album', 'track__album__artist')
    )
    tracks = [entry.track for entry in entries]
    all_catalog_tracks = Track.objects.select_related('album', 'album__artist').all()

    return render_page(request, 'library/playlist_detail.html', {
        'playlist': playlist,
        'tracks': tracks,
        'is_owner': playlist.owner_id == request.user.id,
        'liked_track_ids': _get_user_liked_ids(request.user),
        'user_playlists': Playlist.objects.filter(owner=request.user),
        'all_catalog_tracks': all_catalog_tracks,
    })


@login_required
@require_http_methods(["GET", "POST"])
def playlist_create_view(request):
    """Creates a new playlist owned by the logged-in user."""
    if request.method == 'POST':
        form = PlaylistForm(request.POST, request.FILES)
        if form.is_valid():
            playlist = form.save(commit=False)
            playlist.owner = request.user
            playlist.save()
            messages.success(request, f"Playlist '{playlist.name}' created.")
            return redirect('library:playlist_detail', pk=playlist.pk)
    else:
        form = PlaylistForm()

    return render_page(request, 'library/playlist_form.html', {
        'form': form,
        'is_edit': False,
    })


@login_required
@require_http_methods(["GET", "POST"])
def playlist_update_view(request, pk):
    """Updates a playlist's name, description, or privacy (Owner only)."""
    playlist = get_object_or_404(Playlist, pk=pk)
    _verify_playlist_owner(playlist, request.user)

    if request.method == 'POST':
        form = PlaylistForm(request.POST, request.FILES, instance=playlist)
        if form.is_valid():
            playlist = form.save()
            messages.success(request, f"Playlist '{playlist.name}' updated.")
            return redirect('library:playlist_detail', pk=playlist.pk)
    else:
        form = PlaylistForm(instance=playlist)

    return render_page(request, 'library/playlist_form.html', {
        'form': form,
        'playlist': playlist,
        'is_edit': True,
    })


@login_required
@require_http_methods(["GET", "POST"])
def playlist_delete_view(request, pk):
    """Displays a confirmation page and deletes a playlist on POST (Owner only)."""
    playlist = get_object_or_404(Playlist, pk=pk)
    _verify_playlist_owner(playlist, request.user)

    if request.method == 'POST':
        name = playlist.name
        playlist.delete()
        messages.success(request, f"Playlist '{name}' deleted.")
        return redirect('library:playlist_list')

    return render_page(request, 'core/partials/confirm_delete.html', {
        'object_type': 'Playlist',
        'object_name': playlist.name,
        'warning_note': (
            f"Deleting this playlist will remove the playlist container "
            f"({playlist.tracks.count()} track(s) will remain in the main catalog)."
        ),
        'confirm_url': reverse('library:playlist_delete', kwargs={'pk': playlist.pk}),
        'cancel_url': reverse('library:playlist_detail', kwargs={'pk': playlist.pk}),
    })


@login_required
@require_POST
def playlist_add_track_view(request, pk):
    """Adds a track to the specified playlist (Owner only)."""
    playlist = get_object_or_404(Playlist, pk=pk)
    _verify_playlist_owner(playlist, request.user)

    track_id = request.POST.get('track_id')
    track = get_object_or_404(Track, pk=track_id)

    next_pos = PlaylistTrack.objects.filter(playlist=playlist).count() + 1
    _, created = PlaylistTrack.objects.get_or_create(
        playlist=playlist,
        track=track,
        defaults={'position': next_pos},
    )

    if created:
        messages.success(request, f"Added '{track.title}' to '{playlist.name}'.")
    else:
        messages.info(request, f"'{track.title}' is already in '{playlist.name}'.")

    return redirect('library:playlist_detail', pk=playlist.pk)


@login_required
@require_POST
def playlist_remove_track_view(request, pk, track_pk):
    """Removes a track from the specified playlist (Owner only)."""
    playlist = get_object_or_404(Playlist, pk=pk)
    _verify_playlist_owner(playlist, request.user)

    track = get_object_or_404(Track, pk=track_pk)
    PlaylistTrack.objects.filter(playlist=playlist, track=track).delete()
    messages.success(request, f"Removed '{track.title}' from '{playlist.name}'.")

    return redirect('library:playlist_detail', pk=playlist.pk)


# ============================================================================
# LIKED SONGS & RECENTLY PLAYED
# ============================================================================

@login_required
def liked_songs_view(request):
    """Displays all tracks liked by the logged-in user."""
    likes = (
        LikedSong.objects.filter(user=request.user)
        .select_related('track', 'track__album', 'track__album__artist')
    )
    tracks = [like.track for like in likes]

    return render_page(request, 'library/liked_songs.html', {
        'tracks': tracks,
        'liked_track_ids': {t.pk for t in tracks},
        'user_playlists': Playlist.objects.filter(owner=request.user),
    })


@login_required
@require_POST
def toggle_like_view(request, track_pk):
    """
    Toggles the Like/Unlike state for a track.
    When called via HTMX, returns an updated heart button and an Out-of-Band
    sidebar badge counter (`#sidebar-liked-count`).
    """
    track = get_object_or_404(Track, pk=track_pk)
    existing = LikedSong.objects.filter(user=request.user, track=track).first()

    if existing:
        existing.delete()
        is_liked = False
        messages.info(request, f"Removed '{track.title}' from Liked Songs.")
    else:
        LikedSong.objects.create(user=request.user, track=track)
        is_liked = True
        messages.success(request, f"Added '{track.title}' to Liked Songs.")

    liked_count = LikedSong.objects.filter(user=request.user).count()

    if is_htmx(request):
        return render(request, 'library/partials/like_button.html', {
            'track': track,
            'is_liked': is_liked,
            'sidebar_liked_count': liked_count,
            'oob_update': True,
            'toast_items': consume_toast_messages(request),
        })

    return redirect('library:liked_songs')


@login_required
def recently_played_view(request):
    """Displays the user's recently played tracks in reverse chronological order."""
    recent_entries = (
        RecentlyPlayed.objects.filter(user=request.user)
        .select_related('track', 'track__album', 'track__album__artist')[:30]
    )
    tracks = [entry.track for entry in recent_entries]

    return render_page(request, 'library/recently_played.html', {
        'recent_entries': recent_entries,
        'tracks': tracks,
        'liked_track_ids': _get_user_liked_ids(request.user),
        'user_playlists': Playlist.objects.filter(owner=request.user),
    })

