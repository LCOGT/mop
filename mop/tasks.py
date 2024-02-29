import dramatiq
from tom_targets.models import Target, TargetExtra
from tom_observations.utils import get_sidereal_visibility
from astropy.coordinates import SkyCoord
from astropy import units as u
import numpy as np
import numpy as np
import logging

logger = logging.getLogger(__name__)

@dramatiq.actor
def get_target_visibility_from_site(object, observatory, start_time, end_time,
                                    airmass_max=2.0, visibiliy_intervals = 10):
    """
    Function calculates the visibility of a given Target for the indicated site and date,
    and returns a list of occasions when it can be observed, annotated with extra_field data
    """

    t1 = datetime.utcnow()

    # Use the TOM Toolkit's built-in function to calculate the target's visibiliy
    visibility_data = get_sidereal_visibility(
        object, start_time, end_time,
        visibiliy_intervals, airmass_max,
        observation_facility=observatory
    )

    t2 = datetime.utcnow()
    logger.info('get_target_visibility: Visibility calculation, took ' + repr(t2 - t1))

    # If the target is visible, collect the requested extra_field parameters, as
    # configured in the settings.py
    for site, vis_data in visibility_data.items():
        airmass_data = np.array([x for x in vis_data[1] if x])
        if len(airmass_data) > 0:
            s = SkyCoord(object.ra, object.dec, frame='icrs', unit=(u.deg, u.deg))
            target_data = [
                object.name, s.ra.to_string(u.hour), s.dec.to_string(u.deg, alwayssign=True),
                site, round(airmass_data.min(), 1)
            ]

            # Extract any requested extra parameters for this object, if available
            for param in settings.SELECTION_EXTRA_FIELDS:
                if param in object.extra_fields.keys():
                    target_data.append(object.extra_fields[param])
                else:
                    target_data.append(None)
            observable_targets.append(target_data)

    t3 = datetime.utcnow()
    logger.info('get_target_visibility: completed in ' + repr(t3 - t1))

    return observable_targets