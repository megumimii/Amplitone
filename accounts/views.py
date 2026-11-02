"""
Views for User Authentication and Profile Management.

Uses Django's built-in `login`, `logout`, and `@login_required` utilities.
"""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from core.utils import is_htmx, render_page
from .forms import UserLoginForm, UserProfileForm, UserRegistrationForm
from .utils import ensure_single_admin_account, get_or_create_user_artist


def _redirect_with_htmx(request, url):
    """
    Redirects both standard browser requests and HTMX requests cleanly.
    When auth state changes (login/logout/register), a full shell refresh ensures
    the top navbar and left sidebar reflect the new user session.
    """
    if is_htmx(request):
        response = HttpResponse(status=200)
        response['HX-Redirect'] = url
        return response
    return redirect(url)


@require_http_methods(["GET", "POST"])
def register_view(request):
    """Handles new user registration and provisions their Artist profile."""
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Amplitone, {user.username}.")
            return _redirect_with_htmx(request, reverse('core:home'))
    else:
        form = UserRegistrationForm()

    return render_page(request, 'accounts/register.html', {'form': form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Handles user login (supports both email e.g. admin@gmail.com and username)."""
    ensure_single_admin_account()

    if request.user.is_authenticated:
        return redirect('core:home')

    next_url = request.GET.get('next') or request.POST.get('next') or reverse('core:home')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST, files=request.FILES)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if not (user.is_staff or user.is_superuser):
                get_or_create_user_artist(user)
            messages.success(request, f"Signed in as {user.username}.")
            return _redirect_with_htmx(request, next_url)
    else:
        form = UserLoginForm(request)

    return render_page(request, 'accounts/login.html', {
        'form': form,
        'next': next_url,
    })


@require_POST
def logout_view(request):
    """Logs out the current user (strictly requires POST for CSRF safety)."""
    logout(request)
    messages.info(request, "You have been signed out.")
    return _redirect_with_htmx(request, reverse('core:home'))


@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    """Displays and updates the logged-in user's profile page."""
    if not (request.user.is_staff or request.user.is_superuser):
        get_or_create_user_artist(request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return render_page(request, 'accounts/profile.html', {'form': form})
    else:
        form = UserProfileForm(instance=request.user)

    return render_page(request, 'accounts/profile.html', {'form': form})
