from django.conf import settings
from tom_observations.facility import GenericObservationFacility, GenericObservationForm, get_service_class
from tom_observations.facilities import lco
from tom_observations.cadence import CadenceForm
from tom_observations.models import ObservationRecord
from mop.toolbox.obs_details import all_night_moon_sep, calculate_visibility
from mop.toolbox import lco_visibility, healpixel_functions
from astropy.time import Time, TimeDecimalYear
from astropy.coordinates import SkyCoord
from astropy import units as u
from mop.toolbox import TAP, lco_observations
from mop.toolbox.mop_classes import MicrolensingEvent
import datetime
from django.conf import settings
import copy
import numpy as np
import requests
import os
import json
from scipy import interpolate
import logging

logger = logging.getLogger(__name__)

def fetch_pending_lco_requestgroups():
    """Function to retrieve the request groups for a given user from the LCO Observe Portal"""

    # Contact the LCO Observe Portal.  This query now returns a list of all request groups accessible to the user
    token = os.getenv('LCO_API_KEY')
    username = os.getenv('LCO_USERNAME')
    headers = {'Authorization': 'Token ' + token}
    url = os.path.join(
        "https://observe.lco.global/api/requestgroups/?state=PENDING&user=" + username)
    response = requests.get(url, headers=headers, timeout=20).json()

    return response

def fetch_all_lco_requestgroups():
    """Function to retrieve the request groups for a given user from the LCO Observe Portal"""

    # Contact the LCO Observe Portal.  This query now returns a list of all request groups accessible to the user
    token = os.getenv('LCO_API_KEY')
    username = os.getenv('LCO_USERNAME')
    headers = {'Authorization': 'Token ' + token}
    url = os.path.join(
        "https://observe.lco.global/api/requestgroups/?user=" + username)
    response = requests.get(url, headers=headers, timeout=20).json()

    return response

def parse_lco_requestgroups(response, short_form=True, pending_only=True):
    # Parse the list of results returned to extract observations from the configured observing proposal,
    # and return only those with state pending.
    proposal_code = os.getenv('LCO_PROPOSAL_ID')
    pending_obs = {}

    if 'results' in response.keys():
        for result in response['results']:
            if pending_only:
                select_obs = (result['state'] == 'PENDING') and (result['proposal'] == proposal_code)
            else:
                select_obs = (result['proposal'] == proposal_code)

            if select_obs:
                for request in result['requests']:
                    for config in request['configurations']:
                        if config['target']['name'] not in pending_obs:
                            if short_form:
                                pending_obs[config['target']['name']] = [config['instrument_type']]
                            else:
                                obs_info = extract_obs_request_info(result)
                                pending_obs[config['target']['name']] = [obs_info]
                        else:
                            if short_form:
                                # Note that this will return only one hit per target and instrument combination,
                                # even if multiple observation groups have been submitted
                                if config['instrument_type'] not in pending_obs[config['target']['name']]:
                                    pending_obs[config['target']['name']].append(config['instrument_type'])

                            else:
                                # This will return all submitted groups for a given target
                                obs_info = extract_obs_request_info(result)
                                pending_obs[config['target']['name']].append(obs_info)

    return pending_obs

def extract_obs_request_info(result):
    """Function to extract a set of standard parameters from the JSON dictionary returned by the LCO Observe Portal
    for a given configuration of an observing request"""

    obs_info = {'id': None, 'instrument_type': None, 'state': None, 'name': None,
                'filters': [], 'exposure_times': [], 'exposure_counts': []}

    obs_info['id'] = result['id']
    obs_info['name'] = result['name']
    obs_info['instrument_type'] = result['requests'][0]['configurations'][0]['instrument_type']
    obs_info['state'] = result['state']

    type_spectro = ['LAMP_FLAT', 'ARC', 'SPECTRUM']

    for request in result['requests']:
        for config in request['configurations']:
            if any(x in config['type'] for x in type_spectro):
                # Put here missing code for getting spectroscopic config
                pass
            elif 'EXPOSE' in config['type']:
                if 'instrument_configs' in config.keys():
                    for inst_conf in config['instrument_configs']:
                        obs_info['filters'].append(inst_conf['optical_elements']['filter'])
                        obs_info['exposure_times'].append(inst_conf['exposure_time'])
                        obs_info['exposure_counts'].append(inst_conf['exposure_count'])

    return obs_info

