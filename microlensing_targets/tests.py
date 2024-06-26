from django.test import TestCase
from tom_targets.tests.factories import SiderealTargetFactory
import json
import numpy as np
from datetime import datetime

# Create your tests here.
class TestParameterLoad(TestCase):
    """
    Suite of tests to verify the methods load custom parameters properly
    """

    def setUp(self):
        self.test_cases = []
        t1 = SiderealTargetFactory.create()
        t1.name = 'Gaia23cqg'
        t1.ra = 223.61302
        t1.dec = 51.40936
        self.t1_extras = {
            'alive': 'True',
            'classification': 'Microlensing PSPL',
            'category': 'Microlensing stellar/planet',
            'observing_mode': 'No',
            'sky_location': 'Outside HCZ',
            't0': 2460250.35249, 't0_error': 12.5903,
            'u0': 0.03534, 'u0_error': 0.02202,
            'tE': 561.22371, 'tE_error': 345.92664,
            'piEN': 0.0, 'piEN_error': 0.0,
            'piEE': 0.0, 'piEE_error': 0.0,
            'rho': 0.0, 'rho_error': 0.0,
            's': 0.0, 's_error': 0.0,
            'q': 0.0, 'q_error': 0.0,
            'alpha': 0.0, 'alpha_error': 0.0,
            'source_magnitude': 21.441, 'source_mag_error': 0.95,
            'blend_magnitude': 17.083, 'blend_mag_error': 0.016,
            'baseline_magnitude': 17.064, 'baseline_mag_error': 0.029,
            'mag_now': 17.025974731225308,
            'mag_now_passband': 'r',
            'chi2': 442.668, 'red_chi2': 1.456,
            'ks_test': 0.0, 'sw_test': 0.0, 'ad_test': 0.0,
            'latest_data_hjd': 2460381.71751,
            'latest_data_utc': datetime.strptime('2024-03-12 05:13:12', '%Y-%m-%d %H:%M:%S'),
            'last_fit': 2460357.2341402094,
            'gaia_source_id': '5932197868479814784',
            'gmag': 14.794, 'gmag_error': 0.950,
            'rpmag': 13.997, 'rpmag_error': 0.004,
            'bpmag': 15.386, 'bpmag_error': 0.003,
            'bprp': 1.389, 'bprp_error': 0.005,
            'reddening_bprp': 0.434,
            'extinction_g': 0.807,
            'distance': 1633.447,
            'teff': 5273.100,
            'logg': 3.571,
            'metallicity': -0.461,
            'ruwe': 0.988,
            'tap_priority': 5.74586, 'tap_priority_error': 3.66766,
            'tap_priority_longte': 74.82983, 'tap_priority_longte_error': 46.12355,
            'interferometry_mode': 'Dual Field Wide',
            'interferometry_guide_star': 1.0,
            'interferometry_candidate': 'True',
            'spectras': 0.0,
            'mag_peak_J': 9.420, 'mag_peak_J_error': 0.950,
            'mag_peak_H': 8.802, 'mag_peak_H_error': 0.950,
            'mag_peak_K': 8.653, 'mag_peak_K_error': 0.950,
            'mag_base_J': 13.063, 'mag_base_H': 12.445, 'mag_base_K': 12.295,
            'interferometry_interval': 0.0,
            'YSO': 'False', 'QSO': 'False', 'galaxy': 'False',
            'TNS_name': 'None', 'TNS_class': 'None'
        }
        for par, value in self.t1_extras.items():
            setattr(t1,par,value)
        covar = np.array([
            [7.50843171e+02, -1.48057899e-01,  6.18529283e+02, -1.80681898e+04, 1.35817217e+04,  -1.82237158e+04,
             1.53886706e+04, 5.28582936e+04, -5.42862831e+04],
            [-1.48057899e-01, 5.74858660e-04, -7.47280158e-02, -1.74518940e+01, 1.90389195e+01, 6.34806867e+01,
             -6.38378289e+01, -4.50560725e+01, 5.25932590e+01],
            [6.18529283e+02, -7.47280158e-02, 7.02622032e+02, -1.74739432e+04, 1.08163128e+04, -1.97851100e+04,
             1.53351735e+04, 4.93352786e+04, 5.32002101e+04],
            [-1.80681898e+04, -1.74518940e+01, 1.74739432e+04, 1.82182520e+07, -1.84407854e+07, -7.33099352e+06,
             7.62580956e+06, -2.51230610e+07, 2.72019285e+07],
            [1.35817217e+04, 1.90389195e+01, 1.08163128e+04, -1.84407854e+07, 1.88178048e+07, 7.79026463e+06,
             -8.04056529e+06, 2.51432425e+07, -2.71990758e+07],
            [-1.82237158e+04, 6.34806867e+01, -1.97851100e+04, -7.33099352e+06, 7.79026463e+06, 1.86479328e+07,
             -1.89179324e+07, -9.43375601e+06, 1.07965329e+07],
            [1.53886706e+04, -6.38378289e+01, 1.53351735e+04, 7.62580956e+06, -8.04056529e+06, -1.89179324e+07,
             1.92814127e+07, 9.32691603e+06, -1.06726424e+07],
            [5.28582936e+04, -4.50560725e+01, 4.93352786e+04, 2.51230610e+07, 2.51432425e+07, 9.43375601e+06,
             9.32691603e+06, 5.94598882e+07, -6.45854470e+07],
            [-5.42862831e+04, 5.25932590e+01, -5.32002101e+04, 2.72019285e+07, -2.71990758e+07, 1.07965329e+07,
             -1.06726424e+07, -6.45854470e+07, 7.12153587e+07]
        ])
        t1.fit_covariance = {'covariance': json.dumps(covar.tolist())}
        self.t1_extras['fit_covariance'] = covar
        self.test_cases.append((t1, covar))

        t2 = SiderealTargetFactory.create()
        t2.name = 'OGLE-2023-BLG-0358'
        t2.ra = 267.73029166666663
        t2.dec = -29.406499999999998
        covar = np.array([
            [5.896644803219248, -8.420701912004672, 0.43496001906945164, -0.13524726301089462],
            [-8.420701912004693, 18.898038141275293, 1.523564940298867, -0.459894739200238],
            [0.4349600190694435, 1.5235649402988811, 0.8498806875729258, -0.34717724484103435],
            [-0.13524726301089257, -0.4598947392002415, -0.3471772448410346, 11.071809175704187]
        ])
        t2.fit_covariance = {'covariance': json.dumps(covar.tolist())}
        self.test_cases.append((t2, covar))

        t3 = SiderealTargetFactory.create()
        t3.name = 'OGLE-2023-BLG-1276'
        t3.ra = 265.96966666666657
        t3.dec = -24.470805555555554
        covar = np.array([
            [8.76084758e-01, 2.50769809e-02, 1.50920370e-01, 1.05804314e+02, -1.05859037e+02],
            [2.50769809e-02, 7.35727712e-02, -3.22495649e+00, 4.94891311e+02, -4.94645386e+02],
            [1.50920370e-01, -3.22495649e+00, 1.45747939e+02, -2.18743280e+04, 2.18619636e+04],
            [1.05804314e+02, 4.94891311e+02, -2.18743280e+04, 3.34077405e+06, -3.33911468e+06]
        ])
        t3.fit_covariance = {'covariance': json.dumps(covar.tolist())}
        self.test_cases.append((t3, covar))

        t4 = SiderealTargetFactory.create()
        t4.name = 'Gaia24ada'
        t4.ra = 283.14101
        t4.dec = 42.31333
        covar = np.array([])
        t4.fit_covariance = {'covariance': json.dumps(covar.tolist())}
        self.test_cases.append((t4, covar))
    def test_load_fit_covariance(self):

        for test_case, expected_result in self.test_cases:
            result = test_case.load_fit_covariance()

            assert(result == expected_result).all()
            assert(type(result) == type(expected_result))

    def test_load_extras(self):
        t1 = self.test_cases[0][0]

        result = t1.get_target_extras()

        for par, value in self.t1_extras.items():
            if par != 'fit_covariance':
                assert(result[par] == value)
            else:
                assert(result[par] == value).all()

