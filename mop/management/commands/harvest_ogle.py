from django.core.management.base import BaseCommand
from mop.brokers import ogle
from mop.brokers import gaia as gaia_mop
from mop.toolbox import utilities
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Downloads OGLE data for all events for a given years list'
    def add_arguments(self, parser):
        parser.add_argument('years', help='years you want to harvest, separated by ,')
        parser.add_argument('events', help='name of a specific event, all or an integer number')
        parser.add_argument('--phot', help='Force ingest of full photometry [optional]: True or False')

    def handle(self, *args, **options):
        logger.info('Starting run of OGLE event harvester')

        Ogle = ogle.OGLEBroker()

        # Parse the years for which to harvest target data, since this could be a single
        # integer or a list:
        if ',' in options['years']:
            year_list = options['years'].split(',')
        else:
            year_list = [options['years']]
        full_phot = False
        if options['phot']:
            full_phot = True

        # If a number of events to select is given, make a list of all available events;
        # the random selection is applied later.  If a specific event name is given, fetch data for that event only
        (list_of_targets, new_targets) = Ogle.fetch_alerts(years=year_list, events=str(options['events']))
        logger.info('Identified and ingested '+str(len(list_of_targets))+' target(s) from OGLE survey')

        # For the new targets, set the permissions such that all OMEGA team members can see them
        utilities.open_targets_to_OMEGA_team(list_of_targets)

        # The following random selection is made to avoid the harvesting process taking so long
        # that the Kubernetes pod times out.  By randomizing the target selection, we ensure
        # that all targets should be updated quite often through more frequent runs of this harvester
        if str(options['events']).isnumeric():
            selected_targets = Ogle.select_random_targets(list_of_targets, new_targets, ntargets=int(options['events']))
            logger.info('Ingesting data from '+str(len(selected_targets))+' randomly-selected targets')
        else:
            selected_targets = Ogle.sort_target_list(list_of_targets)
            logger.info('Ingesting data from '+str(len(selected_targets))+' selected targets')

        Ogle.find_and_ingest_photometry(selected_targets, full_phot=full_phot)

        logger.info('Harvesting Gaia photometry for new OGLE targets')
        for target in new_targets:
            gaia_mop.fetch_gaia_dr3_entry(target)

        logger.info('Completed run of OGLE event harvester')


   
