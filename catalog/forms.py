"""
Forms for the Catalog app (Albums and Tracks).

Inherits from `StrictFileSecurityFormMixin` so any file uploaded into a non-file
field is rejected, and uses `validate_image_file` / `validate_audio_file` for
strict binary header verification.
"""

from django import forms
from django.db import models
from core.validators import (
    StrictFileSecurityFormMixin,
    extract_audio_duration,
    validate_audio_file,
    validate_image_file,
)
from .models import Album, Track


class AlbumForm(StrictFileSecurityFormMixin, forms.ModelForm):
    """
    Form for creating and updating an Album.
    For standard users, the `artist` field is omitted and automatically set
    to the user's own Artist profile. Only Administrators can select/assign
    the Artist field.
    """

    cover = forms.FileField(
        required=False,
        validators=[validate_image_file],
        widget=forms.FileInput(attrs={
            'accept': 'image/*,.jpg,.jpeg,.png,.webp',
            'data-preview-image': 'true',
            'id': 'id_album_cover',
        }),
        help_text="Square album cover (JPG, PNG, or WEBP, max 5 MB).",
    )
    release_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    class Meta:
        model = Album
        fields = ('title', 'artist', 'release_date', 'cover')

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Remove the artist field for standard users (Admin-only field)
        is_admin = bool(user and (user.is_staff or user.is_superuser))
        if not is_admin:
            self.fields.pop('artist', None)

    def save(self, commit=True):
        album = super().save(commit=False)
        # If artist field was removed (standard user), assign their own Artist profile
        if 'artist' not in self.fields and self.user:
            from accounts.utils import get_or_create_user_artist
            album.artist = get_or_create_user_artist(self.user)
        if commit:
            album.save()
        return album


class TrackForm(StrictFileSecurityFormMixin, forms.ModelForm):
    """Form for creating and editing a Track with auto sequence numbering and audio duration auto-derivation."""

    cover = forms.FileField(
        required=False,
        validators=[validate_image_file],
        widget=forms.FileInput(attrs={
            'accept': 'image/*,.jpg,.jpeg,.png,.webp',
            'data-preview-image': 'true',
            'id': 'id_track_cover',
        }),
        help_text="Optional track photo / single artwork (defaults to album cover if not set).",
    )
    audio_file = forms.FileField(
        required=False,
        validators=[validate_audio_file],
        widget=forms.FileInput(attrs={
            'accept': 'audio/*,.mp3,.wav,.ogg,.flac,.m4a',
            'data-preview-audio': 'true',
            'id': 'id_audio_file',
        }),
        help_text="Audio stream (MP3, WAV, OGG, FLAC, M4A). Duration is auto-derived from the file.",
    )
    duration_seconds = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_duration_seconds'}),
    )

    class Meta:
        model = Track
        fields = ('album', 'title', 'cover', 'audio_file', 'duration_seconds')

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Filter the album dropdown choices:
        # Standard users only see albums they own (through their linked artist profile).
        # Superusers / staff members see all albums.
        if user and not (user.is_staff or user.is_superuser):
            self.fields['album'].queryset = Album.objects.filter(artist__user=user)

    def clean(self):
        cleaned_data = super().clean()
        audio_file = cleaned_data.get('audio_file')

        # 1. Derive duration on server from the audio file if available
        if audio_file:
            server_duration = extract_audio_duration(audio_file)
            if server_duration:
                cleaned_data['duration_seconds'] = server_duration

        # 2. If server couldn't parse the stream (e.g. non-WAV without tag headers),
        # use client-detected duration if provided
        duration = cleaned_data.get('duration_seconds')
        if not duration or duration <= 0:
            cleaned_data['duration_seconds'] = self.instance.duration_seconds if self.instance.pk else 180

        return cleaned_data

    def save(self, commit=True):
        track = super().save(commit=False)
        if not track.pk or not track.track_number:
            if track.album:
                max_track_num = track.album.tracks.aggregate(
                    models.Max('track_number')
                )['track_number__max'] or 0
                track.track_number = max_track_num + 1
            else:
                track.track_number = 1
        if commit:
            track.save()
        return track
