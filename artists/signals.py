"""
Signals for the Artists app (Automatic Physical File Cleanup).

Ensures that when an Artist is deleted (or when their portrait is replaced),
the image file is cleanly removed from disk.
"""

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import Artist


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


@receiver(post_delete, sender=Artist)
def delete_artist_image_on_delete(sender, instance, **kwargs):
    """Deletes portrait image from disk when an Artist is deleted."""
    _delete_file_from_storage(instance.image)


@receiver(pre_save, sender=Artist)
def delete_old_artist_image_on_change(sender, instance, **kwargs):
    """Deletes old portrait image when an Artist is updated with a new photo."""
    if not instance.pk:
        return

    try:
        old_artist = Artist.objects.get(pk=instance.pk)
    except Artist.DoesNotExist:
        return

    if old_artist.image and old_artist.image != instance.image:
        _delete_file_from_storage(old_artist.image)

