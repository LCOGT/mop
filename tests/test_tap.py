from django.test import TestCase
from tom_targets.tests.factories import SiderealTargetFactory
from tom_dataproducts.models import ReducedDatum
from .test_fittools import generate_test_ReducedDatums
from mop.toolbox import TAP
from unittest import skip
from astropy.time import Time, TimeDelta
from astropy import units as u
import numpy as np
from datetime import datetime

from os import getcwd, path
from mop.brokers import gaia as gaia_mop
from astropy.time import Time, TimezoneInfo

class TestObservingMode(TestCase):
    def setUp(self):
        self.params = [{
                            'planet_priority': 7.5e-5,
                            'planet_priority_error': 0.026,
                            'long_priority': 0.01,
                            'long_priority_error': 1341260.75767964,
                            'mag_now': 14.292,
                            'mag_baseline': 15.0,
                            'tE': 30.0,
                            'tE_error': 0.1,
                            'obs_mode': None,
                            'red_chi2': 1.0,
                            't0': 2460004.97378,
                            'time_now': 2460003.5
                        },
                        {
                            'planet_priority': 15.0,
                            'planet_priority_error': 1.0,
                            'long_priority': 0.01,
                            'long_priority_error': 1e5,
                            'mag_now': 15.5,
                            'mag_baseline': 18.0,
                            'tE': 30.0,
                            'tE_error': 0.1,
                            'obs_mode': 'priority_stellar_event',
                            'red_chi2': 1.0,
                            't0': 2460004.97378,
                            'time_now': 2460003.5
                        },
                        {
                            'planet_priority': 0.01,
                            'planet_priority_error': 10.0,
                            'long_priority': 75.0,
                            'long_priority_error': 5.0,
                            'mag_now': 15.0,
                            'mag_baseline': 16.8,
                            'tE': 300.0,
                            'tE_error': 0.1,
                            'obs_mode': 'priority_long_event',
                            'red_chi2': 1.0,
                            't0': 2460004.97378,
                            'time_now': 2460003.5
                        },
                        {
                            'planet_priority': 0.01,
                            'planet_priority_error': 10.0,
                            'long_priority': 20.0,
                            'long_priority_error': 5.0,
                            'mag_now': 16.0,
                            'mag_baseline': 16.8,
                            'tE': 300.0,
                            'tE_error': 0.1,
                            'obs_mode': 'regular_long_event',
                            'red_chi2': 1.0,
                            't0': 2460004.97378,
                            'time_now': 2460003.5
                        },
                        {
                            'planet_priority': np.nan,
                            'planet_priority_error': np.nan,
                            'long_priority': 0.0,
                            'long_priority_error': 0.0,
                            'mag_now': 13.28,
                            'mag_baseline': 14.4,
                            'tE': 30.0,
                            'tE_error': 0.1,
                            'obs_mode': None,
                            'red_chi2': 5.3,
                            't0': 2460004.97378,
                            'time_now': 2460003.5
                        },
                        ]

    def test_TAP_observing_mode(self):
        for event in self.params:
            print(event)
            obs_mode = TAP.TAP_observing_mode(
                event['planet_priority'],
                event['planet_priority_error'],
                event['long_priority'],
                event['long_priority_error'],
                event['tE'],
                event['tE_error'],
                event['mag_now'],
                event['mag_baseline'],
                event['red_chi2'],
                event['t0'],
                event['time_now']
            )
            self.assertEqual(obs_mode, event['obs_mode'])

class TestEventLocation(TestCase):
    def setUp(self):
        self.kmtnet_fields = TAP.load_KMTNet_fields()
        self.params = [
            {'test': (268.0, -28.60972),
             'expect': True},
            {'test': (150.0, -28.60972),
             'expect': False},
            {'test': (268.0, 15.0),
             'expect': False},
        ]

    def test_event_in_HCZ(self):
        for config in self.params:
            status = TAP.event_in_HCZ(config['test'][0], config['test'][1], self.kmtnet_fields)
            assert (status == config['expect'])

