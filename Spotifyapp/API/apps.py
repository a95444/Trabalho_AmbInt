# API/apps.py
from django.apps import AppConfig

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'API'

'''    def ready(self):
        """O listener já inicia automaticamente ao importar connect_garmin.py"""
        from . import connect_garmin  # Importe o módulo (já inicia a thread)
        print("Listener do Garmin pronto.")'''