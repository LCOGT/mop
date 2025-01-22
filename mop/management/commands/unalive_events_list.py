from django.core.management.base import BaseCommand
from tom_targets.models import Target

class Command(BaseCommand):
    """
    Command to unalive events with target names provided in a list as a command line argument
    """

    help = 'Command to unalive events with target names provided in a list as a command line argument'

    def add_arguments(self, parser):

        parser.add_argument('target_list', help='List of events to unalive')


    def handle(self, *args, **options):

        targets_to_unalive = options['target_list'].split(',')

        for target_name in targets_to_unalive:
            t, created = Target.objects.get_or_create(name=target_name)
            print('Target ' + str(t.pk) + ' ' + t.name + ' has status=' + repr(t.alive))
            t.alive = False
            t.save()
            print('Target ' + str(t.pk) + ' ' + t.name + ' now has status=' + repr(t.alive))