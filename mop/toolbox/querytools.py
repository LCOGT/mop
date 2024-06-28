from tom_dataproducts.models import ReducedDatum
from tom_targets.models import Target, TargetName, TargetList
from django.db.models import Q
from mop.toolbox import utilities
import logging
import datetime
from astropy.time import Time, TimeDelta
from django.db import connection
import numpy as np

logger = logging.getLogger(__name__)

def fetch_alive_events_outside_HCZ(with_atomic=True):
    """
    Function to retrieve Targets that are classified as microlensing events that are currently ongoing.
    """

    if with_atomic:
        ts = Target.objects.select_for_update(skip_locked=True).filter(
            classification__icontains='Microlensing',
            alive=True,
            sky_location__icontains='Outside HCZ'
        )

    else:
        ts = Target.objects.filter(
            classification__icontains='Microlensing',
            alive=True,
            sky_location__icontains='Outside HCZ'
        )

    logger.info('queryTools: Selected ' + str(ts.count()) + ' alive microlensing events outside the HCZ')

    utilities.checkpoint()

    target_set = list(set(ts))

    return target_set

def get_alive_events_outside_HCZ(option):
    """
    Function to retrieve the data for targets that are classified as microlensing events that are currently ongoing.

    Parameters:
        option  str   Can be 'all', in which case the whole database is searched for targets or
                        the name of a specific event.
    """

    if option == 'all':
        t1 = datetime.datetime.utcnow()
        logger.info('queryTools: checkpoint 1')
        utilities.checkpoint()

        # Search TargetExtras to identify alive microlensing events outside the HCZ
        target_list = fetch_alive_events_outside_HCZ()
        t2 = datetime.datetime.utcnow()
        logger.info('queryTools: Initial target list has ' + str(len(target_list)) + ' entries')

        # Now gather any TargetExtra and ReducedDatums associated with these targets.
        # This is managed as a dictionary of MicrolensingEvent objects
        target_data = fetch_data_for_targetset(target_list, check_need_to_fit=False)

        t3 = datetime.datetime.utcnow()
        logger.info('queryTools: Collated data for ' + str(len(target_data)) + ' targets in ' + str(t3 - t2))
        utilities.checkpoint()

    # Search for a specific target
    else:
        qs = Target.objects.filter(name=option)

        if qs.count() == 1:
            target_list = [qs[0]]
            target_data = fetch_data_for_targetset(target_list, check_need_to_fit=False)

        elif qs.count() == 0:
            logger.error('runTAP: Cannot find requested target ' + option)
            target_data = {}

        else:
            target_data = {}
            logger.error('runTAP: Found multiple events by the name ' + target.name)

    return target_data

def fetch_data_for_targetset(target_list, check_need_to_fit=True, fetch_photometry=True):
    """
    Function to retrieve all TargetExtra and ReducedDatums associated with a set of targets
    """
    t1 = datetime.datetime.utcnow()

    # Perform the search for associated data
    datums = ReducedDatum.objects.filter(target__in=target_list).order_by("timestamp")
    names = TargetName.objects.filter(target__in=target_list)

    t2 = datetime.datetime.utcnow()
    logger.info('queryTools: Retrieved associated data for ' + str(len(target_list)) + ' Targets')
    utilities.checkpoint()
    logger.info('queryTools: Time taken: ' + str(t2 - t1))

    # Create microlensing event instances for the selected targets, associating all of the
    # data products for later use
    logger.info('queryTools: collating data on microlensing event set')
    target_data = {}
    for i, mulens in enumerate(target_list):
        mulens.get_target_names(names.filter(target=mulens))
        if fetch_photometry:
            mulens.get_reduced_data(datums.filter(target=mulens))
        if check_need_to_fit:
            (status, reason) = mulens.check_need_to_fit()
            logger.info('queryTools: Need to fit: ' + repr(status) + ', reason: ' + reason)

            if mulens.need_to_fit:
                target_data[mulens.name] = mulens

        else:
            target_data[mulens.name] = mulens
        logger.info('queryTools: collated data for target ' + mulens.name + ', '
                    + str(i) + ' out of ' + str(len(target_list)))
        utilities.checkpoint()

    t3 = datetime.datetime.utcnow()
    logger.info('queryTools: Collated data for ' + str(len(target_data)) + ' targets in ' + str(t3 - t2))
    utilities.checkpoint()

    return target_data

