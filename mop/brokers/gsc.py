from astropy.coordinates import Angle, SkyCoord
from astropy import units as u
from astropy.table import Table, Column
from mop.brokers import vizier_utils
import numpy as np

def query_gsc(target, radius=Angle(0.0083, "deg"), row_limit=-1):
    """Function to perform a Vizier search of the Guide Star Catalogue v2.4.2, I/353"""

    # Note that +_r in the radius column name returns search results ordered in
    # ascending radius from the target
    column_list = ['GSC2', 'RA_ICRS', 'DE_ICRS',
                         'Gmag', 'e_Gmag',
                         'Bmag', 'e_Bmag',
                         'Vmag', 'e_Vmag',
                         'Jmag', 'e_Jmag',
                         'Hmag', 'e_Hmag',
                         'Ksmag', 'e_Ksmag',
                         'W1mag', 'e_W1mag',
                         '+_r', 'pmRA', 'pmDE', 'plx']

    result = vizier_utils.query_vizier(target, 'I/353', column_list, radius=radius, row_limit=row_limit)

    if len(result) == 1:
        result = result[0]
    else:
        result = None

    return result

def verify_Ksmag_data(gsc_table):
    """
    Function estimate a magnitude in Ks-band from data in other filters, if no catalog value is available.
    Parameters:
        gsc_entry   vizier table   Table returned from GSC Vizier query
    Returns
        gsc_entry   vizier table    with missing Ksmag, e_Ksmag entries filled
    """
    # List of functions to call to estimate Ks-band data if needed
    calibrations = [Ksmag_from_JH, Ksmag_from_HW1, Ksmag_from_JW1, Ksmag_from_JHW1]

    # If all entries in the GSC catalog for nearby stars have valid Ks-band data, use these data
    # and make no further changes
    if (gsc_table['Ksmag'].mask).all():
        return gsc_table

    # If not, use a set of survey-calibrated relationships to estimate Ks-band values for the missing entries
    else:
        findex = 0
        while findex < len(calibrations):

            missing_entries = np.where(gsc_table['Ksmag'].mask)[0]

            if len(missing_entries) > 0:
                gsc_table = calibrations[findex](gsc_table, missing_entries)

            findex += 1

    return gsc_table

def find_missing_entries_with_phot(gsc_table, missing_entries, band1, band2, band3=None):
    """
    Function to return an index of the table entries where Ks-band data are missing,
    but sufficient data are available in other passbands to estimate a value based on
    photometric calibrations
    Parameters:
        gsc_table  MaskedTable  Catalog query table
        missing_entries list    Indices of query table where Ks-band magnitudes are missing
        band1       string      Catalog column name for first passband used to calculate Ks magnitudes
        band2       string      Catalog column name for second passband
    Returns:
        idx         list        Indices of gsc_table of entries where Ks mags can be estimated from the bands
    """
    idx1 = np.where(gsc_table[band1].mask == False)[0]
    idx2 = np.where(gsc_table[band2].mask == False)[0]
    idx = set(missing_entries).intersection(set(idx1))
    idx = idx.intersection(set(idx2))

    if band3:
        idx3 = np.where(gsc_table[band3].mask == False)[0]
        idx = idx.intersection(set(idx3))

    return list(idx)

def Ksmag_from_JH(gsc_table, missing_entries):

    # Identify catalog entries where Ks-band measurements are missing, but J and H-band data are available
    idx = find_missing_entries_with_phot(gsc_table, missing_entries, 'Jmag', 'Hmag')

    # Estimate Ks-band magnitudes given each star's J and H-band photometry
    gsc_table['Ksmag'][idx] = gsc_table['Hmag'][idx] + 0.2 * (gsc_table['Jmag'][idx] - gsc_table['Hmag'][idx])

    # Remove the masking of the newly-calculated Ksmag entries
    gsc_table['Ksmag'].mask[idx] = False

    return gsc_table

