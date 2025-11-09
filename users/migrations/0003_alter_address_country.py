from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_paymentmethod_card_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='country',
            field=models.CharField(choices=[('Kyrgyzstan', 'Kyrgyzstan'), ('United States', 'United States')], default='Kyrgyzstan', max_length=100),
        ),
    ]

