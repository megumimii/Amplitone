/**
 * Amplitone Persistent Bottom Media Controller
 *
 * Lives outside `#main-content` so HTMX page transitions never interrupt playback.
 * Supports real audio files (`<audio>`) as well as a simulated timer fallback when
 * a track record has no audio file uploaded yet.
 */

(function () {
    const audio = document.getElementById('amplitone-audio');
    const playBtn = document.getElementById('player-play-btn');
    const prevBtn = document.getElementById('player-prev-btn');
    const nextBtn = document.getElementById('player-next-btn');
    const shuffleBtn = document.getElementById('player-shuffle-btn');
    const repeatBtn = document.getElementById('player-repeat-btn');
    const seekInput = document.getElementById('player-seek-input');
    const volumeInput = document.getElementById('player-volume-input');
    const currentTimeEl = document.getElementById('player-current-time');
    const durationEl = document.getElementById('player-total-time');
    const titleEl = document.getElementById('player-title');
    const artistEl = document.getElementById('player-artist');
    const thumbEl = document.getElementById('player-thumb');

    if (!audio || !playBtn) return;

    let queue = [];
    let currentIndex = -1;
    let isPlaying = false;
    let isShuffle = false;
    let isRepeat = false;
    let fallbackTimer = null;
    let fallbackSeconds = 0;
    let fallbackDuration = 180;

    // Ensure audio element never loops natively by default
    audio.loop = false;

    function formatSeconds(sec) {
        const total = Math.max(0, Math.floor(sec || 0));
        const mins = Math.floor(total / 60);
        const rem = total % 60;
        return `${mins}:${rem < 10 ? '0' : ''}${rem}`;
    }

    function updateProgressUI(current, total) {
        const pct = total > 0 ? Math.min(100, (current / total) * 100) : 0;
        seekInput.value = pct;
        seekInput.style.setProperty('--progress', `${pct}%`);
        currentTimeEl.textContent = formatSeconds(current);
        durationEl.textContent = formatSeconds(total);
    }

    function highlightActiveTrackRow(trackId) {
        document.querySelectorAll('.track-row').forEach((row) => {
            row.classList.toggle('is-playing', Boolean(trackId && String(row.dataset.trackId) === String(trackId)));
        });
    }

    function rebuildQueueFromDOM() {
        const triggers = Array.from(document.querySelectorAll('[data-play-track]'));
        if (triggers.length === 0) return;
        queue = triggers.map((btn) => ({
            id: btn.dataset.trackId,
            title: btn.dataset.title || 'Untitled Track',
            artist: btn.dataset.artist || 'Unknown Artist',
            audioUrl: btn.dataset.audioUrl || '',
            coverUrl: btn.dataset.coverUrl || '',
            duration: parseInt(btn.dataset.duration || '180', 10),
        }));
    }

    function recordPlayOnServer(trackId) {
        if (!trackId) return;
        const csrfToken = document.body.dataset.csrfToken || '';
        fetch(`/catalog/tracks/${trackId}/play/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
            },
        }).catch(() => {});
    }

    function stopFallbackTimer() {
        if (fallbackTimer) {
            clearInterval(fallbackTimer);
            fallbackTimer = null;
        }
    }

    function stopPlayback() {
        audio.pause();
        stopFallbackTimer();
        isPlaying = false;
        playBtn.textContent = '▶';
        fallbackSeconds = 0;
        updateProgressUI(0, fallbackDuration);
        highlightActiveTrackRow(null);
    }

    function handleTrackEnded() {
        // 1. If repeat is ON: restart the same track
        if (isRepeat) {
            if (audio.getAttribute('src')) {
                audio.currentTime = 0;
                audio.play().then(() => {
                    isPlaying = true;
                    playBtn.textContent = '❚❚';
                }).catch(() => {});
            } else {
                fallbackSeconds = 0;
                updateProgressUI(0, fallbackDuration);
                startFallbackTimer();
            }
            return;
        }

        // 2. If repeat is OFF:
        if (queue.length === 0) rebuildQueueFromDOM();

        // If queue is empty or only contains 1 track, stop playback — DO NOT REPEAT!
        if (queue.length <= 1) {
            stopPlayback();
            return;
        }

        if (isShuffle) {
            let nextIdx = currentIndex;
            while (nextIdx === currentIndex) {
                nextIdx = Math.floor(Math.random() * queue.length);
            }
            currentIndex = nextIdx;
            loadAndPlayTrack(queue[currentIndex]);
        } else if (currentIndex >= 0 && currentIndex < queue.length - 1) {
            // Move to next track in queue
            currentIndex += 1;
            loadAndPlayTrack(queue[currentIndex]);
        } else {
            // End of queue reached and repeat is OFF: stop playback
            stopPlayback();
        }
    }

    function startFallbackTimer() {
        stopFallbackTimer();
        fallbackTimer = setInterval(() => {
            fallbackSeconds += 1;
            if (fallbackSeconds >= fallbackDuration) {
                stopFallbackTimer();
                handleTrackEnded();
                return;
            }
            updateProgressUI(fallbackSeconds, fallbackDuration);
        }, 1000);
    }

    function loadAndPlayTrack(trackObj) {
        stopFallbackTimer();
        audio.pause();
        audio.loop = false; // Always keep native loop disabled

        titleEl.textContent = trackObj.title;
        artistEl.textContent = trackObj.artist;
        if (trackObj.coverUrl) {
            thumbEl.innerHTML = `<img src="${trackObj.coverUrl}" alt="${trackObj.title}">`;
        } else {
            thumbEl.innerHTML = '';
        }

        fallbackDuration = trackObj.duration || 180;
        fallbackSeconds = 0;
        updateProgressUI(0, fallbackDuration);
        highlightActiveTrackRow(trackObj.id);
        recordPlayOnServer(trackObj.id);

        if (trackObj.audioUrl) {
            audio.src = trackObj.audioUrl;
            audio.play().then(() => {
                isPlaying = true;
                playBtn.textContent = '❚❚';
            }).catch(() => {
                isPlaying = true;
                playBtn.textContent = '❚❚';
                startFallbackTimer();
            });
        } else {
            audio.removeAttribute('src');
            isPlaying = true;
            playBtn.textContent = '❚❚';
            startFallbackTimer();
        }
    }

    function togglePlayPause() {
        if (currentIndex === -1) {
            rebuildQueueFromDOM();
            if (queue.length > 0) {
                currentIndex = 0;
                loadAndPlayTrack(queue[0]);
                return;
            }
        }

        if (isPlaying) {
            audio.pause();
            stopFallbackTimer();
            isPlaying = false;
            playBtn.textContent = '▶';
        } else {
            isPlaying = true;
            playBtn.textContent = '❚❚';
            if (audio.getAttribute('src')) {
                audio.play().catch(() => startFallbackTimer());
            } else {
                startFallbackTimer();
            }
        }
    }

    function playNext(userInitiated = false) {
        if (queue.length === 0) rebuildQueueFromDOM();
        if (queue.length === 0) return;

        if (isShuffle && queue.length > 1) {
            let nextIdx = currentIndex;
            while (nextIdx === currentIndex) {
                nextIdx = Math.floor(Math.random() * queue.length);
            }
            currentIndex = nextIdx;
            loadAndPlayTrack(queue[currentIndex]);
        } else if (userInitiated) {
            // User manually clicked the "Next" button: advance or wrap around
            currentIndex = (currentIndex + 1) % queue.length;
            loadAndPlayTrack(queue[currentIndex]);
        } else {
            handleTrackEnded();
        }
    }

    function playPrev() {
        if (queue.length === 0) rebuildQueueFromDOM();
        if (queue.length === 0) return;

        const currentSec = audio.currentTime || fallbackSeconds;
        // If track has played for more than 3 seconds, clicking Prev restarts it
        if (currentSec > 3) {
            if (audio.getAttribute('src')) {
                audio.currentTime = 0;
            } else {
                fallbackSeconds = 0;
                updateProgressUI(0, fallbackDuration);
            }
            return;
        }

        currentIndex = (currentIndex - 1 + queue.length) % queue.length;
        loadAndPlayTrack(queue[currentIndex]);
    }

    // Event Delegation for any `[data-play-track]` button inside `#main-content`
    document.addEventListener('click', (e) => {
        const trigger = e.target.closest('[data-play-track]');
        if (!trigger) return;
        e.preventDefault();

        rebuildQueueFromDOM();
        const clickedId = trigger.dataset.trackId;
        const foundIdx = queue.findIndex((item) => String(item.id) === String(clickedId));

        if (foundIdx !== -1) {
            currentIndex = foundIdx;
            loadAndPlayTrack(queue[currentIndex]);
        } else {
            const trackData = {
                id: clickedId,
                title: trigger.dataset.title || 'Untitled Track',
                artist: trigger.dataset.artist || 'Unknown Artist',
                audioUrl: trigger.dataset.audioUrl || '',
                coverUrl: trigger.dataset.coverUrl || '',
                duration: parseInt(trigger.dataset.duration || '180', 10),
            };
            queue.push(trackData);
            currentIndex = queue.length - 1;
            loadAndPlayTrack(trackData);
        }
    });

    playBtn.addEventListener('click', togglePlayPause);
    nextBtn.addEventListener('click', () => playNext(true));
    prevBtn.addEventListener('click', playPrev);

    shuffleBtn.addEventListener('click', () => {
        isShuffle = !isShuffle;
        shuffleBtn.style.color = isShuffle ? 'var(--accent-orange)' : '';
        shuffleBtn.title = isShuffle ? 'Shuffle: On' : 'Shuffle: Off';
    });

    repeatBtn.addEventListener('click', () => {
        isRepeat = !isRepeat;
        audio.loop = false; // Always handle repeat explicitly in handleTrackEnded
        repeatBtn.style.color = isRepeat ? 'var(--accent-orange)' : '';
        repeatBtn.title = isRepeat ? 'Repeat: On' : 'Repeat: Off';
    });

    audio.addEventListener('timeupdate', () => {
        if (audio.duration) {
            updateProgressUI(audio.currentTime, audio.duration);
        }
    });

    // Native audio ended listener
    audio.addEventListener('ended', () => {
        handleTrackEnded();
    });

    seekInput.addEventListener('input', () => {
        const pct = parseFloat(seekInput.value) || 0;
        seekInput.style.setProperty('--progress', `${pct}%`);
        if (audio.getAttribute('src') && audio.duration) {
            audio.currentTime = (pct / 100) * audio.duration;
        } else {
            fallbackSeconds = Math.floor((pct / 100) * fallbackDuration);
            updateProgressUI(fallbackSeconds, fallbackDuration);
        }
    });

    volumeInput.addEventListener('input', () => {
        const pct = parseFloat(volumeInput.value) || 0;
        volumeInput.style.setProperty('--progress', `${pct}%`);
        audio.volume = Math.max(0, Math.min(1, pct / 100));
    });
})();
