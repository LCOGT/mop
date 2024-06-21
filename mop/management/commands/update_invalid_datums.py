from django.core.management.base import BaseCommand
from tom_targets.models import Target
from tom_dataproducts.models import ReducedDatum, DataProduct

class Command(BaseCommand):

    help = "Command to review all ReducedDatums and identify those with invalid source IDs"

    def handle(self, *args, **options):

        data_list = ReducedDatum.objects.all()
        print('Found ' + str(data_list.count()) + ' ReducedDatums to review')

        for rd in data_list:

            if len(rd.source_name) == 0 or rd.source_name == 'None' or rd.source_name == None:

                print(rd.pk, rd.source_name, rd.source_location, rd.data_product)
                # Try to identify the origin of the data if possible
                if 'auto.csv' in rd.data_product.data:
                    rd.source_name = 'OMEGA'
                    rd.source_location = 'MOP'
                    rd.save()
                    print('Updated ReducedDatum ' + str(rd.pk))