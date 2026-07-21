from django.core.management.base import BaseCommand
from tom_dataproducts.models import ReducedDatum, PhotometryReducedDatum
from tom_targets.models import Target
from astropy.time import Time
from mop.toolbox import fittools
from mop.brokers import gaia as gaia_mop
from django.conf import settings


import numpy as np
import datetime

class Command(BaseCommand):

    help = 'Clean a data product kind for a list of targets'
    
    def add_arguments(self, parser):
        parser.add_argument('targets_name', nargs='+', help='name of the events to clean')
        parser.add_argument('data_type', nargs='+', help='name of the data kind to remove')
    
    def handle(self, *args, **options):


       name = options['targets_name']
       data_type = options['data_type']
       
       events = Target.objects.filter()
       if name[0] == 'all':
           list_of_targets = events
       else:
       
           list_of_targets = []
           for event in events:
                if name[0] in event.name:
                    list_of_targets.append(event)
                                 
       for target in list_of_targets:

           resolved_type = settings.DATA_PRODUCT_TYPES[data_type[0]][0]
           if resolved_type == 'photometry':
               PhotometryReducedDatum.objects.filter(target=target).delete()
           else:
               ReducedDatum.objects.filter(target=target, data_type=resolved_type).delete()
           print(target.name, ' : Clean!')

