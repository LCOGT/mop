from django.core.management.base import BaseCommand
from tom_dataproducts.models import ReducedDatum
from tom_targets.models import Target, TargetExtra
from mop.toolbox import TAP
from astropy.table import Table, Column

class Command(BaseCommand):
    help = 'Review all available events and list those within OMEGA-IIs observing area'

    def add_arguments(self, parser):
        parser.add_argument('events', help='name of a specific event or all')

    def handle(self, *args, **options):

        # Load the field definitions of the Bulge High Cadence Zone
        KMTNet_fields = TAP.load_KMTNet_fields()

        # Parse the events to be checked
        if 'all' in str(options['events']).lower():
            target_list = Target.objects.all()
        else:
            target_list = Target.objects.filter(name= options['events'])

        # Review all available events
        target_names = []
        target_ra = []
        target_dec = []
        target_status = []
        for target in target_list:

            # Determine whether the target falls within the HCZ or not
            try:
                event_in_HCZ = TAP.event_in_HCZ(target.ra, target.dec, KMTNet_fields)

                if event_in_HCZ:
                    try:
                        if 'True' in target.extra_fields.alive:
                            alive = 'True'
                        else:
                            alive = 'False'
                    except AttributeError:
                        pass
                    sky_location = 'In HCZ'
                else:
                    sky_location = 'Outside HCZ'

                    try:
                        if 'True' in target.extra_fields.alive:
                            alive = 'True'
                        else:
                            alive = 'False'
                    except AttributeError:
                        alive = 'True'

                print('Target location: ' + sky_location)
                target.sky_location = sky_location
                target.save()

            except TypeError:
                print('TypeError exception raised for event ' + target.name)

        # Output a table of the valid events
        target_list = Table([Column(name='Target', data=target_names),
                             Column(name='RA', data=target_ra),
                             Column(name='Dec', data=target_dec),
                             Column(name='Alive', data=target_status)])
        target_list.pprint_all()
