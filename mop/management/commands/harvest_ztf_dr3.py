from django.core.management.base import BaseCommand
from tom_dataproducts.models import ReducedDatum
from tom_targets.models import Target,TargetExtra
from astropy.time import Time, TimezoneInfo
from mop.toolbox import fittools
from mop.brokers import gaia as gaia_mop
from django.conf import settings

import os
import numpy as np
import datetime
import numpy as np
import requests
import csv
import random
import logging

LOGIN_URL = "https://irsa.ipac.caltech.edu/account/signon/login.do"


logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Download ZTF DR3 for MOP targets'
    
    def add_arguments(self, parser):
        parser.add_argument('events_to_harvest', help='all, alive, [years] or eventname')
    
    def handle(self, *args, **options):

        username =  os.getenv('IRSA_USERNAME')
        password = os.getenv('IRSA_PASSWORD')
        filters = {'zg': 'g_ZTF', 'zr': 'r_ZTF'}
        all_events = options['events_to_harvest']

        logger.info('ZTF HARVESTER: Harvesting ZTF DR3 data for events matching selection: '+all_events)

        if all_events == 'all':
            list_of_targets = Target.objects.filter()
        if all_events == 'alive':
            list_of_targets = Target.objects.filter(alive=True)
        if all_events[0] == '[':
            years = all_events[1:-1].split(',')
            events = Target.objects.filter()

            list_of_targets = []
            for year in years:
                list_of_targets =  [i for i in events if year in i.name]

            list_of_targets = list(list_of_targets)
            random.shuffle(list_of_targets)
        if 'OGLE' in all_events or 'MOA' in all_events or 'Gaia' in all_events or 'ZTF' in all_events:
            list_of_targets = Target.objects.filter(name = all_events)

        logger.info('ZTF HARVESTER: Identified '+str(len(list_of_targets))+' targets to retrieve data for')

        for target in list_of_targets:
            logger.info('ZTF HARVESTER: Retrieving data for '+str(target.name))

            ra =    target.ra
            dec =   target.dec
            radius = 0.0001 #arsec

            try:
                times = [Time(i.timestamp).jd for i in ReducedDatum.objects.filter(target=target) if i.data_type == 'photometry']
            except:
                times = []

            try:
                url = 'https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves?POS=CIRCLE '+str(ra)+' '+str(dec)+' '+str(radius)+'&FORMAT=CSV'
                response = requests.get(url,  timeout=20,auth=(username,password))
                logger.info('ZTF HARVESTER: ZTF returned response for '+str(target.name)+': '+str(response.status_code))

                content = list(csv.reader(response.content.decode('utf-8').splitlines(), delimiter=','))
                light = np.array(content)

                if len(light)>1:
                    #mjd, mag, magerr, filter
                    lightcurve = np.c_[light[1:,3],light[1:,4],light[1:,5],light[1:,7]]

                    for line in lightcurve:
                        try:
                            jd = Time(float(line[0])+2400000.5, format='jd', scale='utc')
                            mag = float(line[1])
                            emag = float(line[2])

                            filt = filters[line[-1]]
                            value = {
                                    'magnitude': mag,
                                    'filter': filt,
                                    'error': emag
                                    }

                            jd.to_datetime(timezone=TimezoneInfo())

                            if  (jd.value not in times):
                                rd, _ = ReducedDatum.objects.get_or_create(
                                    timestamp=jd.to_datetime(timezone=TimezoneInfo()),
                                    value=value,
                                    source_name='ZTFDR3',
                                    source_location='IRSA',
                                    data_type='photometry',
                                    target=target)

                        except:
                            pass

                    logger.info('ZTF HARVESTER: Ingested ZTF data for ' + str(target.name))

            except:
                logger.info('Cannot connect to IRSA')
                pass











