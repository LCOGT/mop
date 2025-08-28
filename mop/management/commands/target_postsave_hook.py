from django.core.management.base import BaseCommand
from tom_targets.models import Target
from mop.brokers import gaia as gaia_mop
from astropy import units as u
from astropy.coordinates import SkyCoord
from mop.toolbox import TAP, utilities, classifier_tools
from mop.brokers import gaia as gaia_mop

class Command(BaseCommand):

    help = 'Run MOPs custom post-save processes for a target'

    def add_arguments(self, parser):
        parser.add_argument('target_name', help='name of the event to compute errors')

    def handle(self, *args, **options):

        qs = Target.objects.filter(name=options['target_name'])

        for target in qs:
            try:
                utilities.add_gal_coords(target)
                utilities.add_gal_coords(target)
                TAP.set_target_sky_location(target)
                classifier_tools.check_known_variable(target)
                gaia_mop.fetch_gaia_dr3_entry(target)
                utilities.open_targets_to_OMEGA_team([target])
                print('Completed post-save target processes ' + target.name)

            except:
                print('Problem with post-save target processes for ' + target.name)