def fetch_priority_targets(priority_threshold, event_type='stellar'):
    """Function to fetch a list of Targets currently assigned a priority value higher than
    the given threshold.  Different priority keys are specified in the extra_fields and can
    be used as selection keys. """

    # First fetch a list of TargetExtra entries where the priority exceeds the threshold.
    # This returns a list of Target pk interger values.

    # With the custom Targets model we can search directly on the Target table,
    # but note that this doesn't exclude Nan or None values
    if event_type == 'stellar':
        ts = Target.objects.filter(
            tap_priority__gt=priority_threshold,
            sky_location__icontains='Outside HCZ',
            classification__icontains='Microlensing',
        ).exclude(
            YSO=True,
            QSO=True,
            galaxy=True,
            alive=False,
        )
    else:
        ts = Target.objects.filter(
            tap_priority_longte__gt=priority_threshold,
            sky_location__icontains='Outside HCZ',
            classification__icontains='Microlensing',
        ).exclude(
            YSO=True,
            QSO=True,
            galaxy=True,
            alive=False,
        )

    logger.info('queryTools: Got ' + str(ts.count()) + ' priority alive events outside the HCZ')
    for t in ts:
        logger.info(t.name + ' ' + str(t.tap_priority) + ' ' + str(type(t.tap_priority))
                    + str(t.tap_priority_longte) + ' ' + str(type(t.tap_priority_longte)))
        if np.isnan(t.tap_priority):
            logger.info('NaN detected')

    target_list = list(set(ts))
    logger.info('QueryTools: identified ' + str(len(target_list)) + ' targets')

    return target_list

def get_gaia_alive_events():
    """
    Function to retrieve Targets that are classified as microlensing events that are currently ongoing.

    Parameters:
        None
    """

    t1 = datetime.datetime.utcnow()
    logger.info('queryTools: checkpoint 1')
    utilities.checkpoint()

    # Search for alive Gaia microlensing events outside the HCZ
    # Since we need to search all TargetName entries here, we can't do a reverse foreign key look-up
    # for properties on the custom Target model because the TargetName model class inherits only
    # the BaseTarget model.
    qs = Target.objects.filter(
        Q(name__icontains='Gaia') | Q(aliases__name__icontains='Gaia'),
        classification__icontains='Microlensing',
        sky_location__icontains='Outside HCZ',
        alive=True
    )
    target_list = list(set(qs))
    logger.info('queryTools: Initial query selected ' + str(qs.count()) + ' alive Gaia events')
    t2 = datetime.datetime.utcnow()
    utilities.checkpoint()

    logger.info('queryTools: target list has ' + str(len(target_list)) + ' entries')

    # Now gather any TargetExtra and ReducedDatums associated with these targets.
    # This is managed as a dictionary of MicrolensingEvent objects
    target_data = fetch_data_for_targetset(target_list, check_need_to_fit=False)

    t3 = datetime.datetime.utcnow()
    logger.info('queryTools: Collated data for ' + str(len(target_data)) + ' targets in ' + str(t3 - t2))
    utilities.checkpoint()

    return target_data

def get_targetlist_alive_events(targetlist_name='all'):
    """
    Function to retrieve and filter the list of targets from a given targetlist, ensuring those returned are Alive
    and not known variables.
    """

    # Options include 'all' targets, in which case we fetch all alive microlensing events
    target_set = fetch_alive_events_outside_HCZ(with_atomic=False)
    if targetlist_name != 'all':
        targets = TargetList.objects.get(id=targetlist_name)
        targets = targets.targets.all()

        target_set = list(set(target_set).intersection(set(targets)))

    return target_set

def get_alive_events_with_old_model(max_model_age):
    """
    Fetch the Targets that are alive, classified as microlensing and which have a last_fit date older
    than the threshold max_model_age [hours]
    """

    # The cutoff for the maximum allowed model fit age needs to be a Time object:
    cutoff = Time(datetime.datetime.utcnow() - datetime.timedelta(hours=max_model_age)).jd

    ts = Target.objects.select_for_update(skip_locked=True).filter(
        alive=True,
        classification__icontains='Microlensing',
        last_fit__lte=cutoff
    )

    return ts