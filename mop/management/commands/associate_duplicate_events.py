from django.core.management.base import BaseCommand
from tom_targets.models import Target, TargetName, TargetExtra
from mop.management.commands import merge_utils

class Command(BaseCommand):
    help = 'Identify events with multiple Target entries'

    def add_arguments(self, parser):
        parser.add_argument('radius', help='Match radius in arcseconds')

    def handle(self, *args, **options):
        radius = float(options['radius'])

        targets = Target.matches.match_cone_search(244.6058, -54.0787, radius)

        # QuerySet > 1 means a duplicated target
        if len(targets) > 1:

            # Sort the targets into the order in which they were created in the MOP DB;
            # this will be used to determine the primary name and aliases of this event
            targets = targets.order_by('created')
            primary_target = targets[0]
            matching_targets = targets[1:]

            print('Primary target name: ' + primary_target.name)
            names = TargetName.objects.filter(target=primary_target)
            print(names)

            for t in matching_targets:
                # Create aliases for the primary target
                new_name, created = TargetName.objects.get_or_create(
                    target=primary_target, name=t.name
                )
                if created:
                    new_name.save()
                print('Alias: ', t.name, created)

                # Target coordinates are NOT merged - the coordinates of the primary target are retained

                # Merge selected extra_params
                # Many parameters are produced by the model fitting process, which will be rerun on the combined
                # data products, so these are not merged.  Here we handle the remaining parameters.
                # This method saves the revised extra_params for the primary target
                update_params = self.merge_extra_params(primary_target, matching_targets)

                # Merge the data products and ReducedDatums for the primary and matching targets
                
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

        return update_params
