from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    # Album routes: Manage (User's Own Albums) & All Albums (Collection / Explore)
    path('albums/', views.album_manage_list_view, name='album_list'),
    path('albums/all/', views.album_all_view, name='album_all'),
    path('albums/create/', views.album_create_view, name='album_create'),
    path('albums/<int:pk>/', views.album_detail_view, name='album_detail'),
    path('albums/<int:pk>/edit/', views.album_update_view, name='album_update'),
    path('albums/<int:pk>/delete/', views.album_delete_view, name='album_delete'),

    # Track routes: Manage (User's Own Tracks) & All Tracks (Overview / All Uploads)
    path('tracks/', views.track_manage_list_view, name='track_list'),
    path('tracks/all/', views.track_all_view, name='track_all'),
    path('tracks/create/', views.track_create_view, name='track_create'),
    path('tracks/<int:pk>/edit/', views.track_update_view, name='track_update'),
    path('tracks/<int:pk>/delete/', views.track_delete_view, name='track_delete'),
    path('tracks/<int:pk>/play/', views.track_play_view, name='track_play'),
]

