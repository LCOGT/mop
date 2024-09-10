from django.core.management.base import BaseCommand
from tom_targets.models import Target
from mop.brokers import gaia as gaia_mop
from mop.toolbox import utilities
from astropy.coordinates import Angle
import astropy.units as u
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Retrieves Gaia DR3 data for a given event'
    def add_arguments(self, parser):
        parser.add_argument('event', help='name of a specific event, or ALL')

    def handle(self, *args, **options):
        logger.info('Starting run of Gaia DR3 data retrieval')

        if 'ALL' in options['event']:
            target_list = Target.objects.all()
        else:
            qs = Target.objects.filter(name=options['event'])
            if qs.count() > 0:
                target_list = [qs[0]]

        if len(target_list) > 0:
            for j,target in enumerate(target_list):
                gaia_mop.fetch_gaia_dr3_entry(target, radius=Angle(0.00014, "deg"))

                # This alternative async TAP query is EXTREMELY slow
                #gaia_mop.query_gaia_tap_service(target, radius=Angle(0.00014, "deg"), row_limit=-1)

                logger.info('Completed fetch of Gaia DR3 data for ' + target.name
                            + ', ' + str(j) + ' of ' + str(len(target_list)))

        else:
            logger.info('No targets matching the name ' + options['event'] + ' found')