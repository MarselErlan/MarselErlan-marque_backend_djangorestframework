from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alter_address_country'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='profile_image_url',
            new_name='profile_image',
        ),
        migrations.AlterField(
            model_name='user',
            name='profile_image',
            field=models.ImageField(blank=True, null=True, upload_to='users/profile_images/'),
        ),
        migrations.RenameField(
            model_name='user',
            old_name='market',
            new_name='location',
        ),
    ]