def filter_duplicated_observations(configs, pending_obs):
    """Function designed to filter a list of dictionaries containing the parameters of
    observing requests for a given target.
    This function checks to see if an observation with similar parameters has already
    been submitted and is still active.  If this is the case, the superfluous configuration
    is removed from the list; otherwise the list is returned unchanged.
    """
    new_configs = []
    for conf in configs:
        need_to_submit = True
        if conf['target'].name in pending_obs.keys():
            if conf['instrument_type'] in pending_obs[conf['target'].name]:
                need_to_submit = False
        if need_to_submit:
            new_configs.append(conf)

    return new_configs

def build_arc_calibration_template(science_obs):

    config_arc = copy.deepcopy(science_obs['requests'][0]['configurations'][0])
    config_arc['type'] = "ARC"
    config_arc['instrument_configs'][0]['exposure_time'] = 50.0
    config_arc['acquisition_config']['mode'] = "OFF"
    config_arc['acquisition_config']['extra_params'] = {}
    config_arc['guiding_config']['optional'] = True

    return config_arc

def build_lamp_calibration_template(science_obs):

    config_lamp = copy.deepcopy(science_obs['requests'][0]['configurations'][0])
    config_lamp['type'] = "LAMP_FLAT"
    config_lamp['instrument_configs'][0]['exposure_time'] = 60.0
    config_lamp['acquisition_config']['mode'] = "OFF"
    config_lamp['acquisition_config']['extra_params'] = {}
    config_lamp['guiding_config']['optional'] = True

    return config_lamp



def build_and_submit_spectro(target, obs_type):

       #Defaults
       observing_type  = 'SPECTRA'
       instrument_type = '2M0-FLOYDS-SCICAM'
       proposal =  os.getenv('LCO_PROPOSAL_ID')
       facility = 'LCO'
       observation_mode = 'NORMAL'
       max_airmass = 2

       if obs_type == 'priority':

          ipp = 1.1
          obs_name = target.name+'_'+'PRI_spectro'
          obs_duration = 3 #days


       else:

          ipp = 0.9
          obs_name = target.name+'_'+'REG_spectro'
          obs_duration = 7 #days

       need_to_submit = check_pending_observations(obs_name,'PENDING')

       if need_to_submit is False:

          return

       # Do no trigger if a spectrum is already taken
       need_to_submit = check_pending_observations(obs_name,'COMPLETED')

       if need_to_submit is False:

          return

       start = datetime.datetime.utcnow().isoformat()
       end  = (datetime.datetime.utcnow()+datetime.timedelta(days=obs_duration)).isoformat()

       mag_now = TAP.TAP_mag_now(target)
       mag_exposure = mag_now

       if mag_now>15:
          # too faint for FLOYDS
          return
       exposure_time_ip = TAP.calculate_exptime_floyds(mag_exposure)




       obs_dic = {}


       obs_dic['name'] = obs_name
       obs_dic['target_id'] = target.id
       obs_dic['start'] = start
       obs_dic['end'] = end
       obs_dic['observation_mode'] = observation_mode
       # Bizzare
       obs_dic['filter'] =  "slit_1.6as"

       obs_dic['ipp_value'] = ipp
       obs_dic['exposure_count'] = 1
       obs_dic['exposure_time'] = exposure_time_ip
       obs_dic['max_airmass'] = max_airmass
       obs_dic['proposal'] = proposal

       obs_dic['instrument_type'] = instrument_type
       obs_dic['facility'] = facility
       obs_dic['observation_type'] = observing_type
       obs_dic['rotator_mode'] ='SKY'
       obs_dic['rotator_angle'] =0
       #obs_dic['extra_params'] = "None"

       request_obs =  lco.LCOSpectroscopyObservationForm(obs_dic)
       request_obs.is_valid()
       the_obs = request_obs.observation_payload()


       #Hacking
       the_obs['requests'][0]['configurations'][0]['instrument_configs'][0]['extra_params'] = {}
       data =  '''{"mode": "BRIGHTEST", "exposure_time": null,
                    "extra_params": {
                    "acquire_radius": "5"}}'''
       the_obs['requests'][0]['configurations'][0]['acquisition_config']=json.loads(data)

       data =  '''{"optional": false,
                "mode": "ON",
                "optical_elements": {},
                "exposure_time": null,
                "extra_params": {}}'''
       the_obs['requests'][0]['configurations'][0]['guiding_config']=json.loads(data)

       config_lamp = build_lamp_calibration_template(the_obs)
       config_arc = build_arc_calibration_template(the_obs)

       the_obs['requests'][0]['configurations'].insert(0,config_arc)
       the_obs['requests'][0]['configurations'].insert(0,config_lamp)
       the_obs['requests'][0]['configurations'].append(config_arc)
       the_obs['requests'][0]['configurations'].append(config_lamp)

       telescope = lco.LCOFacility()
       observation_ids = telescope.submit_observation(the_obs)


       for observation_id in observation_ids:

           record = ObservationRecord.objects.create(
                                      target=target,
                                      facility='LCO',
                                      parameters=request_obs.serialize_parameters(),
                                      observation_id=observation_id
                                      )

