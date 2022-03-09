from tom_observations.facility import GenericObservationFacility, GenericObservationForm, get_service_class
from tom_observations.facilities import lco
from tom_observations.cadence import CadenceForm
from tom_observations.models import ObservationRecord
from mop.toolbox.obs_details import all_night_moon_sep, calculate_visibility
from astropy.time import Time
from mop.toolbox import TAP
import datetime
from django.conf import settings
import copy
import numpy as np
import requests
import os
import json


def check_pending_observations(name,status):

    token  = os.getenv('LCO_API_KEY')
    username =  os.getenv('LCO_USERNAME')
    headers = {'Authorization': 'Token ' + token}
    url = os.path.join("https://observe.lco.global/api/requestgroups/?state="+status+"&user="+username+"&name="+name)

    response = requests.get(url, headers=headers, timeout=20).json()

    if response['count']==0:

       need_to_submit = True

    else:

       need_to_submit = False


    return need_to_submit

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

          ### Fixing the time consumption
          cadence *= 2/3
          
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
