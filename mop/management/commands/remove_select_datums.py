from django.core.management.base import BaseCommand
from tom_targets.models import Target
from tom_dataproducts.models import ReducedDatum, DataProduct
import json

class Command(BaseCommand):

    help = "Command to remove specific datapoints identified to be duplicates"

    def add_arguments(self, parser):
        parser.add_argument('target_name', help='name of the event to fit')
        parser.add_argument('value', help='Value field for ReducedDatum')

    def handle(self, *args, **options):

        entry = eval(options['value'])

        # Find the Target
        t = Target.objects.get(name=options['target_name'])

        # Find all ReducedDatums associated with this Target
        datums_qs = ReducedDatum.objects.filter(target=t)

        for rd in datums_qs:
            print(rd.pk, rd.source_name, rd.value, rd.timestamp)
            got_rd = [False for x in entry.keys()]
            for i,key in enumerate(entry.keys()):
                if key in rd.value:
                    if rd.value[key] == entry[key]:
                        got_rd[i] = True

            if all(i for i in got_rd):
                opt = input(str(rd.pk) + ' identified as ReducedDatum.  Remove? Y or n: ')
                if opt == 'Y':
                    rd.delete()