class TestLightcurveData(TestCase):
    def setUp(self):
        st1 = SiderealTargetFactory.create()
        tel_configs = {
            'OGLE': {
                    'I': [200, 18.0, 0.01,
                          Time('2023-08-01T00:00:00.0', format='isot'),
                          TimeDelta(0.25*u.day)],
                    'G': [10, 17.5, 0.005,
                          Time('2023-08-01T00:00:00.0', format='isot'),
                          TimeDelta(1.0*u.day)]
            },
            'MOA': {
                    'R': [200, 18.0, 0.01,
                          Time('2023-10-01T00:00:00.0', format='isot'),
                          TimeDelta(0.25*u.day)],
            },
        }

        self.params = {
            'target': st1,
            'tel_configs': tel_configs
        }

        # Use this configuration to generate some photometry datapoints for testing
        photometry = generate_test_ReducedDatums(self.params['target'], self.params['tel_configs']['OGLE'], source_name='OGLE')
        photometry2 = generate_test_ReducedDatums(self.params['target'], self.params['tel_configs']['MOA'], source_name='MOA')

        # Generate a test lightcurve model
        self.params['lc_model'] = generate_test_lc_model(self.params['target'])
        st1.existing_model = self.params['lc_model']

    def test_TAP_time_last_datapoint(self):
        # Retrieve the photometry for the test target.  Note that we retrieve it here rather than
        # pass the photometry array into the test because the DB applies a TimeZone correction
        # which adjusts the datapoints.  So the timestamps of the ReducedDatums are slightly different.
        photometry = ReducedDatum.objects.filter(target=self.params['target']).order_by('timestamp')

        # Review timestamps of generated data
        ts = [Time(rd.timestamp, format='datetime').jd for rd in photometry if rd.data_type == 'photometry']
        ts = np.array(ts)
        idx = np.argsort(ts)
        expected_t_last = ts.max()

        # Calculate the timestamp of the latest datapoint
        (t_last_jd, t_last_date) = TAP.TAP_time_last_datapoint(self.params['target'])

        # Expect a floating point number in Julian Date, and a Time object
        tnow = datetime.utcnow()
        assert(t_last_jd > 2450000.0)
        assert(type(t_last_date) == type(tnow))

        # Test the correct most-recent timestamp is returned
        assert(t_last_jd == expected_t_last)

        # Now test to see what happens for a new target with no photometry
        st2 = SiderealTargetFactory.create()
        (t_last_jd, t_last_date) = TAP.TAP_time_last_datapoint(st2)

        # This should still return a floating point JD and datetime, but for a much earlier date
        assert (t_last_jd > 2440000.0)
        assert (type(t_last_date) == type(tnow))

        # Now repeat this test for OGLE data only
        photometry = ReducedDatum.objects.filter(
            target=self.params['target'], source_name__icontains='OGLE'
        ).order_by('timestamp')

        # Recalculate the time of last datapoint:
        ts = [Time(rd.timestamp, format='datetime').jd for rd in photometry if rd.data_type == 'photometry']
        ts = np.array(ts)
        idx = np.argsort(ts)
        expected_t_last = ts.max()

        # Calculate the timestamp of the latest datapoint
        (t_last_jd, t_last_date) = TAP.TAP_time_last_datapoint(self.params['target'], source_name='OGLE')

        # Test the correct most-recent timestamp is returned
        assert (t_last_jd == expected_t_last)

    def test_TAP_mag_now(self):
        mag_now = TAP.TAP_mag_now(self.params['target'])

        last_dp = self.params['lc_model']['lc_model_magnitude'][-1]

        assert(mag_now == last_dp)


