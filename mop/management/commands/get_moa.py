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
        parser.add_argument('out_file', help='Path to output file')

    def handle(self, *args, **options):

        Moa = moa.MOABroker()

        if ',' in options['years']:
            year_list = options['years'].split(',')
        else:
            year_list = [options['years']]

        events = Moa.fetch_alert_params('./data/', year_list)
