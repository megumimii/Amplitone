from django.contrib import admin
from .models import LikedSong, Playlist, PlaylistTrack, RecentlyPlayed


class PlaylistTrackInline(admin.TabularInline):
    model = PlaylistTrack
    extra = 1


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_private', 'created_at')
    search_fields = ('name', 'owner__username')
    inlines = [PlaylistTrackInline]


@admin.register(LikedSong)
class LikedSongAdmin(admin.ModelAdmin):
    list_display = ('user', 'track', 'created_at')


@admin.register(RecentlyPlayed)
class RecentlyPlayedAdmin(admin.ModelAdmin):
    list_display = ('user', 'track', 'played_at')

