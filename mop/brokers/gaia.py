from tom_dataproducts.models import ReducedDatum
from django.core.exceptions import  ValidationError
from astroquery.vizier import Vizier
from astropy.coordinates import Angle
import astropy.units as u
from astropy.coordinates import SkyCoord

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

def query_gaia_dr3(target, radius=Angle(0.004, "deg"), row_limit=-1, Gmag_max=24.0):
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

def fetch_gaia_dr3_entry(target):
    """Function to retrieve the Gaia photometry for a target and store it in the Target's ExtraParameters"""

    # Search the Gaia DR3 catalog:
    results = query_gaia_dr3(target)

    if len(results) > 0:

        fields = {
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
            '[Fe/H]': 'metallicity',
            'RUWE': 'ruwe'}

        for cat_field, mop_field in fields.items():
            try:
                if results[0][0][cat_field]:
                    setattr(target, mop_field, results[0][0][cat_field])
            except KeyError:
                pass

        target.save()
