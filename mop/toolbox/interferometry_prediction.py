from tom_dataproducts.models import ReducedDatum
from django.conf import settings
from astropy.coordinates import SkyCoord
from astropy import units as u
from mop.brokers import gaia, gsc
from mop.toolbox import utilities
import numpy as np
import matplotlib.pyplot as plt
from astroquery.vizier import Vizier
from astropy.coordinates import Angle
from astropy.table import Table, Column
from astropy.time import Time, TimezoneInfo
import logging
from datetime import datetime
from mop import settings

logger = logging.getLogger(__name__)

def unmask_column(mColumn):
    """Gaia catalog searches can return MaskedColumns, which cannot easily be converted. This function
    extracts the data"""

    data = np.zeros(len(mColumn))
    mask = np.where(mColumn.mask == False)
    data[mask] = mColumn.data[mask]

    return data

def find_companion_stars(target, star_catalog):
    """Function to identify stars nearby to the target that have JHK brightneses high enough
    for inteferometry.  """

    # Identifies stars with valid photometry in all passbands
    try:
        mask = ~star_catalog[0]['Gmag'].data.mask & ~star_catalog[0]['BP-RP'].data.mask

        # For this subset of stars, calculates the angular separation between each star and the target
        # Note: this is the wrong formula
        star = SkyCoord(target.ra, target.dec, frame='icrs', unit=(u.deg, u.deg))
        neighbours = SkyCoord(star_catalog[0][mask]['RA_ICRS'].data.data,
                              star_catalog[0][mask]['DE_ICRS'].data.data,
                              frame='icrs', unit=(u.deg, u.deg))
        separations = star.separation(neighbours)

        # Sort into order of ascending distance from the target:
        index = np.argsort(separations)

        # Estimate photometric uncertainties on Gaia photometry
        BPmag_error = unmask_column(star_catalog[0][mask]['e_BPmag'][index])
        RPmag_error = unmask_column(star_catalog[0][mask]['e_RPmag'][index])
        BPRP_error = np.sqrt( BPmag_error*BPmag_error + RPmag_error*RPmag_error )

        # Returns lists of the star subset's photometry in order of ascending distance from
        # the target
        column_list = [
            Column(name='Gaia_Source_ID', data=star_catalog[0][mask]['Source'][index]),
            Column(name='Gmag', data=unmask_column(star_catalog[0][mask]['Gmag'][index])),
            Column(name='Gmag_error', data=unmask_column(star_catalog[0][mask]['e_Gmag'][index])),
            Column(name='BPmag', data=unmask_column(star_catalog[0][mask]['BPmag'][index])),
            Column(name='BPmag_error', data=BPmag_error),
            Column(name='RPmag', data=unmask_column(star_catalog[0][mask]['RPmag'][index])),
            Column(name='RPmag_error', data=RPmag_error),
            Column(name='BP-RP', data=unmask_column(star_catalog[0][mask]['BP-RP'][index])),
            Column(name='BP-RP_error', data=BPRP_error),
            Column(name='Reddening(BP-RP)', data=unmask_column(star_catalog[0][mask]['E_BP-RP_'][index])),
            Column(name='Extinction_G', data=unmask_column(star_catalog[0][mask]['AG'][index])),
            Column(name='Distance', data=unmask_column(star_catalog[0][mask]['Dist'][index])),
            Column(name='Teff', data=unmask_column(star_catalog[0][mask]['Teff'][index])),
            Column(name='logg', data=unmask_column(star_catalog[0][mask]['logg'][index])),
            Column(name='[Fe/H]', data=unmask_column(star_catalog[0][mask]['__Fe_H_'][index])),
            Column(name='RUWE', data=unmask_column(star_catalog[0][mask]['RUWE'][index])),
            Column(name='Separation', data=separations[index])
        ]
    except IndexError:
        column_list = [
            Column(name='Gaia_Source_ID', data=np.array([])),
            Column(name='Gmag', data=np.array([])),
            Column(name='Gmag_error', data=np.array([])),
            Column(name='BPmag', data=np.array([])),
            Column(name='BPmag_error', data=np.array([])),
            Column(name='RPmag', data=np.array([])),
            Column(name='RPmag_error', data=np.array([])),
            Column(name='BP-RP', data=np.array([])),
            Column(name='BP-RP_error', data=np.array([])),
            Column(name='Reddening(BP-RP)', data=np.array([])),
            Column(name='Extinction_G', data=np.array([])),
            Column(name='Distance', data=np.array([])),
            Column(name='Teff', data=np.array([])),
            Column(name='logg', data=np.array([])),
            Column(name='[Fe/H]', data=np.array([])),
            Column(name='RUWE', data=np.array([])),
            Column(name='Separation', data=np.array([]))
        ]

    return Table(column_list)

