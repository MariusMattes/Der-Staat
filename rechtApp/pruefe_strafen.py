from django.core.management.base import BaseCommand
from views import pruefe_abgelaufene_strafen

class Command(BaseCommand):
    def handle(self, *args, **options):
        pruefe_abgelaufene_strafen()
