from tom_dataproducts.models import ReducedDatum
from django.core.exceptions import  ValidationError
from astroquery.vizier import Vizier
from astropy.coordinates import Angle
import astropy.units as u
from astropy.coordinates import SkyCoord
from mop.brokers import gaia as gaia_mop
from mop.toolbox import TAP, utilities, classifier_tools
from microlensing_targets.match_managers import validators
from astroquery.gaia import Gaia


#for a given mag computes new error-bar
#from Gaia DR2 papers, degraded by x10 (N=100 ccds), in log
def estimateGaiaError(mag) :

    a1=0.2
    b1= -5.3#-5.2
    log_err1 = a1*mag + b1
    a2=0.2625
    b2= -6.3625#-6.2625
    log_err2 = a2*mag + b2

    if (mag<13.5): expectedStdAtBaselineMag = 10**(a1*13.5+b1)
    if (mag>=13.5 and mag<17) : expectedStdAtBaselineMag = 10**log_err1
    if (mag>=17) : expectedStdAtBaselineMag = 10**log_err2
    #this works until 21 mag.

    return expectedStdAtBaselineMag

def update_gaia_errors(target):

    datasets = ReducedDatum.objects.filter(target=target)

    for i in datasets:

        if (i.data_type == 'photometry') & ("error" not in i.value.keys())  &  ('Gaia' in i.source_name):
           
            magnitude = i.value['magnitude']
            error = estimateGaiaError(magnitude)
            i.value['error'] = error 

            try:
                i.save()
            except ValidationError:
                pass

def query_gaia_tap_service(target, radius=Angle(0.00014, "deg"), row_limit=-1):
    """
    Function to query the Gaia TAP service.
    WARNING: this asynchronous query can be extremely slow and so is not
    suitable for automation
    """

    # Configure Gaia TAP parameters
    Gaia.ROW_LIMIT = row_limit
    Gaia.MAIN_GAIA_TABLE = "gaiadr3.gaia_source"

    # Establish centroid for the cone search at the target's location
    coord = SkyCoord(ra=target.ra, dec=target.dec, unit=(u.deg, u.deg), frame='icrs')

    # Send query to TAP service - note that this will wait to return results but
    # can take some time
    response = Gaia.cone_search_async(coord, radius=radius)

    # Parse the results
    if not response.failed:
        results = response.get_results()
        print(results)
        print(type(results))
        import pdb; pdb.set_trace()

def query_gaia_dr3(target, radius=Angle(0.00014, "deg"), row_limit=-1, Gmag_max=24.0):
    """Function to query the Gaia DR3 catalog for information on a target and stars nearby"""

    gaia_columns_list = ['Source', 'RA_ICRS', 'DE_ICRS',
                         'Gmag', 'e_Gmag',
                         'RPmag', 'e_RPmag',
                         'BPmag', 'e_BPmag',
                         'BP-RP', 'E(BP-RP)', 'AG', 'Dist', 'Teff', 'logg', '[Fe/H]', 'RUWE']

    v = Vizier(columns=gaia_columns_list)
    v.ROW_LIMIT = row_limit
    coord = SkyCoord(ra=target.ra, dec=target.dec, unit=(u.deg, u.deg), frame='icrs')
    result = v.query_region(coord, radius=radius, catalog='I/355/gaiadr3', column_filters={'Gmag': '<'+str(Gmag_max)})

    return result

def fetch_gaia_dr3_entry(target, radius=Angle(0.00014, "deg")):
    """Function to retrieve the Gaia photometry for a target and store it in the Target's ExtraParameters"""

    # Search the Gaia DR3 catalog:
    results = query_gaia_dr3(target, radius)
    if len(results) > 0:

        fields = {
            'Source': 'gaia_source_id',
            'Gmag': 'gmag',
            'e_Gmag': 'gmag_error',
            'RPmag': 'rpmag',
            'e_RPmag': 'rpmag_error',
            'BPmag': 'bpmag',
            'e_BPmag': 'bpmag_error',
            'BP-RP': 'bprp',
            'E(BP-RP)': 'reddening_bprp',
            'AG': 'extinction_g',
            'Dist':'distance',
            'Teff': 'teff',
            'logg': 'logg',
            '__Fe_H_': 'metallicity',
            'RUWE': 'ruwe'}

        for cat_field, mop_field in fields.items():
            try:
                if results[0][0][cat_field]:
                    setattr(target, mop_field, results[0][0][cat_field])
            except KeyError:
                pass

        target.save()

def ingest_event(name, ra, dec, debug=False):

    target, result = validators.get_or_create_event(
        name,
        ra,
        dec,
        debug=debug
    )

    if result == 'new_target':
        utilities.add_gal_coords(target)
        TAP.set_target_sky_location(target)
        classifier_tools.check_known_variable(target)
        fetch_gaia_dr3_entry(target)

        # Set the permissions on the targets so all OMEGA users can see them
        utilities.open_targets_to_OMEGA_team([target])

    return target, result