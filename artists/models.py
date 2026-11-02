"""
Models for the Artists app.

Requirement:
- Artist CRUD is reserved for Admins.
- Every Artist also has their own linked Django User account (`OneToOneField`).
"""

from django.conf import settings
from django.db import models
from core.validators import validate_image_file


class Artist(models.Model):
    """Represents a recording artist with a dedicated Django user account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='artist_profile',
        help_text="The dedicated user account owned by this artist.",
    )
    name = models.CharField(max_length=150, unique=True)
    bio = models.TextField(blank=True, help_text="Artist biography and editorial notes.")
    image = models.FileField(
        upload_to='artists/images/',
        blank=True,
        null=True,
        validators=[validate_image_file],
        help_text="Square portrait image (JPG, PNG, or WEBP, max 5 MB).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    @property
    def effective_image(self):
        """Returns the artist's portrait image, or falls back to their user profile picture."""
        if self.image:
            return self.image
        profile = getattr(self.user, 'user_profile', None)
        if profile and profile.avatar:
            return profile.avatar
        return None

    def __str__(self):
        return self.name

