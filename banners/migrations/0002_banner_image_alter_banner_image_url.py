from django.db import migrations, models

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('banners', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='banner',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='banners/'),
        ),
        migrations.AlterField(
            model_name='banner',
            name='image_url',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
