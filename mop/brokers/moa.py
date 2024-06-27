from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from tom_alerts.alerts import GenericBroker, GenericQueryForm
from django import forms
from tom_targets.models import Target
from tom_observations import facility
from tom_dataproducts.models import ReducedDatum

from astropy.coordinates import SkyCoord
import astropy.units as unit
import urllib
import os
import numpy as np
from astropy.time import Time, TimezoneInfo
import datetime
from mop.toolbox import logs
from mop.toolbox import TAP, utilities, classifier_tools
from microlensing_targets.match_managers import validators

BROKER_URL = 'https://www.massey.ac.nz/~iabond/moa/'
photometry = "https://www.massey.ac.nz/~iabond/moa/alert2019/fetchtxt.php?path=moa/ephot/"

class MOAQueryForm(GenericQueryForm):
    target_name = forms.CharField(required=False)
    cone = forms.CharField(
        required=False,
        label='Cone Search',
        help_text='RA,Dec,radius in degrees'
    )

    def clean(self):
        if len(self.cleaned_data['target_name']) == 0 and \
                        len(self.cleaned_data['cone']) == 0:
            raise forms.ValidationError(
                "Please enter either a target name or cone search parameters"
                )

class MOABroker(GenericBroker):
    name = 'MOA'
    form = MOAQueryForm

    def add_arguments(self, parser):
        parser.add_argument('years', help='years you want to harvest, spearted by ,')

    def fetch_alerts(self, moa_files_directories, years = []):

        # Start logging process:
        log = logs.start_log()
        log.info('Started ingester for MOA alerts for year(s) '+repr(years))

        #ingest the TOM db
        list_of_targets = []
        new_targets = []
        self.event_dictionnary = {}
        time_now = Time(datetime.datetime.now()).jd
        for year in years:
            url_file_path = os.path.join(BROKER_URL+'alert'+str(year)+'/index.dat' )
            log.info('MOA ingester: querying url: '+url_file_path)
            
            events = urllib.request.urlopen(url_file_path).readlines()

            for event in events[0:]:

                event = event.decode("utf-8").split(' ')
                name = 'MOA-'+event[0]
                #Create or load

                target, result = self.ingest_event(name, float(event[2]), float(event[3]))

                # This needs to store the name of the target it refers to, rather than
                # the input name, in case that is an alias for duplicate events
                self.event_dictionnary[target.name] = [event[1],event[-2],event[-1]]

                if 'new_target' in result:
                   new_targets.append(target)

                list_of_targets.append(target)

        logs.stop_log(log)

        return list_of_targets, new_targets

    def ingest_event(self, name, ra, dec):
        cible = SkyCoord(ra, dec, unit="deg")

        target, result = validators.get_or_create_event(
                    name,
                    cible.ra.degree,
                    cible.dec.degree
                )

        if result == 'new_target':
            utilities.add_gal_coords(target)
            TAP.set_target_sky_location(target)
            classifier_tools.check_known_variable(target, coord=cible)

        return target, result

    def find_and_ingest_photometry(self, targets):


        time_now = Time(datetime.datetime.now()).jd
        for target in targets:

            datasets = ReducedDatum.objects.filter(target=target)
            existing_time = [Time(i.timestamp).jd for i in datasets if i.data_type == 'photometry']

            year = target.name.split('-')[1]
            event = self.event_dictionnary[target.name][0]

            url_file_path = os.path.join(BROKER_URL+'alert'+str(year)+'/fetchtxt.php?path=moa/ephot/phot-'+event+'.dat' )
            lines = urllib.request.urlopen(url_file_path).readlines()

            jd = []
            mags = []
            emags = []

            for line in lines:

                line = line.decode("utf-8").split("  ")
                try:

                    phot = [i for i in line if i!='']
                    tot_flux = float(self.event_dictionnary[target.name][2])+float(phot[1])

                    time = float(phot[0])
                    mag = float(self.event_dictionnary[target.name][1])-2.5*np.log10(tot_flux)
                    emag = float(phot[2])/tot_flux*2.5/np.log(10)
                    if (np.isfinite(mag)) & (emag>0) & (emag<1.0) & (time>time_now-2*365.25) & (time not in existing_time): #Harvest the last 2 years
                        jd.append(time)
                        mags.append(mag)
                        emags.append(emag)

                except:
                    pass


            photometry = np.c_[jd,mags,emags]

            for index,point in enumerate(photometry):
                try:
                    jd = Time(point[0], format='jd', scale='utc')
                    jd.to_datetime(timezone=TimezoneInfo())
                    data = {   'magnitude': point[1],
                           'filter': 'R',
                           'error': point[2]
                       }
                    rd, created = ReducedDatum.objects.get_or_create(
                    timestamp=jd.to_datetime(timezone=TimezoneInfo()),
                    value=data,
                    source_name='MOA',
                    source_location=target.name,
                    data_type='photometry',
                    target=target)

                except:
                        pass

            (t_last_jd, t_last_date) = TAP.TAP_time_last_datapoint(target)
            target.latest_data_hjd = t_last_jd
            target.latest_data_utc = t_last_date
            target.save()

            print(target.name,'Ingest done!')
    def to_generic_alert(self, alert):
        pass
