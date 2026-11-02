"""
Storage cleanup signals for the Accounts app.

Ensures that when a `UserProfile` is deleted or its `avatar` is replaced,
the orphaned image file is physically removed from disk (`media/accounts/avatars/`).
"""

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import UserProfile


def _delete_file_from_storage(file_field):
    """Safely deletes a physical file from Django storage if it exists."""
    if file_field and file_field.name:
        storage = file_field.storage
        name = file_field.name
        if storage.exists(name):
            storage.delete(name)


@receiver(post_delete, sender=UserProfile)
def cleanup_user_profile_avatar_on_delete(sender, instance, **kwargs):
    """Deletes the user's avatar file from disk when the UserProfile is deleted."""
    _delete_file_from_storage(instance.avatar)


@receiver(pre_save, sender=UserProfile)
def cleanup_old_user_profile_avatar_on_update(sender, instance, **kwargs):
    """Deletes the old avatar file from disk when a user uploads a new profile picture."""
    if not instance.pk:
        return
    old_profile = UserProfile.objects.filter(pk=instance.pk).first()
    if old_profile and old_profile.avatar and old_profile.avatar != instance.avatar:
        _delete_file_from_storage(old_profile.avatar)

