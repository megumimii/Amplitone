"""
Forms for the Artists app.

Every Artist has their own linked Django `User` account.
When an Administrator creates an Artist, `ArtistCreateForm` provisions both
the Artist's `User` credentials and their `Artist` catalog profile atomically.
"""

from django import forms
from django.contrib.auth.models import User
from django.db import transaction

from core.validators import StrictFileSecurityFormMixin, validate_image_file
from .models import Artist


class ArtistCreateForm(StrictFileSecurityFormMixin, forms.ModelForm):
    """
    Admin-only form that creates both a dedicated Django User account
    for the artist and their Artist profile.
    """

    account_username = forms.CharField(
        max_length=150,
        label="Artist Account Username",
        help_text="Dedicated login username for this artist's account.",
    )
    account_email = forms.EmailField(
        required=False,
        label="Artist Account Email",
    )
    account_password = forms.CharField(
        widget=forms.PasswordInput,
        min_length=8,
        label="Artist Account Password",
        help_text="Minimum 8 characters.",
    )
    image = forms.FileField(
        required=False,
        validators=[validate_image_file],
        widget=forms.FileInput(attrs={
            'accept': 'image/*,.jpg,.jpeg,.png,.webp',
            'data-preview-image': 'true',
            'id': 'id_artist_image_create',
        }),
        help_text="Upload JPG, PNG, or WEBP portrait (max 5 MB).",
    )

    class Meta:
        model = Artist
        fields = ('name', 'bio', 'image')

    def clean_account_username(self):
        username = self.cleaned_data['account_username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user account with this username already exists.")
        return username

    @transaction.atomic
    def save(self, commit=True):
        artist_user = User.objects.create_user(
            username=self.cleaned_data['account_username'],
            email=self.cleaned_data.get('account_email', ''),
            password=self.cleaned_data['account_password'],
        )
        artist = super().save(commit=False)
        artist.user = artist_user
        if commit:
            artist.save()
        return artist


class ArtistUpdateForm(StrictFileSecurityFormMixin, forms.ModelForm):
    """Admin-only form for updating an existing Artist's profile and account email."""

    account_email = forms.EmailField(
        required=False,
        label="Artist Account Email",
    )
    image = forms.FileField(
        required=False,
        validators=[validate_image_file],
        widget=forms.FileInput(attrs={
            'accept': 'image/*,.jpg,.jpeg,.png,.webp',
            'data-preview-image': 'true',
            'id': 'id_artist_image_update',
        }),
        help_text="Upload a new JPG, PNG, or WEBP portrait to replace the current one.",
    )

    class Meta:
        model = Artist
        fields = ('name', 'bio', 'image')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.user_id:
            self.fields['account_email'].initial = self.instance.user.email

    @transaction.atomic
    def save(self, commit=True):
        artist = super().save(commit=commit)
        if commit and artist.user_id:
            artist.user.email = self.cleaned_data.get('account_email', '')
            artist.user.save(update_fields=['email'])
        return artist

