from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_user_profile_image_location'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserPhoneNumber',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(blank=True, max_length=100, null=True)),
                ('phone', models.CharField(max_length=20)),
                ('is_primary', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='phone_numbers', to='users.user')),
            ],
            options={
                'verbose_name': 'Phone Number',
                'verbose_name_plural': 'Phone Numbers',
                'db_table': 'user_phone_numbers',
                'ordering': ['-is_primary', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='userphonenumber',
            index=models.Index(fields=['user', 'phone'], name='user_phone__user_id_68db7c_idx'),
        ),
        migrations.AddIndex(
            model_name='userphonenumber',
            index=models.Index(fields=['user', '-is_primary', '-created_at'], name='user_phone__user_id_7363d9_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='userphonenumber',
            unique_together={('user', 'phone')},
        ),
    ]

