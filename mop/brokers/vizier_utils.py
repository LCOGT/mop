from astroquery.vizier import Vizier
from astropy.coordinates import Angle
import astropy.units as u
from astropy.coordinates import SkyCoord

def query_vizier(target, catalog, column_list, radius=Angle(0.0083, "deg"), row_limit=-1):
    """
    Function to perform a general-purpose Vizier search centred on the coordinates of a Target.
    Parameters:
        target  TOM Target object   Provides the RA, Dec used for the centroid of the search
        catalog string              Vizier identifier of the catalogue to searched
        column_list list            List of the column names to be returned
        radius  Angle               Search radius, default=30arcsec
        row_limit int               Max number of catalogue rows to be returned, default=-1 (unlimited)

    Returns:
        Vizier table
    """

    v = Vizier(columns=column_list)
    v.cache_location = None
    v.ROW_LIMIT = row_limit
    coord = SkyCoord(ra=target.ra, dec=target.dec, unit=(u.deg, u.deg), frame='icrs')
    result = v.query_region(coord, radius=radius, catalog=catalog)

    return result