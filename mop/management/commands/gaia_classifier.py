from django.core.management.base import BaseCommand
from django.db import transaction
from tom_dataproducts.models import ReducedDatum
from tom_targets.models import Target, TargetName
from astropy.time import Time
from mop.toolbox import querytools, fittools
import numpy as np
from mop.toolbox import classifier_tools

import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Identify microlensing events from Gaia alerts'

    def add_arguments(self, parser):

        parser.add_argument('event', help='name of a specific event or all')

    def handle(self, *args, **options):
        with transaction.atomic():
            classifier = 1

            logger.info('Gaia classifier started run - version check')

            # Retrieve a set of MicrolensingEvent objects of active Gaia Targets:
            if options['event'] == 'all':
                logger.info('Gathering data on all active Gaia events')
                target_data = querytools.get_gaia_alive_events()
            else:
                logger.info('Gathering data on event ' + options['event'])
                qs = Target.objects.filter(name=options['event'])
                if qs.count() == 0:
                    qs = TargetName.objects.filter(name=options['event'])
                    if qs.count() == 1:
                        t = Target.objects.get(pk=qs[0].target.pk)
                else:
                    t = qs[0]
                target_data = querytools.fetch_data_for_targetset([t], check_need_to_fit=False)

            nalive = str(len(target_data))
            logger.info('Found '+ nalive + ' alive Gaia targets')

            if classifier == 1:
                # Evaluate each selected Target:
                for k, (event_name, mulens) in enumerate(target_data.items()):
                    logger.info('Classifier evaluating ' + mulens.name + ', ' + str(k) + ' out of ' + nalive)

                    # First check for targets that have been flagged as binary microlensing events.
                    # The model fit results for these events are known to be unreliable because MOP
                    # doesn't yet handle binary fits, so the following evaluation is invalid, and shouldn't
                    # override a binary classification, which is assigned manually.
                    if 'Microlensing binary' not in mulens.classification:
                        # The expectation is that the lightcurve data for them will have a model
                        # fit by a separate process, which will have stored the resulting model
                        # parameters in the EXTRA_PARAMs for each Target.  Targets with no
                        # fit parameters are ignored until they are model fitted.
                        # Fitted targets will have their class set to microlensing by default

                        if mulens.u0 != 0.0 \
                            and mulens.t0 != 0.0 \
                            and mulens.tE != 0.0 \
                            and mulens.ra != None and mulens.dec != None:

                            # Test for an invalid blend magnitude:
                            valid_blend_mag = classifier_tools.check_valid_blend(float(mulens.blend_magnitude))

                            # Test for a suspiciously large u0:
                            valid_u0 = classifier_tools.check_valid_u0(float(mulens.u0))

                            # Test for low-amplitude change in photometry:
                            valid_dmag = classifier_tools.check_valid_dmag(mulens)

                            # Test for suspicious reduced chi squared value
                            valid_chisq = classifier_tools.check_valid_chi2sq(mulens)

                            # If a target fails all three criteria, set its classification
                            # to 'Unclassified variable'.  Note that TAP will consider scheduling
                            # observations for any object with 'microlensing' in the
                            # classification
                            if not valid_blend_mag or not valid_u0 or not valid_dmag:
                                update_extras={
                                    'classification': 'Unclassified variable',
                                    'category': 'Unclassified'
                                }
                                mulens.store_parameter_set(update_extras)
                                logger.info(mulens.name+': Reset as unclassified variable')

                            if not valid_chisq:
                                update_extras={
                                    'classification': 'Unclassified poor fit',
                                    'category': 'Unclassified'
                                }
                                mulens.store_parameter_set(update_extras)
                                logger.info(event_name + ': Reset as unclassified poor fit')

                    else:
                        logger.info(event_name + ': Classified as microlensing binary, will not override')
                        
            elif classifier == 2:
                for event_name, mulens in target_data.items():
                    update_extras = {
                        'classification': 'Unclassified Gaia target',
                        'category': 'Unclassified'
                    }
                    mulens.store_parameter_set(update_extras)
                    logger.info(mulens.name+': Reset as unclassified Gaia target')


def retrieve_target_photometry(target):
    """Function to retrieve all available photometry for a target, combining
    all datasets.  Based on code by E. Bachelet."""

    datasets = ReducedDatum.objects.filter(target=target)

    phot = []
    time = []
    for data in datasets:
        if data.data_type == 'photometry':
            if 'magnitude' in data.value.keys():
                try:
                    phot.append([float(data.value['magnitude']),
                    float(data.value['error'])])
                    time.append(Time(data.timestamp).jd)
                except:
                    # Weights == 1
                    phot.append([float(data.value['magnitude']),
                    1])
                    time.append(Time(data.timestamp).jd)

    photometry = np.c_[time,phot]

    return photometry
