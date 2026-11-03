"""
Views for the Catalog app (Albums & Tracks CRUD + Audio Play Recording).

Permissions:
- Standard Users can create their own Albums and Tracks (linked automatically to their
  own Artist profile), and edit/delete their own Albums and Tracks.
- The Administrator (`is_staff` / `is_superuser`) can manage Albums and Tracks across
  all Artist accounts.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.utils import get_or_create_user_artist
from core.utils import render_page
from library.models import LikedSong, Playlist, RecentlyPlayed
from .forms import AlbumForm, TrackForm
from .models import Album, Track


def _get_user_liked_ids(user):
    """Helper returning a set of Track IDs liked by the current user."""
    if not user.is_authenticated:
        return set()
    return set(LikedSong.objects.filter(user=user).values_list('track_id', flat=True))


def _can_manage_album(user, album):
    """Returns True if `user` is Admin or owns the Artist profile of `album`."""
    if not user.is_authenticated:
        return False
    return bool(user.is_staff or user.is_superuser or album.artist.user_id == user.id)


def _verify_album_permission(user, album):
    """Raises 403 PermissionDenied if `user` is neither Admin nor the album's owner."""
    if not _can_manage_album(user, album):
        raise PermissionDenied("You only have permission to modify your own albums and tracks.")


# ============================================================================
# ALBUM CRUD & LISTS (Manage vs. All Albums)
# ============================================================================

@login_required
def album_manage_list_view(request):
    """
    Manage Albums table view:
    Displays a table showing ONLY the user's own albums (or all if admin),
    with '+ New Album' button and per-row action buttons (View, Edit, + Track, Delete).
    """
    if request.user.is_staff or request.user.is_superuser:
        albums = (
            Album.objects.select_related('artist')
            .prefetch_related('tracks')
            .order_by('-release_date', '-created_at')
        )
    else:
        albums = (
            Album.objects.filter(artist__user=request.user)
            .select_related('artist')
            .prefetch_related('tracks')
            .order_by('-release_date', '-created_at')
        )

    return render_page(request, 'catalog/album_manage.html', {
        'albums': albums,
        'active_tab': 'my_albums',
    })


def album_all_view(request):
    """
    Collection / All Artists Albums view:
    Displays albums from all artists in the catalog within a visual artwork grid.
    """
    albums = (
        Album.objects.select_related('artist')
        .prefetch_related('tracks')
        .order_by('-release_date', 'title')
    )
    return render_page(request, 'catalog/album_all.html', {
        'albums': albums,
        'active_tab': 'all_albums',
    })



def album_detail_view(request, pk):
    """Displays an album's cover, metadata, and full tracklist."""
    album = get_object_or_404(
        Album.objects.select_related('artist').prefetch_related('tracks__album__artist'),
        pk=pk,
    )
    tracks = album.tracks.all()
    user_playlists = (
        Playlist.objects.filter(owner=request.user)
        if request.user.is_authenticated
        else Playlist.objects.none()
    )

    return render_page(request, 'catalog/album_detail.html', {
        'album': album,
        'tracks': tracks,
        'can_manage_album': _can_manage_album(request.user, album),
        'liked_track_ids': _get_user_liked_ids(request.user),
        'user_playlists': user_playlists,
    })


@login_required
@require_http_methods(["GET", "POST"])
def album_create_view(request):
    """Creates a new album (defaults to the logged-in user's Artist profile)."""
    user_artist = get_or_create_user_artist(request.user)
    initial = {}
    artist_id = request.GET.get('artist')
    if artist_id and artist_id.isdigit():
        initial['artist'] = int(artist_id)
    elif user_artist:
        initial['artist'] = user_artist.pk

    if request.method == 'POST':
        post_data = request.POST.copy()
        if not post_data.get('artist') and user_artist:
            post_data['artist'] = str(user_artist.pk)
        form = AlbumForm(post_data, request.FILES, user=request.user)
        if form.is_valid():
            album = form.save()
            messages.success(request, f"Album '{album.title}' created.")
            return redirect('catalog:album_detail', pk=album.pk)
    else:
        form = AlbumForm(initial=initial, user=request.user)

    return render_page(request, 'catalog/album_form.html', {
        'form': form,
        'is_edit': False,
    })


@login_required
@require_http_methods(["GET", "POST"])
def album_update_view(request, pk):
    """Updates an existing album's details or cover image (Owner or Admin only)."""
    album = get_object_or_404(Album.objects.select_related('artist'), pk=pk)
    _verify_album_permission(request.user, album)

    if request.method == 'POST':
        form = AlbumForm(request.POST, request.FILES, instance=album, user=request.user)
        if form.is_valid():
            album = form.save()
            messages.success(request, f"Album '{album.title}' updated.")
            return redirect('catalog:album_detail', pk=album.pk)
    else:
        form = AlbumForm(instance=album, user=request.user)

    return render_page(request, 'catalog/album_form.html', {
        'form': form,
        'album': album,
        'is_edit': True,
    })


@login_required
@require_http_methods(["GET", "POST"])
def album_delete_view(request, pk):
    """Displays a confirmation page and deletes an album on POST (Owner or Admin only)."""
    album = get_object_or_404(Album.objects.select_related('artist'), pk=pk)
    _verify_album_permission(request.user, album)

    if request.method == 'POST':
        title = album.title
        album.delete()
        messages.success(request, f"Album '{title}' deleted.")
        return redirect('catalog:album_list')

    return render_page(request, 'core/partials/confirm_delete.html', {
        'object_type': 'Album',
        'object_name': f"{album.title} — {album.artist.name}",
        'warning_note': (
            f"Deleting this album will also delete all {album.tracks.count()} track(s) "
            f"contained inside it."
        ),
        'confirm_url': reverse('catalog:album_delete', kwargs={'pk': album.pk}),
        'cancel_url': reverse('catalog:album_detail', kwargs={'pk': album.pk}),
    })


