from django.apps import AppConfig


class TccConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tcc"
    label = 'tcc'
    verbose_name = 'TCC Core'
    
    def ready(self):
        try:
            from apps.tcc.models.base import signals
        except ImportError as e:
            print(f'Warning: Could not import signals: {e}')
        