def convert_Gmag_to_JHK(Gmag,BpRp):
    """Function to convert Gaia photometry in G band, together with colour photometry in BP-RP to
    J, H, Ks filters, using the conversion from
    https://gea.esac.esa.int/archive/documentation/GDR3/Data_processing/chap_cu5pho/cu5pho_sec_photSystem/cu5pho_ssec_photRelations.html#Ch5.T8
    """
    J = Gmag - (-0.01798 + 1.389 * BpRp - 0.09338 * BpRp ** 2)
    H = Gmag - (-0.1048 + 2.011 * BpRp - 0.1758 * BpRp ** 2)
    K = Gmag - (-0.0981 + 2.089 * BpRp - 0.1579 * BpRp ** 2)

    # If the input magnitudes are Table arrays, ensure the output
    # tables column names are accurately renamed
    if type(Gmag) == type(Column()):
        J = Column(name='Jmag', data=J.data)
        H = Column(name='Hmag', data=H.data)
        K = Column(name='Kmag', data=K.data)
    return J, H, K

def estimate_target_peak_phot_uncertainties(Gmag, BPRP, u0, u0_error):
    """Function to estimate the photometric uncertainties for the Gaia photometry of a given star"""

    peak_phot = {'G': Gmag, 'BPRP': BPRP}

    # Simulate a distribution of event baseline magnitudes and colours
    g_sample = np.random.normal(Gmag, 0.1, 10000)

    # Simulate a distribution of event impact parameters, and calculate the corresponding
    # peak magnification
    u0_sample = abs(np.random.normal(u0, u0_error, 10000))
    magnification = peak_magnification(u0_sample)

    # Calculate the corresponding distribution of G-band peak event magnitudes,
    # and estimate the uncertainty from the width of the distribution
    g_sample -= 2.5 * np.log10(magnification)
    peak_phot['Gerror'] = g_sample.std()

    # To estimate the target's NIR photometry around the peak, convert the sample of events
    (Jsample, Hsample, Ksample) = convert_Gmag_to_JHK(g_sample, BPRP)
    peak_phot['J'] = np.median(Jsample)
    peak_phot['Jerror'] = Jsample.std()
    peak_phot['H'] = np.median(Hsample)
    peak_phot['Herror'] = Hsample.std()
    peak_phot['K'] = np.median(Ksample)
    peak_phot['Kerror'] = Ksample.std()

    return peak_phot

def interferometry_decision(G_lens, BPRP_lens, K_neighbours):

    mode = 'No'
    guide = 0

    if len(K_neighbours) > 0:
        g = np.random.normal(G_lens, 0.1, 10000)
        bprp = np.random.normal(BPRP_lens, 0.1, 10000)
        (J_lens, K_lens, H_lens) = convert_Gmag_to_JHK(g, bprp)

        percentiles = np.percentile(K_lens,[16,50,84])
        median = percentiles[1]
        std = (percentiles[2]-percentiles[0])/2
        if (median+2*std<10) & (std<1):

            mode = 'Single Field'

        else:

            if np.min(K_neighbours)<11:

                mode = 'Dual Field Wide'
                guide = np.argmin(K_neighbours)
    return mode,guide
            
def GAIA_toJHK(G,BpRp):
    
    ### https://gea.esac.esa.int/archive/documentation/GDR3/Data_processing/chap_cu5pho/cu5pho_sec_photSystem/cu5pho_ssec_photRelations.html#Ch5.T8
    
    try:
    
        J = G-(-0.01798+1.389*BpRp-0.09338*BpRp**2)+np.random.normal(0,0.04762,len(BpRp))
        H = G-(-0.1048+2.011*BpRp-0.1758*BpRp**2)+np.random.normal(0,0.07805,len(BpRp))
        K = G-(-0.0981+2.089*BpRp-0.1579*BpRp**2)+np.random.normal(0,0.08553,len(BpRp))
    
    except:
        
        J = G-(-0.01798+1.389*BpRp-0.09338*BpRp**2)
        H = G-(-0.1048+2.011*BpRp-0.1758*BpRp**2)
        K = G-(-0.0981+2.089*BpRp-0.1579*BpRp**2)
    
    
    mask = ~np.isnan(J) & ~np.isinf(J) &  ~np.isnan(H) & ~np.isinf(H) & ~np.isnan(K) & ~np.isinf(K)            
    
    return J[mask],H[mask],K[mask]
    

