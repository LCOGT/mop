from django.core.management.base import BaseCommand
from mop.brokers import gaia as MOPGaia
from tom_alerts.brokers import gaia
from astropy.coordinates import SkyCoord
from astropy import units as u

import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Downloads microlensing event list from the Gaia Alerts system'
    def add_arguments(self, parser):
        parser.add_argument('in_file', help='Path to the input CSV file of all Gaia alerts')
        parser.add_argument('out_file', help='Path to output file')

    def handle(self, *args, **options):
        """
        Function to parse the complete list of Gaia alerts from a downloaded CSV file
        into the standardized catalog format.
        Note that although the Gaia broker is available to query the Gaia alerts system,
        this system is now inactive and very slow to load.
        """
        logger.info('Starting run of Gaia alerts parser')

        # Load the full list of Gaia alerts
        events = {}
        with open(options['in_file'], 'r') as f:
            line_list = f.readlines()

            for line in line_list[1:]:
                entries = line.replace('\n','').split(',')
                if len(entries) > 1:
                    name = entries[0]
                    ra = entries[2]
                    dec = entries[3]
                    Ibase = entries[5]
                    if len(Ibase) == 0:
                        Ibase = 'None'

                    s = SkyCoord(ra, dec, frame='icrs', unit=(u.deg, u.deg))
                    sexig = s.to_string('hmsdms')
                    ra = sexig.split()[0].replace('h',':').replace('m',':').replace('s','')
                    dec = sexig.split()[1].replace('d',':').replace('m',':').replace('s','')
                    comment = str(entries[-2]).lower()

                    if 'microlensing' in comment:
                        events[name] = (ra, dec, 'None', 'None', 'None', Ibase, 'None')

        # Output to text file
        with open(options['out_file'], 'w') as f:
            f.write('# Name  RA   Dec  t0[HJD]  tE[days]    u0    Ibase    Ibase_err\n')

            for name, params in events.items():
                f.write(name + ' ' + ' '.join(params) + '\n')
