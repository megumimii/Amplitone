"""
Models for the Accounts app.

Uses Django's built-in `django.contrib.auth.models.User` for authentication
and extends it with a 1-to-1 `UserProfile` model for storing user profile pictures.
"""

from django.conf import settings
from django.db import models
from core.validators import validate_image_file


class UserProfile(models.Model):
    """Stores user-level profile metadata, including their uploaded profile picture."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_profile',
    )
    avatar = models.FileField(
        upload_to='accounts/avatars/',
        blank=True,
        null=True,
        validators=[validate_image_file],
        help_text="Profile picture (JPG, PNG, or WEBP, max 5 MB).",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for @{self.user.username}"


