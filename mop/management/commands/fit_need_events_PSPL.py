from django.core.management.base import BaseCommand
from tom_dataproducts.models import ReducedDatum
from tom_targets.models import Target,TargetExtra
from django.db import transaction
from astropy.time import Time
from mop.toolbox import fittools, utilities, querytools
from mop.toolbox.mop_classes import MicrolensingEvent
import datetime
import os
import logging

logger = logging.getLogger(__name__)

from django.db import connection

def run_fit(mulens, cores=0, verbose=False):
    """
    Function to perform a microlensing model fit to timeseries photometry.

    Parameters:
        target   Target object
        red_data QuerySet of ReducedDatums for the target
        cores integer, optional number of processing cores to use
    """

    logger.info('Fitting event: '+mulens.name)

    t5 = datetime.datetime.utcnow()
    if verbose: utilities.checkpoint()

    try:
        t6 = datetime.datetime.utcnow()
        if verbose: utilities.checkpoint()
        if verbose: logger.info('Time taken chk 2: ' + str(t6 - t5))

        # Retrieve all available ReducedDatum entries for this target.  Note that this may include data
        # other than lightcurve photometry, so the data are then filtered and repackaged for later
        # convenience
        logger.info('FIT: Found '+str(len(mulens.datasets))+' datasets and a total of '
                    +str(mulens.ndata)+' datapoints to model for event '+mulens.name)

        t7 = datetime.datetime.utcnow()
        if verbose: utilities.checkpoint()
        if verbose: logger.info('Time taken chk 3: ' + str(t7 - t6))

        if mulens.ndata > 10:
            (model_params, model_telescope) = fittools.fit_pspl_omega2(
                mulens.ra, mulens.dec, mulens.datasets)
            logger.info('FIT: completed modeling process for '+mulens.name)

            t8 = datetime.datetime.utcnow()
            if verbose: utilities.checkpoint()
            if verbose: logger.info('Time taken chk 4: ' + str(t8 - t7))

            # Store model lightcurve
            if model_telescope:
                fittools.store_model_lightcurve(mulens, model_telescope)
                logger.info('FIT: Stored model lightcurve for event '+mulens.name)
            else:
                logger.warning('FIT: No valid model fit produced so not model lightcurve for event '+mulens.name)

            t9 = datetime.datetime.utcnow()
            if verbose: utilities.checkpoint()
            if verbose: logger.info('Time taken chk 5: ' + str(t9 - t8))

            # Determine whether or not an event is still active based on the
            # current time relative to its t0 and tE
            alive = fittools.check_event_alive(model_params['t0'], model_params['tE'], mulens.last_observation)

            t10 = datetime.datetime.utcnow()
            if verbose: utilities.checkpoint()
            if verbose: logger.info('Time taken chk 6: ' + str(t10 - t9))

            # Store model parameters
            model_params['last_fit'] = Time(datetime.datetime.utcnow()).jd
            model_params['alive'] = alive
            mulens.store_model_parameters(model_params)
            logger.info('FIT: Stored model parameters for event ' + mulens.name)

            t11 = datetime.datetime.utcnow()
            if verbose: utilities.checkpoint()
            if verbose: logger.info('Time taken chk 6: ' + str(t11 - t10))

        else:
            logger.info('Insufficient lightcurve data available to model event '+mulens.name)

            # Determine whether or not an event is still active based on the
            # current time relative to its t0 and tE, and the date it was last observed
            alive = fittools.check_event_alive(float(mulens.t0), float(mulens.tE), mulens.last_observation)
            mulens.store_parameter_set({'alive': alive})

            # Return True because no further processing is required
            return True

    except:
        logger.error('Job failed: '+mulens.name)
        return False

