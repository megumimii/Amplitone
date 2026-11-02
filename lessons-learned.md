# Lessons Learned

## Lesson 1: Pre-Populating Demo Records & Mockup Placeholder Text

- **Problem**: Demo records (artists, albums, tracks, playlists, and user accounts) were seeded into the development database, and the bottom player bar contained hardcoded mockup placeholder text ("Low Signal", "North Arcade", "1:18 / 3:45", progress at 34%) mirroring the Figma screenshots, causing confusion over whether these were active demo records or placeholders.
- **Root cause**: Running an automated seed command to match the reference screenshots visually without keeping the production/development database clean by default, combined with copying static text from the design mockup directly into the template shell.
- **Prevention**: Keep database records completely clean upon initial setup unless sample data is explicitly requested by the user. Templates and stateful UI components (e.g., media players, counters, grids) must always start in neutral, dynamic empty states ("No track selected", "0:00 / 0:00", 0% progress) until real data is created or played.

## Lesson 2: Player Auto-Repeat Behavior When Repeat Is Disabled

- **Problem**: When repeat was turned off, tracks still repeated upon finishing instead of stopping at the end of the queue or when only one track was loaded.
- **Root cause**: The player's track-completion handler directly invoked `playNext()`, which used modulo arithmetic `(currentIndex + 1) % queue.length`. With a single track or at the end of a queue, `(0 + 1) % 1` or `(N + 1) % (N + 1)` wrapped back to index `0`, causing unintentional looping.
- **Prevention**: Centralize automatic end-of-track progression in a dedicated `handleTrackEnded()` handler. When repeat is disabled, only advance if `currentIndex < queue.length - 1`; otherwise stop playback cleanly (`stopPlayback()`). Keep user-initiated manual "Next" clicks distinct from automatic end-of-track events.

## Lesson 3: Accumulating Flash Messages in HTMX Partial Swaps

- **Problem**: Django `messages` rendered only inside `base.html` accumulated in the session during HTMX partial navigations and then dumped all at once as persistent banner boxes inside `#main-content` on the next full page load.
- **Root cause**: HTMX partial responses bypassed `base.html`, so `messages` were not consumed during HTMX requests, and static banner elements had no auto-dismissal or DOM cleanup lifecycle.
- **Prevention**: Consume Django `messages` inside the central `render_page()` helper on every request (both full loads and HTMX requests), deliver them to a floating `<ul id="toast-list">` via HTMX Out-of-Band swaps (`hx-swap-oob="beforeend"`), and attach a `setTimeout` to each toast using a randomly generated element ID so it deletes its own node (`node.remove()`) from the DOM.


