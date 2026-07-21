from django.core.management.base import BaseCommand
from tom_alerts.alerts import GenericBroker
from os import path
import requests
from bs4 import BeautifulSoup

import logging

logger = logging.getLogger(__name__)

BROKER_URL = 'https://kmtnet.kasi.re.kr/ulens/event/'


class KMTNetBroker(GenericBroker):
    """
    Class to harvest alerts of microlensing events from KMTNet.
    Note that this isn't a full broker since KMTNet simply post an HTML-format list
    on a website rather than have a queriable service.
    """

    def fetch_all_parameters(self, year_list):

        logger.info('Started KMTNet broker')

        events = {}
        for year in year_list:
            url = path.join(BROKER_URL, year)
            response = requests.get(url)
            html_content = response.text

            # Parse the HTML soup
            soup = BeautifulSoup(html_content, 'html.parser')
            rows = soup.find_all('tr')

            # Identify and parse all the rows in the table of events
            for row in rows:
                entries = row.text.replace('<td>',' ').replace('</td>','').split()
                if 'KMT-' in entries[0]:
                    if int(year) in [2025, 2020, 2017, 2016]:
                        ra = entries[4]
                        dec = entries[5]
                        t0 = '24' + entries[6]
                        tE = entries[7]
                        u0 = entries[8]
                        Ibase = entries[10]
                        Ibase_err = 'None'
                    elif (int(year) <= 2024 and int(year) > 2020) \
                            or (int(year) <= 2019 and int(year) > 2017):
                        ra = entries[5]
                        dec = entries[6]
                        t0 = '24' + entries[7]
                        tE = entries[8]
                        u0 = entries[9]
                        Ibase = entries[11]
                        Ibase_err = 'None'
                    elif int(year) in [2015]:
                        ra = entries[8]
                        dec = entries[9]
                        t0 = '245' + entries[4]
                        tE = entries[5]
                        u0 = entries[6]
                        Ibase = entries[7]
                        Ibase_err = 'None'

                    events[entries[0]] = (ra, dec, t0, tE, u0, Ibase, Ibase_err)

        return events

    def fetch_alerts(self):
        logger.warning('Not implemented')

        return None

    def to_generic_alert(self):
        logger.warning('Not implemented')

        return None