class Command(BaseCommand):
    help = 'Fit events with PSPL and parallax, then ingest fit parameters in the db'

    def add_arguments(self, parser):
        parser.add_argument('--cores', help='Number of workers (CPU cores) to use', default=os.cpu_count(), type=int)
        parser.add_argument('--run-every', help='Run each Fit every N hours', default=4, type=int)

    def handle(self, *args, **options):

        with transaction.atomic():

            t1 = datetime.datetime.utcnow()
            logger.info('FIT_NEED_EVENTS: Starting checkpoint: ')
            utilities.checkpoint()

            # Fetch a list of alive microlensing targets that were last modelled more than
            # the maximum allowed model age:
            ts = querytools.get_alive_events_with_old_model(options['run_every'])
            logger.info('FIT_NEED_EVENTS: Initial queries selected '
                        + str(ts.count()) + ' alive microlensing events last modeled before '
                        + repr(options['run_every']) + 'hrs ago')
            target_list = list(set(ts))

            utilities.checkpoint()

            datums = ReducedDatum.objects.filter(target__in=target_list).order_by("timestamp")

            t2 = datetime.datetime.utcnow()
            logger.info('FIT_NEED_EVENTS: Retrieved associated data for ' + str(len(target_list)) + ' Targets')
            utilities.checkpoint()
            logger.info('FIT_NEED_EVENTS: Time taken chk 2: ' + str(t2 - t1))

            logger.info('FIT_NEED_EVENTS: Reviewing target list to identify those that need remodeling')
            target_data = {}
            for i,mulens in enumerate(target_list):

                # Catch for events where the RA, Dec is not set - source of this error unknown
                try:
                    if type(mulens.ra) == float:
                        mulens.get_reduced_data(datums.filter(target=mulens))

                        (status, reason) = mulens.check_need_to_fit()
                        logger.info('FIT_NEED_EVENTS: Need to fit ' + mulens.name
                                    + ': ' + repr(status) + ', reason: ' + reason)

                        # If the event is to be fitted, this will take care of evaluating whether or
                        # not the event is still alive, based on the new model.
                        # If the event is not to be fitted for any reason, we need to check whether or not
                        # it is still alive.
                        if mulens.need_to_fit:
                            target_data[mulens.name] = mulens

                        else:
                            if mulens.t0 and mulens.tE:
                                alive = fittools.check_event_alive(float(mulens.t0),
                                                                   float(mulens.tE),
                                                                   mulens.last_observation)
                                if alive != bool(mulens.alive):
                                    update_extras = {'alive': alive}
                                    mulens.store_parameter_set(update_extras)
                                    logger.info('Updated Alive status to ' + repr(alive))

                        logger.info('FIT_NEED_EVENTS: evaluated target ' + mulens.name + ', '
                                    + str(i) + ' out of ' + str(len(target_list)))
                        utilities.checkpoint()

                    else:
                        logger.info('FIT_NEED_EVENTS: Event with invalid RA, Dec, skipping')

                except ValueError:
                    logger.info('FIT_NEED_EVENTS: Could not create an Event object for ' + mulens.name + ', skipping')

            t3 = datetime.datetime.utcnow()
            logger.info('FIT_NEED_EVENTS: Collated data for ' + str(len(target_data)) + ' targets in ' + str(t3 - t2))
            utilities.checkpoint()

            # Loop through all targets in the set
            for i, (target_name, mulens) in enumerate(target_data.items()):
                logger.info('FIT_NEED_EVENTS: modeling target ' + mulens.name + ', '
                            + str(i) + ' out of ' + str(len(target_data)))

                t4 = datetime.datetime.utcnow()

                result = run_fit(mulens, cores=options['cores'])

                t5 = datetime.datetime.utcnow()
                logger.info('FIT_NEED_EVENTS: Completed modeling of ' + mulens.name + ' in ' + str(t5 - t4))
                utilities.checkpoint()

            t6 = datetime.datetime.utcnow()
            logger.info('FIT_NEED_EVENTS: Finished modeling set of targets in ' + str(t6 - t1))
            utilities.checkpoint()

if __name__ == '__main__':
    main()
