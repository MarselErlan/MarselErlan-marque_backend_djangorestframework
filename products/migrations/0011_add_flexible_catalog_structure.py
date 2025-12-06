# Generated manually for flexible catalog structure

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0010_alter_category_icon_alter_category_image'),
    ]

    operations = [
        # Add parent_subcategory to Subcategory for 2-level subcategory hierarchy
        migrations.AddField(
            model_name='subcategory',
            name='parent_subcategory',
            field=models.ForeignKey(
                blank=True,
                help_text='Parent subcategory for 3-level catalog structure. If set, this is a second-level subcategory.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='child_subcategories',
                to='products.subcategory'
            ),
        ),
        # Add second_subcategory to Product for 3-level catalog
        migrations.AddField(
            model_name='product',
            name='second_subcategory',
            field=models.ForeignKey(
                blank=True,
                help_text='Second-level subcategory. Required only for level 3 catalog.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='second_level_products',
                to='products.subcategory'
            ),
        ),
        # Update unique_together constraint for Subcategory
        migrations.AlterUniqueTogether(
            name='subcategory',
            unique_together={
                ('category', 'slug'),
                ('parent_subcategory', 'slug')
            },
        ),
        # Add index for subcategory hierarchy
        migrations.AddIndex(
            model_name='subcategory',
            index=models.Index(fields=['category', 'parent_subcategory', 'is_active'], name='subcategori_categor_idx'),
        ),
        # Add index for product catalog structure
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category', 'subcategory', 'second_subcategory'], name='products_categor_idx'),
        ),
    ]

