"""
Models for the Library app (Playlists, Liked Songs, Recently Played).

Demonstrates:
- ManyToManyField with an explicit `through` model (`PlaylistTrack`)
- Ownership relationships (`owner` ForeignKey to User)
- Unique constraints (`unique_together`) to prevent duplicate likes or playlist entries
"""

from django.conf import settings
from django.db import models
from core.validators import validate_image_file


class Playlist(models.Model):
    """A user-curated collection of tracks. Only the owner may edit or delete it."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='playlists',
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    cover = models.FileField(
        upload_to='playlists/covers/',
        blank=True,
        null=True,
        validators=[validate_image_file],
        help_text="Square playlist artwork (JPG, PNG, or WEBP, max 5 MB).",
    )
    is_private = models.BooleanField(default=False)
    tracks = models.ManyToManyField(
        'catalog.Track',
        through='PlaylistTrack',
        related_name='playlists',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (by {self.owner.username})"


class PlaylistTrack(models.Model):
    """Through model storing the order and timestamp of tracks inside a Playlist."""

    playlist = models.ForeignKey(
        Playlist,
        on_delete=models.CASCADE,
        related_name='playlist_tracks',
    )
    track = models.ForeignKey(
        'catalog.Track',
        on_delete=models.CASCADE,
        related_name='playlist_entries',
    )
    position = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position', 'added_at']
        unique_together = ('playlist', 'track')

    def __str__(self):
        return f"{self.playlist.name} -> {self.track.title}"


class LikedSong(models.Model):
    """Stores tracks liked (hearted) by a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='liked_songs',
    )
    track = models.ForeignKey(
        'catalog.Track',
        on_delete=models.CASCADE,
        related_name='likes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'track')

    def __str__(self):
        return f"{self.user.username} likes {self.track.title}"


class RecentlyPlayed(models.Model):
    """Records the most recent playback timestamp per user and track."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recently_played',
    )
    track = models.ForeignKey(
        'catalog.Track',
        on_delete=models.CASCADE,
        related_name='recent_plays',
    )
    played_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-played_at']
        unique_together = ('user', 'track')

    def __str__(self):
        return f"{self.user.username} played {self.track.title}"

