from django.apps import AppConfig


class ComicsDbConfig(AppConfig):
    name = 'comics_db'

    def ready(self):
        import comics_db.signals
