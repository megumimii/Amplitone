"""
Security and File Input Validation for Amplitone.

Why this module exists:
1. Never trust client-supplied filenames or MIME types alone.
2. Validate both file extensions, MIME types, file sizes, AND binary magic bytes.
3. Reject any file uploaded into a non-file form field (e.g., sending a file payload
   inside a 'title', 'name', or 'bio' field).
"""

import os
from django import forms
from django.core.exceptions import ValidationError

# Maximum allowed upload sizes
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024   # 5 MB
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_IMAGE_MIMES = {'image/jpeg', 'image/png', 'image/webp'}

ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.m4a'}
ALLOWED_AUDIO_MIMES = {
    'audio/mpeg',
    'audio/mp3',
    'audio/wav',
    'audio/x-wav',
    'audio/wave',
    'audio/ogg',
    'audio/flac',
    'audio/x-flac',
    'audio/mp4',
    'audio/x-m4a',
}


def validate_image_file(uploaded_file):
    """
    Validates that an uploaded file is a genuine, safe image (JPEG, PNG, or WebP).
    Checks extension, size, MIME type, and binary magic header bytes.
    """
    if not uploaded_file:
        return

    # 1. Check file extension
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Unsupported image extension '{ext}'. Allowed: JPG, PNG, WEBP."
        )

    # 2. Check file size
    if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError("Image file size cannot exceed 5 MB.")

    # 3. Check MIME type if provided by the HTTP upload
    content_type = getattr(uploaded_file, 'content_type', None)
    if content_type and content_type not in ALLOWED_IMAGE_MIMES:
        raise ValidationError(
            f"Invalid image content type '{content_type}'."
        )

    # 4. Inspect binary magic bytes to prevent renamed scripts/executables
    header = uploaded_file.read(16)
    uploaded_file.seek(0)

    is_png = header.startswith(b'\x89PNG\r\n\x1a\n')
    is_jpeg = header.startswith(b'\xff\xd8\xff')
    is_webp = header.startswith(b'RIFF') and header[8:12] == b'WEBP'

    if not (is_png or is_jpeg or is_webp):
        raise ValidationError(
            "File header does not match a valid PNG, JPEG, or WebP image."
        )


def validate_audio_file(uploaded_file):
    """
    Validates that an uploaded file is a genuine audio file (MP3, WAV, OGG, FLAC, M4A).
    Checks extension, size, MIME type, and binary magic header bytes.
    """
    if not uploaded_file:
        return

    # 1. Check file extension
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise ValidationError(
            f"Unsupported audio extension '{ext}'. Allowed: MP3, WAV, OGG, FLAC, M4A."
        )

    # 2. Check file size
    if uploaded_file.size > MAX_AUDIO_SIZE_BYTES:
        raise ValidationError("Audio file size cannot exceed 25 MB.")

    # 3. Check MIME type if provided by the HTTP upload
    content_type = getattr(uploaded_file, 'content_type', None)
    if content_type and content_type not in ALLOWED_AUDIO_MIMES:
        raise ValidationError(
            f"Invalid audio content type '{content_type}'."
        )

    # 4. Inspect binary magic bytes
    header = uploaded_file.read(12)
    uploaded_file.seek(0)

    is_mp3_id3 = header.startswith(b'ID3')
    is_mp3_sync = len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0
    is_wav = header.startswith(b'RIFF') and header[8:12] == b'WAVE'
    is_ogg = header.startswith(b'OggS')
    is_flac = header.startswith(b'fLaC')
    is_m4a = len(header) >= 8 and header[4:8] == b'ftyp'

    if not (is_mp3_id3 or is_mp3_sync or is_wav or is_ogg or is_flac or is_m4a):
        raise ValidationError(
            "File binary header is not a valid MP3, WAV, OGG, FLAC, or M4A audio stream."
        )


def extract_audio_duration(uploaded_file):
    """
    Attempts to derive the playback duration in seconds directly from the audio file
    using Python's standard library.
    Returns integer seconds if detectable, or None.
    """
    if not uploaded_file:
        return None

    # Try WAV extraction with standard library 'wave'
    try:
        import wave
        uploaded_file.seek(0)
        with wave.open(uploaded_file, 'rb') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            if rate > 0:
                return max(1, round(frames / float(rate)))
    except Exception:
        pass
    finally:
        uploaded_file.seek(0)

    # Return None for complex stream encodings without crashing;
    # caller can use client-derived duration or fallback.
    return None


class StrictFileSecurityFormMixin:
    """
    Mixin for Django Forms & ModelForms that rejects any file uploaded into a
    non-file field (or any file uploaded to a form that has no FileFields).

    How it works:
    - Inspects `self.fields` to find which fields are actually `forms.FileField`.
    - Also checks if any text/non-file key in `self.data` was sent as an uploaded file
      inside `self.files`.
    - Raises a ValidationError immediately if an unexpected file field is present.
    """

    def clean(self):
        cleaned_data = super().clean()

        # Identify which fields on this form are legitimately FileFields
        declared_file_fields = {
            field_name
            for field_name, field_obj in self.fields.items()
            if isinstance(field_obj, forms.FileField)
        }

        # Check every key in request.FILES (bound to self.files)
        for uploaded_key in self.files.keys():
            if uploaded_key not in declared_file_fields:
                raise ValidationError(
                    f"Security error: File upload rejected for non-file field '{uploaded_key}'."
                )

        return cleaned_data

