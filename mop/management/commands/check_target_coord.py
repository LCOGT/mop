from django.core.management.base import BaseCommand
from tom_targets.models import Target
from astropy import units as u
from astropy.coordinates import SkyCoord
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check all targets have valid RA and Dec'

    def handle(self, *args, **options):

        targets = Target.objects.filter()
        logger.info('Checking list of ' + str(targets.count()) + ' targets')

        for t in targets:
            try:
                s = SkyCoord(ra=t.ra * u.degree, dec=t.dec * u.degree, frame='icrs')

            except:
                logger.info(t.name + ' has suspect coordinates')
