/**
 * Amplitone Dual-Tier IntersectionObserver & Button Loading Controller
 *
 * 1. IntersectionObserver:
 *    - Authenticated App Pages use `data-animate="subtle"` for a refined editorial reveal.
 *    - Actual Login & Registration Pages use `data-animate="noticeable"` and `data-animate="line"`
 *      for pronounced architectural entrance choreography.
 *    - Re-observes elements automatically after every HTMX swap into `#main-content`.
 *
 * 2. Button Processing / Loading Indicators:
 *    - Automatically disables buttons and shows a spinner + loading state during
 *      form submissions and HTMX requests, restoring them when complete.
 */

(function () {
    const scrollRoot = document.getElementById('main-content');

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }
            });
        },
        {
            root: scrollRoot || null,
            threshold: 0.08,
            rootMargin: '0px 0px -24px 0px',
        }
    );

    function observeAnimatedNodes(container) {
        const scope = container || document;

        // Assign stagger indices to grid tiles and table rows for smooth cascading
        scope.querySelectorAll('.media-grid, .track-table tbody, .stagger-group').forEach((group) => {
            const children = group.querySelectorAll('[data-animate]');
            children.forEach((child, idx) => {
                if (!child.style.getPropertyValue('--stagger')) {
                    child.style.setProperty('--stagger', Math.min(idx, 12));
                }
            });
        });

        scope.querySelectorAll('[data-animate]:not(.is-visible)').forEach((el) => {
            observer.observe(el);
        });
    }

    // ========================================================================
    // BUTTON LOADING INDICATOR HELPERS
    // ========================================================================

    function activateButtonLoading(btn) {
        if (!btn || btn.classList.contains('is-loading')) return;

        btn.classList.add('is-loading');
        if (btn.tagName === 'BUTTON') {
            btn.disabled = true;
        }
        btn.dataset.originalHtml = btn.innerHTML;

        const isCompact =
            btn.classList.contains('btn-sm') ||
            btn.classList.contains('btn-square') ||
            btn.classList.contains('icon-btn') ||
            btn.classList.contains('like-heart-btn');

        if (isCompact) {
            btn.innerHTML = '<span class="btn-spinner" aria-hidden="true"></span>';
        } else {
            btn.innerHTML = '<span class="btn-spinner" aria-hidden="true"></span><span>Processing...</span>';
        }
    }

    function restoreButtonLoading(btn) {
        if (!btn || !btn.classList.contains('is-loading')) return;

        btn.classList.remove('is-loading');
        if (btn.tagName === 'BUTTON') {
            btn.disabled = false;
        }
        if (btn.dataset.originalHtml !== undefined) {
            btn.innerHTML = btn.dataset.originalHtml;
            delete btn.dataset.originalHtml;
        }
    }

    function resolveTriggerButtons(targetEl, requestConfig) {
        if (!targetEl) return [];

        // If target is a FORM being submitted:
        if (targetEl.tagName === 'FORM') {
            // Search forms / GET queries do not mutate records
            const formMethod = (targetEl.getAttribute('method') || 'GET').toUpperCase();
            if (formMethod === 'GET') {
                return [];
            }
            return Array.from(
                targetEl.querySelectorAll('button[type="submit"], .btn-primary, .btn-danger')
            );
        }

        // Check if this is an HTMX request or regular action
        // Navigation links (<a> elements, or elements performing hx-get for page navigation) should NOT trigger "Processing..."
        const link = targetEl.closest('a');
        if (link) {
            // Anchor navigation links never display "Processing..." button loaders
            return [];
        }

        // For HTMX button triggers, verify if the request is an API/DB modification or mutation
        if (requestConfig) {
            const verb = (requestConfig.verb || '').toUpperCase();
            // GET requests from buttons (like navigation) should not show "Processing..."
            if (verb && verb === 'GET') {
                return [];
            }
        } else {
            // If checking an element directly without requestConfig:
            const hasMutationHx = targetEl.hasAttribute('hx-post') ||
                targetEl.hasAttribute('hx-delete') ||
                targetEl.hasAttribute('hx-put') ||
                targetEl.hasAttribute('hx-patch');
            const isSubmitButton = targetEl.tagName === 'BUTTON' && targetEl.getAttribute('type') === 'submit';
            if (!hasMutationHx && !isSubmitButton) {
                return [];
            }
        }

        const buttonLike = targetEl.closest(
            'button, .btn-primary, .btn-danger'
        );
        return buttonLike ? [buttonLike] : [];
    }

    // ========================================================================
    // FLOATING TOAST NOTIFICATION CONTROLLER (Random ID + setTimeout DOM Cleanup)
    // ========================================================================

    /**
     * Generates a random unique DOM ID for a toast element.
     */
    function generateToastId() {
        const rand = Math.random().toString(36).substring(2, 9);
        const time = Date.now().toString(36).slice(-4);
        return `toast-${rand}-${time}`;
    }

    /**
     * Smoothly transitions out a toast element by its DOM ID and deletes it
     * from the DOM to keep the document tree clean.
     */
    function removeToastById(toastId) {
        const toastEl = document.getElementById(toastId);
        if (!toastEl || toastEl.classList.contains('is-leaving')) return;

        toastEl.classList.add('is-leaving');
        setTimeout(() => {
            const node = document.getElementById(toastId);
            if (node) {
                node.remove();
            }
        }, 220);
    }

    /**
     * Attaches a self-deleting setTimeout to a toast element using its unique ID.
     */
    function scheduleToast(toastEl) {
        if (!toastEl || toastEl.dataset.toastScheduled === 'true') return;
        toastEl.dataset.toastScheduled = 'true';

        if (!toastEl.id) {
            toastEl.id = generateToastId();
        }
        const toastId = toastEl.id;
        const duration = parseInt(toastEl.dataset.timeout || '4000', 10);

        setTimeout(() => {
            removeToastById(toastId);
        }, duration);
    }

    /**
     * Scans `#toast-list` (or the given root) and schedules self-deletion for
     * any newly rendered or HTMX-swapped toast items.
     */
    function initToasts(root) {
        const scope = root || document;
        scope.querySelectorAll('[data-toast-item]').forEach(scheduleToast);
    }

    /**
     * Programmatically creates a new toast inside `#toast-list` with a randomly
     * generated ID and schedules its automatic DOM deletion.
     */
    function createToast(message, level = 'info', timeout = 4000) {
        const list = document.getElementById('toast-list');
        if (!list || !message) return null;

        const toastId = generateToastId();
        const li = document.createElement('li');
        li.id = toastId;
        li.className = `toast-item toast-item--${level}`;
        li.setAttribute('data-toast-item', '');
        li.setAttribute('data-timeout', String(timeout));
        li.setAttribute('role', 'status');

        const indicator = document.createElement('span');
        indicator.className = 'toast-indicator';
        indicator.setAttribute('aria-hidden', 'true');

        const msgSpan = document.createElement('span');
        msgSpan.className = 'toast-message';
        msgSpan.textContent = message;

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'toast-close-btn';
        closeBtn.setAttribute('aria-label', 'Dismiss notification');
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', () => removeToastById(toastId));

        li.appendChild(indicator);
        li.appendChild(msgSpan);
        li.appendChild(closeBtn);
        list.appendChild(li);

        scheduleToast(li);
        return toastId;
    }

    window.AmplitoneToast = {
        generateToastId,
        removeById: removeToastById,
        scheduleToast,
        initToasts,
        create: createToast,
    };

    document.addEventListener('DOMContentLoaded', () => {
        observeAnimatedNodes(document);
        initToasts(document);

        // Keyboard shortcut Cmd/Ctrl + K to focus the top navbar search input
        document.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
                const searchInput = document.getElementById('global-search-input');
                if (searchInput) {
                    e.preventDefault();
                    searchInput.focus();
                    searchInput.select();
                }
            }
        });

        // Standard (non-HTMX) form submit loading state
        document.addEventListener('submit', (e) => {
            const form = e.target;
            if (form && form.tagName === 'FORM') {
                resolveTriggerButtons(form).forEach(activateButtonLoading);
            }
        });
    });

    // ========================================================================
    // MEDIA FILE PREVIEW CONTROLLER (Image & Audio Previews)
    // ========================================================================

    document.addEventListener('change', (e) => {
        const input = e.target;
        if (!input || input.type !== 'file') return;

        const formGroup = input.closest('.form-group');
        if (!formGroup) return;

        const previewContainer = formGroup.querySelector('.media-preview-container');
        if (!previewContainer) return;

        const isAudio = input.matches('[data-preview-audio], [accept*="audio"]') || previewContainer.querySelector('audio');
        const file = input.files && input.files[0];

        if (isAudio) {
            const audioEl = previewContainer.querySelector('audio');
            const badgeEl = previewContainer.querySelector('.media-preview-badge');
            const nameEl = previewContainer.querySelector('.media-preview-filename');

            if (file) {
                const objectUrl = URL.createObjectURL(file);
                if (audioEl) audioEl.src = objectUrl;
                if (badgeEl) badgeEl.textContent = 'New Audio Selection';
                if (nameEl) nameEl.textContent = file.name;
                previewContainer.classList.remove('is-hidden');
                previewContainer.style.display = 'flex';

                // Auto-detect audio duration if hidden duration input is present in the form
                const form = input.closest('form');
                const durationInput = form ? form.querySelector('#id_duration_seconds') : null;
                if (durationInput) {
                    const tempAudio = new Audio();
                    tempAudio.preload = 'metadata';
                    tempAudio.src = objectUrl;
                    tempAudio.addEventListener('loadedmetadata', () => {
                        if (tempAudio.duration && !isNaN(tempAudio.duration) && isFinite(tempAudio.duration)) {
                            durationInput.value = Math.max(1, Math.round(tempAudio.duration));
                        }
                    });
                }
            } else {
                const originalSrc = previewContainer.dataset.originalUrl;
                if (originalSrc && audioEl) {
                    audioEl.src = originalSrc;
                    if (badgeEl) badgeEl.textContent = 'Current Audio';
                    if (nameEl) nameEl.textContent = previewContainer.dataset.originalFilename || 'Existing Audio';
                    previewContainer.classList.remove('is-hidden');
                    previewContainer.style.display = 'flex';
                } else {
                    if (audioEl) audioEl.removeAttribute('src');
                    previewContainer.classList.add('is-hidden');
                    previewContainer.style.display = 'none';
                }
            }
        } else {
            // Image Preview
            const imgEl = previewContainer.querySelector('img');
            const badgeEl = previewContainer.querySelector('.media-preview-badge');
            const nameEl = previewContainer.querySelector('.media-preview-filename');

            if (file) {
                const objectUrl = URL.createObjectURL(file);
                if (imgEl) imgEl.src = objectUrl;
                if (badgeEl) badgeEl.textContent = 'New Selection';
                if (nameEl) nameEl.textContent = file.name;
                previewContainer.classList.remove('is-hidden');
                previewContainer.style.display = 'flex';
            } else {
                const originalSrc = previewContainer.dataset.originalUrl;
                if (originalSrc && imgEl) {
                    imgEl.src = originalSrc;
                    if (badgeEl) badgeEl.textContent = 'Current Image';
                    if (nameEl) nameEl.textContent = previewContainer.dataset.originalFilename || 'Existing Artwork';
                    previewContainer.classList.remove('is-hidden');
                    previewContainer.style.display = 'flex';
                } else {
                    if (imgEl) imgEl.removeAttribute('src');
                    previewContainer.classList.add('is-hidden');
                    previewContainer.style.display = 'none';
                }
            }
        }
    });

    // HTMX request lifecycle loading state
    document.body.addEventListener('htmx:beforeRequest', (event) => {
        const triggerEl = event.detail.elt;
        const requestConfig = event.detail.requestConfig;
        resolveTriggerButtons(triggerEl, requestConfig).forEach(activateButtonLoading);
    });

    ['htmx:afterRequest', 'htmx:responseError', 'htmx:sendError'].forEach((evtName) => {
        document.body.addEventListener(evtName, (event) => {
            const triggerEl = event.detail.elt;
            const requestConfig = event.detail.requestConfig;
            resolveTriggerButtons(triggerEl, requestConfig).forEach(restoreButtonLoading);
        });
    });

    document.body.addEventListener('htmx:oobAfterSwap', () => {
        initToasts(document);
    });

    document.body.addEventListener('htmx:afterSettle', (event) => {
        observeAnimatedNodes(event.detail.elt || document);
        initToasts(document);
    });
})();
