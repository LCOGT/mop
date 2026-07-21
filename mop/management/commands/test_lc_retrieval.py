from django.core.management.base import BaseCommand
from tom_targets.models import Target
from tom_dataproducts.models import ReducedDatum, PhotometryReducedDatum
from mop.toolbox import fittools
from datetime import datetime
import numpy as np

class Command(BaseCommand):

    help = 'Test the time taken to extract timeseries data from MOP'

    def handle(self, *args, **options):

        t1 = datetime.utcnow()

        # Query DB for known pre-configured test target with manually uploaded CSV lightcurve
        # and ReducedDatums
        obj = Target.objects.filter(pk=4134)[0]
        t2 = datetime.utcnow()
        print('Time to retrieve single target: ' + str(t2-t1))

        # Use the procedure currently used by fit_need_events_PSPL.run_fit to retrieve the lightcurve datapoints
        red_data = PhotometryReducedDatum.objects.filter(target=obj).order_by("timestamp")
        t3 = datetime.utcnow()
        print('Time to retrieve filtered PhotometryReducedDatums ' + str(t3-t2))

        (datasets, ndata) = fittools.repackage_lightcurves(red_data)
        t4 = datetime.utcnow()
        print('Time to repackage the lightcurve ' + str(t4-t3))

        # Store the data in array format instead
        # Extract the model lightcurve timeseries from the PyLIMA fit object
        timeseries = datasets['OMEGA_sinistro_gp']
        data = {
            'timeseries': timeseries.tolist()
        }

        # Store this in the test DB:
        t5 = datetime.utcnow()
        qs = ReducedDatum.objects.filter(source_name='test_timeseries', data_type='lc_model',
                                                     source_location=obj.name)
        print('Found ' + str(qs.count()) + ' stored Datums for ' + obj.name)

        if qs.count() == 0:
            rd = ReducedDatum.objects.create(
                timestamp=t5,
                value=data,
                source_name='test_timeseries',
                source_location=obj.name,
                data_type='lc_model',
                target=obj
            )

            rd.save()

        else:
            rd = qs[0]
            rd.value = data
            rd.save()

        t6 = datetime.utcnow()
        print('Time to store timeseries in array format ' + str(t6-t5))

        # Retrieve data in array format:
        t7 = datetime.utcnow()
        qs = ReducedDatum.objects.filter(source_name='test_timeseries', data_type='lc_model',
                                                     source_location=obj.name)
        t8 = datetime.utcnow()
        print('Time to retrieve timeseries in array format ' + str(t8-t7))

        rd = qs[0]
        t9 = datetime.utcnow()
        print('Time to extract first queryset entry: ' + str(t9-t8))

        new_array = np.array(rd.value['timeseries'])
        #ndp = len(qs[0].value['mag'])
        #new_array = np.zeros((ndp,3))
        #new_array[:,0] = qs[0].value['time']
        #new_array[:,1] = qs[0].value['mag']
        #new_array[:,2] = qs[0].value['mag_error']
        datasets2 = {'OMEGA_sinistro_gp': new_array}
        t10 = datetime.utcnow()

        print('Time to repackage timeseries in array format ' + str(t10 - t9))
