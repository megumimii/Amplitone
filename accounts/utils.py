"""
Account & Role Utilities for Amplitone.

Enforces:
1. A single built-in Administrator account (`admin@gmail.com` / `0913admin`).
2. Automatic 1-to-1 `Artist` profile provisioning for every Standard User so they
   can create their own albums and tracks.
"""

from django.contrib.auth.models import User
from artists.models import Artist

ADMIN_EMAIL = 'admin@gmail.com'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '0913admin'


def ensure_single_admin_account():
    """
    Ensures the single Administrator account (`admin@gmail.com` / `0913admin`) exists
    and revokes staff/superuser flags from any other account.
    """
    admin_user = (
        User.objects.filter(email__iexact=ADMIN_EMAIL).first()
        or User.objects.filter(username__iexact=ADMIN_USERNAME).first()
    )

    if admin_user is None:
        admin_user = User.objects.create_user(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
            is_staff=True,
            is_superuser=True,
        )
    else:
        changed = False
        if admin_user.email != ADMIN_EMAIL:
            admin_user.email = ADMIN_EMAIL
            changed = True
        if not admin_user.is_staff or not admin_user.is_superuser:
            admin_user.is_staff = True
            admin_user.is_superuser = True
            changed = True
        if not admin_user.check_password(ADMIN_PASSWORD):
            admin_user.set_password(ADMIN_PASSWORD)
            changed = True
        if changed:
            admin_user.save()

    # Ensure no other account holds admin privileges
    User.objects.exclude(pk=admin_user.pk).filter(
        is_staff=True
    ).update(is_staff=False, is_superuser=False)

    return admin_user


def get_or_create_user_artist(user):
    """
    Returns (or creates) the 1-to-1 Artist profile for a given User so standard
    users can publish their own albums and tracks.
    """
    if not user or not user.is_authenticated:
        return None

    artist = Artist.objects.filter(user=user).first()
    if artist:
        return artist

    base_name = (user.get_full_name() or user.username).strip()
    candidate_name = base_name
    suffix = 2
    while Artist.objects.filter(name__iexact=candidate_name).exists():
        candidate_name = f"{base_name} ({suffix})"
        suffix += 1

    return Artist.objects.create(
        user=user,
        name=candidate_name,
        bio=f"Official artist profile for @{user.username}.",
    )

