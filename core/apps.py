from django.apps import AppConfig

class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from .utils.db_init import ensure_database_exists
        ensure_database_exists()
