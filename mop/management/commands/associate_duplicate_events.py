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
        parser.add_argument('radius', help='Match radius in arcseconds')

    def handle(self, *args, **options):
        radius = float(options['radius'])
        duplicate_targets = []

        # Loop over all targets currently in the database:
        targets = Target.objects.all()
        for working_target in targets:

            # First check whether this target has already been marked as a duplicate of another:
            if working_target not in duplicate_targets:
                logger.info(
                    'Searching for duplicates within ' + options['radius']+'arcsec of ' + working_target.name
                    + ' RA=' + str(working_target.ra)
                    + ', Dec=' + str(working_target.dec)
                            )

                # Search for all targets near to the working target's coordinates:
                nearby_targets = Target.matches.match_cone_search(
                    round(float(working_target.ra),5),
                    round(float(working_target.dec),5),
                    radius)
                print(nearby_targets)

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
                    self.merge_data_products(primary_target, matching_targets)

                    # Merge TargetLists, if the primary or matching targets are listed
                    self.merge_groups(primary_target, matching_targets)

                    # Transfer ownership of any observation records made for the matched targets:
                    self.merge_observation_records(primary_target, matching_targets)

                    # Transfer any comments made on the matched targets:
                    self.merge_comments(primary_target, matching_targets)

                    # Add duplicate targets to the list for removal:
                    for t in matching_targets:
                        duplicate_targets.add(t)

                exit()

        # Last step is to remove the duplicated targets

    def merge_names(self, primary_target, matching_targets):
        """
        Method creates TargetName aliases for the primary target from the names of the
        matching targets
        """

        for t in matching_targets:
            # Create aliases for the primary target
            new_name, created = TargetName.objects.get_or_create(
                target=primary_target, name=t.name
            )
            if created:
                new_name.save()
            logger.info(' -> Alias created for ' + primary_target.name + ': ' + t.name)

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
        """

        # Pre-fetch the extra parameters for the primary and matching targets
        primary_extras = TargetExtra.objects.prefetch_related('target').filter(
                            target=primary_target
                        )
        matching_extras = [TargetExtra.objects.prefetch_related('target').filter(
                            target=t
                        ) for t in matching_targets]

        # Merge the extra parameter entries for all matched targets
        update_params = merge_utils.merge_extra_params(primary_extras, matching_extras)

        # Update the revise extra parameters for the primary target
        primary_target.save(extras=update_params)

        logger.info(' -> Merged extra_params')

    def merge_data_products(self, primary_target, matching_targets):
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
        matching_datums = [ReducedDatum.objects.filter(target=t) for t in matching_targets]

        # Distill a list of the unique data sources of ReducedDatums that the primary target already has
        primary_data_sources = list(set([rd.source_name for rd in primary_datums]))
        self.sanity_check_data_sources(primary_target, primary_datums)

        for i,qs in enumerate(matching_datums):
            self.sanity_check_data_sources(matching_targets[i], qs)

        # Transfer 'ownership' of the dataproducts from the matching targets to the primary target
        for qs in matching_dataproducts:
            for dp in qs:
                dp.target = primary_target
                dp.save()

        # Review all the ReducedDatums for all matching targets.
        # Note that this filters out data labelled 'Interferometry_predictor',
        # 'AOFT_table', 'GSC_query_results', since these are generated by target coordinate queries
        # and will be the same for the primary target.
        # It also skips the lc_model lightcurve for the matching targets, since these will be refitted
        # for the primary target.
        for i,qs in enumerate(matching_datums):
            for rd in qs:
                transfer_ownership = False

                # Survey data that is likely to be unique should be transferred to the primary target
                if rd.source_name in ['OGLE', 'MOA', 'Gaia']:
                    transfer_ownership = True

                # Check whether the primary target already has data from non-unique survey sources;
                # if not, transfer ownership:
                elif rd.source_name in ['ZTF', 'ATLAS']:
                    if rd.source_name not in primary_data_sources:
                        transfer_ownership = True

                # Data products from OMEGA should be transferred, but renamed to distinguish the
                # lightcurve data
                elif 'OMEGA' in rd.source_name:
                    rd.source_name = rd.source_name + '_' + matching_targets[i].name
                    rd.value['filter'] = rd.value['filter'] + '_' + matching_targets[i].name
                    transfer_ownership = True

                if transfer_ownership:
                    rd.target = primary_target
                    rd.save()

        logger.info(' -> Completed merge of data products for ' + primary_target.name + ' with matching objects')

    def sanity_check_data_sources(self, t, datums_qs):
        """
        Verification function to check for data source that we have not considered
        Inputs:
            t   Target
            datum_qs QuerySet ReducedDatums for the given target
        """

        expected_sources = ['OGLE', 'MOA', 'Gaia', 'ZTF', 'ATLAS',
                            'Interferometry_predictor', 'AOFT_table', 'GSC_query_results',
                            'MOP']

        data_sources = list(set([rd.source_name for rd in datums_qs]))

        for ds in data_sources:
            if ds not in expected_sources and 'OMEGA' not in ds:
                raise IOError('Target ' + t.name + ' has ReducedDatums from unknown source ' + ds)

    def merge_observation_records(self, primary_target, matching_targets):
        """
        Method to combine observation records from duplicated targets
        """

        # Retrieve any observation record pertaining to each of the matching targets:
        obs_records = [ObservationRecord.objects.filter(target=t) for t in matching_targets]

        # Transfer ownership of these ObservationRecords to the primary target
        for qs in obs_records:
            for obs in qs:
                obs.target = primary_target
                obs.save()

        logger.info(' -> Completed transfer of observation records to ' + primary_target.name)

    def merge_groups(self, primary_target, matching_targets):
        """
        Method ensures that any group assigned to a matching target is also assigned to the primary target.
        This method takes a maximal view of group assignments, i.e. if a matching target is in a list but
        the primary target isn't, the primary target will be added to the list, but never removed.
        """

        # Pre-fetch the extra parameters for the primary and matching targets
        targetlists = TargetList.objects.prefetch_related('targets').all()
        for tlist in targetlists:

            for t in matching_targets:

                # Is the primary target included in this list already?  If so, move on,
                # because no further changes are necessary
                primary_included = primary_target in tlist.targets.all()
                match_included = t in tlist.targets.all()

                if match_included and not primary_included:
                    tlist.targets.add(primary_target)
                    logger.info(' -> ' + primary_target.name + ' added to TargetList ' + tlist.name)

    def merge_comments(self, primary_target, matching_targets):
        """
        Method to combine the comments recorded for the matching targets with those of the primary target
        """

        # Retrieve all comments associated with the matching targets:
        matching_comments = [Comment.objects.filter(object_pk=t.pk) for t in matching_targets]

        # Transfer ownership of the comments to the primary target
        for qs in matching_comments:
            for com in qs:
                com.object_pk = primary_target.pk
                com.save()

        logger.info(' -> Merged comments for ' + primary_target.name)
