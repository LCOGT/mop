from mop.toolbox import TAP
from datetime import datetime, timedelta
import os
import numpy as np

def determine_obs_config(target, observing_mode, current_mag, time_now, t0, tE):
    """Function to determine the observational configuration for a given event, based on
    its characteristics and the Key Project's strategy

    observing_mode can be one of 'priority_stellar_event', 'priority_long_event', 'regular_long_event'
    """

    configs = []

    # Stellar and planetary lenses in the Bulge Extended Region and beyond
    if observing_mode == 'priority_stellar_event':

        # REGULAR MODE: The cadence of regular mode SDSS-i-band observations
        # depends on how close the event is to the peak:
        deltat = abs(t0 - time_now)/tE
        conf1 = get_default_obs_config(target)
        conf1['filters'] = ['SDSS-i']
        conf1['ipp'] = 1.0
        conf1['duration'] = 3.0   # days
        conf1['group_id'] = target.name+'_'+'reg_phot_ip'

        conf2 = get_default_obs_config(target)
        conf2['filters'] = ['SDSS-g','SDSS-i']
        conf2['ipp'] = 1.0
        conf2['duration'] = 3.0   # days
        conf2['group_id'] = target.name+'_'+'reg_phot_gpip',
        if deltat <= 0.2:
            conf1['period'] = 2.0   # hrs
            conf1['jitter'] = 2.0    # hrs
            conf2['period'] = 24.0  # hrs
            conf2['jitter'] = 24.0   # hrs

        elif deltat >= 0.2 and deltat <= 1.0:
            conf1['period'] = 8.0   # hrs
            conf1['jitter'] = 2.0    # hrs
            conf2['period'] = 24.0  # hrs
            conf2['jitter'] = 24.0   # hrs

        configs.append(conf1)
        configs.append(conf2)

        # PRIORITY MODE: For anomalous events not yet implemented; events need
        # human review

    # Long-tE events:
    elif observing_mode in ['priority_long_event', 'regular_long_event']:
        conf1 = get_default_obs_config(target)
        conf1['filters'] = ['SDSS-i']
        if observing_mode == 'priority_long_event':
            conf1['ipp'] = 1.05
        else:
            conf1['ipp'] = 1.0
        conf1['duration'] = 7.0  # days
        conf1['group_id'] = target.name + '_' + 'reg_phot_ip'
        conf1['period'] = 48.0   # hrs
        conf1['jitter'] = 48.0     # hrs

        conf2 = get_default_obs_config(target)
        conf2['filters'] = ['SDSS-g','SDSS-i']
        conf2['ipp'] = 1.0
        conf2['duration'] = 7.0  # days
        conf2['group_id'] = target.name + '_' + 'reg_phot_gpip'
        conf2['period'] = 168.0   # hrs
        conf2['jitter'] = 168.0     # hrs

        configs.append(conf1)
        configs.append(conf2)

    # For each active configuration, calculate the exposure time required in
    # each bandpass and assign the number of exposures to take. Also replace
    # duration with formal start and end datetimes:
    exposure_time_ip = TAP.calculate_exptime_omega_sdss_i(current_mag)
    exposure_time_gp = np.min(
        (exposure_time_ip * 3., 600))  # no more than 10 min. Factor 3 returns same SNR for ~(g-i) = 1.2

    ### TEMPORARY EXPTIME CAP
    # Due to a autoguider failures on the 1m network (known cases ELP/DomeA, CPT/DomeB)
    # exposure times are capped at 180s, following advice from science support
    max_exptime = 180.0
    exposure_time_gp = min(exposure_time_gp, max_exptime)
    exposure_time_ip = min(exposure_time_ip, max_exptime)
    ###

    for conf in configs:
        conf['exposure_times'] = []
        conf['exposure_counts'] = []
        for f in conf['filters']:
            if f == 'SDSS-i':
                conf['exposure_times'].append(exposure_time_ip)
            elif f == 'SDSS-g':
                conf['exposure_times'].append(exposure_time_gp)

            ### TEMPORARY EXP COUNT ADJUSTMENT
            # To compensate for the shorter exposures, if the exposure time
            # was capped above, then request more exposures.
            if conf['exposure_times'][-1] == max_exptime:
                conf['exposure_counts'].append(4)
            else:
                conf['exposure_counts'].append(2)

        start = datetime.utcnow()
        end = (datetime.utcnow() + timedelta(days=conf['duration']))
        del conf['duration']
        conf['tstart'] = start
        conf['tend'] = end

    return configs

def get_default_obs_config(target):
    """Function returns a dictionary with the standard configuration parameters common to
    all observations, including observation_mode, instrument_type, proposal details,
    facility and maximum airmass limits"""

    config = {
                'observation_mode': 'NORMAL',
                'operator': 'SINGLE',
                'instrument_type': '1M0-SCICAM-SINISTRO',
                'telescope_class': '1m0',
                'proposal': os.getenv('LCO_PROPOSAL_ID'),
                'facility': 'LCO',
                'max_airmass': 2.0,
                'min_lunar_distance': 15.0,
                'max_lunar_phase': 1.0,
                'target': target,
            }

    return config