def peak_magnification(uuu):

    A=(uuu**2+2)/(uuu*(uuu**2+4)**0.5)
    
    return A
        
def interfero_plot():
    ### Example with Gaia19bld

    #RA = 189.38565
    #DEC = -66.11136
    #U0 = 0.0193
    #EU0 = 0.0001


    ### Example with Gaia22ahy

    #RA = 225.25274
    #DEC = -54.40000
    #U0 = 0.55601
    #EU0 = 0.2451797

    ### Example with Kojima-1

    RA = 76.925
    DEC = 24.79888
    U0 = 0.08858
    EU0 = 0.0003


    # Queries Gaia DR3 catalog for the target object and near neighbours
    Vizier.ROW_LIMIT = -1

    coord = SkyCoord(ra=RA, dec=DEC, unit=(u.degree, u.degree), frame='icrs')
    result = Vizier.query_region(coord, radius=Angle(0.004, "deg"), catalog='I/355/gaiadr3')

    # Identifies stars with valid photometry in all passbands
    mask = ~result[0]['Gmag'].data.mask & ~result[0]['BP-RP'].data.mask

    # For this subset of stars, calculates the angular separation between each star and the target
    # Note: this is the wrong formula
    distance = np.sqrt((result[0][mask]['RA_ICRS'].data.data-RA)**2+(result[0][mask]['DE_ICRS'].data.data-DEC)**2)

    # Returns lists of the star subset's photometry in order of ascending distance from
    # the target
    G = result[0][mask]['Gmag'][distance.argmin()]
    BP_RP = result[0][mask]['BP-RP'][distance.argmin()]

    # Generates a set of simulated events?
    g = np.random.normal(G,0.1,10000)
    bp_rp = np.random.normal(BP_RP,0.1,10000)
    uo = np.random.normal(U0,EU0,10000)
    magnification = peak_magnification(uo)
    g -= 2.5*np.log10(magnification)

    # Converts the set of stars from Gaia photometric bands to J,H,K
    J,H,K = GAIA_toJHK(g,bp_rp)

    plt.hist(J,25,alpha=0.5,label='J')
    plt.hist(H,25,alpha=0.5,label='H')
    plt.hist(K,25,alpha=0.5,label='Ks')
    plt.legend()
    plt.xlabel('Mag')
    plt.show()


    JJ = []
    HH = []
    KK = []

    for close_stars_index in distance.argsort()[1:]:


        jjj,hhh,kkk = GAIA_toJHK(result[0][mask]['Gmag'][close_stars_index],result[0][mask]['BP-RP'][close_stars_index])

        JJ.append(jjj)
        HH.append(hhh)
        KK.append(kkk)

        if kkk<11:

            break


    mode,guide = interferometry_decision(K,np.array(KK))

    print(mode,guide)

def search_gsc_catalog(target):
    """
    Function to search the Guide Star Catalog for suitable stars for Adaptive Optics guides and Fringe Tracking
    """
    logger.info('INTERFERO: Querying GSC catalog around event ' + target.name)

    # Perform Vizier catalog search of the GSC
    print('Target: ', target)
    print('Target type', type(target))
    gsc_table = gsc.query_gsc(target)
    print('GSC Table: \n' + gsc_table)

    # If any stars are missing Ks-band magnitudes, attempt to estimate them using calibrations
    # based on other photometric bands
    gsc_table = gsc.verify_Ksmag_data(gsc_table)

    # Identify suitable stars to use for AO and FT
    gsc_table = gsc.select_AO_stars(gsc_table)
    gsc_table = gsc.select_FT_stars(gsc_table)

    # Create comparative grid of AO-FT star matrix
    AOFT_table = gsc.create_AOFT_table(gsc_table)
    AOFT_table = gsc.populate_AOFT_table(gsc_table, AOFT_table)
    logger.info('INTERFERO: Compose matrix of AO and FT stars for ' + target.name)

    return gsc_table, AOFT_table

