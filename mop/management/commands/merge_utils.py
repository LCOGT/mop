from tom_targets.models import Target, TargetName, TargetExtra
from tom_dataproducts.models import DataProduct, ReducedDatum
import logging
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

def merge_boolean_value(primary_value, matching_values):
    """
    If a boolean parameter is true for either the primary target or any of the matching targets,
    then the value true should be the result.  Otherwise, return false.

    Inputs:
        primary_value str           Alive extra_param for primary Target
        matching_values list, str   Alive extra_param values for matching Targets

    Returns:
        new_value  str              New Alive status
    """

    if primary_value in ['False', 'None', None] and 'True' in matching_values:
        return 'True'
    elif primary_value in ['True']:
        return 'True'
    else:
        return 'False'


def merge_obs_mode(primary_value, matching_values):
    """
        Targets under active observation should always be prioritized.
        This function checks through a list of the possible observation mode values
        in order of the urgency of those modes.

        Inputs:
            primary_value str           Alive extra_param for primary Target
            matching_values list, str    Alive extra_param values for matching Targets

        Returns:
            new_value  str              New Observing_mode status
    """

    priority_list = [
        'priority_stellar_event',
        'priority_long_event',
        'regular_long_event'
    ]

    for mode in priority_list:
        # If the primary target already has this observation mode set,
        # this takes priority
        if primary_value == mode:
            return mode

        # If not, check to see if any of the matching targets have this priority
        # If they do, use this observation mode
        for obs_mode in matching_values:
            if obs_mode == mode:
                return obs_mode

    # If we get to this point without returning, neither the primary target
    # nor any matching targets had a valid observing mode
    return 'No'

def merge_classification(primary_value, matching_values):
    """
        If either the primary Target or any matching Target has 'Microlensing' in the classification,
        this takes priority over any other entry.
        In cases of microlensing, binary classifications take priority over PSPL.

        Inputs:
            primary_value str           Alive extra_param for primary Target
            matching_values list, str    Alive extra_param values for matching Targets

        Returns:
            new_value  str              New classification
    """

    # Priority order of standard classifications
    priority_order = [
        'Microlensing binary',
        'Microlensing PSPL',
        'Variable star',
        'Extra-galactic variable',
        'Known transient',
        'Unclassified poor fit'
    ]

    # Prioritize binary microlensing events
    for classification in priority_order:
        if primary_value != None:
            if 'None' not in primary_value and classification in primary_value:
                return classification
        if classification in matching_values:
            return classification

    # If we get here, the entries are either None or non-standard.  Prioritize any user-entered value:
    if primary_value != None and 'None' not in primary_value:
        return primary_value
    for classification in matching_values:
        if classification != None and 'None' not in classification:
            return classification

    # If we get here, then we have no idea what this event is.
    # Return the default status of 'Microlensing PSPL' so that MOP will re-evaluate the target
    return 'Microlensing PSPL'


def merge_category(primary_value, matching_values):
    """
        If either the primary Target or any matching Target has 'Microlensing' in the category,
        this takes priority over any other entry.
        In cases of microlensing, stellar categories take priority over long tE events, due to the urgency
        of their observations.  These events will need to be re-evaluated.

        Inputs:
            primary_value str           Alive extra_param for primary Target
            matching_values list, str    Alive extra_param values for matching Targets

        Returns:
            new_value  str              New category
    """

    # Priority order of standard categories
    priority_order = [
        'Microlensing stellar/planet',
        'Microlensing long-tE',
        'Stellar activity',
        'Nova/supernova',
        'Eclipsing binary',
        'Unclassified'
    ]

    # Look for existing categorizations, in order of priority
    for cat in priority_order:
        if cat in primary_value or cat in matching_values:
            return cat

    # If we get here, the entries are either None or non-standard.  Prioritize any user-entered value,
    # taking that of the primary target first.
    if 'None' not in primary_value:
        return primary_value
    for cat in matching_values:
        if 'None' not in cat:
            return cat

    # If we get here, then we have no idea what this event is.
    # Return the default status of 'Microlensing PSPL' so that MOP will re-evaluate the target
    return 'Microlensing stellar/planet'