class TestCheckBaselineSN(TestCase):
    def setUp(self):
        st1 = SiderealTargetFactory.create()
        st1.name = 'Gaia23cnu'
        cwd = getcwd()
        lightcurve_file = path.join(cwd, 'tests/data/Gaia23dka.csv')
        photometry = generate_gaia_ReducedDatums(st1, lightcurve_file, 'G')

        self.model_params = {
            't0' : 2460177.02487,
            'u0' : 0.00233,
            'tE' : 1973.49932,
            'source_magnitude' : 27.069,
            'blend_magnitude' : 18.666,
            'baseline_magnitude' : 18.666,

        }
        for key, value in self.model_params.items():
            setattr(st1, key, value)
        st1.existing_model = None
        st1.first_observation = st1.t0 - 0.5*st1.tE
        st1.last_observation = None
        st1.gsc_results = None
        st1.aoft_table = None
        st1.neighbours = []
        st1.save()
        
        self.params = {
            'target': st1,
            'lightcurve_file': lightcurve_file,
            'photometry': photometry,
            'latest_data_hjd': 2460281.0316
        }

    def test_TAP_baseline(self):
        baseline_exist = TAP.TAP_check_baseline(self.params['target'])
        assert (type(baseline_exist) == type(True))
        assert (baseline_exist == False)

class TestCheckBaselineUlens(TestCase):
    def setUp(self):
        st1 = SiderealTargetFactory.create()
        st1.name = 'Gaia23dau'
        cwd = getcwd()
        lightcurve_file = path.join(cwd, 'tests/data/Gaia23dau.csv')
        photometry = generate_gaia_ReducedDatums(st1, lightcurve_file, 'G')

        self.model_params = {
            't0': 2460237.97106,
            'u0': 0.33528,
            'tE': 136.26916,
            'source_magnitude': 19.964,
            'blend_magnitude': 17.476,
            'baseline_magnitude': 17.371,

        }
        for key, value in self.model_params.items():
            setattr(st1, key, value)
        st1.existing_model = None
        st1.first_observation = st1.t0 - 2.0*st1.tE
        st1.last_observation = None
        st1.gsc_results = None
        st1.aoft_table = None
        st1.neighbours = []
        st1.save()

        self.params = {
            'target': st1,
            'lightcurve_file': lightcurve_file,
            'photometry': photometry,
            'latest_data_hjd': 2460248.3823
        }

    def test_TAP_baseline(self):
        baseline_exist = TAP.TAP_check_baseline(self.params['target'])
        assert (type(baseline_exist) == type(True))
        assert (baseline_exist == True)

def generate_test_lc_model(target):
    """Method generates a lightcurve model and stores it as a ReducedDatum"""

    ndp = 100
    time_now = Time(datetime.now()).jd
    time_start = time_now - ndp
    times = np.linspace(time_start, time_now, ndp)
    mags = np.random.normal(loc=17.0, scale=0.01, size=ndp)
    model_time = datetime.strptime('2018-06-29 08:15:27.243860', '%Y-%m-%d %H:%M:%S.%f')

    data = {
        'lc_model_time': times.tolist(),
        'lc_model_magnitude': mags.tolist()
    }

    rd, created = ReducedDatum.objects.get_or_create(
        timestamp=model_time,
        value=data,
        source_name='MOP',
        source_location=target.name,
        data_type='lc_model',
        target=target
    )

    return data

def generate_gaia_ReducedDatums(target, lightcurve_file, tel_label):
    """Taken from test_fittools, by R. Street. Modified to match this test case.
    Method generates a set of ReducedDatums for different telescopes, as is held in the TOM for a
    single target
    """

    data = []
    ts_jds = np.loadtxt(lightcurve_file, delimiter=',', skiprows=2, usecols=1)
    mags = np.loadtxt(lightcurve_file, delimiter=',', skiprows=2, usecols=2, dtype='str')

    for i in range(len(mags)):
        if('untrusted' not in mags[i] and 'null' not in mags[i]):
            jd = Time(float(ts_jds[i]), format='jd', scale='utc')
            datum = {
                    'magnitude': float(mags[i]),
                    'filter': tel_label,
                    'error': gaia_mop.estimateGaiaError(float(mags[i]))
                    }
            rd, created = ReducedDatum.objects.get_or_create(
                timestamp=jd.to_datetime(timezone=TimezoneInfo()),
                value=datum,
                source_name='Gaia',
                source_location=target.name,
                data_type='photometry',
                target=target)

            if created:
                data.append(rd)

    return data

