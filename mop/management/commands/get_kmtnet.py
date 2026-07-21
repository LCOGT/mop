from django.core.management.base import BaseCommand
from mop.brokers import kmtnet

import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Downloads KMTNet event list for a given list of years'
    def add_arguments(self, parser):
        parser.add_argument('years', help='years you want to harvest, separated by ,')
        parser.add_argument('events', help='name of a specific event, all or an integer number')
        parser.add_argument('out_file', help='Path to output file')

    def handle(self, *args, **options):
        logger.info('Starting run of KMTNet event harvester')

        KMT = kmtnet.KMTNetBroker()

        # Parse the list years for which to harvest target data
        if ',' in options['years']:
            year_list = options['years'].split(',')
        else:
            year_list = [options['years']]

        # Read the lists of events for the given years
        kmt_events = KMT.fetch_all_parameters(year_list)

        # Output to text file
        with open(options['out_file'], 'w') as f:
            f.write('# Name  RA   Dec  t0[HJD]  tE[days]    u0    Ibase    Ibase_err\n')

            for name, params in kmt_events.items():
                f.write(name + ' ' + ' '.join(params) + '\n')