def find_extra_value(extraset, search_key):
    extra_value = None
    for x in extraset:
        if x.key == search_key:
            extra_value = x.value
    return extra_value
def fetch_param_values(primary_extras, matching_extras, search_key):
    """
    Fetch the values of an extra_param key for the primary target and all matching targets

    Inputs:
        primary_extras QuerySet  Extra_params for the primary target
        matching_extras list of QuerySets   Extra_params for each of the matching targets
        search_key str          Extra_parameter key name

    Returns:
        primary_value   value   Extra_param value for the search_key from the primary target
        matching_values list values Extra_param values for the search_key from each of the matching targets
    """

    primary_value = find_extra_value(primary_extras, search_key)

    matching_values = []
    for extraset in matching_extras:
        matching_values.append(find_extra_value(extraset, search_key))

    return primary_value, matching_values

def fetch_custom_attributes(primary_target, matching_targets, search_key):

    if search_key != 'fit_covariance':
        primary_value = getattr(primary_target, search_key)
        matching_values = [getattr(t, search_key) for t in matching_targets]
    else:
        primary_value = primary_target.load_fit_covariance()
        matching_values = [t.load_fit_covariance() for t in matching_targets]

    return primary_value, matching_values

def merge_extra_params(primary_target, matching_targets):
    """
    Function to handle the merging of the extra_parameters of two or more targets.
    Updated to handle the custom MicrolensingTarget attributes rather than separate extra_params.

    Inputs:
        primary_extras QuerySet  Extra_params for the primary target
        matching_extras list of QuerySets   Extra_params for each of the matching targets

    Returns:
        update_params dict     Set of merged extra_params
    """
    # Holding dictionary for merged parameter values that need updating.  Initialize with the values
    # for the primary target
    update_params = primary_target.get_target_extras()

    # Merge boolean keywords
    param_list = ['alive', 'interferometry_candidate', 'YSO', 'QSO', 'galaxy']
    for param in param_list:
        primary_value, matching_values = fetch_custom_attributes(primary_target, matching_targets, param)
        update_params[param] = merge_boolean_value(primary_value, matching_values)

    # Observing mode
    primary_value, matching_values = fetch_custom_attributes(primary_target, matching_targets, 'observing_mode')
    update_params['Observing_mode'] = merge_obs_mode(primary_value, matching_values)

    # Classification
    primary_value, matching_values = fetch_custom_attributes(primary_target, matching_targets, 'classification')
    update_params['Classification'] = merge_classification(primary_value, matching_values)

    # Category
    primary_value, matching_values = fetch_custom_attributes(primary_target, matching_targets, 'category')
    update_params['Category'] = merge_classification(primary_value, matching_values)

    return update_params

def merge_names(primary_target, matching_targets):
    """
    Method creates TargetName aliases for the primary target from the names of the
    matching targets
    """

    for t in matching_targets:
        try:
            # Create aliases for the primary target
            new_name, created = TargetName.objects.get_or_create(
                target=primary_target, name=t.name
            )
            if created:
                logger.info(' -> Alias created for ' + primary_target.name + ': ' + t.name)
            else:
                logger.info(' -> Alias exists for ' + primary_target.name + ': ' + t.name)

        # Catch rare cases where three targets are in close proximity but sufficiently separated
        # that only one neighbour lies within the search radius of any one target.
        # E.g. MOA-2023-BLG-119, MOA-2023-BLG-123 and OGLE-2023-BLG-0363.
        # An IntegrityError here occurs because we are trying to create an alias for a target which is already an
        # alias of a different target, and TargetNames are required to be unique.
        except IntegrityError:
            # Get the existing targetname entry for the matching target,
            # and update it to point to the new primary target
            tn = TargetName.objects.get(name=t.name)
            tn.target = primary_target
            tn.save()

