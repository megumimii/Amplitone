"""
Models for the Catalog app (Albums & Tracks).

Demonstrates One-to-Many ForeignKey relationships across modular Django apps:
- Artist (in `artists` app) -> Album (in `catalog` app) -> Track (in `catalog` app)
"""

from django.db import models
from core.validators import validate_audio_file, validate_image_file


class Album(models.Model):
    """Represents a music album or EP released by an Artist."""

    artist = models.ForeignKey(
        'artists.Artist',
        on_delete=models.CASCADE,
        related_name='albums',
    )
    title = models.CharField(max_length=200)
    cover = models.FileField(
        upload_to='albums/covers/',
        blank=True,
        null=True,
        validators=[validate_image_file],
        help_text="Album cover image (JPG, PNG, or WEBP, max 5 MB).",
    )
    release_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-release_date', 'title']

    def __str__(self):
        return f"{self.title} — {self.artist.name}"


class Track(models.Model):
    """Represents an individual playable audio track inside an Album."""

    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name='tracks',
    )
    title = models.CharField(max_length=200)
    audio_file = models.FileField(
        upload_to='tracks/audio/',
        blank=True,
        null=True,
        validators=[validate_audio_file],
        help_text="Audio file (MP3, WAV, OGG, FLAC, or M4A, max 25 MB).",
    )
    cover = models.FileField(
        upload_to='tracks/covers/',
        blank=True,
        null=True,
        validators=[validate_image_file],
        help_text="Optional track photo / single artwork (falls back to album cover if not set).",
    )
    duration_seconds = models.PositiveIntegerField(
        default=195,
        help_text="Duration in seconds (e.g. 225 for 3:45).",
    )
    track_number = models.PositiveIntegerField(default=1)
    plays_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['track_number', 'id']

    def __str__(self):
        return f"{self.track_number:02d}. {self.title} ({self.album.artist.name})"

    @property
    def formatted_duration(self):
        """Returns duration formatted as M:SS (e.g., 3:45)."""
        minutes, seconds = divmod(int(self.duration_seconds or 0), 60)
        return f"{minutes}:{seconds:02d}"

    @property
    def effective_cover(self):
        """Returns track-specific cover if uploaded, otherwise falls back to album cover."""
        if self.cover:
            return self.cover
        if self.album and self.album.cover:
            return self.album.cover
        return None

