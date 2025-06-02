# boutiques/apps.py
from django.apps import AppConfig

class BoutiquesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'boutiques'

    def ready(self):
        # Importez vos signaux ici pour qu'ils soient enregistrés au démarrage de l'application
        import boutiques.signals