def evaluate_target_for_interferometry(target):
    """Function to calculate the necessary parameters in order to determine whether this target
    is suitable for interferometry"""
    logger.info('INTERFERO: Evaluating event ' + target.name)

    # Extract the necessary target parameters and sanity check.  For reasons I don't understand,
    # u0_error is sometimes stored as a tag rather than an extra parameter during testing.
    if target.u0 == None or target.u0_error == None:
        logger.info('INTERFERO: Insufficient u0 info to evaluate target')
        return

    # Query the Gaia DR3 catalog for the target object and near neighbours within 14.4 arcsec
    # Search radius is set by the interferometry requirement to have bright neighbouring stars
    #         # that are accessible to the GRAVITY instrument
    neighbour_radius = Angle(20.0/3600.0, "deg")
    star_catalog = gaia.query_gaia_dr3(target, radius=neighbour_radius, row_limit=100, Gmag_max=16.0)
    neighbours = find_companion_stars(target, star_catalog)
    logger.info('INTERFERO: Identified ' + str(len(neighbours)) + ' stars in the neighbourhood of '+target.name)

    # The neighbours table is order in ascending separation from the target coordinates,
    # so the target should be the first entry.  Extract the target's Gaia photometry and estimate
    # the uncertainties
    if len(neighbours) > 0:
        G_lens = neighbours['Gmag'][0]
        BPRP_lens = neighbours['BP-RP'][0]
        peak_phot = estimate_target_peak_phot_uncertainties(G_lens, BPRP_lens, target.u0, target.u0_error)
        logger.info('INTERFERO: Calculated uncertainties Gmag=' + str(G_lens)
                    + '+/-' + str(peak_phot['Gerror']) + 'mag')

        # Calculate the NIR photometry of all stars in the region
        (J, H, K) = convert_Gmag_to_JHK(neighbours['Gmag'], neighbours['BP-RP'])
        logger.info('INTERFERO: Computed JHK photometry for neighbouring stars')

        # Determine how long the target will be bright enough to observe
        interval = predict_period_above_brightness_threshold(target, K[0], Kthreshold=14.0)

        # Evaluate whether this target is suitable for inteferometry
        (mode, guide) = interferometry_decision(G_lens, BPRP_lens, np.array(K.data)[1:])
        logger.info('INTERFERO: Evaluation for interferometry for ' + target.name + ': ' + str(mode) + ' guide=' + str(guide))

        # Store the results
        store_gaia_search_results(target, neighbours, peak_phot, BPRP_lens, mode, guide, J, H, K, interval)

    else:
        peak_phot = {'G': None, 'Gerror': None,
                     'J': None, 'Jerror': None,
                     'H': None, 'Herror': None,
                     'K': None, 'Kerror': None}
        interval = None
        extras = {
                'interferometry_mode': 'No',
                'interferometry_guide_star': 0,
        }
        target.store_parameter_set(extras)
        logger.info('INTERFERO: No interferometry possible without neighbouring stars')

    # Query the Guide Star Catalog for candidate AO and FT stars
    (gsc_table, AOFT_table) = search_gsc_catalog(target)

    # Store the results from the GSC
    store_gsc_search_results(target, gsc_table, AOFT_table)

    # Select candidate targets for GRAVITY program
    if peak_phot['K']:
        gravity_target_selection(target, peak_phot['K'], interval, gsc_table)

