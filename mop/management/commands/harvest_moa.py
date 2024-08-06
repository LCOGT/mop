from django.core.management.base import BaseCommand
from mop.brokers import moa
from mop.brokers import gaia as gaia_mop
from mop.toolbox import utilities
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Downloads MOA data for all events for a given years list'

    def add_arguments(self, parser):
        parser.add_argument('years', help='years you want to harvest, separated by ,')

    def handle(self, *args, **options):
        
        Moa = moa.MOABroker()
        (list_of_targets, new_targets) = Moa.fetch_alerts('./data/',[options['years']])
        logger.info('MOA HARVESTER: Found '+str(len(list_of_targets))+' targets')

        utilities.open_targets_to_OMEGA_team(list_of_targets)

        Moa.find_and_ingest_photometry(list_of_targets, [options['years']])
        logger.info('MOA HARVESTER: Ingested photometry for MOA targets')

        for target in new_targets:
            gaia_mop.fetch_gaia_dr3_entry(target)
        logger.info('MOA HARVESTER: Retrieved Gaia photometry for MOA targets')
