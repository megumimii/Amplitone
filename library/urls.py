from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    # Playlists CRUD & membership
    path('playlists/', views.playlist_list_view, name='playlist_list'),
    path('playlists/create/', views.playlist_create_view, name='playlist_create'),
    path('playlists/<int:pk>/', views.playlist_detail_view, name='playlist_detail'),
    path('playlists/<int:pk>/edit/', views.playlist_update_view, name='playlist_update'),
    path('playlists/<int:pk>/delete/', views.playlist_delete_view, name='playlist_delete'),
    path('playlists/<int:pk>/add-track/', views.playlist_add_track_view, name='playlist_add_track'),
    path(
        'playlists/<int:pk>/remove-track/<int:track_pk>/',
        views.playlist_remove_track_view,
        name='playlist_remove_track',
    ),

    # Liked Songs & Recently Played
    path('liked/', views.liked_songs_view, name='liked_songs'),
    path('liked/toggle/<int:track_pk>/', views.toggle_like_view, name='toggle_like'),
    path('recent/', views.recently_played_view, name='recently_played'),
]

