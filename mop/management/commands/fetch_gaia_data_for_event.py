from django.core.management.base import BaseCommand
from tom_targets.models import Target
from mop.brokers import gaia as gaia_mop
from mop.toolbox import utilities
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Retrieves Gaia DR3 data for a given event'
    def add_arguments(self, parser):
        parser.add_argument('event', help='name of a specific event, all or an integer number')

    def handle(self, *args, **options):
        logger.info('Starting run of Gaia DR3 data retrieval')

        qs = Target.objects.filter(name=options['event'])

        if qs.count() > 0:
            target = qs[0]
            gaia_mop.fetch_gaia_dr3_entry(target)

            logger.info('Completed fetch of Gaia DR3 data for ' + options['event'])

        else:
            logger.info('No targets matching the name ' + options['event'] + ' found')