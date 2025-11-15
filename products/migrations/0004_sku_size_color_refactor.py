from django.db import migrations, models
import django.db.models.deletion


def copy_legacy_size_color(apps, schema_editor):
    ProductSizeOption = apps.get_model('products', 'ProductSizeOption')
    ProductColorOption = apps.get_model('products', 'ProductColorOption')
    SKU = apps.get_model('products', 'SKU')

    size_cache = {}
    color_cache = {}

    for sku in SKU.objects.all().only('id', 'product_id', 'size', 'color'):
        size_value = (getattr(sku, 'size', '') or '').strip()
        color_value = (getattr(sku, 'color', '') or '').strip()

        size_id = None
        if size_value:
            key = (sku.product_id, size_value)
            size_id = size_cache.get(key)
            if size_id is None:
                size = ProductSizeOption.objects.create(
                    product_id=sku.product_id,
                    name=size_value,
                    sort_order=0,
                    is_active=True,
                )
                size_id = size.id
                size_cache[key] = size_id

        color_id = None
        if size_id and color_value:
            color_key = (sku.product_id, size_id, color_value)
            color_id = color_cache.get(color_key)
            if color_id is None:
                color = ProductColorOption.objects.create(
                    product_id=sku.product_id,
                    size_id=size_id,
                    name=color_value,
                    hex_code='',
                    is_active=True,
                )
                color_id = color.id
                color_cache[color_key] = color_id

        update_fields = []
        if size_id is not None:
            sku.size_option_id = size_id
            update_fields.append('size_option')
        if color_id is not None:
            sku.color_option_id = color_id
            update_fields.append('color_option')
        if update_fields:
            sku.save(update_fields=update_fields)


def noop_reverse(apps, schema_editor):
    # We do not attempt to rebuild the legacy columns when rolling back.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_remove_productimage_image_url_productimage_image_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductSizeOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='size_options', to='products.product')),
            ],
            options={
                'verbose_name': 'Product Size',
                'verbose_name_plural': 'Product Sizes',
                'db_table': 'product_size_options',
                'ordering': ['product', 'sort_order', 'name'],
                'unique_together': {('product', 'name')},
            },
        ),
        migrations.CreateModel(
            name='ProductColorOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('hex_code', models.CharField(blank=True, max_length=7, null=True, help_text='Optional HEX code (#FFFFFF).')),
                ('is_active', models.BooleanField(default=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='color_options', to='products.product')),
                ('size', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='color_options', to='products.productsizeoption')),
            ],
            options={
                'verbose_name': 'Product Color',
                'verbose_name_plural': 'Product Colors',
                'db_table': 'product_color_options',
                'ordering': ['product', 'size__sort_order', 'size__name', 'name'],
                'unique_together': {('product', 'size', 'name')},
            },
        ),
        migrations.AddField(
            model_name='sku',
            name='size_option',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='skus', to='products.productsizeoption'),
        ),
        migrations.AddField(
            model_name='sku',
            name='color_option',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='skus', to='products.productcoloroption'),
        ),
        migrations.AlterModelOptions(
            name='sku',
            options={
                'verbose_name': 'SKU',
                'verbose_name_plural': 'SKUs',
                'db_table': 'skus',
                'ordering': ['product', 'size_option__sort_order', 'size_option__name', 'color_option__name'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='sku',
            unique_together={('product', 'size_option', 'color_option')},
        ),
        migrations.RunPython(copy_legacy_size_color, noop_reverse),
        migrations.RemoveField(
            model_name='sku',
            name='color',
        ),
        migrations.RemoveField(
            model_name='sku',
            name='size',
        ),
    ]
