from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import MultipleObjectsReturned
from tom_alerts.alerts import GenericBroker, GenericQueryForm
from django import forms
from django.db.utils import IntegrityError
from tom_targets.models import Target
from tom_observations import facility
from tom_dataproducts.models import ReducedDatum

from astropy.coordinates import SkyCoord, Galactic
import astropy.units as unit
import os
import numpy as np
import requests
from astropy.time import Time, TimezoneInfo
import logging
from mop.toolbox import TAP, utilities, classifier_tools
from microlensing_targets.match_managers import validators

logger = logging.getLogger(__name__)

BROKER_URL = 'https://www.astrouw.edu.pl/ogle/ogle4/ews'

class OGLEQueryForm(GenericQueryForm):
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

class OGLEBroker(GenericBroker):
    name = 'OGLE'
    form = OGLEQueryForm

    def fetch_alerts(self, years = [], events='all'):
        """Fetch data on microlensing events discovered by OGLE"""

        # Read the lists of events for the given years
        ogle_events = self.fetch_lens_model_parameters(years)

        # Apply selection of events, if any
        if str(events).lower() != 'all' and not str(events).isnumeric():
            event_selection = {}
            event_selection[events] = ogle_events[events]
        else:
            event_selection = ogle_events

        #ingest the TOM db
        (list_of_targets, new_targets) = self.ingest_events(event_selection)

        return list_of_targets, new_targets

    def fetch_lens_model_parameters(self, years):
        """Method to retrieve the text file of the model parameters for fits by the OGLE survey"""
        logger.info('OGLE harvester: Fetching event model parameters for years '+repr(years))

        events = {}
        for year in years:
            par_file_url = os.path.join(BROKER_URL,year,'lenses.par')
            response = requests.request('GET', par_file_url)
            logger.info('OGLE harvester: retrieving parameters for events from '
                            +str(year)+' with status '+str(response.status_code))
            if response.status_code == 200:
                for line in response.iter_lines():
                    line = str(line)
                    if 'StarNo' not in line and len(line) > 5:      # Skip the file header
                        entries = line.split()
                        name = 'OGLE-'+entries[0].replace("b'","")
                        ra = entries[3]
                        dec = entries[4]
                        events[name] = (ra,dec)

        logger.info('OGLE harvester: found ' + str(len(events)) + ' event(s)')

        return events

    def ingest_events(self, ogle_events, debug=False):
        """Function to ingest the targets into the TOM database"""
        logger.info('OGLE harvester: ingesting events')

        list_of_targets = []
        new_targets = []

        for event_name, event_params in ogle_events.items():

            qs = Target.objects.filter(name=event_name)

            if len(qs) == 0:
                s = SkyCoord(event_params[0], event_params[1], unit=(unit.hourangle, unit.deg), frame='icrs')

                target, result = validators.get_or_create_event(
                    event_name,
                    s.ra.deg,
                    s.dec.deg,
                    debug=debug
                )

                if result == 'new_target':
                    utilities.add_gal_coords(target)
                    TAP.set_target_sky_location(target)
                    classifier_tools.check_known_variable(target, coord=s)
                    logger.info('OGLE harvester: added event '+event_name+' to MOP')
                    new_targets.append(target)
            else:
                logger.info('OGLE harvester: found ' + str(qs.count()) + ' targets with name ' + event_name)
                target = qs[0]

            list_of_targets.append(target)

        logger.info('OGLE harvester: completed ingest of events, including ' + str(len(new_targets)) + ' new targets')

        return list_of_targets, new_targets

    def find_and_ingest_photometry(self, targets, full_phot=False):
        current_year = str(int(Time.now().byear))
        previous_year = str(int(Time.now().byear)-1)
        logger.info('OGLE harvester: ingesting photometry')

        for target in targets:
            year = target.name.split('-')[1]
            event = target.name.split('-')[2]+'-'+target.name.split('-')[3]

            (t_last_jd, t_last_date) = TAP.TAP_time_last_datapoint(target)
            (ogle_last_jd, ogle_last_date) = TAP.TAP_time_last_datapoint(target, source_name='OGLE')

            # Only harvest the photometry for the current year's events, since
            # it will not otherwise be updating.  Also check to see if the latest
            # datapoint is more recent than those data already ingested, to minimize
            # runtime.
            if year == current_year or year == previous_year:
                photometry = self.read_ogle_lightcurve(target)
                if ogle_last_jd and not full_phot:
                    if photometry[-1][0] > ogle_last_jd:
                        status = self.ingest_ogle_photometry(target, photometry)
                        logger.info('OGLE harvester: read and ingested photometry for event '+target.name)
                    else:
                        logger.info('OGLE harvester: most recent photometry for event '
                                    +target.name+' ('+str(photometry[-1][0])+') already ingested')
                        target.latest_data_hjd = t_last_jd
                        target.latest_data_utc = t_last_date
                        target.save()
                else:
                    status = self.ingest_ogle_photometry(target, photometry)
                    logger.info('OGLE harvester: read and ingested photometry for event ' + target.name)

        logger.info('OGLE harvester: Completed ingest of photometry')

    def read_ogle_lightcurve(self, target):
        """Method to read the OGLE lightcurve via HTTP"""

        year = target.name.split('-')[1]
        event = target.name.split('-')[2] + '-' + target.name.split('-')[3]

        lc_file_url = os.path.join(BROKER_URL, year, event.lower(), 'phot.dat')

        photometry = []

        response = requests.request('GET', lc_file_url)
        if response.status_code == 200:
            for line in response.iter_lines():
                entries = str(line).replace('\n','').replace("b'",'').replace("'",'').split()
                photometry.append( [float(x) for x in entries] )

        return np.array(photometry)

    def ingest_ogle_photometry(self, target, photometry):
        """Method to store the photometry datapoints in the TOM as ReducedDatums"""

        for i in range(0,len(photometry),1):
            jd = Time(photometry[i][0], format='jd', scale='utc')
            jd.to_datetime(timezone=TimezoneInfo())
            datum = {'magnitude': photometry[i][1],
                    'filter': 'OGLE_I',
                    'error': photometry[i][2]
                    }
            try:
                rd, created = ReducedDatum.objects.get_or_create(
                    timestamp=jd.to_datetime(timezone=TimezoneInfo()),
                    value=datum,
                    source_name='OGLE',
                    source_location=target.name,
                    data_type='photometry',
                    target=target)

            except MultipleObjectsReturned:
                logger.error('OGLE HARVESTER: Found duplicated data for event '+target.name)

        (t_last_jd, t_last_date) = TAP.TAP_time_last_datapoint(target)
        target.latest_data_hjd = t_last_jd
        target.latest_data_utc = t_last_date
        target.save()

        return 'OK'

    def sort_target_list(self, list_of_targets):
        name_list = np.array([x.name for x in list_of_targets])
        order = np.argsort(name_list)
        order = order[::-1]
        return (np.array(list_of_targets)[order]).tolist()

    def select_random_targets(self, list_of_targets, new_targets, ntargets=100):

        target_index = np.random.randint(0,len(list_of_targets)-1, size=ntargets)

        # Numpy's random routines don't provide a sample with no unique entries,
        # so filter for that and fill in the gaps.
        target_index = np.unique(target_index)

        max_iter = 10
        i = 0
        while(len(target_index) < ntargets) and (i <= max_iter):
            i += 1
            idx = np.random.randint(0,len(list_of_targets), size=1)[0]
            if idx not in target_index:
                target_index = np.append(target_index, idx)

        random_targets = (np.array(list_of_targets)[target_index]).tolist()

        # If a subset of events has been requested, priorities the new targets first, up to the maximum number allowed
        event_list = []
        i = 0
        while (len(event_list) < ntargets) and (i < len(new_targets)):
            event_list.append(new_targets[i])
            i += 1

        # If there is any space left, add existing events to the selection
        i = 0
        if len(event_list) < ntargets:
            while (len(event_list) < ntargets) and (i < len(random_targets)):
                event_list.append(random_targets[i])
                i += 1

        return np.array(event_list)

    def to_generic_alert(self, alert):
        pass
  
