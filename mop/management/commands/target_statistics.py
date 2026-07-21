from django.core.management.base import BaseCommand
from tom_targets.models import Target, TargetName
from astropy.time import Time
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Calculate statistics on the number of targets'

    def add_arguments(self, parser):

        parser.add_argument('parameter', help='Name of the parameter to filter on')
        parser.add_argument('par_min', help='Minimum value of the parameter')
        parser.add_argument('par_max', help='Maximum value of the parameter')

    def handle(self, *args, **options):

        # Query the DB for all targets matching the selection criteria
        if options['parameter'] == 'tE':
            for iyr in range(2021, 2024, 1):
                year = str(iyr)
                tstart = datetime.strptime(year+'-01-01', '%Y-%m-%d')
                dt = timedelta(days=365.24)
                tend = tstart + dt
                t0 = Time(tstart, format='datetime')
                t1 = Time(tend, format='datetime')

                targets = Target.objects.filter(
                    t0__range=(t0.jd, t1.jd),
                    tE__range=(options['par_min'], options['par_max'])
                )

                logger.info('Identified ' + str(targets.count())
                            + ' targets within tE range in ' + year)


