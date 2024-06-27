from django.core.management.base import BaseCommand
from tom_alerts.brokers import gaia
from tom_targets.models import Target
from mop.brokers import gaia as gaia_mop
import requests
from requests.exceptions import HTTPError
from tom_dataproducts.models import ReducedDatum
from datetime import datetime
from astropy.time import Time, TimezoneInfo
from mop.toolbox import TAP, utilities, classifier_tools
import logging

logger = logging.getLogger(__name__)


BASE_BROKER_URL = gaia.BASE_BROKER_URL


class MOPGaia(gaia.GaiaBroker):

    def process_reduced_data(self, target, alert=None):
        if not alert:
            try:
                alert = self.fetch_alert(target.name)

            except HTTPError:
                raise Exception('Unable to retrieve alert information from broker')

        if alert:
            alert_name = alert['name']
            alert_link = alert.get('per_alert', {})['link']
            lc_url = f'{BASE_BROKER_URL}/alerts/alert/{alert_name}/lightcurve.csv'
            alert_url = f'{BASE_BROKER_URL}/{alert_link}'
        elif target:
            lc_url = f'{BASE_BROKER_URL}/{target.name}/lightcurve.csv'
            alert_url = f'{BASE_BROKER_URL}/alerts/alert/{target.name}/'
        else:
            return

        try:
            response = requests.get(lc_url)
            response.raise_for_status()
            html_data = response.text.split('\n')

            try:
                times = [Time(i.timestamp).jd for i in ReducedDatum.objects.filter(target=target) if i.data_type == 'photometry']
            except:
                times = []

            for entry in html_data[2:]:
                phot_data = entry.split(',')

                if len(phot_data) == 3:

                    jd = Time(float(phot_data[1]), format='jd', scale='utc')
                    jd.to_datetime(timezone=TimezoneInfo())

                    if ('untrusted' not in phot_data[2]) and ('null' not in phot_data[2]) and (jd.value not in times):

                        value = {
                        'magnitude': float(phot_data[2]),
                        'filter': 'G'
                        }

                        rd, created = ReducedDatum.objects.get_or_create(
                                timestamp=jd.to_datetime(timezone=TimezoneInfo()),
                                value=value,
                                source_name=self.name,
                                source_location=alert_url,
                                data_type='photometry',
                                target=target)

            (t_last_jd, t_last_date) = TAP.TAP_time_last_datapoint(target)
            target.latest_data_hjd = t_last_jd
            target.latest_data_utc = t_last_date
            target.save()

        except requests.exceptions.HTTPError:
            pass

        return



class Command(BaseCommand):

    help = 'Downloads Gaia data for all events marked as microlensing candidate'
    def add_arguments(self, parser):

        parser.add_argument('events', help='name of a specific event or all')

    def handle(self, *args, **options):
        logger.info('Gaia Harvester started run at ' + str(datetime.utcnow()))

        Gaia = MOPGaia()

        try:
            if str(options['events']).lower() == 'all':
                (list_of_alerts, broker_feedback) = Gaia.fetch_alerts({'target_name':None, 'cone':None})
            else:
                (list_of_alerts, broker_feedback) = Gaia.fetch_alerts({'target_name': options['events'], 'cone': None})
        except requests.exceptions.ConnectionError:
            logger.error('Connection error: cannot reach Gaia Alerts server')
            exit()

        new_alerts = []
        for alert in list_of_alerts:
            logger.info('Gaia Harvester: gathering data for ' + repr(alert['name']))

            # As of Oct 2022, Gaia alerts will no longer be providing the
            # microlensing class as a comment in the alert.  We therefore
            # switched to downloading all Gaia alerts
            # if 'microlensing' in alert['comment']:

            # Check for duplication first
            clean_alert = Gaia.to_generic_alert(alert)

            target, result = gaia_mop.ingest_event(
                clean_alert.name,
                float(clean_alert.ra),
                float(clean_alert.dec)
            )
            if result == 'new_target':
                new_alerts.append(target)

            Gaia.process_reduced_data(target, alert=alert)
            gaia_mop.update_gaia_errors(target)

        logger.info('Gaia Harvester finished run at ' + str(datetime.utcnow()))