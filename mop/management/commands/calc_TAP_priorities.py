from django.core.management.base import BaseCommand
from tom_targets.models import Target
import datetime
from astropy.time import Time, TimeDelta
from astropy import units as u
from mop.toolbox import TAP_priority, querytools
import numpy as np
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Calculate the current TAP priority for user-selected events'

    def add_arguments(self, parser):

        parser.add_argument('targets', help='Search term of the event selection to calculate priorities for or all')

    def handle(self, *args, **options):
        if 'all' in options['targets']:
            qs = Target.objects.all()
        else:
            qs = Target.objects.filter(name__icontains=options['targets'])
            target_list = list(set(qs))
            target_data = querytools.fetch_data_for_targetset(target_list, check_need_to_fit=False)
            nalive = str(len(target_data))

            for k, (event, mulens) in enumerate(target_data.items()):
                logger.info('Analyzing event ' + mulens.name + ', ' + str(k) + ' out of ' + nalive)

                time_now = Time(datetime.datetime.now()).jd
                covariance = mulens.load_fit_covariance()
                t_last = mulens.last_observation
                if not t_last:
                    t_last = Time.now().jd - TimeDelta(30.0*24.0*60.0*60.0*u.s)

                planet_priority = TAP_priority.TAP_planet_priority(time_now, mulens.t0, mulens.u0, mulens.tE)
                planet_priority_error = TAP_priority.TAP_planet_priority_error(
                    time_now, mulens.t0, mulens.u0, mulens.tE, covariance
                )
                logger.info(' -> Planet priority: ' + str(planet_priority) + ', ' + str(planet_priority_error))

                long_priority = TAP_priority.TAP_long_event_priority(time_now, t_last, mulens.tE)
                long_priority_error = TAP_priority.TAP_long_event_priority_error(mulens.tE, covariance)
                logger.info(' -> Long tE priority: ' + str(long_priority) + ' ' + str(long_priority_error))

                update_extras = {'tap_priority': np.around(planet_priority, 5),
                                 'tap_priority_error': np.around(planet_priority_error, 5),
                                 'tap_priority_longte': np.around(long_priority, 5),
                                 'tap_priority_longte_error': np.around(long_priority_error, 5)}
                mulens.store_parameter_set(update_extras)
                logger.info(' -> Completed TAP calculations for ' + mulens.name)
