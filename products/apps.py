from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'
    
    def ready(self):
        """Import admin configuration when app is ready."""
        try:
            import products.admin_config  # noqa: F401
        except ImportError:
            pass