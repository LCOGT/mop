from django.core.management.base import BaseCommand
from tom_targets.models import Target
from astropy import units as u
from astropy.coordinates import SkyCoord
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Calculate statistics on the number of targets'

    def add_arguments(self, parser):

        parser.add_argument('parameter', help='Name of the parameter to filter on')
        parser.add_argument('par_min', help='Minimum value of the parameter')
        parser.add_argument('par_max', help='Maximum value of the parameter')

    def handle(self, *args, **options):

        # Query the DB for all targets matching the selection criteria
        if options['parameter'] == 'tE':
            targets = Target.objects.filter(
                tE__range(option['par_min'], option['par_max'])
            )

            logger.info('Identified ' + str(targets.count()) + ' targets within tE range')