# ============================================================================
# TRACK CRUD & LISTS (Manage vs. All Tracks Overview)
# ============================================================================

@login_required
def track_manage_list_view(request):
    """
    Manage Tracks view:
    Displays only the logged-in user's OWN uploaded tracks in a table,
    with '+ Upload Track' button and row action buttons.
    """
    if request.user.is_staff or request.user.is_superuser:
        tracks = (
            Track.objects.select_related('album', 'album__artist')
            .order_by('album__title', 'track_number')
        )
    else:
        tracks = (
            Track.objects.filter(album__artist__user=request.user)
            .select_related('album', 'album__artist')
            .order_by('album__title', 'track_number')
        )

    user_playlists = (
        Playlist.objects.filter(owner=request.user)
        if request.user.is_authenticated
        else Playlist.objects.none()
    )

    return render_page(request, 'catalog/track_manage.html', {
        'tracks': tracks,
        'active_tab': 'my_tracks',
        'liked_track_ids': _get_user_liked_ids(request.user),
        'user_playlists': user_playlists,
    })


def track_all_view(request):
    """
    Overview / All Tracks view:
    Displays all tracks uploaded to the system across all artists.
    """
    tracks = (
        Track.objects.select_related('album', 'album__artist')
        .order_by('-plays_count', 'id')
    )
    user_playlists = (
        Playlist.objects.filter(owner=request.user)
        if request.user.is_authenticated
        else Playlist.objects.none()
    )

    return render_page(request, 'catalog/track_all.html', {
        'tracks': tracks,
        'active_tab': 'all_tracks',
        'liked_track_ids': _get_user_liked_ids(request.user),
        'user_playlists': user_playlists,
    })



@login_required
@require_http_methods(["GET", "POST"])
def track_create_view(request):
    """Creates a new track inside an album."""
    user_artist = get_or_create_user_artist(request.user)
    initial = {}
    album_id = request.GET.get('album')
    if album_id and album_id.isdigit():
        if request.user.is_staff or request.user.is_superuser:
            album_obj = Album.objects.filter(pk=int(album_id)).first()
        else:
            album_obj = Album.objects.filter(pk=int(album_id), artist=user_artist).first()
        if album_obj:
            initial['album'] = album_obj.pk

    if request.method == 'POST':
        form = TrackForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            track = form.save()
            messages.success(request, f"Track '{track.title}' added to '{track.album.title}'.")
            return redirect('catalog:album_detail', pk=track.album.pk)
    else:
        form = TrackForm(initial=initial, user=request.user)

    return render_page(request, 'catalog/track_form.html', {
        'form': form,
        'is_edit': False,
    })


@login_required
@require_http_methods(["GET", "POST"])
def track_update_view(request, pk):
    """Edits an existing track's details or audio file (Owner or Admin only)."""
    track = get_object_or_404(Track.objects.select_related('album', 'album__artist'), pk=pk)
    _verify_album_permission(request.user, track.album)

    if request.method == 'POST':
        form = TrackForm(request.POST, request.FILES, instance=track, user=request.user)
        if form.is_valid():
            track = form.save()
            messages.success(request, f"Track '{track.title}' updated.")
            return redirect('catalog:album_detail', pk=track.album.pk)
    else:
        form = TrackForm(instance=track, user=request.user)

    return render_page(request, 'catalog/track_form.html', {
        'form': form,
        'track': track,
        'is_edit': True,
    })


@login_required
@require_http_methods(["GET", "POST"])
def track_delete_view(request, pk):
    """Displays a confirmation page and deletes a track on POST (Owner or Admin only)."""
    track = get_object_or_404(Track.objects.select_related('album', 'album__artist'), pk=pk)
    _verify_album_permission(request.user, track.album)
    album_pk = track.album.pk

    if request.method == 'POST':
        title = track.title
        track.delete()
        messages.success(request, f"Track '{title}' deleted.")
        return redirect('catalog:album_detail', pk=album_pk)

    return render_page(request, 'core/partials/confirm_delete.html', {
        'object_type': 'Track',
        'object_name': f"{track.title} ({track.album.title})",
        'warning_note': "This track will be removed from its album and all user playlists.",
        'confirm_url': reverse('catalog:track_delete', kwargs={'pk': track.pk}),
        'cancel_url': reverse('catalog:album_detail', kwargs={'pk': album_pk}),
    })


@require_POST
def track_play_view(request, pk):
    """
    Lightweight POST endpoint called by the persistent bottom audio player when
    a track starts playing. Increments `plays_count` and logs `RecentlyPlayed`.
    """
    track = get_object_or_404(Track, pk=pk)
    Track.objects.filter(pk=track.pk).update(plays_count=F('plays_count') + 1)
    track.refresh_from_db(fields=['plays_count'])

    if request.user.is_authenticated:
        RecentlyPlayed.objects.update_or_create(
            user=request.user,
            track=track,
            defaults={'played_at': timezone.now()},
        )

    return JsonResponse({
        'status': 'ok',
        'track_id': track.pk,
        'plays_count': track.plays_count,
    })
