from django.core.management.base import BaseCommand
from tom_targets.models import Target
from tom_dataproducts.models import PhotometryReducedDatum
from mop.toolbox import fittools
from os import path

class Command(BaseCommand):

    help = 'Function to output all available lightcurve data for a given target to localdisk'

    def add_arguments(self, parser):
        parser.add_argument('target_name', help='name of the event to fit')
        parser.add_argument('output_dir', help='directory path for output')

    def handle(self, *args, **options):

        # Fetch the Target
        qs = Target.objects.filter(name=options['target_name'])

        if len(qs) == 0:
            raise IOError('No known target matching name '+options['target_name'])
        else:
            target = qs[0]

        # Fetch the PhotometryReducedDatums for this Target
        red_data = PhotometryReducedDatum.objects.filter(target=target).order_by("timestamp")

        # Repackage the data into lightcurves for separate telescopes and filters
        (datasets, ndata) = fittools.repackage_lightcurves(red_data)

        # Output each dataset as lightcurve files
        for data_id, lc in datasets.items():
            file_path = path.join(options['output_dir'], options['target_name']+'_'+data_id+'.txt')
            f = open(file_path, 'w')
            f.write('# JD   mag   mag_error  dataset_ID\n')
            for i in range(0,len(lc),1):
                f.write(str(lc[i,0])+' '+str(lc[i,1])+' '+str(lc[i,2])+' '+data_id+'\n')
            f.close()
