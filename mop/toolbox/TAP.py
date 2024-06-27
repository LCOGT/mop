from django.core.management.base import BaseCommand
from tom_observations.models import ObservationRecord
from tom_dataproducts.models import ReducedDatum
from tom_targets.models import TargetExtra
from astropy import units as u
from astropy.coordinates import Angle
from astropy.time import Time, TimezoneInfo
import datetime
import numpy as np
from pyLIMA import event
from pyLIMA import telescopes

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

from mop.toolbox import TAP_priority
from mop.toolbox import mop_classes
import logging

logger = logging.getLogger(__name__)

ZP = 27.4 #pyLIMA convention

def TAP_anomaly():

    pass

def TAP_observing_mode(planet_priority, planet_priority_error,
                       long_priority, long_priority_error,
                       t_E, t_E_error, mag_now, mag_baseline, red_chi2,
                       t_0, time_now):

    check_planet = TAP_priority.check_planet_priority(planet_priority, planet_priority_error,
                                                      mag_baseline, mag_now,
                                                      t_0, time_now)
    logger.info('Good for planet observations: '+str(check_planet))
    check_long = TAP_priority.check_long_priority(long_priority, long_priority_error,
                                                  t_E, t_E_error,
                                                  mag_now, mag_baseline,
                                                  red_chi2,
                                                  t_0, time_now)
    logger.info('Good for long tE observations: ' + str(check_long))

    if (check_planet):
        return 'priority_stellar_event'

    elif (check_long == 'priority'):
        return 'priority_long_event'

    elif (check_long == 'regular'):
        return 'regular_long_event'

    else:
        return 'No'

def calculate_exptime_floyds(magin):
    """
    This function calculates the required exposure time
    for a given iband magnitude for the floyds spectra
    """
    exposure_time = 3600 #s

    if magin<11:
       exposure_time = 1800 #s

    return exposure_time


def calculate_exptime_omega_sdss_i(magin):
    """
    This function calculates the required exposure time
    for a given iband magnitude (e.g. OGLE I which also
    roughly matches SDSS i) based on a fit to the empiric
    RMS diagram of DANDIA light curves from 2016. The
    output is in seconds.
    """
    if magin < 14.7:
        mag = 14.7
    else:
        mag = magin
    lrms = 0.14075464 * mag * mag - 4.00137342 * mag + 24.17513298
    snr = 1.0 / np.exp(lrms)


    # target 4% -> snr 25
    exptime = np.round((25. / snr)**2 * 300.,1)

    #Scaling for bright events
    if magin<14.7:

        exptime *= 10**((magin-mag)/2.5)

    #no need to more 5 min exposure time, since we have different apertures, but more than 5 s at least

    exptime = float(np.max((5,np.min((exptime,300)))))
    return  exptime



def event_in_the_Bulge(ra,dec):

    # Ensure the RA and Dec passed are floats
    ra = float(ra)
    dec = float(dec)

    Bulge_limits = [[255,275],[-36,-22]]
    if (ra>Bulge_limits[0][0]) & (ra<Bulge_limits[0][1]) & (dec>Bulge_limits[1][0]) & (dec<Bulge_limits[1][1]):
        in_the_Bulge = True
    else:

        in_the_Bulge = False

    return in_the_Bulge

def set_target_sky_location(target):
    """Function to determine whether or not a given target lies within the High Cadence Zone of the Galactic Bulge"""

    KMTNet_fields = load_KMTNet_fields()

    event_status = event_in_HCZ(target.ra, target.dec, KMTNet_fields)

    if event_status:
        target.sky_location = 'In HCZ'
    else:
        target.sky_location = 'Outside HCZ'
    target.save()

def TAP_regular_mode(in_the_Bulge,survey_cadence,sdssi_baseline,tE_fit):

    cadence =   20/tE_fit  #visits per day
    cadence = np.max(0.5,np.min(4,cadence)) # 0.5<cadence<4

    #Inside the Bulge?
    if not in_the_Bulge:
        return cadence

    if survey_cadence<1:

       if sdssi_baseline<16.5:

          return cadence

    return None


def TAP_priority_mode():

    cadence = 24 #pts/day
    duration = 3
    return duration,cadence



def TAP_telescope_class(sdss_i_mag):

    telescope_class = '2m'

    #change telescope class limit to 18.5 to save 2 m time
    if sdss_i_mag<18.0:

        telescope_class = '1m'

    # RAS: Switched off for 2023+ KP since no time allocated
    # on 0.4m network
    use_04_network = False
    if use_04_network:
        if sdss_i_mag<14:
            telescope_class = '0.4m'

    return telescope_class

#def TAP_mag_now(target):

#   fs = 10**((ZP-target.extra_fields['Source_magnitude'])/2.5)
#
#   try:
#       fb = 10**((ZP-target.extra_fields['Blend_magnitude'])/2.5)

#   except:
#      fs = 10**((ZP-target.extra_fields['Baseline_magnitude'])/2.5)
#      fb = 0
#   fit_parameters = [target.extra_fields['t0'],target.extra_fields['u0'],target.extra_fields['tE'],
#                     target.extra_fields['piEN'],target.extra_fields['piEE'],
#                     fs,
#                     fb]
#
#   current_event = event.Event()
#   current_event.name = 'MOP_to_fit'

#   current_event.ra = target.ra
#   current_event.dec = target.dec

#   time_now = Time(datetime.datetime.now()).jd
#   fake_lightcurve = np.c_[time_now,14,0.01]
#   telescope = telescopes.Telescope(name='Fake', camera_filter='I',
#                                            light_curve_magnitude= fake_lightcurve,
#                                            clean_the_lightcurve='No')
#   current_event.telescopes.append(telescope)
#   t0_par = fit_parameters[0]

