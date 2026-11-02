# Amplitone — Update Logs

## 2026-11-02 — Add Python Bytecode & Pycache Rules to Gitignore

### Summary
Updated [`.gitignore`](file:///c:/Users/Isaac/Downloads/amplitone/.gitignore) to exclude `config/__pycache__/` and Python bytecode files globally (`__pycache__/`, `*.pyc`), and removed tracked `.pyc` files from the Git staging index.

### Key Changes
1. **`.gitignore`**:
   - Added standard bytecode ignore rules (`__pycache__/`, `*.py[cod]`, `config/__pycache__/`), virtual environment folders, sqlite databases, media uploads, and IDE files.
2. **Git Index**:
   - Untracked cached `.pyc` files from Git staging via `git rm -r --cached`.

## 2026-11-02 — Remove "Processing..." Loading State on Navigation Buttons

### Summary
Restricted the button loading indicator (`is-loading` / `Processing...` spinner) so that it only triggers on actions that mutate records or fetch from the database via forms and modification endpoints. Navigation buttons and links (such as page transition links, sidebar buttons, "+ New Album", "+ Track", "Cancel", and table view/edit links) no longer trigger "Processing...".

### Key Changes
1. **Button Loading Controller (`core/static/core/js/animations.js`)**:
   - Updated `resolveTriggerButtons()` to ignore anchor navigation links (`<a>` elements styled as buttons) and GET request triggers.
   - For form submissions, verified that the HTTP method is a non-GET mutation before activating button loading.
   - Passed `event.detail.requestConfig` from HTMX `htmx:beforeRequest` and completion events to inspect the request verb, ensuring GET requests (e.g., page navigation swaps) do not show the loading state.
   - Confined button targets to actual mutating triggers (`button[type="submit"]`, `.btn-primary`, `.btn-danger`, or buttons executing `hx-post`/`hx-delete`/`hx-put`/`hx-patch`).

## 2026-11-02 — Scope Track Form Album Dropdown to User-Owned Albums

### Summary
Restricted the `album` dropdown choices in both track creation (`track_create_view`) and track updating (`track_update_view`) so that standard users only see albums they own (associated with their user's artist profile). Administrators retain the ability to select from all albums.

### Key Changes
1. **TrackForm (`catalog/forms.py`)**:
   - Added `user=None` parameter to `TrackForm.__init__`.
   - Scoped `self.fields['album'].queryset` to `Album.objects.filter(artist__user=user)` for standard users (`user and not (user.is_staff or user.is_superuser)`), while retaining the full queryset for administrators.
2. **Catalog Views (`catalog/views.py`)**:
   - Updated `track_create_view` to pass `user=request.user` into `TrackForm` for both GET and POST requests.
   - Updated query parameter pre-selection (`?album=<id>`) to filter by the requesting user's artist profile unless the user is an administrator.
   - Updated `track_update_view` to pass `user=request.user` into `TrackForm` for both GET and POST requests.
3. **Automated Testing (`core/tests.py`)**:
   - Added `test_track_form_album_dropdown_scoped_to_owned_albums` to verify that standard users only see their own albums in the dropdown on track create and edit views, cannot assign tracks to foreign albums, and that administrators can see all albums.


## 2026-10-28 — Initial Modular Implementation of Amplitone (Spotify Clone)

### Summary
Implemented the full **Amplitone** streaming web application using **Django 6 + HTMX** with an **Anti-UI-Slop** editorial dark grey (`#0D0D0D` / `#111111`) and desaturated bright orange (`#E06535`) design system.

### Key Architectural & Feature Additions
1. **Routing & Aliases**:
   - Mapped `path('main/', views.home_view, name='main')` as an alias alongside root `path('', views.home_view, name='home')`.
2. **Modular 5-App Django Project Scaffolding**:
   - `core`: Persistent 4-zone shell (`base.html`, `navbar.html`, `sidebar.html`, `player_bar.html`), Home discovery view, unified cross-model Search, HTMX partial rendering helper (`render_page`), sidebar context processor, and strict file/field validators.
   - `accounts`: Built-in Django authentication (`register`, `login`, `logout`, `profile`) and `@admin_required` role decorator.
   - `artists`: `Artist` model linked `1-to-1` with a dedicated `User` account; public Artist directory/detail views and Admin-reserved Artist CRUD (`manage`, `create`, `update`, `delete`).
   - `catalog`: `Album` and `Track` CRUD with nested tracklists, confirmation pages, and playback tracking (`track_play_view`).
   - `library`: `Playlist` and `PlaylistTrack` CRUD with strict owner-only authorization (`_verify_playlist_owner`), `LikedSong` HTMX toggle with Out-of-Band sidebar counter updates, and `RecentlyPlayed` history.
2. **100% `rem`-Based Anti-UI-Slop Styling & Dual-Tier `IntersectionObserver` Animations**:
   - All layout zones, typography, borders, and spacing in `core/static/core/css/amplitone.css` use `rem` units for consistent text-to-container scaling across browser zoom levels.
   - `core/static/core/js/animations.js` implements subtle reveals (`data-animate="subtle"`) for authenticated views and noticeable architectural choreography (`data-animate="noticeable"` and `data-animate="line"`) on the Login and Registration pages.
   - `core/static/core/js/player.js` powers the persistent bottom audio player across HTMX navigation swaps.
3. **Web & File Upload Security**:
   - `StrictFileSecurityFormMixin` in `core/validators.py` rejects any file uploaded into a non-file field.
   - `validate_image_file` and `validate_audio_file` enforce extension whitelists, MIME types, file size caps, and binary magic-byte header verification.

## 2026-10-28 — Demo Record Purge & Clean Empty States
- Purged all seeded demo database records (`Artist`, `Album`, `Track`, `Playlist`, `LikedSong`, `RecentlyPlayed`, and demo `User` accounts) and deleted generated sample audio files from `media/`.
- Removed `seed_amplitone.py` command.
- Converted the persistent bottom media player bar (`player_bar.html` and `player.js`) from static mockup placeholder text to clean idle empty states ("No track selected", "0:00 / 0:00", 0% progress).
- Documented in `lessons-learned.md`.

## 2026-10-28 — Audio Duration Auto-Derivation, File Picker Filters & Track Cover Art
- Added `extract_audio_duration()` in `core/validators.py` and client-side metadata pre-calculation on `#id_audio_file` selection to auto-derive `duration_seconds` from uploaded audio files without manual input.
- Pre-selected allowed audio files in OS file explorer dialogs via `accept="audio/*,.mp3,.wav,.ogg,.flac,.m4a"`.
- Pre-selected allowed image files in OS file explorer dialogs via `accept="image/*,.jpg,.jpeg,.png,.webp"`.
- Added `cover` field and `effective_cover` fallback property to `Track` model (`catalog.0002_track_cover`), allowing custom track-specific photos that fall back to the album cover if omitted.
- Updated `track_row.html` to display the effective track artwork thumbnail and pass it to the persistent bottom player.

## 2026-10-28 — Single Admin Account, Artist Table/Detail View, Password Validation UI & Button Loading States
- Configured the single Administrator account (`admin@gmail.com` / `0913admin`) via `ensure_single_admin_account()` in `accounts/utils.py`, and updated `UserLoginForm` to authenticate by either Email or Username.
- Enabled Standard Users to automatically receive a linked `Artist` profile (`get_or_create_user_artist`) so they can create/manage their own albums and tracks and curate playlists from any user's tracks, while restricting cross-account management strictly to the Admin.
- Removed the "Manage -> Artists" link from the sidebar for Standard Users.
- Updated the Artist Directory (`artist_list.html`) and Admin Artist Console (`artist_manage.html`) to a table layout with a `View Artist` button, and expanded `artist_detail.html` to display the artist's details, albums, songs, and playlists.
- Added live green password requirement indicators (`#2ecc71`) in `accounts/templates/accounts/register.html`.
- Added global button loading indicators (`is-loading` + spinner + disabled state) in `core/static/core/js/animations.js` and `core/static/core/css/amplitone.css`.

## 2026-10-28 — Hidden Duration Input on Track Create/Edit Form
- Switched `duration_seconds` to a hidden input field (`forms.HiddenInput`) in `catalog/forms.py` (`TrackForm`), completely removing the duration input box from the user-visible form UI.
- Updated `catalog/templates/catalog/track_form.html` to separate hidden and visible fields so `duration_seconds` is auto-populated in the background from the audio file without requiring manual entry.

## 2026-10-28 — Fix Audio Player Repeat Behavior
- Fixed track auto-looping in `core/static/core/js/player.js` by centralizing end-of-track progression inside `handleTrackEnded()`.
- Ensured that when repeat is disabled, the player halts cleanly upon reaching the end of the queue or when only one track exists, preventing unwanted looping.
- Kept native `audio.loop = false` disabled and managed repeat state strictly via JavaScript.
- Documented in `lessons-learned.md`.

## 2026-10-28 — Automatic Physical File Cleanup on Delete & Update
- Added `catalog/signals.py` and `artists/signals.py` connected in `apps.py` (`ready()`).
- Deleting an `Artist`, `Album`, or `Track` record automatically deletes the associated image and audio files from physical disk storage (`media/`).
- Replacing a file on update automatically deletes the previous orphaned file from disk storage.

## 2026-10-28 — Artist Field Scoping on Create & Edit Album Forms
- Removed the `artist` dropdown selector from `AlbumForm` for standard users in `catalog/forms.py` and `catalog/views.py`.
- For standard users, newly created albums are automatically attributed to their own linked `Artist` profile (`get_or_create_user_artist`).
- Restricted manual `artist` selection on album creation/editing strictly to Administrator accounts.
- Updated `catalog/templates/catalog/album_form.html` editorial copy to clearly indicate that standard users release albums under their own profile.

## 2026-10-28 — Floating HTMX Toast Bar & Conditional Authenticated Shell
- Removed the static `.flash-messages` block from `#main-content` in `core/templates/core/base.html`.
- Implemented a floating Toast Notification Bar (`#toast-list` in `core/templates/core/components/toast_bar.html`, `toast_oob.html`, and `toast_item.html`) styled with Anti-UI-Slop editorial cards.
- Added `generate_toast_id()` and `consume_toast_messages(request)` in `core/utils.py` so every flash message is consumed immediately on both full page loads and HTMX requests (delivered via `<ul id="toast-list" hx-swap-oob="beforeend">`).
- Added `window.AmplitoneToast` in `core/static/core/js/animations.js` with random ID generation (`generateToastId()`), `setTimeout` scheduling (`scheduleToast()`), and automatic DOM node self-deletion (`removeById()` / `node.remove()`) to keep the DOM optimized.
- Injected `is_user_authenticated` into all request/response contexts via `core/context_processors.py` (`sidebar_context`) and `core/utils.py` (`render_page`).
- Conditionally removed the Left Sidebar, Bottom Play Controller, and Top Navbar Search Bar when `is_user_authenticated` is `False`, and added `body.is-guest` CSS grid rules so unauthenticated pages occupy the full viewport cleanly.

## 2026-10-28 — User Profile Picture Upload & Automatic Avatar Cleanup
- Added the `UserProfile` model (`accounts/models.py`, migration `accounts.0001_initial`) with `avatar = models.FileField(upload_to='accounts/avatars/', validators=[validate_image_file])`.
- Added `profile_picture` upload field to `UserProfileForm` (`accounts/forms.py`) with file explorer pre-selection (`accept="image/*,.jpg,.jpeg,.png,.webp"`) and magic-byte validation.
- Updated `accounts/templates/accounts/profile.html` to display the user's current profile picture, submit multipart uploads (`enctype="multipart/form-data"` and `hx-encoding="multipart/form-data"`), and out-of-band swap `#navbar-avatar` in the top navbar upon save.
- Added `Artist.effective_image` fallback in `artists/models.py` so a user's profile picture also serves as their artist portrait fallback.
- Added `accounts/signals.py` (`post_delete` and `pre_save`) connected in `accounts/apps.py` to automatically delete replaced or deleted avatar files from disk storage (`media/accounts/avatars/`).

## 2026-10-28 — Playlist Cover Photo Upload & Automatic Storage Cleanup
- Added `cover = models.FileField(upload_to='playlists/covers/', ...)` to the `Playlist` model (`library/models.py`, migration `library.0002_playlist_cover`).
- Added `cover` upload field to `PlaylistForm` (`library/forms.py`) with OS file dialog pre-selection (`accept="image/*,.jpg,.jpeg,.png,.webp"`), max 5 MB cap, and binary magic-byte verification.
- Updated `library/templates/library/playlist_form.html` to support multipart form uploads (`enctype="multipart/form-data"` and `hx-encoding="multipart/form-data"`).
- Updated `library/templates/library/playlist_detail.html`, `library/templates/library/playlist_list.html`, and `core/templates/core/components/sidebar.html` to display the playlist cover photo.
- Added `library/signals.py` (`post_delete` and `pre_save`) connected in `library/apps.py` to physically delete orphaned playlist cover photos from disk storage (`media/playlists/covers/`) upon playlist deletion or cover replacement.








