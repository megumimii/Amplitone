"""
Authentication and Profile Forms for the Accounts app.

All forms inherit from `StrictFileSecurityFormMixin` so that any attempt to
upload files to these text-only forms is immediately rejected.
"""

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from core.validators import StrictFileSecurityFormMixin, validate_image_file
from .models import UserProfile
from .utils import ADMIN_EMAIL, ADMIN_USERNAME, get_or_create_user_artist


class UserRegistrationForm(StrictFileSecurityFormMixin, UserCreationForm):
    """
    Form for registering a new standard user account.
    Automatically creates a linked Artist profile so the user can upload their
    own albums and tracks immediately.
    """

    email = forms.EmailField(required=True, help_text="Required for account login & recovery.")
    first_name = forms.CharField(max_length=150, required=False, label="Display / Artist Name")
    last_name = forms.CharField(max_length=150, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if email == ADMIN_EMAIL:
            raise forms.ValidationError("This email address is reserved for the system administrator.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if username.lower() == ADMIN_USERNAME:
            raise forms.ValidationError("This username is reserved for the system administrator.")
        return username

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            get_or_create_user_artist(user)
        return user


class UserLoginForm(StrictFileSecurityFormMixin, AuthenticationForm):
    """
    Form for authenticating an existing user by EITHER Email (e.g. admin@gmail.com)
    OR Username.
    """

    username = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(
            attrs={'placeholder': 'Enter email (e.g. admin@gmail.com) or username', 'autofocus': True}
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password'})
    )

    def clean(self):
        # First run StrictFileSecurityFormMixin file check
        declared_file_fields = {
            name for name, field in self.fields.items() if isinstance(field, forms.FileField)
        }
        for uploaded_key in self.files.keys():
            if uploaded_key not in declared_file_fields:
                raise forms.ValidationError(
                    f"Security error: File upload rejected for non-file field '{uploaded_key}'."
                )

        identifier = self.cleaned_data.get('username', '').strip()
        password = self.cleaned_data.get('password')

        if identifier and password:
            # Allow logging in with Email (such as admin@gmail.com) or Username
            matched_user = (
                User.objects.filter(email__iexact=identifier).first()
                or User.objects.filter(username__iexact=identifier).first()
            )
            auth_username = matched_user.username if matched_user else identifier

            self.user_cache = authenticate(
                self.request,
                username=auth_username,
                password=password,
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class UserProfileForm(StrictFileSecurityFormMixin, forms.ModelForm):
    """
    Form allowing a logged-in user to update their profile details and upload
    a profile picture (`profile_picture`).
    """

    profile_picture = forms.FileField(
        required=False,
        label="Profile Picture",
        validators=[validate_image_file],
        widget=forms.FileInput(attrs={'accept': 'image/*,.jpg,.jpeg,.png,.webp'}),
        help_text="Upload a square JPG, PNG, or WEBP profile photo (max 5 MB).",
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            uploaded_avatar = self.cleaned_data.get('profile_picture')
            if uploaded_avatar:
                profile.avatar = uploaded_avatar
                profile.save()
        return user

