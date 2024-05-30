from tom_dataproducts.models import ReducedDatum
from tom_targets.models import Target,TargetExtra,TargetName, TargetList
from microlensing_targets.models import MicrolensingTarget
from mop.toolbox import utilities
import logging
import datetime
from django.db import connection
import numpy as np

logger = logging.getLogger(__name__)

def fetch_alive_events_outside_HCZ(with_atomic=True):
    """
    Function to retrieve Targets that are classified as microlensing events that are currently ongoing.
    """

    if with_atomic:
        ts1 = TargetExtra.objects.prefetch_related('target').select_for_update(skip_locked=True).filter(
            key='Classification', value__icontains='Microlensing'
        )
        ts2 = TargetExtra.objects.prefetch_related('target').select_for_update(skip_locked=True).filter(
            key='Alive', value=True
        )
        ts3 = TargetExtra.objects.prefetch_related('target').select_for_update(skip_locked=True).filter(
            key='Sky_location', value__icontains='Outside HCZ'
        )

    else:
        ts1 = TargetExtra.objects.prefetch_related('target').filter(
            key='Classification', value__icontains='Microlensing'
        )
        ts2 = TargetExtra.objects.prefetch_related('target').filter(
            key='Alive', value=True
        )
        ts3 = TargetExtra.objects.prefetch_related('target').filter(
            key='Sky_location', value__icontains='Outside HCZ'
        )
    logger.info('queryTools: Initial queries selected '
                + str(ts1.count()) + ' events classified as microlensing, '
                + str(ts2.count()) + ' events currently Alive, and '
                + str(ts3.count()) + ' events outside the HCZ')
    utilities.checkpoint()

    # This doesn't directly produce a queryset of targets, instead it returns a queryset of target IDs.
    # So we have to extract the corresponding targets:
    targets1 = [x.target for x in ts1]
    targets2 = [x.target for x in ts2]
    targets3 = [x.target for x in ts3]
    target_set = list(set(targets1).intersection(
        set(targets2)
    ).intersection(
        set(targets3)
    ))

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

def fetch_priority_targets(priority_key, priority_threshold):
    """Function to fetch a list of Targets currently assigned a priority value higher than
    the given threshold.  Different priority keys are specified in the extra_fields and can
    be used as selection keys. """

    # First fetch a list of TargetExtra entries where the priority exceeds the threshold.
    # This returns a list of Target pk interger values.
    ts1 = TargetExtra.objects.prefetch_related('target').filter(
        key=priority_key, float_value__gt=priority_threshold
    ).exclude(
        value=np.nan
    ).exclude(
        value__exact=''
    ).exclude(
        value__exact='None'
    )
    ts2 = TargetExtra.objects.prefetch_related('target').filter(
        key='Sky_location', value__icontains='Outside HCZ'
    )
    ts3 = TargetExtra.objects.prefetch_related('target').filter(
        key='Classification', value__icontains='Microlensing'
    )
    ts4 = TargetExtra.objects.prefetch_related('target').filter(
        key='YSO', value=False
    )
    ts5 = TargetExtra.objects.prefetch_related('target').filter(
        key='QSO', value=False
    )
    ts6 = TargetExtra.objects.prefetch_related('target').filter(
        key='galaxy', value=False
    )
    ts7 = TargetExtra.objects.prefetch_related('target').filter(
        key='Alive', value=True
    )

    logger.info('QueryTools: Got ' + str(ts1.count()) + ' targets above priority threshold, '
          + str(ts2.count()) + ' targets outside the HCZ, '
          + str(ts3.count()) + ' targets classified as microlensing, '
          + str(ts4.count()) + ' targets not YSOs, '
          + str(ts5.count()) + ' targets not QSOs, '
          + str(ts6.count()) + ' targets not galaxies, '
          + str(ts7.count()) + ' targets that are currently Alive')

    # Find the intersection of the target sets:
    targets1 = [x.target for x in ts1]
    targets2 = [x.target for x in ts2]
    targets3 = [x.target for x in ts3]
    targets4 = [x.target for x in ts4]
    targets5 = [x.target for x in ts5]
    targets6 = [x.target for x in ts6]
    targets7 = [x.target for x in ts7]

    target_list = list(set(targets1).intersection(
        set(targets2)
    ).intersection(
        set(targets3)
    ).intersection(
        set(targets4)
    ).intersection(
        set(targets5)
    ).intersection(
        set(targets6)
    ).intersection(
        set(targets7)
    ))
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

   # Search TargetExtras to identify alive microlensing events outside the HCZ
    ts1 = TargetExtra.objects.prefetch_related('target').select_for_update(skip_locked=True).filter(
        key='Classification', value__icontains='Microlensing'
    )
    ts2 = TargetExtra.objects.prefetch_related('target').select_for_update(skip_locked=True).filter(
        key='Alive', value=True
    )
    logger.info('queryTools: Initial queries selected '
                + str(ts1.count()) + ' events classified as microlensing, '
                + str(ts2.count()) + ' events currently Alive')
    t2 = datetime.datetime.utcnow()
    utilities.checkpoint()

    # This doesn't directly produce a queryset of targets, instead it returns a queryset of target IDs.
    # So we have to extract the corresponding targets.
    # In the process, filter out any events that are not from Gaia
    targets1 = [x.target for x in ts1 if 'Gaia' in x.target.name]
    targets2 = [x.target for x in ts2 if 'Gaia' in x.target.name]
    target_list = list(set(targets1).intersection(set(targets2)))

    logger.info('queryTools: Initial target list has ' + str(len(target_list)) + ' entries')

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