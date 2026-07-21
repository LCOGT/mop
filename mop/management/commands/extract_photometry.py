from django.core.management.base import BaseCommand
from tom_targets.models import Target
from mop.toolbox import obs_control
from astropy.time import Time
import datetime
from tom_dataproducts.models import PhotometryReducedDatum

import numpy as np

class Command(BaseCommand):

    help = 'Extract photometry from event'
    
    def add_arguments(self, parser):
        parser.add_argument('target_name', help='name of the event to extract')

    
    def handle(self, *args, **options):
      
        target, created = Target.objects.get_or_create(name= options['target_name'])
        datasets = PhotometryReducedDatum.objects.filter(target=target)

        time = [Time(i.timestamp).jd for i in datasets]
        names = [i.source_name for i in datasets]
        phot = [[i.brightness,i.brightness_error,i.bandpass] for i in datasets]

        photometry = np.c_[names,time,phot]

        np.savetxt('./data/'+target.name+'.dat',photometry,fmt='%s')