def build_and_submit_phot(target, obs_type):

       #Defaults
       observing_type  = 'IMAGING'
       instrument_type = '1M0-SCICAM-SINISTRO'
       proposal =  os.getenv('LCO_PROPOSAL_ID')
       facility = 'LCO'
       observation_mode = 'NORMAL'
       max_airmass = 2

       if obs_type == 'priority':
          # planet priority mode
          ipp = 1.0
          obs_name = target.name+'_'+'PRI_phot'
          obs_duration = 3 #days
          cadence = 1 #delta_hours/points

       elif obs_type == 'long_priority':
           # long event priority mode after a gap
           ipp = 1.0
           obs_name = target.name + '_' + 'PRI_phot'
           obs_duration = 3  # days
           cadence = 0.5  # delta_hours/points

       elif obs_type == 'long_regular':
           # long event regular mode
           ipp = 0.95
           obs_name = target.name + '_' + 'REG_phot'
           obs_duration = 7  # days

           cadence = 0.5  # points/days

       else:
          # planet regular mode
          ipp = 0.95
          obs_name = target.name+'_'+'REG_phot'
          obs_duration = 7 #days

          cadence = 20/target.extra_fields['tE']  #points/days

          if cadence<0.5:

             cadence = 0.5

          if cadence>4:

             cadence = 4

          cadence = 24/cadence #delta_hours/points

          ### Fixing the time consumption
          cadence *= 2/3
          ipp *= 2/3

       jitter = cadence
       need_to_submit = check_pending_observations(obs_name,'PENDING')

       if need_to_submit is False:

          return





       mag_now = TAP.TAP_mag_now(target)
       mag_exposure = mag_now

       exposure_time_ip = TAP.calculate_exptime_omega_sdss_i(mag_exposure)


       telescope_class = TAP.TAP_telescope_class(mag_now)


       if telescope_class == '2m':

          start = Time(datetime.datetime.utcnow())
          end  = Time(datetime.datetime.utcnow()+datetime.timedelta(days=obs_duration))

          visible_at_muscat = calculate_visibility(target.ra, target.dec, start, end, 'OGG', max_airmass=max_airmass)
          moon_sep_at_muscat = all_night_moon_sep(target.ra, target.dec, start, end, 'OGG', sample_size=75)

          if visible_at_muscat and min(moon_sep_at_muscat[0]) >= 15:

              build_and_submit_muscat(target, obs_type)
              return

          else:

              instrument_type = '2M0-SCICAM-SPECTRAL'
              exposure_time_ip /= 2 # area ratio (kind of...)

       if telescope_class == '0.4m':
          #currently disabled this since we do not have 0.4m time
          pass
          #instrument_type = '0M4-SCICAM-SBIG'
          #exposure_time_ip *= 4 # area ratio

       exposure_time_gp = np.min((exposure_time_ip*3.,600)) #no more than 10 min. Factor 3 returns same SNR for ~(g-i) = 1.2



       # ip alone
       obs_dic = {}

       start = datetime.datetime.utcnow().isoformat()
       end  = (datetime.datetime.utcnow()+datetime.timedelta(days=obs_duration)).isoformat()
       obs_dic['name'] = obs_name
       obs_dic['target_id'] = target.id
       obs_dic['start'] = start
       obs_dic['end'] = end
       obs_dic['observation_mode'] = observation_mode

       obs_dic['ipp_value'] = ipp
       obs_dic['exposure_count'] = 1
       obs_dic['exposure_time'] = exposure_time_ip
       obs_dic['period'] = cadence
       obs_dic['jitter'] = jitter
       obs_dic['max_airmass'] = max_airmass
       obs_dic['proposal'] = proposal
       obs_dic['filter'] = "ip"
       obs_dic['instrument_type'] = instrument_type
       obs_dic['facility'] = facility
       obs_dic['observation_type'] = observing_type

       request_obs =  lco.LCOBaseObservationForm(obs_dic)
       request_obs.is_valid()
       the_obs = request_obs.observation_payload()

       telescope = lco.LCOFacility()
       observation_ids = telescope.submit_observation(the_obs)

       for observation_id in observation_ids:

           record = ObservationRecord.objects.create(
                                      target=target,
                                      facility='LCO',
                                      parameters=request_obs.serialize_parameters(),
                                      observation_id=observation_id
                                      )
       # gp,ip

       delta_time = cadence/2

       start = (datetime.datetime.utcnow()+datetime.timedelta(hours=delta_time)).isoformat()
       end  = (datetime.datetime.utcnow()+datetime.timedelta(days=obs_duration)+datetime.timedelta(hours=delta_time)+datetime.timedelta(hours= 4*(exposure_time_gp+300)/3600.)).isoformat()


       obs_dic = {}
       obs_dic['name'] = obs_name
       obs_dic['target_id'] = target.id
       obs_dic['start'] = start
       obs_dic['end'] = end
       obs_dic['observation_mode'] = observation_mode

       obs_dic['ipp_value'] = ipp
       obs_dic['exposure_count'] = 1
       obs_dic['exposure_time'] = exposure_time_ip+ exposure_time_gp + 300 #Hack
       obs_dic['period'] = cadence + exposure_time_gp/3600.*2 # Hack
       obs_dic['jitter'] = jitter + exposure_time_gp/3600.*2  #Hack
       obs_dic['max_airmass'] = max_airmass
       obs_dic['proposal'] = proposal
       obs_dic['filter'] = "ip"
       obs_dic['instrument_type'] = instrument_type
       obs_dic['facility'] = facility
       obs_dic['observation_type'] = observing_type

       request_obs =  lco.LCOBaseObservationForm(obs_dic)
       request_obs.is_valid()
       the_obs = request_obs.observation_payload()

       list_of_filters = ["ip","gp"]

       #if in the Bulge, switch gp to rp

       event_in_the_Bulge = TAP.event_in_the_Bulge(target.ra, target.dec)

       if (event_in_the_Bulge):

            list_of_filters[-1] = "rp"
            exposure_time_gp =  exposure_time_gp/2 #Factor 3/2 returns same SNR for ~(g-i) = 0.4


       #Hacking the LCO TOM form to add several filters
       instument_config =   the_obs['requests'][0]['configurations'][0]['instrument_configs'][0]
       exposure_times = [exposure_time_ip,exposure_time_gp]

       for ind_req,req in enumerate(the_obs['requests']):
           for ind_fil,fil in enumerate(list_of_filters):

               if ind_fil>0:
                   new_instrument_config =  copy.deepcopy(instument_config)
                   new_instrument_config['optical_elements']['filter'] = fil
                   new_instrument_config['exposure_time'] = exposure_time_gp

                   the_obs['requests'][ind_req]['configurations'][0]['instrument_configs'].append(new_instrument_config)
               else:
                   the_obs['requests'][ind_req]['configurations'][0]['instrument_configs'][0]['exposure_time'] = exposure_time_ip

       telescope = lco.LCOFacility()
       observation_ids = telescope.submit_observation(the_obs)

       for observation_id in observation_ids:

           record = ObservationRecord.objects.create(
                                      target=target,
                                      facility='LCO',
                                      parameters=request_obs.serialize_parameters(),
                                      observation_id=observation_id
                                      )