def Ksmag_from_HW1(gsc_table, missing_entries):

    # Identify catalog entries where Ks-band measurements are missing, but H and W1-band data are available
    idx = find_missing_entries_with_phot(gsc_table, missing_entries, 'Hmag', 'W1mag')

    # Estimate Ks-band magnitudes given each star's H and W1-band photometry
    gsc_table['Ksmag'][idx] = 0.5 * gsc_table['Hmag'][idx] + 0.5 * gsc_table['W1mag'][idx]

    # Remove the masking of the newly-calculated Ksmag entries
    gsc_table['Ksmag'].mask[idx] = False

    return gsc_table

def Ksmag_from_JW1(gsc_table, missing_entries):

    # Identify catalog entries where Ks-band measurements are missing, but J and W1-band data are available
    idx = find_missing_entries_with_phot(gsc_table, missing_entries, 'Hmag', 'W1mag')

    # Estimate Ks-band magnitudes given each star's J and W1-band photometry
    gsc_table['Ksmag'][idx] = 0.2 * gsc_table['Jmag'][idx] + 0.8 * gsc_table['W1mag'][idx]

    # Remove the masking of the newly-calculated Ksmag entries
    gsc_table['Ksmag'].mask[idx] = False

    return gsc_table

def Ksmag_from_JHW1(gsc_table, missing_entries):

    # Identify catalog entries where Ks-band measurements are missing, but J and W1-band data are available
    idx = find_missing_entries_with_phot(gsc_table, missing_entries, 'Jmag', 'Hmag', band3='W1mag')

    # Estimate Ks-band magnitudes given each star's J and W1-band photometry
    gsc_table['Ksmag'][idx] = 0.2 * gsc_table['Jmag'][idx] + 0.5 * gsc_table['Hmag'][idx] + 0.3 * gsc_table['W1mag'][idx]

    # Remove the masking of the newly-calculated Ksmag entries
    gsc_table['Ksmag'].mask[idx] = False

    return gsc_table

def select_AO_stars(gsc_table, gmax=14.5, distmax=30):
    """
    Stars are selected as Adaptive Optics stars if they have valid G-band magnitude data brighter than the given maximum
    (default 14.5mag), and lie within a distmax angular separation (default 30arcsec)
    The gsc_table is given and returned with an addition column of integer values where 1 indicates that a star
    has been selected, otherwise 0.
    """

    # Distmax needs to be in degrees to be compared with the table data
    distmax = distmax/3600.0

    # If the gsc_table currently has no column named AO, add it to the table
    if 'AOstar' not in gsc_table.colnames:
        gsc_table['AOstar'] = np.zeros(len(gsc_table))

    # Identify suitable stars
    idx1 = np.where(gsc_table['Gmag'] <= gmax)[0]
    idx2 = np.where(gsc_table['_r'] <= distmax)[0]
    idx = list(set(idx1).intersection(set(idx2)))

    # Annotate the table where stars are selected
    gsc_table['AOstar'][idx] = 1.0

    return gsc_table

def select_FT_stars(gsc_table, Ksmax=10.5, distmax=30):
    """
    Stars are selected as Fringe Tracker stars if they have valid Ks-band magnitudes brighter than the given maximum
    (default 10.5mag),  and lie within a distmax angular separation (default 30arcsec)
    The gsc_table is given and returned with an addition column of integer values where 1 indicates that a star
    has been selected, otherwise 0.
    """

    # Distmax needs to be in degrees to be compared with the table data
    distmax = distmax / 3600.0

    # Add a column for FTstars to the table if none already exists:
    if 'FTstar' not in gsc_table.colnames:
        gsc_table['FTstar'] = np.zeros(len(gsc_table))

    # Identify suitable stars
    idx1 = np.where(gsc_table['Ksmag'] <= Ksmax)[0]
    idx2 = np.where(gsc_table['_r'] <= distmax)[0]
    idx = list(set(idx1).intersection(set(idx2)))

    # Annotate the table where stars are selected
    gsc_table['FTstar'][idx] = 1.0

    return gsc_table

