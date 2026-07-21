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
        parser.add_argument('out_file', help='Path to output file')

    def handle(self, *args, **options):
        logger.info('Starting run of OGLE event harvester')

        Ogle = ogle.OGLEBroker()

        # Parse the years for which to harvest target data, since this could be a single
        # integer or a list:
        if ',' in options['years']:
            year_list = options['years'].split(',')
        else:
            year_list = [options['years']]

        # Read the lists of events for the given years
        ogle_events = Ogle.fetch_all_parameters(year_list)

        # Output to text file
        with open(options['out_file'], 'w') as f:
            f.write('# Name  RA   Dec  t0[HJD]  tE[days]    u0    Ibase    Ibase_err\n')

            for name, params in ogle_events.items():
                f.write(name + ' ' + ' '.join(params) + '\n')
