from os import path
from django.core.management.base import BaseCommand
from mop.brokers import ogle
from mop.brokers import gaia as gaia_mop
from mop.toolbox import utilities
from mop.toolbox import fileutils
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Downloads OGLE timeseries data for all events for a given years list'
    def add_arguments(self, parser):
        parser.add_argument('years', help='years you want to harvest, separated by ,')
        parser.add_argument('events', help='name of a specific event, all or an integer number')
        parser.add_argument('data_dir', help='Path to output data directory')

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

        # Filter_id is the label used by MOP to identify different datasets in plots
        # The phot.dat files provided for each event by default contain just the I-band data
        filter_id = 'OGLE-I'

        # Download the photometry files and convert them into MOP-compatible format
        for ogle_name, params in ogle_events.items():
            lc_file_path = path.join(options['data_dir'], ogle_name + '_phot.dat')
            mop_file_path = lc_file_path.replace('_phot.dat', '.csv')

            Ogle.download_ogle_lightcurve(ogle_name, lc_file_path)

            ogle_data = fileutils.load_ogle_lc(lc_file_path, filter_id)

            fileutils.ogle_to_mop_format(ogle_data, mop_file_path)