def calc_mutual_separations(gsc_table, AOFT_table):
    """
    Function to calculate the mutual separations between the selected Adaptive Optics and Fringe Tracker candidates
    """
    AOidx = np.where(gsc_table['AOstar'] > 0.0)[0]
    FTidx = np.where(gsc_table['FTstar'] > 0.0)[0]

    AOcat = SkyCoord(ra=gsc_table['RA_ICRS'][AOidx].data,
                     dec=gsc_table['DE_ICRS'][AOidx].data,
                     frame='icrs', unit=(u.deg, u.deg))
    FTcat = SkyCoord(ra=gsc_table['RA_ICRS'][FTidx].data,
                     dec=gsc_table['DE_ICRS'][FTidx].data,
                     frame='icrs', unit=(u.deg, u.deg))

    for j,itable in enumerate(AOidx):
        if len(AOcat) > 1:
            s = AOcat[j]
        else:
            s = AOcat
        separations = s.separation(FTcat)

        AOFT_table[gsc_table['GSC2'][itable]+'_FT_separation'] = separations

    return AOFT_table

def create_AOFT_table(gsc_table):
    """
    Function to create a grid of the FT and AO stars
    """
    AOidx = np.where(gsc_table['AOstar'] > 0.0)[0]
    FTidx = np.where(gsc_table['FTstar'] > 0.0)[0]

    columns = [
        Column(name='FTstar', data=gsc_table['GSC2'][FTidx]),
        Column(name='SC_separation', data=gsc_table['_r'][FTidx]),
        Column(name='Ksmag', data=gsc_table['Ksmag'][FTidx]),
        Column(name='SC_Vloss', data=np.zeros(len(FTidx)))
    ]
    for i in AOidx:
        columns.append( Column(name=gsc_table['GSC2'][i]+'_SCstrehl', data=np.zeros(len(FTidx))) )
        columns.append( Column(name=gsc_table['GSC2'][i]+'_FTstrehl', data=np.zeros(len(FTidx))) )
        columns.append( Column(name=gsc_table['GSC2'][i]+'_Gmag', data=np.array([gsc_table['Gmag'][i]]*len(FTidx))) )
        columns.append( Column(name=gsc_table['GSC2'][i]+'_SC_separation', data=np.array([gsc_table['_r'][i]]*len(FTidx))) )
        columns.append( Column(name=gsc_table['GSC2'][i]+'_Ksmag', data=np.array([gsc_table['Ksmag'][i]]*len(FTidx))) )
        columns.append( Column(name=gsc_table['GSC2'][i]+'_FT_separation', data=np.zeros(len(FTidx))) )

    return Table(columns)

def AOstrehl(mag, dist, wfs='visible'):
    """
    Function to calculate the expected Strehl ratio of a guide star, based on its angular separation from
    the science target star.

    This function is based on data given in the VLTI User Manual:
    http://www.eso.org/sci/facilities/paranal/telescopes/vlti/documents/VLT-MAN-ESO-15000-4552_v111.pdf

    If the default Wavefront Sensor of 'visible' is used, then the function returns the MACAO Strehl ratio in Ks band,
    derived from an interpolation of data in Figure 5 of the manual.

    If the WFS is set to 'ir' then, the CIAO Strehl ratio is returned, determined as a function of Ks mag, based
    on interpolating data from Figure 7.

    Parameters:
        mag     float   Guide star magnitude in band (G for visible, Ks for NIR)
        dist    float   Angular separation from AO star, in arcsec
        wfs     str     Wavefront sensor type, 'visible' (default) or 'ir'

    Returns:
        strehl  float   Strehl ratio value.  Set to NAN if the WFS option parsed is invalid.

    Based on code by Antoine Merand
    """
    wfs = str(wfs).lower()
    if wfs not in ['visible', 'ir']:
        return np.nan

    if wfs == 'visible':
        strehl = np.interp(mag, [-10,   6,   9,    11, 13.5, 14,  14.5, 15, 15.5, 100],
                           [0.4, 0.4, 0.37, 0.35, 0.31, 0.2, 0.15, 0.1,   0,   0])

    elif wfs == 'ir':
        strehl = np.interp(mag, [-10,   7,   8, 9, 10, 10.5, 100],
                           [0.6, 0.6, 0.55, 0.4, 0.1, 0, 0])

    strehl *= np.interp(dist, [0, 5,   10, 15, 20, 28, 30, 35, 45],
                         [1, 0.8, 0.6, 0.4, 0.3, 0.2, 0.15, 0.1, 0.05])

    return strehl

