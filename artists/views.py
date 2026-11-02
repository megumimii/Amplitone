"""
Views for the Artists app.

Permissions & Capabilities:
- Public / Standard Users can view the Artist Directory and Artist Detail pages
  (which display the artist's details, songs, albums, and playlists).
- The Artist Management CRUD page (`/artists/manage/`), create, update, and delete
  views are strictly reserved for the Administrator (`@admin_required`).
"""

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from accounts.decorators import admin_required
from catalog.models import Track
from core.utils import render_page
from library.models import LikedSong, Playlist
from .forms import ArtistCreateForm, ArtistUpdateForm
from .models import Artist


def _annotated_artists_queryset():
    """Returns artists with pre-counted albums, tracks, and playlists for table views."""
    return (
        Artist.objects.select_related('user')
        .prefetch_related('albums')
        .annotate(
            albums_total=Count('albums', distinct=True),
            tracks_total=Count('albums__tracks', distinct=True),
            playlists_total=Count('user__playlists', distinct=True),
        )
    )


def artist_list_view(request):
    """Displays the table of all artists with a 'View Artist' button (and Admin CRUD controls if Admin)."""
    artists = _annotated_artists_queryset()
    return render_page(request, 'artists/artist_list.html', {
        'artists': artists,
    })


def artist_detail_view(request, pk):
    """
    Displays an artist's full profile:
    1. Artist Details (bio, image, linked account)
    2. Their Albums
    3. Their Songs (Tracks)
    4. Their Playlists
    """
    artist = get_object_or_404(
        Artist.objects.select_related('user').prefetch_related('albums__tracks'),
        pk=pk,
    )
    albums = artist.albums.all()
    tracks = (
        Track.objects.filter(album__artist=artist)
        .select_related('album', 'album__artist')
        .order_by('-album__release_date', 'track_number')
    )

    # Show all playlists if Admin or the artist themselves; otherwise only public playlists
    is_admin_or_self = request.user.is_authenticated and (
        request.user.is_staff
        or request.user.is_superuser
        or request.user.id == artist.user_id
    )
    if is_admin_or_self:
        artist_playlists = Playlist.objects.filter(owner=artist.user).prefetch_related('tracks')
    else:
        artist_playlists = Playlist.objects.filter(
            owner=artist.user, is_private=False
        ).prefetch_related('tracks')

    liked_track_ids = (
        set(LikedSong.objects.filter(user=request.user).values_list('track_id', flat=True))
        if request.user.is_authenticated
        else set()
    )
    user_playlists = (
        Playlist.objects.filter(owner=request.user)
        if request.user.is_authenticated
        else Playlist.objects.none()
    )

    return render_page(request, 'artists/artist_detail.html', {
        'artist': artist,
        'albums': albums,
        'tracks': tracks,
        'artist_playlists': artist_playlists,
        'can_manage_artist_catalog': is_admin_or_self,
        'liked_track_ids': liked_track_ids,
        'user_playlists': user_playlists,
    })


@admin_required
def artist_manage_view(request):
    """Admin-only Artist CRUD table showing all artists, accounts, albums, tracks, and playlists."""
    artists = _annotated_artists_queryset()
    return render_page(request, 'artists/artist_manage.html', {
        'artists': artists,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def artist_create_view(request):
    """Admin-only view to create a new Artist and their linked User account."""
    if request.method == 'POST':
        form = ArtistCreateForm(request.POST, request.FILES)
        if form.is_valid():
            artist = form.save()
            messages.success(
                request,
                f"Artist '{artist.name}' and account '@{artist.user.username}' created.",
            )
            return redirect('artists:detail', pk=artist.pk)
    else:
        form = ArtistCreateForm()

    return render_page(request, 'artists/artist_form.html', {
        'form': form,
        'is_edit': False,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def artist_update_view(request, pk):
    """Admin-only view to update an Artist's bio, portrait, or account email."""
    artist = get_object_or_404(Artist.objects.select_related('user'), pk=pk)

    if request.method == 'POST':
        form = ArtistUpdateForm(request.POST, request.FILES, instance=artist)
        if form.is_valid():
            artist = form.save()
            messages.success(request, f"Artist '{artist.name}' updated.")
            return redirect('artists:detail', pk=artist.pk)
    else:
        form = ArtistUpdateForm(instance=artist)

    return render_page(request, 'artists/artist_form.html', {
        'form': form,
        'artist': artist,
        'is_edit': True,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def artist_delete_view(request, pk):
    """Admin-only view to confirm and delete an Artist and their linked User account."""
    artist = get_object_or_404(Artist.objects.select_related('user'), pk=pk)

    if request.method == 'POST':
        artist_name = artist.name
        linked_user = artist.user
        linked_user.delete()
        messages.success(request, f"Artist '{artist_name}' and linked account deleted.")
        return redirect('artists:manage')

    return render_page(request, 'core/partials/confirm_delete.html', {
        'object_type': 'Artist & Linked Account',
        'object_name': f"{artist.name} (@{artist.user.username})",
        'warning_note': (
            f"Deleting this artist will permanently remove their dedicated user account "
            f"(@{artist.user.username}) and {artist.albums.count()} associated album(s)."
        ),
        'confirm_url': reverse('artists:delete', kwargs={'pk': artist.pk}),
        'cancel_url': reverse('artists:detail', kwargs={'pk': artist.pk}),
    })
