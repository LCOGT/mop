from django.core.management.base import BaseCommand
from tom_targets.models import Target
from tom_dataproducts.models import ReducedDatum, DataProduct
import copy

class Command(BaseCommand):

    help = "Command to review all ReducedDatums and identify those with invalid source IDs"

    def handle(self, *args, **options):

        dataproducts = DataProduct.objects.filter(data__icontains='auto.csv')

        data_list = ReducedDatum.objects.filter(data_product__in=dataproducts)
        print('Found ' + str(data_list.count()) + ' ReducedDatums to review')

        for rd in data_list:
            print('Reviewing rd ' + str(rd.pk) + ' source=' + rd.source_name)
            print(rd.pk, rd.source_name, rd.source_location, rd.data_product)

            rd_new = copy.deepcopy(rd)

            rd.delete()

            rd_new.source_name = 'OMEGA'
            rd_new.source_location = 'MOP'
            rd_new.save()

            print('Updated ReducedDatum to ' + str(rd_new.pk))