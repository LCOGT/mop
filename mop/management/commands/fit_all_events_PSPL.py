from django.core.management.base import BaseCommand
from django.db import transaction
from tom_targets.models import Target
from tom_dataproducts.models import ReducedDatum
from mop.management.commands.fit_need_events_PSPL import run_fit

import logging

logger = logging.getLogger(__name__)



class Command(BaseCommand):

    help = 'Fit a specific selection of events with PSPL and parallax, then ingest fit parameters in the db'

    def add_arguments(self, parser):

        parser.add_argument('name_search_term', help='Search term to use for selecting events by name')

    def handle(self, *args, **options):

        logger.info('FIT_ALL_EVENTS: Running fit_all_events_PSPL')

        # Create a QuerySet which allows us to lock DB rows to avoid clashes
        target_list = Target.objects.filter(
            name__icontains=options['name_search_term'],
            classification__icontains='Microlensing'
        )

        logger.info('FIT_ALL_EVENTS: Found ' + str(target_list.count()) + ' targets to fit')

        datums = ReducedDatum.objects.filter(target__in=target_list).order_by("timestamp")
        logger.info('FIT_ALL_EVENTS: Retrieved photometry for selected targets')

        for i,mulens in enumerate(target_list):
            logger.info('FIT_ALL_EVENTS: Fitting data for ' + mulens.name + ', '
                        + str(i) + ' out of ' + str(target_list.count()))
            mulens.get_reduced_data(datums.filter(target=mulens))

            try:
                result = run_fit(mulens)

                logger.info('FIT_ALL_EVENTS: Completed modeling of ' + mulens.name)
            except:
                logger.warning('FIT_ALL_EVENTS: Fitting event ' + mulens.name + ' hit an exception')

        logger.info('FIT_ALL_EVENTS: Finished modeling set of targets')