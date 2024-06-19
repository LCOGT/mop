from django.test import TestCase
from tom_targets.models import Target
from tom_targets.tests.factories import SiderealTargetFactory
from astropy.time import Time, TimeDelta
import os
import numpy as np
from mop.toolbox import omegaII_strategy

class TestObsConfig(TestCase):
    def setUp(self):
        time_now = Time.now()
        tE = 30.0
        t0 = Time((time_now + 0.1*tE), format='isot')
        self.params = [
            {'target': SiderealTargetFactory.create(),
             'observing_mode': 'priority_stellar_event',
             'current_mag': 16.0,
             'time_now': time_now.jd,
             'tE': tE,
             't0': t0.jd},
            {'target': SiderealTargetFactory.create(),
             'observing_mode': 'priority_stellar_event',
             'current_mag': 18.0,
             'time_now': time_now.jd,
             'tE': tE,
             't0': t0.jd}
                    ]

    def test_get_default_obs_config(self):
        for test_target in self.params:
            config = omegaII_strategy.get_default_obs_config(test_target['target'])
            self.assertTrue(config['observation_mode']=='NORMAL')
            self.assertTrue(config['operator']=='SINGLE')
            self.assertTrue(config['instrument_type']=='1M0-SCICAM-SINISTRO')
            self.assertTrue(config['proposal']==os.getenv('LCO_PROPOSAL_ID'))
            self.assertTrue(config['facility']=='LCO')
            self.assertTrue(config['max_airmass']==2.0)
            self.assertTrue(config['min_lunar_distance']==15.0)
            self.assertTrue(config['max_lunar_phase']==1.0)
            self.assertTrue(config['target']==test_target['target'])

    def test_determine_obs_config(self):
        for test_target in self.params:
            configs = omegaII_strategy.determine_obs_config(test_target['target'],
                                                        test_target['observing_mode'],
                                                        test_target['current_mag'],
                                                        test_target['time_now'],
                                                        test_target['t0'],
                                                        test_target['tE'])

            # Test that this target results in the expected two configurations:
            self.assertTrue(len(configs) == 2)

            # Test that the contents of the list of configurations is a set
            # of dictionaries with the following keys populated:
            expected_keys = ['filters', 'ipp', 'tstart', 'tend', 'group_id',
                             'period', 'jitter', 'exposure_times', 'exposure_counts']
            for conf in configs:
                for key in expected_keys:
                    self.assertTrue(key in conf.keys())

                # TEMPORARY TEST FOR CAPPED EXPOSURES
                if test_target['current_mag'] > 17.5:
                    assert (np.array(conf['exposure_times']) == 180.0).all()
                    assert (np.array(conf['exposure_counts']) == 4).all()
