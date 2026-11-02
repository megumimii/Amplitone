import core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Artist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('bio', models.TextField(blank=True, help_text='Artist biography and editorial notes.')),
                ('image', models.FileField(blank=True, help_text='Square portrait image (JPG, PNG, or WEBP, max 5 MB).', null=True, upload_to='artists/images/', validators=[core.validators.validate_image_file])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(help_text='The dedicated user account owned by this artist.', on_delete=django.db.models.deletion.CASCADE, related_name='artist_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
    ]

