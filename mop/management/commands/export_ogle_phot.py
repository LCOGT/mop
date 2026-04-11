from django.core.management.base import BaseCommand
from mop.toolbox import utilities
import logging
from tom_targets.models import Target, TargetName, TargetList
from tom_dataproducts.models import ReducedDatum
from django.db.models import Q
import pandas as pd
from os import path

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Downloads OGLE data for all events for a given years list'
    def add_arguments(self, parser):
        parser.add_argument('years', help='years you want to harvest, separated by ,')
        parser.add_argument('events', help='name of a specific event, all or an integer number')
        parser.add_argument('data_dir', help='Path to output files')

    def handle(self, *args, **options):
        logger.info('Starting extraction of OGLE data')

        # Parse the years for which to harvest target data, since this could be a single
        # integer or a list:
        if ',' in options['years']:
            year_list = options['years'].split(',')
        else:
            year_list = [options['years']]

        # Read the lists of events for the given years
        for i,yr in enumerate(year_list):
            qs = Target.objects.filter(
                Q(name__icontains='OGLE-'+str(yr)) | Q(aliases__name__icontains='OGLE-'+str(yr))
            )
            if i == 0:
                ogle_events = qs
            else:
                ogle_events = ogle_events | qs

        # Extract dataums for the whole list
        datums = ReducedDatum.objects.filter(target__in=ogle_events).order_by("timestamp")

        # Output to text file
        for mulens in ogle_events:
            mulens.get_reduced_data(datums.filter(target=mulens))

            df = pd.DataFrame(mulens.datasets['OGLE_I'], columns=['time', 'magnitude', 'error'])
            df.insert(1, 'filter', ['OGLE-I']*len(df))

            df.to_csv(path.join(options['data_dir'], mulens.name + '_OGLE-I.csv'), index=False)
            logger.info('Exported lightcurve for ' + mulens.name)
