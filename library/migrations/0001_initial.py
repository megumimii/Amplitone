import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('catalog', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Playlist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('description', models.TextField(blank=True)),
                ('is_private', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='playlists', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PlaylistTrack',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveIntegerField(default=1)),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('playlist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='playlist_tracks', to='library.playlist')),
                ('track', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='playlist_entries', to='catalog.track')),
            ],
            options={
                'ordering': ['position', 'added_at'],
                'unique_together': {('playlist', 'track')},
            },
        ),
        migrations.AddField(
            model_name='playlist',
            name='tracks',
            field=models.ManyToManyField(blank=True, related_name='playlists', through='library.PlaylistTrack', to='catalog.track'),
        ),
        migrations.CreateModel(
            name='LikedSong',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('track', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', to='catalog.track')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='liked_songs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('user', 'track')},
            },
        ),
        migrations.CreateModel(
            name='RecentlyPlayed',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('played_at', models.DateTimeField(auto_now=True)),
                ('track', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recent_plays', to='catalog.track')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recently_played', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-played_at'],
                'unique_together': {('user', 'track')},
            },
        ),
    ]

