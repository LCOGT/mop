from django.core.management.base import BaseCommand
from tom_targets.models import Target, TargetName, TargetExtra, TargetList
from tom_dataproducts.models import DataProduct, ReducedDatum
from tom_observations.models import ObservationRecord, ObservationGroup
from mop.management.commands import merge_utils
from django_comments.models import Comment
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Identify events with multiple Target entries'

    def add_arguments(self, parser):
        parser.add_argument('target', help='Name of target to check or all')
        parser.add_argument('radius', help='Match radius in arcseconds')
        parser.add_argument('delete', help='Delete duplicated Targets?  If yes, enter "delete"')
        parser.add_argument('remove', help='Remove duplicated ReducedDatums?  If yes, enter "remove"')

    def handle(self, *args, **options):

        # Figure out if we should check just one target for duplication or all of them
        self.exclude_events()
        if 'all' in str(options['target']).lower():
            target_selection = Target.objects.all().exclude(
                name__in=self.exclude_list
            )
        else:
            target_selection = Target.objects.filter(
                name__icontains=options['target']
            ).exclude(
                name__in=self.exclude_list
            )

        if len(target_selection) == 0:
            raise IOError('No targets found matching selection ' + options['target'])
        else:
            nselected = target_selection.count()
            logger.info('Identified ' + str(nselected) + ' targets to check')

        radius = float(options['radius'])
        duplicate_targets = {}

        if 'delete' in str(options['delete']).lower():
            check_opt = input('Configured to DELETE duplicated targets!  Are you sure?  Type yes to proceed: ')

            if check_opt != 'yes':
                logger.warning('Deletion of duplicates NOT authorised, halting')
                exit()

        # Loop over all targets currently in the database:
        for j,working_target in enumerate(target_selection):

            # First check whether this target has already been marked as a duplicate of another:
            if working_target not in duplicate_targets.keys():
                logger.info('Working on target ' + working_target.name + ', ' + str(j) + ' out of ' + str(nselected))
                logger.info(
                    'Searching for duplicates within ' + options['radius']+'arcsec of ' + working_target.name
                    + ' RA=' + str(working_target.ra)
                    + ', Dec=' + str(working_target.dec)
                            )

                # Search for all targets near to the working target's coordinates, sanity checking for
                # targets with mal-formed coordinates:
                try:
                    ra = float(working_target.ra)
                    dec = float(working_target.dec)
                except TypeError:
                    raise IOError('MAL-FORMED TARGET COORDINATES: ' + working_target.name + ', pk=' + str(working_target.pk))

                nearby_targets = Target.matches.match_cone_search(
                    round(float(working_target.ra),5),
                    round(float(working_target.dec),5),
                    radius)
                logger.info('Found nearby targets: ' + repr(nearby_targets))

                logger.info(' -> Found ' + str(nearby_targets.count()) + ' in proximity to ' + working_target.name)

                # QuerySet > 1 means a duplicated target
                if len(nearby_targets) > 1:

                    # Sort the targets into the order in which they were created in the MOP DB;
                    # this will be used to determine the primary name and aliases of this event
                    targets = nearby_targets.order_by('created')
                    primary_target = targets[0]
                    matching_targets = targets[1:]
                    logger.info(' -> Primary target name: ' + primary_target.name)
                    logger.info(' -> Matches with duplicates: ' + repr([t.name for t in matching_targets]))

                    self.merge_names(primary_target, matching_targets)

                    # Merge selected extra_params
                    # Many parameters are produced by the model fitting process, which will be rerun on the combined
                    # data products, so these are not merged.  Here we handle the remaining parameters.
                    self.merge_extra_params(primary_target, matching_targets)

                    # Merge the data products and ReducedDatums for the primary and matching targets
                    self.merge_data_products(options, primary_target, matching_targets)

                    # Merge TargetLists, if the primary or matching targets are listed
                    self.merge_targetgroups(primary_target, matching_targets)

                    # Transfer ownership of any observation records and groups made for the matched targets:
                    self.merge_observation_records(primary_target, matching_targets)

                    # Transfer any comments made on the matched targets:
                    self.merge_comments(primary_target, matching_targets)

                    # Add duplicate targets to the list for removal:
                    duplicate_targets[working_target] = []
                    for t in matching_targets:
                        duplicate_targets[working_target].append(t)

        # Last step is to remove the duplicated targets
        if len(duplicate_targets) > 0:
            logger.info('Summary of duplicated targets: ')
            for t, matches in duplicate_targets.items():
                if len(matches) > 0:
                    logger.info(t.name + ' has matches ' + repr(matches))
                    if 'delete' in str(options['delete']).lower():
                        for matching_target in matches:
                            matching_target.delete()
        else:
            logger.info('No duplicated targets found')

    def merge_names(self, primary_target, matching_targets):
        """
        Method creates TargetName aliases for the primary target from the names of the
        matching targets
        """
        merge_utils.merge_names(primary_target, matching_targets)

    def merge_extra_params(self, primary_target, matching_targets):
        """
        Many parameters are produced by the model fitting process, which will be rerun on the combined
        data products, so these are not merged.  This method handles the remaining parameters.

        Since all matching targets may have independent values for any given extra_parameter, which may differ.
        For example, the primary_target may have a classification of 'Microlensing PSPL' while the
        matching_targets may have different classifications.  In this case, any status relating to microlensing
        should be prioritized, so that the system will re-model and review this classification.

        The primary target coordinates are retained, so any extra parameters that depend on coordinates
        also retain the value from the primary target.  This includes the Sky location value and the results
        of cross-matching to the Gaia catalogue.  Similarly, TNS name and class are also based on a positional
        match and the primary target's values are retained.

        The original version of this method was intended to work with unmigrated Targets and the extra_params
        rather than custom MicrolensingTargets where these data are attributes.  Since in deployment it makes more
        sense to convert the targets first and then associate duplicates, this method is updated to use
        the attributes.
        """

        # Pre-fetch the extra parameters for the primary and matching targets
        #primary_extras = TargetExtra.objects.prefetch_related('target').filter(
        #                    target=primary_target
        #                )
        #matching_extras = [TargetExtra.objects.prefetch_related('target').filter(
        #                    target=t
        #                ) for t in matching_targets]

        # Merge the extra parameter entries for all matched targets
        update_params = merge_utils.merge_extra_params(primary_target, matching_targets)

        # Update the revise extra parameters for the primary target
        primary_target.store_parameter_set(update_params)

        logger.info(' -> Merged extra_params')

    def merge_data_products(self, options, primary_target, matching_targets):
        """
        Function to combine the data products and ReducedDatums for duplicated targets.

        Survey data for duplicated objects may or may not be duplicated also.  For example, if
        both OGLE and MOA detect a target, the lightcurves are independent and not duplicated.  However,
        queries to data archives based on sky coordinates are likely to be duplicated, e.g. a query of the ZTF
        photometry catalogue for a given RA,Dec will produce the same lightcurve.  In this case, only one copy of
        that data should be retained.

        MOP stores data in two different forms:
        - Data Products: Records of data obtained with URLs to the files themselves
        - ReducedDatums: Timeseries or other data arrays, which often relate to the content of data files

        Since these are related in the database, both should be updated together.

        The ReducedDatums for an object also record other data including the model lightcurve.  Since this will be
        updated, we simply retain the primary target's model.
        """

        # Retrieve QuerySets of the DataProducts and ReducedDatums for the primary and matching targets.
        primary_datums = ReducedDatum.objects.filter(target=primary_target)
        matching_dataproducts = [DataProduct.objects.filter(target=t) for t in matching_targets]

        merge_utils.merge_data_products(options, primary_target, primary_datums, matching_targets, matching_dataproducts)

        logger.info(' -> Completed merge of data products for ' + primary_target.name + ' with matching objects')

    def merge_observation_records(self, primary_target, matching_targets):
        """
        Method to combine observation records from duplicated targets.  Note that although
        ObservationGroups are also stored these are associated with ObservationRecords,
        rather than with targets directly, so the ownership of ObsGroups transfers
        automatically once the ObservationRecords are updated.
        """

        # Retrieve any observation record pertaining to each of the matching targets:
        obs_records = [ObservationRecord.objects.filter(target=t) for t in matching_targets]

        merge_utils.merge_observations(obs_records, primary_target)

        logger.info(' -> Completed transfer of observation records to ' + primary_target.name)

    def merge_targetgroups(self, primary_target, matching_targets):
        """
        Method ensures that any group assigned to a matching target is also assigned to the primary target.
        This method takes a maximal view of group assignments, i.e. if a matching target is in a list but
        the primary target isn't, the primary target will be added to the list, but never removed.
        """

        # Pre-fetch the extra parameters for the primary and matching targets
        targetlists = TargetList.objects.prefetch_related('targets').all()
        merge_utils.merge_targetgroups(targetlists, primary_target, matching_targets)

    def merge_comments(self, primary_target, matching_targets):
        """
        Method to combine the comments recorded for the matching targets with those of the primary target
        """

        # Retrieve all comments associated with the matching targets:
        matching_comments = [Comment.objects.filter(object_pk=t.pk) for t in matching_targets]

        merge_utils.merge_comments(matching_comments, primary_target)

    def exclude_events(self):
        """List of events to skip from automatic processing as they have been flagged for human
        management"""

        self.exclude_list = [
            'MOA-2019-BLG-0284',       # Excluded when auto de-duplication repeatedly crashed
            'Gaia20dup'
        ]
        logger.info('Excluding ' + str(len(self.exclude_list)) + ' events from selection')
