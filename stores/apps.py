from django.apps import AppConfig


class StoresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stores'
    
    def ready(self):
        """Import admin configuration when app is ready."""
        try:
            import stores.admin_config  # noqa: F401
        except ImportError:
            pass