def sanity_check_data_sources(t, datums_qs):
    """
    Verification function to check for data source that we have not considered
    Inputs:
        t   Target
        datum_qs QuerySet ReducedDatums for the given target
    """

    expected_sources = ['OGLE', 'MOA', 'Gaia', 'ZTF', 'ZTFDR3', 'ATLAS',
                        'Interferometry_predictor', 'AOFT_table', 'GSC_query_results',
                        'MOP', 'ASAS-SN']

    for i,rd in enumerate(datums_qs):

        # Test that the data_source has one of the expected labels
        if rd.source_name not in expected_sources and 'OMEGA' not in rd.source_name:
            # If it doesn't check that the name includes one of the identifiers from an accepted source.
            # This allows labels such as "MOA_MOA-2023-BLG-457" which can happen due to the merge process itself
            found_source = False
            for source in expected_sources:
                if source in rd.source_name:
                    found_source = True

            if not found_source:
                raise IOError('Target ' + t.name + ' has ReducedDatum (pk=' + str(rd.pk) \
                              + ') from unknown source ' + rd.source_name)

def merge_data_products(options, primary_target, primary_datums, matching_targets, matching_dataproducts):
    """
    Function to merge the data products associated with duplicated targets

    Note that this filters out data labelled 'Interferometry_predictor',
    'AOFT_table', 'GSC_query_results', since these are generated by target coordinate queries
    and will be the same for the primary target.
    It also skips the lc_model lightcurve for the matching targets, since these will be refitted
    for the primary target.

    It should also be noted that this function does not update any DataProductGroups, since MOP
    doesn't make use of these.
    """
    # Distill a list of the unique data sources of ReducedDatums that the primary target already has
    primary_data_sources = list(set([rd.source_name for rd in primary_datums]))
    sanity_check_data_sources(primary_target, primary_datums)

    matching_datums = [ReducedDatum.objects.filter(target=t) for t in matching_targets]
    for i, qs in enumerate(matching_datums):
        sanity_check_data_sources(matching_targets[i], qs)

    # Transfer 'ownership' of the dataproducts from the matching targets to the primary target
    for qs in matching_dataproducts:
        for dp in qs:
            dp.target = primary_target
            dp.save()

    # Review all the ReducedDatums for all matching targets.
    for i, qs in enumerate(matching_datums):
        for rd in qs:
            transfer_ownership = False

            # Survey data that is likely to be unique should be transferred to the primary target
            if rd.source_name in ['OGLE', 'MOA', 'Gaia']:
                transfer_ownership = True

            # Check whether the primary target already has data from non-unique survey sources;
            # if not, transfer ownership:
            elif 'ZTF' in rd.source_name or 'ATLAS' in rd.source_name or 'ASAS-SN' in rd.source_name:
                if rd.source_name not in primary_data_sources:
                    transfer_ownership = True

            # Data products from OMEGA should be transferred, but renamed to distinguish the
            # lightcurve data
            elif 'OMEGA' in rd.source_name:
                transfer_ownership = True

            if transfer_ownership:
                rd.source_name = rd.source_name + '_' + matching_targets[i].name
                rd.value['filter'] = rd.value['filter'] + '_' + matching_targets[i].name
                rd.target = primary_target

                try:
                    rd.save()
                except ValidationError as err:
                    if 'remove' in options['remove']:
                        rd.delete()
                    else:
                        raise err

def merge_targetgroups(targetlists, primary_target, matching_targets):
    """
    Function ensures that any group assigned to a matching target is also assigned to the primary target.
    This method takes a maximal view of group assignments, i.e. if a matching target is in a list but
    the primary target isn't, the primary target will be added to the list, but never removed.
    """

    for tlist in targetlists:

        for t in matching_targets:

            # Is the primary target included in this list already?  If so, move on,
            # because no further changes are necessary
            primary_included = primary_target in tlist.targets.all()
            match_included = t in tlist.targets.all()

            if match_included and not primary_included:
                tlist.targets.add(primary_target)
                logger.info(' -> ' + primary_target.name + ' added to TargetList ' + tlist.name)


def merge_comments(matching_comments, primary_target):
    """
    Function to ensure that any comments recorded for matched targets are transfered to the primary target
    """

    # Transfer ownership of the comments to the primary target
    for qs in matching_comments:
        for com in qs:
            com.object_pk = primary_target.pk
            com.save()

    logger.info(' -> Merged comments for ' + primary_target.name)

def merge_observations(observations, primary_target):
    """
    Function to re-assign ownership of an observation record to the primary target.

    observations    list of QuerySets   ObservationRecords
    """

    for qs in observations:
        for obs in qs:
            obs.target = primary_target
            obs.save()
