import core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('artists', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Album',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('cover', models.FileField(blank=True, help_text='Album cover image (JPG, PNG, or WEBP, max 5 MB).', null=True, upload_to='albums/covers/', validators=[core.validators.validate_image_file])),
                ('release_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('artist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='albums', to='artists.artist')),
            ],
            options={
                'ordering': ['-release_date', 'title'],
            },
        ),
        migrations.CreateModel(
            name='Track',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('audio_file', models.FileField(blank=True, help_text='Audio file (MP3, WAV, OGG, FLAC, or M4A, max 25 MB).', null=True, upload_to='tracks/audio/', validators=[core.validators.validate_audio_file])),
                ('duration_seconds', models.PositiveIntegerField(default=195, help_text='Duration in seconds (e.g. 225 for 3:45).')),
                ('track_number', models.PositiveIntegerField(default=1)),
                ('plays_count', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('album', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tracks', to='catalog.album')),
            ],
            options={
                'ordering': ['track_number', 'id'],
            },
        ),
    ]