def calc_Vloss(dist, seeing=0.6, theta0=None, D=820):
    """
    Function to calculate the Strehl ratio loss due to anisoplanetism as a function of angular separation
    Based on data in the VLTI Users Manual
    http://www.eso.org/sci/facilities/paranal/telescopes/vlti/documents/VLT-MAN-ESO-15000-4552_v111.pdf
    and
    data for the isoplanetic angle measured for GRAVITY and seeing in Paranel, taken from
    GRAVITY+ Collaboration, 2022, A&A, 665, A75: https://www.aanda.org/articles/aa/pdf/2022/09/aa43941-22.pdf

    Parameters:
        dist    float   Angular distance from FT star, in arcsec
        seeing  float   Seeing in arcsec (at 500nm) [default=0.6]
        theta0  float   Isoplanetic angle in arcsec (at 500nm) [default=None]
        D       float   Telescope diameter in cm [default=820cm]

    Returns:
        Vloss   float   Strehl ratio loss
    Based on code by Antoine Merand
    """

    if theta0 is None:
        # -- isolplanetic angle measured in Paranal (K band), from Gwide commissioning
        # https://www.aanda.org/articles/aa/pdf/2022/09/aa43941-22.pdf
        # table 3
        # c = np.polyfit(np.log([0.52, 0.62, 0.76]), np.log([3.01, 2.48, 1.96]), 1)
        c = [-1.13111414, 0.36411506]
        theta0 = np.exp(np.polyval(c, np.log(seeing)))

    # -- r0 in cm at 500nm based on seeing
    r0 = 0.98 * 0.5e-6 / (seeing * np.pi / 180 / 3600) * 1e2
    # print('theta0=%.1f", r0=%.1fcm at 500nm'%(theta0, r0))

    wl = 2.2  # wavelength in um for Gwide
    r0 *= (wl / 0.5) ** (6 / 5)
    theta0 *= (wl / 0.5) ** (6 / 5)

    # print('theta0=%.1f", r0=%.1fcm at %.1fum'%(theta0, r0, wl))
    sig_p = 0.12 * np.pi ** (1 / 3) * wl * (D / r0) ** (-1 / 6) * dist / theta0
    Vloss = np.exp(-2 * np.pi ** 2 / wl ** 2 * sig_p ** 2)

    return Vloss
def populate_AOFT_table(gsc_table, AOFT_table):
    """
    Function to populate the Strehl ratio entries of the table of AO and FT stars
    """
    AOidx = np.where(gsc_table['AOstar'] > 0.0)[0]
    FTidx = np.where(gsc_table['FTstar'] > 0.0)[0]
    maxStrehl = 40

    # Calculate mutual separations between all selected AO and FT stars
    AOFT_table = calc_mutual_separations(gsc_table, AOFT_table)

    # Calculate the Strehl ratio for each of the AO stars, based on their separations from the science target
    for na, j in enumerate(AOidx):
        AOFT_table[gsc_table['GSC2'][j]+'_SCstrehl'] = 100*AOstrehl(gsc_table['Gmag'][j],
                                                                    gsc_table['_r'][j]*3600.0,
                                                                    wfs='visible')

        # Calculate the Strehl ratio for each of the FT stars, based on their separations from all of the AO stars
        # Use the ratio of this value with the maxStrehl to adjust the expected Ks magnitude value
        for nf, i in enumerate(FTidx):
            FTstrehl = 100*AOstrehl(gsc_table['Gmag'][j],
                                    AOFT_table[gsc_table['GSC2'][j] + '_FT_separation'][nf]*3600.0,
                                    wfs='visible')
            AOFT_table[gsc_table['GSC2'][j] + '_FTstrehl'][nf] = FTstrehl

            kmag = AOFT_table['Ksmag'][nf]
            kmag = kmag - 2.5 * np.log10(FTstrehl / maxStrehl)
            AOFT_table[gsc_table['GSC2'][j] + '_Ksmag'][nf] = kmag

    # Calculate the Strehl ratio loss for each FT star
    vloss = calc_Vloss(dist=AOFT_table['SC_separation']*3600.0)
    AOFT_table['SC_Vloss'] = 100*vloss

    return AOFT_table