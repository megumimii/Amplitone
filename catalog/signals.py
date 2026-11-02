"""
Signals for the Catalog app (Automatic Physical File Cleanup).

Django by default does not delete files from disk when a model is deleted or updated.
These signals ensure that when a Track or Album is deleted (or when its cover/audio
file is replaced in an update form), the physical file is removed from disk to prevent
orphaned storage bloat.
"""

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import Album, Track


def _delete_file_from_storage(file_field):
    """Deletes a file from storage if it exists, without raising errors."""
    if not file_field:
        return
    try:
        storage = file_field.storage
        file_name = file_field.name
        if file_name and storage.exists(file_name):
            storage.delete(file_name)
    except Exception:
        pass


# ----------------------------------------------------------------------------
# TRACK SIGNALS
# ----------------------------------------------------------------------------

@receiver(post_delete, sender=Track)
def delete_track_files_on_delete(sender, instance, **kwargs):
    """Deletes audio file and custom cover from disk when a Track is deleted."""
    _delete_file_from_storage(instance.audio_file)
    _delete_file_from_storage(instance.cover)


@receiver(pre_save, sender=Track)
def delete_old_track_files_on_change(sender, instance, **kwargs):
    """Deletes old audio or cover file when a Track is updated with a new file."""
    if not instance.pk:
        return

    try:
        old_track = Track.objects.get(pk=instance.pk)
    except Track.DoesNotExist:
        return

    if old_track.audio_file and old_track.audio_file != instance.audio_file:
        _delete_file_from_storage(old_track.audio_file)

    if old_track.cover and old_track.cover != instance.cover:
        _delete_file_from_storage(old_track.cover)


# ----------------------------------------------------------------------------
# ALBUM SIGNALS
# ----------------------------------------------------------------------------

@receiver(post_delete, sender=Album)
def delete_album_cover_on_delete(sender, instance, **kwargs):
    """Deletes album cover file from disk when an Album is deleted."""
    _delete_file_from_storage(instance.cover)


@receiver(pre_save, sender=Album)
def delete_old_album_cover_on_change(sender, instance, **kwargs):
    """Deletes old cover file when an Album is updated with a new cover."""
    if not instance.pk:
        return

    try:
        old_album = Album.objects.get(pk=instance.pk)
    except Album.DoesNotExist:
        return

    if old_album.cover and old_album.cover != instance.cover:
        _delete_file_from_storage(old_album.cover)

