"""
Custom Permission Decorators for Amplitone.

Provides a clean, readable `@admin_required` decorator used by the `artists` app
to restrict Artist CRUD operations strictly to Administrator accounts.
"""

from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """
    Ensures the user is logged in AND is an administrator (`is_staff` or `is_superuser`).
    - Unauthenticated users are redirected to the Login page.
    - Logged-in non-admin users receive a 403 PermissionDenied response.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied("Administrator privileges are required for Artist CRUD.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view

