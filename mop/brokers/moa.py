from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from tom_alerts.alerts import GenericBroker, GenericQueryForm
from django import forms
from tom_targets.models import Target, TargetName
from tom_observations import facility
from tom_dataproducts.models import ReducedDatum
from os import path
from astropy.coordinates import SkyCoord
import astropy.units as u
import urllib
import requests
import pandas as pd
from io import StringIO
import os
import numpy as np
from astropy.time import Time, TimezoneInfo
import datetime
from mop.toolbox import logs
from mop.toolbox import TAP, utilities, classifier_tools
from microlensing_targets.match_managers import validators

BROKER_URL = 'https://www.massey.ac.nz/~iabond/moa/'
BROKER_URL_2025 = 'https://moaprime.massey.ac.nz/alerts/index/moa/2025'
BROKER_EVENT_URL_2025 = 'https://moaprime.massey.ac.nz/alerts/display/'
BROKER_PHOT_URL_2025 = 'https://moaprime.massey.ac.nz/alerts/datafile/MOA/'
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

            # Fetch the alert listing for the current year
            alert_content = self.fetch_alert_page_listing(year, log)

            # MOA's event pages have been made available in different formats
            # for different years.  Through to 2024, the events list is an ASCII
            # filet
            if year <= 2024:
                events = self.parse_event_list_pre2025(url_file_path)
            else:
                events = self.parse_event_list_2025(url_file_path)

            # Ingest targets from the alerts
            for name, params in events:
                target, result = self.ingest_event(name, params['RA'], params['Dec'])

                # This needs to store the name of the target it refers to, rather than
                # the input name, in case that is an alias for duplicate events
                # Note: this is no longer required for events post 2025
                if year <= 2024:
                    self.event_dictionnary[target.name] = params['MOA_params']
                else:
                    self.event_dictionnary[target.name] = [target.name]

                if 'new_target' in result:
                   new_targets.append(target)

                list_of_targets.append(target)

        logs.stop_log(log)

        return list_of_targets, new_targets

    def test_url(self, url):
        test_response = requests.get(url)
        if test_response.status_code != 404:
            return True
        else:
            return False

    def fetch_alert_page_listing(self, year, log):
        """
        Function to fetch the list of MOA alerts.

        The URL for the alerts changed over time.  Prior to 2024, the alerts were served from
        https://www.massey.ac.nz/~iabond/moa/alertYYYY/index.dat
        in ASCII format, while in 2025 the alerts were located at
        https://moaprime.massey.ac.nz/alerts/index/moa/2025
        as an HTML table.
        """

        if year <= 2024:
            url_file_path = os.path.join(BROKER_URL + 'alert' + str(year) + '/index.dat')
        else:
            url_file_path = BROKER_URL_2025
        log.info('Searching for ' + str(year) + ' alerts at ' + url_file_path)

        if test_url(url_file_path):
            log.info('Website is live, retrieving alert information')
            response = requests.get(url_file_path)
            content = response.text

        else:
            log.info('Website is OFFLINE, no alert data available')
            content = None

        return content

    def parse_event_list_pre2025(self, content):
        """
        Through until 2024, MOA events were disseminated as an ASCII .dat file,
        which we parse here to return a dictionary of event names, RAs, Decs and MOA parameters.
        """

        linelist = str(content).split('\n')

        events = {}
        for line in linelist:
            if len(line) > 0:
                entry = line.split(' ')
                name = 'MOA-' + entry[0]
                ra = float(entry[2])
                dec = float(entry[3])
                moa_params = [entry[1], entry[-2], entry[-1]]
                events[name] = {'RA': ra, 'Dec': dec, 'MOA_params': moa_params}

        return events

    def parse_event_list_2025(self, content):
        """
        For 2025, MOA events are being distributed as an HTML table, as MOA transition
        to a new alerts system for PRIME.
        """

        event_table = pd.read_html(StringIO(content))[0]

        # The event name column is unlabeled
        names = event_table['Unnamed: 0']

        events = {}
        for i,name in enumerate(names):
            s = SkyCoord(event_table['RA'][i], event_table['Dec'][i], frame='icrs', unit=(u.hourangle, u.deg))
            # MOA have switched to peak magnification and baseline magnitude rather than flux
            moa_params = [name, event_table['Amax'][i], event_table['I0'][i]]
            events[name] = {'RA': s.ra.deg, 'Dec': s.dec.deg, 'MOA_params': moa_params}

        return events

    def parse_event_pages_2025(self, events):
        """As of 2025, MOA's event table no longer contains the internal MOA name for the event, typically of
        the form gb1-R-...
        This must now be harvested from the specific page for the event.
        """

        for name, event_params in events.items():
            url_file_path = path.join(BROKER_EVENT_URL_2025, name)
            print(url_file_path)
            response = requests.get(url_file_path)
            print(response)
            content = response.text
            event_page = pd.read_html(StringIO(content))
            print(event_page)


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

    def find_and_ingest_photometry(self, targets, year_list):


        time_now = Time(datetime.datetime.now()).jd
        for target in targets:

            datasets = ReducedDatum.objects.filter(target=target)
            existing_time = [Time(i.timestamp).jd for i in datasets if i.data_type == 'photometry']
            event = self.event_dictionnary[target.name][0]

            jd = []
            mags = []
            emags = []
            for year in year_list:
                # Note the handling of the photometry changed in 2025
                if year <= 2024:
                    url_file_path = os.path.join(BROKER_URL+'alert'+str(year)+'/fetchtxt.php?path=moa/ephot/phot-'+event+'.dat' )
                else:
                    url_file_path = os.path.join(
                        BROKER_URL + 'alert' + str(year) + '/fetchtxt.php?path=moa/ephot/phot-' + event + '.dat')

                lines = urllib.request.urlopen(url_file_path).readlines()

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
