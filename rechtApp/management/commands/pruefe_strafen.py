from django.core.management.base import BaseCommand
from rechtApp.views import pruefe_abgelaufene_strafen

class Command(BaseCommand):
    def handle(self):
        pruefe_abgelaufene_strafen()
