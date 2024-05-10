from django.db import models
from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np

class EventMatchManager(models.Manager):
    """
    Return a Queryset for a Target within a specified radial separation
    """

    def check_for_radius_match(self, ra, dec, radius=2.0):
        """
        Returns a queryset matching by RA, Dec within the given radius
        """

        # Create SkyCoords for all known Targets and the current object
        targets = Target.objects.all()

        ra_list = [t.ra for t in targets]
        dec_list = [t.dec for t in targets]
        coords = SkyCoord(ra_list, dec_list, frame='icrs', unit=(u.deg, u.deg))

        s = SkyCoord(ra, dec, frame='icrs', unit=(u.deg, u.deg))

        # Identify all DB entries with an angular separation closer
        # than the radius in arcseconds:
        max_sep = Angle(float(radius) / 3600.0, unit=u.deg)

        sep = s.separation(coords)
        mask = np.where(sep <= max_sep)[0]

        # Extract a list of the names of these targets
        targets_list = list(targets)
        matching_events = [targets_list[j].name for j in mask]

        # Return a QuerySet with these Targets
        queryset = Target.objects.filter(name__in=matching_events)

        return queryset