def build_lco_imaging_request(configurations):
    """
    Function to build a dictionary of the parameters of an observation request in the
    standard TOM format for the LCO facility
    Parameters:
        configs is a list of dictionaries, each containing the following parameters:
            observation_mode        str     Typically 'NORMAL'
            instrument_type         str     E.g. '1M0-SCICAM-SINISTRO',
            proposal                str     Proposal code
            facility                str     Always 'LCO'
            max_airmass             float   Typically 2.0
            min_lunar_distance      float   Typically 15.0 deg
            target                  Target  Target object from the TOM database
            filters                 list    String codes describing the filters requested
            ipp_value               float   Inter-proposal priority value of the observation request
            name                    str     String identifier for the observation
            period                  float   Interval after which to repeat the observation request, in hours
            jitter                  float   Allowed flexibility on the interval of repeat, in hours
            exposure_times          list    (Floats) Exposure times in seconds for each filter configuration requested
            exposure_counts         list    (Ints) Number of exposures for each filter
            tstart                  Datetime Observation window starting date
            tend                    Datetime Observation window end date
    """

    obs_requests = []
    for config in configurations:
        # Add to the configuration dictionary the TOM-configured parameters,
        # such as the Target information, user and proposal details
        obs_params = {
                        "group_id": config['group_id'],
                        "submitter": os.getenv("LCO_USERNAME"),
                        "proposal_id": os.getenv('LCO_PROPOSAL_ID'),
                        "observation_type": "NORMAL",
                        "telescope_class": config['telescope_class'],
                        "instrument_type": config['instrument_type'],
                        "target_name": config['target'].name,
                        "target_type": "ICRS",
                        "ra": config['target'].ra,
                        "dec": config['target'].dec,
                        "max_airmass": config['max_airmass'],
                        "min_lunar_distance": config['min_lunar_distance'],
                        "max_lunar_phase": config['max_lunar_phase'],
                        "exposure_counts": config['exposure_counts'],
                        "exposure_times": config['exposure_times'],
                        "filters": config['filters'],
                        "ipp": config['ipp'],
                        "tstart": config['tstart'],
                        "tend": config['tend']
                    }

        obs = lco_observations.LasCumbresObservation(obs_params)
        obs.build_obs_request()

        obs_requests.append(obs)

    return obs_requests

