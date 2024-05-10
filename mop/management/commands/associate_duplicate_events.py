from django.core.management.base import BaseCommand
from tom_targets.models import Target, TargetMatchManager


class Command(BaseCommand):
    help = 'Identify events with multiple Target entries'

    def handle(self, *args, **options):
        targets = Target.objects.all()


