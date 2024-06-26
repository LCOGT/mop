from django.db import models
from tom_targets.base_models import TargetMatchManager

class EventMatchManager(TargetMatchManager):
    """
    Return a Queryset for a Target within a specified radial separation
    """

    def match_target(self, target, *args, **kwargs):
        """
        Overrides the default name-matching for duplicate targets and
        returns a queryset matching by RA, Dec within a radius of 2 arcsec
        """
        search_radius = 2.0 # arcsec

        cone_search_queryset = self.match_cone_search(target.ra, target.dec, search_radius)

        return cone_search_queryset
