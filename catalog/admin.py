from django.contrib import admin
from .models import Album, Track


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'release_date', 'created_at')
    list_filter = ('release_date', 'artist')
    search_fields = ('title', 'artist__name')


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'album', 'track_number', 'duration_seconds', 'plays_count')
    list_filter = ('album',)
    search_fields = ('title', 'album__title', 'album__artist__name')