def submit_lco_obs_request(obs_requests, target):
    """Function to submit observation requests to LCO using MOP's own LCO observation class,
    and to record the submission to the MOP DB"""

    # Submit the observations
    credentials = {'lco_token': os.getenv('LCO_API_KEY')}

    for obs in obs_requests:
        response = obs.submit(credentials)
        logger.info('OBS CONTROL: Submitted observation request with response: ' + repr(response))
        # Record each observation
        if 'id' in response.keys() and 'requests' in response.keys():
            logger.info('OBS CONTROL: Saving observation record with status ' + repr(response['requests'][0]['state']))
            if response['requests'][0]['state'] == 'PENDING':
                record = ObservationRecord.objects.create(
                    target=target,
                    facility='LCO',
                    parameters=obs.request,
                    observation_id=response['requests'][0]['id'],
                    scheduled_start=obs.tstart,
                    scheduled_end=obs.tend
                )
                logger.info('OBS CONTROL: stored record in MOP')
        else:
            logger.warning('OBS CONTROL: Received unexpected response to obs submission ' + repr(response))

def submit_lco_obs_requests_old(obs_request):
    """
    Function to build a TOM-standard observation request form for the LCO facility class,
    based on the parameters defined in the input dictionary, submit the requests to LCO,
    and record the corresponding observations in the TOM.
    """

    telescope = lco.LCOFacility()
    for obs in obs_requests:
        payload = obs.observation_payload()
        observation_ids = telescope.submit_observation(payload)

        for observation_id in observation_ids:
            record = ObservationRecord.objects.create(
                target=target,
                facility='LCO',
                parameters=payload.serialize_parameters(),
                observation_id=observation_id
            )

