"""
Forms for the Library app (Playlists).

Inherits from `StrictFileSecurityFormMixin` so any attempt to inject files
into non-file fields is strictly rejected. Uses `validate_image_file` to verify
genuine image file uploads.
"""

from django import forms
from core.validators import StrictFileSecurityFormMixin, validate_image_file
from .models import Playlist


class PlaylistForm(StrictFileSecurityFormMixin, forms.ModelForm):
    """Form for creating and updating a user Playlist with optional square cover art."""

    cover = forms.FileField(
        required=False,
        validators=[validate_image_file],
        widget=forms.FileInput(attrs={
            'accept': 'image/*,.jpg,.jpeg,.png,.webp',
            'data-preview-image': 'true',
            'id': 'id_playlist_cover',
        }),
        help_text="Square playlist artwork (JPG, PNG, or WEBP, max 5 MB).",
    )

    class Meta:
        model = Playlist
        fields = ('name', 'description', 'cover', 'is_private')
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Late Night Circuit'}),
            'description': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Notes on the mood or sequence...'}
            ),
        }

