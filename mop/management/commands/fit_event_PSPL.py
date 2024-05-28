from django.core.management.base import BaseCommand
from tom_dataproducts.models import ReducedDatum
from tom_targets.models import Target, TargetExtra
from astropy.time import Time
from mop.toolbox.mop_classes import MicrolensingEvent
from mop.brokers import gaia as gaia_mop

import json
import numpy as np
import datetime
import os
import logging
from mop.management.commands.fit_need_events_PSPL import run_fit
from django.db import connection

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Fit an event with PSPL and parallax, then ingest fit parameters in the db'

    def add_arguments(self, parser):
        parser.add_argument('target_name', help='name of the event to fit')
        parser.add_argument('--cores', help='Number of workers to use', default=os.cpu_count(), type=int)
        parser.add_argument('--stout', help='Direction for standard output',)


    def handle(self, *args, **options):

        tstart = datetime.datetime.utcnow()
        t, created = Target.objects.get_or_create(name= options['target_name'])
        logger.info('Fitting single event: '+t.name)

        try:
            mulens = MicrolensingEvent(t)
            mulens.set_extra_params(TargetExtra.objects.filter(target=t))
            mulens.set_reduced_data(
                ReducedDatum.objects.filter(target=t).order_by("timestamp")
            )

            if len(mulens.red_data) > 0:
                result = run_fit(mulens, cores=options['cores'], verbose=True)

        except:
            logger.warning('Fitting event '+t.name+' hit an exception')

        connection.close()
        tend = datetime.datetime.utcnow()
        logger.info('Total time for single target model fit: ' + str(tend - tstart))
