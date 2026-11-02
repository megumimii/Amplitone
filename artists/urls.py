from django.urls import path
from . import views

app_name = 'artists'

urlpatterns = [
    path('', views.artist_list_view, name='list'),
    path('manage/', views.artist_manage_view, name='manage'),
    path('create/', views.artist_create_view, name='create'),
    path('<int:pk>/', views.artist_detail_view, name='detail'),
    path('<int:pk>/edit/', views.artist_update_view, name='update'),
    path('<int:pk>/delete/', views.artist_delete_view, name='delete'),
]