def store_gaia_search_results(target, neighbours, peak_phot, BPRP_lens, mode, guide, J, H, K, interval):
    extras = {
        'gaia_source_id': neighbours['Gaia_Source_ID'][0],
        'gmag': peak_phot['G'], 'Gmag_error': peak_phot['Gerror'],
        'rpmag': neighbours['RPmag'][0], 'RPmag_error': neighbours['RPmag_error'][0],
        'bpmag': neighbours['BPmag'][0], 'BPmag_error': neighbours['BPmag_error'][0],
        'bprp': BPRP_lens, 'BP-RP_error': neighbours['BP-RP_error'][0],
        'reddening_bprp': neighbours['Reddening(BP-RP)'][0],
        'extinction_g': neighbours['Extinction_G'][0],
        'distance': neighbours['Distance'][0],
        'teff': neighbours['Teff'][0],
        'logg': neighbours['logg'][0],
        'metallicity': neighbours['[Fe/H]'][0],
        'ruwe': neighbours['RUWE'][0],
        'interferometry_mode': mode,
        'interferometry_guide_star': guide,
        'mag_base_J': J[0],
        'mag_base_H': H[0],
        'mag_base_K': K[0],
        'mag_peak_J': peak_phot['J'],
        'mag_peak_J_error': peak_phot['Jerror'],
        'mag_peak_H': peak_phot['H'],
        'mag_peak_H_error': peak_phot['Herror'],
        'mag_peak_K': peak_phot['K'],
        'mag_peak_K_error': peak_phot['Kerror'],
        'interferometry_interval': interval
    }
    target.store_parameter_set(extras)

    # Repackage data into a convenient form for storage
    # Note that the column headings used here are different from the MicrolensingTarget attribute
    # names because these data are displayed in tabular form in the UI, and so reflect the
    # columns from the Gaia catalogue.
    datum = {
        'Gaia_Source_ID': [str(x) for x in neighbours['Gaia_Source_ID']],
        'Gmag': [x for x in neighbours['Gmag']],
        'Gmag_error': [x for x in neighbours['Gmag_error']],
        'BPmag': [x for x in neighbours['BPmag']],
        'BPmag_error': [x for x in neighbours['BPmag_error']],
        'RPmag': [x for x in neighbours['RPmag']],
        'RPmag_error': [x for x in neighbours['RPmag_error']],
        'BP-RP': [x for x in neighbours['BP-RP']],
        'BP-RP_error': [x for x in neighbours['BP-RP_error']],
        'Jmag': [x for x in J],
        'Hmag': [x for x in H],
        'Kmag': [x for x in K],
        'Reddening(BP-RP)': [x for x in neighbours['Reddening(BP-RP)']],
        'Extinction_G': [x for x in neighbours['Extinction_G']],
        'Distance': [x for x in neighbours['Distance']],
        'Teff': [x for x in neighbours['Teff']],
        'logg': [x for x in neighbours['logg']],
        '[Fe/H]': [x for x in neighbours['[Fe/H]']],
        'RUWE': [x for x in neighbours['RUWE']],
        'Separation': [x for x in neighbours['Separation']],
    }

    # To avoid accumulating entries, search for any existing tabular
    # data for this object and remove it from the DB:
    qs = ReducedDatum.objects.filter(target=target)
    for rd in qs:
        if rd.data_type == 'tabular' and rd.source_name == 'Interferometry_predictor':
            rd.delete()

    # Now store the tabular results
    tnow = Time.now()
    rd, created = ReducedDatum.objects.get_or_create(
        timestamp=tnow.to_datetime(timezone=TimezoneInfo()),
        value=datum,
        source_name='Interferometry_predictor',
        source_location=target.name,
        data_type='tabular',
        target=target)
    logger.info('INTERFERO: Stored neighbouring star data in MOP')

def um(mask_value):

    if type(mask_value) == np.ma.core.MaskedConstant:
        return 0.0
    else:
        return np.float64(mask_value)