def build_and_submit_muscat(target, obs_type):

       #Defaults
       observing_type  = 'IMAGING'
       instrument_type = '2M0-SCICAM-MUSCAT'
       proposal =  os.getenv('LCO_PROPOSAL_ID')
       facility = 'LCO'
       observation_mode = 'NORMAL'
       max_airmass = 2


       if obs_type == 'priority':

          ipp = 1.0
          obs_name = target.name+'_'+'PRI_phot'
          obs_duration = 3 #days
          cadence = 1 #delta_hours/points


       else:

          ipp = 0.95
          obs_name = target.name+'_'+'REG_phot'
          obs_duration = 7 #days

          cadence = 20/target.extra_fields['tE']  #points/days

          if cadence<0.5:

             cadence = 0.5

          if cadence>4:

             cadence = 4

          cadence = 24/cadence #delta_hours/points

       jitter = cadence


       need_to_submit = check_pending_observations(obs_name,'PENDING')

       if need_to_submit is False:

          return


       mag_now = TAP.TAP_mag_now(target)
       mag_exposure = mag_now

       exposure_time_ip = TAP.calculate_exptime_omega_sdss_i(mag_exposure)
       exposure_time_i = exposure_time_ip/2 # 2M telescope
       exposure_time_g = exposure_time_i * 3
       exposure_time_r = exposure_time_i * 3/2
       exposure_time_z = exposure_time_i
       exposure_time = max(exposure_time_g, exposure_time_r, exposure_time_i, exposure_time_z)

       diffuser_g_position = 'out'
       diffuser_r_position = 'out'
       diffuser_i_position = 'out'
       diffuser_z_position = 'out'

       start = datetime.datetime.utcnow().isoformat()
       end  = (datetime.datetime.utcnow()+datetime.timedelta(days=obs_duration)).isoformat()

       obs_dic = {} # ASYNCHRONOUS MODE

       obs_dic['name'] = obs_name
       obs_dic['target_id'] = target.id
       obs_dic['start'] = start
       obs_dic['end'] = end
       obs_dic['observation_mode'] = observation_mode

       obs_dic['ipp_value'] = ipp
       obs_dic['exposure_count'] = 1
       obs_dic['exposure_time_g'] = exposure_time_g
       obs_dic['exposure_time_r'] = exposure_time_r
       obs_dic['exposure_time_i'] = exposure_time_i
       obs_dic['exposure_time_z'] = exposure_time_z

       obs_dic ['diffuser_g_position'] = diffuser_g_position
       obs_dic ['diffuser_r_position'] = diffuser_r_position
       obs_dic ['diffuser_i_position'] = diffuser_i_position
       obs_dic ['diffuser_z_position'] = diffuser_z_position

       obs_dic['guider_mode'] = 'ON'
       obs_dic['exposure_mode'] = 'ASYNCHRONOUS'

       obs_dic['period'] = cadence
       obs_dic['jitter'] = jitter
       obs_dic['max_airmass'] = max_airmass

       obs_dic['proposal'] = proposal
       obs_dic['instrument_type'] = instrument_type
       obs_dic['facility'] = facility



       request_obs =  lco.LCOMuscatImagingObservationForm(obs_dic)
       request_obs.is_valid()
       the_obs = request_obs.observation_payload()

       telescope = lco.LCOFacility()
       observation_ids = telescope.submit_observation(the_obs)

       for observation_id in observation_ids:

           record = ObservationRecord.objects.create(
                                      target=target,
                                      facility='LCO',
                                      parameters=request_obs.serialize_parameters(),
                                      observation_id=observation_id
                                      )


def build_and_submit_regular_phot(target):


    build_and_submit_phot(target, 'regular')

def build_and_submit_priority_phot(target):

    build_and_submit_phot(target, 'priority')

def build_and_submit_regular_spectro(target):

    build_and_submit_spectro(target, 'regular')

def build_and_submit_long_priority_phot(target):


    build_and_submit_phot(target, 'long_priority')

def build_and_submit_long_regular_phot(target):


    build_and_submit_phot(target, 'long_regular')

def check_visibility(target, timenow, threshold_hrs=2.0*3.0, verbose=False):
    """Function to calculate the total number of hours for which
    a given target is visible from the whole LCO 1m network
    on the given date in decimalyears = Time.now().decimalyear

    The threshold for visibility is set by assuming that a target will
    be visible typically from three sites within 1 day, so the minimum
    observable period is 2hr per site.  Although this is on the generous
    side, the pixelized nature of the pre-calculated data is somewhat
    approximate, so in practise this gives reasonable results.
    """
    if verbose:
        print('Checking visibility')
        print(target.ra, target.dec, timenow)

    # Fetch the pre-calculated visibility data for the LCO 1m network
    # Subtract the integer year from the timenow date, as the date array
    # is generic for all years. 
    (dates, vis_data) = lco_visibility.get_visibility_data()
    timenow = timenow - int(timenow)

    # The visibility data is computed per HEALpixel, so work out which
    # HEALpixel this target lies on, and extract the vis
    s = SkyCoord(target.ra, target.dec, frame='icrs', unit=(u.deg, u.deg))
    hpindex = healpixel_functions.skycoord_to_HPindex(s, 32, radius=2.0)

    ipix = hpindex[0]
    if verbose: print('Target in HEALpixel '+str(ipix))

    # Interpolate the visibility data for this HEALpixel as a function of time,
    # in order to estimate the total number of hours for which this target
    # can currently be observed within a 24hr period
    pixel_vis_func = interpolate.interp1d(dates, vis_data[ipix, :])
    hrs_visible = pixel_vis_func(timenow)
    if verbose: print('Total hours visible: '+str(hrs_visible))

    # Decide whether or not this target is currently visible:
    visible = True
    if hrs_visible < threshold_hrs:
        visible = False
    if verbose: print('Target visible? '+repr(visible))

    return visible

