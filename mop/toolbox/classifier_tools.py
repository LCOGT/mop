from astroquery.vizier import Vizier
from astropy.coordinates import Angle, SkyCoord
from astropy import units as u
from mop.brokers import tns
import logging
import requests
import numpy as np

logger = logging.getLogger(__name__)

def check_YSO(coord):
    '''
    This function checks if the target can be found in Marton et al. 2019, 2023
    YSO catalogs. For Marton et al. 2019, we classify the target as YSO if
    either of the probabilities in the catalog are larger than 0.9.

    :params coord: astropy SkyCoord with coordinates of the checked target
    :return: boolean if the target was found YSO catalogs
    '''

    try:
        Vizier.cache_location = None
        # check if in Konkoly YSO catalogue, Marton et al. 2023
        result1 = Vizier.query_region(coord, radius=Angle(1. / 60. / 60., "deg"), catalog='J/A+A/674/A21/kyso')
        # Marton et al 2019 YSOs
        result2 = Vizier.query_region(coord, radius=Angle(1. / 60. / 60., "deg"), catalog='II/360/catalog')

        if(len(result1) > 0):
            return True
        elif(len(result2) > 0):
            table = result2[0]
            for k in range(len(table)):
                ly = table['LY'].data.data[k]
                sy = table['SY'].data.data[k]
                if(ly>0.9 or sy>0.9):
                    return True
    except requests.exceptions.ConnectionError:
        logger.error('ConnectionError while querying Vizier')

    return False

def check_QSO(coord):
    '''
    This function checks if the target appears within 2 arc sec of the Milliquas catalogue (Flesch et al 2021)
    or the Gaia DR3 AGN catalog (Carnerer et al. 2023).

    :params coord: astropy SkyCoord with coordinates of the checked target
    :return: boolean if the target was found QSO/AGN catalogs
    '''

    try:
        Vizier.cache_location = None
        # check if in Flesch et al. 2021 Milliquas
        result1 = Vizier.query_region(coord, radius=Angle(2. / 60. / 60., "deg"), catalog='VII/290/catalog')
        # check if in GDR3 vari_agn, Carnerer et al. 2023
        result2 = Vizier.query_region(coord, radius=Angle(1. / 60. / 60., "deg"), catalog='I/358/vagn')

        if (len(result1) > 0):
            return True
        elif (len(result2) > 0):
            return True

    except requests.exceptions.ConnectionError:
        logger.error('ConnectionError while querying Vizier')

    return False

def check_galaxy(coord):
    '''
    This function checks if the target appears within 1.5 arcsec of the GLADE+ catalog of galaxies.
    If yes, this could be a supernova.

    :params coord: astropy SkyCoord with coordinates of the checked target
    :return: boolean if the target was found the GLADE+ catalog (Dálya et al. 2022)
    '''

    try:
        Vizier.cache_location = None
        # check if near galaxy in GLADE+ catalogue
        result = Vizier.query_region(coord, radius=Angle(1.5 / 60. / 60., "deg"), catalog='VII/281')

        if (len(result) > 0):
            return True

    except requests.exceptions.ConnectionError:
        logger.error('ConnectionError while querying Vizier')

    return False

def check_tns(coord):
    """
    Function to query the Transient Name Service to see if a target is already known to them
    """

    tns_results = {'TNS_name': 'None', 'TNS_class': 'None'}

    # Search TNS for objects at these coordinates
    parameters = {
        'ra': coord.ra.value,
        'dec': coord.dec.value,
        'radius': 1.0,
        'units': 'arcsec',
    }

    tns_object = tns.Custom_TNS
    tns_name = tns.Custom_TNS.fetch_tns_name(tns_object, parameters)

    # If at least one name is known for this object, search for a classification
    # if any is available.  Note here we search on the last name in the list, in
    # case more than one is returned rather than cycling through the whole list
    if len(tns_name) > 0:
        full_name = ';'.join(tns_name)

        tns_results['TNS_name'] = full_name

        parameters = {
            'objname': tns_name[-1]
        }
        tns_class = tns.Custom_TNS.fetch_tns_class(tns_object, parameters)

        if tns_class:
            tns_results['TNS_class'] = str(tns_class)

    return tns_results

def check_known_variable(target, coord=None):
    """
    Function to check whether a target is known to existing catalogs of Young Stellar Objects,
    Quasi-stellar Objects and galaxies.
    """
    if not coord:
        coord = SkyCoord(target.ra, target.dec, frame='icrs', unit=(u.deg, u.deg))

    yso = check_YSO(coord)
    qso = check_QSO(coord)
    gal = check_galaxy(coord)
    tns_results = check_tns(coord)

    extra_params = {
        'YSO': yso,
        'QSO': qso,
        'galaxy': gal,
        'TNS_name': tns_results['TNS_name'],
        'TNS_class': tns_results['TNS_class']
    }

    # If any of these flags are true, the target cannot be a microlensing target,
    # so re-classify
    if yso:
        extra_params['Classification'] = 'Variable star'
        extra_params['Category'] = 'Stellar activity'
    if qso or gal:
        extra_params['Classification'] = 'Extra-galactic variable'
    if qso:
        extra_params['Category'] = 'Active Galactic Nucleus'
    elif gal:
        extra_params['Category'] = 'Galaxy'
    if 'none' not in str(extra_params['TNS_name']).lower():
        if 'none' not in str(extra_params['TNS_class']).lower():
            extra_params['Classification'] = extra_params['TNS_class']
            extra_params['Category'] = extra_params['TNS_class']
        #     extra_params['Classification'] = 'Known transient'
        #     extra_params['Category'] = 'Unclassified'

    target.save(extras=extra_params)

def check_valid_blend(blend_field):
    if blend_field == None or blend_field == 0.0:
        return False

    return True

def check_valid_u0(u_0_field):
    if abs(u_0_field) > 0.5:
        return False

    return True

def check_valid_dmag(mulens):
    """Function to find the brightest valid photometric measurement from all available
    lightcurves, and use it to estimate the change in magnitude from the baseline.
    If the change is < 0.5, return False, as the target has not brightened enough to be
    considered for follow-up.  If > 0.5mag, return True.
    """

    if len(mulens.datasets) > 0:

        peak_mag = 50.0
        for passband, lc in mulens.datasets.items():
            idx = np.where(lc[:,1] > 0.0)
            if lc[idx].min() < peak_mag:
                peak_mag = lc[idx].min()

        delta_mag = float(mulens.extras['Baseline_magnitude'].value) - peak_mag

        if delta_mag < 0.5:
            return False
    else:
        return False

    return True

def check_valid_chi2sq(mulens):
    if 'red_chi2' in mulens.extras.keys():
        if float(mulens.extras['red_chi2'].value) > 50.0 \
                or float(mulens.extras['red_chi2'].value) < 0.0:
            return False

    else:
        return False

    return True