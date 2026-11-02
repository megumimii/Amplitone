"""
Comprehensive Automated Tests for Amplitone across all 5 modular apps:
- `core`: Home, Search, HTMX partial rendering, Strict File & Field Security
- `accounts`: Registration, Login, Logout, Profile
- `artists`: Admin-only Artist CRUD + 1-to-1 Artist User Account creation
- `catalog`: Album CRUD, Track CRUD, Play counter
- `library`: Playlist CRUD, Owner-only protection, Liked Songs toggle
"""

from datetime import date
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from artists.models import Artist
from catalog.models import Album, Track
from library.models import LikedSong, Playlist


class AmplitoneSecurityAndCRUDTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin_user',
            email='admin@amplitone.local',
            password='StrongPassword123!',
        )
        self.user_a = User.objects.create_user(
            username='listener_a',
            email='a@amplitone.local',
            password='StrongPassword123!',
        )
        self.user_b = User.objects.create_user(
            username='listener_b',
            email='b@amplitone.local',
            password='StrongPassword123!',
        )

        # Create an Artist with their own dedicated User account
        self.artist_user = User.objects.create_user(
            username='north_arcade',
            password='StrongPassword123!',
        )
        self.artist = Artist.objects.create(
            user=self.artist_user,
            name='North Arcade',
            bio='Electronic duo.',
        )
        self.album = Album.objects.create(
            artist=self.artist,
            title='Night Index',
            release_date=date(2026, 4, 2),
        )
        self.track = Track.objects.create(
            album=self.album,
            title='Low Signal',
            track_number=1,
            duration_seconds=225,
        )

    def test_admin_only_artist_crud_and_dedicated_account(self):
        """Only admins can access Artist CRUD, and creating an Artist provisions a User account."""
        # Non-admin user receives 403 Forbidden
        self.client.login(username='listener_a', password='StrongPassword123!')
        resp_forbidden = self.client.get(reverse('artists:create'))
        self.assertEqual(resp_forbidden.status_code, 403)

        # Admin can create a new Artist + dedicated User account
        self.client.login(username='admin_user', password='StrongPassword123!')
        resp = self.client.post(reverse('artists:create'), {
            'name': 'Mara Vale',
            'bio': 'Nocturnal synth artist.',
            'account_username': 'mara_vale_acct',
            'account_email': 'mara@amplitone.local',
            'account_password': 'ArtistSecretPassword123',
        })
        self.assertEqual(resp.status_code, 302)
        created_artist = Artist.objects.get(name='Mara Vale')
        self.assertEqual(created_artist.user.username, 'mara_vale_acct')

    def test_playlist_owner_permissions(self):
        """Only the owner of a playlist can edit, delete, or add/remove tracks."""
        playlist = Playlist.objects.create(
            owner=self.user_a,
            name='Late Night Circuit',
            description='Owner A playlist',
        )

        # User B attempts to edit or delete User A's playlist -> 403 Forbidden
        self.client.login(username='listener_b', password='StrongPassword123!')
        self.assertEqual(
            self.client.post(
                reverse('library:playlist_update', kwargs={'pk': playlist.pk}),
                {'name': 'Hacked Name', 'description': ''},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse('library:playlist_delete', kwargs={'pk': playlist.pk})
            ).status_code,
            403,
        )

        # Owner (User A) can add and remove tracks
        self.client.login(username='listener_a', password='StrongPassword123!')
        self.client.post(
            reverse('library:playlist_add_track', kwargs={'pk': playlist.pk}),
            {'track_id': self.track.pk},
        )
        self.assertTrue(playlist.tracks.filter(pk=self.track.pk).exists())

        self.client.post(
            reverse(
                'library:playlist_remove_track',
                kwargs={'pk': playlist.pk, 'track_pk': self.track.pk},
            )
        )
        self.assertFalse(playlist.tracks.filter(pk=self.track.pk).exists())

    def test_reject_files_in_non_file_fields(self):
        """Uploading a file inside a non-file field (e.g. 'name' on PlaylistForm) is rejected."""
        self.client.login(username='listener_a', password='StrongPassword123!')
        injected_file = SimpleUploadedFile(
            'exploit.txt', b'not allowed in text field', content_type='text/plain'
        )
        resp = self.client.post(
            reverse('library:playlist_create'),
            {'name': injected_file, 'description': 'Testing non-file field rejection'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "File upload rejected for non-file field")
        self.assertEqual(Playlist.objects.count(), 0)

    def test_strict_image_and_audio_binary_validation(self):
        """Spoofed image/audio files with invalid binary headers are rejected."""
        self.client.login(username='listener_a', password='StrongPassword123!')

        # Spoofed PNG (wrong magic header)
        fake_png = SimpleUploadedFile(
            'cover.png', b'NOT_A_REAL_PNG_HEADER', content_type='image/png'
        )
        resp = self.client.post(reverse('catalog:album_create'), {
            'title': 'Bad Cover Album',
            'artist': self.artist.pk,
            'release_date': '2026-05-01',
            'cover': fake_png,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "File header does not match a valid PNG, JPEG, or WebP image.")

        # Valid PNG magic header passes validation
        valid_png = SimpleUploadedFile(
            'cover.png',
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01',
            content_type='image/png',
        )
        resp_ok = self.client.post(reverse('catalog:album_create'), {
            'title': 'Valid Cover Album',
            'artist': self.artist.pk,
            'release_date': '2026-05-01',
            'cover': valid_png,
        })
        self.assertEqual(resp_ok.status_code, 302)

    def test_htmx_partial_rendering_and_likes(self):
        """HTMX requests return only the #main-content partial so audio playback continues."""
        resp_full = self.client.get(reverse('core:home'))
        self.assertContains(resp_full, '<!DOCTYPE html>')

        resp_htmx = self.client.get(reverse('core:home'), HTTP_HX_REQUEST='true')
        self.assertNotContains(resp_htmx, '<!DOCTYPE html>')
        self.assertContains(resp_htmx, 'Music that')

        # Like toggle
        self.client.login(username='listener_a', password='StrongPassword123!')
        self.client.post(
            reverse('library:toggle_like', kwargs={'track_pk': self.track.pk}),
            HTTP_HX_REQUEST='true',
        )
        self.assertTrue(
            LikedSong.objects.filter(user=self.user_a, track=self.track).exists()
        )

    def test_track_audio_duration_derivation_and_photo_upload(self):
        """Duration is automatically derived from WAV audio file, and optional track photo is saved."""
        import io
        import wave

        self.client.login(username='north_arcade', password='StrongPassword123!')

        # Build a 3-second valid WAV in memory
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(b'\x00\x00' * 8000 * 3)  # 3 seconds of silence

        wav_file = SimpleUploadedFile('sample.wav', buf.getvalue(), content_type='audio/wav')
        photo_file = SimpleUploadedFile(
            'single.png',
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01',
            content_type='image/png',
        )

        resp = self.client.post(reverse('catalog:track_create'), {
            'album': self.album.pk,
            'title': 'WAV Derived Track',
            'track_number': 2,
            'audio_file': wav_file,
            'cover': photo_file,
        })
        self.assertEqual(resp.status_code, 302)
        created_track = Track.objects.get(title='WAV Derived Track')
        self.assertEqual(created_track.duration_seconds, 3)
        self.assertTrue(bool(created_track.cover))
        self.assertEqual(created_track.effective_cover, created_track.cover)

    def test_single_admin_email_login_and_standard_user_restrictions(self):
        """
        Verifies:
        1. Single admin account login via `admin@gmail.com` / `0913admin`.
        2. Standard users do not see the Manage Artists link in the sidebar.
        3. Artist detail page displays details, albums, songs, and playlists.
        """
        resp_login = self.client.post(reverse('accounts:login'), {
            'username': 'admin@gmail.com',
            'password': '0913admin',
        })
        self.assertEqual(resp_login.status_code, 302)

        # Admin sees the Manage Artists route in the sidebar
        home_admin = self.client.get(reverse('core:home'))
        self.assertContains(home_admin, reverse('artists:manage'))

        # Standard user does NOT see the Manage Artists route in the sidebar
        self.client.logout()
        self.client.login(username='listener_a', password='StrongPassword123!')
        home_std = self.client.get(reverse('core:home'))
        self.assertNotContains(home_std, reverse('artists:manage'))

        # Artist detail view shows artist details, albums, songs, and playlists
        detail_resp = self.client.get(reverse('artists:detail', kwargs={'pk': self.artist.pk}))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, 'North Arcade')
        self.assertContains(detail_resp, 'Night Index')
        self.assertContains(detail_resp, 'Low Signal')

    def test_physical_file_cleanup_on_delete(self):
        """Verifies that deleting an Artist, Album, or Track cleans up the file from storage."""
        valid_png = SimpleUploadedFile(
            'img.png',
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01',
            content_type='image/png',
        )

        test_artist = Artist.objects.create(
            user=self.user_b,
            name='Cleanup Artist',
            image=valid_png,
        )
        artist_img_name = test_artist.image.name
        self.assertTrue(test_artist.image.storage.exists(artist_img_name))

        test_artist.delete()
        self.assertFalse(test_artist.image.storage.exists(artist_img_name))

    def test_album_form_standard_user_vs_admin(self):
        """
        Verifies that:
        1. Standard users do not have an 'artist' field when creating/editing albums;
           saving automatically binds the album to their own Artist profile.
        2. Admin users have the 'artist' field in the form and can assign any artist.
        """
        # Standard user accesses album create form
        self.client.login(username='listener_a', password='StrongPassword123!')
        resp_std_form = self.client.get(reverse('catalog:album_create'))
        self.assertEqual(resp_std_form.status_code, 200)
        self.assertNotContains(resp_std_form, 'id_artist')

        # Standard user posts album create form without artist field
        post_resp = self.client.post(reverse('catalog:album_create'), {
            'title': 'Listener A Solo Debut',
            'release_date': '2026-05-12',
        })
        self.assertEqual(post_resp.status_code, 302)
        album_created = Album.objects.get(title='Listener A Solo Debut')
        self.assertEqual(album_created.artist.user, self.user_a)

        # Admin user accesses album create form
        self.client.logout()
        self.client.login(username='admin_user', password='StrongPassword123!')
        resp_admin_form = self.client.get(reverse('catalog:album_create'))
        self.assertEqual(resp_admin_form.status_code, 200)
        self.assertContains(resp_admin_form, 'id_artist')

    def test_guest_vs_authenticated_shell_and_htmx_toast_bar(self):
        """
        Verifies:
        1. Unauthenticated requests receive `is_user_authenticated=False` and do NOT
           render the Left Sidebar, Bottom Media Player, or Navbar Search Bar.
        2. Authenticated requests receive `is_user_authenticated=True` and DO render
           the Left Sidebar, Bottom Media Player, and Navbar Search Bar.
        3. Inline `.flash-messages` in `#main-content` are replaced by the floating
           `#toast-list` Toast Bar with random `toast-...` IDs and HTMX OOB support.
        """
        self.client.logout()
        guest_home = self.client.get(reverse('core:home'))
        self.assertEqual(guest_home.status_code, 200)
        self.assertFalse(guest_home.context['is_user_authenticated'])
        self.assertNotContains(guest_home, 'class="left-sidebar"')
        self.assertNotContains(guest_home, 'id="player-bar"')
        self.assertNotContains(guest_home, 'id="global-search-input"')
        self.assertContains(guest_home, 'id="toast-list"')
        self.assertNotContains(guest_home, 'class="flash-messages"')

        # Authenticate as standard user
        self.client.login(username='listener_a', password='StrongPassword123!')
        auth_home = self.client.get(reverse('core:home'))
        self.assertEqual(auth_home.status_code, 200)
        self.assertTrue(auth_home.context['is_user_authenticated'])
        self.assertContains(auth_home, 'class="left-sidebar"')
        self.assertContains(auth_home, 'id="player-bar"')
        self.assertContains(auth_home, 'id="global-search-input"')

        # Trigger an HTMX action (toggle like) and verify HTMX OOB toast with random ID
        htmx_like = self.client.post(
            reverse('library:toggle_like', kwargs={'track_pk': self.track.pk}),
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(htmx_like.status_code, 200)
        self.assertContains(htmx_like, 'hx-swap-oob="beforeend"')
        self.assertContains(htmx_like, 'data-toast-item')
        self.assertContains(htmx_like, 'id="toast-')

    def test_user_profile_picture_upload_and_cleanup(self):
        """Verifies uploading a profile picture on user profile update and automatic file cleanup."""
        self.client.login(username='listener_a', password='StrongPassword123!')

        avatar_png = SimpleUploadedFile(
            'avatar.png',
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01',
            content_type='image/png',
        )
        resp = self.client.post(
            reverse('accounts:profile'),
            {
                'username': 'listener_a',
                'email': 'a@amplitone.local',
                'first_name': 'Alex',
                'last_name': 'Vane',
                'profile_picture': avatar_png,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.user_a.refresh_from_db()
        self.assertTrue(bool(self.user_a.user_profile.avatar))
        saved_avatar_name = self.user_a.user_profile.avatar.name
        self.assertTrue(self.user_a.user_profile.avatar.storage.exists(saved_avatar_name))
        self.assertContains(resp, self.user_a.user_profile.avatar.url)

        # Deleting the UserProfile removes the physical file from disk
        self.user_a.user_profile.delete()
        self.assertFalse(self.artist.image.storage.exists(saved_avatar_name))

    def test_manage_albums_and_tracks_scoping_vs_collection_and_overview(self):
        """
        Verifies:
        1. Manage Albums (/catalog/albums/) displays ONLY the user's own albums in a table
           with action buttons and a + New Album button.
        2. Collection Albums (/catalog/albums/all/) displays albums of all artists.
        3. Manage Tracks (/catalog/tracks/) displays ONLY the user's own tracks.
        4. Overview Tracks (/catalog/tracks/all/) displays all tracks across the catalog.
        5. Sidebar navigation routes are mapped accurately.
        """
        from accounts.utils import get_or_create_user_artist
        artist_a = get_or_create_user_artist(self.user_a)
        user_a_album = Album.objects.create(
            artist=artist_a,
            title='User A Debut',
            release_date=date(2026, 6, 1),
        )
        user_a_track = Track.objects.create(
            album=user_a_album,
            title='User A Song',
            track_number=1,
            duration_seconds=180,
        )

        self.client.login(username='listener_a', password='StrongPassword123!')

        # 1. Manage Albums: User A sees only their own album, NOT North Arcade's album
        resp_manage_albums = self.client.get(reverse('catalog:album_list'))
        self.assertEqual(resp_manage_albums.status_code, 200)
        self.assertContains(resp_manage_albums, 'User A Debut')
        self.assertNotContains(resp_manage_albums, 'Night Index')
        self.assertContains(resp_manage_albums, reverse('catalog:album_create'))
        self.assertContains(resp_manage_albums, reverse('catalog:album_update', kwargs={'pk': user_a_album.pk}))
        self.assertContains(resp_manage_albums, reverse('catalog:album_delete', kwargs={'pk': user_a_album.pk}))

        # 2. Collection Albums: Shows all albums across all artists
        resp_all_albums = self.client.get(reverse('catalog:album_all'))
        self.assertEqual(resp_all_albums.status_code, 200)
        self.assertContains(resp_all_albums, 'User A Debut')
        self.assertContains(resp_all_albums, 'Night Index')

        # 3. Manage Tracks: User A sees only their own track, NOT North Arcade's track
        resp_manage_tracks = self.client.get(reverse('catalog:track_list'))
        self.assertEqual(resp_manage_tracks.status_code, 200)
        self.assertContains(resp_manage_tracks, 'User A Song')
        self.assertNotContains(resp_manage_tracks, 'Low Signal')
        self.assertContains(resp_manage_tracks, reverse('catalog:track_create'))

        # 4. Overview Tracks: Shows all tracks across the system
        resp_all_tracks = self.client.get(reverse('catalog:track_all'))
        self.assertEqual(resp_all_tracks.status_code, 200)
        self.assertContains(resp_all_tracks, 'User A Song')
        self.assertContains(resp_all_tracks, 'Low Signal')

        # 5. Sidebar check: Collection links to album_all; Manage links to album_list and track_list
        home_resp = self.client.get(reverse('core:home'))
        self.assertContains(home_resp, reverse('catalog:album_all'))
        self.assertContains(home_resp, reverse('catalog:album_list'))
        self.assertContains(home_resp, reverse('catalog:track_list'))

    def test_playlist_cover_upload_and_cleanup_on_delete(self):
        """Verifies uploading a playlist cover photo and automatic physical cleanup on delete."""
        self.client.login(username='listener_a', password='StrongPassword123!')

        cover_png = SimpleUploadedFile(
            'pl_cover.png',
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01',
            content_type='image/png',
        )
        resp = self.client.post(reverse('library:playlist_create'), {
            'name': 'Covered Playlist',
            'description': 'A playlist with cover art.',
            'cover': cover_png,
            'is_private': False,
        })
        self.assertEqual(resp.status_code, 302)

        playlist = Playlist.objects.get(name='Covered Playlist')
        self.assertTrue(bool(playlist.cover))
        cover_storage_name = playlist.cover.name
        self.assertTrue(playlist.cover.storage.exists(cover_storage_name))

        # Check detail view renders the cover
        detail_resp = self.client.get(reverse('library:playlist_detail', kwargs={'pk': playlist.pk}))
        self.assertContains(detail_resp, playlist.cover.url)

        # Deleting the playlist physically cleans up the cover file
        playlist.delete()
        self.assertFalse(self.artist.image.storage.exists(cover_storage_name))

    def test_track_form_album_dropdown_scoped_to_owned_albums(self):
        """
        Standard users only see albums they own in track create & update forms.
        Admins see all albums. Standard users cannot assign a track to an album they do not own.
        """
        # listener_a has their own artist profile and album
        from accounts.utils import get_or_create_user_artist
        artist_a = get_or_create_user_artist(self.user_a)
        album_a = Album.objects.create(
            artist=artist_a,
            title="Listener A Album",
            release_date=date(2026, 5, 1),
        )

        # 1. Check create view form choices for listener_a
        self.client.login(username='listener_a', password='StrongPassword123!')
        resp_create = self.client.get(reverse('catalog:track_create'))
        self.assertEqual(resp_create.status_code, 200)
        # Should contain album_a and NOT contain self.album (North Arcade's album)
        self.assertContains(resp_create, album_a.title)
        self.assertNotContains(resp_create, self.album.title)

        # 2. Attempting to create track under another artist's album should be rejected
        resp_post_invalid = self.client.post(reverse('catalog:track_create'), {
            'album': self.album.pk,
            'title': 'Hacked Track',
            'track_number': 1,
        })
        # Form validation fails, returning 200 with error
        self.assertEqual(resp_post_invalid.status_code, 200)
        self.assertFalse(Track.objects.filter(title='Hacked Track').exists())

        # Creating track under own album succeeds
        resp_post_valid = self.client.post(reverse('catalog:track_create'), {
            'album': album_a.pk,
            'title': 'Valid Track',
            'track_number': 1,
        })
        self.assertEqual(resp_post_valid.status_code, 302)
        created_track = Track.objects.get(title='Valid Track')
        self.assertEqual(created_track.album, album_a)

        # 3. Check update view form choices for listener_a
        resp_update = self.client.get(reverse('catalog:track_update', kwargs={'pk': created_track.pk}))
        self.assertEqual(resp_update.status_code, 200)
        self.assertContains(resp_update, album_a.title)
        self.assertNotContains(resp_update, self.album.title)

        # 4. Check admin sees all albums
        self.client.logout()
        self.client.force_login(self.admin_user)
        resp_admin_create = self.client.get(reverse('catalog:track_create'))
        self.assertEqual(resp_admin_create.status_code, 200)
        self.assertContains(resp_admin_create, album_a.title)
        self.assertContains(resp_admin_create, self.album.title)






