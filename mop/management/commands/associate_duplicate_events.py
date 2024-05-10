from django.core.management.base import BaseCommand
from tom_targets.models import Target, TargetMatchManager
from astropy.coordinates import SkyCoord, Angle
import astropy.units as u
import numpy as np

class Command(BaseCommand):
    help = 'Identify events with multiple Target entries'

    def add_arguments(self, parser):
        parser.add_argument('radius', help='Match radius in arcseconds')

    def handle(self, *args, **options):
        radius = Angle(float(options['radius'])/3600.0, unit=u.deg)

        targets = Target.objects.all()
        ra_list = [t.ra for t in targets]
        dec_list = [t.dec for t in targets]
        coords = SkyCoord(ra_list, dec_list, frame='icrs', unit=(u.deg, u.deg))

        s = SkyCoord(244.6058, -54.0788, frame='icrs', unit=(u.deg, u.deg))

        sep = s.separation(coords)
        mask = np.where(sep <= radius)[0]
        print(mask)

        targets_list = list(targets)
        matches = [targets_list[j].name for j in mask]
        print(matches)