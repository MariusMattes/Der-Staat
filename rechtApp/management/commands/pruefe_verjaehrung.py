from django.core.management.base import BaseCommand
from rechtApp.views import pruefe_verjaehrung_vorstrafen

class Command(BaseCommand):
    def handle(self):
        pruefe_verjaehrung_vorstrafen()