#   Model_parallax = microlmodels.create_model('PSPL', current_event, parallax=['Full', t0_par],blend_flux_ratio=False)
#   Model_parallax.define_model_parameters()
#   pyLIMA_parameters = Model_parallax.compute_pyLIMA_parameters(fit_parameters)
#   ml_model, f_source, f_blending = Model_parallax.compute_the_microlensing_model(telescope, pyLIMA_parameters)
#
#   mag_now = ZP-2.5*np.log10(ml_model)
#   return mag_now

def TAP_mag_now(mulens):
    lightcurve = ReducedDatum.objects.filter(target=mulens, data_type='lc_model')
    time_now = Time(datetime.datetime.now()).jd

    if mulens.existing_model:
        closest_mag = np.argmin(np.abs(lightcurve[0].value['lc_model_time']-time_now))
        mag_now =  lightcurve[0].value['lc_model_magnitude'][closest_mag]

        mulens.mag_now = round(mag_now,3)
        mulens.save()
        
    else:
        mag_now = None
        mulens.mag_now = None

    return mag_now
   
def load_KMTNet_fields():
    """
    Returns a numpy array with the vertices
    describing the KMTNet zone polygon.
    """
    fields = np.array([[264.00, -37.40],
                        [270.50, -37.40],
                        [270.50, -33.75],
                        [272.50, -33.75],
                        [272.50, -32.00],
                        [275.50, -32.00],
                        [275.50, -25.30],
                        [275.60, -25.30],
                        [275.60, -21.90],
                        [272.00, -21.90],
                        [272.00, -23.00],
                        [270.40, -23.00],
                        [270.40, -20.50],
                        [264.50, -20.50],
                        [264.50, -22.70],
                        [262.00, -22.70],
                        [262.00, -26.25],
                        [260.50, -26.25],
                        [260.50, -31.40],
                        [262.00, -31.40],
                        [262.00, -36.00],
                        [264.00, -36.00]])
    return fields
    
def event_in_HCZ(ra, dec, KMTNet_fields):

    """
    This function checks if the event is within the KMTNet fields.
    If it is, the event has to be rejected and not followed by OMEGA-II.

    :param ra: Right Ascension of the event.
    :param dec: Declination of the event.
    :param KMTNet_fields: A numpy array that contains a series of
                          points describing roughly
    :return: Boolean value if the event is not ok for OMEGA II.
    """

    exclusion_zone = Polygon(zip(KMTNet_fields[:,0], KMTNet_fields[:,1]))

    event_in_HCZ = False

    point = Point(ra, dec)
    if (exclusion_zone.contains(point)):
        event_in_HCZ = True

    return event_in_HCZ

def TAP_time_last_datapoint(target, source_name=None):
    """
    Returns time of the latest datapoint in the lightcurve.  If no photometry for this target is available,
    this function returns a default timestamp for 1995-01-01.  This is done to indicate that any subsequent
    photometry should be considered to be more recent and therefore ingested.
    """
    if not source_name:
        datasets = ReducedDatum.objects.filter(target=target).order_by('timestamp')
    else:
        datasets = ReducedDatum.objects.filter(target=target, source_name__icontains=source_name).order_by('timestamp')

    # If there is existing photometry for this object, identify the most recent datapoint
    if datasets.count() > 0:
        time = [Time(i.timestamp, format='datetime').jd for i in datasets if i.data_type == 'photometry']

        # It's apparently possible for targets to get ingested with a single, zero-length dataset array,
        # in which case this exception handling is needed
        if len(time) > 0:
            last_jd = time[-1]
            last_ts = Time(last_jd, format='jd').to_datetime(timezone=TimezoneInfo())
        else:
            last_jd = None
            last_ts = None

    # If there is no photometry for this target, return a default timestamp a long time ago
    # so that any photometry that subsequently becomes available will be more recent and MOP will
    # therefore know it should be ingested
    else:
        default_t = Time('1995-01-01T00:00:00.0', format='isot')
        last_jd = default_t.jd
        last_ts = default_t.tt.datetime

    return last_jd, last_ts

def categorize_event_timescale(mulens, threshold=75.0):
    """
    This function is designed to classify an event based on the best
    currently available estimate of its Einstein crossing time.

    Events with a tE >= threshold [days] are considered to be
    long-timescale events and black hole candidates.
    """

    category = 'Microlensing stellar/planet'

    if float(mulens.tE) >= threshold:
        mulens.category = 'Microlensing long-tE'
        mulens.save()

    return category

def sanity_check_model_parameters(t0_pspl, t0_pspl_error, u0_pspl, tE_pspl, tE_pspl_error, red_chi2, covariance):
    """
    Function to review the model parameters to verify that valid calulations can be made with them.
    """
    sane = True
    reason = ''
    params = [t0_pspl, t0_pspl_error, u0_pspl, tE_pspl, tE_pspl_error, red_chi2]

    # Check t0, tE and u0 values are non-zero, not NaNs and floating point variables
    for value in params:
        if value == 0.0 or np.isnan(value) or type(value) != type(1.0) or value == None:
            sane = False
            reason += ' Bad parameter value: ' + str(value)

    # Check the covariance array is an array of non-zero length:
    if type(covariance) != type(np.zeros(1)) or len(covariance) == 0:
        sane = False
        reason += ' ; Bad covariance matrix: '+repr(covariance)

    logger.info('TAP model parameters sanity check returned ' + repr(sane) + ' ' + reason)

    return sane

def TAP_check_baseline(mulens):
    """
    Checks if a baseline exists for a target.
    """

    if mulens.first_observation:
        if (mulens.first_observation < float(mulens.t0) - float(mulens.tE)):
            logger.info('Baseline data prior to an event found.')
            return True

    return False