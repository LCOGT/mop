from django.core.management.base import BaseCommand
from tom_targets.models import Target
from mop.brokers import gaia as gaia_mop
from astropy import units as u
from astropy.coordinates import SkyCoord
from mop.toolbox import TAP, utilities

class Command(BaseCommand):

    help = 'Compute galactic coordinates l and b for all targets'

    def add_arguments(self, parser):
        parser.add_argument('target_name', help='name of the event to compute errors')

    def handle(self, *args, **options):

        if str(options['target_name']).lower() == 'all':
            qs = Target.objects.all()
        else:
            qs = Target.objects.filter(name=options['target_name'])

        for target in qs:
            try:
                utilities.add_gal_coords(target)
                print('Set galactic coordinates for ' + target.name)
            except:
                print('Problem setting galactic coordinates for ' + target.name)