def store_gsc_search_results(target, gsc_table, AOFT_table):

    # Repackage the table of neighbouring GSC stars
    # Since this is a masked Astropy Table, and JSON serialization doesn't handle masked entries,
    # we need to convert to standard numpy flex values
    idx = np.where(gsc_table['FTstar'] == 1.0)[0]

    datum = {
        'GSC2': [str(x) for x in gsc_table['GSC2'][idx]],
        'Separation': [(x*3600.0) for x in gsc_table['_r'][idx]],    # Convert to arcsec
        'Jmag': [um(x) for x in gsc_table['Jmag'][idx]],
        'Hmag': [um(x) for x in gsc_table['Hmag'][idx]],
        'Ksmag': [um(x) for x in gsc_table['Ksmag'][idx]],
        'W1mag': [um(x) for x in gsc_table['W1mag'][idx]],
        'RA': [np.float64(x) for x in gsc_table['RA_ICRS'][idx]],
        'Dec': [np.float64(x) for x in gsc_table['DE_ICRS'][idx]],
        'plx': [um(x) for x in gsc_table['plx'][idx]],
        'pmRA': [um(x) for x in gsc_table['pmRA'][idx]],
        'pmDE': [um(x) for x in gsc_table['pmDE'][idx]],
        'AOstar': [str(bool(x)) for x in gsc_table['AOstar'][idx]],       # Convert to boolean
        'FTstar': [str(bool(x)) for x in gsc_table['FTstar'][idx]],       # Convert to boolean
    }

    # To avoid accumulating entries, search for any existing tabular
    # data for this object and remove it from the DB:
    qs = ReducedDatum.objects.filter(target=target)
    for rd in qs:
        if rd.data_type == 'tabular' and rd.source_name == 'GSC_query_results':
            rd.delete()

    # Now store the tabular results
    tnow = Time.now()
    rd, created = ReducedDatum.objects.get_or_create(
        timestamp=tnow.to_datetime(timezone=TimezoneInfo()),
        value=datum,
        source_name='GSC_query_results',
        source_location=target.name,
        data_type='tabular',
        target=target)
    logger.info('INTERFERO: Stored GSC search results in MOP')

    # Repackage the AOFT_table for storage
    datum = {
        'FTstar': [str(x) for x in AOFT_table['FTstar']],
        'SC_separation': [(x*3600.0) for x in AOFT_table['SC_separation']],     # Convert to arcsec
        'Ksmag': [x for x in AOFT_table['Ksmag']],
        'SC_Vloss': [x for x in AOFT_table['SC_Vloss']],
    }
    AOidx = np.where(gsc_table['AOstar'] == 1.0)[0]
    col_suffices = ['_SCstrehl', '_FTstrehl', '_Gmag', '_SC_separation', '_Ksmag', '_FT_separation']
    for j in AOidx:
        AOname = str(gsc_table['GSC2'][j])
        for suffix in col_suffices:
            col = AOname+suffix
            if '_separation' in col:
                datum[col] = [(x*3600.0) for x in AOFT_table[col]]
            else:
                datum[col] = [x for x in AOFT_table[col]]

    # Removed from the DB any previous AOFT table data for this target
    qs = ReducedDatum.objects.filter(target=target)
    for rd in qs:
        if rd.data_type == 'tabular' and rd.source_name == 'AOFT_table':
            rd.delete()

    # Store the new data
    tnow = Time.now()
    rd, created = ReducedDatum.objects.get_or_create(
        timestamp=tnow.to_datetime(timezone=TimezoneInfo()),
        value=datum,
        source_name='AOFT_table',
        source_location=target.name,
        data_type='tabular',
        target=target)
    logger.info('INTERFERO: Stored AOFT matrix in MOP')

def predict_peak_brightness(mag_base, mag_base_error, u0, u0_error):
    """
    Function to estimate the peak brightness expected for the lensed target
    """

    # Calculate the expected peak K-band brightness
    if u0 > 0.0:
        magnification = peak_magnification(u0)
        mag_peak = mag_base - 2.5 * np.log10(magnification)
        dmag = mag_base_error / mag_base
        du = ((1.0/np.log(10.0)) * (u0_error/u0))
        mag_peak_error = np.sqrt(dmag*dmag + du*du)
    elif u0 == 0.0:
        mag_peak = np.inf
        mag_peak_error
    elif np.isnan(u0):
        mag_peak = np.nan
        mag_peak_error = np.nan

    return mag_peak, mag_peak_error

def predict_period_above_brightness_threshold(target, Kbase, Kthreshold=14.0):
    # Search MOP to see if an existing model is already stored.  The model_time parameter is hardwired into
    # mop.toolbox.fittools.  Unclear why.
    ##model_time = datetime.strptime('2018-06-29 08:15:27.243860', '%Y-%m-%d %H:%M:%S.%f')
    qs = ReducedDatum.objects.filter(source_name='MOP', data_type='lc_model',
                                     source_location=target.name)
    mag_base = target.baseline_magnitude
    interval = np.nan

    # This calculation can only be made if a valid model has been fitted
    if qs.count() > 0 and not np.isnan(mag_base) and mag_base > 0.0:
        ts = np.array(qs[0].value['lc_model_time'])
        mags = np.array(qs[0].value['lc_model_magnitude'])

        # Estimate the K-band lightcurve
        Klc = Kbase + (mags - mag_base)
        
        # Calulate how many days the lightcurve spends brighter than Kthreshold
        idx = np.where(Klc <= Kthreshold)[0]
        
        if len(idx) > 0 and len(idx) < len(mags):
            interval = ts[idx].max() - ts[idx].min()
        elif len(idx) > 0 and len(idx) == len(mags):
            interval = np.inf

    return interval

def gravity_target_selection(target, Kpeak, interval, gsc_table, Kthreshold=14.0):

    # Count the numbers of AO and FT stars
    nft = len(np.where(gsc_table['FTstar'] == 1.0)[0])
    nao = len(np.where(gsc_table['AOstar'] == 1.0)[0])

    if Kpeak <= Kthreshold \
            and (interval > 0.0 or np.isinf(interval)) \
            and nao > 0 and nft > 0:
        extras = {'interferometry_candidate': True}
        target.store_parameter_set(extras)
