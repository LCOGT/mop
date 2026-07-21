from django.core.management.base import BaseCommand
from tom_targets.models import Target
from tom_dataproducts.models import ReducedDatum, PhotometryReducedDatum, DataProduct
import copy

class Command(BaseCommand):

    help = "Command to review all ReducedDatums and identify those with invalid source IDs"

    def handle(self, *args, **options):

        dataproducts = DataProduct.objects.filter(data__icontains='auto.csv')

        self.review_datums(ReducedDatum.objects.filter(data_product__in=dataproducts))
        self.review_datums(PhotometryReducedDatum.objects.filter(data_product__in=dataproducts))

    def review_datums(self, data_list):
        print('Found ' + str(data_list.count()) + ' ' + data_list.model.__name__ + 's to review')

        for i,rd in enumerate(data_list):
            print('Reviewing rd ' + str(rd.pk) + ' source=' + rd.source_name + ', ' + str(i)
                  + ' out of ' + str(data_list.count()))
            print(rd.pk, rd.source_name, rd.source_location, rd.data_product)

            if 'OMEGA' not in rd.source_name:
                rd_new = copy.deepcopy(rd)

                rd.delete()

                rd_new.source_name = 'OMEGA'
                rd_new.source_location = 'MOP'
                rd_new.save()

                print('Updated ' + data_list.model.__name__ + ' to ' + str(rd_new.pk))