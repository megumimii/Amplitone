"""
Root URL configuration for Amplitone.

Each modular app uses its own URL namespace (`app_name`) so templates and views
can reverse routes cleanly, e.g.:
- {% url 'core:home' %}
- {% url 'accounts:login' %}
- {% url 'artists:list' %}
- {% url 'catalog:album_list' %}
- {% url 'library:playlist_list' %}
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('artists/', include('artists.urls')),
    path('catalog/', include('catalog.urls')),
    path('library/', include('library.urls')),
]

# Serve uploaded media files (album covers, artist images, audio tracks) in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
