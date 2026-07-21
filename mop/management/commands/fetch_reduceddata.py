from django.core.management.base import BaseCommand
from tom_targets.models import Target
from tom_dataproducts.models import PhotometryReducedDatum

class Command(BaseCommand):
    help = 'Retrieve all ReducedDatums for a given Target'

    def add_arguments(self, parser):
        parser.add_argument('target_name', help='name of the event to fit')

    def handle(self, *args, **options):
        qs = Target.objects.filter(name=options['target_name'])

        if qs.count() == 0:
            print('FETCH DATA: No target found by name ' + options['target_name'])

        else:
            target = qs[0]

            qs = PhotometryReducedDatum.objects.filter(target=target)

            print('FETCH DATA: Found ' + str(qs.count()) + 'datapoints for ' + target.name)

            for rd in qs:
                print('RD: ' + rd.bandpass + ' ' + str(rd.timestamp) + ' ' \
                        + str(rd.brightness) + ' ' + str(rd.brightness_error))
