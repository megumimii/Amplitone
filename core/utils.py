"""
Shared HTMX rendering utilities for Amplitone.

How HTMX navigation works in Amplitone:
- The page has 4 persistent sections: Top Navbar, Left Sidebar, Main Body (#main-content),
  and Bottom Media Controller (#player-bar).
- When a link or form is triggered via HTMX (`HX-Request: true`), we return ONLY the
  partial template so `#main-content` updates while the `<audio>` player keeps playing.
- When a user visits or refreshes a URL directly in the browser (not an HTMX request),
  we render `core/base.html` and pass `content_template` so the full 4-section shell loads.
"""

import secrets
from django.contrib import messages
from django.shortcuts import render
from django.template.loader import render_to_string


def is_htmx(request):
    """Returns True if the request was triggered by HTMX."""
    return request.headers.get('HX-Request') == 'true'


def generate_toast_id():
    """Generates a random unique DOM element ID for a Toast notification."""
    return f"toast-{secrets.token_hex(4)}"


def consume_toast_messages(request):
    """
    Consumes pending Django flash messages and converts them into a list of
    toast dictionaries, each with its own randomly generated DOM ID.
    """
    storage = messages.get_messages(request)
    toasts = []
    for msg in storage:
        toasts.append({
            'id': generate_toast_id(),
            'message': str(msg),
            'level': msg.level_tag or 'info',
        })
    return toasts


def render_page(request, partial_template, context=None, status=200):
    """
    Renders `partial_template` alone for HTMX requests targeting `#main-content`,
    or wraps it inside `core/base.html` for full browser page loads.

    Always injects:
    - `is_user_authenticated`: Boolean indicating whether the current user is logged in.
    - `toast_items`: List of consumed toast notifications (with random DOM IDs),
      delivered via HTMX Out-of-Band swap (`hx-swap-oob="beforeend"`) on HTMX requests
      or rendered directly inside `#toast-list` on full page loads.
    """
    context = dict(context) if context else {}
    context['content_template'] = partial_template
    context['is_user_authenticated'] = bool(
        getattr(request, 'user', None) and request.user.is_authenticated
    )
    context['toast_items'] = consume_toast_messages(request)

    if is_htmx(request):
        response = render(request, partial_template, context, status=status)
        if context['toast_items']:
            oob_html = render_to_string(
                'core/components/toast_oob.html',
                context,
                request=request,
            )
            response.content += oob_html.encode('utf-8')
        return response

    return render(request, 'core/base.html', context, status=status)

