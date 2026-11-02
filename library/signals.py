"""
Storage cleanup signals for the Library app.

Ensures that when a `Playlist` is deleted or its `cover` artwork is replaced,
the orphaned image file is physically removed from disk (`media/playlists/covers/`).
"""

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Playlist


def _delete_file_from_storage(file_field):
    """Safely deletes a physical file from Django storage if it exists."""
    if file_field and file_field.name:
        storage = file_field.storage
        name = file_field.name
        if storage.exists(name):
            storage.delete(name)


@receiver(post_delete, sender=Playlist)
def cleanup_playlist_cover_on_delete(sender, instance, **kwargs):
    """Deletes the playlist cover file from disk when the Playlist is deleted."""
    _delete_file_from_storage(instance.cover)


@receiver(pre_save, sender=Playlist)
def cleanup_old_playlist_cover_on_update(sender, instance, **kwargs):
    """Deletes the old cover file from disk when a user replaces the playlist artwork."""
    if not instance.pk:
        return
    old_playlist = Playlist.objects.filter(pk=instance.pk).first()
    if old_playlist and old_playlist.cover and old_playlist.cover != instance.cover:
        _delete_file_from_storage(old_playlist.cover)