# def new_build_and_submit_phot(target, obs_type):
#     # Defaults
#     observing_type = 'IMAGING'
#     instrument_type = '1M0-SCICAM-SINISTRO'
#     proposal = os.getenv('LCO_PROPOSAL_ID')
#     facility = 'LCO'
#     observation_mode = 'NORMAL'
#     max_airmass = 2
#
#     if obs_type == 'priority':
#
#         ipp = 1.0
#         obs_name = target.name + '_' + 'PRI_phot'
#         obs_duration = 3  # days
#         cadence = 1  # delta_hours/points
#
#     elif obs_type == 'long_priority':
#
#         ipp = 1.0
#         obs_name = target.name + '_' + 'PRI_phot'
#         obs_duration = 3 # days
#         cadence = 0.5
#
#     elif obs_type == 'long_regular':
#
#         ipp = 0.95
#         obs_name = target.name + '_' + 'REG_phot'
#         obs_duration = 7  # days
#
#         cadence = 0.5
#
#     else:
#         # planet regular mode
#         ipp = 0.95
#         obs_name = target.name + '_' + 'REG_phot'
#         obs_duration = 7  # days
#
#         cadence = 20 / target.extra_fields['tE']  # points/days
#
#         if cadence < 0.5:
#             cadence = 0.5
#
#         if cadence > 4:
#             cadence = 4
#
#         cadence = 24 / cadence  # delta_hours/points
#
#         ### Fixing the time consumption
#         cadence *= 2 / 3
#         ipp *= 2 / 3
#
#     jitter = cadence
#     need_to_submit = check_pending_observations(obs_name, 'PENDING')
#
#     if need_to_submit is False:
#         return
#
#     mag_now = TAP.TAP_mag_now(target)
#     mag_exposure = mag_now
#
#     exposure_time_ip = TAP.calculate_exptime_omega_sdss_i(mag_exposure)
#
#     telescope_class = TAP.TAP_telescope_class(mag_now)
#
#     if telescope_class == '2m':
#
#         start = Time(datetime.datetime.utcnow())
#         end = Time(datetime.datetime.utcnow() + datetime.timedelta(days=obs_duration))
#
#         visible_at_muscat = calculate_visibility(target.ra, target.dec, start, end, 'OGG', max_airmass=max_airmass)
#         moon_sep_at_muscat = all_night_moon_sep(target.ra, target.dec, start, end, 'OGG', sample_size=75)
#
#         if visible_at_muscat and min(moon_sep_at_muscat[0]) >= 15:
#
#             build_and_submit_muscat(target, obs_type)
#             return
#
#         else:
#
#             instrument_type = '2M0-SCICAM-SPECTRAL'
#             exposure_time_ip /= 2  # area ratio (kind of...)
#
#     if telescope_class == '0.4m':
#         # currently disabled this since we do not have 0.4m time
#         pass
#         # instrument_type = '0M4-SCICAM-SBIG'
#         # exposure_time_ip *= 4 # area ratio
#
#     exposure_time_gp = np.min(
#         (exposure_time_ip * 3., 600))  # no more than 10 min. Factor 3 returns same SNR for ~(g-i) = 1.2
#
#     # ip alone
#     obs_dic = {}
#
#     start = datetime.datetime.utcnow().isoformat()
#     end = (datetime.datetime.utcnow() + datetime.timedelta(days=obs_duration)).isoformat()
#     obs_dic['name'] = obs_name
#     obs_dic['target_id'] = target.id
#     obs_dic['start'] = start
#     obs_dic['end'] = end
#     obs_dic['observation_mode'] = observation_mode
#
#     obs_dic['ipp_value'] = ipp
#     obs_dic['exposure_count'] = 1
#     obs_dic['exposure_time'] = exposure_time_ip
#     obs_dic['period'] = cadence
#     obs_dic['jitter'] = jitter
#     obs_dic['max_airmass'] = max_airmass
#     obs_dic['proposal'] = proposal
#     obs_dic['filter'] = "ip"
#     obs_dic['instrument_type'] = instrument_type
#     obs_dic['facility'] = facility
#     obs_dic['observation_type'] = observing_type
#
#     request_obs = lco.LCOBaseObservationForm(obs_dic)
#     request_obs.is_valid()
#     the_obs = request_obs.observation_payload()
#
#     telescope = lco.LCOFacility()
#     observation_ids = telescope.submit_observation(the_obs)
#
#     for observation_id in observation_ids:
#         record = ObservationRecord.objects.create(
#             target=target,
#             facility='LCO',
#             parameters=request_obs.serialize_parameters(),
#             observation_id=observation_id
#         )
#     # gp,ip
#
#     delta_time = cadence / 2
#
#     start = (datetime.datetime.utcnow() + datetime.timedelta(hours=delta_time)).isoformat()
#     end = (datetime.datetime.utcnow() + datetime.timedelta(days=obs_duration) + datetime.timedelta(
#         hours=delta_time) + datetime.timedelta(hours=4 * (exposure_time_gp + 300) / 3600.)).isoformat()
#
#     obs_dic = {}
#     obs_dic['name'] = obs_name
#     obs_dic['target_id'] = target.id
#     obs_dic['start'] = start
#     obs_dic['end'] = end
#     obs_dic['observation_mode'] = observation_mode
#
#     obs_dic['ipp_value'] = ipp
#     obs_dic['exposure_count'] = 1
#     obs_dic['exposure_time'] = exposure_time_ip + exposure_time_gp + 300  # Hack
#     obs_dic['period'] = cadence + exposure_time_gp / 3600. * 2  # Hack
#     obs_dic['jitter'] = jitter + exposure_time_gp / 3600. * 2  # Hack
#     obs_dic['max_airmass'] = max_airmass
#     obs_dic['proposal'] = proposal
#     obs_dic['filter'] = "ip"
#     obs_dic['instrument_type'] = instrument_type
#     obs_dic['facility'] = facility
#     obs_dic['observation_type'] = observing_type
#
#     request_obs = lco.LCOBaseObservationForm(obs_dic)
#     request_obs.is_valid()
#     the_obs = request_obs.observation_payload()
#
#     list_of_filters = ["ip", "gp"]
#
#     # if in the Bulge, switch gp to rp
#
#     event_in_the_Bulge = TAP.event_in_the_Bulge(target.ra, target.dec)
#
#     if (event_in_the_Bulge):
#         list_of_filters[-1] = "rp"
#         exposure_time_gp = exposure_time_gp / 2  # Factor 3/2 returns same SNR for ~(g-i) = 0.4
#
#     # Hacking the LCO TOM form to add several filters
#     instument_config = the_obs['requests'][0]['configurations'][0]['instrument_configs'][0]
#     exposure_times = [exposure_time_ip, exposure_time_gp]
#
#     for ind_req, req in enumerate(the_obs['requests']):
#         for ind_fil, fil in enumerate(list_of_filters):
#
#             if ind_fil > 0:
#                 new_instrument_config = copy.deepcopy(instument_config)
#                 new_instrument_config['optical_elements']['filter'] = fil
#                 new_instrument_config['exposure_time'] = exposure_time_gp
#
#                 the_obs['requests'][ind_req]['configurations'][0]['instrument_configs'].append(new_instrument_config)
#             else:
#                 the_obs['requests'][ind_req]['configurations'][0]['instrument_configs'][0][
#                     'exposure_time'] = exposure_time_ip
#
#     telescope = lco.LCOFacility()
#     observation_ids = telescope.submit_observation(the_obs)
#
#     for observation_id in observation_ids:
#         record = ObservationRecord.objects.create(
#             target=target,
#             facility='LCO',
#             parameters=request_obs.serialize_parameters(),
#             observation_id=observation_id
#         )