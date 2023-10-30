from astroquery.vizier import Vizier
from astropy.coordinates import Angle

from mop.toolbox import logs

def check_YSO(coord):
    '''
    This function checks if the target can be found in Marton et al. 2019, 2023
    YSO catalogs. For Marton et al. 2019, we classify the target as YSO if
    either of the probabilities in the catalog are larger than 0.9.

    :params coord: astropy SkyCoord with coordinates of the checked target
    :return: boolean if the target was found YSO catalogs
    '''

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

    return False

def check_QSO(coord):
    '''
    This function checks if the target appears within 2 arc sec of the Milliquas catalogue (Flesch et al 2021)
    or the Gaia DR3 AGN catalog (Carnerer et al. 2023).

    :params coord: astropy SkyCoord with coordinates of the checked target
    :return: boolean if the target was found QSO/AGN catalogs
    '''
    # check if in Flesch et al. 2021 Milliquas
    result1 = Vizier.query_region(coord, radius=Angle(2. / 60. / 60., "deg"), catalog='VII/290/catalog')
    # check if in GDR3 vari_agn, Carnerer et al. 2023
    result2 = Vizier.query_region(coord, radius=Angle(1. / 60. / 60., "deg"), catalog='I/358/vagn')

    if (len(result1) > 0):
        return True
    elif (len(result2) > 0):
        return True

    return False

def check_SN(coord):
    '''
    This function checks if the target appears within 1.5 arcsec of the GLADE+ catalog of galaxies.
    If yes, this could be a supernova.

    :params coord: astropy SkyCoord with coordinates of the checked target
    :return: boolean if the target was found the GLADE+ catalog (Dálya et al. 2022)
    '''
    # check if near galaxy in GLADE+ catalogue
    result = Vizier.query_region(coord, radius=Angle(1.5 / 60. / 60., "deg"), catalog='VII/281')

    if (len(result) > 0):
        return True

    return False